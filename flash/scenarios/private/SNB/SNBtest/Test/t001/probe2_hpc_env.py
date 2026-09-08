#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HPC 编译/运行环境精确探测 (临时诊断, 不打印密码)。

回答 run_snb_hpc.py 三个关键未知:
  1. 登录节点干净环境下 mpiifort/ifort 能否直接执行 (编译作业内能否直接用绝对路径编译器)
  2. 各账号常规树 Makefile.h 真实关键行 + 常规树 flash4 动态库依赖
     (决定运行作业内需要 source/load 什么才能解析 flash4 的库)
  3. module avail 中可用的编译器/运行时模块

用法: python probe2_hpc_env.py --account flash_ssh|flash_ssh_2
"""
import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
for _ in range(8):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession  # noqa: E402

QUICK_PROBE = r'''
set +e
echo "===A clean env==="
echo "PATH=$PATH" | tr ':' '\n' | grep -v '^$' | head -8
echo "LD_LIBRARY_PATH=[$LD_LIBRARY_PATH]"
echo "===B compiler direct==="
MPIROOT=$(grep -E '^MPI_PATH' ~/QC/FLASH/FLASH4.8/Makefile.h 2>/dev/null | head -1 | sed 's/^MPI_PATH[[:space:]]*=[[:space:]]*//')
echo "MPIROOT=[$MPIROOT]"
if [ -n "$MPIROOT" ] && [ -x "$MPIROOT/bin/mpif90" ]; then "$MPIROOT/bin/mpif90" --version 2>&1 | head -2; else echo NO_MPIF90; fi
if [ -n "$MPIROOT" ] && [ -x "$MPIROOT/bin/mpiifort" ]; then "$MPIROOT/bin/mpiifort" --version 2>&1 | head -2; else echo NO_MPIIFORT; fi
ls /public1/soft/oneAPI/2022.1/compiler/latest/linux/bin/intel64/ifort 2>/dev/null && echo IFORT_EXE_OK || echo NO_IFORT_EXE
echo "===C normal Makefile.h==="
grep -E '^(MPI_PATH|HDF5_PATH|NCMPI_PATH|HYPRE_PATH|FCOMP|CCOMP|LINK|FFLAGS_OPT|LIB_LAPACK|LIB_HDF5)' ~/QC/FLASH/FLASH4.8/Makefile.h 2>/dev/null
echo "===D normal flash4==="
ls -d ~/QC/FLASH/FLASH4.8/object 2>/dev/null
ls ~/QC/FLASH/FLASH4.8/object/flash4 2>/dev/null && echo NORMAL_FLASH4_OK || echo NO_NORMAL_FLASH4
echo "===E ldd normal flash4 (clean env)==="
ldd ~/QC/FLASH/FLASH4.8/object/flash4 2>/dev/null | grep -E 'not found|=> /' | head -20
echo PROBE2_DONE
'''

PROBE = r'''
set +e
echo "===A clean env==="
echo "PATH=$PATH" | tr ':' '\n' | grep -v '^$' | head -8
echo "LD_LIBRARY_PATH=[$LD_LIBRARY_PATH]"
echo "===B compiler direct==="
MPIROOT=$(grep -E '^MPI_PATH' ~/QC/FLASH/FLASH4.8/Makefile.h 2>/dev/null | head -1 | sed 's/^MPI_PATH[[:space:]]*=[[:space:]]*//')
echo "MPIROOT=[$MPIROOT]"
if [ -n "$MPIROOT" ] && [ -x "$MPIROOT/bin/mpif90" ]; then "$MPIROOT/bin/mpif90" --version 2>&1 | head -2; else echo NO_MPIF90; fi
if [ -n "$MPIROOT" ] && [ -x "$MPIROOT/bin/mpiifort" ]; then "$MPIROOT/bin/mpiifort" --version 2>&1 | head -2; else echo NO_MPIIFORT; fi
ls /public1/soft/oneAPI/2022.1/compiler/latest/linux/bin/intel64/ifort 2>/dev/null && echo IFORT_EXE_OK || echo NO_IFORT_EXE
echo "===C normal Makefile.h==="
grep -E '^(MPI_PATH|HDF5_PATH|NCMPI_PATH|HYPRE_PATH|FCOMP|CCOMP|LINK|FFLAGS_OPT|LIB_LAPACK|LIB_HDF5)' ~/QC/FLASH/FLASH4.8/Makefile.h 2>/dev/null
echo "===D normal flash4==="
ls -d ~/QC/FLASH/FLASH4.8/object 2>/dev/null
ls ~/QC/FLASH/FLASH4.8/object/flash4 2>/dev/null && echo NORMAL_FLASH4_OK || echo NO_NORMAL_FLASH4
echo "===E ldd normal flash4 (clean env)==="
ldd ~/QC/FLASH/FLASH4.8/object/flash4 2>/dev/null | grep -E 'not found|=> /' | head -20
echo "===F module avail==="
source /public1/soft/modules/module.sh 2>/dev/null; module purge 2>&1 | head -1; module avail 2>&1 | grep -iE 'intel|oneapi|mpi|hdf|gcc|mpich|compiler' | head -25
echo "===G FLASHSNB==="
ls -d ~/QC/FLASH/FLASHSNB/FLASH4.8 2>/dev/null && echo SNB_TREE_OK || echo NO_SNB_TREE
ls -d ~/SNB_hpc_build ~/SNB_hpc_run 2>/dev/null || echo NO_HPC_DIRS
echo "===H sbatch/sinfo==="
which sbatch sinfo squeue 2>/dev/null
sinfo -s 2>/dev/null | head -8
echo PROBE2_DONE
'''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", default="flash_ssh", choices=["flash_ssh", "flash_ssh_2"])
    ap.add_argument("--quick", action="store_true", help="只跑 A-E 编译器/依赖段")
    args = ap.parse_args()
    print(f"[Probe2] 账号: {args.account}")
    probe = QUICK_PROBE if args.quick else PROBE
    with RemoteSession(credential_name=args.account, verbose=True) as s:
        out, err, code = s.run(probe, timeout=180)
        print(out[:3000] if args.quick else out[-3500:])
        if err.strip():
            print("--- stderr ---")
            print(err[-800:])
        print(f"exit={code}")
        ok = "PROBE2_DONE" in out
        print(f"[{'OK' if ok else 'FAIL'}] probe2 done={ok}")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
