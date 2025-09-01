# tools/dedupe_db.py
from __future__ import annotations

import argparse, json, hashlib, re, shutil, sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
from datetime import datetime, UTC  # timezone-aware


def repo_root() -> Path:
    here = Path(__file__).resolve()
    return here.parents[1] if (here.parent.name == "tools") else Path.cwd()


def db_path_from_root(root: Path) -> Path:
    return root / "data" / "prompts.json"


def load_items(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"DB not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
        return data["items"]
    if isinstance(data, list):
        return data
    raise ValueError("Unsupported DB format; expected dict with 'items' list or a list")


def write_items(path: Path, items: List[Dict[str, Any]]) -> None:
    payload = {"items": items}
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


_ws_re = re.compile(r"\s+")

def norm_text(s: str) -> str:
    return _ws_re.sub(" ", (s or "").strip()).lower()


def content_hash(item: Dict[str, Any]) -> str:
    content = item.get("content") or ""
    return hashlib.sha256(norm_text(content).encode("utf-8")).hexdigest()[:16]


def make_key(item: Dict[str, Any], mode: str) -> Tuple[str, str]:
    if mode == "content":
        return ("", content_hash(item))
    title = norm_text(str(item.get("title") or ""))
    return (title, content_hash(item))


def summarize_dupes(items: List[Dict[str, Any]], mode: str):
    seen: dict[Tuple[str, str], List[int]] = {}
    for idx, it in enumerate(items):
        k = make_key(it, mode)
        seen.setdefault(k, []).append(idx)
    groups = {k: idxs for k, idxs in seen.items() if len(idxs) > 1}
    return groups


def backup_file(path: Path) -> Path:
    bdir = path.parent.parent / "backups"
    bdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    bpath = bdir / f"prompts_{stamp}.json"
    shutil.copy2(path, bpath)
    return bpath


def main() -> int:
    ap = argparse.ArgumentParser(description="Detect and optionally remove duplicate records in prompts DB.")
    ap.add_argument("--mode", choices=["title+content", "content"], default="title+content", help="Key for duplicate detection")
    ap.add_argument("--keep", choices=["first", "last"], default="first", help="Which record to keep per duplicate group")
    ap.add_argument("--apply", action="store_true", help="Write de-duplicated DB in place (creates backup)")
    ap.add_argument("--limit-print", type=int, default=20, help="Max groups to print in summary")
    args = ap.parse_args()

    root = repo_root()
    db = db_path_from_root(root)
    items = load_items(db)
    groups = summarize_dupes(items, "content" if args.mode=="content" else "title+content")

    total_dupes = sum(len(v)-1 for v in groups.values())
    total_groups = len(groups)

    print(f"DB: {db}")
    print(f"Items: {len(items)}")
    print(f"Duplicate groups: {total_groups}  |  Duplicate records: {total_dupes}")
    print()
    shown = 0
    for (title_key, chash), idxs in list(groups.items())[: args.limit_print]:
        keep_idx = idxs[0] if args.keep=="first" else idxs[-1]
        titles = [ (items[i].get('title') or '').strip() for i in idxs ]
        print(f"- key=({title_key[:40]}…, {chash})  idxs={idxs}  keep={keep_idx}  titles={titles}")
        shown += 1
    if total_groups > shown:
        print(f"... ({total_groups - shown} more groups)")

    if not args.apply:
        print("\nDry-run. Use --apply to write changes (a backup will be created).")
        return 0

    # Apply: build new list preserving order but dropping duplicates per policy
    to_keep = set()
    for (title_key, chash), idxs in groups.items():
        keep_idx = idxs[0] if args.keep=="first" else idxs[-1]
        to_keep.add(keep_idx)
    new_items: List[Dict[str, Any]] = []
    seen_keys: set[Tuple[str,str]] = set()
    for i, it in enumerate(items):
        k = make_key(it, "content" if args.mode=="content" else "title+content")
        if k in seen_keys:
            continue
        if i in to_keep or k not in groups:
            new_items.append(it)
            seen_keys.add(k)

    if len(new_items) == len(items):
        print("No changes to apply.")
        return 0

    bpath = backup_file(db)
    write_items(db, new_items)
    print(f"Applied. New items: {len(new_items)} (was {len(items)}). Backup: {bpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
