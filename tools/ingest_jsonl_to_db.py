# tools/ingest_jsonl_to_db.py
from __future__ import annotations

# Ensure repo root on sys.path when executed directly
import sys
from pathlib import Path
from urllib.parse import urlparse, unquote

_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import argparse
import json
from typing import Dict, List, Optional, Any

from data.prompt_repository import PromptRepository
from ingestion.article_ingestor import map_extraction_to_prompts, SourceMeta


def _iter_jsonl_files(path: Path) -> List[Path]:
    if path.is_file():
        return [path]
    files: List[Path] = []
    for pat in ("*.jsonl", "*.ndjson"):
        files.extend(sorted(path.glob(pat)))
    return files


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for ln, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception as e:
                print(f"[ingest_jsonl_to_db] WARN {path}:{ln}: invalid json: {e}", file=sys.stderr)
                continue
            if isinstance(item, dict):
                out.append(item)
    return out


def _coerce_to_extraction(item: Dict[str, Any]):
    """
    Accepts:
      - {"extraction": {...}, "meta": {...}}
      - flat: {"title","text"/"content","tags","url"}
      - alt names: "source_title","source_url","keywords","source_path","src"
    """
    # explicit structure
    if "extraction" in item and isinstance(item["extraction"], dict):
        ext = dict(item["extraction"])
        meta_in = item.get("meta") or {}
        src_path = item.get("source_path") or item.get("src")
        # prefer explicit meta url; else synthesize from src_path if present
        url = meta_in.get("url") or meta_in.get("source_url") or item.get("source_url")
        if not url and src_path:
            url = "file:///" + str(Path(src_path)).replace("\\", "/")
        meta = SourceMeta(
            url=url,
            title=meta_in.get("title") or meta_in.get("source_title") or item.get("source_title"),
            fetched_at=meta_in.get("fetched_at"),
            extractor=meta_in.get("extractor"),
        )
        return ext, meta

    # flat / alt names
    title = item.get("title") or item.get("source_title") or ""
    text = item.get("text") or item.get("content") or ""
    tags = item.get("tags") or item.get("keywords") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.replace(";", ",").split(",") if t.strip()]

    src_path = item.get("source_path") or item.get("src")
    url = item.get("url") or item.get("source_url")
    if not url and src_path:
        url = "file:///" + str(Path(src_path)).replace("\\", "/")

    extraction = {
        "title": title,
        "text": text,
        "tags": tags,
        "key_takeaways": item.get("key_takeaways") or [],
        "patterns": item.get("patterns") or [],
    }
    meta = SourceMeta(
        url=url,
        title=title or item.get("source_title"),
        fetched_at=item.get("fetched_at"),
        extractor=item.get("extractor"),
    )
    return extraction, meta


