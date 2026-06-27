@echo off
REM Wrapper de conveniencia (Windows cmd).
REM Uso: decanting <subcomando> [args]
where python3 >nul 2>nul
if %errorlevel%==0 (
  python3 "%~dp0\..\scripts\multiagents.py" %*
) else (
  python "%~dp0\..\scripts\multiagents.py" %*
)
