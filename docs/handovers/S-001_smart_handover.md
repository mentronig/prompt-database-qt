# Smart Handover – S-001 Tag Overloading (Tag-Normalisierung + Synonyme + DB-Update)

> **Ziel:** Der Code-Chat setzt die Story S-001 vollständig um und liefert ein **ZIP-Paket** mit fertigen, vollständigen Dateien.  
> **Dein Aufwand:** ZIP entpacken → Tests laufen lassen → commit/push.

---

## 1) Kontext

- **Projekt:** MT Prompt Engine
- **Quelle:** `BACKLOG.md` (Story S-001)
- **Ziel-Chat:** Code-Chat
- **Branch:** `feature/S-001-tag-overloading`

---

## 2) Story (aus BACKLOG.md)

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

**Status:** In Arbeit  
**Owner:** Mentronig

---

## 3) Aufgabe

Implementiere die Story S-001 vollständig:

- Neue Module für Tag-Normalisierung + Alias-Mapping erstellen  
- Repository (`prompt_repository.py`) anpassen: Normalisierung bei `add()`/`update()`, plus `bulk_update_from_alias_map()`  
- Ingestor (`article_ingestor.py` / `bulk_ingest_local.py`) erweitern, sodass beim Speichern normalisiert wird  
- Tests ergänzen (pytest)  
- Dokumentation anpassen (`CHANGELOG.md`, `PROJECT_STATUS.md`)  
- Commit-Message vorbereiten

---

## 4) Output (Pflicht)

Der Code-Chat liefert ein **ZIP-Paket** mit dieser Struktur:

```
S-001_deliverable.zip
├─ changes/
│  ├─ ingestion/tag_normalizer.py
│  ├─ ingestion/article_ingestor.py
│  ├─ ingestion/bulk_ingest_local.py
│  ├─ data/prompt_repository.py
│  ├─ config/tag_aliases.json
│  ├─ tests/test_tag_normalizer.py
│  ├─ PROJECT_STATUS.md
│  └─ CHANGELOG.md
├─ COMMIT_MESSAGE.txt
└─ AENDERUNGSPROTOKOLL.md
```

---

## 5) Änderungsprotokoll (Pflichtinhalt)

`AENDERUNGSPROTOKOLL.md` enthält:

- Überblick: Was wurde implementiert  
- Dateiliste: Neu / Geändert + Kurzbeschreibung  
- Tests: Welche Fälle, wie ausführen (`pytest -q`)  
- Manuelle Schritte: „ZIP entpacken, Tests ausführen, commit/push“

---

## 6) Commit-Message (Format)

`COMMIT_MESSAGE.txt`:

```
feat: S-001 Tag Overloading – Normalisierung & Alias-Mapping

- Normalisiert Tags (lowercase, trim, Sonderzeichen vereinheitlicht)
- Alias-Mapping via config/tag_aliases.json
- Repository: Normalisierung bei add()/update(), DB-Update mit bulk_update_from_alias_map()
- Tests ergänzt
```

---

## 7) Qualitätskriterien

- [ ] Alle betroffenen Dateien vollständig im ZIP  
- [ ] Tests enthalten und lauffähig  
- [ ] CHANGELOG.md unter [Unreleased] ergänzt  
- [ ] PROJECT_STATUS.md aktualisiert  
- [ ] Keine manuellen Code-Einfügungen nötig  

---

## 8) Anweisung für den Code-Chat

> „Hier ist die Story **S-001 Tag Overloading** aus `BACKLOG.md`.  
> Bitte setze sie **vollständig** um und liefere ein **ZIP** gemäß `docs/handovers/S-001_smart_handover.md`.  
> **Keine Diffs**, alle betroffenen `.py`-Dateien als **finale Vollversion**, inkl. **Tests**, aktualisierten Markdown-Dateien, `AENDERUNGSPROTOKOLL.md` + `COMMIT_MESSAGE.txt`.  
> Ich möchte danach nur **entpacken, testen, committen**.“
