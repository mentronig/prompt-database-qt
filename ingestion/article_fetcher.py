
# ingestion/article_fetcher.py (v2.3 – Medium PRELOADED_STATE parser)
from __future__ import annotations
import argparse
import re
import sys
import os
import json as _json
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, List
from urllib.parse import urlparse

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

def _auth_headers_for(url: str) -> Dict[str, str]:
    hdr: Dict[str, str] = {}
    host = urlparse(url).hostname or ""
    medium_cookie = os.getenv("MEDIUM_COOKIE", "").strip()
    if medium_cookie and ("medium.com" in host or host.endswith(".medium.com")):
        hdr["Cookie"] = medium_cookie
    extra = os.getenv("EXTRA_HEADERS_JSON", "").strip()
    if extra:
        try:
            parsed = _json.loads(extra)
            if isinstance(parsed, dict):
                for k, v in parsed.items():
                    if isinstance(k, str) and isinstance(v, str):
                        hdr[k] = v
        except Exception:
            pass
    return hdr

def fetch_url(url: str, timeout: int = 25) -> Tuple[str, str]:
    base_headers = {"User-Agent": DEFAULT_UA, "Accept": "text/html,application/xhtml+xml"}
    headers = {**base_headers, **_auth_headers_for(url)}
    auth = None
    user = os.getenv("BASIC_AUTH_USER", "").strip()
    pwd  = os.getenv("BASIC_AUTH_PASS", "").strip()
    if user and pwd:
        auth = (user, pwd)
    s = requests.Session()
    resp = s.get(url, headers=headers, auth=auth, timeout=timeout, allow_redirects=True)
    resp.raise_for_status()
    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text, str(resp.url)

# ----- PRELOADED_STATE parser (Medium) -----
_PRELOADED_RE = re.compile(
    r'window\\.__PRELOADED_STATE__\\s*=\\s*(\\{.*?\\})\\s*<\\/script>',
    re.DOTALL
)

def parse_preloaded_state_text(html: str) -> Optional[str]:
    m = _PRELOADED_RE.search(html)
    if not m:
        return None
    raw = m.group(1)
    # The JSON can contain escaped unicode; try to load
    try:
        data = _json.loads(raw)
    except Exception:
        # Attempt to repair common issues (unescaped </script> or stray characters)
        fixed = raw.replace('\\n', '\\n').replace('\\r', '\\r')
        try:
            data = _json.loads(fixed)
        except Exception:
            return None
    # Strategy 1: Traverse for Paragraph blocks
    text_blocks: List[str] = []
    def walk(obj):
        if isinstance(obj, dict):
            # Medium often stores paragraphs with __typename == "Paragraph" and a "text" field
            if obj.get("__typename") == "Paragraph":
                t = obj.get("text")
                if isinstance(t, str) and t.strip():
                    text_blocks.append(t.strip())
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
    walk(data)
    if text_blocks:
        # Join with double newline to preserve paragraphs
        return "\\n\\n".join(text_blocks)
    # Strategy 2: Sometimes body is under keys like 'payload'/'references' etc.
    # As a conservative fallback, stringify and extract "text":"..." occurrences from Paragraph-like snippets
    try:
        s = _json.dumps(data, ensure_ascii=False)
        para_texts = re.findall(r'"__typename":"Paragraph".*?"text":"(.*?)"', s, re.DOTALL)
        para_texts = [bytes(t, "utf-8").decode("unicode_escape") for t in para_texts]
        para_texts = [t for t in (p.strip() for p in para_texts) if t]
        if para_texts:
            return "\\n\\n".join(para_texts)
    except Exception:
        pass
    return None

# ----- Other extractors -----
def extract_with_trafilatura(html: str, url: str) -> Optional[str]:
    try:
        import trafilatura
        return trafilatura.extract(html, url=url, include_links=False, include_tables=False, favor_recall=True)
    except Exception:
        return None

def extract_with_readability(html: str) -> Optional[str]:
    try:
        from readability import Document
        from bs4 import BeautifulSoup
        doc = Document(html)
        main_html = doc.summary()
        content_html = getattr(doc, "content", None)
        if callable(content_html):
            try:
                main_html = content_html() or main_html
            except Exception:
                pass
        soup = BeautifulSoup(main_html, "lxml")
        for tag in soup(["script","style","noscript"]):
            tag.decompose()
        main = soup.find("article") or soup
        return main.get_text(separator="\\n")
    except Exception:
        return None

