from __future__ import annotations

import json
import os
import shutil
from typing import List, Optional

from PySide6.QtCore import QObject, QProcess, Signal


def _which(name: str) -> Optional[str]:
    return shutil.which(name)


def _repo_root_from_here() -> str:
    here = os.path.abspath(__file__)
    ui_dir = os.path.dirname(here)
    root = os.path.dirname(ui_dir)
    return root


def last_json_line(text: str) -> Optional[dict]:
    """
    Return the last parsable JSON object from multi-line text.
    Robust to:
      - real newlines (\\n) and Windows newlines (\\r\\n)
      - literal backslash-n sequences ('\\n') when no real newlines exist
      - noise prefix before the JSON object on the same line
    """
    if not text:
        return None

    stripped = text.strip()
    lines = stripped.splitlines()

    # Fallback: if no real newlines but literal '\n' is present, split on that
    if len(lines) <= 1 and "\\n" in stripped:
        lines = [seg.strip() for seg in stripped.split("\\n")]

    for line in reversed(lines):
        s = line.strip()
        if not s:
            continue
        # Try direct parse
        try:
            return json.loads(s)
        except Exception:
            # Try parsing from the last '{' onwards to drop any prefix noise
            idx = s.rfind("{")
            if idx != -1:
                candidate = s[idx:]
                try:
                    return json.loads(candidate)
                except Exception:
                    pass
    return None


class IngestRunner(QObject):
    """
    Repo-aligned runner for Bulk Ingest (S-002).
    Prefers 'ingestion.*' CLI modules; falls back to 'tools.*'.
    Uses KPI wrapper from 'scripts/' or 'tools/' when available on Windows.
    """
    log = Signal(str)
    started = Signal(str)
    step_finished = Signal(int, int)  # exitCode, step index
    finished = Signal(dict)           # parsed summary JSON
    failed = Signal(int, str)         # exitCode, message

    def __init__(
        self,
        folder: str,
        model: str = "gpt-4o-mini",
        min_prompts: int = 0,
        min_content_len: int = 20,
        default_tags: Optional[str] = None,
        category: Optional[str] = None,
        enable_dedupe: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.folder = os.path.abspath(folder)
        self.model = model
        self.min_prompts = min_prompts
        self.min_content_len = min_content_len
        self.default_tags = default_tags
        self.category = category
        self.enable_dedupe = enable_dedupe

        self._proc: Optional[QProcess] = None
        self._cmds: List[List[str]] = []
        self._stdout_acc = ""

    # -----------------------------
    # Helpers
    # -----------------------------
    def _module_exists(self, dotted: str) -> bool:
        root = _repo_root_from_here()
        path = os.path.join(root, *dotted.split(".")) + ".py"
        return os.path.exists(path)

    def _prefer_module(self, *candidates: str) -> str:
        for mod in candidates:
            if self._module_exists(mod):
                return mod
        return candidates[0]

    def _find_kpi_wrapper(self) -> Optional[str]:
        root = _repo_root_from_here()
        candidates = [
            os.path.join(root, "scripts", "run_with_kpi.cmd"),
            os.path.join(root, "scripts", "run_with_kpi.ps1"),
            os.path.join(root, "tools", "run_with_kpi.cmd"),
            os.path.join(root, "tools", "run_with_kpi.ps1"),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    # -----------------------------
    # Public API
    # -----------------------------
    def build_commands(self) -> List[List[str]]:
        jsonl_path = os.path.join(self.folder, "llm_extract_prompts.jsonl")

        llm_mod = self._prefer_module("ingestion.llm_extract_prompts", "tools.llm_extract_prompts")
        ingest_mod = self._prefer_module("ingestion.ingest_jsonl_to_db", "tools.ingest_jsonl_to_db")
        dedupe_mod = self._prefer_module("ingestion.dedupe_db", "tools.dedupe_db")

        llm_cmd = ["python", "-m", llm_mod, "--path", self.folder, "--mode", "llm-refine", "--model", self.model]
        if self.min_prompts and self.min_prompts > 0:
            llm_cmd += ["--min-prompts", str(self.min_prompts)]

        ingest_cmd = ["python", "-m", ingest_mod, "--path", jsonl_path, "--min-content-len", str(self.min_content_len)]
        if self.default_tags:
            ingest_cmd += ["--default-tags", self.default_tags]
        if self.category:
            ingest_cmd += ["--category", self.category]

        cmds = [llm_cmd, ingest_cmd]

        if self.enable_dedupe:
            cmds.append(["python", "-m", dedupe_mod, "--mode", "content", "--apply"])

        wrapped: List[List[str]] = []
        wrapper = self._find_kpi_wrapper() if os.name == "nt" else None
        if wrapper:
            for c in cmds:
                wrapped.append([wrapper] + c)
            self._cmds = wrapped
        else:
            self._cmds = cmds
        return self._cmds

    def start(self) -> None:
        if not os.path.isdir(self.folder):
            self.failed.emit(2, f"Folder does not exist: {self.folder}")
            return

        if not self._cmds:
            self.build_commands()

        self._stdout_acc = ""
        self._start_next(0)

    def cancel(self) -> None:
        if self._proc:
            self._proc.terminate()

    # -----------------------------
    # Internals
    # -----------------------------
    def _start_next(self, idx: int) -> None:
        if idx >= len(self._cmds):
            summary = last_json_line(self._stdout_acc) or {}
            if "db_path" not in summary:
                summary["db_path"] = os.path.join(_repo_root_from_here(), "data", "prompts.json")
            self.finished.emit(summary)
            return

        cmd = self._cmds[idx]
        self.started.emit(" ".join(cmd))

        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.MergedChannels)
        self._proc.readyReadStandardOutput.connect(self._on_ready_read)
        self._proc.readyReadStandardError.connect(self._on_ready_read)
        self._proc.finished.connect(lambda code, status: self._on_step_finished(code, status, idx))

        self._proc.start(cmd[0], cmd[1:])

    def _on_ready_read(self) -> None:
        if not self._proc:
            return
        out = self._proc.readAllStandardOutput().data().decode("utf-8", errors="replace")
        if not out:
            out = self._proc.readAllStandardError().data().decode("utf-8", errors="replace")
        if out:
            self._stdout_acc += out
            self.log.emit(out)

    def _on_step_finished(self, exitCode: int, _status, idx: int) -> None:
        self.step_finished.emit(exitCode, idx)
        if exitCode != 0:
            self.failed.emit(exitCode, f"Step {idx+1} failed with code {exitCode}")
            return
        self._start_next(idx + 1)
