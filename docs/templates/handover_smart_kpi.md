# Smart Handover – Automatisierte Umsetzung (ZIP-Output, v3 mit KPI-Policy)

> **Ziel:** Der Code-Chat setzt die Aufgabe **vollständig und selbständig** um und liefert ein **ZIP-Paket** mit **fertigen, vollständigen Dateien**.  
> **Dein Aufwand:** ZIP entpacken → Tests laufen lassen → commit/push.  
> **NEU (Pflicht):** Während der Umsetzung werden **KPI-Kennzahlen** erfasst (Ampel) und **Quality-Gates** eingehalten. **Jeder** Python-Aufruf außerhalb von Pytest läuft über `tools\run_with_kpi.cmd`.

---

## 0) Projektstruktur (lebendiges Dokument)

- Füge hier den **aktuellen Projektbaum** ein (aus Repo).  
- Regeln:
  - Verwende **exakt diese Struktur**.  
  - Neue Dateien in passende Ordner (z. B. `ingestion/`, `data/`, `tests/`).  
  - Importe an diese Struktur anpassen.  
  - Am Ende der Umsetzung: **aktualisierte Projektstruktur** in `AENDERUNGSPROTOKOLL.md` ergänzen.

---

## 1) Kontext

- **Projekt:** MT Prompt Engine  
- **Quelle:** `BACKLOG.md` (Story-/Bug-ID), `PROJECT_STATUS.md`  
- **Ziel-Chat:** Code-Chat (Implementer)  
- **Branch:** `feature/<ID>-<kurzname>`

---

## 2) Aufgabe

Setze **<ID – Kurztitel>** **vollständig** um:

- **Neue Dateien vollständig erstellen**  
- **Geänderte Dateien als komplette Version liefern** (keine Diffs)  
- **Dokumentation aktualisieren**: `CHANGELOG.md`, `PROJECT_STATUS.md`  
- **Tests hinzufügen** (pytest, optional UI-Smoketests)  
- **Commit-Message vorbereiten`**

---

## 3) Laufumgebung

- **Python:** 3.13  
- **PowerShell:** 7.x empfohlen (5.1 möglich)  
- **pytest:** verwenden (JUnit/HTML-Report)  
- **requirements.txt:** nutzen (keine unnötigen Zusatzlibs)

**Setup (PowerShell):**
```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
```

---

## 3a) KPI-Policy (Pflicht)

**Ziel der KPIs:**  
- **Pytest-Erfolgsrate** (Fenster, standard 20 Läufe)  
- **Errors/Stunde seit letztem Commit** (inkl. externer Tool-Fehler)  
- **Runs-to-Green** (Testläufe bis zum ersten „grün“)

**Werkzeuge/Artefakte:**  
- `tools/kpi_logger.py` (schreibt `reports/kpi_history.csv`)  
- `tools/kpi_report.py` (Ampel, schreibt `reports/kpi_summary.md`)  
- `tools/run_tests.cmd` (führt `pytest` → KPI-Logger → KPI-Report aus)  
- `tools/kpi_exec.py` & `tools/run_with_kpi.cmd` (zählen **externe** Python-/Tool-Aufrufe als **extra errors**)  
- Reports: `reports/last/junit.xml`, `reports/last/report.html`, `reports/kpi_history.csv`, `reports/kpi_summary.md`, `reports/tool_history.csv`

**Verbindliche Anwendung während der Umsetzung:**
1) **Baseline-Run** zu Chat-Beginn:
   ```bat
   toolsun_tests.cmd
   ```
2) **Nach jedem relevanten Implementierungsschritt**:
   ```bat
   toolsun_tests.cmd
   ```
3) **JEDER Python-Aufruf außerhalb von Pytest** (z. B. CLIs, Hilfsskripte) wird **ausnahmslos** über den Wrapper gestartet:
   ```bat
   toolsun_with_kpi.cmd python -m <modul> [args...]
   ```
   Dadurch werden **Exit≠0** als **extra error** in den KPIs erfasst (und in `tool_history.csv` protokolliert).

**KPI-Quality-Gates (Ampel, Pflicht für Abgabe):**
- **Pytest-Erfolgsrate** (letzte 20 Läufe):  
  🟢 **≥ 98 %** · 🟡 95–97 % · 🔴 < 95 %  
- **Errors/Stunde seit Commit** (mit extra errors):  
  🟢 **≤ 1.0** · 🟡 > 1.0–3.0 · 🔴 > 3.0  
- **Runs-to-Green**:  
  🟢 **≤ 2** · 🟡 3–4 · 🔴 ≥ 5

**Abgabekriterium (muss erfüllt sein):**
- Letzter Testlauf **grün**  
- Erfolgsrate **≥ 98 %** *(oder: letzte 5 Läufe = 100 %)*  
- Runs-to-Green **≤ 2**  
- Errors/Stunde **≤ 1.0**  
- `reports/kpi_summary.md` zeigt **keine rote Ampel**

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

*(Je nach Story anpassen – Beispiel Tag-Normalizer)*

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

- **GS-1:** Input `["AI","Gen AI"]` → Output `["artificial-intelligence","generative-ai"]`  
- **GS-2:** Input `["AI","ai","Ai"]` → Output `["artificial-intelligence"]`  
- **GS-3:** Input `None` → Output `[]`

---

## 9) Tests

- Pflicht: Golden-Sample-Tests + Mini-Integrationstests (z. B. `PromptRepository`)  
- **CLI-Integrationstest** (empfohlen): CLI via `subprocess` aus Pytest starten, Exit-Code/Stdout prüfen.  
- Optional: **UI-Smoketest** (PySide6):  
  - `QApplication` + `MainWindow` starten & sofort schließen → prüft Imports/Wiring

---

## 9a) KPI-Auswertung (Pflicht vor Abgabe)

- Ampel erstellen/prüfen:
  ```bat
  python tools\kpi_report.py --window 20
  ```
- `reports/kpi_summary.md` und `reports/kpi_history.csv` als Artefakte ins ZIP aufnehmen.  
- Bei **gelb/rot** → Ursachen beheben, erneut laufen lassen (bis Ampel **grün**).

---

## 10) Output (Pflicht)

```
<id>_deliverable.zip
├─ changes/ (alle betroffenen Dateien als Vollversion)
├─ reports/
│  ├─ last/junit.xml
│  ├─ last/report.html
│  ├─ kpi_history.csv
│  ├─ kpi_summary.md
│  └─ tool_history.csv
├─ COMMIT_MESSAGE.txt
└─ AENDERUNGSPROTOKOLL.md  (inkl. Projektstruktur nach Umsetzung)
```

---

## 11) Commit-Message (Format)

```
feat: <ID> <Kurztitel> – <kurzer Nutzen>

