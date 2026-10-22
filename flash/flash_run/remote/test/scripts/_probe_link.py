#!/usr/bin/env python3
"""_probe_link.py — 第四轮冒烟失败诊断（注入生效性与错误变化）。"""
import sys

sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

IN = ("/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/flash_sim"
      "/flash/scenarios/public/center_evolution/ch_center/flash_input")

with RemoteSession("flash_ssh") as s:
    checks = [
        ("A_impi_injected", f"grep -c flash_impi_env {IN}/submit_flash.sh"),
        ("B_module_lines", f"grep -cE '^module' {IN}/submit_flash.sh"),
        ("C_cannot_find", f"grep -c 'cannot find' {IN}/FLASH_batch_err.txt"),
        ("D_make_errors", f"grep -E 'Error [0-9]+|^ld:|^/usr' {IN}/FLASH_batch_err.txt | tail -4"),
        ("E_env_file", f"cat {IN}/flash_impi_env.sh 2>/dev/null | head -3"),
        ("F_out_tail", f"grep -E 'Error|error|undefined' {IN}/FLASH_batch_out.txt | tail -4"),
    ]
    for name, cmd in checks:
        out, err, rc = s.run(cmd, timeout=60)
        print(f"== {name} (rc={rc}) ==")
        print(((out or "") + (err or "")).strip()[:500])
