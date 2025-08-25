# Python venv Guide (Prompt-Datenbank)

## FAQ – kurz erklärt
**Wann verwende ich venv?**  
- Wenn ein Projekt eigene Abhängigkeiten (Pakete) hat  
- Wenn mehrere Projekte unterschiedliche Pakete benötigen  
- Wenn Reproduzierbarkeit wichtig ist (z. B. für GitHub/Team)

**Wann brauche ich venv nicht?**  
- Bei kleinen Einmal‑Skripten ohne externe Pakete

**Muss ich Pakete jedes Mal neu installieren?**  
- Nein. Pakete werden **einmalig** ins `.venv` installiert und bleiben dort,
  bis du den Ordner löschst. Vor jedem Arbeiten nur **aktivieren**.

**Wie wechsle ich zwischen Projekten?**  
- Jedes Projekt hat sein eigenes `.venv`. Im jeweiligen Projektordner `Activate.ps1` ausführen.

**Wie teile ich das Projekt?**  
- `.venv` **nicht committen**. Stattdessen `requirements.txt` committen. Andere erzeugen ihr eigenes venv.

---

## Einrichtung (einmalig)
```powershell
cd C:\Users\Roland\source\repos\prompt-database-qt
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Nutzung (jedes Mal)
```powershell
cd C:\Users\Roland\source\repos\prompt-database-qt
.\.venv\Scripts\Activate.ps1
python main.py
```

## Optional: Tools (Designer & Co.) im venv starten
```powershell
.\.venv\Scripts\pyside6-designer.exe
```

## Zusammenarbeit (GitHub/Team)
Andere können die gleiche Umgebung so erstellen:
```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Troubleshooting
- **`python --version` zeigt nicht 3.13** → Terminal neu öffnen, venv erneut aktivieren.
- **Pakete fehlen** → `pip install -r requirements.txt` im **aktiven** venv ausführen.
- **Build findet Assets nicht** → `build.ps1` nutzen (fügt Themes/Icons via `--add-data` hinzu).
