from __future__ import annotations

import argparse, sys, json as _json, re, html as _html
from dataclasses import dataclass, asdict
from typing import Dict, Iterable, List, Optional
from data.tag_normalizer import TagNormalizer
from data.prompt_repository import PromptRepository
from .article_fetcher import clean_text

@dataclass
class SourceMeta:
    url: Optional[str] = None
    title: Optional[str] = None
    fetched_at: Optional[str] = None
    extractor: Optional[str] = None

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
_STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)

def _looks_like_html(s: str) -> bool:
    if not isinstance(s, str):
        return False
    sniff = s[:200].lower()
    return ("<!doctype" in sniff) or ("<html" in sniff) or ("</p>" in sniff) or ("</div>" in sniff)

def _strip_html(s: str) -> str:
    if not s:
        return s
    s = _SCRIPT_RE.sub(" ", s)
    s = _STYLE_RE.sub(" ", s)
    s = _TAG_RE.sub(" ", s)
    s = _html.unescape(s)
    return s

def _collect_tags(extraction: Dict) -> List[str]:
    tags: List[str] = []
    for key in ("tags", "keywords"):
        val = extraction.get(key)
        if isinstance(val, str):
            tags.extend([p.strip() for p in val.split(",") if p.strip()])
        elif isinstance(val, (list, tuple, set)):
            tags.extend([str(x) for x in val if str(x).strip()])
    patterns = extraction.get("patterns", [])
    if isinstance(patterns, list):
        for p in patterns:
            if isinstance(p, dict) and "tags" in p:
                v = p.get("tags", [])
                if isinstance(v, str):
                    tags.extend([s.strip() for s in v.split(",") if s.strip()])
                elif isinstance(v, (list, tuple, set)):
                    tags.extend([str(x) for x in v if str(x).strip()])
    return tags

def _derive_title(payload: Dict, meta: Optional[SourceMeta]) -> str:
    title = payload.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    patterns = payload.get("patterns", [])
    if isinstance(patterns, list):
        for p in patterns:
            if isinstance(p, dict):
                nm = p.get("name")
                if isinstance(nm, str) and nm.strip():
                    return nm.strip()
    if meta and isinstance(meta.title, str) and meta.title.strip():
        return meta.title.strip()
    return ""

def _derive_content(payload: Dict) -> str:
    text = payload.get("text") or payload.get("content")
    if isinstance(text, str) and text.strip():
        if _looks_like_html(text):
            text = _strip_html(text)
        return clean_text(text)
    parts: List[str] = []
    patterns = payload.get("patterns", [])
    if isinstance(patterns, list):
        for p in patterns:
            if isinstance(p, dict):
                ex = p.get("example_prompts")
                if isinstance(ex, str):
                    parts.append(ex)
                elif isinstance(ex, (list, tuple, set)):
                    parts.extend([str(x) for x in ex if str(x).strip()])
    if parts:
        return clean_text(" ".join(parts))
    kt = payload.get("key_takeaways")
    if isinstance(kt, str):
        return clean_text(kt)
    elif isinstance(kt, (list, tuple, set)):
        return clean_text(" ".join([str(x) for x in kt if str(x).strip()]))
    return ""

def map_extraction_to_prompts(extraction: Dict, meta: Optional[SourceMeta] = None, category: Optional[str] = None, default_tags: Optional[Iterable[str]] = None, normalizer: Optional[TagNormalizer] = None) -> List[Dict]:
    normalizer = normalizer or TagNormalizer()
    payload: Dict = dict(extraction or {})
    title = _derive_title(payload, meta)
    content = _derive_content(payload)
    tags = _collect_tags(payload)
    if default_tags:
        tags.extend(list(default_tags))
    tags, _ = normalizer.normalize_list(tags)
    record = {
        "title": title,
        "content": content,
        "tags": tags,
        "meta": asdict(meta) if meta else {},
    }
    if category:
        record["category"] = str(category)
    return [record]

def _build_argparser():
    ap = argparse.ArgumentParser(description="Map text/extraction to prompts and (optionally) save to DB.")
    ap.add_argument("--file", help="Pfad zu einer Textdatei; Inhalt wird als 'content' benutzt.")
    ap.add_argument("--source-url", default=None)
    ap.add_argument("--source-title", default=None)
    ap.add_argument("--category", default=None)
    ap.add_argument("--tags", default="", help="Kommagetrennte Tags als Default (z. B. 'article,pattern')")
    ap.add_argument("--dry-run", action="store_true", help="Nur Ausgabe JSON, nicht in DB schreiben.")
    return ap

def _from_textfile(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def main_cli(argv: Optional[List[str]] = None) -> int:
    ap = _build_argparser()
    args = ap.parse_args(argv)
    defaults = [t.strip() for t in (args.tags or "").replace(";", ",").split(",") if t.strip()]
    text = _from_textfile(args.file) if args.file else ""
    meta = SourceMeta(url=args.source_url, title=args.source_title)
    extraction = {
        "title": args.source_title or "",
        "text": text,
        "tags": defaults,
        "key_takeaways": [],
        "patterns": [],
    }
    records = map_extraction_to_prompts(extraction, meta, args.category, defaults)
    result = {"ok": True, "saved_prompts": 0, "items": records}
    if args.dry_run:
        sys.stdout.write(_json.dumps(result, ensure_ascii=False))
        return 0
    repo = PromptRepository()
    for rec in records:
        repo.add(rec)
        result["saved_prompts"] += 1
    sys.stdout.write(_json.dumps(result, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main_cli())