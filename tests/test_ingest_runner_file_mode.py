import os, sys
from ui.ingest_runner import build_commands_for_file, _is_windows

def test_build_commands_for_file_basic(tmp_path):
    f = tmp_path / "sample.html"
    f.write_text("<html><body>hi</body></html>", encoding="utf-8")
    cmds = build_commands_for_file(str(f))
    assert len(cmds) == 3
    # first command must call tools.llm_extract_prompts
    joined0 = " ".join(cmds[0])
    assert "python" in joined0 and "tools.llm_extract_prompts" in joined0
    # second command ingests the produced jsonl
    joined1 = " ".join(cmds[1])
    assert "tools.ingest_jsonl_to_db" in joined1
