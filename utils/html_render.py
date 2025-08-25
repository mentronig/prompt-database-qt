from __future__ import annotations

from typing import Dict, Any, List
from html import escape

def _badge(text: str) -> str:
    t = escape(text)
    return f'<span style="display:inline-block;margin:2px 6px 2px 0;padding:2px 8px;border-radius:10px;background:#EAF2FF;color:#1F2937;font-size:12px;border:1px solid #D6E4FF;">{t}</span>'

def _mono_block(text: str) -> str:
    t = escape(text)
    return f'<pre style="white-space:pre-wrap;background:#0b12201a;border:1px solid #e5e7eb;border-radius:8px;padding:10px;margin-top:6px;">{t}</pre>'

def render_details(row: Dict[str, Any] | None) -> str:
    if not row:
        return '<div style="color:#6B7280">Kein Eintrag ausgewählt.</div>'
    title = escape(row.get("title","(ohne Titel)"))
    cat = escape(row.get("category",""))
    tags: List[str] = row.get("tags") or []
    desc = row.get("description") or ""
    content = row.get("content") or ""
    sample = row.get("sample_output") or ""

    tag_html = " ".join(_badge(t) for t in tags) if tags else '<span style="color:#9CA3AF">–</span>'

    parts = [
        f'<h2 style="margin:0 0 4px 0;font-size:18px;">{title}</h2>',
        f'<div style="margin:0 0 10px 0;color:#374151;"><strong>Kategorie:</strong> {cat or "–"}</div>',
        f'<div style="margin:0 0 6px 0;"><strong>Tags:</strong> {tag_html}</div>',
    ]
    if desc.strip():
        parts.append('<div style="margin-top:10px;"><strong>Beschreibung</strong></div>')
        parts.append(_mono_block(desc))

    if content.strip():
        parts.append('<div style="margin-top:10px;"><strong>Prompt</strong></div>')
        parts.append(_mono_block(content))

    if sample.strip():
        parts.append('<div style="margin-top:10px;"><strong>Beispielausgabe</strong></div>')
        parts.append(_mono_block(sample))

    return "<div>" + "\n".join(parts) + "</div>"
