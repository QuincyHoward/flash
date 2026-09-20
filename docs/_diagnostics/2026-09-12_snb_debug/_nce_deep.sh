#!/bin/bash
# 深挖 NC-E 上 RUNNING 的 4864358 是否真在算
DD=$HOME/QC/SNBOneCH_ml_deploy
echo "=== run.sh ==="
cat "$DD/run.sh" 2>&1
echo
echo "=== build.sh (head 60) ==="
head -60 "$DD/build.sh" 2>&1
echo
echo "=== run_*_err.txt ==="
for f in "$DD"/run_*_err.txt; do echo "--- $f ($(stat -c %s "$f") B) ---"; cat "$f"; echo; done
echo
echo "=== run_4864358_out.txt size + content ==="
ls -la "$DD/run_4864358_out.txt"
wc -c "$DD/run_4864358_out.txt"
echo
echo "=== 作业工作目录 (slurm 实际 cwd) ==="
scontrol show job 4864358 2>&1 | head -40
echo
echo "=== 作业目录下文件 (按时间) ==="
ls -lat "$DD" | head -25
echo
echo "=== 找 4864358 的实际输出 (可能在别处) ==="
find "$HOME" -maxdepth 4 -newermt '2026-09-12 17:24' -type f \
     \( -name '*.log' -o -name 'slurm-*' -o -name '*_out.txt' \) 2>/dev/null | head -30
echo
echo "=== 有无 chk/plt 生成 ==="
find "$DD" -name '*_chk_*' -o -name '*_plt_*' 2>/dev/null | head
echo "(none above = 尚未产生输出)"
echo
echo "=== 节点上进程 ==="
srun --jobid=4864358 --overlap --pty bash -c 'ps -eo pid,pcpu,etime,comm | head -20' 2>&1 | head -25
echo "=== END ==="
