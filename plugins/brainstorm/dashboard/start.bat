@echo off
REM Ideation Dashboard launcher (Windows)
REM Serves the run directory's parent so /dashboard/index.html?run=<run_id> works,
REM or — in the default layout — opens this dashboard's index.html directly.

cd /d "%~dp0\.."
start "" http://localhost:8765/dashboard/index.html
python -m http.server 8765
