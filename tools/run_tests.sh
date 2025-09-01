#!/usr/bin/env bash
set -euo pipefail
mkdir -p reports/last
pytest
if [[ "${NO_TIMESTAMP:-0}" != "1" ]]; then
  ts=$(date +"%Y%m%d-%H%M%S"); out="reports/$ts"; mkdir -p "$out"
  cp -r reports/last/* "$out"/
  python tools/report_summary.py --junit "$out/junit.xml" --out-md "$out/summary.md" --out-html "$out/summary.html"
fi
