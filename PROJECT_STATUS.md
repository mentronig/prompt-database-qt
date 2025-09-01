# Projektstatus – MT Prompt Engine

## Überblick
- Projektname: **MT Prompt Engine**
- Ursprung: Weiterentwicklung des Projekts *Prompt-Database-QT*
- Ziel: Eine erweiterbare Prompt-Datenbank mit Ingest-Funktionen, UI (Qt), Backlog-Verwaltung und automatisierter Projektsteuerung.

## Aktueller Stand
- **Codebasis:** Prompt-Database-QT (Visual Studio Projekt, Python/PySide6)
- **Bestehende Features:**
  - PromptRepository (TinyDB als Backend)
  - Qt-UI mit Tabellenansicht, Detailansicht, Export (CSV, JSON, YAML, MD)
  - Artikel-Ingestor (`article_ingestor.py`) → wandelt Texte in Prompts und speichert in DB
  - Bulk-Ingest (`bulk_ingest_local.py`) für ganze Ordner mit .txt-Dateien
  - Integration Bulk-Ingest in GUI (Import-Menü, QProcess, Fortschrittsdialog)
  - Lokaler HTML-Fetcher (`article_fetcher_local.py`) → extrahiert Artikeltext aus gespeicherten HTML-Seiten
  - **LLM-Extraktion:** `tools/llm_extract_prompts.py` inkl. **Refine-Modus** (1:1 Ausgabe)
  - KPI-Wrapper (`tools/run_with_kpi.cmd`) + Reports
	
- **Neue Dokumentation:**
  - Handover-Templates für Stories, Bugs, Experimente (`docs/templates/…`)

## Offene Probleme
- HTML-Diversität: Heuristiken robust, dennoch Edge-Cases denkbar → LLM-Refine als Sicherheitsnetz.
- LLM-Verfügbarkeit: API-Key/Rate-Limits → Fallback auf Heuristik gesichert (kein Datenverlust).

## Nächste geplante Arbeiten (UI-Integration)
1. **QAction „Bulk ingest folder…“** an Worker-Prozess anbinden (QProcess, non-blocking).  
2. KPI-Wrapper für **alle** Aufrufe (`llm_extract_prompts`, `ingest_jsonl_to_db`, optional `dedupe_db`).  
3. Fortschrittsdialog (Start/Cancel) + Ergebnis-Panel (Zahlen/JSON-Summary, Pfade).  
4. Mini-Integrationstest (CLI) + UI-Smoketest erweitern.

## Definition of Ready (S-002)
- LLM-Tool + Import-Tool vorhanden (ja)  
- KPI-Wrapper vorhanden (ja)  
- Handover-Dokument liegt bei (ja)  

## Definition of Done (S-002)
- End-to-End aus der UI: HTML → JSONL → DB → Dedupe (optional) ohne manuelle Schritte.  
- KPI-Metriken geloggt; Fehlerpfade sichtbar.  
- Tests grün, Doku aktualisiert.

# Projektstatus – MT Prompt Engine (Auszug)

## S-006 – UI-Integration: Einzel-HTML → DB
**Status:** Geplant  
**Kurzbeschreibung:** Einzelne HTML-Datei aus der GUI auswählen, per Tooling (ingestion.*) zu Prompts verarbeiten und in DB schreiben. Nicht-blockierend, Live-Logs, Summary.  
**Nächste Schritte:**
- `html_import_dialog.py` umsetzen (analog Bulk-Dialog)
- `IngestRunner.build_commands_for_file()` ergänzen
- Tests (Parser/Builder/UI-Smoke) hinzufügen
**Abhängigkeiten:** PySide6, ingestion.*-Module, optional KPI-Wrapper

## S-005 – UI-Integration: Bulk-Ingest (Ordner)
**Status:** In Arbeit / Verfeinerung (KPI/Charts, Drag&Drop)

## S-002 – Repo-aligned Bulk Ingest
**Status:** Abgeschlossen
