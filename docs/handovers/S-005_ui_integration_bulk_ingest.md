# Smart Handover – S-005 UI-Integration: Bulk Ingest + KPI (Option B)

> **Ziel:** Verlustfreie, messbare UI-Integration des Bulk-Ingest-Workflows.  
> **Output:** Fertige Python-Dateien (vollständig), aktualisierte Doku (MD), Tests; ZIP-Format gemäß Template.

---

## 0) Projektstruktur (Soll)
Top-Level-Pakete: `config`, `data`, `docs`, `ingestion`, `models`, `scripts`, `services`, `tests`, `themes`, `ui`, `utils`, `tools`

Relevante Dateien (Auszug):
- `ui/main_window.py` (QAction `action_bulk_ingest`, QProcess-Integration)
- `tools/run_with_kpi.cmd` (KPI-Wrapper)
- `tools/llm_extract_prompts.py` (Modi inkl. `llm-refine`)
- `tools/ingest_jsonl_to_db.py`
- `tools/dedupe_db.py` (optional im Workflow)
- `data/prompt_repository.py` (absoluter Standardpfad)
- `tests/test_gui_mainwindow.py` (UI-Smoketest erweitern)
- `tests/test_ingest_e2e.py` (neu, CLI-E2E)

> Bei Abgabe bitte die **aktuelle Projektstruktur** in `AENDERUNGSPROTOKOLL.md` ergänzen (Tree-Ausgabe).

---

## 1) Kontext
- **Projekt:** MT Prompt Engine
- **Story:** S-002 UI-Integration (Option B)
- **Quelle:** BACKLOG.md / PROJECT_STATUS.md
- **Branch:** `feature/S-002-ui-bulk-ingest`

---

## 2) Aufgabe
Implementiere die UI-Integration:
- `Import → Bulk ingest folder…` startet einen **nicht-blockierenden** Workflow per **QProcess**.
- Alle Aufrufe erfolgen über `tools/run_with_kpi.cmd` (KPI-Logging). 
- Workflow (empfohlen, verlustfrei):
  1. `tools/llm_extract_prompts.py --mode llm-refine` (oder `auto` mit `--min-prompts=50`), Ziel: `<folder>/llm_extract_prompts.jsonl`
  2. `tools/ingest_jsonl_to_db.py --path <jsonl>` mit `--category`, `--default-tags`, `--min-content-len`
  3. Optional: `tools/dedupe_db.py --mode content --apply`
- Fortschritt/Logs im UI anzeigen (Streaming aus Stdout/Err).
- Nach Abschluss: Ergebnis-Panel mit Summary (JSON-parsed) und DB-Infos.

---

## 3) Laufumgebung
- **Python** 3.13, **PowerShell** 7.x empfohlen
- **pytest** vorhanden
- **OpenAI-Key** optional (nur für LLM)

Beispiel (PowerShell):
```powershell
& .\tools\run_with_kpi.cmd python -m tools.llm_extract_prompts `
  --path "C:\path\to\html_or_folder" `
  --mode llm-refine `
  --model "gpt-4o-mini" `
  --verbose
```

---

## 4) Importpfade (Top-Level)
- `from data.prompt_repository import PromptRepository`
- `from ingestion.article_ingestor import map_extraction_to_prompts`
- `from tools import ...` (nur über `-m tools.<script>` aufrufen)

---

## 5) Implementierungs-Vertrag (UI)
### 5.1 Signals/Slots (Beispiel)
- `self.action_bulk_ingest.triggered.connect(self.on_bulk_ingest_triggered)`
- `def on_bulk_ingest_triggered(self):`  
  - Ordnerdialog öffnen → Pfad merken
  - QProcess starten mit `tools/run_with_kpi.cmd` + Parameter (siehe 2)
  - Fortschritt anzeigen: QProgressDialog oder eigenes Dock-Panel
  - Cancel: `self._ingest_proc.terminate()` → UI-Status zurücksetzen

### 5.2 Ergebnis-Parsing
- JSON-Summary aus den Tools via Stdout (letzte JSON-Zeile)
- Felder: `files`, `prompts`, `saved_prompts`, `skipped_short`, `errors`, `jsonl`, `db_path`

### 5.3 Fehlerbehandlung
- Tool-Exit-Code ≠ 0 → UI zeigt Fehler-Toast + Details
- Kein Crash, UI bleibt bedienbar

---

## 6) Akzeptanzkriterien (DoD)
- Start/Cancel stabil, kein UI-Freeze
- KPI-Wrapper umschließt alle Aufrufe
- Ergebnis-Summary sichtbar; DB-Pfad wird angezeigt
- Tests grün (inkl. UI-Smoketest + E2E-CLI)

---

## 7) Tests
- **UI-Smoketest**: Instanziieren, Menüpunkt anklicken (simuliert), unmittelbares Schließen
- **E2E-CLI**: Fixture-HTML → `llm_extract_prompts` (dry-run/refine) → `ingest_jsonl_to_db` → `print_db_info` (Count prüfen)

---

## 8) Output (Pflicht)
```
S-005_deliverable.zip
├─ changes/ (alle betroffenen Python-Dateien als Vollversion)
├─ tests/ (neue/erweiterte Tests)
├─ COMMIT_MESSAGE.txt
├─ AENDERUNGSPROTOKOLL.md (inkl. Projektstruktur)
└─ aktualisierte MDs: BACKLOG.md, PROJECT_STATUS.md, CHANGELOG.md
```

---

## 9) Commit-Message (Vorschlag)
```
feat: S-005 UI-Integration Bulk Ingest mit KPI & Progress

- QAction „Bulk ingest folder…“ an Worker (QProcess) angebunden
- KPI-Wrapper integriert; Logs/JSON-Summary im UI sichtbar
- Ergebnis-Panel mit Count/Skips/Errors/DB-Pfad
- Mini-E2E & UI-Smoketest ergänzt
```

---

## 10) Qualitätskriterien
- Dateien in korrekten Ordnern, Importe lauffähig
- Golden Path: HTML → JSONL → DB → Dedupe → Anzeige (ohne manuelle Schritte)
- KPI-Metriken grün (Grenzwerte siehe KPI-README)
- Doku aktualisiert (Backlog/Status/Changelog)
