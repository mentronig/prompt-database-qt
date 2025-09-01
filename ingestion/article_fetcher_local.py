# ingestion/article_fetcher_local.py
from __future__ import annotations

import sys, re, html, json, argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

def read_text_tolerant(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        try:
            return p.read_text(encoding="cp1252", errors="ignore")
        except Exception:
            return ""

def is_view_source_escaped(s: str) -> bool:
    sl = s.lower()
    return ("&lt;html" in sl) or ("&lt;!doctype" in sl) or ("&lt;body" in sl)

def unescape_if_needed(s: str) -> str:
    return html.unescape(s) if is_view_source_escaped(s) else s

def strip_tags_keep_ws(s: str) -> str:
    s = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def find_title(u: str) -> Optional[str]:
    m = re.search(r"<h1[^>]*>(.*?)</h1>", u, re.I|re.S)
    if m:
        t = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if t:
            return t
    m = re.search(r"<title[^>]*>(.*?)</title>", u, re.I|re.S)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return None

def extract_candidates(u: str) -> List[str]:
    # Prefer list items
    lis = re.findall(r"<li\b[^>]*>(.*?)</li>", u, re.I|re.S)
    out: List[str] = []
    for li in lis:
        t = re.sub(r"<[^>]+>", " ", li)
        t = html.unescape(t)
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) >= 15:
            out.append(t)
    if out:
        return out
    # Fallback to paragraphs / numbered sections
    body = strip_tags_keep_ws(u)
    parts = re.split(r"(?:\n\s*\d{1,3}\.\s+|\n\s*[-–•]\s+)", body)
    for p in parts:
        t = p.strip()
        if len(t) >= 15:
            out.append(t)
    return out

def _file_url(p: Path) -> str:
    return "file:///" + str(p.resolve()).replace("\\", "/")

def make_records(cands: List[str], src: Path, page_title: Optional[str]) -> List[Dict[str, Any]]:
    lines: List[Dict[str, Any]] = []
    for i, text in enumerate(cands, start=1):
        title = f"Prompt {i} — {page_title or src.stem}"
        lines.append({
            "extraction": {
                "title": title,
                "text": text,
                "tags": ["article", "pattern"]
            },
            "meta": {
                "url": _file_url(src),
                "source_title": page_title or src.stem
            },
            "source_path": str(src)
        })
    return lines

def write_jsonl(lines: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in lines:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Fetch prompts from local HTML (heuristic).")
    ap.add_argument("--path", required=True, help="HTML file or directory (non-recursive)")
    ap.add_argument("--out-dir", required=True, help="Output directory (txt + JSONL)")
    ap.add_argument("--min-length", type=int, default=0, help="Minimum content length to accept")
    ap.add_argument("--greedy", action="store_true", help="Keep paragraphs when no <li> found")
    ap.add_argument("--verbose", action="store_true", help="Verbose output")
    args = ap.parse_args(argv)

    base = Path(args.path)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files: List[Path] = []
    if base.is_file():
        if base.suffix.lower() in (".html", ".htm"):
            files.append(base)
    else:
        for f in base.iterdir():
            if f.is_file() and f.suffix.lower() in (".html", ".htm"):
                files.append(f)

    report_path = out_dir / "article_fetch_local_report.jsonl"
    report_lines: List[Dict[str, Any]] = []
    txt_written = 0

    for f in files:
        raw = read_text_tolerant(f)
        if not raw.strip():
            if args.verbose: print(f"[warn] empty file: {f}", file=sys.stderr)
            continue
        u = unescape_if_needed(raw)
        page_title = find_title(u)
        cands = extract_candidates(u)

        # If not greedy, keep only items that likely look like prompts (end with .?! or start with imperative)
        if not args.greedy:
            def is_prompt_like(t: str) -> bool:
                if re.search(r'(Act as|Write|Generate|Create|Explain|Draft|Summarize|How|What|Why|Please|Analyze|Suggest|Classify|Compare|Convert|Translate|Outline|Design|Propose|Prompt:)', t, re.I):
                    return True
                return bool(re.search(r'[?.!]$', t))
            cands = [t for t in cands if is_prompt_like(t)]

        cands = [t for t in cands if len(t) >= args.min_length]

        # Write .txt (joined)
        if cands:
            txt_path = out_dir / (f.stem + ".txt")
            txt_path.write_text("\n".join(cands), encoding="utf-8")
            txt_written += 1

        # JSONL records (one per prompt)
        report_lines.extend(make_records(cands, f, page_title))

    write_jsonl(report_lines, report_path)
    print(f"Report: {report_path}")
    if args.verbose:
        print(json.dumps({"files": len(files), "txt_written": txt_written, "jsonl_records": len(report_lines)}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
