# Projektstatus – MT Prompt Engine

## Überblick
- Projektname: **MT Prompt Engine**
- Ursprung: Weiterentwicklung des Projekts *Prompt-Database-QT*
- Ziel: Eine erweiterbare Prompt-Datenbank mit Ingest-Funktionen, UI (Qt), Backlog-Verwaltung und automatisierter Projektsteuerung.

## Aktueller Stand
- **Codebasis:** Prompt-Database-QT (Visual Studio Projekt, Python/PySide6)
- **Bestehende Features:**
  - PromptRepository (TinyDB als Backend)
  - Qt-UI mit Tabellenansicht, Detailansicht, Export (CSV, JSON, YAML, MD)
  - Artikel-Ingestor (`article_ingestor.py`) → wandelt Texte in Prompts und speichert in DB
  - Bulk-Ingest (`bulk_ingest_local.py`) für ganze Ordner mit .txt-Dateien
  - Integration Bulk-Ingest in GUI (Import-Menü, QProcess, Fortschrittsdialog)
  - Lokaler HTML-Fetcher (`article_fetcher_local.py`) → extrahiert Artikeltext aus gespeicherten HTML-Seiten
- **Neue Dokumentation:**
  - Handover-Templates für Stories, Bugs, Experimente (`docs/templates/…`)

## Offene Probleme
- **Tag Overloading:** Tags wachsen unkontrolliert durch Artikelimporte, Übersicht leidet.
- **Performance im Chat:** Kontextgröße und viele Dateien machen Chats langsamer (gelöst durch Aufteilung in themenspezifische Chats und Brückendateien).

## Nächste geplante Arbeiten
1. Tags konsolidieren (Normalisierung, Synonym-Mapping, DB-Update).
2. Backlog mit Stories systematisch aufbauen.
3. Testlauf einer Story-Implementierung mit Handover-Template (Dry-Run).
