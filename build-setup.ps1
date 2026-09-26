param(
    [string]$OutputPath = (Join-Path $PSScriptRoot "dist\RemoveBackground-Setup.exe")
)

$ErrorActionPreference = "Stop"

if ($env:OS -ne "Windows_NT") {
    throw "The setup executable can only be built on Windows."
}

$IExpress = Join-Path $env:SystemRoot "System32\iexpress.exe"
if (-not (Test-Path -LiteralPath $IExpress -PathType Leaf)) {
    throw "IExpress is not available on this Windows installation."
}

$OutputPath = [IO.Path]::GetFullPath($OutputPath)
$OutputDirectory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$TempDirectory = Join-Path ([IO.Path]::GetTempPath()) (
    "RemoveBackgroundSetup-" + [guid]::NewGuid().ToString("N")
)
New-Item -ItemType Directory -Path $TempDirectory | Out-Null

try {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "install.ps1") `
        -Destination (Join-Path $TempDirectory "install.ps1")

    $SedPath = Join-Path $TempDirectory "setup.sed"
    $Sed = @"
[Version]
Class=IEXPRESS
SEDVersion=3

[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=1
HideExtractAnimation=0
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=%InstallPrompt%
DisplayLicense=%DisplayLicense%
FinishMessage=%FinishMessage%
TargetName=%TargetName%
FriendlyName=%FriendlyName%
AppLaunched=%AppLaunched%
PostInstallCmd=%PostInstallCmd%
AdminQuietInstCmd=%AdminQuietInstCmd%
UserQuietInstCmd=%UserQuietInstCmd%
SourceFiles=SourceFiles

[SourceFiles]
SourceFiles0=$TempDirectory\

[SourceFiles0]
%FILE0%=

[Strings]
InstallPrompt=
DisplayLicense=
FinishMessage=
TargetName=$OutputPath
FriendlyName=Remove Background Setup
AppLaunched=powershell.exe -NoProfile -ExecutionPolicy Bypass -File install.ps1
PostInstallCmd=<None>
AdminQuietInstCmd=
UserQuietInstCmd=
FILE0="install.ps1"
"@
    Set-Content -LiteralPath $SedPath -Value $Sed -Encoding ASCII

    $IExpressProcess = Start-Process -FilePath $IExpress `
        -ArgumentList @("/N", "/Q", $SedPath) `
        -Wait -PassThru -WindowStyle Hidden
    if ($IExpressProcess.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $OutputPath)) {
        throw "IExpress did not create the setup executable (exit code $($IExpressProcess.ExitCode))."
    }
}
finally {
    if (Test-Path -LiteralPath $TempDirectory) {
        Remove-Item -LiteralPath $TempDirectory -Recurse -Force
    }
}

Write-Host "Built: $OutputPath" -ForegroundColor Green
Write-Host "The setup EXE downloads the stable remove-bg.exe release and registers the menu."
