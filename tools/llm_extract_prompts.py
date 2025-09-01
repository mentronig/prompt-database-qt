# tools/llm_extract_prompts.py
from __future__ import annotations

import os, sys, re, html, json, argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterable

# --------------------------
# Basics & utilities
# --------------------------

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
    # remove script/style/noscript, then tags; keep basic spacing
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

def clean_prompt_text(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    # strip common smart quotes and quotes/surrounding punctuation
    STRIP_CHARS = ' \t“”„‟«»‹›"\'\u201c\u201d\u2018\u2019'
    s = s.strip(STRIP_CHARS)
    return s

def looks_like_prompt(t: str) -> bool:
    if len(t) < 15:
        return False
    if re.search(r'(Act as|Write|Generate|Create|Explain|Draft|Summarize|How|What|Why|Please|Analyze|Suggest|Classify|Compare|Convert|Translate|Outline|Design|Propose|Prompt:)', t, re.I):
        return True
    return bool(re.search(r'[?.!]$', t))

def iter_html_files(path: str, exts: tuple[str, ...] = (".html", ".htm")) -> List[Path]:
    """Return a list of HTML files for a file or a directory (non-recursive).
       If path does not exist, return []. Never raises FileNotFoundError.
    """
    p = Path(path)
    if not p.exists():
        return []
    if p.is_file():
        return [p] if p.suffix.lower() in exts else []
    if p.is_dir():
        return [f for f in p.iterdir() if f.is_file() and f.suffix.lower() in exts]
    return []

# --------------------------
# Heuristics
# --------------------------

def heuristics_extract_prompts_from_html(u: str, max_prompts: int = 400) -> List[Dict[str, str]]:
    # 1) Try list items (common case)
    lis = re.findall(r"<li\b[^>]*>(.*?)</li>", u, re.I|re.S)
    out: List[Dict[str,str]] = []
    for li in lis:
        t = clean_prompt_text(li)
        if looks_like_prompt(t):
            out.append({"title": None, "content": t})
        if len(out) >= max_prompts:
            break
    # 2) Paragraph/numbered split fallback
    if not out:
        body = strip_tags_keep_ws(u)
        parts = re.split(r"(?:\n\s*\d{1,3}\.\s+|\n\s*[-–•]\s+)", body)
        for p in parts:
            t = p.strip()
            if looks_like_prompt(t):
                out.append({"title": None, "content": t})
            if len(out) >= max_prompts:
                break
    return out

# --------------------------
# LLM integration (extract or refine)
# --------------------------

LLM_SYS_EXTRACT = (
    "Extract a list of end-user prompts from the given article text.\n"
    "Return ONLY a JSON array of objects with fields:\n"
    "{\"title\": string (<= 80 chars), \"content\": string (the prompt text)}.\n"
    "No commentary, no markdown code fences.\n"
    "Be exhaustive; do not summarize or merge items."
)

LLM_SYS_REFINE = (
    "You will receive a JSON array named 'items' containing prompt candidates.\n"
    "Return ONLY a JSON array of the SAME LENGTH, with objects:\n"
    "{\"title\": string (<=80 chars), \"content\": string}.\n"
    "- Preserve order.\n"
    "- Do not drop, merge, or add items.\n"
    "- Keep 'content' as-is or lightly cleaned; create concise titles.\n"
    "No commentary, no markdown code fences."
)

def _call_openai_v1(messages: List[Dict[str, str]], model: str, temperature: float = 0.0, verbose: bool=False) -> str:
    from openai import OpenAI  # type: ignore
    client = OpenAI()
    if verbose:
        print("[llm] using openai v1 client (from openai import OpenAI)", file=sys.stderr)
    resp = client.chat.completions.create(model=model, messages=messages, temperature=temperature)
    return resp.choices[0].message.content or ""

def _call_openai_legacy(messages: List[Dict[str, str]], model: str, temperature: float = 0.0, verbose: bool=False) -> str:
    import openai  # type: ignore
    if not getattr(openai, "api_key", None):
        openai.api_key = os.getenv("OPENAI_API_KEY", "")
    if verbose:
        print("[llm] using legacy openai.ChatCompletion API", file=sys.stderr)
    resp = openai.ChatCompletion.create(model=model, messages=messages, temperature=temperature)
    return resp["choices"][0]["message"]["content"]

def call_openai(messages: List[Dict[str, str]], model: str, temperature: float = 0.0, verbose: bool=False) -> str:
    try:
        return _call_openai_v1(messages, model=model, temperature=temperature, verbose=verbose)
    except Exception as e_v1:
        msg = str(e_v1)
        if "No module named 'openai'" in msg or "cannot import name 'OpenAI'" in msg:
            return _call_openai_legacy(messages, model=model, temperature=temperature, verbose=verbose)
        raise RuntimeError(f"OpenAI call failed (v1): {e_v1}")

def parse_llm_json(s: str) -> List[Dict[str, str]]:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.I|re.S)
    if not (s.startswith("[") and s.endswith("]")):
        m = re.search(r"\[[\s\S]+\]", s)
        if m:
            s = m.group(0)
    data = json.loads(s)
    if not isinstance(data, list):
        raise ValueError("LLM did not return a JSON array")
    out: List[Dict[str,str]] = []
    for x in data:
        if not isinstance(x, dict):
            continue
        title = (x.get("title") or "").strip()
        content = (x.get("content") or "").strip()
        if content:
            out.append({"title": title or None, "content": content})
    return out

