#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HPC 双账号冒烟探测 (临时诊断用, 不打印密码)。

对 flash_ssh / flash_ssh_2 依次执行远程环境探测:
  whoami / HOME / 家目录布局 / module 系统 / mpich+hdf5 可用性。
"""
import sys
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
for _ in range(8):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession  # noqa: E402

REMOTE_PROBE = (
    "echo '--- whoami ---'; whoami; "
    "echo '--- HOME ---'; echo $HOME; "
    "echo '--- ls ~ ---'; ls -la ~ 2>/dev/null | head -15; "
    "echo '--- module.sh ---'; ls -la /public1/soft/modules/module.sh 2>/dev/null || echo NO_MODULE_SH; "
    "echo '--- module load ---'; "
    "module purge 2>/dev/null; source /public1/soft/modules/module.sh 2>/dev/null; "
    "module load mpich/3.2-gcc9.3 2>/dev/null; module load hdf5/1.8.18 2>/dev/null; "
    "echo '--- which ---'; which mpicc mpiexec mpirun h5cc h5pcc 2>/dev/null; "
    "echo '--- mpicc ver ---'; mpicc --version 2>/dev/null | head -1; "
    "echo '--- nproc/mem ---'; nproc; free -g 2>/dev/null | head -2; "
    "echo PROBE_DONE"
)


def main() -> int:
    rc = 0
    for cred in ("flash_ssh", "flash_ssh_2"):
        print(f"\n{'=' * 60}\n[Probe] 账号: {cred}\n{'=' * 60}")
        try:
            with RemoteSession(credential_name=cred, verbose=True) as s:
                out, err, code = s.run(REMOTE_PROBE, timeout=120)
                print("--- stdout ---")
                print(out[-2000:])
                if err.strip():
                    print("--- stderr ---")
                    print(err[-500:])
                print(f"exit={code}")
                if code != 0 or "PROBE_DONE" not in out:
                    print(f"[FAIL] {cred} 探测未完成")
                    rc = 1
        except Exception as e:  # noqa: BLE001
            print(f"[ERROR] {cred}: {type(e).__name__}: {e}")
            rc = 1
    print(f"\n[Result] rc={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
