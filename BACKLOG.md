# Backlog – MT Prompt Engine

> Arbeitsmodus: Windows 11 · PowerShell · Python 3.13 · **Aufrufe via** `tools\run_with_kpi.cmd` · KPI-Gates aktiv.

## Konventionen
- **Story-ID**: `S-xxx`, **Bug**: `B-xxx`, **Experiment**: `E-xxx`.
- Jede Story hat: **Ziel**, **Tasks**, **Akzeptanzkriterien (AK)**, **KPI/Checks**, **Status**, **Owner**.
- Checkboxes `- [ ] / - [x]` werden im Verlauf gepflegt (verbindliche Fortschrittsanzeige).
- **Definition of Done (global):**
  1) `pytest -q` grün; 2) Tools via Wrapper lauffähig; 3) **KPI**-Schwellen OK; 4) Doku aktualisiert.

---

## Stories

### [S-001] Tag Overloading – Normalisierung & Synonyme
**Ziel:** Einheitliche, robuste Tags in DB + UI (Normalisierung, Synonyme, DB-Update).  
**Tasks:**
- [x] `ingestion/tag_normalizer.py` implementieren (lowercase, trim, Sonderzeichen, Synonyme).
- [x] `ingestion/article_ingestor.py` → Mapping `extraction → prompts` inkl. `SourceMeta`.
- [x] Unit-Tests (`tests/test_tag_normalizer.py`, `tests/test_article_ingestor.py`).
- [x] UI: Anzeige/Filter kompatibel.
- [x] Migrations-Backup & Repo-Path-Fix (`PromptRepository` absolute Pfade).
**AK:** `pytest` grün (5+ Tests), importierte Datensätze enthalten normalisierte Tags.  
**KPI/Checks:** Dedupe-Rate < 5 %, Import-Pass-Rate > 95 %.  
**Status:** Done  
**Owner:** Mentronig  
**Verweis:** `docs/handovers/S-001_tag_overloading.md`

---

### [S-002] Ingest JSONL → DB (Mapping, Filter, Ext-Mapping)
**Ziel:** JSONL/NDJSON zuverlässig in `data/prompts.json` überführen.  
**Tasks:**
- [x] `tools/ingest_jsonl_to_db.py` (Default-Tags, Kategorie-Fallback).
- [x] **Ext→Kategorie/Tags**-Mapping + `source_path/src/url`-Erkennung.
- [x] `--min-content-len` Filter + Report (`saved`, `skipped_short`, `errors`).
- [x] Tools: `tools/show_last_records.py`, `tools/print_db_info.py`.
- [x] PowerShell: `tools/jsonl_content_len.ps1` (Längen-Debug).
**AK:** Import aus `out/*.jsonl` landet sichtbar in DB; Summary zeigt korrekte Zähler.  
**KPI/Checks:** Import-Pass-Rate ≥ 95 %, 0 ungefangene Exceptions.  
**Status:** Done  
**Owner:** Mentronig

---

### [S-003] Fetcher & Enrichment (lokal)
**Ziel:** Lokale HTMLs extrahieren; „view‑source“/escaped HTML unterstützen.  
**Tasks:**
- [x] `ingestion/article_fetcher_local.py` (unescape, Readability/Soup/Regex-Fallback, Report-JSONL).
- [x] `tools/jsonl_enrich_text.py` (aus Quell-HTML Text in JSONL-Zeilen nachtragen).
- [ ] Smoke-Tests mit Beispiel-HTMLs (escaped/unescaped).
**AK:** `article_fetch_local_report.jsonl` hat für Testseiten `extraction.text` > 60.  
**KPI/Checks:** Enrichment-Hit-Rate > 80 % bei „view-source“-Saves.  
**Status:** In Arbeit  
**Owner:** Mentronig

---

