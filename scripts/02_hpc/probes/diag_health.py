#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diag_health.py — 复现 start_flash 健康探针 + 直接跑三套测试（绕过 wipe 循环）。"""
import sys

sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

TARGET = "/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim"
VPY = f"{TARGET}/.venv-hpc-nce/bin/python"

PROBE = (
    "import importlib, sys\n"
    "mods = ['pytest', 'pluggy', 'iniconfig', 'packaging', 'pygments', "
    "'numpy', 'scipy', 'h5py', 'matplotlib', 'cycler', 'kiwisolver', "
    "'paramiko', 'cryptography', 'nacl', 'setuptools', 'yt']\n"
    "bad = []\n"
    "for m in mods:\n"
    "    importlib.import_module(m)\n"
    "print('HEALTHY')\n"
    "sys.exit(0)\n"
)

with RemoteSession("flash_ssh") as s:
    # 1. 健康探针复现 3 次
    for i in range(1, 4):
        out, err, rc = s.run(f"{VPY} -c '{PROBE}' 2>&1 | tail -4", timeout=300)
        print(f"[probe {i}/3] rc={rc}: {((out or '') + (err or '')).strip()[-200:]}")
    # 2. pytest 可启动性
    out, err, rc = s.run(f"{VPY} -m pytest --version 2>&1", timeout=120)
    print(f"[pytest --version] rc={rc}: {((out or '') + (err or '')).strip()[:150]}")
    # 3. 直接跑三套测试（-q，串行）
    for name, rel in [("framework", "test"),
                      ("input_gen", "flash/input_gen/test"),
                      ("output_processors", "flash/output_processors/test")]:
        out, err, rc = s.run(
            f"cd {TARGET} && {VPY} -m pytest {rel} -q --tb=line 2>&1 | tail -4",
            timeout=1800)
        print(f"[suite {name}] rc={rc}: {((out or '') + (err or '')).strip()[-220:]}")
