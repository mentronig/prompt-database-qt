# HOWTO – Tools & CLI (Hardening / Import / Tooling)

## Quick Start (TL;DR)

- **Immer** so ausführen:
  ```powershell
  & .\tools\run_with_kpi.cmd python -m <modul> [args]


Letzte Datensätze ansehen:

& .\tools\run_with_kpi.cmd python -m tools.show_last_records --limit 5


JSONL → DB importieren (mit Mapping + Mindestlänge):

& .\tools\run_with_kpi.cmd python -m tools.ingest_jsonl_to_db `
  --path "C:\Pfad\zu\out" `
  --map ".md=note;.html=enhancement" `
  --tag-map ".md=article,notes;.html=article,pattern" `
  --default-tags "article,pattern" `
  --min-content-len 60 `
  --verbose


Duplikate prüfen (Dry-Run):

& .\tools\run_with_kpi.cmd python -m tools.dedupe_db --mode Content



Ordner- & Aufruf-Konventionen

Repo-Root: data/prompts.json ist die einzige Quelle (PromptRepository findet ihn automatisch).

PowerShell: Zeilenumbruch mit Backtick ` (kein Caret ^).

Wrapper-Pflicht: Python-Module immer via & .\tools\run_with_kpi.cmd python -m modul.

Vorteil: KPI-Logging, Exitcodes, Fehlerzähler.

Pfad-Quoting: Windows-Pfade immer in "Anführungszeichen".


==================================================================================================================

KPI-Wrapper
tools\run_with_kpi.cmd

Zweck: Führt einen Python-Befehl aus, erfasst Pass/Fail, und loggt zusätzliche Fehler als extra_errors.

Aufruf:

& .\tools\run_with_kpi.cmd python -m tools.show_last_records --limit 5


Fehlerbehandlung:

Wrapper beendet nicht den Python-Prozess vorzeitig; er protokolliert das Ergebnis.

In der Konsole erscheint z. B.:

[kpi_logger] recorded: commit=<hash> outcome=pass pass_rate=100.00% extra_errors=0

Tool-Referenz
1) tools.ingest_jsonl_to_db — JSONL/NDJSON → DB

