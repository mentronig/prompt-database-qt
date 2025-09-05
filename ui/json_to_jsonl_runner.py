from __future__ import annotations
import argparse, json
from pathlib import Path

def _flatten(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("final_prompts", "heuristic_prompts", "prompts", "items", "records"):
            v = data.get(key)
            if isinstance(v, list):
                return v
        batches = data.get("batches")
        if isinstance(batches, list):
            out = []
            for b in batches:
                if isinstance(b, dict):
                    for key in ("final_prompts", "heuristic_prompts", "prompts", "items", "records"):
                        v = b.get(key)
                        if isinstance(v, list):
                            out.extend(v)
            return out
    return []

def main():
    ap = argparse.ArgumentParser(description="Convert JSON array/dict to JSONL")
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    a = ap.parse_args()
    src = Path(a.src); dst = Path(a.dst)
    rows = _flatten(json.loads(src.read_text(encoding="utf-8")))
    with dst.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    main()
