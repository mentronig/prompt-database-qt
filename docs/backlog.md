# 📋 Projekt-Backlog – Prompt Database Qt (Status inkl. CRUD/UI-Update)

| ID     | Thema                                   | Beschreibung                                                                 | MoSCoW | Status      | Begründung |
|--------|-----------------------------------------|------------------------------------------------------------------------------|--------|------------|------------|
| **UI-001** | **Modern Business Look & Theme-System** | Light/Dark + Solarized/Nord, Sidebar-Umschalter, Icons, QSS-Basisthema.       | Must   | **Done**    | Umgesetzt, ausgeliefert. |
| **UI-002** | **Look & Feel verbessern (Phase 2)** | Mikro-Animationen, Card-Styles, Feintuning Spacing/Farben, ggf. Icon+Text.    | Should | **Planned** | Weiteres optisches Feintuning. |
| **DB-004** | **Prompt-Beschreibung & Zusatzinfos** | Felder: Beschreibung, Kategorie, Version, Beispielausgabe, Verwandte IDs; Suche & Editor erweitert. | Must | **Done** | Implementiert inkl. Editor & Suche, geliefert. |
| **OPS-003** | **Automatische DB-Migration + Backup** | Backup vor Migration, idempotente Feld-Erweiterung (Zero-Loss).               | Must   | **Done**    | Läuft beim Start, loggt geänderte Einträge. |
| **UI-003** | **CRUD-Dialoge erweitern (Kategorie+Tags-UX)** | Editable Kategorie (Dropdown + freie Eingabe), Tags mit Live-Autocomplete, neue Felder vollständig in Neu/Bearbeiten. | Must | **Done** | Umsetzung abgeschlossen, ausgeliefert. |
| **UI-004** | **Tabelle: Kategorie mit Icon+Text** | Kategorie-Spalte kombiniert Icon + Text; Such-/Sortierfähig; Tags-Spalte erweitert. | Must | **Done** | Verbesserung der Übersicht & Navigierbarkeit. |

## Status-Definitionen
- **Planned** = im Backlog, noch nicht begonnen  
- **In Progress** = in Umsetzung  
- **Done** = umgesetzt, ausgeliefert  
- **Blocked** = extern abhängig / wartet auf Entscheidung
