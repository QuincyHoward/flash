#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diag_yt_segfault.py — 定位 yt 扩展导入段错误的具体模块 + engine_dryrun 细节。"""
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
LOG = HERE.parent / "logs" / f"diag_yt_{datetime.now():%Y%m%d_%H%M%S}.log"
lf = open(LOG, "w", encoding="utf-8", errors="replace")


def w(msg):
    print(msg)
    lf.write(msg + "\n")
    lf.flush()


# 逐个 yt 扩展导入（faulthandler 打印崩溃帧）；ulimit 检查
YT_EXTS = [
    "yt.geometry.selection_routines", "yt.utilities.lib.allocation_container",
    "yt.utilities.lib.bitarray", "yt.geometry.grid_visitors",
    "yt.geometry.oct_container", "yt.geometry.oct_visitors",
    "yt.utilities.lib.partitioned_grid", "yt.utilities.lib.image_samplers",
    "yt.utilities.lib.spheroid_funcs", "yt.utilities.lib.geometry_utils",
    "yt.utilities.lib.bounding_volume_hierarchy", "yt.utilities.lib.marching_cubes",
    "yt.utilities.lib.origami", "yt.utilities.lib.primitives",
    "yt.utilities.lib.pixelization_routines", "yt.utilities.lib.cosmology_time_series",
    "yt.utilities.lib.distance_queue", "yt.utilities.lib.element_wise_smoother",
    "yt.utilities.lib.interpolate", "yt.geometry.particle_deposit",
    "yt.geometry.particle_oct_container", "yt.geometry.grid_container",
]
with RemoteSession("flash_ssh") as s:
    out, err, rc = s.run("ulimit -s; lscpu | grep -o 'avx[0-9a-z]*' | sort -u | tr '\n' ' '; cat /proc/cpuinfo | grep 'model name' | head -1", timeout=60)
    w(f"===== ulimit/cpu =====\n{(out or '').strip()[:400]}")
    w("===== 逐扩展 import =====")
    for m in YT_EXTS:
        out, err, rc = s.run(f"{VPY} -c 'import {m}' 2>&1; echo RC=$?", timeout=120)
        blob = (out or "").strip()
        last = blob.splitlines()[-1] if blob else ""
        if "RC=0" in blob:
            w(f"  [ok  ] {m}")
        else:
            w(f"  [FAIL] {m}: rc_line={last[:120]}")
            if "Segmentation" in blob or "Aborted" in blob or "RC=139" in blob or "RC=134" in blob:
                w(f"         {blob[-400:]}")
    w("===== yt 最低层 import 链 =====")
    out, err, rc = s.run(f"{VPY} -X faulthandler -c 'import yt' 2>&1 | tail -12; echo RC=$?", timeout=300)
    w(((out or "")).strip()[-900:])
    w("===== engine_dryrun 失败细节 =====")
    out, err, rc = s.run(
        f"cd {TARGET} && {VPY} -m pytest test/scenarios/test_engine_dryrun.py::test_engine_dry_run -q --tb=long 2>&1 | tail -30",
        timeout=600)
    w(((out or "") + (err or "")).strip()[-2200:])
    w("===== 部署树 plasma_preparation =====")
    out, err, rc = s.run(
        f"ls {TARGET}/flash/scenarios/public/ ; cd {TARGET} && git log --oneline -1; "
        f"git ls-files flash/scenarios/public/ | head -20", timeout=120)
    w(((out or "")).strip()[:1200])
lf.close()
print(f"LOG: {LOG}")
