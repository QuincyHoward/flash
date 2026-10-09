@echo off
REM ===============================================================
REM  build_wheelhouse.bat - build offline install package (ONLINE PC)
REM  ASCII only / CRLF - avoid Windows cmd GBK mojibake
REM
REM  Usage: double-click to run (full profile + Python installer)
REM         or: build_wheelhouse.bat --profile runtime --no-interpreter
REM ===============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0..\.."

echo ==============================================================
echo   build_wheelhouse  --  ONLINE machine: make offline package
echo ==============================================================
echo.

REM --- locate python -------------------------------------------------
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY (
    echo [FATAL] python not found in PATH.
    echo         Install Python 3.10+ and tick "Add Python to PATH".
    pause
    exit /b 1
)

echo [info] Using python:
%PY% --version

REM --- run builder ----------------------------------------------------
%PY% scripts\08_offline_install\build_wheelhouse.py %*

set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo ==============================================================
    echo   [OK] wheelhouse built.
    echo.
    echo   NEXT STEPS:
    echo     1. Copy the whole folder to USB:
    echo         offline_pkg\wheelhouse
    echo        ^(include MANIFEST.json - do not copy only .whl files^)
    echo     2. Copy project source too ^(optional but recommended^):
    echo        python scripts\04_backup\usb_backup.py E:\usb_src
    echo     3. On the OFFLINE machine, run install_offline.bat
    echo ==============================================================
) else (
    echo [FAIL] build_wheelhouse exited with code %RC%
)

echo.
pause
endlocal