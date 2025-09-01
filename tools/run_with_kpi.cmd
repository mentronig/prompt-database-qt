@echo off
REM Run any command and log nonzero exit as KPI extra-error (if junit exists).
REM Usage: tools\run_with_kpi.cmd python -m ingestion.article_ingestor --file "C:\path\to\file.txt" --source-title "T" --category enhancement --tags "article,pattern"

python tools\kpi_exec.py -- %*
exit /b %ERRORLEVEL%
