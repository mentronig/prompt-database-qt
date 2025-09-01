from __future__ import annotations

# ensure repo root on sys.path when executed as module or file
import sys
from pathlib import Path
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import argparse, json
from typing import List, Any
from data.prompt_repository import PromptRepository  # type: ignore

def _shorten(s: str, n: int) -> str:
    if s is None: return ""
    s = str(s)
    return s if len(s) <= n else s[: max(0, n - 1)] + "…"

def _ensure_list(x: Any) -> List[str]:
    if isinstance(x, list): return [str(v) for v in x]
    if x is None: return []
    return [str(x)]

def main() -> int:
    ap = argparse.ArgumentParser(description="Show the last N records from the prompts DB.")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--fields", default="title,category,tags")
    ap.add_argument("--truncate", type=int, default=80)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    repo = PromptRepository()
    items = repo.all()
    if args.limit and args.limit > 0:
        items = items[-args.limit:]

    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return 0

    fields = [f.strip() for f in (args.fields or "").split(",") if f.strip()]
    rows = []
    for it in items:
        row = []
        for f in fields:
            val = it.get(f, "")
            if f == "tags":
                val = ", ".join(_ensure_list(val))
            else:
                val = _shorten(str(val), args.truncate)
            row.append(val)
        rows.append(row)

    widths = [len(h) for h in fields]
    for r in rows:
        for i, v in enumerate(r):
            widths[i] = max(widths[i], len(v))

    def fmt(vals):
        return " | ".join(v.ljust(widths[i]) for i, v in enumerate(vals))

    if fields:
        print(fmt(fields))
        print("-+-".join("-" * w for w in widths))
    for r in rows:
        print(fmt(r))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
