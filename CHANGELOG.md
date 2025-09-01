# Changelog – MT Prompt Engine

## [Unreleased]
- **LLM-Extraktion erweitert:** `tools/llm_extract_prompts.py` mit Modi `auto`, `heuristic-only`, `llm-fallback`, **`llm-refine`** (1:1, keine Verluste). Robuste Pfadprüfung, JSON-Parsing, Batch-Refine.
- **Import-Tooling gefestigt:** `tools/ingest_jsonl_to_db.py` mit Mapping/Tagging/Min-Len und KPI-Wrapper-Integration.
- **Qualitätswerkzeuge:** KPI-Wrapper, JSONL-Content-Längen-Check (`tools/jsonl_content_len.ps1`), Dedupe-Tool verbessert.
- **Vorbereitung Option B (UI):** Handover erstellt: `docs/handovers/S-002_ui_integration_bulk_ingest.md`. GUI-Action vorhanden; Anbindung an KPI-Workflow geplant.
- Dokumentation aktualisiert: `BACKLOG.md`, `PROJECT_STATUS.md`.
-
## [0.1.0] – Initialer Stand (Prompt-Database-QT)
- PromptRepository mit TinyDB
- Grundlegende Qt-UI (Tabellenansicht, Filter, Export CSV/JSON/YAML/MD)
- Artikel-Ingestor für Texte


