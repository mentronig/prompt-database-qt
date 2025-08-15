import os, re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from tinydb import TinyDB, Query

def _db_path() -> str:
    return os.getenv("DB_PATH", "data/prompts.json")

def _attach_id(doc) -> Dict[str, Any]:
    d = dict(doc); d["id"] = getattr(doc, "doc_id", None); return d

def _ensure_defaults(item: Dict[str, Any]) -> Dict[str, Any]:
    item.setdefault("description", "")
    item.setdefault("category", "")
    item.setdefault("tags", [])
    item.setdefault("version", "v1.0")
    item.setdefault("sample_output", "")
    item.setdefault("related_ids", [])
    return item

class PromptRepository:
    def __init__(self, path: Optional[str] = None):
        self.db = TinyDB(path or _db_path())
        self.table = self.db.table("prompts")

    def add(self, item: Dict[str, Any]) -> int:
        now = datetime.utcnow().isoformat()
        item = _ensure_defaults(dict(item))
        item.setdefault("created_at", now)
        item["updated_at"] = now
        return self.table.insert(item)

    def update(self, doc_id: int, changes: Dict[str, Any]) -> None:
        changes = _ensure_defaults(dict(changes))
        changes["updated_at"] = datetime.utcnow().isoformat()
        self.table.update(changes, doc_ids=[doc_id])

    def get(self, doc_id: int) -> Optional[Dict[str, Any]]:
        doc = self.table.get(doc_id=doc_id)
        return _attach_id(doc) if doc else None

    def delete(self, doc_id: int) -> None:
        self.table.remove(doc_ids=[doc_id])

    def all(self) -> List[Dict[str, Any]]:
        return [_attach_id(d) for d in self.table.all()]

    def search(self, text: str = "", tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        Q = Query(); cond = None
        if text:
            cond = (
                Q.title.search(re.escape(text), flags=re.I)
                | Q.content.search(re.escape(text), flags=re.I)
                | Q.description.search(re.escape(text), flags=re.I)
                | Q.category.search(re.escape(text), flags=re.I)
            )
        if tags:
            tag_cond = Q.tags.test(lambda t: isinstance(t, list) and set(tags).issubset(set([x.lower() for x in t])))
            cond = tag_cond if cond is None else (cond & tag_cond)
        res = self.table.search(cond) if cond is not None else self.table.all()
        return [_attach_id(d) for d in res]

    def all_categories(self) -> List[str]:
        cats: Set[str] = set()
        for d in self.table.all():
            c = (d.get("category") or "").strip()
            if c:
                cats.add(c)
        return sorted(cats, key=lambda s: s.lower())

    def all_tags(self) -> List[str]:
        tags: Set[str] = set()
        for d in self.table.all():
            for t in d.get("tags", []) or []:
                tnorm = str(t).strip()
                if tnorm:
                    tags.add(tnorm)
        return sorted(tags, key=lambda s: s.lower())
