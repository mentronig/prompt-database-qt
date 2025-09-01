# Smart Handover – S-001 Tag Overloading (Tag-Normalisierung + Synonyme + DB-Update, v4)

> **Ziel:** Der Code-Chat setzt die Story S-001 vollständig um und liefert ein **ZIP-Paket** mit fertigen, vollständigen Dateien.  
> **Dein Aufwand:** ZIP entpacken → Tests laufen lassen → commit/push.  
> **Neu in v4:** Konsolidierung der Ursprungsversion (Story, Aufgabe, Kontext) und v3 (Technik, Laufumgebung, Tests).

---
## 0) Projektstruktur (lebendiges Dokument)
*(Aktueller Projektbaum hier einfügen. Am Ende der Umsetzung muss der Code-Chat die aktualisierte Struktur in `AENDERUNGSPROTOKOLL.md` ergänzen.)*

### Regeln
- Verwende **exakt diese Struktur** für die Umsetzung.  
- Lege neue Dateien in passende Ordner (z. B. `tag_normalizer.py` → `data/`, Tests → `tests/`).  
- Passe Importe an, sodass sie in dieser Struktur funktionieren.  
- **Am Ende der Umsetzung**: Projektstruktur nach Umsetzung dokumentieren.

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
## 4) Laufumgebung

**Interpreter & Tools**
- **Python:** 3.13 (CPython)
- **PowerShell:** 7.x empfohlen (Windows PowerShell 5.1 möglich)
- **pytest:** nutzen, keine speziellen Plugins erforderlich
- **GitHub CLI (optional):** `gh` für PR-Workflow

**Virtuelle Umgebung (PowerShell)**
```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Tests ausführen**
```powershell
pytest -q
```

---
## 5) Importpfade / Top-Level-Pakete

- Top-Level: `config`, `data`, `docs`, `ingestion`, `models`, `scripts`, `services`, `tests`, `themes`, `ui`, `utils`
- Beispielimporte:
  - `from data.prompt_repository import PromptRepository`
  - `from ingestion.tag_normalizer import normalize_tags, load_alias_map`
- **Keine neuen Top-Level-Pakete** anlegen.

---
## 6) Konfig-Pfade (Ground Truth)

- **Alias/Mapping:** `config/tag_aliases.json`
- Format: `{ "AI": "artificial-intelligence", "ml": "machine-learning" }`
- Wenn Datei fehlt → leerer Alias-Map, keine Exception.

---
## 7) Implementierungs-Vertrag (Signaturen & Rückgaben)

### ingestion/tag_normalizer.py
```python
def normalize_tag(tag: str, alias_map: dict[str, str] | None = None) -> str: ...
def normalize_tags(tags: list[str] | tuple[str, ...] | set[str] | None,
                   alias_map: dict[str, str] | None = None) -> list[str]: ...
def load_alias_map(path: str = "config/tag_aliases.json") -> dict[str, str]: ...
def normalize_item_tags(item: dict, alias_map: dict[str, str] | None = None) -> dict: ...
```

### data/prompt_repository.py (relevant)
```python
class PromptRepository:
    def add(self, item: dict) -> int: ...
    def update(self, doc_id: int, data: dict) -> None: ...
    def bulk_update_from_alias_map(self) -> dict[str, int]: ...
```

---
## 8) Feldprioritäten (Ingest-Mapping)

- **title**: Item-Wert bevorzugt; falls leer → Alternative (Pattern/Überschrift). Keine Dummy-Werte.  
- **tags**: übernehmen → normalisieren → leere entfernen.  
- **category**: falls leer → `""`.  
- **description/sample_output**: optional; wenn leer → nicht erzwingen.

---
## 9) „Golden Samples“ (Soll-Verhalten)

**GS-1: einfache Normalisierung**
- Input: `["  AI  ", "Gen AI", "NLP"]`
- Alias-Map: `{"AI": "artificial-intelligence", "Gen AI": "generative-ai"}`
- Output: `["artificial-intelligence", "generative-ai", "nlp"]`

**GS-2: Dedupe & Reihenfolge**
- Input: `["AI", "ai", "Ai", "Artificial Intelligence"]`
- Alias-Map: `{"ai": "artificial-intelligence"}`
- Output: `["artificial-intelligence"]`

**GS-3: Robust bei None/Leer**
- Input: `None` oder `[]`
- Output: `[]`

---
## 10) Tests/Erwartungen

**Pflicht (leichtgewichtig):**
- `tests/test_tag_normalizer.py`: deckt GS-1..3 ab, Test für `load_alias_map()` (Datei vorhanden/nicht).  
- Mini-Integrationstest für Repository:  
  - `add()` normalisiert unsaubere Tags  
  - `bulk_update_from_alias_map()` ändert bestehende Datensätze wie erwartet

**Optional (effizient):**
- UI-Smoketest (PySide6):
  - Startet `QApplication` + `MainWindow`
  - Prüft, dass Menü/Action „Tags konsolidieren“ vorhanden ist (falls integriert)
  - Schließt sofort → kein Rendering

---
## 11) Output (Pflicht)

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
## 12) Commit-Message (Format)

```
feat: S-001 Tag Overloading – Normalisierung & Alias-Mapping

- Normalisiert Tags (lowercase, trim, whitespace→dash)
- Alias-Mapping via config/tag_aliases.json
- Repository: Hooks für add()/update(), rückwirkendes DB-Update
- Tests (Golden Samples + Mini-Integration, optional UI-Smoketest)
```

---
## 13) Qualitätskriterien

- [ ] Dateien im richtigen Ordner, Importe lauffähig  
- [ ] Golden Samples grün  
- [ ] Mini-Integrationstest grün  
- [ ] (Optional) UI-Smoketest läuft fehlerfrei  
- [ ] `CHANGELOG.md` & `PROJECT_STATUS.md` aktualisiert  
- [ ] `AENDERUNGSPROTOKOLL.md` enthält Projektstruktur nach Umsetzung  
- [ ] Keine manuellen Code-Einfügungen nötig

---
## 14) Anweisung für den Code-Chat

> „Hier ist die Story **S-001 Tag Overloading** aus `BACKLOG.md`.  
> Bitte setze sie **vollständig** um und liefere ein **ZIP** gemäß `docs/handovers/S-001_smart_handover_v4.md`.  
> **Keine Diffs**, alle betroffenen `.py`-Dateien als Vollversion, inkl. Tests, aktualisierten Markdown-Dateien, `AENDERUNGSPROTOKOLL.md` (inkl. Projektstruktur nach Umsetzung) + `COMMIT_MESSAGE.txt`.  
> Danach soll nur nötig sein: **entpacken, testen, committen**.“
