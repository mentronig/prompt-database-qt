<#
Erstellt:
  - project_tree.txt           -> Liste aller Git-Whitelisted Dateien (vor Filter)
  - project_tree.filtered.txt  -> Liste der nach Include-Filter berücksichtigten Dateien
  - mtpe_repo.zip              -> ZIP nur mit (Git-Whitelist ∩ Include-Filter)

Whitelist-Quelle (Git):
  git ls-files --cached --others --exclude-standard
  (Optional strikt: --cached = nur versionierte Dateien)

Matching basiert auf PowerShell-Wildcards (-like):
	ui\**\* = rekursiv alle Dateien unter ui\
	*.py = alle Python-Dateien
Git liefert die Basis-Whitelist (tracked + untracked, nicht ignoriert). Der Include-Filter schränkt diese weiter ein.
Für einen reproduzierbaren Release-Snapshot ist -StrictTrackedOnly ideal.

Verwendung (Beispiele siehe unten):
	Standard (empfohlen): tracked + untracked (nicht ignoriert), mit den vordefinierten Include-Mustern
	.\export_project.ps1
	
	Strikt nur versionierte Dateien (wie git archive), mit Standard-Include
	.\export_project_whitelist.ps1 -StrictTrackedOnly

	Eigene Include-Muster (nur Python & Kernordner)
	.\export_project.ps1 -IncludePatterns @("*.py","ui\**\*","ingestion\**\*")

	Zusätzliche Excludes (z. B. Logs)
	 .\export_project.ps1 -ExtraExcludePatterns @("*.svg","*.pyc")
	.\export_project.ps1 -ExtraExcludePatterns @("*.log","data\exports\**\*")
#>

param(
    [string]$ZipName = "mtpe_repo.zip",
    [string]$TreeName = "project_tree.txt",
    [string]$FilteredTreeName = "project_tree.filtered.txt",
    [switch]$StrictTrackedOnly,
    # Whitelist-Filter: Es werden NUR Dateien einbezogen, die mind. EIN Muster matchen.
    # Standard: typische MT Prompt Engine-Projektpfade & Engineering-Dateitypen
    [string[]]$IncludePatterns = @(
        # Quellcode & Config
        "*.py","*.md","*.toml","*.yml","*.yaml","*.json","*.ini",
        "*.ps1","*.psm1","*.cmd","*.bat","*.sh",
        # Projektverzeichnisse (rekursiv)
        "ui\**\*","ingestion\**\*","tools\**\*","data\**\*","tests\**\*",
        "config\**\*","services\**\*","themes\**\*","utils\**\*","docs\**\*","scripts\**\*"
    ),
    # Optionale zusätzliche Excludes (nach (!) Include-Filter), z.B. Logfiles
    [string[]]$ExtraExcludePatterns = @("*.log","*.tmp","*.cache","*.bak")
)

function Assert-GitPresent {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "Git nicht gefunden. Bitte Git installieren oder PATH prüfen."
    }
}

function Get-RepoRoot {
    $root = (git rev-parse --show-toplevel 2>$null)
    if (-not $root) { throw "Kein Git-Repository gefunden. Bitte im Repo-Root ausführen." }
    return $root
}

function Convert-ToWindowsWildcard([string]$p) {
    # Git liefert "/" → für -like Wildcards Windows-Pfade verwenden
    return ($p -replace '/', '\')
}

function Matches-Any([string]$path, [string[]]$patterns) {
    foreach ($pat in $patterns) {
        if ($path -like $pat) { return $true }
    }
    return $false
}

try {
    Assert-GitPresent
    $repoRoot = Get-RepoRoot
    Set-Location $repoRoot

    # --- 1) Whitelist-Dateien von Git holen ---
    if ($StrictTrackedOnly) {
        $gitFiles = git ls-files --cached
    } else {
        $gitFiles = git ls-files --cached --others --exclude-standard
    }

    # Normalisieren zu Windows-Backslashes für Wildcard-Matching
    $gitFilesWin = $gitFiles | ForEach-Object { Convert-ToWindowsWildcard $_ }

    if (-not $gitFilesWin -or $gitFilesWin.Count -eq 0) {
        throw "Whitelist leer. Prüfe Repo-Inhalt oder .gitignore."
    }

    # Vollständige Whitelist in Datei (Info)
    $gitFilesWin | Sort-Object | Out-File -FilePath $TreeName -Encoding UTF8
    Write-Host "👉 Projektliste (vor Filter): $TreeName"

    # --- 2) Include-Filter anwenden ---
    $include = $gitFilesWin | Where-Object { Matches-Any $_ $IncludePatterns }

    # --- 3) Extra-Excludes nachschalten (feingranular) ---
    if ($ExtraExcludePatterns.Count -gt 0) {
        $filtered = foreach ($p in $include) {
            if (-not (Matches-Any $p $ExtraExcludePatterns)) { $p }
        }
    } else {
        $filtered = $include
    }

    if (-not $filtered -or $filtered.Count -eq 0) {
        throw "Nach Include-/Exclude-Filter keine Dateien übrig. Prüfe -IncludePatterns / -ExtraExcludePatterns."
    }

    # Gefilterte Liste in Datei
    $filtered | Sort-Object | Out-File -FilePath $FilteredTreeName -Encoding UTF8
    Write-Host "👉 Gefilterte Projektliste: $FilteredTreeName"

    # --- 4) ZIP bauen (nur gefilterte Dateien) ---
    if (Test-Path $ZipName) { Remove-Item $ZipName -Force }

    # In Batches zippen (Compress-Archive hat Argumentlimits)
    $batchSize = 2000
    $chunks = @()
    for ($i = 0; $i -lt $filtered.Count; $i += $batchSize) {
        $chunks += ,($filtered[$i..([Math]::Min($i+$batchSize-1, $filtered.Count-1))])
    }

    $first = $true
    foreach ($chunk in $chunks) {
        if ($first) {
            Compress-Archive -Path $chunk -DestinationPath $ZipName -CompressionLevel Optimal
            $first = $false
        } else {
            Compress-Archive -Path $chunk -Update -DestinationPath $ZipName
        }
    }

    Write-Host "✅ ZIP erstellt: $ZipName"
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}
