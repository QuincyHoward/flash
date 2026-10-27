#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diag_health2.py — 健康探针完整 traceback + 三套测试完整统计。"""
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST_DIR = HERE.parent
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from flash._core.paths import hpc_home_required as _hpc_home_req
_RH = _hpc_home_req()  # 超算家目录：运行期解析，绝不硬编码

from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

TARGET = f"{_RH}/PhySimX/PhySimX/simulation/flash/flash_sim"
VPY = f"{TARGET}/.venv-hpc-nce/bin/python"
LOG = HERE.parent / "logs" / f"diag_health2_{datetime.now():%Y%m%d_%H%M%S}.log"
lf = open(LOG, "w", encoding="utf-8", errors="replace")


def w(msg):
    print(msg)
    lf.write(msg + "\n")
    lf.flush()


PROBE = (
    "import importlib, sys, traceback\n"
    "mods = ['pytest', 'pluggy', 'iniconfig', 'packaging', 'pygments', "
    "'numpy', 'scipy', 'h5py', 'matplotlib', 'cycler', 'kiwisolver', "
    "'paramiko', 'cryptography', 'nacl', 'setuptools', 'yt']\n"
    "for m in mods:\n"
    "    try:\n"
    "        importlib.import_module(m)\n"
    "        print('import', m, 'OK')\n"
    "    except BaseException as e:\n"
    "        print('import', m, 'FAIL')\n"
    "        traceback.print_exc()\n"
    "print('PROBE_DONE')\n"
)

with RemoteSession("flash_ssh") as s:
    for i in range(1, 3):
        out, err, rc = s.run(f"{VPY} -c '{PROBE}' 2>&1", timeout=300)
        w(f"===== probe {i}/2 (rc={rc}) =====")
        w(((out or "") + (err or "")).strip()[-1800:])
    for name, rel in [("framework", "test"),
                      ("input_gen", "flash/input_gen/test"),
                      ("output_processors", "flash/output_processors/test")]:
        out, err, rc = s.run(
            f"cd {TARGET} && {VPY} -m pytest {rel} -q --tb=line 2>&1 | tail -25",
            timeout=1800)
        w(f"===== suite {name} (pipe-rc) =====")
        w(((out or "") + (err or "")).strip()[-1800:])
lf.close()
print(f"LOG: {LOG}")
