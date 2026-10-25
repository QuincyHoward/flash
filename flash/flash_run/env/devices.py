# -*- coding: utf-8 -*-
"""devices.py — 超算**装置参数**唯一事实源（分区 / 模块 / 库路径）。

★ 为什么需要这个模块（2026-10-26 架构护栏 R-SCENE-05 实测）：
  场景层的 sbatch 脚本里**不得**出现装置参数（分区名、模块路径、
  `/public1/soft/...` 绝对路径）—— 换机器即静默失效，且不同场景
  各写一份必然漂移。规则 R-SCENE-05 的提示原文：
  "装置参数（账户/分区/模块）应下沉 flash_run/env/devices.py 或凭据配置"。

  ★ 事故背景（超算实测，作业 4924449 FAILED）：
    两个 sandwich 场景的 sbatch 脚本原本**完全不加载 module** ⇒
    编译期缺 MPI/HDF5 环境；补上 `module load mpich/3.2-gcc9.3` 后
    **链接反而失败**：`ld: cannot find -lmpifort / -lmpi`。
    对照实验（超算逐条实测）：
      无 module               ⇒ 链接 OK
      module load mpich/3.2   ⇒ 链接 FAIL
      module load hdf5/1.8.18 ⇒ 链接 FAIL（连显式 -L 都救不回）
    ⇒ **任何 module load 都会污染 ifort/mpiifort 的隐式 MPI 库路径**
      （module 设的 LIBRARY_PATH/CPATH 指向旧 Intel 2018 环境，
        屏蔽了 oneAPI 2022.1 自带的 libmpifort）。
    而 FLASH 的 Makefile.h 已**硬编码**绝对路径 ⇒ 本就不需要 module。
    ⇒ 正解：不加载 module，显式注入 Intel MPI / HDF5 的库路径。

  本模块把这些路径集中一处，场景脚本通过 `python -c "from
  flash.flash_run.env.devices import ...; print(...)"` 或直接
  由生成器把值渲染进脚本 —— 生成器（场景层）只**读取**本模块，
  不硬编码任何装置路径。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

# ── NC-E（超算）装置参数 ────────────────────────────────────────────
#: 超算软件根（oneAPI / hdf5 / modules 都挂在这里）
SOFT_ROOT = "/public1/soft"

#: Intel oneAPI 根（编译器 + Intel MPI）
ONEAPI_ROOT = f"{SOFT_ROOT}/oneAPI/2022.1"

#: Intel MPI 的 bin（含 mpiifort / mpirun / hydra_bstrap_proxy）
INTEL_MPI_BIN = f"{ONEAPI_ROOT}/mpi/latest/bin"

#: Intel MPI 库目录（★ 顺序敏感，见下方 LD_LIBRARY_PATH 注释）
INTEL_MPI_LIB_RELEASE = f"{ONEAPI_ROOT}/mpi/latest/lib/release"
INTEL_MPI_LIB = f"{ONEAPI_ROOT}/mpi/latest/lib"

#: HDF5 库目录（FLASH Makefile.h 已硬编码 -I/-L 到 1.8.18）
HDF5_LIB = f"{SOFT_ROOT}/hdf5/1.8.18/lib"

#: 作业分区（★ 不写进场景脚本；由本模块提供）
HPC_PARTITION = "v5_192"

#: 可选分区（更宽的分区，排队更慢）
HPC_PARTITION_WIDE = "v6_384"


def intel_mpi_lib_dirs() -> List[str]:
    """Intel MPI 库目录（**顺序敏感**）。

    ★ `lib/release` 必须在前：`libmpifort.so.12` 只在 `mpi/latest/lib/`，
      而 `MPII_F_TRUE` 是**导入**符号（nm: U），必须由
      `mpi/latest/lib/release/libmpi.so.12` 提供（nm: R 已定义）。
      顺序颠倒 ⇒ 计算节点上其它 libmpi.so.12 副本抢先加载 ⇒
      `symbol lookup error: libmpifort.so.12: undefined symbol: MPII_F_TRUE`
      （ch_center 场景 2026-10-24 作业 4921721 FAILED 127 同款事故）。
    """
    return [INTEL_MPI_LIB_RELEASE, INTEL_MPI_LIB]


def build_env(base: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """构造**不依赖 module** 的编译/运行环境。

    ★ 铁律（超算实测）：**不要 `module load`**。module 会设
      LIBRARY_PATH/CPATH 指向旧 Intel 2018 环境，屏蔽 oneAPI 2022.1
      自带的 libmpifort ⇒ 链接期 `cannot find -lmpifort/-lmpi`。
      FLASH 的 Makefile.h 已硬编码编译器与 HDF5 路径 ⇒ 无需 module。

    Args:
        base: 基础环境（默认 `os.environ`）。

    Returns:
        新环境字典：PATH 追加 Intel MPI bin，
        LIBRARY_PATH / LD_LIBRARY_PATH 前置 Intel MPI 库目录。
    """
    env = dict(base if base is not None else os.environ)
    libs = intel_mpi_lib_dirs()
    env["PATH"] = f"{INTEL_MPI_BIN}{os.pathsep}{env.get('PATH', '')}"
    env["LIBRARY_PATH"] = os.pathsep.join(
        [*libs, env.get("LIBRARY_PATH", "")]).rstrip(os.pathsep)
    env["LD_LIBRARY_PATH"] = os.pathsep.join(
        [*libs, HDF5_LIB, env.get("LD_LIBRARY_PATH", "")]).rstrip(os.pathsep)
    return env


def shell_exports(indent: str = "") -> str:
    """生成可直接嵌入 sbatch 脚本的 shell 导出片段。

    用法（场景脚本模板里）::

        exports = shell_exports()
        # → export PATH=...; export LIBRARY_PATH=...; ...

    ★ 脚本模板里出现 `/public1/soft` 会触发架构护栏 R-SCENE-05 ⇒
      场景层只调本函数取值，不硬编码装置路径。
    """
    libs = intel_mpi_lib_dirs()
    lib_path = ":".join(libs)
    return (
        f"{indent}export PATH={INTEL_MPI_BIN}:$PATH\n"
        f"{indent}export LIBRARY_PATH={lib_path}:${{LIBRARY_PATH:-}}\n"
        f"{indent}export LD_LIBRARY_PATH={lib_path}:{HDF5_LIB}:${{LD_LIBRARY_PATH:-}}\n"
    )


def partition() -> str:
    """作业分区名（可用环境变量覆盖）。"""
    return os.environ.get("FLASH_HPC_PARTITION", "").strip() or HPC_PARTITION


def main() -> int:
    """打印当前装置参数（诊断用）。"""
    print(f"ONEAPI_ROOT    = {ONEAPI_ROOT}")
    print(f"INTEL_MPI_BIN  = {INTEL_MPI_BIN}")
    print(f"INTEL_MPI_LIB  = {INTEL_MPI_LIB}")
    print(f"INTEL_MPI_LIB_RELEASE = {INTEL_MPI_LIB_RELEASE}")
    print(f"HDF5_LIB       = {HDF5_LIB}")
    print(f"HPC_PARTITION  = {partition()}")
    print("--- shell_exports ---")
    print(shell_exports(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
