#!/usr/bin/env python3
"""_probe_impi.py — Intel MPI 运行期符号错误诊断。"""
import sys

sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

FLASH4 = ("/publicfs01/fs1-e/home/scfa2696/QC/FLASH/FLASH4.8/hello/"
          "LaserSlab_ChCenter/flash4")

with RemoteSession("flash_ssh") as s:
    checks = [
        ("mpi_versions", "ls -la /public1/soft/oneAPI/2022.1/mpi/ 2>/dev/null | head -8"),
        ("latest_lib_mpi", "ls /public1/soft/oneAPI/2022.1/mpi/latest/lib/ 2>/dev/null | grep -E 'libmpi.*so' | head -6"),
        ("release_dir", "ls /public1/soft/oneAPI/2022.1/mpi/latest/release 2>/dev/null | head -4"),
        ("ldd_flash4", f"ldd {FLASH4} 2>/dev/null | grep -iE 'mpi|mpifort' | head -6"),
        ("driver_ldpath", "bash -lc 'echo $LD_LIBRARY_PATH' | tr ':' '\\n' | grep -iE 'mpi' | head -6"),
        ("MPII_F_TRUE_in_libs", "for f in /public1/soft/oneAPI/2022.1/mpi/latest/lib/libmpi.so.12 /public1/soft/oneAPI/2022.1/mpi/2021.*/lib/libmpi.so.12; do [ -f $f ] && echo \"$f: $(nm -D $f 2>/dev/null | grep -c MPII_F_TRUE)\"; done"),
        ("setversion", "cat /public1/soft/oneAPI/2022.1/mpi/latest/etc/mpi_vars.sh 2>/dev/null | grep -E 'LD_LIBRARY|PATH' | head -4"),
    ]
    for name, cmd in checks:
        out, err, rc = s.run(cmd, timeout=120)
        print(f"== {name} ==")
        print(((out or "") + (err or "")).strip()[:600])
