
param([switch]$NoTimestamp)
$ErrorActionPreference = "Stop"
$reports = Join-Path (Get-Location) "reports"
$lastDir = Join-Path $reports "last"
New-Item -ItemType Directory -Force -Path $lastDir | Out-Null
pytest
if (-not $NoTimestamp) {
  $ts = Get-Date -Format "yyyyMMdd-HHmmss"
  $outDir = Join-Path $reports $ts
  New-Item -ItemType Directory -Force -Path $outDir | Out-Null
  Copy-Item -Recurse -Force (Join-Path $lastDir "*") $outDir
  python tools\report_summary.py --junit "$($outDir)\junit.xml" --out-md "$($outDir)\summary.md" --out-html "$($outDir)\summary.html" | Out-Null
}
exit $LASTEXITCODE
