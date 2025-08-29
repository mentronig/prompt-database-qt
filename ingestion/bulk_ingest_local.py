from __future__ import annotations
import argparse, json, os, sys, subprocess, hashlib
from pathlib import Path

def first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s:
            return s
    return ""

def to_file_uri(p: Path) -> str:
    # Windows-kompatibel (file:///C:/path/…)
    abs_p = p.resolve()
    if os.name == "nt":
        return "file:///" + str(abs_p).replace("\\", "/")
    return "file://" + str(abs_p)

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()

def run_ingestor_for_file(txt_path: Path, title: str, category: str, tags: str, dry_run: bool) -> dict:
    file_uri = to_file_uri(txt_path)
    args = [
        sys.executable, "-m", "ingestion.article_ingestor",
        "--file", str(txt_path),
        "--source-url", file_uri,
        "--source-title", title,
        "--category", category,
        "--tags", tags,
    ]
    if dry_run:
        args.append("--dry-run")

    # Aufruf: wir erwarten JSON-Zusammenfassung auf stdout (so wie dein article_ingestor es bereits ausgibt)
    proc = subprocess.run(args, text=True, capture_output=True)
    out = proc.stdout.strip()
    err = proc.stderr.strip()
    ok = (proc.returncode == 0)

    # Versuch: JSON parsen, sonst Rohtext anhängen
    payload = {}
    if out:
        try:
            payload = json.loads(out)
        except Exception:
            payload = {"raw_stdout": out}

    result = {
        "ok": ok,
        "returncode": proc.returncode,
        "stdout": payload,
        "stderr": err,
    }
    return result

def main():
    ap = argparse.ArgumentParser(description="Bulk-Ingest aller .txt in einem Verzeichnis (ruft ingestion.article_ingestor pro Datei).")
    ap.add_argument("--dir", required=True, help="Ordner mit .txt Dateien")
    ap.add_argument("--glob", default="*.txt", help="Dateimuster (Default: *.txt)")
    ap.add_argument("--category", default="local", help="Kategorie für den Ingest")
    ap.add_argument("--tags", default="article,pattern,local", help="Kommagetrennte Tags")
    ap.add_argument("--dry-run", action="store_true", help="Nur Durchlauf testen, nichts speichern")
    ap.add_argument("--max-title-len", type=int, default=120, help="Titel hart kürzen auf diese Länge")
    ap.add_argument("--emit-jsonl", default="", help="Optional: JSONL-Logdatei mit allen Ergebnissen")
    args = ap.parse_args()

    base = Path(args.dir)
    files = sorted(base.rglob(args.glob)) if "**" in args.glob else sorted(base.glob(args.glob))

    if not files:
        print(json.dumps({"ok": False, "files": 0, "note": "keine Dateien gefunden"}, ensure_ascii=False))
        sys.exit(0)

    results = []
    ok_count = 0
    for idx, f in enumerate(files, 1):
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            item = {"file": str(f), "ok": False, "error": f"read_error: {e}"}
            results.append(item)
            continue

        title = first_non_empty_line(txt) or f.stem
        title = title[:args.max_title_len]
        content_hash = sha256_text(txt)

        # Ingest aufrufen
        r = run_ingestor_for_file(f, title=title, category=args.category, tags=args.tags, dry_run=args.dry_run)
        item = {
            "file": str(f),
            "title": title,
            "content_hash": content_hash,
            "ingestor_ok": r["ok"],
            "ingestor_rc": r["returncode"],
            "ingestor_out": r["stdout"],
            "ingestor_err": r["stderr"],
        }
        results.append(item)
        if r["ok"]:
            ok_count += 1

        # Fortschritt auf stdout (ein JSON pro Zeile – gut für die GUI)
        # Infos aus dem Ingestor sammeln (falls vorhanden)
        payload = r.get("ingestor_out") or {}
        saved_ids = []
        for key in ("saved_ids", "inserted_ids", "ids"):
            if isinstance(payload, dict) and key in payload and isinstance(payload[key], list):
                saved_ids = payload[key]
                break
        saved_prompts = payload.get("saved_prompts") if isinstance(payload, dict) else None

        progress_obj = {
            "progress": idx,
            "total": len(files),
            "file": str(f),
            "title": title,                 # <— NEU
            "ok": r["ok"],
            "saved_ids": saved_ids,         # <— NEU (liste von ints/strs, wenn verfügbar)
            "saved_prompts": saved_prompts, # <— NEU (anzahl, wenn verfügbar)
        }
        print(json.dumps(progress_obj, ensure_ascii=False))

        sys.stdout.flush()

    summary = {
        "ok": ok_count == len(files),
        "processed": len(files),
        "succeeded": ok_count,
        "failed": len(files) - ok_count,
    }

    if args.emit_jsonl:
        with open(args.emit_jsonl, "w", encoding="utf-8") as fp:
            for item in results:
                fp.write(json.dumps(item, ensure_ascii=False) + "\n")

    # Abschluss-Summary (GUI kann letzte Zeile lesen)
    print(json.dumps({"summary": summary}, ensure_ascii=False))

if __name__ == "__main__":
    main()
