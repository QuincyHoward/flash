#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diag_srun_yt.py — 对比登录节点 vs 计算节点的 yt import（srun 提交即时作业）。"""
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from flash._core.paths import hpc_home_required as _hpc_home_req
_RH = _hpc_home_req()  # 超算家目录：运行期解析，绝不硬编码

from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

TARGET = f"{_RH}/PhySimX/PhySimX/simulation/flash/flash_sim"
VPY = f"{TARGET}/.venv-hpc-nce/bin/python"
LOG = HERE.parent / "logs" / f"diag_srun_{datetime.now():%Y%m%d_%H%M%S}.log"
lf = open(LOG, "w", encoding="utf-8", errors="replace")


def w(msg):
    print(msg)
    lf.write(msg + "\n")
    lf.flush()


with RemoteSession("flash_ssh") as s:
    # 1. 可用分区与账户
    out, err, rc = s.run("sacctmgr show assoc user=$USER format=account,partition,qos -n 2>/dev/null | head -5; sinfo -o '%P %a' -h 2>/dev/null | head -8", timeout=60)
    w(f"===== 分区/账户 =====\n{(out or '').strip()[:600]}")

    # 2. 计算节点上 import yt（srun 即时作业，5 分钟上限）
    out, err, rc = s.run(
        f"srun --account flash_ssh -p NC-E -N 1 -n 1 -t 5 "
        f"bash -c 'source /public1/soft/modules/module.sh 2>/dev/null; module load python/3.10.8; "
        f"uname -r; {VPY} -c \"import yt; print(\\\"COMPUTE_YT_OK\\\", yt.__version__)\" 2>&1 | tail -3' ",
        timeout=420)
    w(f"===== 计算节点 import yt =====\n{(out or '').strip()[-600:]}\n(err) {(err or '').strip()[-300:]}")
lf.close()
print(f"LOG: {LOG}")
