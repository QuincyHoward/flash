#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wait_install.py — 等待当前唯一安装编排进程（PID 由参数给出）结束并汇报。"""
import sys
import time

sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

PKG = "/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim_pkg"
SENT = f"{PKG}/install_20261022_114604.done"
LOG = f"{PKG}/install_20261022_114604.log"
ORCH_PID = sys.argv[1] if len(sys.argv) > 1 else "23920"

with RemoteSession("flash_ssh") as s:
    for n in range(1, 41):
        time.sleep(90)
        out, err, rc = s.run(
            f"ps -p {ORCH_PID} --no-headers >/dev/null && echo ALIVE || echo GONE; "
            f"echo ---; tail -c 300 {LOG} | tr '\n' ' ' | tail -c 200",
            timeout=90)
        blob = (out or "")
        alive = "ALIVE" in blob
        tail = blob.split("---")[-1].strip()
        est = n * 90 // 60
        if not alive:
            out2, _, _ = s.run(f"cat {SENT} 2>/dev/null; echo ===; tail -30 {LOG}", timeout=90)
            print(f"[done] 编排进程已结束（累计 {est}min）")
            print((out2 or "").strip()[-2500:])
            # 哨兵文件内容是脚本最后一条命令的 echo $?
            sent = (out2 or "").strip().split("===")[0].strip()
            sys.exit(0 if sent == "0" else 1)
        print(f"[poll {n:3d}] 已等 {est:3d}min 运行中 | ...{tail[-130:]!r}")
print("TIMEOUT")
sys.exit(2)
