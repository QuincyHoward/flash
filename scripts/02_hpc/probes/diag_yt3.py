#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diag_yt3.py — 验证 ulimit -s unlimited 假设 + ldd 依赖检查。"""
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
SO = f"{TARGET}/.venv-hpc-nce/lib/python3.10/site-packages/yt/geometry/selection_routines.cpython-310-x86_64-linux-gnu.so"
LOG = HERE.parent / "logs" / f"diag_yt3_{datetime.now():%Y%m%d_%H%M%S}.log"
lf = open(LOG, "w", encoding="utf-8", errors="replace")


def w(msg):
    print(msg)
    lf.write(msg + "\n")
    lf.flush()


with RemoteSession("flash_ssh") as s:
    # 1. ★ 核心假设：ulimit -s 8192（8MB）下 yt 能否导入
    out, err, rc = s.run(
        f"bash -c 'ulimit -s 8192; {VPY} -c \"import yt; print(\\\"YT_OK\\\", yt.__version__)\" 2>&1 | tail -3; echo PIPERC=${{PIPESTATUS[0]}}'",
        timeout=300)
    w(f"===== ulimit -s 8192 下 import yt =====\n{(out or '').strip()[-500:]}")

    # 2. 不同栈大小梯度
    for sz in ("2048", "8192", "65536", "unlimited"):
        out, err, rc = s.run(
            f"bash -c 'ulimit -s {sz}; {VPY} -c \"import yt.geometry.selection_routines; print(\\\"OK\\\")\" 2>&1 | tail -1; echo RC=${{PIPESTATUS[0]}}'",
            timeout=300)
        w(f"  ulimit -s {sz:>9}: {((out or '').strip().splitlines() or ['?'])[-1][:120]}")

    # 3. ldd 依赖
    out, err, rc = s.run(f"ldd {SO} 2>&1 | head -12", timeout=120)
    w(f"===== ldd selection_routines =====\n{(out or '').strip()[:900]}")
    out, err, rc = s.run(
        f"strings /lib64/libstdc++.so.6 2>/dev/null | grep -c GLIBCXX_3.4.2 ; "
        f"strings {TARGET}/.venv-hpc-nce/lib/python3.10/site-packages/../../lib/python3.10/site-packages/../../../../lib -r 2>/dev/null | head -1", timeout=60)
    w(f"===== 系统 libstdc++ GLIBCXX_3.4.2x 计数 =====\n{(out or '').strip()[:200]}")
lf.close()
print(f"LOG: {LOG}")
