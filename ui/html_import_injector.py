from __future__ import annotations

# PySide6: QAction/QKeySequence liegen in QtGui
try:
    from PySide6.QtWidgets import QMenu
    from PySide6.QtGui import QAction, QKeySequence
except Exception:
    try:
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction, QKeySequence
    except Exception:
        raise ImportError("Neither PySide6 nor PyQt6 is available")

from .html_import_dialog import HtmlImportDialog

def _safe_refresh(window, summary: dict):
    # 1) expliziter Hook im MainWindow
    if hasattr(window, "on_import_completed"):
        try:
            window.on_import_completed(summary)
            return
        except Exception:
            pass
    # 2) Repository reload (sofern vorhanden)
    repo = getattr(window, "repo", None) or getattr(window, "repository", None)
    if repo and hasattr(repo, "reload"):
        try:
            repo.reload()
        except Exception:
            pass
    # 3) Gängige Refresh-Methoden
    for name in ("refresh", "refresh_table", "reload_view", "reload_table", "rebuild_model"):
        if hasattr(window, name):
            try:
                getattr(window, name)()
            except Exception:
                pass

def install(window):
    bar = window.menuBar()
    # Frisches Menü anlegen, keine Iteration über bestehende Objekte (vermeidet "C++ object deleted")
    menu = QMenu("&Import", window)
    bar.addMenu(menu)
    window._menu_import_html_db = menu  # starke Referenz

    action = QAction("Import HTML → DB", window)
    try:
        action.setShortcut(QKeySequence("Ctrl+H"))
    except Exception:
        pass

    def _open():
        dlg = HtmlImportDialog(window)
        try:
            dlg.importCompleted.connect(lambda summary: _safe_refresh(window, summary))
        except Exception:
            pass
        dlg.exec()

    action.triggered.connect(_open)
    menu.addAction(action)
    window._action_import_html_db = action  # starke Referenz
