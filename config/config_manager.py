import json
from pathlib import Path
from typing import Any, Dict

CONFIG_PATH = Path("config/app_config.json")

def load_config_json() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {"theme": "light", "last_view": "list"}

def save_config_json(cfg: Dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
