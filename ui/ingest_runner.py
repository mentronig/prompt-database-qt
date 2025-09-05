from __future__ import annotations
"""
ui.ingest_runner
----------------
Startet den HTML→Prompts→DB Workflow schrittweise in Unterprozessen:

1) Extractor:
   python -m tools.llm_extract_prompts --path <file|folder> --mode <heuristic-only|llm-refine>

   Erwartet eine JSON-Zeile als Summary im STDOUT, z. B.:
   {"ok": true, "jsonl": "C:\\path\\to\\out.jsonl"} oder {"ok": true, "json": "C:\\path\\to\\out.json"}

2) Falls nur .json existiert → JSON→JSONL Konvertierung:
   python -m ui.json_to_jsonl_runner --in <out.json> --out <out.jsonl>

3) Qualitäts-Cleanup der JSONL-Zeilen (HTML-Attribute/Tags/Whitespace säubern):
   python -m tools.clean_jsonl_prompts --in <out.jsonl> --out <out.clean.jsonl>

4) Ingest in die TinyDB:
   python -m tools.ingest_jsonl_to_db --path <out.clean.jsonl>

5) Dedupe:
   python -m tools.dedupe_db --mode content --apply
"""

import os
import json
from pathlib import Path
from typing import List, Optional, Dict

# --- Qt Bindings (PySide6 bevorzugt, PyQt6 Fallback) ---
try:
    from PySide6.QtCore import QObject, QProcess, Signal
except Exception:  # pragma: no cover
    from PyQt6.QtCore import QObject, QProcess  # type: ignore
    from PyQt6.QtCore import pyqtSignal as Signal  # type: ignore


# ---------------- Utils ----------------
def _repo_root() -> Path:
    """Repo-Root ausgehend von dieser Datei bestimmen."""
    here = Path(__file__).resolve()
    return here.parent.parent


def _is_windows() -> bool:
    return os.name == "nt"


def _wrap_cmd(cmd: List[str]) -> List[str]:
    """
    Unter Windows optional mit KPI-Wrapper ausführen, falls vorhanden.
    Erwartet 'tools/run_with_kpi.cmd' im Repo-Root.
    """
    if _is_windows():
        wrapper = _repo_root() / "tools" / "run_with_kpi.cmd"
        if wrapper.exists():
            return [str(wrapper)] + cmd
    return cmd


def last_json_line(text: str) -> Optional[dict]:
    """
    Letzte gültige JSON-Zeile aus einem Log-Text extrahieren.
    Nützlich, falls der Extractor eine JSON-Summary ausgibt.
    """
    if not text:
        return None
    for line in reversed(text.splitlines()):
        s = line.strip()
        if not s:
            continue
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
            try:
                return json.loads(s)
            except Exception:
                continue
    return None


