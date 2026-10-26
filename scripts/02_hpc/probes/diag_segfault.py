#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diag_segfault.py — 逐模块 import 探针，定位 venv python SIGSEGV 的元凶。"""
import sys

sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

TARGET = "/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim"
VPY = f"{TARGET}/.venv-hpc-nce/bin/python"

MODULES = ["pytest", "pluggy", "iniconfig", "packaging", "pygments",
           "numpy", "scipy", "h5py", "matplotlib", "cycler", "kiwisolver",
           "paramiko", "cryptography", "nacl", "setuptools", "yt", "pandas"]

with RemoteSession("flash_ssh") as s:
    out, err, rc = s.run(f"{VPY} --version 2>&1", timeout=60)
    print(f"venv python: {(out or err).strip()} (rc={rc})")
    for m in MODULES:
        out, err, rc = s.run(
            f"{VPY} -X faulthandler -c 'import {m}; print(\"OK\", {m}.__version__)' 2>&1 | tail -3",
            timeout=120)
        blob = ((out or "") + (err or "")).strip()
        status = "OK" if rc == 0 else f"FAIL(rc={rc})"
        print(f"[{status:10s}] {m}: {blob[-160:]!r}")
