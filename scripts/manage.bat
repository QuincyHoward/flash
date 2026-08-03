@echo off
REM Flash 凭据管理中心 - 双击运行入口
REM 兼容两种模式: standalone (flash) / PhySimX (physimx_sim.flash)

set SCRIPT_DIR=%~dp0
set CRED_DIR=%SCRIPT_DIR%..\_core\credentials\
set FLASH_DIR=%SCRIPT_DIR%..\..\
set PARENT_DIR=%FLASH_DIR%..\

REM 检测是 PhySimX 模式还是 standalone 模式
if exist "%PARENT_DIR%physimx_sim\src" (
    REM PhySimX 模式: 将 physimx_sim/src/ 加入 PYTHONPATH
    set PYTHONPATH=%PARENT_DIR%physimx_sim\src;%PYTHONPATH%
    python -m physimx_sim.flash._core.credentials.manage %*
) else (
    REM standalone 模式: 将 flash/ 的父目录加入 PYTHONPATH
    set PYTHONPATH=%PARENT_DIR%;%PYTHONPATH%
    python -m flash._core.credentials.manage %*
)

pause