### [S-004] LLM Prompt‑Extractor (Agent)
**Ziel:** Prompts semantisch extrahieren, wenn Heuristik unzureichend.  
**Tasks:**
- [x] `tools/llm_extract_prompts.py` (Heuristik + LLM‑Fallback, OpenAI).
- [ ] JSON‑Schema‑Validator für Agent‑Output (strict).
- [ ] Kosten‑Limiter (max Tokens/Artikel, Tagesbudget).
- [ ] Retries mit Backoff; klare Fehlercodes.
**AK:** `llm_extract_prompts.jsonl` enthält strukturierte Prompts (`extraction.title/text`).  
**KPI/Checks:** Fallback‑Quote < 60 %, Kosten/Artikel ≤ Ziel.  
**Status:** In Planung  
**Owner:** Mentronig

---

### [S-005] UI‑Integration (Import & Agent)
**Ziel:** Bedienung aus der Oberfläche mit Fortschritt & Logs.  
**Tasks:**
- [x] Menü „Import → Bulk ingest folder…“ (QProcess, ProgressDialog).
- [ ] Button „Prompts extrahieren (LLM)“ (Datei/URL wählen → Agent → Import).
- [x] Smoke‑Test `tests/test_gui_mainwindow.py` (Instanziierung).  
**AK:** Nutzer kann HTML wählen → Agent/Fetcher → JSONL → DB → Erfolgsmeldung.  
**KPI/Checks:** UI‑Fehlerdialoge statt Tracebacks; R2G ≤ 3.  
**Status:** In Arbeit  
**Owner:** Mentronig

---

# S-006: UI-Integration – Einzel-HTML in Datenbank (Tool-gestützt)

## Kontext & Referenzen
- Bestehende Bulk-Ingest Story: **S-005_ui_integration_bulk_ingest** (Ordnerweise).
- Ziel hier: **Einzeldatei-Import** aus der GUI, mit denselben Tooling-Bausteinen wie S-005.
- Relevante Bereiche: `ui/` (PySide6), `ingestion/` (CLI-Module), `data/` (DB).

## Ziel
Aus der **GUI** heraus eine **HTML-Datei** auswählen und per vorhandenen CLI-Tools in **Prompts** umwandeln und in die **Datenbank** schreiben. Der gesamte Ablauf ist **nicht-blockierend** (QProcess), zeigt **Logs live** an und liefert eine **verlässliche Ergebnis-Summary** (z. B. `files`, `prompts`, `db_path`, `skipped`, `errors`).

## User Story
Als **Research-User** möchte ich in der App eine **HTML-Datei** auswählen und mit einem Klick **Prompts extrahieren** und **in die DB speichern**, damit ich Inhalte sofort im System weiterverwenden kann — ohne CLI oder manuelle Zwischenschritte.

## Business Value
- Schneller Import einzelner Artikel/Seiten ohne Batch-Vorbereitung  
- Reduziert Medienbrüche (kein Terminal nötig)  
- Hebelt die vorhandenen Tools direkt in der UI

## Annahmen
- `ingestion.llm_extract_prompts` akzeptiert **Datei- oder Ordnerpfade**. Falls nur Ordner unterstützt werden: Die UI legt eine **temporäre Arbeitsmappe** an, kopiert die Datei hinein und nutzt diesen Ordner.
- `ingestion.ingest_jsonl_to_db` nimmt den von Schritt 1 erzeugten `*.jsonl`-Pfad.
- Letzte Log-Zeile ist JSON-Summary (robust geparst über `last_json_line()`).

## Abhängigkeiten
- PySide6 (UI)
- CLI-Module in `ingestion/` (Fallback: `tools/`)
- Optional KPI-Wrapper: `scripts/run_with_kpi.*` bzw. `tools/run_with_kpi.*` (Windows)

