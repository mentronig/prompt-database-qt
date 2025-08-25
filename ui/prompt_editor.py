from __future__ import annotations
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QComboBox, QDialogButtonBox
)
from PySide6.QtCore import Qt

class PromptEditor(QDialog):
    def __init__(self, parent=None, data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle("Prompt bearbeiten")
        self.resize(700, 540)

        self.data = data or {}

        root = QVBoxLayout(self)

        # Titel
        self.title_edit = QLineEdit(self.data.get("title",""))
        root.addWidget(QLabel("Titel *"))
        root.addWidget(self.title_edit)

        # Kategorie
        self.category_edit = QLineEdit(self.data.get("category",""))
        root.addWidget(QLabel("Kategorie"))
        root.addWidget(self.category_edit)

        # Tags
        self.tags_edit = QLineEdit(", ".join(self.data.get("tags", []) or []))
        root.addWidget(QLabel("Tags (Komma-getrennt)"))
        root.addWidget(self.tags_edit)

        # Beschreibung
        self.desc_edit = QTextEdit(self.data.get("description",""))
        root.addWidget(QLabel("Beschreibung"))
        root.addWidget(self.desc_edit, 1)

        # Prompt
        self.content_edit = QTextEdit(self.data.get("content",""))
        root.addWidget(QLabel("Prompt *"))
        root.addWidget(self.content_edit, 2)

        # Beispielausgabe
        self.sample_edit = QTextEdit(self.data.get("sample_output",""))
        root.addWidget(QLabel("Beispielausgabe"))
        root.addWidget(self.sample_edit, 1)

        # Version
        self.version_edit = QLineEdit(str(self.data.get("version","")))
        root.addWidget(QLabel("Version"))
        root.addWidget(self.version_edit)

        # Errors
        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet("color:#ef4444;")
        root.addWidget(self.error_lbl)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.buttons.button(QDialogButtonBox.Ok).setText("Speichern")
        root.addWidget(self.buttons)
        self.buttons.accepted.connect(self.on_accept)
        self.buttons.rejected.connect(self.reject)

        # Live-Validation
        self.title_edit.textChanged.connect(self.validate)
        self.content_edit.textChanged.connect(self.validate)
        self.tags_edit.textChanged.connect(self.validate)

        self.validate()

    def _parse_tags(self, text: str) -> List[str]:
        # Erlaubt Komma oder Semikolon als Trenner
        parts = [p.strip() for p in text.replace(";",",").split(",")]
        return [p for p in parts if p]

    def validate(self):
        title_ok = bool(self.title_edit.text().strip())
        content_ok = bool(self.content_edit.toPlainText().strip())

        errors = []
        if not title_ok:
            errors.append("Titel ist Pflicht.")
        if not content_ok:
            errors.append("Prompt ist Pflicht.")

        # Tags Format prüfen (z. B. keine doppelten)
        tags = self._parse_tags(self.tags_edit.text())
        if len(tags) != len(set(t.lower() for t in tags)):
            errors.append("Tags enthalten Duplikate.")

        # UI Feedback
        def mark(widget, ok: bool):
            widget.setStyleSheet("" if ok else "border:1px solid #ef4444;")
        mark(self.title_edit, title_ok)
        mark(self.content_edit, content_ok)

        self.error_lbl.setText(" \n".join(errors))
        self.buttons.button(self.buttons.Ok).setEnabled(len(errors) == 0)

    def get_result(self) -> Dict[str, Any]:
        return {
            "title": self.title_edit.text().strip(),
            "description": self.desc_edit.toPlainText().strip(),
            "category": self.category_edit.text().strip(),
            "tags": self._parse_tags(self.tags_edit.text()),
            "content": self.content_edit.toPlainText().strip(),
            "sample_output": self.sample_edit.toPlainText().strip(),
            "version": self.version_edit.text().strip(),
        }

    def on_accept(self):
        self.validate()
        if self.buttons.button(self.buttons.Ok).isEnabled():
            self.accept()
