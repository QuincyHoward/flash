@echo off
REM E4 任务一键运行 (双击)
REM 使用系统 python (含 numpy/scipy/matplotlib/cryptography)
cd /d "%~dp0"
python E4_task.py %*
pause
