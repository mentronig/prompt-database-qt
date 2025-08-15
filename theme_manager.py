import json
from pathlib import Path
from PySide6.QtWidgets import QApplication
SETTINGS = Path("settings.json"); THEMES_DIR = Path("themes")
def available_themes() -> list[str]:
    return [p.stem for p in THEMES_DIR.glob("*.qss")] if THEMES_DIR.exists() else []
def load_saved_theme(default: str = "light") -> str:
    try:
        if SETTINGS.exists():
            return json.loads(SETTINGS.read_text(encoding="utf-8")).get("theme", default)
    except Exception: pass
    return default
def save_theme(name: str) -> None:
    SETTINGS.write_text(json.dumps({"theme": name}, ensure_ascii=False, indent=2), encoding="utf-8")
def apply_theme(app: QApplication, name: str) -> None:
    qss_path = THEMES_DIR / f"{name}.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
        save_theme(name)
