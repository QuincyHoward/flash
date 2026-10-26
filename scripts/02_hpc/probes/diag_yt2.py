#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diag_yt2.py — yt 崩溃帧完整捕获 + .so 完整性核对 + 强制重装验证。"""
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

TARGET = "/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim"
VPY = f"{TARGET}/.venv-hpc-nce/bin/python"
PKG = "/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim_pkg"
SP = f"{TARGET}/.venv-hpc-nce/lib/python3.10/site-packages"
LOG = HERE.parent / "logs" / f"diag_yt2_{datetime.now():%Y%m%d_%H%M%S}.log"
lf = open(LOG, "w", encoding="utf-8", errors="replace")


def w(msg):
    print(msg)
    lf.write(msg + "\n")
    lf.flush()


with RemoteSession("flash_ssh") as s:
    # 1. 完整 faulthandler 帧（写文件再 cat，避免管道截断）
    s.run(f"{VPY} -X faulthandler -c 'import yt.geometry.selection_routines' "
          f"> {PKG}/yt_crash.txt 2>&1; echo $? > {PKG}/yt_crash.rc", timeout=120)
    out, err, rc = s.run(f"cat {PKG}/yt_crash.rc; echo ---; head -25 {PKG}/yt_crash.txt", timeout=60)
    w(f"===== selection_routines 崩溃帧 =====\n{(out or '').strip()[:1800]}")

    # 2. .so 完整性: venv vs wheel 内条目大小
    out, err, rc = s.run(
        f"ls -la {SP}/yt/geometry/selection_routines*.so 2>/dev/null; "
        f"{VPY} -c \"import zipfile,glob; w=glob.glob('{PKG}/wheelhouse-linux/yt-4*.whl')[0]; z=zipfile.ZipFile(w); print([ (i.filename, i.file_size) for i in z.infolist() if 'selection_routines' in i.filename and i.filename.endswith('.so')])\"",
        timeout=120)
    w(f"===== selection_routines .so 大小对比 =====\n{(out or '').strip()[:800]}")

    # 3. 强制重装 yt 后复测（wheelhouse 本地源）
    out, err, rc = s.run(
        f"{SP}/../../bin/pip install --no-index --find-links {PKG}/wheelhouse-linux "
        f"--force-reinstall --no-deps yt==4.3.1 2>&1 | tail -2", timeout=600)
    w(f"===== force-reinstall yt =====\n{(out or '').strip()[:400]}")
    out, err, rc = s.run(f"{VPY} -c 'import yt; print(\"YT_OK\", yt.__version__)' 2>&1; echo RC=$?",
                         timeout=300)
    w(f"===== 重装后 import yt =====\n{(out or '').strip()[-300:]}")

    # 4. 复制 yt 到节点本地 /tmp 再 import（排除 Lustre mmap 因素）
    out, err, rc = s.run(
        f"rm -rf /tmp/yt_test_$$ && mkdir -p /tmp/yt_test_$$/yt_pkg && "
        f"cp -r {SP}/yt /tmp/yt_test_$$/yt_pkg/ && "
        f"cd /tmp/yt_test_$$/yt_pkg && "
        f"{VPY} -S -c 'import sys; sys.path.insert(0, \".\"); import yt.geometry.selection_routines; print(\"TMP_OK\")' 2>&1 | tail -3; "
        f"rm -rf /tmp/yt_test_$$", timeout=600)
    w(f"===== /tmp 本地盘 yt import =====\n{(out or '').strip()[-400:]}")
lf.close()
print(f"LOG: {LOG}")