- Punkt 1
- Punkt 2

KPI: pass-rate ≥98 %, runs-to-green ≤2, errors/hour ≤1.0 (siehe reports/kpi_summary.md)
```

---

## 12) Qualitätskriterien (Pflicht)

- [ ] Dateien im richtigen Ordner, Importe lauffähig  
- [ ] Golden Samples & Tests **grün**  
- [ ] (Optional) UI-Smoketest läuft fehlerfrei  
- [ ] `CHANGELOG.md` & `PROJECT_STATUS.md` aktualisiert  
- [ ] `AENDERUNGSPROTOKOLL.md` enthält Projektstruktur nach Umsetzung  
- [ ] **KPI-Gates erfüllt** (siehe 3a)  
- [ ] Keine manuellen Einfügungen nötig

---

## 13) Beispiel-Aufrufe

**Tests + KPIs (komplett):**
```bat
toolsun_tests.cmd
python tools\kpi_report.py --window 20
```

**Externe Python-Skripte immer über Wrapper:**
```bat
toolsun_with_kpi.cmd python -m ingestion.article_ingestor --file "C:oller\pfad.txt" --source-title "Titel" --category enhancement --tags "article,pattern"
```

**Vollständiger Handover-Prompt an den Code-Chat:**
> „Hier ist die Story **<ID <Kurztitel>>** aus `BACKLOG.md`.  
> Bitte setze sie **vollständig** um und liefere ein **ZIP** gemäß `docs/templates/handover_smart.md`.  
> **Keine Diffs**, alle betroffenen `.py` als **finale Vollversion**, inkl. **Tests**, aktualisierten Markdown-Dateien, `AENDERUNGSPROTOKOLL.md` (inkl. Projektstruktur) + `COMMIT_MESSAGE.txt`.  
> **Wichtig:** Halte die **KPI-Policy** ein (Abschnitt 3a). **Jeden** externen Python-Aufruf über `toolsun_with_kpi.cmd`.  
> Ich möchte danach nur **entpacken, testen, committen**.“
