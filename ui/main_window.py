# ui/main_window.py – Komplettversion mit Import-Assistent & Validierung

import sys                    
import json                   
from typing import Optional, List
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QTableView,
    QTextEdit, QSplitter, QToolBar, QFileDialog, QMessageBox, QPushButton,
    QDockWidget, QComboBox, QToolButton, QMenu, QCheckBox, QScrollArea, QProgressDialog
)
from PySide6.QtCore import Qt, QSortFilterProxyModel, QModelIndex, QSize, QPoint, QProcess
from PySide6.QtGui import QIcon, QAction, QKeySequence

from data.prompt_repository import PromptRepository
from services.export_service import export_csv, export_markdown, export_json, export_yaml
from ui.prompt_table_model import PromptTableModel
from ui.prompt_editor import PromptEditor
from ui.import_dialog import ImportDialog
from theme_manager import apply_theme, available_themes, load_saved_theme
from services import prefs

# Optional HTML-Details (schönere Darstellung)
try:
    from utils.html_render import render_details as _render_details
except Exception:
    _render_details = None

# Optional WebEngine (falls installiert, für schönes HTML)
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView  # type: ignore
    _HAS_WEB = True
except Exception:
    QWebEngineView = None  # type: ignore
    _HAS_WEB = False

from utils.flow_layout import FlowLayout

ICON_DIR = Path("assets/icons")
def icon(name: str) -> QIcon:
    p = ICON_DIR / f"{name}.svg"
    return QIcon(str(p)) if p.exists() else QIcon()


