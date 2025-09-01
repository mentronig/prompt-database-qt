# Smart Handover – Automatisierte Umsetzung (ZIP-Output, v2)

> **Ziel:** Der Code-Chat setzt die Aufgabe **vollständig und selbständig** um und liefert ein **ZIP-Paket** mit **fertigen, vollständigen Dateien**.  
> **Dein Aufwand:** ZIP entpacken → Tests laufen lassen → commit/push.

---

## 0) Projektstruktur (lebendiges Dokument)

- Füge hier den **aktuellen Projektbaum** ein (aus Repo).  
- Regeln:
  - Verwende **exakt diese Struktur**.  
  - Neue Dateien in passende Ordner (z. B. `ingestion/`, `data/`, `tests/`).  
  - Passe Importe an diese Struktur an.  
  - Am Ende der Umsetzung: **aktualisierte Projektstruktur** in `AENDERUNGSPROTOKOLL.md` ergänzen.

---

## 1) Kontext

- **Projekt:** MT Prompt Engine  
- **Quelle:** `BACKLOG.md` (Story-/Bug-ID), `PROJECT_STATUS.md`  
- **Ziel-Chat:** Code-Chat (Implementer)  
- **Branch:** `feature/<ID>-<kurzname>`

---

## 2) Aufgabe

Setze `<ID – Kurztitel>` **vollständig** um:

- **Neue Dateien vollständig erstellen**  
- **Geänderte Dateien als komplette Version liefern** (keine Diffs)  
- **Dokumentation aktualisieren**: `CHANGELOG.md`, `PROJECT_STATUS.md`  
- **Tests hinzufügen** (pytest, optional UI-Smoketests)  
- **Commit-Message vorbereiten**

---

## 3) Laufumgebung

- **Python:** 3.13  
- **PowerShell:** 7.x empfohlen (5.1 möglich)  
- **pytest:** verwenden, keine Spezialplugins  
- **requirements.txt:** nutzen (keine unnötigen Zusatzlibs)

**Setup (PowerShell):**
```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
```

---

## 4) Importpfade / Top-Level-Pakete

- Top-Level: `config`, `data`, `docs`, `ingestion`, `models`, `scripts`, `services`, `tests`, `themes`, `ui`, `utils`  
- Beispielimporte:
  - `from data.prompt_repository import PromptRepository`
  - `from ingestion.tag_normalizer import normalize_tags`

---

## 5) Konfig-Pfade (Ground Truth)

- Alias/Mapping: `config/tag_aliases.json`  
- Format: `{ "AI": "artificial-intelligence", "ml": "machine-learning" }`  
- Falls Datei fehlt → leerer Alias-Map, keine Exception.

---

## 6) Implementierungs-Vertrag (Signaturen & Rückgaben)

*(Je nach Story anpassen – hier exemplarisch für Tag-Normalizer)*

```python
def normalize_tag(tag: str, alias_map: dict[str, str] | None = None) -> str: ...
def normalize_tags(tags: list[str] | None, alias_map: dict[str, str] | None = None) -> list[str]: ...
def load_alias_map(path: str = "config/tag_aliases.json") -> dict[str, str]: ...
def normalize_item_tags(item: dict, alias_map: dict[str, str] | None = None) -> dict: ...
```

---

## 7) Feldprioritäten (falls Ingest)

- **title:** Item-Wert bevorzugt; wenn leer → Alternative (Pattern/Überschrift).  
- **tags:** übernehmen → normalisieren → leere entfernen.  
- **category:** falls leer → `""`.  
- **description/sample_output:** optional; leere nicht erzwingen.

---

## 8) Golden Samples (Soll-Output)

*(Klein halten, 2–3 Beispiele reichen; hier für Tag-Normalisierung)*

- **GS-1:** Input `["AI","Gen AI"]` → Output `["artificial-intelligence","generative-ai"]`  
- **GS-2:** Input `["AI","ai","Ai"]` → Output `["artificial-intelligence"]`  
- **GS-3:** Input `None` → Output `[]`

---

## 9) Tests

- Pflicht: Golden-Sample-Tests + Mini-Integrationstests für relevante Klassen (z. B. `PromptRepository`)  
- Optional: **UI-Smoketest** (PySide6):  
  - `QApplication` + `MainWindow` starten & sofort schließen → prüft Imports/Wiring  
  - Kein Rendering, kein Screenshot → effizient

---

## 10) Output (Pflicht)

```
<id>_deliverable.zip
├─ changes/ (alle betroffenen Dateien als Vollversion)
├─ COMMIT_MESSAGE.txt
└─ AENDERUNGSPROTOKOLL.md  (inkl. Projektstruktur nach Umsetzung)
```

---

## 11) Commit-Message (Format)

```
feat: <ID> <Kurztitel> – <kurzer Nutzen>

- Punkt 1
- Punkt 2
```

---

## 12) Qualitätskriterien

- [ ] Dateien im richtigen Ordner, Importe lauffähig  
- [ ] Golden Samples & Mini-Tests grün  
- [ ] (Optional) UI-Smoketest läuft fehlerfrei  
- [ ] `CHANGELOG.md` & `PROJECT_STATUS.md` aktualisiert  
- [ ] `AENDERUNGSPROTOKOLL.md` enthält Projektstruktur nach Umsetzung  
- [ ] Keine manuellen Einfügungen nötig

---

## 13) Beispiel-Aufruf

> „Hier ist die Story **<ID> <Kurztitel>** aus `BACKLOG.md`.  
> Bitte setze sie **vollständig** um und liefere ein **ZIP** gemäß `docs/templates/handover_smart.md`.  
> **Keine Diffs**, alle betroffenen `.py` als **finale Vollversion**, inkl. **Tests**, aktualisierten Markdown-Dateien, `AENDERUNGSPROTOKOLL.md` (inkl. Projektstruktur) + `COMMIT_MESSAGE.txt`.  
> Ich möchte danach nur **entpacken, testen, committen**.“
