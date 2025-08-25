from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import csv, json

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

from utils.hash_utils import prompt_signature

def _read_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]

def _read_json(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        # either dict of objects or single object
        if "items" in data and isinstance(data["items"], list):
            return list(data["items"])
        return [data]
    if isinstance(data, list):
        return list(data)
    raise ValueError("JSON-Struktur nicht unterstützt (erwartet Liste oder Objekt).")

def _read_yaml(path: Path) -> List[Dict[str, Any]]:
    if yaml is None:
        raise RuntimeError("PyYAML ist nicht installiert. Bitte `pip install PyYAML` ausführen.")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        if "items" in data and isinstance(data["items"], list):
            return list(data["items"])
        return [data]
    if isinstance(data, list):
        return list(data)
    raise ValueError("YAML-Struktur nicht unterstützt (erwartet Liste oder Objekt).")

def load_rows(path: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Liest Datei und liefert (rows, headers)."""
    ext = path.suffix.lower()
    if ext == ".csv":
        rows = _read_csv(path)
    elif ext == ".json":
        rows = _read_json(path)
    elif ext in (".yml", ".yaml"):
        rows = _read_yaml(path)
    else:
        raise ValueError(f"Unbekanntes Format: {ext}")
    headers = []
    for r in rows:
        for k in r.keys():
            if k not in headers:
                headers.append(k)
    return rows, headers

INTERNAL_FIELDS = ["title","description","category","tags","content","sample_output","version","related_ids"]

def map_row(src: Dict[str, Any], mapping: Dict[str, Optional[str]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for field in INTERNAL_FIELDS:
        src_key = mapping.get(field)
        val = src.get(src_key) if src_key else None
        if field == "tags":
            if isinstance(val, str):
                parts = [p.strip() for p in val.replace(";",",").split(",") if p.strip()]
                out[field] = parts
            elif isinstance(val, list):
                out[field] = [str(x).strip() for x in val if str(x).strip()]
            else:
                out[field] = []
        elif field == "related_ids":
            if isinstance(val, str):
                parts = [p.strip() for p in val.replace(";",",").split(",") if p.strip()]
                out[field] = parts
            elif isinstance(val, list):
                out[field] = [str(x).strip() for x in val if str(x).strip()]
            else:
                out[field] = []
        else:
            out[field] = "" if val is None else str(val)
    return out

def analyze(rows: List[Dict[str, Any]], mapping: Dict[str, Optional[str]]) -> Dict[str, Any]:
    mapped = [map_row(r, mapping) for r in rows]
    # Basic validation
    invalid = [m for m in mapped if not (m.get("title") and m.get("content"))]
    return {
        "total": len(rows),
        "mapped": len(mapped),
        "invalid": len(invalid),
    }

def import_rows(repo, rows: List[Dict[str, Any]], mapping: Dict[str, Optional[str]], *, dry_run: bool, skip_duplicates: bool) -> Dict[str, Any]:
    mapped = [map_row(r, mapping) for r in rows]
    added = 0
    dupes = 0
    errors: List[str] = []

    # Build existing signatures
    existing = set()
    for r in repo.all():
        s = prompt_signature(r.get("title",""), r.get("content",""))
        existing.add(s)

    for m in mapped:
        if not (m.get("title") and m.get("content")):
            errors.append(f"Ungültig (fehlende Pflichtfelder): {m.get('title','(ohne Titel)')}")
            continue
        sig = prompt_signature(m.get("title",""), m.get("content",""))
        if skip_duplicates and sig in existing:
            dupes += 1
            continue
        if dry_run:
            added += 1
            continue
        try:
            repo.add(m)
            existing.add(sig)
            added += 1
        except Exception as e:
            errors.append(str(e))

    return {"added": added, "duplicates": dupes, "errors": errors}
