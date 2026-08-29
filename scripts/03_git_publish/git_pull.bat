@echo off
REM Flash Git 拉取脚本 - 双击执行
REM ================================
REM 双击运行: 自动读取加密凭据 + 从 Gitee 拉取当前分支最新 (--ff-only)
REM 命令行: git_pull.bat [-b branch] [--rebase] [--stash] [-n] [--status] [--setup]
REM
REM 参数说明:
REM   (无参数)    拉取当前分支最新 (快进合并, 干净工作区)
REM   -b branch   拉取指定分支
REM   --rebase    用 rebase 方式拉取 (线性历史)
REM   --stash     有未提交变更时先暂存, 拉取后恢复
REM   -n          dry-run 模式 (只展示不执行)
REM   --status    查看与远端同步状态 (不拉取)
REM   --setup     进入凭据设置 (唯一需要交互的选项)

cd /d "%~dp0"

echo.
echo  Flash Git 拉取工具
echo  ====================
echo.

python git_pull.py %*

echo.
pause
