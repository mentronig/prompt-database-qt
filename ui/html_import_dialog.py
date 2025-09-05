from __future__ import annotations
from pathlib import Path
from typing import Optional
import json

try:
    from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                                   QFileDialog, QTextEdit, QLineEdit, QDialogButtonBox)
    from PySide6.QtCore import Qt, Signal
except Exception:
    from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                                 QFileDialog, QTextEdit, QLineEdit, QDialogButtonBox)
    from PyQt6.QtCore import Qt
    from PyQt6.QtCore import pyqtSignal as Signal

from ui.ingest_runner import IngestRunner, build_commands_for_path

class HtmlImportDialog(QDialog):
    importCompleted = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import HTML → DB")
        self.resize(720, 460)
        self._build_ui()
        self._runner: Optional[IngestRunner] = None

    def _build_ui(self):
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        self.path_edit = QLineEdit(self)
        self.browse_btn = QPushButton("Durchsuchen…", self)
        row.addWidget(QLabel("HTML-Datei:", self))
        row.addWidget(self.path_edit)
        row.addWidget(self.browse_btn)
        lay.addLayout(row)

        self.log = QTextEdit(self)
        self.log.setReadOnly(True)
        lay.addWidget(self.log)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                        QDialogButtonBox.StandardButton.Cancel, self)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Import starten")
        lay.addWidget(self.buttons)

        self.browse_btn.clicked.connect(self._on_browse)
        self.buttons.accepted.connect(self._on_start)
        self.buttons.rejected.connect(self.reject)

    def _on_browse(self):
        file, _ = QFileDialog.getOpenFileName(self, "HTML auswählen", "", "HTML (*.html *.htm)")
        if file:
            self.path_edit.setText(file)

    def append_log(self, text: str):
        self.log.append(text)

    def _on_start(self):
        p = self.path_edit.text().strip()
        if not p:
            self.append_log("Bitte eine HTML-Datei auswählen.")
            return
        if not Path(p).exists():
            self.append_log(f"Datei nicht gefunden: {p}")
            return

        # Stabil: kein LLM nötig
        cmds = build_commands_for_path(p, mode="heuristic-only")
        self._runner = IngestRunner(self)
        self._runner.stdout.connect(self.append_log)
        self._runner.stderr.connect(self.append_log)
        self._runner.finished.connect(self._on_finished)
        self.append_log("Starte Import-Workflow… (Modus: heuristic-only)")
        self._runner.run(cmds)

    def _on_finished(self, code: int, summary: dict):
        if code == 0:
            self.append_log("✅ Import abgeschlossen.")
        else:
            self.append_log(f"❌ Import fehlgeschlagen (Exit {code}).")
        try:
            self.importCompleted.emit(summary or {})
        except Exception:
            pass
        if summary:
            try:
                self.log.append("Summary: " + json.dumps(summary, ensure_ascii=False))
            except Exception:
                pass
