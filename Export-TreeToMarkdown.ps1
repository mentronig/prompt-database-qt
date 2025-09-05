<#
.SYNOPSIS
Erzeugt eine Markdown-Dokumentation eines Verzeichnisbaums (inkl. Dateien).

.PARAMETER RootPath
Wurzelverzeichnis, ab dem der Tree erzeugt wird.

.PARAMETER OutputPath
Pfad zur auszugebenden Markdown-Datei. Standard: ./verzeichnisbaum.md

.PARAMETER Exclude
Liste von Verzeichnis- oder Dateimustern (Wildcard, z. B. '.git','node_modules','*.tmp'), die ausgeschlossen werden.

.PARAMETER MaxDepth
Maximale Tiefe (0 = unbegrenzt).

.PARAMETER IncludeSizes
Wenn gesetzt, werden Dateigrößen angezeigt.

.PARAMETER ShowHidden
Wenn gesetzt, werden versteckte/System-Dateien und -Ordner mit ausgegeben.

.EXAMPLE
	Einfacher export
	.\Export-TreeToMarkdown.ps1 -RootPath "C:\Projekte\MeinRepo"

	Dateien ausklammern
	.\Export-TreeToMarkdown.ps1 -RootPath "C:\Projekte\MeinRepo" -OutputPath ".\tree.md" -Exclude ".git","node_modules",".venv" -IncludeSizes

	Mit Dateigröße und eigene Zieldatei
	.\Export-TreeToMarkdown.ps1 -RootPath "D:\Data" -OutputPath ".\tree.md" -IncludeSizes

	Tiefe Begrenzen
	.\Export-TreeToMarkdown.ps1 -RootPath "C:\inetpub\wwwroot" -MaxDepth 3 -ShowHidden



#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$RootPath,

    [Parameter()]
    [string]$OutputPath = (Join-Path -Path (Get-Location) -ChildPath "verzeichnisbaum.md"),

    [Parameter()]
    [string[]]$Exclude = @(".git","node_modules","bin","obj",".venv",".idea",".pytest_cache",".DS_Store"),

    [Parameter()]
    [int]$MaxDepth = 0,

    [Parameter()]
    [switch]$IncludeSizes,

    [Parameter()]
    [switch]$ShowHidden
)

