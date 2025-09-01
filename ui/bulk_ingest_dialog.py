from __future__ import annotations

import json
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel, QFileDialog, QHBoxLayout, QTableWidget, QTableWidgetItem
)

from .ingest_runner import IngestRunner


class BulkIngestDialog(QDialog):
    """Dialog to run the bulk ingest workflow without modifying the main window."""
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Bulk Ingest")
        self.resize(900, 600)

        self._folder = None

        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self.btn_select = QPushButton("Ordner wählen…", self)
        self.btn_run = QPushButton("Start", self)
        self.btn_run.setEnabled(False)
        top.addWidget(self.btn_select)
        top.addWidget(self.btn_run)
        layout.addLayout(top)

        self.log = QTextEdit(self)
        self.log.setReadOnly(True)
        layout.addWidget(QLabel("Logs:", self))
        layout.addWidget(self.log)

        self.table = QTableWidget(0, 2, self)
        self.table.setHorizontalHeaderLabels(["Key", "Value"])
        layout.addWidget(QLabel("Ergebnis:", self))
        layout.addWidget(self.table)

        self.btn_select.clicked.connect(self._choose_folder)
        self.btn_run.clicked.connect(self._start)

        self._runner: Optional[IngestRunner] = None

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Ordner mit HTML/TXT wählen")
        if folder:
            self._folder = folder
            self.btn_run.setEnabled(True)
            self._append(f"Selected folder: {folder}\\n")

    def _start(self) -> None:
        if not self._folder:
            return

        self.log.clear()
        self._runner = IngestRunner(folder=self._folder)
        self._runner.log.connect(self._append)
        self._runner.started.connect(lambda cmd: self._append(f"\\n>> {cmd}\\n"))
        self._runner.finished.connect(self._on_finished)
        self._runner.failed.connect(lambda code, msg: self._append(f"ERROR({code}): {msg}\\n"))
        self._runner.build_commands()
        self._runner.start()

    def _append(self, text: str) -> None:
        self.log.moveCursor(self.log.textCursor().End)
        self.log.insertPlainText(text)
        self.log.moveCursor(self.log.textCursor().End)

    def _on_finished(self, summary: dict) -> None:
        self.table.setRowCount(0)
        for k, v in summary.items():
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(k)))
            self.table.setItem(r, 1, QTableWidgetItem(json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)))
        self._append("\\nFertig.\\n")


def register_bulk_ingest_action(main_window) -> None:
    """Add an Import → Bulk ingest… action that opens this dialog."""
    from PySide6.QtGui import QAction
    menu_bar = main_window.menuBar()
    menu = None
    for a in menu_bar.actions():
        if a.text().replace("&", "").lower() == "import":
            menu = a.menu()
            break
    if menu is None:
        menu = menu_bar.addMenu("&Import")

    act = QAction("Bulk ingest folder…", main_window)
    act.triggered.connect(lambda: BulkIngestDialog(main_window).exec())
    menu.addAction(act)
