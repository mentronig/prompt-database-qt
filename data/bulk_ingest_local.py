"""
Bulk local ingestor that reads JSON lines (one article per line) from a file path.

Each article is a dict with optional 'tags' key; tags are normalized before storage.
"""
from __future__ import annotations

import json
from typing import Iterable, Tuple, Dict, List, IO
from .tag_normalizer import TagNormalizer


def _iter_json_lines(fp: IO[str]) -> Iterable[Dict]:
    for line in fp:
        line = line.strip()
        if not line:
            continue
        yield json.loads(line)


def bulk_ingest_from_path(path: str, repo, normalizer: TagNormalizer) -> List[Tuple[Dict, List[Tuple[str, str]]]]:
    results = []
    with open(path, "r", encoding="utf-8") as f:
        for obj in _iter_json_lines(f):
            from .article_ingestor import ingest_article
            stored, log = ingest_article(repo, obj, normalizer)
            results.append((stored, log))
    return results
