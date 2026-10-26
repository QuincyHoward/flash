# -*- coding: utf-8 -*-
"""devices.py — 超算**装置参数**唯一事实源（分区 / 模块 / 库路径）。

★ 为什么需要这个模块（2026-10-26 架构护栏 R-SCENE-05 实测）：
  场景层的 sbatch 脚本里**不得**出现装置参数（分区名、模块路径、
  `/public1/soft/...` 绝对路径）—— 换机器即静默失效，且不同场景
  各写一份必然漂移。规则 R-SCENE-05 的提示原文：
  "装置参数（账户/分区/模块）应下沉 flash_run/env/devices.py 或凭据配置"。

  ★ 事故背景（超算实测，作业 4924449 FAILED）：
    早期场景自带的 sbatch 脚本**完全不加载 module** ⇒
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

#: SLURM 的 PMI 库目录（★ Intel MPI 走 srun 时**必须**可见，否则
#: "slurmstepd: error: mpi/pmi2: invalid client request" +
#: "Fatal error in PMII_Init" ⇒ 作业 CANCELLED。实测超算既有
#: libpmi.so（PMI1）与 libpmi2.so（PMI2），缺任一都会失败。）
SLURM_LIB = "/opt/slurm/slurm/lib"

#: oneAPI 编译器**运行时**库目录（libimf / libsvml / libirng / libintlc）
#: ★ 二进制由 Intel MPI 编译 ⇒ 运行期依赖这些库；不在 LD_LIBRARY_PATH
#:   里则 "./flash4: error while loading shared libraries: libimf.so"。
ONEAPI_RT_LIB = f"{ONEAPI_ROOT}/compiler/2022.0.0/linux/compiler/lib/intel64_lin"

#: Intel 2018 发行版里的 MPI 库（★ **运行阶段**用这一套，见
#: runtime_lib_dirs 注释）
INTEL2018_ROOT = f"{SOFT_ROOT}/intel/2018/compilers_and_libraries_2018.2.199/linux"
INTEL2018_MPI_LIB = f"{INTEL2018_ROOT}/mpi/intel64/lib"

#: Intel 2018 的 MPI bin（运行阶段 PATH：mpirun / mpiifort 等）
INTEL2018_MPI_BIN = f"{INTEL2018_ROOT}/mpi/intel64/bin"

#: GCC 运行时库目录（libgfortran.so.5 等）
#: ★ 实测：`gcc/9.3.0/lib64` **不存在**，实际在 `gcc/9.3.0-new/lib64`
GCC_LIB = f"{SOFT_ROOT}/gcc/9.3.0-new/lib64"

#: 作业分区（★ 不写进场景脚本；由本模块提供）
HPC_PARTITION = "v5_192"

#: 可选分区（更宽的分区，排队更慢）
HPC_PARTITION_WIDE = "v6_384"

# ── 装置默认值（2026-10-26 从 resource_config 迁入）────────────────
#: 与场景**无关**的装置档位：计费账户名 / 登录节点 venv 目录名 / 装置分类。
#:
#: ★ 为什么在这里：这些是**站点事实**（哪个账户、哪个 venv），
#:   任何场景都能用 ⇒ 属执行层的装置事实源；
#:   而"某场景族该用多少核"是**网格事实** ⇒ 归场景层
#:   `flash.scenarios.device_defaults`。
DEVICE_DEFAULTS: Dict[str, str] = {
    # 超算计费账户名（凭据名，与 ~/.physimx/flash/hpc_accounts.json 对应）
    "account": "flash_ssh",
    # 登录节点 venv 目录名（离线安装链创建）
    "insitu_venv": ".venv-hpc-nce",
    # 装置分类（hpc / laptop / desktop —— 见 resource_config.classify_device）
    "device": "hpc",
}


def device_default(key: str, default: str = "") -> str:
    """取装置默认值（`DEVICE_DEFAULTS` 的只读访问口）。

    环境变量 `FLASH_<KEY>` 可覆盖（如 `FLASH_ACCOUNT`）。

    用法::

        from flash.flash_run.env.devices import device_default
        ACCOUNT = device_default("account")     # → flash_ssh
    """
    env_key = "FLASH_" + key.upper()
    override = os.environ.get(env_key, "").strip()
    if override:
        return override
    return DEVICE_DEFAULTS.get(key, default)



def intel_mpi_lib_dirs() -> List[str]:
    """Intel MPI 库目录（**顺序敏感**）。

    ★ `lib/release` 必须在前：`libmpifort.so.12` 只在 `mpi/latest/lib/`，
      而 `MPII_F_TRUE` 是**导入**符号（nm: U），必须由
      `mpi/latest/lib/release/libmpi.so.12` 提供（nm: R 已定义）。
      顺序颠倒 ⇒ 计算节点上其它 libmpi.so.12 副本抢先加载 ⇒
      `symbol lookup error: libmpifort.so.12: undefined symbol: MPII_F_TRUE`
      （作业 4921721 FAILED 127 同款事故）。
    """
    return [INTEL_MPI_LIB_RELEASE, INTEL_MPI_LIB]


def runtime_lib_dirs() -> List[str]:
    """**运行阶段**需要的库目录（顺序敏感）。

    ★ 顺序：Intel 2018 MPI → SLURM PMI → HDF5 → oneAPI runtime → GCC runtime。
      - Intel 2018 MPI 放最前：★ 该集群上已验证跑通的一次作业
        （作业 4924413 COMPLETED，341 chk）用的就是这套。实测对照（超算，同一二进制）：
          oneAPI 2022.1 的 lib/release + lib  ⇒ MPI_Init SIGSEGV
                                              （forrtl severe 174）
          Intel 2018 的 mpi/intel64/lib       ⇒ 正常启动（仅缺 libimf）
        ⇒ 二进制虽由 oneAPI 2022.1 编译，但其 mpiifort 实际是
          **Intel MPI 2021.5.0**（与 2018 目录里那份同版本）⇒ 2018 路径
          的 libmpi 与之 ABI 兼容。
      - SLURM PMI：Intel MPI 走 srun 的前提（否则 "mpi/pmi2: invalid
        client request" ⇒ 作业 CANCELLED）。
      - oneAPI runtime：libimf/libsvml/libirng/libintlc（Intel 编译产物
        的运行期依赖）。
      - GCC runtime：libgfortran.so.5。

    ★★ **不要** `module load mpich/3.2-gcc9.3`：它把 LD_LIBRARY_PATH 指向
      **Intel 2018** 的 MPI —— 虽然本模块也用 2018 路径，但顺序与 module
      注入的混杂会导致旧副本抢先加载 ⇒ 稳妥做法是运行阶段**不加载
      mpich 模块**，只加载 hdf5/1.8.18（提供 libhdf5.so.10），
      其余库全部由本模块的显式路径提供（module 后必须重新 export）。
    """
    return [INTEL2018_MPI_LIB, SLURM_LIB, HDF5_LIB, ONEAPI_RT_LIB, GCC_LIB]


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


#: 场景脚本模板里可用的占位符 → 取值函数
TEMPLATE_TOKENS = {
    "@DEV_EXPORTS@": shell_exports,
    # ★ 运行阶段的 MPI 工具链用 **2018** 目录（其 mpiifort = Intel MPI
    #   2021.5.0，与 oneAPI 2022.1 自带的同版本 ⇒ ABI 兼容；
    #   而 oneAPI 的 lib/release 组合实测 MPI_Init SIGSEGV）。
    "@IMPI_BIN@": lambda: INTEL2018_MPI_BIN,
    "@IMPI_LIBS@": lambda: ":".join(intel_mpi_lib_dirs()),
    "@HDF5_LIB@": lambda: HDF5_LIB,
    "@RUNTIME_LIBS@": lambda: ":".join(runtime_lib_dirs()),
    "@SLURM_LIB@": lambda: SLURM_LIB,
    # ★ 运行阶段 PATH 用 2018 的 mpi bin（其 mpirun/hydra 与 2018 库匹配）
    "@RUNTIME_BIN@": lambda: INTEL2018_MPI_BIN,
}

#: 必须**独占一行**的占位符（其值是**多行** shell 片段，接在行尾会让
#: 首行被注释吞掉、后续行裸露执行 ⇒ bash 语法错；
#: 超算实测作业 4924488: "line 25: ）。: command not found"）
MULTILINE_TOKENS = ("@DEV_EXPORTS@",)


def render_template(content: str) -> str:
    """渲染场景脚本模板里的装置参数占位符。

    ★ **多行**占位符（见 MULTILINE_TOKENS）必须独占一行；
      **单行**占位符（路径等）可内联在 export 语句中。
      违反前者时显式 raise，避免同类问题静默进入产物。
    """
    for i, line in enumerate(content.splitlines(), 1):
        for tok in MULTILINE_TOKENS:
            if tok in line and line.strip() != tok:
                raise ValueError(
                    f"多行占位符 {tok} 必须独占一行（第 {i} 行: {line!r}）"
                    " —— 否则渲染后首条 export 会被注释吞掉"
                    "（超算作业 4924488 实测教训）")
    out = content
    for tok, fn in TEMPLATE_TOKENS.items():
        out = out.replace(tok, fn())
    return out


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
