import argparse
import sys
from pathlib import Path

from rembg import remove
from PIL import Image


def to_output_path(src: Path, out_dir: Path | None, suffix: str, inplace: bool):
    if inplace:
        return src
    base = src.stem + suffix + ".png"
    return (out_dir or src.parent) / base


def is_image(path: Path) -> bool:
    try:
        with Image.open(path) as im:
            im.verify()
        return True
    except Exception:
        return False


def process_file(src: Path, out_dir: Path | None, suffix: str, inplace: bool, overwrite: bool):
    if not src.exists():
        print(f"Skip (missing): {src}", file=sys.stderr)
        return

    if not is_image(src):
        print(f"Skip (not image): {src}", file=sys.stderr)
        return

    dst = to_output_path(src, out_dir, suffix, inplace)

    if dst.exists() and not overwrite and not inplace:
        print(f"Skip (exists): {dst}", file=sys.stderr)
        return

    # rembg.remove works with bytes; returns PNG bytes with alpha.
    data_in = src.read_bytes()
    data_out = remove(data_in)

    if inplace:
        # Overwrite with PNG; keep old file as .bak once to be safe.
        backup = src.with_suffix(src.suffix + ".bak")
        if not backup.exists():
            src.rename(backup)
        dst = src.with_suffix(".png")
        dst.write_bytes(data_out)
        print(f"Wrote: {dst}")
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data_out)
        print(f"Wrote: {dst}")


def iter_inputs(paths: list[Path], recursive: bool):
    for p in paths:
        if p.is_dir():
            if recursive:
                for x in p.rglob("*"):
                    if x.is_file():
                        yield x
            else:
                for x in p.iterdir():
                    if x.is_file():
                        yield x
        else:
            yield p


def main():
    ap = argparse.ArgumentParser(
        description="Remove background from images using rembg."
    )
    ap.add_argument("paths", nargs="+", help="Files or directories.")
    ap.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Write outputs to this folder.",
    )
    ap.add_argument(
        "-s",
        "--suffix",
        default="_no-bg",
        help="Suffix added to output name (default: _no-bg).",
    )
    ap.add_argument(
        "--inplace",
        action="store_true",
        help="Overwrite original as PNG (backs up once as .bak).",
    )
    ap.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing outputs when not inplace.",
    )
    ap.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recurse into directories.",
    )

    args = ap.parse_args()
    paths = [Path(p) for p in args.paths]

    any_done = False
    for p in iter_inputs(paths, args.recursive):
        try:
            process_file(
                p, args.output_dir, args.suffix, args.inplace, args.overwrite
            )
            any_done = True
        except Exception as e:
            print(f"Error: {p}: {e}", file=sys.stderr)

    if not any_done:
        sys.exit(1)


if __name__ == "__main__":
    main()
