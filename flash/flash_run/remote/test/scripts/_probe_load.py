#!/usr/bin/env python3
"""_probe_load.py — 两种 LD_LIBRARY_PATH 顺序下 libmpifort 加载测试。"""
import sys

sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

MPI = "/public1/soft/oneAPI/2022.1/mpi/latest"

with RemoteSession("flash_ssh") as s:
    tests = [
        ("lib_first",
         f"LD_LIBRARY_PATH={MPI}/lib:$LD_LIBRARY_PATH "
         f"python3 -c \"import ctypes; ctypes.CDLL('libmpifort.so.12'); print('LOAD_OK')\" 2>&1 | tail -1"),
        ("release_first",
         f"LD_LIBRARY_PATH={MPI}/lib/release:{MPI}/lib:$LD_LIBRARY_PATH "
         f"python3 -c \"import ctypes; ctypes.CDLL('libmpifort.so.12'); print('LOAD_OK')\" 2>&1 | tail -1"),
        ("lib_only",
         f"LD_LIBRARY_PATH={MPI}/lib "
         f"python3 -c \"import ctypes; ctypes.CDLL('libmpifort.so.12'); print('LOAD_OK')\" 2>&1 | tail -1"),
    ]
    for name, cmd in tests:
        out, err, rc = s.run(cmd, timeout=60)
        print(f"== {name} == {(out or '').strip()[-160:]}")