# ---------------- Command Builder ----------------
def build_commands_for_path(
    path: str,
    mode: str = "heuristic-only",
    model: Optional[str] = None,
    min_content_len: Optional[int] = None,
    category: Optional[str] = None,
    default_tags: Optional[List[str]] = None,
) -> List[List[str]]:
    """
    Erzeuge das Startkommando für den Extractor.
    Weitere Schritte (Konvertierung/Cleanup/Ingest/Dedupe) werden
    dynamisch nach der Extractor-Ausgabe ergänzt.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Path not found: {path}")

    cmd1 = ["python", "-m", "tools.llm_extract_prompts", "--path", str(p), "--mode", mode]
    if model:
        cmd1 += ["--model", model]
    # (Optional params sind aktuell für den Extractor nicht zwingend, können aber später ergänzt werden)
    return [_wrap_cmd(cmd1)]


def build_commands_for_file(
    file_path: str,
    mode: str = "heuristic-only",
    model: Optional[str] = None,
    min_content_len: Optional[int] = None,
    category: Optional[str] = None,
    default_tags: Optional[List[str]] = None,
) -> List[List[str]]:
    """Alias für Einzeldatei – entspricht build_commands_for_path."""
    return build_commands_for_path(
        file_path, mode=mode, model=model,
        min_content_len=min_content_len, category=category, default_tags=default_tags
    )


# ---------------- Ingest Runner ----------------
class IngestRunner(QObject):  # pragma: no cover
    """
    Führt den Workflow in Sequenz mit QProcess aus.
    Signale:
      - started(): wenn ein neuer Schritt startet
      - stdout(str), stderr(str): durchgeleitete Prozessausgaben
      - finished(int, dict): Gesamterfolgscode + letzte Summary (falls vorhanden)
    """

    started = Signal()
    stdout = Signal(str)
    stderr = Signal(str)
    finished = Signal(int, dict)  # exitCode, summary

    def __init__(self, parent=None, folder: Optional[str] = None, env: Optional[Dict[str, str]] = None):
        super().__init__(parent)
        self._proc: Optional[QProcess] = None
        self._buffer: List[str] = []
        self._last_json: Optional[dict] = None
        self._workdir = Path(folder) if folder else _repo_root()
        self._env = env or {}
        self._commands: List[List[str]] = []
        self._index: int = 0

    # Hinweis: Die Tests verwenden r.build_commands() nicht – wird hier bewusst NICHT implementiert.
    # def build_commands(self, *args, **kwargs) -> List[List[str]]:
    #     raise NotImplementedError("Use build_commands_for_path/file to create commands externally.")

    # --------- Public API ---------
    def run(self, commands: List[List[str]]):
        if not commands:
            raise ValueError("No commands to run.")
        self._commands = commands
        self._index = 0
        self._buffer.clear()
        self._last_json = None
        self._start_next()

    def terminate(self):
        if self._proc:
            self._proc.terminate()

    # --------- Internals ---------
    def _start_next(self):
        # Ende der Pipeline erreicht
        if self._index >= len(self._commands):
            code = 0
            summary = self._last_json or last_json_line("\n".join(self._buffer)) or {}
            self.finished.emit(code, summary)
            return

        args = self._commands[self._index]
        self._index += 1

        self._proc = QProcess()
        self._proc.setProgram(args[0])
        self._proc.setArguments(args[1:])
        self._proc.setWorkingDirectory(str(self._workdir))

        if self._env:
            env = self._proc.processEnvironment()
            for k, v in self._env.items():
                env.insert(f"{k}={v}")
            self._proc.setProcessEnvironment(env)

        self._proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._proc.readyReadStandardOutput.connect(self._on_read)
        self._proc.readyReadStandardError.connect(self._on_read_err)
        self._proc.finished.connect(self._on_finished_step)
        self.started.emit()
        self._proc.start()

    def _on_read(self):
        if not self._proc:
            return
        data = bytes(self._proc.readAllStandardOutput()).decode(errors="ignore")
        if not data:
            return
        for line in data.splitlines():
            self.stdout.emit(line)
            self._buffer.append(line)
            self._capture_json(line)

    def _on_read_err(self):
        if not self._proc:
            return
        data = bytes(self._proc.readAllStandardError()).decode(errors="ignore")
        if not data:
            return
        for line in data.splitlines():
            self.stderr.emit(line)
            self._buffer.append(line)
            self._capture_json(line)

    def _capture_json(self, line: str):
        s = line.strip()
        if not s or len(s) < 2:
            return
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
            try:
                self._last_json = json.loads(s)
            except Exception:
                pass

    def _on_finished_step(self, exitCode: int, _exitStatus):
        # Schritt fehlgeschlagen → Pipeline beenden
        if exitCode != 0:
            summary = self._last_json or last_json_line("\n".join(self._buffer)) or {}
            self.finished.emit(exitCode, summary)
            return

        # Nach dem 1. Schritt (Extractor) Folgeschritte anhand der Summary einfügen
        if self._index == 1:
            follow = self._build_followup_from_summary()
            # Direkt als nächste Kommandos einfügen
            if follow:
                self._commands[self._index:self._index] = follow

        # Nächster Schritt
        self._start_next()

    def _build_followup_from_summary(self) -> List[List[str]]:
        """
        Lese aus der zuletzt erfassten JSON-Summary den Pfad der Ergebnisdatei (jsonl/json)
        und generiere die nächsten Schritte: json→jsonl (falls nötig), Cleanup, Ingest, Dedupe.
        """
        out_path: Optional[str] = None
        if isinstance(self._last_json, dict):
            # Bevorzugt jsonl, sonst json
            out_path = self._last_json.get("jsonl") or self._last_json.get("json")

        if not out_path:
            return []

        out = Path(out_path)
        cmds: List[List[str]] = []

        # Falls nur .json vorhanden → in .jsonl konvertieren
        ingest_path = out
        if out.suffix.lower() == ".json":
            ingest_path = out.with_suffix(".jsonl")
            cmds.append(["python", "-m", "ui.json_to_jsonl_runner", "--in", str(out), "--out", str(ingest_path)])

        # Qualitäts-Cleanup von JSONL → .clean.jsonl
        cleaned_path = ingest_path.with_name(ingest_path.stem + ".clean.jsonl")
        cmds.append(["python", "-m", "tools.clean_jsonl_prompts", "--in", str(ingest_path), "--out", str(cleaned_path)])
        ingest_path = cleaned_path

        # Ingest in DB
        cmds.append(_wrap_cmd(["python", "-m", "tools.ingest_jsonl_to_db", "--path", str(ingest_path)]))

        # Dedupe
        cmds.append(_wrap_cmd(["python", "-m", "tools.dedupe_db", "--mode", "content", "--apply"]))

        return cmds
