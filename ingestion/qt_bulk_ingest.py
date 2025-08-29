import json
import sys
import os
from pathlib import Path

from PySide6.QtCore import Qt, QProcess, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QProgressBar,
    QLabel,
    QTextEdit,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QMenuBar,
    QMessageBox,
)

# Hinweis:
# Dieses UI ruft dein Skript `ingestion.bulk_ingest_local` auf.
# Es erwartet pro Datei eine JSON-Zeile mit {"progress": i, "total": n, ...}
# und am Ende {"summary": {...}} – genau so gibt es unser Bulk-Skript aus.


class BulkIngestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MT Prompt Engine — Bulk Ingest")
        self.resize(980, 640)

        # --- zentraler Bereich (Progress + Log + Buttons) ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # bis wir total kennen
        self.progress_label = QLabel("Noch kein Ingest gestartet.")
        self.progress_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        self.btn_start = QPushButton("Bulk ingest folder…")
        self.btn_start.clicked.connect(self.on_choose_and_start)

        self.btn_cancel = QPushButton("Abort")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.on_abort)

        top_row = QHBoxLayout()
        top_row.addWidget(self.progress_label)
        top_row.addStretch(1)
        top_row.addWidget(self.btn_start)
        top_row.addWidget(self.btn_cancel)

        layout = QVBoxLayout()
        layout.addLayout(top_row)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        # --- Menü ---
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)

        menu_tools = menubar.addMenu("&Tools")
        self.action_bulk = QAction("Bulk ingest folder…", self)
        self.action_bulk.setShortcut(QKeySequence("Ctrl+I"))
        self.action_bulk.triggered.connect(self.on_choose_and_start)
        menu_tools.addAction(self.action_bulk)

        # Prozess
        self.proc: QProcess | None = None
        self.running = False
        self.total = None
        self.completed = 0

        # optional: Merke letzten Ordner (kleiner Komfort)
        self.last_dir = str(Path.cwd())

    # ---------------------------
    # UI actions
    # ---------------------------
    def on_choose_and_start(self):
        if self.running:
            QMessageBox.warning(self, "Schon aktiv", "Ein Ingest läuft bereits.")
            return

        folder = QFileDialog.getExistingDirectory(
            self, "Choose folder with .txt files", self.last_dir
        )
        if not folder:
            return

        self.last_dir = folder
        self.start_process(folder)

    def start_process(self, folder: str):
        """
        Startet QProcess:
          python -m ingestion.bulk_ingest_local --dir <folder> --emit-jsonl <folder>/ingest_log.jsonl
        """
        self.append_log(f"Starting bulk ingest in: {folder}\n")

        self.proc = QProcess(self)
        # Wichtig: Puffer zeilenweise verarbeiten
        self.proc.setProcessChannelMode(QProcess.SeparateChannels)

        py = sys.executable  # venv-sicher
        args = [
            "-m", "ingestion.bulk_ingest_local",
            "--dir", folder,
            "--emit-jsonl", os.path.join(folder, "ingest_log.jsonl"),
            # HIER optional Flags:
            # "--dry-run",
            # "--category", "local",
            # "--tags", "article,pattern,local",
        ]

        # Verzeichnis setzen (damit Python das Modul findet)
        self.proc.setWorkingDirectory(str(Path.cwd()))

        # Verbinden
        self.proc.readyReadStandardOutput.connect(self.on_stdout)
        self.proc.readyReadStandardError.connect(self.on_stderr)
        self.proc.finished.connect(self.on_finished)

        self.proc.start(py, args)
        if not self.proc.waitForStarted(3000):
            QMessageBox.critical(self, "Fehler", "Konnte Python-Prozess nicht starten.")
            self.proc = None
            return

        self.running = True
        self.completed = 0
        self.total = None
        self.progress_bar.setRange(0, 0)  # bis wir total wissen
        self.progress_label.setText("Bulk ingest läuft…")
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)

    def on_abort(self):
        if self.proc and self.running:
            self.append_log("\n[User] Abbruch angefordert…\n")
            self.proc.kill()
            self.proc = None
            self.on_finished(-1, QProcess.CrashExit)

    # ---------------------------
    # Prozess-Callbacks
    # ---------------------------
    def on_stdout(self):
        if not self.proc:
            return
        # Wir lesen zeilenweise
        while self.proc.canReadLine():
            raw = bytes(self.proc.readLine()).decode("utf-8", errors="replace").strip()
            if not raw:
                continue
            self.parse_progress_line(raw)

    def on_stderr(self):
        if not self.proc:
            return
        data = self.proc.readAllStandardError().data().decode("utf-8", errors="replace")
        if data:
            self.append_log(data)

    def on_finished(self, code: int, status: QProcess.ExitStatus):
        self.running = False
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)

        if code == 0 and status == QProcess.NormalExit:
            self.append_log("\n[OK] Bulk ingest beendet.\n")
        elif code == -1 and status == QProcess.CrashExit:
            self.append_log("\n[ABORT] Prozess wurde beendet.\n")
        else:
            self.append_log(f"\n[ERROR] Prozess endete mit Code={code}, Status={status}.\n")

        # Progress finalisieren
        if self.total:
            self.progress_bar.setValue(self.total)
        else:
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(1)
        self.progress_label.setText("Fertig.")

        # Prozess-Objekt freigeben
        self.proc = None

    # ---------------------------
    # Helpers
    # ---------------------------
    def parse_progress_line(self, line: str):
        """
        Erwartete Zeilen:
          {"progress": i, "total": n, "file": "...", "ok": true}
          {"summary": {"processed": x, "succeeded": y, "failed": z, "ok": true/false}}
        Alles andere wird geloggt.
        """
        try:
            obj = json.loads(line)
        except Exception:
            # kein JSON → normal loggen
            self.append_log(line + "\n")
            return

        if "progress" in obj and "total" in obj:
            i = int(obj["progress"])
            n = int(obj["total"])
            self.total = n
            self.completed = i

            # Fortschritt updaten
            self.progress_bar.setRange(0, n)
            self.progress_bar.setValue(i)
            file_disp = obj.get("file", "")
            ok_disp = "✓" if obj.get("ok") else "×"
            self.progress_label.setText(f"{i}/{n} — {file_disp} [{ok_disp}]")
            # optional kompakter Log
            self.append_log(f"[{i}/{n}] {file_disp} ok={obj.get('ok')}\n")
            return

        if "summary" in obj:
            s = obj["summary"]
            msg = (
                f"\nSummary:\n"
                f"  processed: {s.get('processed')}\n"
                f"  succeeded: {s.get('succeeded')}\n"
                f"  failed   : {s.get('failed')}\n"
                f"  ok       : {s.get('ok')}\n"
            )
            self.append_log(msg)
            return

        # sonst Vollausgabe
        self.append_log(json.dumps(obj, ensure_ascii=False) + "\n")

    def append_log(self, text: str):
        self.log.moveCursor(self.log.textCursor().End)
        self.log.insertPlainText(text)
        self.log.moveCursor(self.log.textCursor().End)


def main():
    app = QApplication(sys.argv)
    win = BulkIngestWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
