import os, sys

try:
    from ui.ingest_runner import IngestRunner, last_json_line
except ModuleNotFoundError:
    ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    from ui.ingest_runner import IngestRunner, last_json_line


def test_last_json_line():
    text = "noise\n" + '{"a": 1, "db_path": "/tmp/db.json"}' + "\n"
    obj = last_json_line(text)
    assert obj["a"] == 1 and obj["db_path"].endswith("db.json")

def test_build_commands_contains_modules(tmp_path):
    r = IngestRunner(folder=str(tmp_path))
    cmds = r.build_commands()
    flat = " ".join(" ".join(c) for c in cmds)
    assert ("ingestion." in flat) or ("tools." in flat)
