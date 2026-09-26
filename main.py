from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import sys
from functools import lru_cache
from pathlib import Path


APP_NAME = "Remove Background"
APP_DIRECTORY = "RemoveBackground"
EXECUTABLE_NAME = "remove-bg.exe"
MENU_TEXT = "Remove Background"
CONTEXT_MENU_KEY = (
    r"Software\Classes\SystemFileAssociations\image\shell\RemoveBackground"
)


def is_frozen() -> bool:
    """Return True when running from a PyInstaller executable."""
    return bool(getattr(sys, "frozen", False))


def install_directory() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is not available for this Windows user.")
    return Path(local_app_data) / "Programs" / APP_DIRECTORY


def notify_shell() -> None:
    """Tell Explorer that file associations have changed."""
    try:
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
    except (AttributeError, OSError):
        # Explorer also notices the registry change after it refreshes/restarts.
        pass


def register_context_menu(executable: Path) -> None:
    if os.name != "nt":
        raise RuntimeError("Explorer context-menu installation is Windows-only.")

    import winreg

    executable = executable.resolve()
    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER, CONTEXT_MENU_KEY, 0, winreg.KEY_WRITE
    ) as menu_key:
        winreg.SetValueEx(menu_key, "", 0, winreg.REG_SZ, MENU_TEXT)
        winreg.SetValueEx(menu_key, "MUIVerb", 0, winreg.REG_SZ, MENU_TEXT)
        winreg.SetValueEx(menu_key, "Icon", 0, winreg.REG_SZ, f"{executable},0")

    command = f'"{executable}" --context "%1"'
    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER,
        CONTEXT_MENU_KEY + r"\command",
        0,
        winreg.KEY_WRITE,
    ) as command_key:
        winreg.SetValueEx(command_key, "", 0, winreg.REG_SZ, command)

    notify_shell()


def unregister_context_menu() -> None:
    if os.name != "nt":
        raise RuntimeError("Explorer context-menu removal is Windows-only.")

    import winreg

    for key_path in (CONTEXT_MENU_KEY + r"\command", CONTEXT_MENU_KEY):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
        except FileNotFoundError:
            pass

    notify_shell()


def install_context_menu() -> Path:
    if not is_frozen():
        raise RuntimeError(
            "Context-menu installation must be run from the built remove-bg.exe. "
            "Run .\\build.ps1 first."
        )

    source = Path(sys.executable).resolve()
    destination_dir = install_directory()
    destination = destination_dir / EXECUTABLE_NAME
    destination_dir.mkdir(parents=True, exist_ok=True)

    if source != destination.resolve():
        shutil.copy2(source, destination)

    register_context_menu(destination)
    return destination


@lru_cache(maxsize=1)
def pillow_image_module():
    from PIL import Image

    return Image


@lru_cache(maxsize=1)
def background_remover():
    from rembg import remove

    return remove


def to_output_path(src: Path, out_dir: Path | None, suffix: str, inplace: bool) -> Path:
    if inplace:
        return src.with_suffix(".png")
    base = src.stem + suffix + ".png"
    return (out_dir or src.parent) / base


def is_image(path: Path) -> bool:
    try:
        with pillow_image_module().open(path) as image:
            image.verify()
        return True
    except Exception:
        return False


def process_file(
    src: Path,
    out_dir: Path | None,
    suffix: str,
    inplace: bool,
    overwrite: bool,
) -> bool:
    if not src.exists():
        print(f"Skip (missing): {src}", file=sys.stderr)
        return False

    if not src.is_file() or not is_image(src):
        print(f"Skip (not image): {src}", file=sys.stderr)
        return False

    dst = to_output_path(src, out_dir, suffix, inplace)

    if dst.exists() and not overwrite and not inplace:
        print(f"Skip (exists): {dst}", file=sys.stderr)
        return False

    data_out = background_remover()(src.read_bytes())

    if inplace:
        # Keep one backup of the original before writing the transparent PNG.
        backup = src.with_suffix(src.suffix + ".bak")
        if not backup.exists():
            src.rename(backup)

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data_out)
    print(f"Wrote: {dst}")
    return True


def iter_inputs(paths: list[Path], recursive: bool):
    for path in paths:
        if path.is_dir():
            items = path.rglob("*") if recursive else path.iterdir()
            for item in items:
                if item.is_file():
                    yield item
        else:
            yield path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Remove image backgrounds with rembg, or install the Windows Explorer "
            "context menu when the built EXE is run without a file."
        )
    )
    parser.add_argument("paths", nargs="*", help="Image files or directories.")

    setup_actions = parser.add_mutually_exclusive_group()
    setup_actions.add_argument(
        "--install",
        action="store_true",
        help="Install or repair the per-user Explorer context menu.",
    )
    setup_actions.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove the per-user Explorer context menu.",
    )

    parser.add_argument(
        "--context",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Write outputs to this folder.",
    )
    parser.add_argument(
        "-s",
        "--suffix",
        default="_no-bg",
        help="Suffix added to output names (default: _no-bg).",
    )
    parser.add_argument(
        "--inplace",
        action="store_true",
        help="Replace the source with a PNG and keep one .bak backup.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing outputs when not using --inplace.",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recurse into input directories.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.uninstall:
        try:
            unregister_context_menu()
            print("Explorer context menu removed.")
            return 0
        except Exception as error:
            print(f"Could not remove the Explorer context menu: {error}", file=sys.stderr)
            return 1

    if args.install or (is_frozen() and not args.paths):
        try:
            destination = install_context_menu()
            print(f"Installed {APP_NAME} to: {destination}")
            print(
                "Right-click an image and choose 'Remove Background'. "
                "On Windows 11, first choose 'Show more options'."
            )
            return 0
        except Exception as error:
            print(f"Could not install the Explorer context menu: {error}", file=sys.stderr)
            return 1

    if not args.paths:
        parser.print_help()
        print("\nBuild the EXE and run it without arguments to install the context menu.")
        return 2

    completed = 0
    failed = 0
    for path in iter_inputs([Path(value) for value in args.paths], args.recursive):
        try:
            if process_file(
                path,
                args.output_dir,
                args.suffix,
                args.inplace,
                args.overwrite,
            ):
                completed += 1
            else:
                failed += 1
        except Exception as error:
            failed += 1
            print(f"Error: {path}: {error}", file=sys.stderr)

    if completed:
        print(f"Finished: {completed} image(s) processed, {failed} skipped or failed.")
        return 0 if failed == 0 else 1

    print("No images were processed.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
