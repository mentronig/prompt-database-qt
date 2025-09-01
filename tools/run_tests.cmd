@echo off
setlocal ENABLEDELAYEDEXPANSION

if not exist "reports\last" mkdir "reports\last"

REM 1) Run tests (pytest.ini should write junit/html to reports\last\)
pytest
set TEST_EXIT=%ERRORLEVEL%

REM 2) Run KPI reporter (Ampel). If it fails, count as 1 tooling error.
set TOOL_ERRORS=0
python tools\kpi_report.py --window 20
if ERRORLEVEL 1 set TOOL_ERRORS=1

REM 3) Log KPIs, passing extra tooling errors (does not flip pass/fail, but counts for errors/hour)
python tools\kpi_logger.py --extra-errors %TOOL_ERRORS%

exit /b %TEST_EXIT%
