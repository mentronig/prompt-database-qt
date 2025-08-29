# Backlog – MT Prompt Engine

## Struktur
- **Stories**: Funktionale Erweiterungen
- **Bugs**: Fehler und Regressionen
- **Experimente**: Spikes / Machbarkeitsstudien

---

## Stories

### [S-001] Tag Overloading – Konsolidierung
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

- **Status:** In Arbeit  
**Owner:** Mentronig 
**Verweis:** docs/handovers/S-001_tag_overloading.md
---

## Bugs
*(aktuell keine offenen Bugs dokumentiert)*

---

## Experimente
- [E-001] Testlauf: Alternative Extraktoren (trafilatura vs readability) → Evaluieren, welcher für HTML-Fetcher stabiler ist.
