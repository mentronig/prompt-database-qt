# tools/source_path_injector.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any


def ensure_source_path(row: Dict[str, Any], src_path: str | Path) -> Dict[str, Any]:
    """
    Idempotent helper to enrich a JSONL row with a resolvable local source path
    and a file:// URL (if missing). Safe to call multiple times.

    Usage in article_fetcher_local.py (example):
        from tools.source_path_injector import ensure_source_path
        ...
        for src in input_files:
            row = {...}  # the row you are about to write to JSONL
            ensure_source_path(row, src)
            jsonl_file.write(json.dumps(row, ensure_ascii=False) + "\n")
    """
    p = Path(src_path)
    row.setdefault("source_path", str(p))

    # Prefer nested "meta" if present; else set flat "url"
    meta = row.get("meta")
    file_url = "file:///" + str(p).replace("\\", "/")
    if isinstance(meta, dict):
        meta.setdefault("url", file_url)
        row["meta"] = meta
    else:
        row.setdefault("url", file_url)

    return row