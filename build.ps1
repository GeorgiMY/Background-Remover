param(
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$VenvDir = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $VenvPython)) {
    if ($PythonPath) {
        & $PythonPath -m venv $VenvDir
    }
    else {
        & py -3.13 -m venv $VenvDir
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Python 3.13 is required. Install it or pass -PythonPath with Python 3.11, 3.12, or 3.13."
    }
}

$Version = & $VenvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($Version -notin @("3.11", "3.12", "3.13")) {
    throw "rembg requires Python 3.11 through 3.13; the build environment is Python $Version."
}

& $VenvPython -m pip install --upgrade pip wheel
if ($LASTEXITCODE -ne 0) { throw "Could not update the build tools." }

& $VenvPython -m pip install -r (Join-Path $ProjectRoot "requirements-build.txt")
if ($LASTEXITCODE -ne 0) { throw "Could not install the build dependencies." }

Push-Location $ProjectRoot
try {
    & $VenvPython -m PyInstaller --noconfirm --clean "remove-bg.spec"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

    & (Join-Path $ProjectRoot "dist\remove-bg.exe") --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "The built executable did not start correctly." }
}
finally {
    Pop-Location
}

Write-Host "Built: $(Join-Path $ProjectRoot 'dist\remove-bg.exe')" -ForegroundColor Green
Write-Host "Double-click the EXE to install the Explorer context menu."