begin {
    # --- Validierung ---
    if (-not (Test-Path -LiteralPath $RootPath)) {
        throw "RootPath '$RootPath' existiert nicht."
    }
    $RootPath = (Resolve-Path -LiteralPath $RootPath).Path

    # Ausgabe-Ordner anlegen (falls nötig)
    $outDir = Split-Path -Path $OutputPath -Parent
    if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
        New-Item -ItemType Directory -Path $outDir | Out-Null
    }

    # Hilfsfunktionen
    function Test-IsHiddenOrSystem {
        param([System.IO.FileSystemInfo]$Item)
        return (($Item.Attributes -band [IO.FileAttributes]::Hidden) -or ($Item.Attributes -band [IO.FileAttributes]::System))
    }

    function Test-IsExcluded {
        param(
            [System.IO.FileSystemInfo]$Item,
            [string[]]$Patterns
        )
        $name = $Item.Name
        $full = $Item.FullName

        foreach ($pat in $Patterns) {
            # Wildcards auf Name und Pfad anwenden
            if ($name -like $pat -or $full -like ("*" + $pat + "*")) {
                return $true
            }
        }
        return $false
    }

    function Get-ReadableSize {
        param([Int64]$Bytes)
        if ($Bytes -lt 1KB) { return "$Bytes B" }
        elseif ($Bytes -lt 1MB) { return ("{0:N1} KB" -f ($Bytes/1KB)) }
        elseif ($Bytes -lt 1GB) { return ("{0:N1} MB" -f ($Bytes/1MB)) }
        else { return ("{0:N1} GB" -f ($Bytes/1GB)) }
    }

    function Get-DisplayName {
        param(
            [System.IO.FileSystemInfo]$Item,
            [switch]$IncludeSizes
        )
        if ($Item.PSIsContainer) {
            return "$($Item.Name)/"
        } else {
            if ($IncludeSizes) {
                $size = Get-ReadableSize -Bytes ([int64]$Item.Length)
                return "$($Item.Name) ($size)"
            } else {
                return $Item.Name
            }
        }
    }

    # Core: Baum rekursiv als Liste von Zeilen aufbauen
    function Build-Tree {
        param(
            [string]$Path,
            [string]$Prefix = "",
            [int]$Depth = 0
        )

        $dir = Get-Item -LiteralPath $Path

        # Kinder sammeln: erst Ordner, dann Dateien – jeweils gefiltert/sortiert
        $children = @()
        try {
            $children = Get-ChildItem -LiteralPath $Path -Force -ErrorAction Stop
        } catch {
            # z. B. Zugriffsproblem -> Hinweis einfügen
            return @("$Prefix└── (Zugriff verweigert: $Path)")
        }

        # Filtern: versteckte/System-Elemente ausblenden, wenn nicht gewünscht
        if (-not $ShowHidden) {
            $children = $children | Where-Object { -not (Test-IsHiddenOrSystem $_) }
        }

        # Excludes
        if ($Exclude -and $Exclude.Count -gt 0) {
            $children = $children | Where-Object { -not (Test-IsExcluded -Item $_ -Patterns $Exclude) }
        }

        # Sortierung: Ordner A->Z, dann Dateien A->Z
        $dirs  = $children | Where-Object { $_.PSIsContainer } | Sort-Object Name
        $files = $children | Where-Object { -not $_.PSIsContainer } | Sort-Object Name
        $ordered = @($dirs + $files)

        $lines = New-Object System.Collections.Generic.List[string]
        for ($i = 0; $i -lt $ordered.Count; $i++) {
            $child = $ordered[$i]
            $isLast = ($i -eq $ordered.Count - 1)
            $connector = $isLast ? "└── " : "├── "
            $nextPrefix = $isLast ? ($Prefix + "    ") : ($Prefix + "│   ")
            $lines.Add($Prefix + $connector + (Get-DisplayName -Item $child -IncludeSizes:$IncludeSizes))

            # Tiefe beachten
            if ($child.PSIsContainer -and (($MaxDepth -eq 0) -or ($Depth + 1 -lt $MaxDepth))) {
                $subLines = Build-Tree -Path $child.FullName -Prefix $nextPrefix -Depth ($Depth + 1)
                foreach ($l in $subLines) { $lines.Add($l) }
            }
        }

        return $lines
    }

    $timestamp = Get-Date
}

process {
    try {
        $rootItem = Get-Item -LiteralPath $RootPath
        $header = @()
        $header += "# Verzeichnisbaum-Dokumentation"
        $header += ""
        $header += "**Root:** `$RootPath`  "  # zwei Leerzeichen für Markdown-Zeilenumbruch
        $header += "**Erstellt:** $($timestamp.ToString('yyyy-MM-dd HH:mm:ss'))  "
        $header += "**Optionen:** MaxDepth=$MaxDepth; IncludeSizes=$($IncludeSizes.IsPresent); ShowHidden=$($ShowHidden.IsPresent)"
        if ($Exclude.Count -gt 0) {
            $header += "**Exclude:** " + ($Exclude -join ", ")
        }
        $header += ""
        $header += "```text"
        $header += (Get-DisplayName -Item $rootItem)  # Root-Zeile
        $treeLines = Build-Tree -Path $RootPath
        if ($treeLines.Count -gt 0) {
            $header += $treeLines
        }
        $header += "```"
        $header += ""
        $header += '> Hinweis: Dieser Tree zeigt Ordner und Dateien. Einträge können per Parameter `-Exclude`, `-MaxDepth`, `-IncludeSizes` und `-ShowHidden` beeinflusst werden.'

        # Datei schreiben (UTF-8)
        $content = $header -join [Environment]::NewLine
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($OutputPath, $content, $utf8NoBom)

        Write-Host "Markdown-Datei erstellt: $OutputPath"
    }
    catch {
        Write-Error $_
        exit 1
    }
}
