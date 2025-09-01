# KPI Pack (fokussiert)

Erfasst drei Kennzahlen ohne Performance-Tests:
1. Pytest-Erfolgsrate (letzte N Läufe, default 20)
2. Errors pro Stunde seit letztem Commit (bis zum ersten grünen Lauf)
3. Runs-to-Green (wie viele Läufe bis grün)

## Installation
- Dateien ins Repo-Root kopieren:
  - tools/kpi_logger.py
  - tools/kpi_report.py
  - (optional) tools/run_tests.cmd

## Verwendung
- Normale Tests: `pytest` (JUnit/HTML müssen bereits nach reports/last geschrieben werden)
- KPIs ansehen: `python tools/kpi_report.py --window 20`
- Optional Wrapper: `toolsun_tests.cmd` (ruft Logger & Report automatisch)

## Artefakte
- reports/kpi_history.csv (Historie)
- reports/kpi_summary.md (Kurzbericht)
