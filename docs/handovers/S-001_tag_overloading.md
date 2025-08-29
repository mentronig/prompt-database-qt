# Handover: Story Implementierung – S-001 Tag Overloading

📌 Kontext:
- Projekt: MT Prompt Engine
- Quelle: BACKLOG.md (S-001)
- Ziel-Chat: Code-Chat

📝 Story:
**Problem:** Für jeden Artikelimport wächst die Tagliste, Übersicht geht verloren.  
**Lösungsideen:**  
- Normalisierung (lowercase, trim, Sonderzeichen vereinheitlichen)  
- Synonym-Mapping via `tag_aliases.json`  
- Bestehende Datensätze rückwirkend aktualisieren  
- Import-Log mit Meldungen über Tag-Ersetzungen  
- Optional: Tag-Manager-UI  

**Akzeptanzkriterien:**  
- Keine doppelten/varianten Tags mehr in DB  
- Log zeigt Normalisierung + Updates  
- Tagliste bleibt übersichtlich  

🎯 Ziel:
Implementierung der automatischen Tag-Konsolidierung im Import-Prozess (inkl. Update bestehender Datensätze).

🔄 Randbedingungen:
- Integration in `article_ingestor.py` / `bulk_ingest_local.py`
- Anpassung `prompt_repository.py` (Batch-Update von Tags)
- Log-Ausgabe im Ingestor
- Tests ergänzen
- Dokumentation in CHANGELOG.md

📊 Output-Erwartung:
- Code-Diffs oder neue Module
- Tests (pytest oder unittest)
- Commit-Msg:
  "feat: S-001 Tag Overloading (Tag-Normalisierung + Synonyme + DB-Update)"
