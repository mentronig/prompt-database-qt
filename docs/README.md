# Prompt-Datenbank (Qt) – Modern Business Look (v2)

- CRUD-Dialoge erweitert: Beschreibung, Kategorie (Dropdown + freie Eingabe), Tags mit Live-Autocomplete, Version, Beispielausgabe, Verwandte IDs
- Haupttabelle: Kategorie mit Icon+Text in einer Spalte, Tags-Spalte
- Suche über Titel, Beschreibung, Content, Kategorie, Tags
- Automatische DB-Migration mit Backup
- Themes (Light/Dark/Solarized/Nord), Sidebar-Theme-Umschalter
- Build-Script packt Themes & Icons inklusive

## Start
pip install -r requirements.txt
cp .env.template .env  # optional
python main.py

## Build (.exe)
powershell -ExecutionPolicy Bypass -File .\build.ps1
