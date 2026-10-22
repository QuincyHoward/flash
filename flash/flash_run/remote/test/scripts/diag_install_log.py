#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diag_install_log.py — 拉取远端安装日志的错误行与尾部（诊断用，只读）。"""
import sys
from pathlib import Path

sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

PKG = "/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim_pkg"
LOG = f"{PKG}/install_20261022_114604.log"

with RemoteSession("flash_ssh") as s:
    out, err, rc = s.run(f"wc -l {LOG}", timeout=60)
    print("行数:", (out or "").strip())
    out, err, rc = s.run(
        f"grep -n 'OSError' {LOG} | tail -10", timeout=60)
    print("===== OSError 行 =====")
    print((out or "").strip()[:1500])
    out, err, rc = s.run(
        f"grep -n 'ERROR:' {LOG} | tail -10", timeout=60)
    print("===== ERROR 行 =====")
    print((out or "").strip()[:1200])
    out, err, rc = s.run(
        f"grep -n 'Successfully installed\\|Requirement already satisfied' {LOG} | tail -5", timeout=60)
    print("===== 成功/已装行（末 5） =====")
    print((out or "").strip()[:1200])
    out, err, rc = s.run(f"tail -90 {LOG}", timeout=60)
    print("===== 尾部 90 行 =====")
    print((out or "").strip()[-4000:])
