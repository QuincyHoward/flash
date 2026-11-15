# -*- coding: utf-8 -*-
"""1.6 ns 长跑看护进程：每 10 min 快照 JobID 4946680(16ns 主跑) 与
4946684(ic0509 诊断) 的 SLURM 状态到本地 watch 日志；主跑进入终态后
再快照一次 wsl 日志尾部 + chk 帧数并退出。

用法: python watch_16ns.py            # 前台
      python watch_16ns.py --bg      # 由后台 Bash 调起（无额外行为差异）
"""
import sys
import time
from datetime import datetime
from pathlib import Path

# ★ 可移植：按 pyproject.toml 上溯定位仓库根（parents[N] 层数硬编码会随
#   场景收纳/加深断裂 —— audit R-parents 护栏）
_REPO = Path(__file__).resolve()
for _ in range(12):
    if (_REPO / "pyproject.toml").is_file():
        break
    _REPO = _REPO.parent
else:
    raise RuntimeError("watch_16ns: cannot locate repo root")
sys.path.insert(0, str(_REPO))  # flash 仓库根

from flash.flash_run.remote.executors import SSHExecutor  # noqa: E402
from flash._core.paths import hpc_home_required  # noqa: E402

HERE = Path(__file__).resolve().parent
LOG = HERE / "hpc_run3_16ns_watch.log"
MAIN_JOB = "4946680"
DIAG_JOB = "4946684"
# ★ R-SCENE-06：家目录运行期解析（唯一事实源），绝不硬编码绝对家目录
OBJDIR = f"{hpc_home_required('flash_ssh')}/QC/FLASH/FLASHSNB/FLASH4.8/SNBVTi2um_hot_ug_obj"
TERMINAL = {"COMPLETED", "FAILED", "TIMEOUT", "CANCELLED", "NODE_FAIL"}


def main() -> int:
    ex = SSHExecutor(credential="flash_ssh", verbose=False)
    LOG.write_text(f"# watch start {datetime.now():%F %T}\n", encoding="utf-8")
    for cycle in range(1, 241):  # 上限 240 × 10 min ≈ 40 h
        out, _, _ = ex.run(
            f"squeue -j {MAIN_JOB},{DIAG_JOB} -h -o \"%i %T %M %R\"; "
            f"sacct -j {MAIN_JOB},{DIAG_JOB} --format=JobID,State,Elapsed,"
            f"NodeList%22 --noheader 2>/dev/null | head -6",
            timeout=90,
        )
        line = f"[{datetime.now():%F %T}] cycle={cycle}\n{out.strip()}\n"
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line)
        # 主跑终态 → 抓取收尾信息后退出
        if MAIN_JOB in out:
            for ln in out.splitlines():
                if ln.startswith(MAIN_JOB) and ln.split()[1] in TERMINAL:
                    tail, _, _ = ex.run(
                        f"tail -4 {OBJDIR}/wsl_run_snbonech.log 2>/dev/null; "
                        f"echo CHKCNT=$(ls {OBJDIR} 2>/dev/null | grep -c chk)",
                        timeout=90,
                    )
                    with LOG.open("a", encoding="utf-8") as f:
                        f.write(f"# MAIN_TERMINAL\n{tail}\n")
                    return 0
        time.sleep(600)
    return 0


if __name__ == "__main__":
    sys.exit(main())
