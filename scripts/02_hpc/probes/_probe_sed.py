#!/usr/bin/env python3
"""_probe_sed.py — 远端 sed a-命令行为测试（找真实报错）。"""
import sys

sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

IN = ("/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim"
      "/flash/scenarios/public/center_evolution/ch_center/flash_input")

with RemoteSession("flash_ssh") as s:
    tests = [
        ("sed_a_one_line",
         f"cp {IN}/submit_flash.sh /tmp/sedtest.sh && "
         f"sed -i '/^set -e/a source ./flash_impi_env.sh' /tmp/sedtest.sh; "
         f"echo RC=$?; grep -c flash_impi_env /tmp/sedtest.sh"),
        ("sed_a_escape",
         f"cp {IN}/submit_flash.sh /tmp/sedtest2.sh && "
         f"sed -i '/^set -e$/a source .\\/flash_impi_env.sh' /tmp/sedtest2.sh; "
         f"echo RC=$?; grep -c flash_impi_env /tmp/sedtest2.sh"),
        ("awk_variant",
         f"cp {IN}/submit_flash.sh /tmp/sedtest3.sh && "
         f"awk '{{print}} /^set -e$/ && !x {{print \"source ./flash_impi_env.sh\"; x=1}}' "
         f"{IN}/submit_flash.sh > /tmp/sedtest3.sh; "
         f"echo RC=$?; grep -c flash_impi_env /tmp/sedtest3.sh"),
    ]
    for name, cmd in tests:
        out, err, rc = s.run(cmd, timeout=60)
        print(f"== {name} ==")
        print("OUT:", (out or "").strip()[-200:])
        if (err or "").strip():
            print("ERR:", err.strip()[:300])
    s.run("rm -f /tmp/sedtest*.sh", timeout=30)
