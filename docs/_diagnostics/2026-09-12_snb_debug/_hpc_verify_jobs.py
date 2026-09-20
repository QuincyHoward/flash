# -*- coding: utf-8 -*-
"""核实超算上的作业是否真的在执行。

对 NC-E / BSCC 两台机器分别:
  1. `squeue -u $USER`            当前排队/运行作业
  2. `sacct -u $USER -S <today>`  今日所有作业 + 状态 + 已用时长
  3. 统计作业目录下的输出文件数量与总字节数, 4 秒后再测一次 -> 判断是否在增长
  4. `tail` 作业 stdout 最后几行

只读操作, 不下发任何计算。
"""
import io
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_INNER = os.path.abspath(os.path.join(_HERE, "flash"))
sys.path.insert(0, os.path.join(_INNER, "scenarios", "flash_demo", "demo_hpc"))
sys.path.insert(0, _INNER)

from remote_ssh_helper import quick_run  # noqa: E402

OUT = os.path.join(_HERE, "_hpc_verify_jobs.txt")
LOG = io.open(OUT, "w", encoding="utf-8", buffering=1)


def w(s=""):
    print(s, flush=True)
    LOG.write(s + "\n")


# 远端探测脚本 (LF, 通过 printf 写入远端再 bash 执行, 避免嵌套引号)
REMOTE = r"""
echo "=== WHOAMI ==="; whoami; hostname
echo "=== DATE ==="; date
echo "=== SQUEUE ==="; squeue -u $USER 2>&1 | head -30
echo "=== SACCT TODAY ==="
sacct -u $USER -S $(date +%Y-%m-%d)T00:00:00 \
      --format=JobID,JobName%20,State,Elapsed,Start,End,NNodes,NTasks --noheader 2>&1 | head -40
echo "=== DEPLOY DIRS ==="
for d in "$HOME" ; do ls -la "$d" 2>/dev/null | grep -i deploy; done
echo "=== SNBOneCH_ml_deploy ==="
DD="$HOME/QC/SNBOneCH_ml_deploy"
ls -la "$DD" 2>/dev/null | head -40
echo "=== OUT FILE SIZE T0 ==="
find "$HOME" -maxdepth 4 -name 'run_*_out.txt' -printf '%s %p\n' 2>/dev/null | head -20
find "$HOME" -maxdepth 4 -name '*.out' -printf '%s %p\n' 2>/dev/null | head -20
echo "=== CHK/PLT COUNT T0 ==="
find "$HOME" -maxdepth 5 \( -name '*_chk_*' -o -name '*_hdf5_plt_cnt_*' \) 2>/dev/null | wc -l
echo "=== SLEEP 6 ==="; sleep 6
echo "=== OUT FILE SIZE T1 ==="
find "$HOME" -maxdepth 4 -name 'run_*_out.txt' -printf '%s %p\n' 2>/dev/null | head -20
find "$HOME" -maxdepth 4 -name '*.out' -printf '%s %p\n' 2>/dev/null | head -20
echo "=== CHK/PLT COUNT T1 ==="
find "$HOME" -maxdepth 5 \( -name '*_chk_*' -o -name '*_hdf5_plt_cnt_*' \) 2>/dev/null | wc -l
echo "=== TAIL LOGS ==="
for f in $(find "$HOME" -maxdepth 4 -name 'run_*_out.txt' 2>/dev/null | head -5); do
  echo "----- $f -----"; tail -c 600 "$f" 2>/dev/null; echo
done
echo "=== PROBE_END ==="
"""


def probe(account: str) -> None:
    w("\n" + "#" * 78)
    w(f"# 账户 {account}")
    w("#" * 78)
    # 远端脚本以 base64 传输, 彻底规避引号/换行/CRLF 问题
    import base64
    b64 = base64.b64encode(REMOTE.encode("utf-8")).decode("ascii")
    cmd = (f"printf '%s' '{b64}' | base64 -d > /tmp/_probe_$$.sh && "
           f"bash /tmp/_probe_$$.sh; rm -f /tmp/_probe_$$.sh")
    try:
        out, err, rc = quick_run(cmd, credential_name=account, timeout=180)
        w(out or "(空)")
        if err:
            w(f"[stderr] {err[-500:]}")
        w(f"[rc] {rc}")
    except Exception as exc:
        w(f"[EXC] {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    for acct in ("flash_ssh", "flash_ssh_2"):
        try:
            probe(acct)
        except Exception as exc:
            w(f"[FATAL {acct}] {exc}")
    LOG.close()
    print(f"\n>>> 结果写入 {OUT}")
