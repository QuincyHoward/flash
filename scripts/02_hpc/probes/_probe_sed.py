#!/usr/bin/env python3
"""_probe_sed.py — 远端 sed a-命令行为测试（找真实报错）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from flash._core.paths import hpc_home_required as _hpc_home_req
_RH = _hpc_home_req()  # 超算家目录：运行期解析，绝不硬编码

from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

# ★ 2026-11-11 可移植化：ch_center 目录经 discovery 按名解析（场景移动免疫），
#   不再字面量硬编码包路径。
from flash.scenarios.core.scene_reg.discovery import resolve_scene_meta  # noqa: E402

_REPO = Path(__file__).resolve().parents[3]
_ch_dir = Path(resolve_scene_meta("ch_center").source).parent
IN = (f"{_RH}/PhySimX/PhySimX/simulation/flash/flash_sim/"
      f"{_ch_dir.relative_to(_REPO).as_posix()}/flash_input")

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