def _parse_simple_map(spec: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not spec:
        return out
    parts = [p.strip() for p in spec.split(";") if p.strip()]
    for p in parts:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        k = k.strip().lower()
        if not k.startswith("."):
            k = "." + k
        out[k] = v.strip()
    return out


def _parse_tag_map(spec: str) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    if not spec:
        return out
    parts = [p.strip() for p in spec.split(";") if p.strip()]
    for p in parts:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        k = k.strip().lower()
        if not k.startswith("."):
            k = "." + k
        tags = [t.strip() for t in v.replace(";", ",").split(",") if t.strip()]
        out[k] = tags
    return out


def _ext_from_meta(meta: SourceMeta, row: Dict[str, Any]) -> Optional[str]:
    """
    Derive extension from:
      1) row['source_path'] or row['src'] (local path)
      2) meta.url if file:// or path-like
    """
    # 1) explicit local keys
    for key in ("source_path", "src"):
        sp = row.get(key)
        if isinstance(sp, str) and sp:
            try:
                suf = Path(sp).suffix.lower()
                if suf:
                    return suf
            except Exception:
                pass

    # 2) meta.url
    url = getattr(meta, "url", None)
    if isinstance(url, str) and url:
        try:
            u = urlparse(url)
            if u.scheme in ("file", ""):
                path_str = unquote(u.path) if u.scheme == "file" else url
                if path_str.startswith("/") and len(path_str) > 2 and path_str[2] == ":":
                    path_str = path_str[1:]
                suf = Path(path_str).suffix.lower()
                if suf:
                    return suf
        except Exception:
            pass
    return None


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Ingest JSONL (e.g., article_fetcher_local output) into prompts DB.")
    ap.add_argument("--path", required=True, help="File or directory with *.jsonl/ndjson")
    ap.add_argument("--category", default=None, help="Category to assign to all records (fallback if none set elsewhere)")
    ap.add_argument("--default-tags", default="", help="Default tags to add (comma-separated)")
    ap.add_argument("--dry-run", action="store_true", help="Do not write to DB; just print summary")
    ap.add_argument("--verbose", action="store_true", help="Verbose logging")
    ap.add_argument("--min-content-len", type=int, default=30, help="Skip records whose cleaned content is shorter than N characters (default: 30)")
    ap.add_argument("--map", dest="ext_category_map", default="",
                    help="Extension to category mapping, e.g. \".md=note;.html=enhancement\"")
    ap.add_argument("--tag-map", dest="ext_tag_map", default="",
                    help="Extension to additional tags, e.g. \".md=article,notes;.html=article,pattern\"")
    ap.add_argument("--map-overwrite", action="store_true",
                    help="Overwrite category/tags from data with mapped values (default: False = only fill if empty)")
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    ap = build_argparser()
    args = ap.parse_args(argv)

    base = Path(args.path).expanduser()
    files = _iter_jsonl_files(base)
    if not files:
        print(f"[ingest_jsonl_to_db] No JSONL files found at: {base}", file=sys.stderr)
        return 2

    defaults = [t.strip() for t in (args.default_tags or "").replace(";", ",").split(",") if t.strip()]
    repo = PromptRepository()

    cat_map = _parse_simple_map(args.ext_category_map)
    tag_map = _parse_tag_map(args.ext_tag_map)

    total_lines = 0
    saved = 0
    errors = 0
    skipped = 0
    skipped_short = 0
    applied_cat = 0
    applied_tags = 0

    for fp in files:
        rows = _read_jsonl(fp)
        if args.verbose:
            print(f"[ingest_jsonl_to_db] Reading {fp} … {len(rows)} rows", file=sys.stderr)
        total_lines += len(rows)
        for row in rows:
            try:
                extraction, meta = _coerce_to_extraction(row)
                records = map_extraction_to_prompts(extraction, meta, args.category, defaults)
                if not records:
                    skipped += 1
                    continue

                # Determine extension once per row/meta
                ext = _ext_from_meta(meta, row)

                # Apply ext→category/tags mapping on each record
                for rec in records:
                    if ext:
                        # category mapping
                        mapped_cat = cat_map.get(ext)
                        if mapped_cat:
                            if args.map_overwrite or not rec.get("category"):
                                rec["category"] = mapped_cat
                                applied_cat += 1
                        # tag mapping
                        mapped_tags = tag_map.get(ext) or []
                        if mapped_tags:
                            if args.map_overwrite:
                                rec["tags"] = mapped_tags[:]
                                applied_tags += 1
                            else:
                                old = list(rec.get("tags") or [])
                                for t in mapped_tags:
                                    if t not in old:
                                        old.append(t)
                                if old != rec.get("tags"):
                                    applied_tags += 1
                                rec["tags"] = old

                # Filter by cleaned content length (after mapping/sanitizing)
                filtered = []
                for rec in records:
                    content = (rec.get("content") or "").strip()
                    if len(content) < args.min_content_len:
                        skipped_short += 1
                        continue
                    filtered.append(rec)

                if not filtered:
                    continue

                if not args.dry_run:
                    for rec in filtered:
                        repo.add(rec)
                saved += len(filtered)

            except Exception as e:
                print(f"[ingest_jsonl_to_db] ERROR {fp.name}: {e}", file=sys.stderr)
                errors += 1

    summary = {
        "ok": errors == 0,
        "files": len(files),
        "lines": total_lines,
        "saved_prompts": saved,
        "skipped": skipped,
        "skipped_short": skipped_short,
        "errors": errors,
        "min_content_len": args.min_content_len,
        "applied_category_mappings": applied_cat,
        "applied_tag_mappings": applied_tags,
    }
    import json as _json
    sys.stdout.write(_json.dumps(summary, ensure_ascii=False))
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
