
# Ensures project root is importable for tests (so 'ingestion', 'data', etc. can be imported)
# and guarantees the reports/last folder exists for pytest-html & junitxml outputs.
import sys
from pathlib import Path

def pytest_sessionstart(session):
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    (ROOT / "reports" / "last").mkdir(parents=True, exist_ok=True)