def llm_extract_prompts(text: str, model: str, temperature: float, truncate_chars: int = 12000, verbose: bool=False) -> List[Dict[str, str]]:
    t = text if truncate_chars <= 0 else text[:truncate_chars]
    messages = [{"role": "system", "content": LLM_SYS_EXTRACT}, {"role": "user", "content": t}]
    raw = call_openai(messages, model=model, temperature=temperature, verbose=verbose)
    return parse_llm_json(raw)

def _chunks(seq: List[Any], size: int) -> Iterable[List[Any]]:
    for i in range(0, len(seq), size):
        yield seq[i:i+size]

def llm_refine_prompts(items: List[Dict[str, str]], model: str, temperature: float, batch_size: int = 120, verbose: bool=False) -> List[Dict[str, str]]:
    """Refine heuristics prompts into titled objects, preserving count and order."""
    refined: List[Dict[str, str]] = []
    for batch in _chunks(items, batch_size):
        user_payload = json.dumps({"items": batch}, ensure_ascii=False)
        messages = [
            {"role": "system", "content": LLM_SYS_REFINE},
            {"role": "user",   "content": user_payload}
        ]
        raw = call_openai(messages, model=model, temperature=temperature, verbose=verbose)
        part = parse_llm_json(raw)
        # Safety: if LLM returns wrong length, fall back to identity mapping for this batch
        if len(part) != len(batch):
            if verbose:
                print(f"[llm-refine-warning] expected {len(batch)} items, got {len(part)} — falling back to heuristic batch.", file=sys.stderr)
            part = [{"title": None, "content": x.get("content","")} for x in batch]
        refined.extend(part)
    return refined

# --------------------------
# JSONL writer
# --------------------------

def _file_url(p: Path) -> str:
    return "file:///" + str(p.resolve()).replace("\\", "/")

def records_for_ingestion(prompts: List[Dict[str, str]], src_file: Path, page_title: Optional[str]) -> List[Dict[str, Any]]:
    lines: List[Dict[str,Any]] = []
    f_url = _file_url(src_file)
    for i, p in enumerate(prompts, start=1):
        title = p.get("title") or f"Prompt {i} — {page_title or src_file.stem}"
        text = p.get("content") or ""
        lines.append({
            "extraction": {
                "title": title,
                "text": text,
                "tags": ["article", "pattern"]
            },
            "meta": {
                "url": f_url,
                "source_title": page_title or src_file.stem
            },
            "source_path": str(src_file)
        })
    return lines