def extract_moderately_bs(html: str) -> Optional[str]:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        # Prefer ".meteredContent" when available (as per JSON-LD hints)
        metered = soup.select_one(".meteredContent")
        if metered:
            for tag in metered(["script","style","noscript","header","footer","nav","aside"]):
                tag.decompose()
            return metered.get_text(separator="\\n")
        # Else try <article> then largest <section>
        art = soup.find("article")
        if art:
            for tag in art(["script","style","noscript","header","footer","nav","aside"]):
                tag.decompose()
            return art.get_text(separator="\\n")
        secs = soup.find_all("section")
        if secs:
            best = max(secs, key=lambda s: len(s.get_text(" ", strip=True)))
            for tag in best(["script","style","noscript","header","footer","nav","aside"]):
                tag.decompose()
            return best.get_text(separator="\\n")
        # Fallback to body
        if soup.body:
            for tag in soup.body(["script","style","noscript","header","footer","nav","aside"]):
                tag.decompose()
            return soup.body.get_text(separator="\\n")
        return soup.get_text(separator="\\n")
    except Exception:
        return None

# ----- Cleaning -----
NAV_NOISE = [
    re.compile(r"^\\s*(home|about|contact|subscribe|login|log in|sign in|sign up|get started)\\s*$", re.I),
    re.compile(r"^\\s*(share|follow|menu|search|privacy|terms|cookies|advertising)\\s*$", re.I),
    re.compile(r"^\\s*(©|copyright)\\s+\\d{4}", re.I),
    re.compile(r"^\\s*by\\s+[\\w\\s\\-]+$", re.I),
    re.compile(r"^\\s*\\d+\\s+min(read| lesen)\\s*$", re.I),
]

def clean_text(text: str) -> str:
    text = re.sub(r"\\r\\n|\\r", "\\n", text)
    text = re.sub(r"(\\n\\s*){3,}", "\\n\\n", text)
    lines = text.split("\\n")
    out: List[str] = []
    for ln in lines:
        s = ln.strip()
        if not s:
            out.append("")
            continue
        if len(s) <= 2:
            continue
        if any(p.search(s) for p in NAV_NOISE):
            continue
        if s.count("|") >= 3 or s.count(" • ") >= 2:
            continue
        out.append(ln)
    return "\\n".join(out).strip()

@dataclass
class FetchResult:
    final_url: str
    length: int
    saved_to: Optional[str]
    preview: str

def _try_extract(html: str, final_url: str, greedy: bool = False) -> str:
    # 0) PRELOADED_STATE (best for Medium)
    pre = parse_preloaded_state_text(html)
    if pre and len(pre) > 1000:
        return clean_text(pre)
    # 1) High-precision extractors
    text = (
        extract_with_trafilatura(html, final_url)
        or extract_with_readability(html)
        or extract_moderately_bs(html)
        or ""
    )
    text = text or ""
    # Greedy fallback when short
    if greedy or len(text) < 2500:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script","style","noscript"]):
            tag.decompose()
        greedy_text = soup.get_text(separator="\\n")
        if greedy_text and len(greedy_text) > len(text):
            text = greedy_text
    return clean_text(text)

def fetch_article_text(url: str, min_length: int = 200, greedy: bool = False) -> Tuple[str, str]:
    html, final_url = fetch_url(url)
    text = _try_extract(html, final_url, greedy=greedy)
    if len(text) < min_length:
        raise ValueError(f"Extrahierter Text zu kurz ({len(text)} < {min_length}). URL: {final_url}")
    return text, final_url

def _parse_args():
    ap = argparse.ArgumentParser(description="Artikeltext aus URL extrahieren (Medium PRELOADED_STATE, Auth, Greedy)")
    ap.add_argument("--url", required=True, help="Ziel-URL des Artikels")
    ap.add_argument("--out", default="", help="Ausgabedatei (z. B. article.txt). Wenn leer, wird nichts gespeichert.")
    ap.add_argument("--min-length", type=int, default=200, help="Mindestlänge des extrahierten Textes (Zeichen)")
    ap.add_argument("--print", action="store_true", help="Extrahierten Text auf STDOUT ausgeben (gekürzt)")
    ap.add_argument("--greedy", action="store_true", help="Erzwinge Greedy-Fallback (ganze Seite auslesen)")
    return ap.parse_args()

def main():
    args = _parse_args()
    try:
        text, final_url = fetch_article_text(args.url, min_length=args.min_length, greedy=args.greedy)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    saved_to = None
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        saved_to = args.out
    preview = text[:900] + ("…" if len(text) > 900 else "")
    safe_preview = preview.replace('"', '\\"')
    print("{")
    print(f' "final_url": "{final_url}",')
    print(f' "length": {len(text)},')
    print(f' "saved_to": "{saved_to or ""}",')
    print(f' "preview": "{safe_preview}"')
    print("}")

if __name__ == "__main__":
    main()
