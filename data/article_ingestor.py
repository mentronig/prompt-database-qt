"""
Article ingestor that applies tag normalization before persisting.
"""
from __future__ import annotations

from typing import Dict, Tuple, List
from .tag_normalizer import TagNormalizer


def ingest_article(repo, article: Dict, normalizer: TagNormalizer) -> Tuple[Dict, List[Tuple[str, str]]]:
    """Normalize article tags and forward to repository.

    The function is side-effect free for tests, but `repo.add()` will be called if present.

    Args:
        repo: Repository-like object exposing `add(data: Dict)`
        article: Dictionary with (at minimum) an optional 'tags' list
        normalizer: TagNormalizer instance

    Returns:
        (stored_payload, mapping_log)
    """
    article = dict(article or {})
    tags = article.get("tags", [])
    normalized, mapping_log = normalizer.normalize_list(tags)
    article["tags"] = normalized

    # If repo has add(), use it; otherwise, remain a pure transform for testability.
    add = getattr(repo, "add", None)
    if callable(add):
        add(article)

    return article, mapping_log
