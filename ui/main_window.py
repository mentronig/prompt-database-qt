from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QTableView,
    QTextEdit, QSplitter, QToolBar, QFileDialog, QMessageBox, QPushButton,
    QDockWidget, QComboBox, QToolButton
)
from PySide6.QtCore import Qt, QSortFilterProxyModel, QModelIndex, QSize
from PySide6.QtGui import QIcon
from pathlib import Path

from data.prompt_repository import PromptRepository
from services.export_service import export_csv, export_markdown
from ui.prompt_table_model import PromptTableModel
from ui.prompt_editor import PromptEditor
from theme_manager import apply_theme, available_themes, load_saved_theme

ICON_DIR = Path("assets/icons")

def icon(name: str) -> QIcon:
    p = ICON_DIR / f"{name}.svg"
    return QIcon(str(p)) if p.exists() else QIcon()

class PromptFilterProxyModel(QSortFilterProxyModel):
    """Erweiterter Filter: durchsucht Titel, Inhalt, Beschreibung, Kategorie
       und kann zusätzlich per Tags einschränken (kommagetrennt).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.text = ""
        self.tags = []

    def set_text(self, text: str):
        self.text = (text or "").strip().lower()
        self.invalidateFilter()

    def set_tags(self, tags):
        self.tags = [t.strip().lower() for t in (tags or []) if t.strip()]
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        row = model.row_at(source_row)
        if not row:
            return True

        if self.text:
            blob = f"{row.get('title','')}\n{row.get('content','')}\n{row.get('description','')}\n{row.get('category','')}".lower()
            if self.text not in blob:
                return False

        if self.tags:
            row_tags = [t.lower() for t in (row.get('tags') or [])]
            for t in self.tags:
                if t not in row_tags:
                    return False

        return True

class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("Prompt-Datenbank (Qt)")
        self.resize(1240, 800)

        self.repo = PromptRepository()

        # Toolbar
        tb = QToolBar("Aktionen", self)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(tb)

        btn_new = QPushButton(icon("add"), "Neu")
        btn_edit = QPushButton(icon("edit"), "Bearbeiten")
        btn_del = QPushButton(icon("delete"), "Löschen")
        btn_export_csv = QPushButton(icon("export"), "Export CSV")
        btn_export_md = QPushButton(icon("markdown"), "Export MD")

        theme_btn = QToolButton()
        theme_btn.setIcon(icon("theme"))
        theme_btn.setToolTip("Theme wechseln (Sidebar)")

        for b in (btn_new, btn_edit, btn_del, btn_export_csv, btn_export_md):
            b.setMinimumHeight(28)
            tb.addWidget(b)
        tb.addSeparator()
        tb.addWidget(theme_btn)

        # Suche
        search_box = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Suche in Titel/Beschreibung/Content/Kategorie ...")
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Tags (kommagetrennt)")
        search_box.addWidget(QLabel("Suche:"))
        search_box.addWidget(self.search_edit, 2)
        search_box.addSpacing(8)
        search_box.addWidget(QLabel("Tags:"))
        search_box.addWidget(self.tags_edit, 1)

        # Tabelle & Preview
        self.model = PromptTableModel(self.repo.all())
        self.proxy = PromptFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.AscendingOrder)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.setColumnWidth(0, 60)   # ID
        self.table.setColumnWidth(1, 360)  # Titel
        self.table.setColumnWidth(2, 240)  # Kategorie (mit Icon)
        self.table.setColumnWidth(3, 260)  # Tags

        self.content = QTextEdit()
        self.content.setReadOnly(True)

        splitter = QSplitter(self)
        split_left = QWidget()
        left_layout = QVBoxLayout(split_left)
        left_layout.setContentsMargins(10,10,10,10)
        left_layout.addLayout(search_box)
        left_layout.addWidget(self.table)
        splitter.addWidget(split_left)
        splitter.addWidget(self.content)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        wrapper = QWidget(self)
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(12,12,12,12)
        layout.addWidget(splitter)
        self.setCentralWidget(wrapper)

        # Sidebar Dock (Theme chooser)
        dock = QDockWidget("Ansicht", self)
        dock.setObjectName("SidebarDock")
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        side = QWidget()
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(10,10,10,10)
        lbl = QLabel("Theme")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(available_themes())
        self.theme_combo.setCurrentText(load_saved_theme("light"))
        apply_btn = QPushButton("Anwenden")
        side_layout.addWidget(lbl)
        side_layout.addWidget(self.theme_combo)
        side_layout.addWidget(apply_btn)
        side_layout.addStretch(1)
        dock.setWidget(side)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        dock.hide()

        theme_btn.clicked.connect(lambda: dock.setVisible(not dock.isVisible()))
        apply_btn.clicked.connect(self.apply_selected_theme)

        # Signals
        self.search_edit.textChanged.connect(self.on_search_changed)
        self.tags_edit.textChanged.connect(self.on_tags_changed)
        self.table.selectionModel().currentRowChanged.connect(self.on_row_selected)
        btn_new.clicked.connect(self.on_new)
        btn_edit.clicked.connect(self.on_edit)
        btn_del.clicked.connect(self.on_delete)
        btn_export_csv.clicked.connect(self.on_export_csv)
        btn_export_md.clicked.connect(self.on_export_md)

        self.refresh()

    # --- actions ---
    def apply_selected_theme(self):
        name = self.theme_combo.currentText() or "light"
        apply_theme(self.app, name)

    def refresh(self):
        rows = self.repo.all()
        self.model.set_rows(rows)
        self.statusBar().showMessage(f"{len(rows)} Einträge geladen.")

    def current_row_data(self):
        index: QModelIndex = self.table.currentIndex()
        if not index.isValid():
            return None
        src_index = self.proxy.mapToSource(index)
        return self.model.row_at(src_index.row())

    def on_row_selected(self, current, prev):
        row = self.current_row_data()
        self.content.setPlainText(row.get("content","") if row else "")

    def on_search_changed(self, text):
        self.proxy.set_text(text)

    def on_tags_changed(self, text):
        tags = [t.strip() for t in text.split(",")] if text else []
        self.proxy.set_tags(tags)

    def on_new(self):
        dlg = PromptEditor(self)
        if dlg.exec():
            data = dlg.get_result()
            if data["title"] and data["content"]:
                self.repo.add(data)
                self.refresh()

    def on_edit(self):
        row = self.current_row_data()
        if not row:
            QMessageBox.information(self, "Bearbeiten", "Bitte Eintrag auswählen.")
            return
        dlg = PromptEditor(self, data=row)
        if dlg.exec():
            data = dlg.get_result()
            self.repo.update(row["id"], data)
            self.refresh()

    def on_delete(self):
        row = self.current_row_data()
        if not row:
            QMessageBox.information(self, "Löschen", "Bitte Eintrag auswählen.")
            return
        from PySide6.QtWidgets import QMessageBox as MB
        confirm = MB.question(self, "Löschen", f"Eintrag '{row.get('title','')}' wirklich löschen?")
        if confirm == MB.Yes:
            self.repo.delete(row["id"])
            self.refresh()

    def on_export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "exports/prompts.csv", "CSV (*.csv)")
        if not path:
            return
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        export_csv(self.repo.all(), Path(path))
        QMessageBox.information(self, "Export", f"CSV exportiert: {path}")

    def on_export_md(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Markdown", "exports/prompts.md", "Markdown (*.md)")
        if not path:
            return
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        export_markdown(self.repo.all(), Path(path))
        QMessageBox.information(self, "Export", f"Markdown exportiert: {path}")
