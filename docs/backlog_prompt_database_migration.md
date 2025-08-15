# Migration Prompt-Datenbank → PySide6 / Qt

**Ziel:** Streamlit-UI ablösen, Desktop-UX (.exe) bereitstellen, Services & Datenebene wiederverwenden.

## MoSCoW – Migration (höchste Prio = Must)
### Must
- PySide6 Skeleton (MainWindow, Table, Editor, Export, Backup)
- TinyDB-Repository weiterverwenden (mit `id`-Feld)
- Logging & .env-Check (bestehendes Setup)
- Packaging-Anleitung (PyInstaller)
- Such-/Tag-Filter (ProxyModel)

### Should
- Theming-Hooks vorbereiten (Palette API)
- Tests für Services (Export/Backup/Repo – smoke)
- README/Docs aktualisieren

### Could
- Window-Layout-Persistenz
- Keyboard-Shortcuts, Kontextmenü
- Undo/Redo (Soft-Delete)

## Migrationsschritte
1. Core extrahieren (Services/Daten behalten)
2. Qt-Shell implementieren (Liste, Preview, Toolbar)
3. Editor-Dialog (Neu/Bearbeiten)
4. Filter (Text + Tags)
5. Export/Backup via Dialoge
6. Packaging (PyInstaller)
7. Optionale Veredelungen

## Nächste Schritte
- [x] Qt-Skeleton implementiert
- [x] Repo/Services integriert
- [x] Packaging-Guide ergänzt
- [ ] Optional: Theming & Layout-Persistenz
- [ ] Optional: Shortcuts, Kontextmenüs
