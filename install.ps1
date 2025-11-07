$ErrorActionPreference = "Stop"

$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\RemoveBackground"
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

$ExeUrl = "https://github.com/GeorgiMY/Background-Remover/releases/download/stable-releases/remove-bg.exe"
$IcoUrl = "https://github.com/GeorgiMY/Background-Remover/releases/download/stable-releases/icon.ico"

$ExePath = Join-Path $InstallDir "remove-bg.exe"
$IconPath = Join-Path $InstallDir "icon.ico"

Invoke-WebRequest -Uri $ExeUrl -OutFile $ExePath
Invoke-WebRequest -Uri $IcoUrl -OutFile $IconPath

$BaseKey = "HKCU:\Software\Classes\SystemFileAssociations\image\shell\RemoveBackground"
New-Item -Path $BaseKey -Force | Out-Null
New-ItemProperty -Path $BaseKey -Name "MUIVerb" -PropertyType String `
  -Value "Remove background" -Force | Out-Null
New-ItemProperty -Path $BaseKey -Name "Icon" -PropertyType String `
  -Value $IconPath -Force | Out-Null

$CmdKey = Join-Path $BaseKey "command"
New-Item -Path $CmdKey -Force | Out-Null
Set-Item -Path $CmdKey -Value "`"$ExePath`" `"%1`""

Write-Host "Installed. Right-click an image > Show more options > Remove background."
