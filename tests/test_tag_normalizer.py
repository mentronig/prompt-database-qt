
# Ensure project root is on sys.path so `data` and `ingestion` are importable
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.tag_normalizer import TagNormalizer


def test_alias_mapping_ai():
    tn = TagNormalizer(alias_map={"ai":["Artificial Intelligence","KI","Künstliche Intelligenz","A.I."]})
    assert tn.canonicalize("AI") == "ai"
    assert tn.canonicalize("Künstliche Intelligenz") == "ai"


def test_deduplicate_and_order_preservation():
    tn = TagNormalizer(alias_map={"ai":["Artificial Intelligence"],"nlp":["natural language processing"]})
    tags = ["AI","NLP","Artificial Intelligence","natural language processing","ai"]
    normalized, _ = tn.normalize_list(tags)
    assert normalized == ["ai","nlp"]