Zweck: Konvertiert Zeilen aus *.jsonl/*.ndjson (z. B. Output von article_fetcher_local) in normalisierte Prompt-Records und schreibt sie in data/prompts.json.

Funktionsweise (Kurz):

Lädt JSONL-Dateien (nur Top-Level im angegebenen Pfad).

Akzeptiert flache (title, text/content, tags) oder structured ({"extraction": {...}, "meta": {...}}) Zeilen.

Übergibt an ingestion.article_ingestor.map_extraction_to_prompts.

Optionale Ext→Kategorie/Tags-Mappings.

Filtert nach bereinigter Content-Länge.

Schreibt pro Record in DB (Append).

Parameter:

--path PATH (Pflicht): Datei oder Ordner mit *.jsonl/*.ndjson (kein Rekursiv-Scan).

--category TEXT: Fallback-Kategorie für alle Records, falls nicht gesetzt.

--default-tags "t1,t2": Zusatztags für alle Records.

--min-content-len N (Default 30): Records mit bereinigtem Content < N werden verworfen und als skipped_short gezählt.

--map ".md=note;.html=enhancement": Dateiendung → Kategorie.

--tag-map ".md=article,notes;.html=article,pattern": Dateiendung → zusätzliche Tags.

--map-overwrite: Überschreibt vorhandene category/tags mit Mapping statt nur zu ergänzen.

--dry-run: Nichts schreiben, nur zählen.

--verbose: Zeigt gelesene Dateien/Zeilen.

Ergebnis (JSON-Zeile):

{
  "ok": true,
  "files": 2,
  "lines": 20,
  "saved_prompts": 18,
  "skipped": 1,
  "skipped_short": 1,
  "errors": 0,
  "min_content_len": 60,
  "applied_category_mappings": 10,
  "applied_tag_mappings": 10
}


Fehler & Behandlung:

No JSONL files found at: … → Pfad prüfen; nur Top-Level; ggf. einzelne Datei übergeben.

invalid json → Zeile wird übersprungen; Datei weiterverarbeitet.

ModuleNotFoundError → IMMER über python -m + Wrapper aus dem Repo-Root starten.

Beispiel (erzwingen, z. B. bei kurzen Texten):

& .\tools\run_with_kpi.cmd python -m tools.ingest_jsonl_to_db `
  --path "C:\...\out" ` --category enhancement ` --default-tags "article,pattern" `
  --min-content-len 0 ` --verbose

2) tools.dedupe_db — Duplikate finden/entfernen (mit Backup)

Zweck: Ermittelt Duplikate in data/prompts.json und kann sie in-place entfernen (Backup wird vorher erzeugt).

Funktionsweise:

Schlüssel = title+content (Default) oder nur content.

content wird bereinigt/normalisiert (Whitespace). Danach Hash (SHA-256/16).

Parameter:

--mode [title+content|content] (Default title+content).

--keep [first|last] (Default first): Pro Duplikatgruppe welcher Datensatz bleibt.

--apply: Änderungen schreiben (sonst Dry-Run).

--limit-print N (Default 20): Max. Gruppen im Report.

Beispiele:

# Dry-Run
& .\tools\run_with_kpi.cmd python -m tools.dedupe_db --mode content

# Anwenden (mit Backup)
& .\tools\run_with_kpi.cmd python -m tools.dedupe_db --mode content --apply


Fehler & Behandlung:

DB not found → Prüfe Repo-Root, Datei existiert?

Unsupported DB format → Datei nicht im erwarteten Format; vorher mit Repo-Tools erzeugen.

3) tools.show_last_records — letzte N Datensätze

Zweck: Schneller Überblick über die letzten Einträge (Tabellen-Ausgabe).

Parameter:

--limit N (Default 5)

--fields "title,category,tags"

--truncate N (Default 80)

--json (volle Datensätze als JSON)

Beispiele:

& .\tools\run_with_kpi.cmd python -m tools.show_last_records --limit 5
& .\tools\run_with_kpi.cmd python -m tools.show_last_records --limit 5 --fields "title,category,tags" --truncate 60
& .\tools\run_with_kpi.cmd python -m tools.show_last_records --limit 10 --json

4) tools.print_db_info — Pfad/Größe/Anzahl

Zweck: Zeigt den absoluten DB-Pfad, Dateigröße und Item-Count.

Beispiel:

python -m tools.print_db_info


Hinweis: Direkter Aufruf ohne Wrapper ist hier ok; für KPI-Tracking aber gern:

& .\tools\run_with_kpi.cmd python -m tools.print_db_info

5) tools\jsonl_content_len.ps1 — Content-Länge je Zeile (JSONL)

Zweck: Debug: Zeigt bereinigte Content-Länge je JSONL-Zeile (um Threshold-Entscheidungen zu verstehen).

Parameter:

-Path (Datei oder Ordner; Top-Level)

-Threshold (Default 60)

-MaxLinesPerFile (Default 200)

Beispiel:

.\tools\jsonl_content_len.ps1 -Path "C:\...\out" -Threshold 60


Ausgabe (Beispiel):

LINE    LEN    VERDICT  FILE :: PREVIEW
-----   -----  -------  ----------------------------
1       12     SHORT    article_fetch_local_report.jsonl :: <!doctype html> …
2       124    PASS     ingest_log.jsonl :: This article explains …

6) tools.source_path_injector.ensure_source_path — Helper

Zweck: Anreicherung einer JSONL-Zeile um source_path + file:///… URL, damit Ext-Mapping greift.

Signatur:

ensure_source_path(row: dict, src_path: str|Path) -> dict


Verwendung (in article_fetcher_local.py):

from tools.source_path_injector import ensure_source_path

row = {...}  # bestehende Felder (title, text, …)
ensure_source_path(row, r"C:\pfad\datei.html")
# row["source_path"] und meta/url oder url werden gesetzt

Fehlerbilder & Troubleshooting

No JSONL files found at: …

Pfad zeigt auf Ordner ohne *.jsonl/*.ndjson auf Top-Level. Entweder einzelne Datei übergeben oder Dateien in den Ordner kopieren.

ModuleNotFoundError: No module named 'data'/'ingestion'

Aus Repo-Root starten und immer python -m modul verwenden (keine direkten .py-Aufrufe ohne -m).

Über Wrapper ausführen.

SyntaxError in Tool-Datei

Vermutlich PowerShell-Befehle in eine Python-Datei kopiert. Datei neu erstellen (nur Python-Inhalt).

Best Practices

Erst Dry-Run, dann --apply (Dedupe).

Backups: Dedupe erstellt automatisch backups\prompts_YYYYMMDDTHHMMSSZ.json.

KPI-Grün halten: Wrapper nutzen, kleine Schritte, nach jedem Schritt show_last_records + print_db_info.

Beispielablauf (End-to-End)
# 1) Import (mit Mindestlänge)
& .\tools\run_with_kpi.cmd python -m tools.ingest_jsonl_to_db `
  --path "C:\...\out" ` --default-tags "article,pattern" ` --min-content-len 60 ` --verbose

# 2) Falls zu kurz → Schwelle senken (z. B. 0) oder Daten nachbessern
& .\tools\run_with_kpi.cmd python -m tools.ingest_jsonl_to_db `
  --path "C:\...\out" ` --category enhancement ` --default-tags "article,pattern" ` --min-content-len 0

# 3) Sichtkontrolle
& .\tools\run_with_kpi.cmd python -m tools.show_last_records --limit 5
python -m tools.print_db_info

# 4) Duplikate prüfen/entfernen
& .\tools\run_with_kpi.cmd python -m tools.dedupe_db --mode content
& .\tools\run_with_kpi.cmd python -m tools.dedupe_db --mode content --apply

Anhänge

PowerShell-Zeilenumbruch: Backtick ` am Zeilenende.

Quoting: Pfade stets in "...".

UTF-8: Skripte als UTF-8 ohne BOM speichern (Standard in VS Code).