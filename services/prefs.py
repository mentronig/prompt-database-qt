from __future__ import annotations
from pathlib import Path
import json

APP_DIR = Path.home() / ".promptdb"
APP_DIR.mkdir(parents=True, exist_ok=True)
PREFS_FILE = APP_DIR / "user_prefs.json"

def load() -> dict:
    if PREFS_FILE.exists():
        try:
            return json.loads(PREFS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save(data: dict) -> None:
    try:
        PREFS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