## UX / Flow
1. Menü **Import → HTML-Datei importieren…**
2. Dateidialog (Filter: `*.html;*.htm`)
3. Start → Nicht-blockierende Ausführung (QProcess), **Live-Log** in Dock/Panel
4. Am Ende **Ergebnis-Tabelle** (Key/Value) mit `files`, `prompts`, `db_path`, `skipped`, `errors`
5. Fehler werden im Log und via MessageBox angezeigt; Retry möglich

## Technische Umsetzung (High-Level)
- **Neuer Dialog:** `ui/html_import_dialog.py` (analog zu `bulk_ingest_dialog.py`)
  - Steuert die Pipeline, zeigt Logs/Tabelle
- **Runner-Klasse wiederverwenden:** `ui/ingest_runner.py`
  - Neue Methode `build_commands_for_file(file_path: str)`
    - Bevorzugt `python -m ingestion.llm_extract_prompts --path <file_or_tmpdir> --mode llm-refine --model <cfg>`
    - Danach `python -m ingestion.ingest_jsonl_to_db --path <jsonl> --min-content-len <cfg> [--default-tags ...] [--category ...]`
    - Optional: Dedupe `python -m ingestion.dedupe_db --mode content --apply`
  - Windows: falls vorhanden Wrapper `scripts/run_with_kpi.*` / `tools/run_with_kpi.*` vorschalten
- **Parsing:** `last_json_line()` (robust: echte `\n`, literal `\\n`, Prefix-Noise)

### Telemetrie / KPI (optional)
- Metriken im Log extrahieren: Dauer je Schritt, #Prompts, Skip-Gründe
- Basis für spätere UI-Charts (S-005/S-002 Follow-Ups)

### Fehlerfälle & Handling
- Ungültige Datei oder leerer Inhalt → UI-Hinweis + Log-Eintrag
- CLI-ExitCode ≠ 0 → Fehlerdialog mit Step-Index und Code
- Summary fehlt → defensiver Default (`db_path`, `files=0`, `prompts=0`) + Warnung

## Akzeptanzkriterien (Gherkin)

  Scenario: Erfolgreicher Import einer HTML-Datei
    Given ich öffne "Import → HTML-Datei importieren…"
    And ich wähle eine gültige HTML-Datei aus
    When ich den Import starte
    Then sehe ich laufende Logs im UI
    And nach Abschluss erscheint eine Ergebnis-Summary mit mindestens den Keys "files", "prompts", "db_path"
    And "prompts" > 0
    And die Datenbankdatei ist vorhanden und wurde aktualisiert

  Scenario: Ungültige Datei
    Given ich wähle eine leere oder ungültige HTML-Datei
    When ich den Import starte
    Then erhalte ich eine verständliche Fehlermeldung im UI und im Log
    And es werden keine DB-Änderungen vorgenommen

  Scenario: CLI-Fehler im ersten Schritt
    Given die Tools sind nicht verfügbar oder liefern Exit-Code != 0
    When ich den Import starte
    Then zeigt das UI den fehlerhaften Schritt und den Exit-Code an
    And der Prozess wird sauber abgebrochen

## Definition of Done
- UI-Dialog **`HTML-Datei importieren…`** vorhanden, nicht-blockierend, mit Live-Log und Summary
- Einzeldatei-Pfad wird korrekt verarbeitet (Datei **oder** tmp-Ordner-Fallback)
- **Unit-Tests**:
  - Parser: `last_json_line()` (Echt-`\n`, literal `\\n`, Prefix-Noise)
  - Command-Builder für Einzeldatei: enthält `ingestion.llm_extract_prompts` und `ingestion.ingest_jsonl_to_db`
- **UI-Smoketest** (qtbot): Dialog lässt sich öffnen, Buttons sind wired, Start ruft Runner an (ohne echten Prozesslauf)
- **Doku aktualisiert**: `CHANGELOG.md`, `PROJECT_STATUS.md` (Status S-006), `BACKLOG.md` (verlinkt)
- **Commit-Message** vorhanden

