@echo off
REM Flash 凭据管理中心 - 双击运行入口
REM 兼容两种模式: standalone (flash) / PhySimX (physimx_sim.flash)
REM
REM 脚本位于 scripts/06_migration/ 下, 向上三级为项目根目录

set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..\..\..\
set CRED_DIR=%ROOT_DIR%flash\_core\credentials\
set PARENT_DIR=%ROOT_DIR%..\

REM 检测是 PhySimX 模式还是 standalone 模式
if exist "%PARENT_DIR%physimx_sim\src" (
    REM PhySimX 模式: 将 physimx_sim/src/ 加入 PYTHONPATH
    set PYTHONPATH=%PARENT_DIR%physimx_sim\src;%PYTHONPATH%
    python -m physimx_sim.flash._core.credentials.manage %*
) else (
    REM standalone 模式: 将项目根目录加入 PYTHONPATH
    set PYTHONPATH=%ROOT_DIR%;%PYTHONPATH%
    python -m flash._core.credentials.manage %*
)

pause
