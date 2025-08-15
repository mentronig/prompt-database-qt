[CmdletBinding()]
param(
  [string]$Name = "PromptDBQt",
  [string]$Icon = "",
  [switch]$OneFile = $true,
  [switch]$Console = $false,
  [switch]$Clean = $true
)
$ErrorActionPreference = "Stop"
function Resolve-Python {
  $venvPy = Join-Path -Path (Join-Path -Path $PSScriptRoot -ChildPath "venv") -ChildPath "Scripts\python.exe"
  if (Test-Path $venvPy) { return $venvPy } else { return "python" }
}
$python = Resolve-Python
Write-Host "Using Python: $python"
try { & $python -m pip show pyinstaller | Out-Null } catch {
  Write-Host "Installing PyInstaller..."
  & $python -m pip install --upgrade pip
  & $python -m pip install pyinstaller
}
if ($Clean) { if (Test-Path build) { Remove-Item build -Recurse -Force } ; if (Test-Path dist) { Remove-Item dist -Recurse -Force } }
$cli = @()
if ($Console) { $cli += "--console" } else { $cli += "--noconsole" }
if ($OneFile) { $cli += "--onefile" } else { $cli += "--onedir" }
$cli += @("--name", $Name)
if ($Icon) { if (Test-Path $Icon) { $cli += @("--icon", $Icon) } else { Write-Warning "Icon '$Icon' not found – building without icon." } }
$cli += @(
  "--hidden-import","PySide6.QtCore",
  "--hidden-import","PySide6.QtGui",
  "--hidden-import","PySide6.QtWidgets",
  "--collect-submodules","PySide6",
  "--add-data","themes;themes",
  "--add-data","assets/icons;assets/icons",
  "--add-data",".env.template;."
)
Write-Host "Building..."
& $python -m PyInstaller @cli main.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed (exit $LASTEXITCODE)." }
$exe = Join-Path "dist" ("{0}.exe" -f $Name)
if (Test-Path $exe) { Write-Host "Done: $exe" } else { Write-Host "Build finished. Check 'dist\\'." }
