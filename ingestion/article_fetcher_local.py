from __future__ import annotations
import argparse, os, re, json as _json
from typing import Optional, List, Tuple
from dataclasses import dataclass

try:
    import bs4
    from bs4 import BeautifulSoup
except Exception:
    bs4 = None
try:
    import trafilatura
except Exception:
    trafilatura = None
try:
    from readability import Document
except Exception:
    Document = None

_PRELOADED_RE = re.compile(r'window\.__PRELOADED_STATE__\s*=\s*(\{.*?\})\s*<\/script>', re.DOTALL)

def parse_preloaded_state_text(html: str) -> Optional[str]:
    m = _PRELOADED_RE.search(html)
    if not m: return None
    raw = m.group(1)
    try:
        data = _json.loads(raw)
    except Exception:
        return None
    texts: List[str] = []
    def walk(obj):
        if isinstance(obj, dict):
            if obj.get("__typename") == "Paragraph":
                t = obj.get("text")
                if isinstance(t, str) and t.strip():
                    texts.append(t.strip())
            for v in obj.values(): walk(v)
        elif isinstance(obj, list):
            for v in obj: walk(v)
    walk(data)
    if texts: return "\n\n".join(texts)
    return None

def _soup(html: str):
    if not bs4: raise RuntimeError("beautifulsoup4 required")
    try: return BeautifulSoup(html, "lxml")
    except Exception: return BeautifulSoup(html, "html.parser")

def _text_from_node(node) -> str:
    for tag in node(["script","style","noscript","header","footer","nav","aside","form","button"]): tag.decompose()
    return node.get_text(separator="\n")

def extract_dom_smart(html: str) -> Optional[str]:
    soup = _soup(html)
    met = soup.select_one(".meteredContent")
    if met: return _text_from_node(met)
    art = soup.find("article")
    if art: return _text_from_node(art)
    secs = soup.find_all("section")
    if secs:
        best = max(secs, key=lambda s: len(s.get_text(" ", strip=True)))
        return _text_from_node(best)
    divs = soup.find_all("div")
    best_div, best_score = None, 0
    for d in divs[:5000]:
        ps = d.find_all("p")
        score = len(ps) * 200 + len(d.get_text(" ", strip=True))
        if score > best_score: best_score, best_div = score, d
    if best_div: return _text_from_node(best_div)
    if soup.body: return _text_from_node(soup.body)
    return soup.get_text(separator="\n")

def extract_readability(html: str) -> Optional[str]:
    if not Document: return None
    try:
        soup = _soup(Document(html).summary())
        art = soup.find("article") or soup
        return _text_from_node(art)
    except Exception: return None

def extract_trafilatura(html: str) -> Optional[str]:
    if not trafilatura: return None
    try:
        return trafilatura.extract(html, include_links=False, include_tables=False, favor_recall=True)
    except Exception: return None

def extract_greedy_fullpage(html: str) -> Optional[str]:
    soup = _soup(html)
    for tag in soup(["script","style","noscript"]): tag.decompose()
    return soup.get_text(separator="\n")

NAV_NOISE = [
    re.compile(r"^\s*(home|about|contact|subscribe|login|log in|sign in|sign up|get started)\s*$", re.I),
    re.compile(r"^\s*(share|follow|menu|search|privacy|terms|cookies|advertising)\s*$", re.I),
    re.compile(r"^\s*(©|copyright)\s+\d{4}", re.I),
    re.compile(r"^\s*by\s+[\w\s\-]+$", re.I),
    re.compile(r"^\s*\d+\s+min(read| lesen)\s*$", re.I),
]

def clean_text(text: str) -> str:
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"(\n\s*){3,}", "\n\n", text)
    lines = text.split("\n")
    out = []
    for ln in lines:
        s = ln.strip()
        if not s: out.append(""); continue
        if len(s) <= 2: continue
        if any(p.search(s) for p in NAV_NOISE): continue
        if s.count("|") >= 3 or s.count(" • ") >= 2: continue
        out.append(ln)
    return "\n".join(out).strip()

def extract_from_html(html: str, greedy: bool = False) -> str:
    pre = parse_preloaded_state_text(html)
    if pre and len(pre) > 500: return clean_text(pre)
    text = extract_trafilatura(html) or extract_readability(html) or extract_dom_smart(html) or ""
    if greedy or len(text) < 2500:
        g = extract_greedy_fullpage(html)
        if g and len(g) > len(text): text = g
    return clean_text(text or "")

@dataclass
class ResultItem:
    src: str; out: str; ok: bool; length: int; note: str

def _iter_html_files(path: str, recursive: bool, exts=(".html",".htm")):
    if os.path.isfile(path):
        if path.lower().endswith(exts): yield path
        return
    for root, dirs, files in os.walk(path):
        for fn in files:
            if fn.lower().endswith(exts):
                yield os.path.join(root, fn)
        if not recursive: break

def process_path(path: str, out_dir: str, greedy: bool, min_length: int, recursive: bool, suffix: str):
    os.makedirs(out_dir, exist_ok=True)
    report_path = os.path.join(out_dir, "article_fetch_local_report.jsonl")
    with open(report_path, "w", encoding="utf-8") as rep:
        for html_path in _iter_html_files(path, recursive):
            try:
                with open(html_path, "r", encoding="utf-8", errors="ignore") as f: html = f.read()
                text = extract_from_html(html, greedy=greedy)
                length = len(text)
                base = os.path.splitext(os.path.basename(html_path))[0]
                out_txt = os.path.join(out_dir, f"{base}{suffix}.txt")
                note, ok = "ok", True
                if length < min_length:
                    note, ok = f"too short (<{min_length})", False
                with open(out_txt, "w", encoding="utf-8") as g: g.write(text)
                item = ResultItem(src=html_path, out=out_txt, ok=ok, length=length, note=note)
            except Exception as e:
                item = ResultItem(src=html_path, out="", ok=False, length=0, note=f"error: {e}")
            rep.write(_json.dumps(item.__dict__, ensure_ascii=False)+"\n")
    print(f"Report: {report_path}")

def _parse_args():
    ap = argparse.ArgumentParser(description="Lokaler HTML-Fetcher (Datei/Verzeichnis, Bulk, kein Netzwerk)")
    ap.add_argument("--path", required=True, help="Pfad zu HTML-Datei oder Verzeichnis")
    ap.add_argument("--out-dir", required=True, help="Output-Verzeichnis für .txt und Report")
    ap.add_argument("--recursive", action="store_true")
    ap.add_argument("--greedy", action="store_true")
    ap.add_argument("--min-length", type=int, default=200)
    ap.add_argument("--suffix", default="")
    return ap.parse_args()

def main():
    args = _parse_args()
    process_path(args.path, args.out_dir, args.greedy, args.min_length, args.recursive, args.suffix)

if __name__ == "__main__":
    main()