## Aufgaben & Aufwand (T-Shirt)
- UI: `html_import_dialog.py` (S)
- Runner-Erweiterung: `build_commands_for_file()` + Wrapper-Erkennung wiederverwenden (S)
- Tests: Parser/Builder/Smoke (S–M)
- Doku: Changelog/Status/Backlog (XS)

## Testplan (kurz)
- **Unit**: Parser (3 Varianten), Builder (Datei & tmp-Ordner)
- **UI**: qtbot-Smoke (Instanziieren, Button-Enable, Start-Signal)
- **Manuell**: reale HTML-Datei → Logs prüfen → Summary/DB prüfen

## Nicht im Scope
- KPI-Charts in der UI
- Batch/Ordner (ist S-005)
- Duplikat-UI mit Undo (separate Story)

## Risiken
- Tool akzeptiert keine Einzeldatei → tmp-Ordner-Fallback nötig
- Parser erwartet genaue Form der Summary → robust gehalten (letzte `{...}`)

---

---

### [S-007] Datenqualität & Wartung
**Ziel:** Saubere DB, einfache Diagnose.  
**Tasks:**
- [x] `tools/dedupe_db.py` (Dry‑Run/Apply, Backup).
- [x] `tools/show_last_records.py` (Tabellenansicht).  
- [x] `tools/print_db_info.py` (Pfad, Count, Size).  
**AK:** Dedupe mit Backup funktioniert; letzte Datensätze sichtbar.  
**KPI/Checks:** Dedupe‑Rate < 5 %, keine Datenverluste.  
**Status:** Done  
**Owner:** Mentronig

---

### [S-008] Repository & Migration
**Ziel:** Stabiler DB‑Pfad, Backups, Migration bei Start.  
**Tasks:**
- [x] `PromptRepository`: Repo‑Root Auto‑Pfad (`data/prompts.json`), Debugpfad‑Log.
- [x] Start‑Backup & optionale Migration.  
**AK:** `python -m tools.print_db_info` zeigt absoluten Pfad, Backups werden erzeugt.  
**Status:** Done  
**Owner:** Mentronig

---

### [S-009] Dokumentation
**Ziel:** Reproduzierbarkeit & Onboarding.  
**Tasks:**
- [x] `docs/HOWTO_TOOLS.md` (alle Tools, Beispiele, Fehlerbilder).
- [x] KPI‑HowTo + Handover‑Template‑Ergänzung.  
**AK:** Doku deckt End‑to‑End import ab; Beispielbefehle funktionieren.  
**Status:** Done  
**Owner:** Mentronig

---

### [S-010] End‑to‑End‑Tests
**Ziel:** Pipeline‑Sicherheit über CLI/Tools.  
**Tasks:**
- [ ] Mini‑Fixture (HTML escaped/unescaped) → Enrichment → Import → Dedupe → Assert Count.
- [ ] Smoke‑Test LLM‑Agent (dry‑run; Schema‑Mock).  
**AK:** `pytest -q -m "e2e"` grün; Artefakte im Temp‑Workspace.  
**KPI/Checks:** R2G ≤ 3, Pass‑Rate 100 % für E2E‑Suite.  
**Status:** Geplant  
**Owner:** Mentronig

---

## Bugs
- [B-001] JSONL‑Reports mit `src` aber ohne `extraction.text` führen zu `saved=0` bei `--min-content-len>0`.  
  **Fix:** `tools/jsonl_enrich_text.py` einführen und im HowTo prominent verlinken. **Status:** Gefixt (Tool vorhanden).

---

## Experimente
- [E-001] Trafilatura vs. Readability vs. Soup‑Heuristik – Präzision/Länge.  
- [E-002] Playwright‑Render nur für problematische Seiten (Heuristik‑Trigger).  
- [E-003] On‑prem LLM (z. B. GPT‑4o‑Mini‑Compat) für DSGVO‑engere Kontexte.

