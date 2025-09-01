from __future__ import annotations
import csv, sys, time, argparse
from pathlib import Path
from typing import Optional, List, Dict

HISTORY = Path("reports") / "kpi_history.csv"

def load_rows() -> List[Dict[str, str]]:
    if not HISTORY.exists():
        return []
    with HISTORY.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def runs_to_green(rows: List[Dict[str, str]], commit: str) -> Optional[int]:
    crows = [r for r in rows if r.get("commit")==commit]
    if not crows: 
        return None
    for i, r in enumerate(crows, start=1):
        if r.get("outcome") == "pass":
            return i
    return None

def errors_per_hour_since_commit(rows: List[Dict[str, str]], commit: str) -> Optional[float]:
    crows = [r for r in rows if r.get("commit")==commit]
    if not crows: 
        return None
    commit_time = int(crows[0].get("commit_time") or 0)
    now = int(time.time())
    end_time = None
    errs = 0
    for r in crows:
        # prefer errors_total if present, else plain errors
        e = r.get("errors_total") or r.get("errors") or "0"
        errs += int(e)
        if r.get("outcome") == "pass":
            end_time = int(r.get("timestamp") or now)
            break
    if end_time is None:
        end_time = now
    elapsed_h = max((end_time - commit_time) / 3600.0, 1/60)
    return errs / elapsed_h

def pass_rate(rows: List[Dict[str, str]], window: Optional[int]) -> float:
    use = rows[-window:] if window and window>0 else rows
    if not use: 
        return 0.0
    passes = sum(1 for r in use if r.get("outcome")=="pass")
    return passes / len(use)

def ampel_pass_rate(pr: float):
    if pr >= 0.98: return "🟢", "green"
    if pr >= 0.95: return "🟡", "yellow"
    return "🔴", "red"

def ampel_errors_per_hour(eph: Optional[float]):
    if eph is None: return "⚪", "n/a"
    if eph <= 1.0: return "🟢", "green"
    if eph <= 3.0: return "🟡", "yellow"
    return "🔴", "red"

def ampel_runs_to_green(r2g: Optional[int]):
    if r2g is None: return "⚪", "n/a"
    if r2g <= 2: return "🟢", "green"
    if r2g <= 4: return "🟡", "yellow"
    return "🔴", "red"

def main() -> int:
    ap = argparse.ArgumentParser(description="KPIs mit Ampel inkl. tool errors: pass-rate, errors/hour, runs-to-green")
    ap.add_argument("--window", type=int, default=20)
    ap.add_argument("--commit", default=None)
    args = ap.parse_args()

    rows = load_rows()
    if not rows:
        print("No KPI history found.")
        return 2

    last_commit = rows[-1]["commit"]
    commit = args.commit or last_commit

    r2g = runs_to_green(rows, commit)
    eph = errors_per_hour_since_commit(rows, commit)
    pr = pass_rate(rows, args.window)

    e_pr, s_pr = ampel_pass_rate(pr)
    e_eph, s_eph = ampel_errors_per_hour(eph)
    e_r2g, s_r2g = ampel_runs_to_green(r2g)

    print(f"Commit: {commit[:7]}")
    print(f"Pass-rate (last {args.window}): {e_pr} {pr:.0%} [{s_pr}]")
    if eph is not None:
        print(f"Errors/hour since commit: {e_eph} {eph:.2f} [{s_eph}]")
    else:
        print(f"Errors/hour since commit: {e_eph} n/a [{s_eph}]")
    if r2g is not None:
        print(f"Runs to green: {e_r2g} {r2g} [{s_r2g}]")
    else:
        print(f"Runs to green: {e_r2g} n/a [{s_r2g}]")

    lines = [
        "# KPIs", "",
        f"- Commit: `{commit}`",
        f"- Pass-rate (last {args.window}): {e_pr} {pr:.0%} [{s_pr}]",
        f"- Errors/hour since commit: {e_eph} {eph:.2f} [{s_eph}]" if eph is not None else f"- Errors/hour since commit: {e_eph} n/a [{s_eph}]",
        f"- Runs to green: {e_r2g} {r2g} [{s_r2g}]" if r2g is not None else f"- Runs to green: {e_r2g} n/a [{s_r2g}]",
    ]
    out_md = Path("reports") / "kpi_summary.md"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
