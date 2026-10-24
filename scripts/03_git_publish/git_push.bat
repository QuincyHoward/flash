@echo off
REM Flash Git 推送脚本 - 双击执行
REM ================================
REM 双击运行: 自动提交所有变更 + 推送到远程 (触发 pre-commit / pre-push 钩子)
REM 命令行: git_push.bat [-b branch] [-m "message"] [-f] [-n] [--tag TAG] [--setup] [--status]
REM
REM 参数说明:
REM   (无参数)    自动提交变更 + 推送 Gitee + 同步超算部署仓库
REM   -b branch   推送到指定分支
REM   -m "msg"    自定义提交信息
REM   -f          强制推送
REM   -n          dry-run 模式 (只展示不执行)
REM   --tag TAG   打标签并推送 (先跑测试)
REM   --no-hpc    跳过超算同步 (默认随 Gitee 一并同步; 超算失败仅提示不阻断)
REM   --setup     进入凭据设置 (唯一需要交互的选项)
REM   --status    查看当前 git 状态 (不推送)

cd /d "%~dp0"

echo.
echo  Flash Git 推送工具
echo  ====================
echo.

python git_push.py %*

echo.
pause
