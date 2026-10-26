#!/usr/bin/env python3
"""_probe_flash4.py — flash4 直接加载复现 + env/vars.sh 方案验证。"""
import sys

sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

FLASH4 = ("/publicfs01/fs1-e/home/scfa2696/QC/FLASH/FLASH4.8/hello/"
          "LaserSlab_ChCenter/flash4")
MPI = "/public1/soft/oneAPI/2022.1/mpi/latest"

with RemoteSession("flash_ssh") as s:
    checks = [
        ("vars_sh_exists", f"ls {MPI}/env/vars.sh 2>/dev/null && echo YES || echo NO"),
        ("repro_current_order",
         f"LD_LIBRARY_PATH={MPI}/lib/release:{MPI}/lib:$LD_LIBRARY_PATH "
         f"{FLASH4} 2>&1 | head -2; echo RC=$?"),
        ("repro_vars_sh",
         f"bash -c 'source {MPI}/env/vars.sh 2>/dev/null; {FLASH4}' 2>&1 | head -2; echo RC=$?"),
        ("nm_libmpi", f"command -v nm >/dev/null && nm -D {MPI}/lib/libmpi.so.12 2>/dev/null | grep -c MPII_F_TRUE || echo NO_NM; nm -D {MPI}/lib/libmpifort.so.12 2>/dev/null | grep -c MPII_F_TRUE"),
    ]
    for name, cmd in checks:
        out, err, rc = s.run(cmd, timeout=120)
        print(f"== {name} ==")
        print(((out or "") + (err or "")).strip()[:700])
