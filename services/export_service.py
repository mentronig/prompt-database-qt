from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional
import csv, json

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

DEFAULT_FIELDS = [
    "id","title","description","category","tags","version",
    "content","sample_output","related_ids","created_at","updated_at"
]

def _ensure_list_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Make shallow copies to avoid mutating originals for CSV/MD
    out = []
    for r in rows:
        c = dict(r)
        if isinstance(c.get("tags"), list):
            c["tags"] = ", ".join(map(str, c["tags"]))
        if isinstance(c.get("related_ids"), list):
            c["related_ids"] = ", ".join(map(str, c["related_ids"]))
        out.append(c)
    return out

def export_csv(rows: List[Dict[str, Any]], path: Path, fields: Optional[List[str]] = None) -> None:
    fields = fields or DEFAULT_FIELDS
    path.parent.mkdir(parents=True, exist_ok=True)
    rows_norm = _ensure_list_rows(rows)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows_norm:
            w.writerow(r)

def export_markdown(rows: List[Dict[str, Any]], path: Path, fields: Optional[List[str]] = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows_norm = _ensure_list_rows(rows)
    lines: List[str] = []
    if fields:
        # Tabellarische Ausgabe nur mit sichtbaren Feldern
        lines.append("| " + " | ".join(fields) + " |")
        lines.append("| " + " | ".join(["---"] * len(fields)) + " |")
        for r in rows_norm:
            vals = []
            for f in fields:
                v = r.get(f, "")
                if isinstance(v, (list, dict)):
                    v = json.dumps(v, ensure_ascii=False)
                vals.append(str(v).replace("\n", " ").strip())
            lines.append("| " + " | ".join(vals) + " |")
    else:
        # Detaillierte Abschnitte
        lines.append("# Prompts\n")
        for r in rows_norm:
            lines.append(f"## {r.get('title','(ohne Titel)')}")
            lines.append(f"- **ID:** {r.get('id','')}")
            lines.append(f"- **Kategorie:** {r.get('category','')}")
            lines.append(f"- **Tags:** {r.get('tags','')}")
            lines.append(f"- **Version:** {r.get('version','')}")
            desc = (r.get('description') or '').strip()
            if desc:
                lines.append("\n**Beschreibung**\n")
                lines.append("```")
                lines.append(desc)
                lines.append("```")
            content = (r.get('content') or '').strip()
            if content:
                lines.append("\n**Prompt**\n")
                lines.append("```")
                lines.append(content)
                lines.append("```")
            sample = (r.get('sample_output') or '').strip()
            if sample:
                lines.append("\n**Beispielausgabe**\n")
                lines.append("```")
                lines.append(sample)
                lines.append("```")
            lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")

def export_json(rows: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

def export_yaml(rows: List[Dict[str, Any]], path: Path) -> None:
    if yaml is None:
        raise RuntimeError("PyYAML ist nicht installiert. Bitte 'pip install PyYAML' ausführen.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(rows, sort_keys=False, allow_unicode=True), encoding="utf-8")
