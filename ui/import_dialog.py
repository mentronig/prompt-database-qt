from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog,
    QComboBox, QGridLayout, QTableWidget, QTableWidgetItem, QCheckBox, QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt

from services import import_service

class ImportDialog(QDialog):
    def __init__(self, repo, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import-Assistent")
        self.resize(820, 560)
        self.repo = repo
        self.rows: List[Dict[str, Any]] = []
        self.headers: List[str] = []

        root = QVBoxLayout(self)

        # File row
        file_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_btn = QPushButton("Datei wählen…")
        self.load_btn = QPushButton("Laden")
        file_row.addWidget(QLabel("Datei:"))
        file_row.addWidget(self.path_edit, 1)
        file_row.addWidget(self.path_btn)
        file_row.addWidget(self.load_btn)
        root.addLayout(file_row)

        # Mapping
        grid = QGridLayout()
        self.map_widgets: Dict[str, QComboBox] = {}
        row = 0
        for field in import_service.INTERNAL_FIELDS:
            grid.addWidget(QLabel(field), row, 0)
            cb = QComboBox()
            cb.addItem("<leer>")
            self.map_widgets[field] = cb
            grid.addWidget(cb, row, 1)
            row += 1
        root.addLayout(grid)

        # Options
        opt_row = QHBoxLayout()
        self.cb_dry = QCheckBox("Dry-Run (nur prüfen)")
        self.cb_dry.setChecked(True)
        self.cb_skip_dupes = QCheckBox("Duplikate überspringen")
        self.cb_skip_dupes.setChecked(True)
        opt_row.addWidget(self.cb_dry)
        opt_row.addWidget(self.cb_skip_dupes)
        opt_row.addStretch(1)
        root.addLayout(opt_row)

        # Preview
        self.preview = QTableWidget(0, 0)
        self.preview.setAlternatingRowColors(True)
        root.addWidget(self.preview, 1)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.buttons.button(QDialogButtonBox.Ok).setText("Import starten")
        root.addWidget(self.buttons)
        self.buttons.accepted.connect(self.on_do_import)
        self.buttons.rejected.connect(self.reject)

        # Signals
        self.path_btn.clicked.connect(self.on_pick_file)
        self.load_btn.clicked.connect(self.on_load)

    def on_pick_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Datei wählen", "", "Daten (*.csv *.json *.yml *.yaml)")
        if path:
            self.path_edit.setText(path)

    def on_load(self):
        p = Path(self.path_edit.text().strip())
        if not p.exists():
            QMessageBox.warning(self, "Fehler", "Datei nicht gefunden.")
            return
        try:
            self.rows, self.headers = import_service.load_rows(p)
        except Exception as e:
            QMessageBox.critical(self, "Lesefehler", str(e))
            return

        # Mapping-Combos befüllen
        for cb in self.map_widgets.values():
            cb.clear()
            cb.addItem("<leer>")
            for h in self.headers:
                cb.addItem(h)

        # Auto-Mapping (simple heuristics)
        auto = {
            "title": ["title","name","titel"],
            "description": ["description","desc","beschreibung"],
            "category": ["category","kategorie"],
            "tags": ["tags","tag","labels","schlagworte"],
            "content": ["content","prompt","text","inhalt"],
            "sample_output": ["sample","output","beispiel","example"],
            "version": ["version","rev"],
            "related_ids": ["related","relations","related_ids"],
        }
        for field, cb in self.map_widgets.items():
            # find first matching header
            found = None
            for cand in auto.get(field, []):
                for h in self.headers:
                    if h.strip().lower() == cand:
                        found = h; break
                if found: break
            if found:
                idx = cb.findText(found)
                if idx >= 0:
                    cb.setCurrentIndex(idx)

        # Preview (max 20 rows)
        self.preview.setColumnCount(len(self.headers))
        self.preview.setHorizontalHeaderLabels(self.headers)
        self.preview.setRowCount(min(20, len(self.rows)))
        for r, row in enumerate(self.rows[:20]):
            for c, h in enumerate(self.headers):
                val = row.get(h, "")
                self.preview.setItem(r, c, QTableWidgetItem(str(val)))

        # Analyze
        mapping = self._current_mapping()
        info = import_service.analyze(self.rows, mapping)
        QMessageBox.information(self, "Analyse",
                                f"Zeilen: {info['total']}\n"
                                f"Mapped: {info['mapped']}\n"
                                f"Ungültig (fehlende Pflichtfelder): {info['invalid']}")

    def _current_mapping(self) -> Dict[str, Optional[str]]:
        mp: Dict[str, Optional[str]] = {}
        for field, cb in self.map_widgets.items():
            text = cb.currentText()
            mp[field] = None if text == "<leer>" else text
        return mp

    def on_do_import(self):
        if not self.rows:
            QMessageBox.warning(self, "Import", "Keine Daten geladen.")
            return
        mapping = self._current_mapping()
        # Sicherheitscheck: Titel + Content müssen gemappt sein
        if not mapping.get("title") or not mapping.get("content"):
            QMessageBox.warning(self, "Import", "Bitte mindestens 'title' und 'content' mappen.")
            return

        res = import_service.import_rows(
            self.repo, self.rows, mapping,
            dry_run=self.cb_dry.isChecked(),
            skip_duplicates=self.cb_skip_dupes.isChecked()
        )

        msg = (f"Hinzugefügt: {res['added']}\n"
               f"Duplikate (übersprungen): {res['duplicates']}\n"
               f"Fehler: {len(res['errors'])}")
        if res['errors']:
            msg += "\n\n" + "\n".join(res['errors'][:10])
            if len(res['errors']) > 10:
                msg += f"\n… und {len(res['errors'])-10} weitere."
        QMessageBox.information(self, "Ergebnis", msg)

        if not self.cb_dry.isChecked() and not res['errors']:
            self.accept()
