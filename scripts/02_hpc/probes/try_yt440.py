#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""try_yt440.py — 上传 yt 4.4.0 实测 + ensure_sim_input 文件式探针（避免引号剥离）。"""
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST_DIR = HERE.parent
REPO_ROOT = TEST_DIR.parents[1]  # 02_hpc → scripts → 仓库根
CAND = TEST_DIR / "packages" / "yt_candidates"
sys.path.insert(0, str(REPO_ROOT))
from flash._core.paths import hpc_home_required as _hpc_home_req
_RH = _hpc_home_req()  # 超算家目录：运行期解析，绝不硬编码

from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

TARGET = f"{_RH}/PhySimX/PhySimX/simulation/flash/flash_sim"
PKG = f"{_RH}/PhySimX/PhySimX/simulation/flash/flash_sim_pkg"
WH = f"{PKG}/wheelhouse-linux"
VPY = f"{TARGET}/.venv-hpc-nce/bin/python"
PIP = f"{TARGET}/.venv-hpc-nce/bin/pip"
LOG = TEST_DIR / "logs" / f"try_yt440_{datetime.now():%Y%m%d_%H%M%S}.log"
lf = open(LOG, "w", encoding="utf-8", errors="replace")


def w(msg):
    print(msg)
    lf.write(msg + "\n")
    lf.flush()


# 文件式探针（上传后远端执行，无引号问题）
PROBE_SIM = """import traceback
from flash.scenarios.core.registry import get_scenario
sc = get_scenario('ch_center')
print('sim_input_dir:', sc.sim_input_dir)
try:
    sc.ensure_sim_input()
    import pathlib
    names = sorted(p.name for p in pathlib.Path(sc.sim_input_dir).iterdir())
    print('GENERATED_COUNT:', len(names))
    print('GENERATED:', names[:10])
except BaseException:
    traceback.print_exc()
"""

with RemoteSession("flash_ssh") as s:
    whl = CAND / "yt-4.4.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
    ok = s.upload(str(whl), f"{WH}/{whl.name}")
    w(f"[upload] {whl.name}: {'OK' if ok else 'FAIL'}")

    out, err, rc = s.run(
        f"{PIP} install --no-index --find-links {WH} "
        f"--force-reinstall --no-deps yt==4.4.0 2>&1 | tail -1", timeout=600)
    w(f"[install yt==4.4.0] {(out or '').strip()[-120:]}")

    out, err, rc = s.run(
        f"{VPY} -c 'import yt; print(\"YT_OK\", yt.__version__)' 2>&1; echo RC=$?",
        timeout=300)
    w(f"[import yt==4.4.0] {(out or '').strip()[-200:]}")

    if "YT_OK" in (out or ""):
        # yt 成功 → 全量依赖健康探针 + 三套测试
        probe_health = (
            "import importlib\n"
            "mods = ['pytest','pluggy','iniconfig','packaging','pygments','numpy',"
            "'scipy','h5py','matplotlib','cycler','kiwisolver','paramiko',"
            "'cryptography','nacl','setuptools','yt']\n"
            "for m in mods:\n"
            "    importlib.import_module(m)\n"
            "print('HEALTH_OK')\n"
        )
        out, err, rc = s.run(f"{VPY} -c '{probe_health}' 2>&1 | tail -2; echo PRC=${{PIPESTATUS[0]}}",
                             timeout=300)
        w(f"[health] {(out or '').strip()[-200:]}")

        for name, rel in [("framework", "test"),
                          ("input_gen", "flash/input_gen/test"),
                          ("output_processors", "flash/output_processors/test")]:
            out, err, rc = s.run(
                f"cd {TARGET} && {VPY} -m pytest {rel} -q --tb=line 2>&1 | tail -6",
                timeout=1800)
            w(f"===== suite {name} =====\n{(out or '').strip()[-600:]}")

    # ensure_sim_input 文件式探针
    s.upload(str(HERE.parent / "scripts" / "_probe_sim.py"), f"{PKG}/_probe_sim.py")
    out, err, rc = s.run(f"cd {TARGET} && {VPY} {PKG}/_probe_sim.py 2>&1 | tail -15",
                         timeout=600)
    w(f"===== ensure_sim_input =====\n{(out or '').strip()[-1000:]}")
lf.close()
print(f"LOG: {LOG}")
