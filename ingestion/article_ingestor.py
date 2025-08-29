# ingestion/article_ingestor.py (patched v004): robustes Repo-Adapter + Hinweis zu --file/--text
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Callable
import argparse
import hashlib
import json
import os
from datetime import datetime

try:
    from data.prompt_repository import PromptRepository
    HAS_REPO = True
except Exception:
    HAS_REPO = False

def _load_llm_provider():
    try:
        from ingestion.llm_provider import LLMProvider
        return LLMProvider
    except Exception as e:
        raise RuntimeError(f"LLMProvider nicht gefunden: {e}")

DEFAULT_CATEGORY = "enhancement"
DEFAULT_TAGS = ["article", "pattern"]

@dataclass
class SourceMeta:
    url: str | None = None
    title: str | None = None
    author: str | None = None
    published_at: str | None = None

SYSTEM_PROMPT = """Du bist ein Extraktionsassistent.
Lies den gegebenen Artikeltext und extrahiere strukturierte Informationen als reines JSON.
Gib ausschließlich JSON zurück, ohne zusätzliche Erklärungen.
Schema:
{
  "key_takeaways": [ "…" ],
  "patterns": [
    {
      "name": "string",
      "intent": "string",
      "structure": "string",
      "guidelines": {
        "do": ["…"],
        "dont": ["…"]
      },
      "example_prompts": ["…"],
        "pitfalls": ["…"],
        "tags": ["…"]
    }
  ]
}
"""

USER_PROMPT_TEMPLATE = """Artikel:
\"\"\"{article_text}\"\"\"

Aufgabe:
1) Extrahiere 3–10 aussagekräftige "patterns" (siehe Schema).
2) Fülle möglichst viele Felder. Wenn etwas fehlt, lasse es leer oder nutze [].
3) Antworte ausschließlich mit gültigem JSON (ohne Markdown).
"""

def build_user_prompt(article_text: str) -> str:
    return USER_PROMPT_TEMPLATE.format(article_text=article_text.strip())

