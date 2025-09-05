"""Prompt repository with absolute DB path + robust schema guard & auto-migration + stable IDs.

- Anchors DB path at repo root (data/prompts.json)
- Reads legacy formats and migrates to {"items": [...]}
- Creates timestamped backups before in-place migration
- Ensures every item has a stable 'id' (uuid4 hex)
- delete() accepts either index (int) OR id (str)
"""
from __future__ import annotations

import json, os, logging, shutil, re, uuid
from typing import Dict, Optional, List, Iterable, Set, Any
from pathlib import Path
from datetime import datetime
from data.tag_normalizer import TagNormalizer

log = logging.getLogger(__name__)


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ts() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


class PromptRepository:
    def __init__(self, db_path: Optional[str] = None, normalizer: Optional[TagNormalizer] = None) -> None:
        env_override = os.environ.get("PROMPT_DB_PATH")
        repo_root = _default_repo_root()

        if env_override:
            path = Path(env_override)
            resolved = path if path.is_absolute() else (repo_root / path).resolve()
            source = "PROMPT_DB_PATH"
        elif db_path is None:
            resolved = (repo_root / "data" / "prompts.json").resolve()
            source = "default@repo_root"
        else:
            path = Path(db_path)
            resolved = path if path.is_absolute() else (repo_root / path).resolve()
            source = "ctor"

        self.db_path = str(resolved)
        self.normalizer = normalizer or TagNormalizer()

        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        if not Path(self.db_path).exists():
            self._write({"items": []})
            log.info("PromptRepository created new DB file at %s (source=%s)", self.db_path, source)
        else:
            self._ensure_schema_on_disk()
            # NEW: ensure every item has a stable id
            added = self._ensure_ids_on_disk()
            if added:
                log.info("DB ensured ids for %d items (db=%s)", added, self.db_path)
            log.info("PromptRepository using DB at %s (source=%s)", self.db_path, source)

    # ----------------- internal IO -----------------
    def _backup_db(self) -> Optional[str]:
        try:
            src = Path(self.db_path)
            if not src.exists():
                return None
            backups = _default_repo_root() / "backups"
            backups.mkdir(parents=True, exist_ok=True)
            dst = backups / f"prompts_{_ts()}.json"
            shutil.copy2(src, dst)
            return str(dst)
        except Exception as e:
            log.warning("DB backup failed: %s", e)
            return None

    def _load_raw(self) -> Any:
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning("Reading DB failed (%s). Resetting to empty schema.", e)
            return {}

    def _normalize_items(self, data: Any) -> List[Dict]:
        """Try to extract a list of items from various legacy layouts."""
        # Standard: {"items": [...]}
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return data["items"]

        # If top-level is already a list of items
        if isinstance(data, list):
            return data

        # Legacy: {"prompts": [...]}
        if isinstance(data, dict) and isinstance(data.get("prompts"), list):
            return data["prompts"]

        # Legacy TinyDB-like: {"prompts": {"1": {...}, "2": {...}}} or {"_default": {"1": {...}}}
        def dict_of_docs_to_list(d: Any) -> Optional[List[Dict]]:
            if isinstance(d, dict) and d and all(isinstance(k, str) and isinstance(v, dict) for k, v in d.items()):
                # Heuristic: keys look like numeric ids
                if all(re.fullmatch(r"\d+", k) for k in d.keys()):
                    return list(d.values())
            return None

        if isinstance(data, dict):
            # Prefer named table "prompts"
            maybe = dict_of_docs_to_list(data.get("prompts"))
            if maybe is not None:
                return maybe
            # Fallback: merge all table-like dicts
            merged: List[Dict] = []
            for v in data.values():
                maybe = dict_of_docs_to_list(v)
                if maybe:
                    merged.extend(maybe)
            if merged:
                return merged

        # Default empty
        return []

    def _ensure_schema_on_disk(self) -> None:
        """Ensure file is a dict with 'items': list. If not, migrate in place with backup."""
        raw = self._load_raw()
        items = self._normalize_items(raw)
        if isinstance(raw, dict) and raw.get("items") == items and isinstance(items, list):
            return  # already normalized

        # Needs migration
        backup = self._backup_db()
        self._write({"items": items})
        log.info("DB auto-migrated to {{'items': [...]}}; backup=%s; count=%d; db=%s", backup, len(items), self.db_path)

    def _read(self) -> Dict:
        raw = self._load_raw()
        if not isinstance(raw, dict):
            raw = {"items": []}
        if "items" not in raw or not isinstance(raw["items"], list):
            # self-heal (unlikely after ensure)
            raw["items"] = self._normalize_items(raw)
            self._write({"items": raw["items"]})
        return raw

    def _write(self, data: Dict) -> None:
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ----------------- ID handling -----------------
    def _ensure_ids_on_disk(self) -> int:
        """Assign uuid4 hex 'id' to any item missing it; persist in place. Returns count added."""
        data = self._read()
        items = data.get("items", [])
        added = 0
        for it in items:
            if isinstance(it, dict) and not it.get("id"):
                it["id"] = uuid.uuid4().hex
                added += 1
        if added:
            self._write(data)
        return added

    def _find_index_by_id(self, id_value: str) -> Optional[int]:
        data = self._read()
        for idx, it in enumerate(data.get("items", [])):
            if isinstance(it, dict) and str(it.get("id", "")) == str(id_value):
                return idx
        return None

    # ----------------- CRUD ------------------------
    def add(self, item: Dict) -> Dict:
        data = self._read()
        before = len(data.get("items", []))
        item = dict(item)
        # ensure id
        if not item.get("id"):
            item["id"] = uuid.uuid4().hex
        # normalize tags
        tags, _ = self.normalizer.normalize_list(item.get("tags", []))
        item["tags"] = tags
        data["items"].append(item)
        self._write(data)
        after = len(data.get("items", []))
        log.info("DB add() ok: %s -> %s items (db=%s)", before, after, self.db_path)
        return item

    def update(self, idx: int, fields: Dict) -> Dict:
        data = self._read()
        item = data["items"][idx]
        for k, v in (fields or {}).items():
            if k == "tags":
                v, _ = self.normalizer.normalize_list(v)
            item[k] = v
        # never drop id
        if not item.get("id"):
            item["id"] = uuid.uuid4().hex
        data["items"][idx] = item
        self._write(data)
        log.info("DB update() idx=%s ok (db=%s)", idx, self.db_path)
        return item

    def delete(self, key: int | str) -> Dict:
        """Delete by index (int) OR by stable id (str). Returns removed item."""
        data = self._read()
        items = data.get("items", [])
        if isinstance(key, int):
            removed = items.pop(key)
            self._write(data)
            log.info("DB delete() idx=%s ok (db=%s)", key, self.db_path)
            return removed
        # else: treat as id
        idx = self._find_index_by_id(str(key))
        if idx is None:
            raise KeyError(f"id not found: {key}")
        removed = items.pop(idx)
        self._write(data)
        log.info("DB delete() id=%s (idx=%s) ok (db=%s)", key, idx, self.db_path)
        return removed

    def get(self, idx: int) -> Dict:
        return self._read()["items"][idx]

    def get_by_id(self, id_value: str) -> Dict:
        idx = self._find_index_by_id(id_value)
        if idx is None:
            raise KeyError(f"id not found: {id_value}")
        return self.get(idx)

    def count(self) -> int:
        c = len(self._read().get("items", []))
        log.debug("DB count() -> %s (db=%s)", c, self.db_path)
        return c

    def bulk_update_from_alias_map(self) -> int:
        data = self._read()
        mutated = 0
        for it in data.get("items", []):
            new_tags, _ = self.normalizer.normalize_list(it.get("tags", []))
            if new_tags != it.get("tags", []):
                it["tags"] = new_tags
                mutated += 1
        if mutated:
            self._write(data)
        log.info("DB reindex aliases -> mutated=%s (db=%s)", mutated, self.db_path)
        return mutated

    # --------------- UI helper methods -------------
    def list_items(self) -> List[Dict]:
        return list(self._read().get("items", []))

    def all(self) -> List[Dict]:
        return self.list_items()

    def all_categories(self) -> List[str]:
        cats: Set[str] = set()
        for it in self._read().get("items", []):
            c = it.get("category") or it.get("Category") or ""
            if isinstance(c, str):
                c = c.strip()
                if c:
                    cats.add(c)
        return sorted(cats)

    def all_tags(self) -> List[str]:
        tags: Set[str] = set()
        for it in self._read().get("items", []):
            for t in it.get("tags", []) or []:
                if isinstance(t, str) and t.strip():
                    tags.add(t.strip())
        return sorted(tags)

    def search(self, query: str = "", tags: Iterable[str] = (), category: str = "") -> List[Dict]:
        q = (query or "").strip().lower()
        tset = {self.normalizer.canonicalize(t) for t in (tags or []) if str(t).strip()}
        cat = (category or "").strip().lower()

        results: List[Dict] = []
        for it in self._read().get("items", []):
            if cat and (str(it.get("category", "")).strip().lower() != cat):
                continue
            item_tags = [self.normalizer.canonicalize(t) for t in (it.get("tags") or [])]
            if tset and not tset.issubset(set(item_tags)):
                continue
            if q:
                hay = " ".join([
                    str(it.get("title", "")),
                    str(it.get("content", "")),
                    str(it.get("category", "")),
                    " ".join(it.get("tags", []) or []),
                ]).lower()
                if q not in hay:
                    continue
            results.append(it)
        return results