def write_jsonl(lines: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in lines:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

# --------------------------
# CLI
# --------------------------

def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Extract prompts from local HTML using heuristics and/or LLM.")
    ap.add_argument("--path", required=True, help="HTML file or directory (non-recursive)")
    ap.add_argument("--out", default="", help="Output JSONL file (default: <dir>/llm_extract_prompts.jsonl)")
    ap.add_argument("--mode", default="auto", choices=["auto", "heuristic-only", "llm-fallback", "llm-refine"],
                    help="Extraction strategy: 'auto'=heuristics then fallback; 'heuristic-only'=no LLM; 'llm-fallback'=LLM replaces heuristics; 'llm-refine'=LLM enriches heuristics 1:1")
    ap.add_argument("--dry-run", action="store_true", help="No LLM calls in 'auto'/'llm-fallback' (heuristics only)")
    ap.add_argument("--min-prompts", type=int, default=5, help="If heuristics find fewer, call LLM (auto mode)")
    ap.add_argument("--max-prompts", type=int, default=400, help="Cap prompts per file (applies to heuristics before refine)")
    ap.add_argument("--truncate-chars", type=int, default=12000, help="Max input chars for LLM extraction (<=0 means no truncation)")
    ap.add_argument("--model", default="gpt-4o-mini", help="OpenAI model (used only if LLM is called)")
    ap.add_argument("--temperature", type=float, default=0.0, help="LLM temperature")
    ap.add_argument("--refine-batch", type=int, default=120, help="Batch size for llm-refine mode")
    ap.add_argument("--verbose", action="store_true", help="Verbose logs")
    return ap

def main(argv: Optional[List[str]] = None) -> int:
    ap = build_argparser()
    args = ap.parse_args(argv)

    base = Path(args.path)
    files_list = iter_html_files(str(base))
    if not files_list:
        not_found = " (path does not exist)" if not base.exists() else ""
        print(json.dumps({"ok": False, "error": f"No HTML files at: {base}{not_found}"}))
        return 2

    out_path = Path(args.out) if args.out else ((base.parent if base.is_file() else base) / "llm_extract_prompts.jsonl")

    errors = 0
    total_prompts_written = 0
    total_heuristic = 0
    refined_batches = 0

    out_lines: List[Dict[str, Any]] = []

    for f in files_list:
        try:
            raw = read_text_tolerant(f)
            if not raw.strip():
                if args.verbose: print(f"[warn] empty file: {f}", file=sys.stderr)
                continue
            u = unescape_if_needed(raw)
            page_title = find_title(u)

            heur = heuristics_extract_prompts_from_html(u, max_prompts=args.max_prompts)
            total_heuristic += len(heur)
            if args.verbose: print(f"[heuristics] {f.name}: {len(heur)} prompt(s)", file=sys.stderr)

            mode = args.mode
            prompts: List[Dict[str, str]] = []

            if mode == "heuristic-only":
                prompts = heur

            elif mode == "llm-fallback":
                if args.dry-run:
                    prompts = heur
                else:
                    text_for_llm = strip_tags_keep_ws(u)
                    prompts = llm_extract_prompts(text_for_llm, model=args.model,
                                                  temperature=args.temperature,
                                                  truncate_chars=args.truncate_chars,
                                                  verbose=args.verbose)

            elif mode == "llm-refine":
                # Always refine heuristics 1:1 via LLM (if available), else keep heuristics
                if args.dry_run or not heur:
                    prompts = heur
                else:
                    refined = llm_refine_prompts(heur, model=args.model,
                                                 temperature=args.temperature,
                                                 batch_size=args.refine_batch,
                                                 verbose=args.verbose)
                    refined_batches += (len(heur) + args.refine_batch - 1) // args.refine_batch
                    # Safety: ensure we don't lose items
                    if len(refined) != len(heur):
                        if args.verbose:
                            print(f"[llm-refine-warning] refined count {len(refined)} != heuristics {len(heur)} — using heuristics.", file=sys.stderr)
                        prompts = heur
                    else:
                        prompts = refined

            else:  # auto
                if len(heur) >= args.min_prompts or args.dry_run:
                    prompts = heur
                else:
                    text_for_llm = strip_tags_keep_ws(u)
                    prompts = llm_extract_prompts(text_for_llm, model=args.model,
                                                  temperature=args.temperature,
                                                  truncate_chars=args.truncate_chars,
                                                  verbose=args.verbose)

            total_prompts_written += len(prompts)
            out_lines.extend(records_for_ingestion(prompts, f, page_title))

        except Exception as e:
            errors += 1
            if args.verbose: print(f"[error] failed to process: {f}: {e}", file=sys.stderr)

    write_jsonl(out_lines, out_path)
    print(json.dumps({
        "ok": errors == 0,
        "mode": args.mode,
        "files": len(files_list),
        "heuristic_prompts": total_heuristic,
        "final_prompts": total_prompts_written,
        "refined_batches": refined_batches if args.mode == "llm-refine" else 0,
        "errors": errors,
        "jsonl": str(out_path)
    }, ensure_ascii=False))
    return 0 if errors == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
