# tests/test_article_ingestor.py
from ingestion.article_ingestor import map_extraction_to_prompts, SourceMeta

def test_mapping_minimal():
    extraction = {
        "key_takeaways": ["x"],
        "patterns": [
            {
                "name": "Bias Avoidance",
                "intent": "Neutral antworten",
                "structure": "Vergleiche neutral formulieren",
                "guidelines": {"do": ["Fakten"], "dont": ["Suggestivfragen"]},
                "example_prompts": ["Avoid bias and tell me the difference between X and Y"],
                "pitfalls": ["Wertungen"],
                "tags": ["bias", "neutrality"]
            }
        ],
    }
    src = SourceMeta(url="https://ex", title="Artikel")
    out = map_extraction_to_prompts(extraction, src, "enhancement", ["article","pattern"])
    assert len(out) == 1
    rec = out[0]
    assert rec["title"] == "Bias Avoidance"
    assert rec["category"] == "enhancement"
    assert "article" in rec["tags"]
    assert rec["content"].startswith("Avoid bias")
