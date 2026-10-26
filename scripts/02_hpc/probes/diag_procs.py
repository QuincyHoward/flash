#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diag_procs.py — 检查远端残留进程与 venv 状态。"""
import sys

sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

TARGET = "/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim"

with RemoteSession("flash_ssh") as s:
    out, err, rc = s.run(
        "ps -u scfa2696 -o pid,etime,cmd --no-headers | grep -Ev 'ps -u|grep' | head -30",
        timeout=60)
    print("===== 用户进程 =====")
    print((out or "").strip()[:2000])
    out, err, rc = s.run(
        f"ls -la {TARGET}/ | head -20; ls {TARGET}/.venv-hpc-nce/bin 2>&1 | head -5",
        timeout=60)
    print("===== 部署目录与 venv =====")
    print((out or "").strip()[:1200])
