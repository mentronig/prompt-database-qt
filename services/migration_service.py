from __future__ import annotations
from pathlib import Path
from typing import Tuple
import shutil, datetime, json, io

def _backup(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    bak = path.with_suffix(path.suffix + f".bak.{ts}")
    if path.exists():
        shutil.copy2(path, bak)
    return bak

def _normalize_utf8(path: Path) -> bool:
    """
    Ensure file is valid JSON and UTF-8 encoded.
    Returns True if the file was modified (re-encoded or cleaned), else False.
    """
    if not path.exists():
        return False
    raw = path.read_bytes()
    modified = False

    # Try UTF-8 first (accept BOM)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Fallback: try cp1252 and then re-encode to UTF-8
        text = raw.decode("cp1252")
        modified = True

    # Validate JSON structure of TinyDB file: {"_default": { "1": {...}, ... }}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to repair common issues: stray control chars that cp1252 kept
        # Remove characters that are invalid in JSON text (keep it conservative)
        cleaned = "".join(ch for ch in text if ch.isprintable() or ch in "\n\r\t")
        if cleaned != text:
            text = cleaned
            modified = True
        data = json.loads(text)  # may still raise; let it bubble up

    # Write back normalized UTF-8 (no BOM) with ensure_ascii=False, indent for readability
    if modified:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return modified

def migrate_tinydb(db_path: Path) -> Tuple[int, Path | None]:
    """
    Normalize TinyDB JSON file encoding to UTF-8 (handles cp1252 files) and validate JSON.
    Returns (changed_count, backup_path).
    changed_count = 1 if file was modified/normalized, else 0.
    """
    db_path = Path(db_path)
    bak = None
    if db_path.exists():
        bak = _backup(db_path)
        changed = 1 if _normalize_utf8(db_path) else 0
        return changed, bak
    else:
        # No DB yet; nothing to migrate
        return 0, None
