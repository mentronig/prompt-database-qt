# 🧭 Workflow Handout – MT Prompt Engine

Dieses Handout beschreibt die **Prozessschritte** für die tägliche Arbeit im Projekt. Es dient als Anleitung für die effiziente Nutzung von Backlog, Code und UI-Chats sowie den Brückendateien.

---

## 1️⃣ Arbeitsweise / Vorgehen
- **Chats aufteilen:**  
  - *Backlog-Chat*: User Stories, Bugs, Experimente → lebendes Gedächtnis.  
  - *Code-Chat*: Implementierung & Tests → zieht Stories aus Backlog.  
  - *UI-Chat*: Themen rund um Oberfläche, Design, UX.  
- **Brückendateien als Gedächtnis**:
  - `PROJECT_STATUS.md` → aktueller Stand  
  - `BACKLOG.md` → Stories, Bugs, Experimente  
  - `CHANGELOG.md` → wichtigste Ergebnisse  
- **Handover Templates** (`handover_story.md`, `handover_bug.md`, `handover_experiment.md`) → standardisierte Übergabe zwischen Chats.

---

## 2️⃣ Dateibrücke pflegen
Nach jedem Task oder Sprint:  
1. **Projektstatus aktualisieren** (`PROJECT_STATUS.md`):  
   - Was ist neu?  
   - Welche Probleme offen?  
2. **Backlog pflegen** (`BACKLOG.md`):  
   - Neue Stories/Bugs hinzufügen  
   - Erledigte Stories abhaken  
3. **Changelog schreiben** (`CHANGELOG.md`):  
   - Kurzer Eintrag pro Änderung mit Datum + Version/Commit

👉 Tools:  
- `scripts/update_docs.ps1` → staged & pusht die drei Dateien.  
- `scripts/update_docs_pr.ps1` → legt einen Branch + PR auf GitHub an.

---

## 3️⃣ Beispiel Testlauf (Story)
1. Wähle eine Story aus dem Backlog (z. B. **S-001 Tag Overloading**).  
2. Erstelle ein Handover mit `handover_story.md`.  
3. Gib dieses Handover im **Code-Chat** → Umsetzung durch GPT.  
4. Ergebnis testen → bei Erfolg:  
   - `PROJECT_STATUS.md` anpassen (Stand aktualisieren).  
   - `CHANGELOG.md` ergänzen („feat: S-001 Tag Overloading umgesetzt“).  
5. Push mit `update_docs.ps1`.

---

## 4️⃣ Review-Prozess
- **Code Review:** über GitHub Pull Request (wenn `update_docs_pr.ps1` genutzt wird).  
- **Status Review:** im Backlog-Chat kurz abstimmen („Story S-001 abgeschlossen, bitte review“).  
- **Dokumentation:** Änderungen immer in die Brückendateien schreiben und committen.  
- **Release-Rhythmus:** alle abgeschlossenen Features werden im CHANGELOG gesammelt → GitHub Release Notes.

---

## 5️⃣ Quick-Check für Beginner
- **Starte neuen Chat:**  
  „Nutze den Stand aus `PROJECT_STATUS.md` und den Dateien der Projektablage. Starte mit Task X.“  
- **Nach Arbeit:**  
  - Dateien aktualisieren  
  - `scripts/update_docs.ps1` laufen lassen  
  - Commit/Push auf GitHub  
- **Immer dran denken:**  
  Nur aktuelle Stories in den Code-Chat geben → alles andere bleibt im Backlog-Chat.

---

✅ Damit ist der Workflow kompakt, klar und anfängerfreundlich beschrieben.
