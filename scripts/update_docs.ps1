<# 
.SYNOPSIS
  Staged, committet und pusht die Projekt-Brückendateien (Status/Backlog/Changelog).

.PARAMETER Message
  Commit-Nachricht (Default generiert aus Datum/Zeit).

.PARAMETER Files
  Liste der Dateien, die aufgenommen werden sollen.
  Default: PROJECT_STATUS.md, BACKLOG.md, CHANGELOG.md

.PARAMETER Branch
  Ziel-Branch (Default = aktueller Branch)

.EXAMPLE
  ./scripts/update_docs.ps1 -Message "docs: status/backlog updated after sprint 03"
#>

param(
  [string]$Message = "",
  [string[]]$Files = @("PROJECT_STATUS.md","BACKLOG.md","CHANGELOG.md"),
  [string]$Branch = ""
)

function Fail($msg) { Write-Host "ERROR: $msg" -ForegroundColor Red; exit 1 }

# 1) Checks
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail "git nicht gefunden. Bitte installieren/ins PATH legen." }

# Im Git-Repo?
$gitTop = git rev-parse --show-toplevel 2>$null
if ($LASTEXITCODE -ne 0) { Fail "Kein Git-Repository (git rev-parse scheiterte)." }
Set-Location $gitTop

# 2) Branch ermitteln (falls nicht angegeben)
if ([string]::IsNullOrWhiteSpace($Branch)) {
  $Branch = (git rev-parse --abbrev-ref HEAD).Trim()
  if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($Branch)) { Fail "Konnte aktuellen Branch nicht ermitteln." }
}

# 3) Dateien prüfen
$missing = @()
foreach ($f in $Files) {
  if (-not (Test-Path $f)) { $missing += $f }
}
if ($missing.Count -gt 0) { Fail "Diese Dateien fehlen: $($missing -join ', ')" }

# 4) Stage + Commit
git add -- $Files
if ($LASTEXITCODE -ne 0) { Fail "git add fehlgeschlagen." }

if ([string]::IsNullOrWhiteSpace($Message)) {
  $ts = Get-Date -Format "yyyy-MM-dd HH:mm"
  $Message = "docs: update project bridge files ($ts)"
}

git commit -m "$Message"
if ($LASTEXITCODE -ne 0) {
  Write-Host "Hinweis: git commit hat evtl. nichts zu committen (keine Änderungen?)." -ForegroundColor Yellow
}

# 5) Push
git push origin $Branch
if ($LASTEXITCODE -ne 0) { Fail "git push fehlgeschlagen." }

Write-Host "✔ Erfolgreich aktualisiert & gepusht auf '$Branch'." -ForegroundColor Green