def hash_article(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def extract_with_llm(article_text: str, provider) -> Dict[str, Any]:
    user_prompt = build_user_prompt(article_text)
    return provider.extract_json(SYSTEM_PROMPT, user_prompt)

def map_extraction_to_prompts(extraction: Dict[str, Any],
                              source: SourceMeta,
                              category: str,
                              tags: List[str]) -> List[Dict[str, Any]]:
    prompts: List[Dict[str, Any]] = []
    patterns = extraction.get("patterns", []) or []
    for p in patterns:
        title = p.get("name") or "Untitled Pattern"
        intent = p.get("intent", "")
        structure = p.get("structure", "")
        guidelines = p.get("guidelines", {})
        do_list = ", ".join(guidelines.get("do", []) or [])
        dont_list = ", ".join(guidelines.get("dont", []) or [])
        pits = p.get("pitfalls", []) or []
        example_prompts = p.get("example_prompts", []) or []

        description_parts = []
        if intent: description_parts.append(f"Intent: {intent}")
        if structure: description_parts.append(f"Struktur: {structure}")
        if do_list or dont_list:
            description_parts.append(f"Guidelines – DO: {do_list} | DONT: {dont_list}")
        if pits:
            description_parts.append("Pitfalls: " + ", ".join(pits))
        src_bits = []
        if source.title: src_bits.append(f"Quelle: {source.title}")
        if source.url: src_bits.append(f"URL: {source.url}")
        if src_bits: description_parts.append(" / ".join(src_bits))
        description = "\n".join(description_parts)

        content = example_prompts[0] if example_prompts else ""
        sample_output = ""
        if len(example_prompts) > 1:
            sample_output = "\n".join(example_prompts[1:])

        merged_tags = list(dict.fromkeys((p.get("tags") or []) + tags))

        prompts.append({
            "title": title,
            "description": description,
            "category": category,
            "tags": merged_tags,
            "content": content,
            "sample_output": sample_output,
        })
    return prompts

def _make_repo_writer(repo) -> Callable[[Dict[str, Any]], None]:
    # 1) add_prompt(title=..., content=..., ...)
    if hasattr(repo, "add_prompt"):
        def _w(rec: Dict[str, Any]):
            repo.add(
                title=rec.get("title",""),
                content=rec.get("content",""),
                description=rec.get("description",""),
                category=rec.get("category",""),
                tags=rec.get("tags",[]),
                sample_output=rec.get("sample_output",""),
                version=rec.get("version",""),
                related_ids=rec.get("related_ids",[]),
            )
        return _w

    # 2) insert_prompt/create_prompt/save_prompt(dict)
    for name in ("insert_prompt","create_prompt","save_prompt"):
        if hasattr(repo, name):
            method = getattr(repo, name)
            def _w(rec: Dict[str, Any], _m=method):
                _m(rec)
            return _w

    # 3) generisch: insert/add/create/upsert(dict)
    for name in ("insert","add","create","upsert"):
        if hasattr(repo, name):
            method = getattr(repo, name)
            def _w(rec: Dict[str, Any], _m=method):
                _m(rec)
            return _w

    def _nope(_rec: Dict[str, Any]):
        raise AttributeError("PromptRepository kennt keine add/insert/create-ähnliche Methode.")
    return _nope

def save_prompts(prompts: List[Dict[str, Any]],
                 article_hash: str,
                 dry_run: bool = False) -> int:
    if dry_run:
        return 0

    if HAS_REPO:
        repo = PromptRepository()
        write = _make_repo_writer(repo)
        count = 0
        try:
            for pr in prompts:
                write(pr)
                count += 1
            return count
        except AttributeError:
            pass  # Fallback auf TinyDB

    from tinydb import TinyDB
    os.makedirs("db", exist_ok=True)
    db = TinyDB("db/prompts.json")
    table = db.table("prompts")
    for pr in prompts:
        pr_rec = {
            **pr,
            "ingestion_article_hash": article_hash,
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
        table.insert(pr_rec)
    return len(prompts)

def run_ingestion(article_text: str,
                  source: SourceMeta,
                  category: str = DEFAULT_CATEGORY,
                  tags: List[str] | None = None,
                  dry_run: bool = False) -> Dict[str, Any]:
    if dry_run:
        extraction = {
            "key_takeaways": ["Demo ohne LLM"],
            "patterns": [{
                "name": "Dummy Pattern",
                "intent": "Testen ohne LLM",
                "structure": "Artikeltext analysieren",
                "guidelines": {"do": ["testen"], "dont": ["produktiv nutzen"]},
                "example_prompts": ["Explain X in simple terms"],
                "pitfalls": ["Kein echtes Ergebnis"],
                "tags": ["dummy","test"]
            }]
        }
    else:
        LLMProvider = _load_llm_provider()
        provider = LLMProvider()
        extraction = extract_with_llm(article_text, provider)

    mapped = map_extraction_to_prompts(extraction, source, category, tags or DEFAULT_TAGS)
    a_hash = hash_article(article_text)
    saved = 0 if dry_run else save_prompts(mapped, a_hash, dry_run=dry_run)
    return {
        "article_hash": a_hash,
        "extracted_patterns": len(extraction.get("patterns", []) or []),
        "mapped_prompts": len(mapped),
        "saved_prompts": saved,
        "dry_run": dry_run,
    }

def _parse_args():
    ap = argparse.ArgumentParser(description="Artikel → Patterns → Prompt-Records")
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--file", type=str, help="Pfad zu einer Textdatei mit dem Artikel")
    grp.add_argument("--text", type=str, help="Artikeltext direkt (String)")
    ap.add_argument("--source-url", type=str, default="", help="Quellen-URL")
    ap.add_argument("--source-title", type=str, default="", help="Quellen-Titel")
    ap.add_argument("--source-author", type=str, default="", help="Autor")
    ap.add_argument("--source-published", type=str, default="", help="ISO-Datum")
    ap.add_argument("--category", type=str, default=DEFAULT_CATEGORY)
    ap.add_argument("--tags", type=str, default="article,pattern")
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()

def main():
    args = _parse_args()
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            article_text = f.read()
    else:
        article_text = args.text or ""

    # Hinweis: Wenn du eine Datei verarbeiten willst, nutze --file Pfad\zur\Datei
    # Beispiel (Windows): python -m ingestion.article_ingestor --file .\Beispiel.txt

    source = SourceMeta(
        url=args.source_url or None,
        title=args.source_title or None,
        author=args.source_author or None,
        published_at=args.source_published or None,
    )
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    result = run_ingestion(
        article_text=article_text,
        source=source,
        category=args.category,
        tags=tags,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
