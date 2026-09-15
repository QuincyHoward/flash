@echo off
REM Create + push the private Gitee repo (credentials are READ-ONLY).
REM Line endings are CRLF on purpose (cmd.exe multi-line blocks).
setlocal
set ROOT=%~dp0..
set VENV=C:\Users\Administrator\.workbuddy\binaries\python\envs\default
set PYEXE=%VENV%\Scripts\python.exe
if not exist "%PYEXE%" (
  echo venv missing, run env_setup.bat first
  pause ^& exit /b 1
)
cd /d "%ROOT%"
"%PYEXE%" scripts\07_gitee_publish.py %*
echo.
pause
