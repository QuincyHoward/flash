@echo off
REM Step 06: batch QA plots (all-English, PPT grade, DPI >= 450)
REM Double-clickable one-step launcher. ASCII-only (Windows cmd GBK safe).
REM Line endings are CRLF on purpose: cmd.exe wants CRLF for multi-line blocks.
setlocal
set ROOT=%~dp0..
set VENV=C:\Users\Administrator\.workbuddy\binaries\python\envs\default
set PYEXE=%VENV%\Scripts\python.exe
if not exist "%PYEXE%" (
  echo venv missing, run env_setup.bat first
  pause ^& exit /b 1
)
cd /d "%ROOT%"
"%PYEXE%" -m eosop_pro.cli plot-all %*
echo.
pause
