from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple
from tinydb import TinyDB

DEFAULTS: Dict[str, Any] = {
    "description": "",
    "category": "",
    "tags": [],
    "version": "v1.0",
    "sample_output": "",
    "related_ids": [],
}

def _backup_file(db_path: Path, backups_dir: Path = Path("backups")) -> Path:
    backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    dst = backups_dir / f"{db_path.stem}_{stamp}.json"
    if not db_path.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.write_text("[]", encoding="utf-8")
    dst.write_text(db_path.read_text(encoding="utf-8"), encoding="utf-8")
    return dst

def _ensure_defaults(doc: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in DEFAULTS.items():
        if k not in doc:
            doc[k] = v
    return doc

def migrate_tinydb(db_path: Path) -> Tuple[int, Path | None]:
    backup = _backup_file(db_path)
    db = TinyDB(str(db_path)); table = db.table("prompts")
    changed_count = 0
    for doc in table:
        before = dict(doc); after = _ensure_defaults(before.copy())
        if after != before:
            table.update(after, doc_ids=[doc.doc_id])
            changed_count += 1
    db.close()
    return changed_count, backup
