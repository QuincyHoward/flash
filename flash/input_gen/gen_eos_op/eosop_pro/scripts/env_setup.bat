@echo off
REM Create the managed venv and install deps. Double-clickable. ASCII only.
REM Line endings are CRLF on purpose (cmd.exe multi-line blocks).
setlocal
set VENV=C:\Users\Administrator\.workbuddy\binaries\python\envs\default
set PY=C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe
if not exist "%VENV%\Scripts\python.exe" (
  echo [1/3] creating venv ...
  "%PY%" -m venv "%VENV%"
)
echo [2/3] installing numpy h5py scipy cryptography ...
set PIPEXE=%VENV%\Scripts\pip.exe
"%PIPEXE%" install numpy h5py scipy cryptography
echo [3/3] installing matplotlib (extra retries for flaky networks) ...
"%PIPEXE%" install matplotlib --retries 15 --timeout 180
echo.
echo verify:
set PYEXE=%VENV%\Scripts\python.exe
"%PYEXE%" -c "import numpy,h5py,scipy,cryptography,matplotlib;print('ALL OK')"
echo.
pause
