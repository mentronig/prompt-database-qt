from pathlib import Path
from typing import Iterable, Dict, Any
import csv
def export_csv(rows: Iterable[Dict[str, Any]], path: Path) -> Path:
    rows = list(rows)
    if not rows: path.write_text("", encoding="utf-8"); return path
    headers = sorted({k for r in rows for k in r.keys()})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers); writer.writeheader()
        for r in rows: writer.writerow(r)
    return path
def export_markdown(rows: Iterable[Dict[str, Any]], path: Path) -> Path:
    rows = list(rows); parts = []
    for r in rows:
        title = r.get("title", "Untitled"); tags = ", ".join(r.get("tags", []) or [])
        parts.append(f"# {title}\n"); 
        if tags: parts.append(f"*Tags:* {tags}\n")
        parts.append("```\n"); parts.append((r.get("content") or "").rstrip() + "\n"); parts.append("```\n\n")
    path.write_text("".join(parts), encoding="utf-8"); return path
