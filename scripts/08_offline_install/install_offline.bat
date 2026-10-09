@echo off
REM ===============================================================
REM  install_offline.bat - OFFLINE machine: install from USB
REM  ASCII only / CRLF - avoid Windows cmd GBK mojibake
REM
REM  Usage: double-click to run (auto-detect wheelhouse)
REM         or: install_offline.bat D:\pkg\wheelhouse
REM         or: install_offline.bat --check-only
REM ===============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0..\.."

echo ==============================================================
echo   install_offline  --  OFFLINE machine: install from USB
echo   (no network access needed)
echo ==============================================================
echo.

REM --- locate python -------------------------------------------------
REM Priority: project .venv > system python > py launcher
set "PY="
if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    where py >nul 2>nul && set "PY=py -3"
)
if not defined PY (
    echo.
    echo [FATAL] No Python interpreter found on this machine.
    echo.
    echo   If the USB package contains a Python installer
    echo   ^(offline_pkg\wheelhouse\python-*-amd64.exe^), double-click it
    echo   first and tick "Add Python to PATH". Then run this file again.
    echo.
    pause
    exit /b 1
)

echo [info] Using: %PY%

REM --- run installer --------------------------------------------------
%PY% scripts\08_offline_install\install_offline.py %*

set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo ==============================================================
    echo   [OK] Offline install finished.
    echo   Report   : INSTALL_TEST_REPORT.txt
    echo   Venv     : .venv
    echo   Activate : .venv\Scripts\activate
    echo ==============================================================
) else (
    echo [FAIL] install_offline exited with code %RC%
    echo.
    echo Common causes:
    echo   - wheelhouse incomplete  = copy the WHOLE wheelhouse folder
    echo   - profile mismatch       = rebuild with the same --profile
    echo   - wheel file corrupted   = re-copy from USB, then re-run
)

echo.
pause
endlocal