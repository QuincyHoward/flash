#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""try_yt_versions.py — 上传 yt 候选 wheel 并在超算逐版本实测 + ensure_sim_input 诊断。"""
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST_DIR = HERE.parent
REPO_ROOT = TEST_DIR.parents[3]
CAND = TEST_DIR / "packages" / "yt_candidates"
sys.path.insert(0, str(REPO_ROOT))
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

TARGET = "/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim"
PKG = "/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim_pkg"
WH = f"{PKG}/wheelhouse-linux"
VPY = f"{TARGET}/.venv-hpc-nce/bin/python"
PIP = f"{TARGET}/.venv-hpc-nce/bin/pip"
LOG = TEST_DIR / "logs" / f"try_yt_{datetime.now():%Y%m%d_%H%M%S}.log"
lf = open(LOG, "w", encoding="utf-8", errors="replace")


def w(msg):
    print(msg)
    lf.write(msg + "\n")
    lf.flush()


with RemoteSession("flash_ssh") as s:
    # 1. 上传候选 wheel
    for whl in sorted(CAND.glob("*.whl")):
        ok = s.upload(str(whl), f"{WH}/{whl.name}")
        w(f"[upload] {whl.name}: {'OK' if ok else 'FAIL'}")

    # 2. 逐版本实测（先老后新：4.1.4 → 4.3.0）
    winner = None
    for ver in ("4.1.4", "4.3.0"):
        out, err, rc = s.run(
            f"{PIP} install --no-index --find-links {WH} "
            f"--force-reinstall --no-deps yt=={ver} 2>&1 | tail -1", timeout=600)
        w(f"[install yt=={ver}] {(out or '').strip()[-120:]}")
        out, err, rc = s.run(
            f"{VPY} -c 'import yt; print(\"YT_OK\", yt.__version__)' 2>&1; echo RC=$?",
            timeout=300)
        blob = (out or "").strip()
        w(f"[import yt=={ver}] {blob[-160:]}")
        if "YT_OK" in blob:
            winner = ver
            break

    w(f"[winner] {winner}")

    # 3. ensure_sim_input 手动诊断
    probe = (
        "import traceback\n"
        "from flash.scenarios.registry import get_scenario\n"
        "sc = get_scenario('ch_center')\n"
        "print('sim_input_dir:', sc.sim_input_dir)\n"
        "try:\n"
        "    sc.ensure_sim_input()\n"
        "    import pathlib\n"
        "    print('generated:', sorted(p.name for p in pathlib.Path(sc.sim_input_dir).iterdir())[:10])\n"
        "except BaseException:\n"
        "    traceback.print_exc()\n"
    )
    out, err, rc = s.run(
        f"cd {TARGET} && {VPY} -c '{probe}' 2>&1 | tail -20", timeout=600)
    w(f"===== ensure_sim_input 诊断 =====\n{(out or '').strip()[-1200:]}")
lf.close()
print(f"LOG: {LOG}")
