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
**Problem:** Ingest-Tools laufen aktuell primär manuell/CLI. In der UI fehlt eine robuste, messbare Integration mit Fortschritt und Ergebnis-Einblick.  
**Ziel:** Verlustfreie Integration in die GUI (Menü **Import → Bulk ingest folder…**) mit KPI-Wrapper, Fortschrittsdialog (Start/Cancel), Result-Panel (Counts, Skips, Dedupe, DB-Pfad).  
**Lösungsskizze:**  
- QAction `action_bulk_ingest` triggert Worker (QProcess) → ruft `tools/run_with_kpi.cmd` mit `llm_extract_prompts` (auto/llm-refine) und `ingest_jsonl_to_db` auf.  
- Fortschritt über QProcess-Stdout (Streaming), Cancel via `terminate()` + Soft-Cleanup.  
- Ergebnis-Panel mit: *files, prompts, saved_prompts, skipped_short, errors, jsonl, db_path*.  
- KPI-Events automatisch geloggt (keine Sonderbehandlung in UI).

**Akzeptanzkriterien:**  
- Start/Cancel/Close funktionieren ohne UI-Freeze.  
- KPI-Wrapper umschließt alle Aufrufe.  
- Ergebnisdaten werden sauber angezeigt (auch bei Fehlern/Abbruch).  
- Kein manueller Eingriff in Pfade (DB/Out) nötig.

- **Status:** Bereit zur Umsetzung (nächster Chat)
- **Owner:** Mentronig
- **Verweis:** docs/handovers/S-002_ui_integration_bulk_ingest.md

---

### [S-006] KPI & Gates
**Ziel:** Messbare Qualität/Produktivität; Ampellogik.  
**Tasks:**
- [x] Wrapper `tools/run_with_kpi.cmd` + Logger.
- [x] `tools/kpi_report.py` inkl. Ampel (Grenzwerte).
- [x] `README-KPI.md` + Handover‑Erweiterung.
**AK:** `tools/kpi_report.py --window 20` erzeugt Report + Ampel.  
**KPI/Checks:** Fehler/h ≤ 2; Pass‑Rate ≥ 90 %; R2G‑Median ≤ 3.  
**Status:** Done  
**Owner:** Mentronig

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

