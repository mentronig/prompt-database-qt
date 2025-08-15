from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtGui import QIcon
from pathlib import Path

COLUMNS = ["id", "title", "category", "tags", "updated_at"]
CAT_ICON_DIR = Path("assets/icons/categories")

def category_icon_path(cat: str) -> Path | None:
    key = (cat or "").strip().lower()
    mapping = {
        "entwicklung": "dev.svg",
        "analyse": "analysis.svg",
        "dokumentation": "doc.svg",
        "kreativ": "creative.svg",
        "sonstiges": "misc.svg",
    }
    fname = mapping.get(key, "misc.svg")
    p = CAT_ICON_DIR / fname
    return p if p.exists() else None

class PromptTableModel(QAbstractTableModel):
    def __init__(self, rows=None, parent=None):
        super().__init__(parent)
        self._rows = rows or []

    def set_rows(self, rows):
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        key = COLUMNS[index.column()]

        if role in (Qt.DisplayRole, Qt.EditRole):
            val = row.get(key, "")
            if key == "tags" and isinstance(val, (list, tuple)):
                return ", ".join(val)
            return str(val) if val is not None else ""

        if role == Qt.DecorationRole and key == "category":
            p = category_icon_path(row.get("category",""))
            if p:
                return QIcon(str(p))

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            headers = {"id":"ID","title":"Titel","category":"Kategorie","tags":"Tags","updated_at":"Aktualisiert"}
            return headers.get(COLUMNS[section], COLUMNS[section])
        return str(section + 1)

    def row_at(self, row_idx: int):
        return self._rows[row_idx] if 0 <= row_idx < len(self._rows) else None
