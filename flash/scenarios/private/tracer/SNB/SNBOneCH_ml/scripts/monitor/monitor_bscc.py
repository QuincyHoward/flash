"""BSCC 作业 36201968 轮询监控 (低频): 每 30 分钟查一次, 终态即打印 WALL_SECONDS。

修复: 脚本文件运行时 sys.path[0] 是脚本目录, 需手动插入项目根,
否则 remote_ssh_helper 内部 `from flash._core...` 报 ModuleNotFoundError。
"""
import os
import sys
import time

# 结构: layer3/flash (外层根, 含 flash 包) / flash (内层) / scenarios / private /
# tracer / SNB / SNBOneCH_ml <- 本脚本。上溯 5 级 = 内层 flash, 6 级 = 外层根。
_HERE = os.path.dirname(os.path.abspath(__file__))
# 脚本位于 SNBOneCH_ml/scripts/monitor/: 上溯 7 级 = 内层 flash, 8 级 = 外层根
_INNER = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "..", "..", ".."))
_ROOT = os.path.abspath(os.path.join(_INNER, ".."))
sys.path.insert(0, os.path.join(_INNER, "scenarios", "flash_demo", "demo_hpc"))
sys.path.insert(0, _ROOT)

from remote_ssh_helper import quick_run  # noqa: E402

JOB = "36201968"
MAX_POLLS = 26          # 26 次 x 30 分钟 = 13 小时上限
INTERVAL = 1800         # 秒

for i in range(1, MAX_POLLS + 1):
    try:
        out, err, rc = quick_run(
            f"sacct -j {JOB} --format=State,Elapsed --noheader | head -1; "
            f"tail -c 300 ~/SNBOneCH_ml_deploy/run_{JOB}_out.txt",
            credential_name="flash_ssh_2",
            timeout=90,
        )
    except Exception as exc:  # 网络抖动不退出
        print(f"[poll {i}/{MAX_POLLS}] EXC: {exc}", flush=True)
        time.sleep(120)
        continue
    tail = out[-400:]
    print(f"[poll {i}/{MAX_POLLS}] {tail}", flush=True)
    if any(s in tail for s in ("COMPLETED", "FAILED", "TIMEOUT", "CANCELLED")):
        print("MONITOR_DONE", flush=True)
        break
    if i < MAX_POLLS:
        time.sleep(INTERVAL)
else:
    print("MONITOR_TIMEOUT_STILL_RUNNING", flush=True)
