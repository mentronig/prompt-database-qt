from __future__ import annotations
import re, json, html, argparse
from pathlib import Path
from typing import Any

# Einzel-Attribut
ATTR = r'(?:id|class|style|data-[\w:-]+|aria-[\w:-]+|role|href|src)\s*=\s*"[^"]*"'
ATTR_RE = re.compile(rf'\b{ATTR}', re.I)

# Ein ganzer Attribute-Block gefolgt von '>'
ATTR_BLOCK_THEN_GT_RE = re.compile(rf'^(?:\s*{ATTR}\s*)+>\s*', re.I)

# "Prompt N — " vorne
PROMPT_PREFIX_RE = re.compile(r'^\s*Prompt\s+\d+\s+[—-]\s+', re.I)

# HTML-Tags & Whitespace
TAG_RE = re.compile(r"<[^>]+>")
WS_RE  = re.compile(r"\s+")

ATTR_KEYWORD_RE = re.compile(r'\b(id|class|data-|aria-|href|src|style|role)\b', re.I)

def _strip_attrs_and_prefix(s: str) -> str:
    # 1) echte HTML-Tags raus
    s = TAG_RE.sub(" ", s)
    # 2) "Prompt N — " vorne ab
    s = PROMPT_PREFIX_RE.sub("", s)
    # 3) HARD CUT: komplette Attribute-Klötze + folgendes '>'
    s = ATTR_BLOCK_THEN_GT_RE.sub("", s)
    # 4) übrige Einzel-Attribute killen
    s = ATTR_RE.sub(" ", s)
    # 5) Falls noch '>' + Attribut-Wörter vorkommen → alles nach letztem '>'
    if ">" in s and ATTR_KEYWORD_RE.search(s):
        s = s.split(">")[-1]
    # 6) Entities & Whitespace
    s = html.unescape(s)
    s = WS_RE.sub(" ", s).strip()
    # 7) führende Anführungen
    s = re.sub(r'^[\'"]\s*', "", s)
    return s

def _clean_any(x: Any) -> Any:
    if isinstance(x, str):
        return _strip_attrs_and_prefix(x)
    if isinstance(x, list):
        return [_clean_any(v) for v in x]
    if isinstance(x, dict):
        return {k: _clean_any(v) for k, v in x.items()}
    return x

def clean_row(row: dict) -> dict:
    row = _clean_any(row)
    # Tags-Liste leicht normalisieren
    tags = row.get("tags")
    if isinstance(tags, list):
        seen, out = set(), []
        for t in tags:
            if not isinstance(t, str):
                continue
            t = WS_RE.sub(" ", t).strip().lower()
            t = re.sub(r"[^a-z0-9_\- ]+", "", t)
            if t and t not in seen:
                seen.add(t); out.append(t)
        row["tags"] = out
    return row

def main():
    ap = argparse.ArgumentParser(description="Recursively clean noisy JSONL prompts (strip attribute dumps/tags/ws)")
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    args = ap.parse_args()
    src, dst = Path(args.src), Path(args.dst)
    with src.open("r", encoding="utf-8", errors="ignore") as fin, dst.open("w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            row = clean_row(row)
            fout.write(json.dumps(row, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    main()
