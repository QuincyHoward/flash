#!/usr/bin/env python3
"""_probe_pair.py — Intel MPI lib/ 与 lib/release/ 配对检查 + 小程序作业验证。"""
import sys
import time

sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

MPI = "/public1/soft/oneAPI/2022.1/mpi/latest"

with RemoteSession("flash_ssh") as s:
    out, _, _ = s.run(
        f"ls {MPI}/lib/release/ 2>/dev/null | grep -E 'libmpi' | head -6; "
        f"echo ---; ls -la {MPI}/lib/libmpifort.so.12 {MPI}/lib/release/libmpifort* "
        f"{MPI}/lib/libmpi.so.12 {MPI}/lib/release/libmpi.so.12 2>/dev/null",
        timeout=60)
    print("== lib/release 内容 ==")
    print((out or "").strip()[:800])

    # 决定性：flash4 用 release 优先的 LD 顺序直接跑一次（登录节点即可触发符号解析）
    FLASH4 = ("/publicfs01/fs1-e/home/scfa2696/QC/FLASH/FLASH4.8/hello/"
              "LaserSlab_ChCenter/flash4")
    out, _, _ = s.run(
        f"cd /publicfs01/fs1-e/home/scfa2696/QC/FLASH/FLASH4.8/hello/LaserSlab_ChCenter && "
        f"LD_LIBRARY_PATH={MPI}/lib/release:{MPI}/lib:/public1/soft/hdf5/1.8.18/lib:"
        f"$LD_LIBRARY_PATH ./flash4 2>&1 | head -3; echo RC=$?",
        timeout=120)
    print("== flash4 release-first 加载 ==")
    print((out or "").strip()[:500])
