<# 
.SYNOPSIS
  Aktualisiert Brückendateien auf neuem Branch und erstellt optional einen GitHub Pull Request.

.PARAMETER Title
  PR-Titel (Default generiert).

.PARAMETER Body
  PR-Beschreibung (Default generiert).

.PARAMETER Files
  Liste der Dateien; Default = Brückendateien.

.PARAMETER Base
  Ziel-Branch für den PR (Default: main)

.EXAMPLE
  ./scripts/update_docs_pr.ps1 -Title "docs: backlog/status refresh" -Body "Sprint 04 Abschluss" 
#>

param(
  [string]$Title = "",
  [string]$Body  = "",
  [string[]]$Files = @("PROJECT_STATUS.md","BACKLOG.md","CHANGELOG.md"),
  [string]$Base = "main"
)

function Fail($msg) { Write-Host "ERROR: $msg" -ForegroundColor Red; exit 1 }

# Checks
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail "git nicht gefunden." }

$gitTop = git rev-parse --show-toplevel 2>$null
if ($LASTEXITCODE -ne 0) { Fail "Kein Git-Repository." }
Set-Location $gitTop

# Timestamped Branch
$stamp = Get-Date -Format "yyyyMMdd-HHmm"
$branchName = "docs/update-$stamp"

# Files present?
$missing = @()
foreach ($f in $Files) { if (-not (Test-Path $f)) { $missing += $f } }
if ($missing.Count -gt 0) { Fail "Diese Dateien fehlen: $($missing -join ', ')" }

# Create branch from Base
git fetch origin $Base
if ($LASTEXITCODE -ne 0) { Fail "git fetch fehlgeschlagen." }
git switch -c $branchName origin/$Base
if ($LASTEXITCODE -ne 0) { Fail "Branch '$branchName' konnte nicht erstellt werden." }

# Stage + Commit
git add -- $Files
if ($LASTEXITCODE -ne 0) { Fail "git add fehlgeschlagen." }

$commitMsg = "docs: update project bridge files ($stamp)"
git commit -m "$commitMsg"
if ($LASTEXITCODE -ne 0) {
  Write-Host "Hinweis: commit evtl. leer (keine Änderungen?)." -ForegroundColor Yellow
}

git push -u origin $branchName
if ($LASTEXITCODE -ne 0) { Fail "git push fehlgeschlagen." }

# PR erstellen (wenn GitHub CLI vorhanden)
if (Get-Command gh -ErrorAction SilentlyContinue) {
  if ([string]::IsNullOrWhiteSpace($Title)) { $Title = $commitMsg }
  if ([string]::IsNullOrWhiteSpace($Body))  { $Body  = "Automatisches Update der Brückendateien (PROJECT_STATUS.md, BACKLOG.md, CHANGELOG.md)." }
  gh pr create --title "$Title" --body "$Body" --base "$Base" --head "$branchName"
  if ($LASTEXITCODE -eq 0) {
    Write-Host "✔ Pull Request erstellt." -ForegroundColor Green
  } else {
    Write-Host "PR-Erstellung via gh fehlgeschlagen. Bitte PR manuell auf GitHub erstellen." -ForegroundColor Yellow
  }
} else {
  Write-Host "GitHub CLI (gh) nicht gefunden. PR bitte manuell auf GitHub erstellen." -ForegroundColor Yellow
  Write-Host "Branch: $branchName  ->  Base: $Base"
}

Write-Host "✔ Fertig." -ForegroundColor Green
