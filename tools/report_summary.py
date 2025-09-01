import argparse, xml.etree.ElementTree as ET, datetime, html as _html

def parse_junit(path):
    tree = ET.parse(path); root = tree.getroot()
    suites = [root] if root.tag.endswith("testsuite") else root.findall(".//testsuite")
    total=failures=errors=skipped=0; duration=0.0; cases=[]
    for s in suites:
        total+=int(s.attrib.get("tests",0)); failures+=int(s.attrib.get("failures",0))
        errors+=int(s.attrib.get("errors",0)); skipped+=int(s.attrib.get("skipped",0))
        duration+=float(s.attrib.get("time",0.0) or 0.0)
        for c in s.findall("testcase"):
            name=c.attrib.get("name",""); cls=c.attrib.get("classname",""); t=float(c.attrib.get("time",0.0) or 0.0)
            status="passed"
            if c.find("failure") is not None: status="failure"
            elif c.find("error") is not None: status="error"
            elif c.find("skipped") is not None: status="skipped"
            cases.append((status,cls,name,t))
    return {"total":total,"failures":failures,"errors":errors,"skipped":skipped,"duration":duration,"cases":cases}

def write_md(path, s):
    ok = s["failures"]==0 and s["errors"]==0
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Test Summary ({ts})",
        "",
        f"**Status:** {'✅ Erfolgreich' if ok else '❌ Fehler'} · **Dauer:** {s['duration']:.2f}s · **Tests:** {s['total']}  (F:{s['failures']} E:{s['errors']} S:{s['skipped']})",
        "",
        "## Top 10 Testfälle (nach Dauer)",
        "| Status | Test | Dauer (s) |",
        "|---|---|---:|",
    ]
    for status, cls, name, t in sorted(s["cases"], key=lambda x: x[3], reverse=True)[:10]:
        badge = {"passed":"✅","failure":"❌","error":"⛔","skipped":"↷"}.get(status,status)
        lines.append(f"| {badge} {status} | `{cls}::{name}` | {t:.2f} |")
    with open(path,"w",encoding="utf-8") as f: f.write("\n".join(lines))

def write_html(path, s):
    ok = s["failures"]==0 and s["errors"]==0
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    def esc(x): return _html.escape(str(x))
    rows = []
    for status, cls, name, t in sorted(s["cases"], key=lambda x: x[3], reverse=True)[:10]:
        badge = {"passed":"✅","failure":"❌","error":"⛔","skipped":"↷"}.get(status,status)
        rows.append(f"<tr><td>{badge} {esc(status)}</td><td><code>{esc(cls)}::{esc(name)}</code></td><td style='text-align:right'>{t:.2f}</td></tr>")
    style = "body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Arial,sans-serif;line-height:1.5;margin:2rem;color:#1f2937} table{border-collapse:collapse;width:100%;margin:1rem 0} th,td{border:1px solid #e5e7eb;padding:.4rem .6rem;text-align:left} th{background:#f9fafb} .ok{color:#059669;font-weight:600} .err{color:#dc2626;font-weight:600}"
    html = f"<!doctype html><html lang='de'><meta charset='utf-8'><title>Test Summary</title><style>{style}</style><h1>Test Summary <small style='color:#6b7280'>({esc(ts)})</small></h1><p>Status: <span class='{ 'ok' if ok else 'err' }'>{ 'Erfolgreich' if ok else 'Fehler' }</span> · Dauer: {s['duration']:.2f}s · Tests: {s['total']} (F:{s['failures']} E:{s['errors']} S:{s['skipped']})</p><h2>Top 10 nach Dauer</h2><table><tr><th>Status</th><th>Test</th><th>Dauer (s)</th></tr>{''.join(rows)}</table></html>"
    with open(path,"w",encoding="utf-8") as f: f.write(html)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--junit", required=True)
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--out-html", required=True)
    args = ap.parse_args()
    stats = parse_junit(args.junit)
    write_md(args.out_md, stats)
    write_html(args.out_html, stats)
