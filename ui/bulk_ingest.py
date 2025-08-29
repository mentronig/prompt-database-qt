# gui/bulk_ingest.py
# PySide6/PyQt5-kompatibler Bulk-Ingest (QProcess) + Menüeintrag "Import → Bulk ingest folder…"

from __future__ import annotations
import json, os, sys
from pathlib import Path

# ---- Qt-Shim: PySide6 bevorzugt, PyQt5 fallback ----
try:
    from PySide6.QtCore import Qt, QProcess
    from PySide6.QtGui import QAction, QKeySequence
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
        QTextEdit, QPushButton, QFileDialog, QMessageBox
    )
    PYSIDE = True
except Exception:
    from PyQt5.QtCore import Qt, QProcess
    from PyQt5.QtGui import QAction, QKeySequence
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
        QTextEdit, QPushButton, QFileDialog, QMessageBox
    )
    PYSIDE = False


class BulkIngestDialog(QDialog):
    """
    Startet `python -m ingestion.bulk_ingest_local` über QProcess.
    Liest zeilenweise JSON-Progress von stdout:
      {"progress": i, "total": n, "file": "...", "ok": true}
      {"summary": {...}}
    """
    def __init__(self, parent=None, default_dir: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("Bulk ingest – Ordner verarbeiten")
        self.resize(900, 520)

        self.lbl = QLabel("Ordner nicht gewählt.")
        self.bar = QProgressBar()
        self.bar.setRange(0, 1)
        self.bar.setValue(0)

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        self.btn_choose = QPushButton("Ordner wählen…")
        self.btn_start  = QPushButton("Start")
        self.btn_abort  = QPushButton("Abbrechen")
        self.btn_start.setEnabled(False)
        self.btn_abort.setEnabled(False)

        top = QHBoxLayout()
        top.addWidget(self.lbl)
        top.addStretch(1)
        top.addWidget(self.btn_choose)
        top.addWidget(self.btn_start)
        top.addWidget(self.btn_abort)

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.bar)
        lay.addWidget(self.log)

        self.proc: QProcess | None = None
        self.folder = default_dir or str(Path.cwd())

        self.btn_choose.clicked.connect(self.choose_folder)
        self.btn_start.clicked.connect(self.start_run)
        self.btn_abort.clicked.connect(self.abort_run)

    # ---------------- actions ----------------
    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Ordner mit .txt-Dateien wählen", self.folder)
        if not folder:
            return
        self.folder = folder
        self.lbl.setText(f"Ordner: {self.folder}")
        self.btn_start.setEnabled(True)
        self.append_log(f">> gewählt: {self.folder}\n")

    def start_run(self):
        if not self.folder:
            QMessageBox.warning(self, "Hinweis", "Bitte Ordner wählen.")
            return
        if self.proc:
            QMessageBox.information(self, "Läuft", "Ein Prozess läuft bereits.")
            return

        self.append_log(f">> starte Ingest in: {self.folder}\n")
        self.bar.setRange(0, 0)
        self.btn_start.setEnabled(False)
        self.btn_abort.setEnabled(True)

        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.SeparateChannels)

        py = sys.executable  # venv-sicher
        args = [
            "-m", "ingestion.bulk_ingest_local",
            "--dir", self.folder,
            "--emit-jsonl", os.path.join(self.folder, "ingest_log.jsonl"),
            # hier kannst du Defaults ändern/ergänzen:
            # "--category", "local",
            # "--tags", "article,pattern,local",
            # "--dry-run",
        ]
        self.proc.readyReadStandardOutput.connect(self.on_stdout)
        self.proc.readyReadStandardError.connect(self.on_stderr)
        self.proc.finished.connect(self.on_finished)

        self.proc.setWorkingDirectory(str(Path.cwd()))
        self.proc.start(py, args)
        if not self.proc.waitForStarted(3000):
            QMessageBox.critical(self, "Fehler", "Konnte Python-Prozess nicht starten.")
            self.proc = None
            self.btn_start.setEnabled(True)
            self.btn_abort.setEnabled(False)
            return

    def abort_run(self):
        if self.proc:
            self.append_log(">> Abbruch angefordert…\n")
            self.proc.kill()

    # ------------- QProcess handlers -------------
    def on_stdout(self):
        if not self.proc:
            return
        while self.proc.canReadLine():
            raw = bytes(self.proc.readLine()).decode("utf-8", errors="replace").strip()
            if not raw:
                continue
            self._parse_line(raw)

    def on_stderr(self):
        if not self.proc:
            return
        data = self.proc.readAllStandardError().data().decode("utf-8", errors="replace")
        if data:
            self.append_log(data)

    def on_finished(self, code: int, status):
        self.btn_abort.setEnabled(False)
        self.btn_start.setEnabled(True)
        self.proc = None
        if code == 0:
            self.append_log("\n[OK] Ingest beendet.\n")
        else:
            self.append_log(f"\n[ENDE] Code={code}\n")
        # Fortschritt final setzen
        self.bar.setRange(0, 1)
        self.bar.setValue(1)

    # ------------- helpers -------------
    def _parse_line(self, line: str):
        try:
            obj = json.loads(line)
        except Exception:
            self.append_log(line + "\n")
            return

        if "progress" in obj and "total" in obj:
            i, n = int(obj["progress"]), int(obj["total"])
            self.bar.setRange(0, n)
            self.bar.setValue(i)
            fn = obj.get("file", "")
            ok = "✓" if obj.get("ok") else "×"
            self.lbl.setText(f"{i}/{n} — {fn} [{ok}]")
            self.append_log(f"[{i}/{n}] {fn} ok={obj.get('ok')}\n")
            return

        if "summary" in obj:
            s = obj["summary"]
            self.append_log(
                f"\nSummary: processed={s.get('processed')}  "
                f"succeeded={s.get('succeeded')}  failed={s.get('failed')}  ok={s.get('ok')}\n"
            )
            return

        self.append_log(json.dumps(obj, ensure_ascii=False) + "\n")

    def append_log(self, text: str):
        self.log.moveCursor(self.log.textCursor().End)
        self.log.insertPlainText(text)
        self.log.moveCursor(self.log.textCursor().End)


def register_with(main_window) -> None:
    """
    Fügt im bestehenden MainWindow ein Menü "Import" (falls nicht vorhanden) hinzu
    und registriert dort "Bulk ingest folder…".
    main_window muss eine QMainWindow-Instanz sein (mit .menuBar()).
    """
    menubar = getattr(main_window, "menuBar", None)() if hasattr(main_window, "menuBar") else None
    if menubar is None:
        # Fallback: nichts tun
        return

    # Versuche vorhandenes "Import" Menü zu finden (nach Titel)
    import_menu = None
    for act in menubar.actions():
        if act.text().replace("&", "").strip().lower() == "import":
            import_menu = act.menu()
            break
    if import_menu is None:
        import_menu = menubar.addMenu("&Import")

    act = QAction("Bulk ingest folder…", main_window)
    act.setShortcut(QKeySequence("Ctrl+I"))
    import_menu.addAction(act)

    def _open_dialog():
        dlg = BulkIngestDialog(main_window)
        dlg.setModal(True)
        dlg.exec()

    act.triggered.connect(_open_dialog)
