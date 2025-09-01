
"""Tag Normalizer & Alias Mapper (S-001)

- Normalize individual tags (trim, lowercase, de-accent, unify separators)
- Map aliases/synonyms to a canonical tag based on config/tag_aliases.json
- Deduplicate tag lists while preserving the first-seen order
"""
from __future__ import annotations

import json, os, re, unicodedata
from typing import Dict, Iterable, List, Optional, Tuple

_NORMALIZE_NONALNUM = re.compile(r"[^a-z0-9]+")


def _basic_normalize(text: str) -> str:
    if text is None:
        return ""
    t = text.strip().lower()
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    t = _NORMALIZE_NONALNUM.sub(" ", t)
    t = " ".join(t.split())
    return t


class TagNormalizer:
    def __init__(self, alias_path: Optional[str] = None, alias_map: Optional[Dict[str, Iterable[str]]] = None) -> None:
        if alias_map is None:
            alias_path = alias_path or os.environ.get("TAG_ALIAS_PATH", "config/tag_aliases.json")
            if os.path.exists(alias_path):
                with open(alias_path, "r", encoding="utf-8") as f:
                    alias_map = json.load(f)
            else:
                alias_map = {}
        self._canonical_lookup: Dict[str, str] = {}
        for canonical, aliases in alias_map.items():
            norm_canon = _basic_normalize(canonical)
            self._canonical_lookup[norm_canon] = norm_canon
            for a in aliases:
                self._canonical_lookup[_basic_normalize(a)] = norm_canon

    def normalize_tag(self, tag: str) -> str:
        return _basic_normalize(tag)

    def map_alias(self, tag: str) -> str:
        norm = _basic_normalize(tag)
        return self._canonical_lookup.get(norm, norm)

    def canonicalize(self, tag: str) -> str:
        return self.map_alias(self.normalize_tag(tag))

    def normalize_list(self, tags: Iterable[str]):
        seen = set()
        result: List[str] = []
        mapping_log = []
        for t in tags or []:
            final = self.canonicalize(t)
            mapping_log.append((t, final))
            if final and final not in seen:
                seen.add(final)
                result.append(final)
        return result, mapping_log
