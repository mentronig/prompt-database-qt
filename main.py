import logging, sys, os
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from PySide6.QtWidgets import QApplication
from config.config_loader import load_config
from ui.main_window import MainWindow
from theme_manager import load_saved_theme, apply_theme
from services.migration_service import migrate_tinydb
from ui.html_import_injector import install as install_html_import

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():
    try:
        load_config()
        db_path = Path(os.getenv("DB_PATH", "data/prompts.json"))
        changed, backup = migrate_tinydb(db_path)
        logging.info(f"Migration geprüft: {changed} Einträge aktualisiert. Backup: {backup}")

        app = QApplication(sys.argv)
        apply_theme(app, load_saved_theme("light"))
        win = MainWindow(app)
        install_html_import(win)
        win.show()
        sys.exit(app.exec())
    except Exception:
        logging.exception("❌ Fehler beim Starten der Anwendung")
        sys.exit(1)

if __name__ == "__main__":
    main()
