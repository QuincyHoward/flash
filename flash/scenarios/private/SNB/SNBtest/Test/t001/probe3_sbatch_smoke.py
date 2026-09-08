#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sbatch 作业内环境冒烟 (临时诊断): 验证作业内 PATH/LD_LIBRARY_PATH 继承
登录环境、hdf5 module 可用、flash4 动态库全解析、分区可提交。

用法: python probe3_sbatch_smoke.py --account flash_ssh
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

PARTITION = {"flash_ssh": "v5_192", "flash_ssh_2": "v6_384"}

SMOKE = r'''#!/bin/bash
#SBATCH --job-name=SNB_smoke
#SBATCH -p {part}
#SBATCH -N 1
#SBATCH --ntasks=2
#SBATCH --output=smoke_%j_out.txt
#SBATCH --error=smoke_%j_err.txt
set +e
echo "===A PATH head==="
echo "$PATH" | tr ':' '\n' | grep -v '^$' | head -6
echo "===B LD_LIBRARY_PATH==="
echo "$LD_LIBRARY_PATH"
echo "===C module func==="
type module 2>/dev/null | head -1 || echo NO_MODULE_FUNC
source /public1/soft/modules/module.sh 2>/dev/null || true
module load hdf5/1.8.18 2>&1 | head -3
echo "===D mpiexec==="
which mpiexec mpirun 2>/dev/null
mpiexec --version 2>&1 | head -2
echo "===E ldd flash4==="
ldd ~/QC/FLASH/FLASH4.8/object/flash4 2>/dev/null | grep -c 'not found'
echo SMOKE_DONE
'''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default="flash_ssh", choices=["flash_ssh", "flash_ssh_2"])
    ap.add_argument("--partition", default="", help="覆盖分区")
    args = ap.parse_args()
    part = args.partition or PARTITION[args.account]
    print(f"[Smoke] 账号={args.account} 分区={part}")

    with RemoteSession(credential_name=args.account, verbose=True) as s:
        s.run("mkdir -p ~/SNB_hpc_build", timeout=30)
        script = SMOKE.format(part=part)
        b64 = base64.b64encode(script.encode()).decode()
        out, _, _ = s.run(
            f"echo {b64} | base64 -d > ~/SNB_hpc_build/smoke.sh && bash -n ~/SNB_hpc_build/smoke.sh && echo SCRIPT_OK",
            timeout=30,
        )
        if "SCRIPT_OK" not in out:
            print(f"脚本写入失败: {out[-200:]}")
            return 1
        out, _, code = s.run("cd ~/SNB_hpc_build && sbatch smoke.sh 2>&1", timeout=60)
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
            f"cd ~/SNB_hpc_build && ls -t smoke_*_out.txt | head -1 | xargs cat 2>/dev/null; "
            f"echo '--- ERR ---'; ls -t smoke_*_err.txt | head -1 | xargs cat 2>/dev/null | tail -10",
            timeout=30,
        )
        print(out[-2500:])
        ok = "SMOKE_DONE" in out
        print(f"[{'OK' if ok else 'FAIL'}] smoke")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
