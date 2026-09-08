#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BSCC (sch0348) sbatch 作业内环境冒烟 (临时诊断)。

验证: 作业内 PATH/LD 继承、mpich mpif90 绝对路径可用、显式 export
mpich bin + hdf5 lib 后常规树 flash4 依赖全解析、mpich mpiexec 可运行。
"""
import argparse
import base64
import re
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
for _ in range(8):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession  # noqa: E402

SMOKE = r'''#!/bin/bash
#SBATCH --job-name=SNB_bscc_smoke
#SBATCH -p v6_384
#SBATCH -N 1
#SBATCH --ntasks=2
#SBATCH --output=smoke_bscc_%j_out.txt
#SBATCH --error=smoke_bscc_%j_err.txt
set +e
echo "===A PATH head==="
echo "$PATH" | tr ':' '\n' | grep -v '^$' | head -6
echo "===B mpif90 direct==="
/public1/soft/mpich/3.2/bin/mpif90 --version 2>&1 | head -1
echo "===C mpich libs==="
ls /public1/soft/mpich/3.2/lib/libmpich* 2>/dev/null | head -4
echo "===D gfortran5 search==="
ls /public1/soft/gcc/*/lib64/libgfortran.so* 2>/dev/null | head -3
ls /public1/soft/mpich/3.2/../*/lib/libgfortran.so* 2>/dev/null | head -3
find /public1/soft -maxdepth 4 -name "libgfortran.so.5" 2>/dev/null | head -3
echo "===E export env + ldd==="
export PATH=/public1/soft/mpich/3.2/bin:$PATH
export LD_LIBRARY_PATH=/public1/soft/hdf5/1.8.18/lib:$LD_LIBRARY_PATH
which mpiexec
ldd ~/QC/FLASH/FLASH4.8/object/flash4 2>/dev/null | grep 'not found'
echo "===F mpiexec test==="
mpiexec -n 2 hostname 2>&1 | head -3
echo "RC=$?"
echo SMOKE_BSCC_DONE
'''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default="flash_ssh_2")
    args = ap.parse_args()
    print(f"[Smoke-BSCC] 账号={args.account}")
    with RemoteSession(credential_name=args.account, verbose=True) as s:
        s.run("mkdir -p ~/SNB_hpc_build", timeout=30)
        b64 = base64.b64encode(SMOKE.encode()).decode()
        out, _, _ = s.run(
            f"echo {b64} | base64 -d > ~/SNB_hpc_build/smoke_bscc.sh && bash -n ~/SNB_hpc_build/smoke_bscc.sh && echo SCRIPT_OK",
            timeout=30,
        )
        if "SCRIPT_OK" not in out:
            print(f"脚本写入失败: {out[-200:]}")
            return 1
        out, _, code = s.run("cd ~/SNB_hpc_build && sbatch smoke_bscc.sh 2>&1", timeout=60)
        m = re.search(r"Submitted batch job (\d+)", out)
        if not m:
            print(f"sbatch 失败: {out[-300:]}")
            return 1
        jid = m.group(1)
        print(f"JobID={jid} 等待完成...")
        for _ in range(90):
            out, _, _ = s.run(
                f"sacct -j {jid} --format=State --noheader 2>/dev/null | head -1", timeout=30
            )
            st = out.strip()
            if st in ("COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL"):
                print(f"状态: {st}")
                break
            time.sleep(15)
        out, _, _ = s.run(
            f"cd ~/SNB_hpc_build && ls -t smoke_bscc_*_out.txt | head -1 | xargs cat 2>/dev/null; "
            f"echo '--- ERR ---'; ls -t smoke_bscc_*_err.txt | head -1 | xargs cat 2>/dev/null | tail -8",
            timeout=30,
        )
        print(out[-2600:])
        ok = "SMOKE_BSCC_DONE" in out
        print(f"[{'OK' if ok else 'FAIL'}] smoke-bscc")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
