param(
  [Parameter(Mandatory=$true)]
  [string]$Path,
  [int]$Threshold = 60,
  [int]$MaxLinesPerFile = 200
)

function Get-JsonlFiles($p) {
  if (Test-Path $p -PathType Leaf) {
    if ($p.ToLower().EndsWith(".jsonl") -or $p.ToLower().EndsWith(".ndjson")) { ,(Get-Item $p) } else { @() }
  } elseif (Test-Path $p -PathType Container) {
    Get-ChildItem -Path $p -Filter *.jsonl -File
  } else {
    @()
  }
}

function Get-TextFromRow($row) {
  if ($null -ne $row.extraction -and $row.extraction.PSObject.Properties.Name -contains 'text' -and $row.extraction.text) {
    return [string]$row.extraction.text
  }
  if ($row.PSObject.Properties.Name -contains 'text' -and $row.text) { return [string]$row.text }
  if ($row.PSObject.Properties.Name -contains 'content' -and $row.content) { return [string]$row.content }
  return ""
}

function Clean-Text([string]$s) {
  if (-not $s) { return "" }
  $t = [System.Text.RegularExpressions.Regex]::Replace($s, '<[^>]+>', ' ')
  $t = $t -replace '&nbsp;',' '
  $t = $t -replace '\s+',' '
  $t.Trim()
}

$files = Get-JsonlFiles -p $Path
if (-not $files -or $files.Count -eq 0) {
  Write-Error "No JSONL/NDJSON files found at: $Path"
  exit 2
}

"{0,-6}  {1,-6}  {2,-7}  {3}" -f "LINE","LEN","VERDICT","FILE :: PREVIEW"
"{0,-6}  {1,-6}  {2,-7}  {3}" -f "-----","-----","-------","----------------"

foreach ($f in $files) {
  $ln = 0
  Get-Content -LiteralPath $f.FullName -ReadCount 1 -ErrorAction Stop | ForEach-Object {
    $ln += 1
    if ($ln -gt $MaxLinesPerFile) { return }
    $line = $_.Trim()
    if (-not $line) { return }
    try {
      $row = $line | ConvertFrom-Json -Depth 100
    } catch {
      "{0,-6}  {1,-6}  {2,-7}  {3}" -f $ln, "-", "ERROR", "$($f.Name) :: <invalid json>"
      return
    }
    $raw = Get-TextFromRow -row $row
    $clean = Clean-Text -s $raw
    $len = ($clean).Length
    $verdict = if ($len -ge $Threshold) { "PASS" } else { "SHORT" }
    $preview = if ($clean.Length -gt 60) { $clean.Substring(0,60) + "…" } else { $clean }
    "{0,-6}  {1,-6}  {2,-7}  {3}" -f $ln, $len, $verdict, "$($f.Name) :: $preview"
  }
}