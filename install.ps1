param(
    [switch]$Uninstall,
    [string]$ExePath = ""
)

$ErrorActionPreference = "Stop"

$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\RemoveBackground"
$InstalledExe = Join-Path $InstallDir "remove-bg.exe"
$InstalledIcon = Join-Path $InstallDir "icon.ico"
$MenuKey = "HKCU:\Software\Classes\SystemFileAssociations\image\shell\RemoveBackground"

function Update-ExplorerAssociations {
    try {
        if (-not ("RemoveBackground.NativeMethods" -as [type])) {
            Add-Type -Namespace RemoveBackground -Name NativeMethods -MemberDefinition @"
[DllImport("shell32.dll")]
public static extern void SHChangeNotify(
    int eventId,
    uint flags,
    System.IntPtr item1,
    System.IntPtr item2
);
"@
        }

        [RemoveBackground.NativeMethods]::SHChangeNotify(
            0x08000000,
            0,
            [IntPtr]::Zero,
            [IntPtr]::Zero
        )
    }
    catch {
        Write-Warning "Explorer may need to be restarted before the menu changes appear."
    }
}

if ($Uninstall) {
    Remove-Item -LiteralPath $MenuKey -Recurse -Force -ErrorAction SilentlyContinue
    Update-ExplorerAssociations
    Write-Host "Explorer context menu removed."
    Write-Host "Installed files remain at: $InstallDir"
    exit 0
}

if (-not $ExePath) {
    $LocalBuild = Join-Path $PSScriptRoot "dist\remove-bg.exe"
    if (Test-Path -LiteralPath $LocalBuild -PathType Leaf) {
        $ExePath = $LocalBuild
    }
}

if ($ExePath) {
    if (-not (Test-Path -LiteralPath $ExePath -PathType Leaf)) {
        throw "Executable not found at '$ExePath'."
    }

    $ResolvedExe = (Resolve-Path -LiteralPath $ExePath).Path
    & $ResolvedExe --install
    exit $LASTEXITCODE
}

# No local build was supplied, so install the stable GitHub release.
$ExeUrl = "https://github.com/GeorgiMY/Background-Remover/releases/download/stable-releases/remove-bg.exe"
$IconUrl = "https://github.com/GeorgiMY/Background-Remover/releases/download/stable-releases/icon.ico"
$PendingExe = "$InstalledExe.download"
$PendingIcon = "$InstalledIcon.download"

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

try {
    Invoke-WebRequest -Uri $ExeUrl -OutFile $PendingExe
    Invoke-WebRequest -Uri $IconUrl -OutFile $PendingIcon
    Move-Item -LiteralPath $PendingExe -Destination $InstalledExe -Force
    Move-Item -LiteralPath $PendingIcon -Destination $InstalledIcon -Force
}
catch {
    Remove-Item -LiteralPath $PendingExe, $PendingIcon -Force -ErrorAction SilentlyContinue
    throw
}

New-Item -Path $MenuKey -Force | Out-Null
New-ItemProperty -Path $MenuKey -Name "MUIVerb" -PropertyType String `
    -Value "Remove Background" -Force | Out-Null
New-ItemProperty -Path $MenuKey -Name "Icon" -PropertyType String `
    -Value $InstalledIcon -Force | Out-Null

$CommandKey = Join-Path $MenuKey "command"
New-Item -Path $CommandKey -Force | Out-Null
Set-Item -Path $CommandKey -Value "`"$InstalledExe`" `"%1`""
Update-ExplorerAssociations

Write-Host "Installed Remove Background to: $InstalledExe" -ForegroundColor Green
Write-Host "Right-click an image and choose 'Remove Background'."
Write-Host "On Windows 11, first choose 'Show more options'."
