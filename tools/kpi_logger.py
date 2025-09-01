from __future__ import annotations
import csv, os, sys, time, subprocess, argparse
from pathlib import Path
import xml.etree.ElementTree as ET

HISTORY = Path("reports") / "kpi_history.csv"
LAST_JUNIT = Path("reports") / "last" / "junit.xml"

def _git(args):
    try:
        return subprocess.check_output(["git"] + args, text=True).strip()
    except Exception:
        return ""

def parse_junit(path: Path):
    tree = ET.parse(path)
    root = tree.getroot()
    suites = [root] if root.tag.endswith("testsuite") else root.findall(".//testsuite")
    total=failures=errors=skipped=0
    for s in suites:
        total += int(s.attrib.get("tests", 0) or 0)
        failures += int(s.attrib.get("failures", 0) or 0)
        errors += int(s.attrib.get("errors", 0) or 0)
        skipped += int(s.attrib.get("skipped", 0) or 0)
    return total, failures, errors, skipped

def main():
    ap = argparse.ArgumentParser(description="Append KPIs from last junit.xml to kpi_history.csv")
    ap.add_argument("--extra-errors", type=int, default=0, help="Additional errors from tooling/CLI (non-pytest)")
    args = ap.parse_args()

    if not LAST_JUNIT.exists():
        print(f"[kpi_logger] No junit file at {LAST_JUNIT}", file=sys.stderr)
        return 2

    total, failures, errors, skipped = parse_junit(LAST_JUNIT)
    extra = max(int(args.extra_errors or 0), 0)
    total_errors = errors + extra  # used for errors/hour KPI (reporter can choose field)
    passed = total - failures - errors  # pass/fail shouldn't be affected by extra tooling errors
    pass_rate = (passed / total) if total else 0.0
    outcome = "pass" if failures==0 and errors==0 else "fail"

    ts = int(time.time())
    def _git_safe(a):
        try:
            return subprocess.check_output(["git"] + a, text=True).strip()
        except Exception:
            return ""
    commit = _git_safe(["rev-parse", "HEAD"]) or "UNKNOWN"
    commit_time = _git_safe(["show", "-s", "--format=%ct", "HEAD"])
    commit_time = int(commit_time) if commit_time.isdigit() else ts
    branch = _git_safe(["rev-parse", "--abbrev-ref", "HEAD"]) or ""
    subject = _git_safe(["show", "-s", "--format=%s", "HEAD"]) or ""

    row = {
        "timestamp": ts,
        "commit": commit,
        "branch": branch,
        "commit_time": commit_time,
        "total": total,
        "failures": failures,
        "errors": errors,
        "extra_errors": extra,
        "errors_total": total_errors,
        "skipped": skipped,
        "pass_rate": f"{pass_rate:.4f}",
        "outcome": outcome,
        "subject": subject,
    }

    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    write_header = not HISTORY.exists()
    with HISTORY.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header: w.writeheader()
        w.writerow(row)

    print(f"[kpi_logger] recorded: commit={commit[:7]} outcome={outcome} pass_rate={pass_rate:.2%} extra_errors={extra}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
