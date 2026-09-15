@echo off
REM One-click full pipeline: docs -> inventory -> audit -> Z-bar -> identify
REM -> convert+h5 -> plots -> zero-prior inference -> prune reports -> tests.
REM ASCII-only launcher (Windows cmd GBK safe). CRLF on purpose.
setlocal
set ROOT=%~dp0..
set VENV=C:\Users\Administrator\.workbuddy\binaries\python\envs\default
set PYEXE=%VENV%\Scripts\python.exe
if not exist "%PYEXE%" (
  echo venv missing, run env_setup.bat first
  pause ^& exit /b 1
)
cd /d "%ROOT%"
echo === [1/9] extract docs ===
"%PYEXE%" -m eosop_pro.cli extract-docs
echo === [2/9] inventory ===
"%PYEXE%" -m eosop_pro.cli inventory
echo === [3/9] audit sweep (stage A) ===
"%PYEXE%" -m eosop_pro.cli audit
if errorlevel 1 echo WARNING: audit gate did NOT pass - inspect outputs\reports
echo === [4/9] Z-bar inventory ===
"%PYEXE%" -m eosop_pro.cli zeff
echo === [5/9] declared vs inferred ===
"%PYEXE%" -m eosop_pro.cli identify
echo === [6/9] convert + h5 (dual track) ===
"%PYEXE%" -m eosop_pro.cli convert-all
echo === [7/9] QA plots ===
"%PYEXE%" -m eosop_pro.cli plot-all
echo === [8/9] zero-prior inference on unresolved set ===
"%PYEXE%" -m eosop_pro.cli infer-unknown
echo === [9/10] prune old report batches (keep newest only) ===
"%PYEXE%" -m eosop_pro.cli prune-reports
echo === [10/10] tests ===
"%PYEXE%" test\run_all.py
echo.
echo ALL DONE. see outputs\reports, outputs\plots, outputs\h5, docs\extracted
pause
