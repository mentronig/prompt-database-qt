from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox, QComboBox
)
from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtWidgets import QCompleter

from data.prompt_repository import PromptRepository

DEFAULT_CATEGORIES = ["", "Entwicklung", "Analyse", "Dokumentation", "Kreativ", "Sonstiges"]

class PromptEditor(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("Prompt bearbeiten" if data else "Prompt anlegen")
        self.resize(720, 680)
        self.data = data or {}
        self.repo = PromptRepository()

        # Titel
        self.title_edit = QLineEdit(self.data.get("title", ""))

        # Beschreibung
        self.desc_edit = QTextEdit(self.data.get("description", ""))
        self.desc_edit.setPlaceholderText("Kurzbeschreibung – wofür ist der Prompt gedacht?")

        # Kategorie (Dropdown + freie Eingabe)
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems(DEFAULT_CATEGORIES)
        current_cat = self.data.get("category", "").strip()
        if current_cat:
            idx = self.category_combo.findText(current_cat)
            if idx < 0:
                self.category_combo.addItem(current_cat)
                idx = self.category_combo.findText(current_cat)
            self.category_combo.setCurrentIndex(idx)

        # Tags mit Autocomplete (kommagetrennt)
        self.tags_edit = QLineEdit(", ".join(self.data.get("tags", []) or []))
        tags = self.repo.all_tags()
        self.tag_model = QStringListModel(tags)
        completer = QCompleter(self.tag_model, self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)  # FIX: richtiger Typ
        completer.setFilterMode(Qt.MatchContains)
        self.tags_edit.setCompleter(completer)

        # Version
        self.version_edit = QLineEdit(self.data.get("version", "v1.0"))

        # Inhalt (Pflichtfeld)
        self.content_edit = QTextEdit(self.data.get("content", ""))
        self.content_edit.setPlaceholderText("Der eigentliche Prompt-Text ...")

        # Beispielausgabe
        self.sample_edit = QTextEdit(self.data.get("sample_output", ""))
        self.sample_edit.setPlaceholderText("Optionale Beispielausgabe ...")

        # Verwandte IDs
        self.related_edit = QLineEdit(", ".join(map(str, self.data.get("related_ids", []) or [])))
        self.related_edit.setPlaceholderText("z. B. 3, 12, 57")

        # Layout
        form = QFormLayout(self)
        form.setVerticalSpacing(12)
        form.addRow("Titel*", self.title_edit)
        form.addRow("Beschreibung", self.desc_edit)
        form.addRow("Kategorie", self.category_combo)
        form.addRow("Tags", self.tags_edit)
        form.addRow("Version", self.version_edit)
        form.addRow("Inhalt*", self.content_edit)
        form.addRow("Beispielausgabe", self.sample_edit)
        form.addRow("Verwandte IDs (Komma)", self.related_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _parse_related(self, text: str):
        out = []
        for p in (text or "").split(","):
            p = p.strip()
            if p.isdigit():
                out.append(int(p))
        return out

    def get_result(self):
        tags = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]
        return {
            "title": self.title_edit.text().strip(),
            "description": self.desc_edit.toPlainText().strip(),
            "category": self.category_combo.currentText().strip(),
            "tags": tags,
            "version": self.version_edit.text().strip() or "v1.0",
            "content": self.content_edit.toPlainText().strip(),
            "sample_output": self.sample_edit.toPlainText().strip(),
            "related_ids": self._parse_related(self.related_edit.text()),
        }

    def accept(self):
        # einfache Validierung
        if not self.title_edit.text().strip() or not self.content_edit.toPlainText().strip():
            super().reject()
            return
        # Autocomplete-Quelle für zukünftige Dialoge aktualisieren (live beim nächsten Öffnen)
        self.tag_model.setStringList(self.repo.all_tags())
        super().accept()
