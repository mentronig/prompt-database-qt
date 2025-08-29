# tests/test_article_fetcher.py
from ingestion.article_fetcher import clean_text

def test_clean_text():
    raw = """Line1\n\n\nLine2\n\t\tIndent\n\n\n\nLine3"""
    out = clean_text(raw)
    assert "\n\n\n" not in out
    assert out.startswith("Line1")
    assert out.endswith("Line3")
