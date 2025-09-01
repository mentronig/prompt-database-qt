from __future__ import annotations
import argparse, subprocess, sys, time, shlex
from pathlib import Path

JUNIT = Path("reports") / "last" / "junit.xml"
LOGGER = Path("tools") / "kpi_logger.py"
TOOL_HISTORY = Path("reports") / "tool_history.csv"

def main() -> int:
    ap = argparse.ArgumentParser(description="Run any command and log nonzero exit as extra error into KPIs (if junit exists).")
    ap.add_argument("--no-pass-through", action="store_true", help="Do not echo child stdout/stderr (capture only).")
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to run (use -- before the command).")
    args = ap.parse_args()

    if not args.cmd:
        print("Usage: python tools/kpi_exec.py -- <command> [args...]", file=sys.stderr)
        return 2

    # Drop a leading '--' if present (common pattern)
    cmd = args.cmd
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]

    start = time.time()
    try:
        if args.no_pass_through:
            r = subprocess.run(cmd, text=True, capture_output=True)
            # Show a compact view in our console
            sys.stdout.write(r.stdout)
            sys.stderr.write(r.stderr)
        else:
            r = subprocess.run(cmd)
        code = r.returncode
    except FileNotFoundError as e:
        sys.stderr.write(f"[kpi_exec] Command not found: {e}\n")
        code = 127
    except Exception as e:
        sys.stderr.write(f"[kpi_exec] Failed: {e}\n")
        code = 1
    duration = time.time() - start

    # If junit exists, propagate as extra-errors (1 if nonzero else 0)
    logged = False
    if JUNIT.exists() and LOGGER.exists():
        extra = 1 if code != 0 else 0
        try:
            subprocess.run([sys.executable, str(LOGGER), "--extra-errors", str(extra)], check=False)
            logged = True
        except Exception as e:
            sys.stderr.write(f"[kpi_exec] logger failed: {e}\n")

    # Append to tool history (independent from junit)
    TOOL_HISTORY.parent.mkdir(parents=True, exist_ok=True)
    header_needed = not TOOL_HISTORY.exists()
    import csv
    row = {
        "timestamp": int(time.time()),
        "cmd": " ".join(shlex.quote(c) for c in cmd),
        "exit_code": code,
        "duration_s": f"{duration:.3f}",
        "logged_to_kpi": "yes" if logged else "no",
    }
    with TOOL_HISTORY.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if header_needed: w.writeheader()
        w.writerow(row)

    return code

if __name__ == "__main__":
    raise SystemExit(main())