class PromptFilterProxyModel(QSortFilterProxyModel):
    """Filter: Volltext, Kategorie, Tags mit UND/ODER-Logik."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.text = ""
        self.tags: List[str] = []
        self.category = ""
        self.tag_logic_or = False  # False=UND (default), True=ODER

    def set_text(self, text: str):
        self.text = (text or "").strip().lower()
        self.invalidateFilter()

    def set_tags(self, tags: List[str]):
        self.tags = [t.strip().lower() for t in (tags or []) if t.strip()]
        self.invalidateFilter()

    def set_category(self, category: str):
        self.category = (category or "").strip().lower()
        self.invalidateFilter()

    def set_tag_logic_or(self, is_or: bool):
        self.tag_logic_or = bool(is_or)
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

        if self.category:
            if (row.get('category') or '').strip().lower() != self.category:
                return False

        if self.tags:
            row_tags = [t.lower() for t in (row.get('tags') or [])]
            if self.tag_logic_or:
                if not any(t in row_tags for t in self.tags):
                    return False
            else:
                for t in self.tags:
                    if t not in row_tags:
                        return False

        return True


class MainWindow(QMainWindow):
    def __init__(self, app, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle("Prompt-Datenbank (Qt)")
        self.resize(1360, 900)

        self.repo = PromptRepository()

        #Ignest aufrufe
        self._ingest_proc: QProcess | None = None
        self._ingest_progress: QProgressDialog | None = None


        # Toolbar
        tb = QToolBar("Aktionen", self)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(tb)

        btn_new = QPushButton(icon("add"), "Neu")
        btn_edit = QPushButton(icon("edit"), "Bearbeiten")
        btn_dup = QPushButton(icon("copy"), "Duplizieren")
        btn_del = QPushButton(icon("delete"), "Löschen")
        btn_import = QPushButton(icon("import"), "Import…")
        btn_export_csv = QPushButton(icon("export"), "CSV")
        btn_export_md = QPushButton(icon("markdown"), "MD")
        btn_export_json = QPushButton(icon("export"), "JSON")
        btn_export_yaml = QPushButton(icon("export"), "YAML")

        self.cb_export_filtered = QCheckBox("nur gefilterte Zeilen")
        self.cb_export_filtered.setChecked(True)
        self.cb_export_visible = QCheckBox("nur sichtbare Spalten (CSV/MD)")
        self.cb_export_visible.setChecked(False)

        btn_reset = QPushButton(icon("reset"), "Filter zurücksetzen")

        # Spalten-Menü
        self.columns_menu_btn = QToolButton()
        self.columns_menu_btn.setText("Spalten")
        self.columns_menu_btn.setPopupMode(QToolButton.InstantPopup)
        self.columns_menu = QMenu(self)
        self.columns_actions = {}

        theme_btn = QToolButton()
        theme_btn.setIcon(icon("theme"))
        theme_btn.setToolTip("Theme wechseln (Sidebar)")

        for b in (btn_new, btn_edit, btn_dup, btn_del, btn_import, btn_export_csv, btn_export_md, btn_export_json, btn_export_yaml):
            b.setMinimumHeight(28)
            tb.addWidget(b)
        tb.addSeparator()
        tb.addWidget(self.cb_export_filtered)
        tb.addWidget(self.cb_export_visible)
        tb.addSeparator()
        tb.addWidget(self.columns_menu_btn)
        tb.addSeparator()
        tb.addWidget(btn_reset)
        tb.addSeparator()
        tb.addWidget(theme_btn)

        #==========================================================
        # ---- Menüleiste: Import -> Bulk ingest folder… ----
        menubar = self.menuBar()
        import_menu = None
        # versuche vorhandenes "Import" Menü zu finden
        for act in menubar.actions():
            if act.text().replace("&", "").strip().lower() == "import":
                import_menu = act.menu()
                break
        if import_menu is None:
            import_menu = menubar.addMenu("&Import")

        self.action_bulk_ingest = QAction("Bulk ingest folder…", self)
        self.action_bulk_ingest.setShortcut(QKeySequence("Ctrl+I"))
        import_menu.addAction(self.action_bulk_ingest)
        self.action_bulk_ingest.triggered.connect(self.on_bulk_ingest_triggered)
        #==========================================================



        # Suche & Filter + Tag-Logik-Umschalter
        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Volltextsuche (Titel, Beschreibung, Content, Kategorie)")
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Tags (kommagetrennt)")

        self.category_combo = QComboBox()
        self.category_combo.addItem("")
        for c in self.repo.all_categories():
            self.category_combo.addItem(c)

        self.btn_tag_logic = QPushButton("Logik: UND")
        self.btn_tag_logic.setCheckable(True)
        self.btn_tag_logic.setToolTip("Klicken, um auf ODER umzuschalten")
        self.btn_tag_logic.clicked.connect(self.on_toggle_tag_logic)

        search_row.addWidget(QLabel("Suche:"))
        search_row.addWidget(self.search_edit, 2)
        search_row.addSpacing(8)
        search_row.addWidget(QLabel("Kategorie:"))
        search_row.addWidget(self.category_combo, 1)
        search_row.addSpacing(8)
        search_row.addWidget(QLabel("Tags:"))
        search_row.addWidget(self.tags_edit, 1)
        search_row.addSpacing(12)
        search_row.addWidget(self.btn_tag_logic)

        # Tag-Chips (Dark-Theme gut lesbar)
        chips_container = QWidget()
        self.chips_layout = FlowLayout(chips_container, spacing=6)
        self._build_tag_chips()
        chips_scroll = QScrollArea()
        chips_scroll.setWidgetResizable(True)
        chips_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        chips_scroll.setWidget(chips_container)

        # Tabelle & Detail-Panel
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
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 360)
        self.table.setColumnWidth(2, 260)
        self.table.setColumnWidth(3, 300)

        if _HAS_WEB and QWebEngineView is not None:
            self.detail = QWebEngineView()
            self._detail_is_web = True
        else:
            self.detail = QTextEdit()
            self.detail.setReadOnly(True)
            self._detail_is_web = False

        # Kontextmenü (inkl. Duplizieren)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.on_context_menu)

        splitter = QSplitter(self)
        split_left = QWidget(); left_layout = QVBoxLayout(split_left)
        left_layout.setContentsMargins(10,10,10,10)
        left_layout.addLayout(search_row)
        left_layout.addWidget(QLabel("Tags (Chips):"))
        left_layout.addWidget(chips_scroll)
        left_layout.addWidget(self.table)
        splitter.addWidget(split_left)
        splitter.addWidget(self.detail)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 4)

        wrapper = QWidget(self)
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(12,12,12,12)
        layout.addWidget(splitter)
        self.setCentralWidget(wrapper)

        # Sidebar: Themes
        dock = QDockWidget("Ansicht", self)
        dock.setObjectName("SidebarDock")
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        side = QWidget(); s_layout = QVBoxLayout(side)
        s_layout.setContentsMargins(10,10,10,10)
        lbl = QLabel("Theme")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(available_themes())
        self.theme_combo.setCurrentText(load_saved_theme("light"))
        apply_btn = QPushButton("Anwenden")
        s_layout.addWidget(lbl)
        s_layout.addWidget(self.theme_combo)
        s_layout.addWidget(apply_btn)
        s_layout.addStretch(1)
        dock.setWidget(side)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        dock.hide()

        theme_btn.clicked.connect(lambda: dock.setVisible(not dock.isVisible()))
        apply_btn.clicked.connect(self.apply_selected_theme)
        btn_reset.clicked.connect(self.on_reset_filters)

        # Signals
        self.search_edit.textChanged.connect(self.on_search_changed)
        self.tags_edit.textChanged.connect(self.on_tags_changed)
        self.category_combo.currentTextChanged.connect(self.on_category_changed)
        self.table.selectionModel().currentRowChanged.connect(self.on_row_selected)
        btn_new.clicked.connect(self.on_new)
        btn_edit.clicked.connect(self.on_edit)
        btn_dup.clicked.connect(self.on_duplicate)
        btn_del.clicked.connect(self.on_delete)
        btn_import.clicked.connect(self.on_import)
        btn_export_csv.clicked.connect(self.on_export_csv)
        btn_export_md.clicked.connect(self.on_export_md)
        btn_export_json.clicked.connect(self.on_export_json)
        btn_export_yaml.clicked.connect(self.on_export_yaml)

        # Spalten-Menü (nach Table init)
        for col, label in [(0, "ID"), (1, "Titel"), (2, "Kategorie"), (3, "Tags")]:
            act = QAction(label, self, checkable=True, checked=True)
            act.toggled.connect(lambda checked, c=col: self.table.setColumnHidden(c, not checked))
            self.columns_actions[col] = act
            self.columns_menu.addAction(act)

        # Preferences laden
        self._load_prefs()

        self.refresh()

    
    # --- Prefs ---
    def _load_prefs(self):
        p = prefs.load()
        self.search_edit.setText(p.get("search_text",""))
        self.tags_edit.setText(p.get("tags_text",""))
        cat = p.get("category","")
        if cat:
            idx = self.category_combo.findText(cat)
            if idx >= 0: self.category_combo.setCurrentIndex(idx)
        logic_or = bool(p.get("tag_logic_or", False))
        self.btn_tag_logic.setChecked(logic_or)
        self.btn_tag_logic.setText("Logik: ODER" if logic_or else "Logik: UND")
        self.proxy.set_tag_logic_or(logic_or)
        self.cb_export_filtered.setChecked(bool(p.get("export_filtered", True)))
        self.cb_export_visible.setChecked(bool(p.get("export_visible", False)))
        hidden_cols = set(p.get("hidden_cols", []))
        for col, act in self.columns_actions.items():
            vis = col not in hidden_cols
            act.setChecked(vis)
            self.table.setColumnHidden(col, not vis)

    def _save_prefs(self):
        hidden = []
        header = self.table.horizontalHeader()
        for col in range(4):
            if header.isSectionHidden(col):
                hidden.append(col)
        data = {
            "search_text": self.search_edit.text(),
            "tags_text": self.tags_edit.text(),
            "category": self.category_combo.currentText() or "",
            "tag_logic_or": self.btn_tag_logic.isChecked(),
            "export_filtered": self.cb_export_filtered.isChecked(),
            "export_visible": self.cb_export_visible.isChecked(),
            "hidden_cols": hidden,
        }
        prefs.save(data)

    # --- helpers ---
    def apply_selected_theme(self):
        name = self.theme_combo.currentText() or "light"
        apply_theme(self.app, name)

    def refresh(self):
        rows = self.repo.all()
        self.model.set_rows(rows)
        self._rebuild_chips_if_needed()
        self.statusBar().showMessage(f"{len(rows)} Einträge geladen.")
        self._update_details(self.current_row_data())

    def current_row_data(self):
        index: QModelIndex = self.table.currentIndex()
        if not index.isValid():
            return None
        src_index = self.proxy.mapToSource(index)
        return self.model.row_at(src_index.row())

    def _render_html(self, row):
        if _render_details is None:
            return None
        return _render_details(row)

    def _update_details(self, row):
        html = self._render_html(row)
        if html:
            self.detail.setHtml(html)
        else:
            if not row:
                text = "Kein Eintrag ausgewählt."
            else:
                tags = ", ".join(row.get("tags", []) or [])
                text = (
                    f"Titel: {row.get('title','')}\n"
                    f"Kategorie: {row.get('category','')}\n"
                    f"Tags: {tags}\n\n"
                    f"Beschreibung:\n{row.get('description','')}\n\n"
                    f"Prompt:\n{row.get('content','')}\n\n"
                    f"Beispielausgabe:\n{row.get('sample_output','')}\n"
                )
            if hasattr(self, "_detail_is_web") and self._detail_is_web:
                safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                self.detail.setHtml(f"<pre style='white-space:pre-wrap'>{safe}</pre>")
            else:
                self.detail.setPlainText(text)

    def _selected_tags_from_chips(self) -> List[str]:
        tags = []
        for i in range(self.chips_layout.count()):
            item = self.chips_layout.itemAt(i)
            w = item.widget()
            if hasattr(w, "isChecked") and w.isChecked():
                t = getattr(w, "tag_value", None)
                if t:
                    tags.append(t)
        return tags

    def _build_tag_chips(self):
        while self.chips_layout.count():
            self.chips_layout.takeAt(0)
        tags = sorted(self.repo.all_tags(), key=lambda s: s.lower())
        for t in tags:
            b = QPushButton(t)
            b.tag_value = t
            b.setCheckable(True)
            b.setStyleSheet("""
                QPushButton {
                    border: 1px solid #4b5563;
                    border-radius: 12px;
                    padding: 2px 10px;
                    background: #1f2937;
                    color: #f9fafb;
                }
                QPushButton:hover { background: #374151; }
                QPushButton:checked {
                    background: #2563eb;
                    border-color: #3b82f6;
                    color: #ffffff;
                }
            """)
            b.clicked.connect(lambda _=False: self.on_chip_changed())
            self.chips_layout.addWidget(b)

    def _rebuild_chips_if_needed(self):
        self._build_tag_chips()

    def _filtered_rows(self):
        rows = []
        model = self.model
        proxy = self.proxy
        for r in range(proxy.rowCount()):
            src_index = proxy.mapToSource(proxy.index(r, 0))
            row = model.row_at(src_index.row())
            if row:
                rows.append(row)
        return rows

    # --- Tag logic toggle ---
    def on_toggle_tag_logic(self):
        is_or = self.btn_tag_logic.isChecked()
        self.proxy.set_tag_logic_or(is_or)
        self.btn_tag_logic.setText("Logik: ODER" if is_or else "Logik: UND")
        self.btn_tag_logic.setToolTip("Klicken, um auf UND umzuschalten" if is_or else "Klicken, um auf ODER umzuschalten")

    # --- signals ---
    def on_row_selected(self, current, prev):
        row = self.current_row_data()
        self._update_details(row)

    def on_search_changed(self, text):
        self.proxy.set_text(text)

    def on_tags_changed(self, text):
        tags = [t.strip() for t in text.split(",")] if text else []
        chip_tags = self._selected_tags_from_chips()
        combined = list(dict.fromkeys(chip_tags + tags))
        self.proxy.set_tags(combined)

    def on_category_changed(self, text):
        self.proxy.set_category(text)

    def on_chip_changed(self):
        text_tags = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]
        chip_tags = self._selected_tags_from_chips()
        combined = list(dict.fromkeys(chip_tags + text_tags))
        self.proxy.set_tags(combined)

    def on_reset_filters(self):
        self.search_edit.clear()
        self.tags_edit.clear()
        self.category_combo.setCurrentIndex(0)
        self.btn_tag_logic.setChecked(False)
        self.on_toggle_tag_logic()
        for i in range(self.chips_layout.count()):
            w = self.chips_layout.itemAt(i).widget()
            if hasattr(w, "setChecked"):
                w.setChecked(False)
        self.proxy.set_tags([])

    # CRUD
    def on_new(self):
        dlg = PromptEditor(self)
        if dlg.exec():
            data = dlg.get_result()
            if data.get("title") and data.get("content"):
                self.repo.add(data)
                self._reload_categories()
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
            self._reload_categories()
            self.refresh()

    def on_duplicate(self):
        row = self.current_row_data()
        if not row:
            QMessageBox.information(self, "Duplizieren", "Bitte Eintrag auswählen.")
            return
        data = dict(row)
        data.pop("id", None)
        data["title"] = f"{row.get('title','')} (Kopie)".strip()
        dlg = PromptEditor(self, data=data)
        if dlg.exec():
            new_data = dlg.get_result()
            self.repo.add(new_data)
            self._reload_categories()
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
            self._reload_categories()
            self.refresh()

    def on_import(self):
        dlg = ImportDialog(self.repo, self)
        if dlg.exec():
            self._reload_categories()
            self.refresh()

    def _reload_categories(self):
        current = self.category_combo.currentText()
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("")
        for c in self.repo.all_categories():
            self.category_combo.addItem(c)
        idx = self.category_combo.findText(current)
        if idx >= 0:
            self.category_combo.setCurrentIndex(idx)
        self.category_combo.blockSignals(False)

    # Kontextmenü
    def on_context_menu(self, point: QPoint):
        index: QModelIndex = self.table.indexAt(point)
        if not index.isValid():
            return
        row = self.current_row_data()
        menu = QMenu(self)
        act_copy_prompt = QAction("Prompt kopieren", self)
        act_copy_title = QAction("Titel kopieren", self)
        act_copy_tags = QAction("Tags kopieren", self)
        act_dup = QAction("Duplizieren …", self)
        menu.addAction(act_copy_prompt)
        menu.addAction(act_copy_title)
        menu.addAction(act_copy_tags)
        menu.addSeparator()
        menu.addAction(act_dup)

        def _copy(text: str):
            if not text:
                return
            cb = self.app.clipboard()
            cb.setText(text)

        act_copy_prompt.triggered.connect(lambda: _copy(row.get("content", "") if row else ""))
        act_copy_title.triggered.connect(lambda: _copy(row.get("title", "") if row else ""))
        act_copy_tags.triggered.connect(lambda: _copy(", ".join(row.get("tags", []) if row else [])))
        act_dup.triggered.connect(self.on_duplicate)
        menu.exec(self.table.viewport().mapToGlobal(point))

    # --- Export helpers ---
    def _rows_for_export(self):
        if self.cb_export_filtered.isChecked():
            return self._filtered_rows()
        return self.repo.all()

    def _visible_fields(self) -> List[str]:
        """Sichtbare Spalten -> Feldnamen (Mapping der ersten 4 Spalten)."""
        header = self.table.horizontalHeader()
        mapping = {0: "id", 1: "title", 2: "category", 3: "tags"}
        fields = []
        for col, field in mapping.items():
            if not header.isSectionHidden(col):
                fields.append(field)
        if not fields:
            fields = list(mapping.values())
        return fields

    # Exporte
    def on_export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "exports/prompts.csv", "CSV (*.csv)")
        if not path: return
        rows = self._rows_for_export()
        fields = self._visible_fields() if self.cb_export_visible.isChecked() else None
        export_csv(rows, Path(path), fields=fields)
        QMessageBox.information(self, "Export", f"CSV exportiert: {path}")

    def on_export_md(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Markdown", "exports/prompts.md", "Markdown (*.md)")
        if not path: return
        rows = self._rows_for_export()
        fields = self._visible_fields() if self.cb_export_visible.isChecked() else None
        export_markdown(rows, Path(path), fields=fields)
        QMessageBox.information(self, "Export", f"Markdown exportiert: {path}")

    def on_export_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export JSON", "exports/prompts.json", "JSON (*.json)")
        if not path: return
        export_json(self._rows_for_export(), Path(path))
        QMessageBox.information(self, "Export", f"JSON exportiert: {path}")

    def on_export_yaml(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export YAML", "exports/prompts.yaml", "YAML (*.yaml *.yml)")
        if not path: return
        try:
            export_yaml(self._rows_for_export(), Path(path))
            QMessageBox.information(self, "Export", f"YAML exportiert: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export-Fehler", str(e))

        # ===== Bulk-Ingest (QProcess) =====

    def on_bulk_ingest_triggered(self):
        # Ordner mit .txt-Dateien wählen
        folder = QFileDialog.getExistingDirectory(self, "Ordner mit .txt-Dateien für Ingest wählen")
        if not folder:
            return
        self._start_bulk_ingest(folder)

    def _start_bulk_ingest(self, folder: str):
        if self._ingest_proc is not None:
            QMessageBox.information(self, "Läuft", "Ein Bulk-Ingest läuft bereits.")
            return

        # Fortschrittsdialog
        dlg = QProgressDialog("Starte Bulk-Ingest…", "Abbrechen", 0, 0, self)
        dlg.setCancelButtonText("Abbrechen")  # eindeutiger
        dlg.setWindowTitle("Bulk ingest")
        dlg.setWindowModality(Qt.ApplicationModal)
        dlg.setAutoClose(False)
        dlg.setAutoReset(False)
        dlg.show()
        self._ingest_progress = dlg

        # QProcess konfigurieren
        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.SeparateChannels)
        py = sys.executable   # venv-sicher
        args = [
            "-m", "ingestion.bulk_ingest_local",
            "--dir", folder,
            "--emit-jsonl", str(Path(folder) / "ingest_log.jsonl"),
            # Optional: Flags hier ergänzen
            # "--dry-run",
            # "--category", "local",
            # "--tags", "article,pattern,local",
        ]
        # working dir = Projekt-Root, damit -m ingestion.* gefunden wird
        proc.setWorkingDirectory(str(Path.cwd()))

        # Signale verbinden
        proc.readyReadStandardOutput.connect(self._on_ingest_stdout)
        proc.readyReadStandardError.connect(self._on_ingest_stderr)
        proc.finished.connect(self._on_ingest_finished)
        dlg.canceled.connect(proc.kill)
        dlg.canceled.connect(dlg.close)

        self._ingest_proc = proc
        proc.start(py, args)
        if not proc.waitForStarted(3000):
            QMessageBox.critical(self, "Fehler", "Konnte den Python-Prozess nicht starten.")
            self._ingest_proc = None
            dlg.close()
            self._ingest_progress = None
            return

        # initialer Text
        dlg.setLabelText(f"Verarbeite Ordner:\n{folder}")

    def _on_ingest_stdout(self):
        if not self._ingest_proc or not self._ingest_progress:
            return
        proc = self._ingest_proc
        dlg = self._ingest_progress
        # Zeilenweise lesen (JSON-Progress)
        while proc.canReadLine():
            raw = bytes(proc.readLine()).decode("utf-8", errors="replace").strip()
            if not raw:
                continue
            # Versuch JSON zu parsen
            try:
                obj = json.loads(raw)
            except Exception:
                # kein JSON -> im Dialog anzeigen
                dlg.setLabelText((dlg.labelText() or "") + "\n" + raw)
                continue

                i, n = int(obj["progress"]), int(obj["total"])
                if dlg.maximum() != n:
                    dlg.setMaximum(n)
                dlg.setValue(i)

                fn   = obj.get("file", "")
                titl = obj.get("title", "")
                ids  = obj.get("saved_ids") or []
                ok   = "✓" if obj.get("ok") else "×"

                # Mehrzeilige, gut lesbare Statusanzeige
                lines = [f"[{i}/{n}] {fn} {ok}"]
                if titl:
                    lines.append(f"→ Titel: {titl}")
                if ids:
                    lines.append(f"→ IDs : {', '.join(map(str, ids))}")
                dlg.setLabelText("\n".join(lines))
                return

                #continue

            if "summary" in obj:
                s = obj["summary"]
                txt = (
                    f"Fertig.\n"
                    f"processed: {s.get('processed')}  "
                    f"succeeded: {s.get('succeeded')}  "
                    f"failed: {s.get('failed')}  "
                    f"ok: {s.get('ok')}"
                )
                dlg.setLabelText(txt)
                continue

            # sonst Roh-Objekt anzeigen
            dlg.setLabelText((dlg.labelText() or "") + "\n" + json.dumps(obj, ensure_ascii=False))

    def _on_ingest_stderr(self):
        if not self._ingest_proc or not self._ingest_progress:
            return
        data = self._ingest_proc.readAllStandardError().data().decode("utf-8", errors="replace")
        if data:
            self._ingest_progress.setLabelText((self._ingest_progress.labelText() or "") + "\n" + data)

    def _on_ingest_finished(self, code: int, status):
        if self._ingest_progress:
            self._ingest_progress.setCancelButtonText("Fertig")
            if code == 0:
                self._ingest_progress.setLabelText((self._ingest_progress.labelText() or "") + "\nOK.")
            else:
                self._ingest_progress.setLabelText((self._ingest_progress.labelText() or "") + f"\nBeendet mit Code={code}.")
            self._ingest_progress.setMaximum(1)
            self._ingest_progress.setValue(1)
        # Prozess freigeben
        self._ingest_proc = None
        # Nach erfolgreichem Ingest: Tabelle neu laden
        try:
            self._reload_categories()
            self.refresh()
        except Exception:
            pass

    
    # Persist preferences on close
    def closeEvent(self, event):
        self._save_prefs()
        super().closeEvent(event)
