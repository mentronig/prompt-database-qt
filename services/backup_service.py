from datetime import datetime
from pathlib import Path
def backup_json(src: Path, dst_dir: Path = Path("backups")) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"); dst = dst_dir / f"{src.stem}_{stamp}.json"
    if not src.exists(): src.parent.mkdir(parents=True, exist_ok=True); src.write_text("[]", encoding="utf-8")
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8"); return dst
def restore_json(backup_file: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True); dst.write_text(backup_file.read_text(encoding="utf-8"), encoding="utf-8")
