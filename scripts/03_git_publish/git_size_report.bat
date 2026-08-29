@echo off
REM Gitee 分支文件大小统计 - 双击执行
REM ==================================
REM 双击运行: 统计 Gitee master 分支全部文件大小 -> xlsx (按大小降序)
REM 命令行: git_size_report.bat [--ext py,f90] [--path docs/] [--exclude test/]
REM         [--min-size 100KB] [--top 50] [-b branch] [-o out.xlsx]
REM
REM 参数说明:
REM   (无参数)          全库统计, 输出 reports/gitee_file_stats_*.xlsx
REM   --ext py,f90      只统计指定扩展名
REM   --path docs/      只统计指定路径前缀
REM   --exclude test/   排除指定路径前缀
REM   --min-size 100KB  只统计大于等于指定大小
REM   --top 50          只保留排序后前 N 个
REM   --sort path       排序方式 (size_desc/size_asc/path)
REM   -b branch         指定分支 (默认 master)
REM   --setup           进入凭据设置 (唯一需要交互的选项)

cd /d "%~dp0"

echo.
echo  Gitee 分支文件大小统计工具
echo  ============================
echo.

python git_size_report.py %*

echo.
pause
