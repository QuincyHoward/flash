#!/bin/bash
#SBATCH -J grad_dens_sandwich
#SBATCH -o grad_dens_sandwich_%j.out
#SBATCH -e grad_dens_sandwich_%j.err
#SBATCH -N 1
#SBATCH -n 7
#SBATCH --time=01:00:00

set -e
SIM_NAME="grad_dens_sandwich"
RUN_ID="${2:-000001}"
# ★★ 2026-10-26 实测修复（链接失败 'ld: cannot find -lmpifort/-lmpi'）：
#   根因 = **任何 `module load` 都会污染 ifort/mpiifort 的隐式 MPI 库路径**
#   （module 设的 LIBRARY_PATH/CPATH 指向旧 Intel 2018 环境，屏蔽了
#     oneAPI 2022.1 自带的 libmpifort）⇒ 链接必 FAIL。
#   实测对照（超算）：无 module ⇒ OK；load mpich ⇒ FAIL；
#     load hdf5/1.8.18 ⇒ FAIL（连显式 -L 都救不回）。
#   ★ 而 FLASH 的 Makefile.h 已**硬编码**绝对路径 ⇒ 本就不需要任何 module。
#   ⇒ 解法：不加载 module，改用绝对路径 + 显式 LIBRARY_PATH/LD_LIBRARY_PATH。
# ★ 装置参数（Intel MPI / HDF5 路径）**不在场景层硬编码**（架构护栏
#   R-SCENE-05）—— 由 flash.flash_run.env.devices 统一提供，
#   生成器在写文件时渲染进脚本（占位符见下一行）。
#   ★ 占位符必须**独占一行**（不能接在注释行尾）：否则渲染后首条 export
#   会被注释吞掉、后续行裸露执行 ⇒ bash 语法错（实测作业 4924488
#   "line 25: ）。: command not found"）。
export PATH=/public1/soft/oneAPI/2022.1/mpi/latest/bin:$PATH
export LIBRARY_PATH=/public1/soft/oneAPI/2022.1/mpi/latest/lib/release:/public1/soft/oneAPI/2022.1/mpi/latest/lib:${LIBRARY_PATH:-}
export LD_LIBRARY_PATH=/public1/soft/oneAPI/2022.1/mpi/latest/lib/release:/public1/soft/oneAPI/2022.1/mpi/latest/lib:/public1/soft/hdf5/1.8.18/lib:${LD_LIBRARY_PATH:-}

F=$HOME/${FLASH_SIM_USER_DIR:-QC}/FLASH/FLASH4.8
S=$F/source/Simulation/SimulationMain/QC/${SIM_NAME}_${RUN_ID}
O=$F/QC/object_${SIM_NAME}_${RUN_ID}
R=/tmp/flash_${SIM_NAME}_$$

mkdir -p "$S"
# ★★ 2026-10-26 实测修复：sbatch 下 `$0` = spool 目录里的脚本副本
#   （/var/spool/slurm/d/jobNNNN/），**不是**提交目录 ⇒ `dirname "$0"`
#   解析出的路径里没有 par/cn4 ⇒ 作业立刻 FAILED：
#     "cp: cannot stat '/var/spool/slurm/d/job4924446/*.par': No such file"
#   ⇒ 优先用 SLURM_SUBMIT_DIR（提交时的 cwd），退回 PWD；
#     两者都不含 par 时才用 dirname（直接 bash 执行的场景）。
#   ★ glob 在 [ ] 内不展开 ⇒ 用 compgen 计数做判据。
SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$PWD}"
_n_par=$(compgen -G "$SCRIPT_DIR/*.par" | wc -l)
if [ "$_n_par" -eq 0 ]; then
    echo "  SCRIPT_DIR 无 par 文件，回退 dirname \$0"
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
fi
echo "  SCRIPT_DIR = $SCRIPT_DIR (par x $(compgen -G "$SCRIPT_DIR/*.par" | wc -l))"
for f in Config Simulation_data.F90 Simulation_init.F90 Simulation_initBlock.F90 Grid_markRefineDerefine.F90 Makefile *.cn4; do
    [ -f "$SCRIPT_DIR/$f" ] && cp "$SCRIPT_DIR/$f" "$S/"
done
cp "$SCRIPT_DIR"/*.par "$S/${SIM_NAME}_${RUN_ID}.par"

cd $F
# ★ 复用已编译二进制（2026-10-26）：原脚本无条件 `rm -rf "$O"` + setup
#   + make，每轮重编约 2 分钟，迭代时极慢。与 ch_center 场景一致：
#   二进制存在即跳过编译。★ 用不同 RUN_ID 可并存多套二进制。
if [ -x "$O/flash4" ]; then
    echo "  [compile] 二进制已存在，跳过 setup+make: $O/flash4"
else
    rm -rf "$O"
    ./setup -auto "QC/${SIM_NAME}_${RUN_ID}" -1d +cartesian -nxb=16 -maxblocks=2048 +hdf5typeio species=cham,targ,poly +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 ed_maxPulseSections=240 -objdir="QC/object_${SIM_NAME}_${RUN_ID}"
    cd $O
    make -j7
fi

mkdir -p "$R"
cp $O/flash4 "$R/"
cp "$S"/*.cn4 "$R/"
cp "$S/${SIM_NAME}_${RUN_ID}.par" "$R"/flash.par
cd "$R"

# ★★ 2026-10-26 运行阶段环境（两阶段策略，实测必需）：
#   编译/链接阶段**必须无模块**（module 会屏蔽 oneAPI 自带的 libmpifort
#   ⇒ 链接期 'cannot find -lmpifort/-lmpi'）；
#   但**运行阶段需要模块** —— 二进制依赖 libgfortran.so.5 与
#   libhdf5.so.10，这两个库只在模块环境里可见（实测：加载模块后
#   `ldd flash4 | grep "not found"` 为空；无模块则 libhdf5/libgfortran
#   全部 not found ⇒ 运行即失败）。
#   ⇒ 运行前再加载一次模块（编译已完成，不影响已生成的二进制）。
# ★★ 运行阶段环境（2026-10-26 实测，与 ch_center 已验证路径对齐）：
#   ① module purge（**必须**）：不清空会与登录节点残留环境混杂。
#   ② ★★ **不加载 mpich/3.2-gcc9.3**！它把 LD_LIBRARY_PATH 指向
#      **Intel 2018** 的 MPI ⇒ 加载旧版 libmpi.so.12，与 oneAPI 2022.1
#      编译的二进制版本不匹配 ⇒ MPI_Init 处 SIGSEGV
#      （forrtl: severe (174)，实测作业 4924506）。
#      只加载 hdf5/1.8.18（提供 libhdf5.so.10）；其余库由 /public1/soft/oneAPI/2022.1/mpi/latest/lib/release:/public1/soft/oneAPI/2022.1/mpi/latest/lib:/opt/slurm/slurm/lib:/public1/soft/hdf5/1.8.18/lib:/public1/soft/oneAPI/2022.1/compiler/2022.0.0/linux/compiler/lib/intel64_lin:/public1/soft/gcc/9.3.0/lib64 提供。
#   ③ 编译/链接阶段**不能**有 module（会屏蔽 oneAPI 自带的 libmpifort
#      ⇒ 链接期 'cannot find -lmpifort/-lmpi'）⇒ module 只在
#      **编译完成之后**的运行阶段加载（两阶段环境）。
module purge >/dev/null 2>&1
module load hdf5/1.8.18 >/dev/null 2>&1
# 完整运行库路径：Intel MPI 2022.1 (release:lib) → SLURM PMI → HDF5
#                → oneAPI runtime (libimf/libsvml/...) → GCC runtime
# ★ module 会覆盖 LD_LIBRARY_PATH ⇒ 必须在 module 之后重新导出。
export LIBRARY_PATH="/public1/soft/oneAPI/2022.1/mpi/latest/lib/release:/public1/soft/oneAPI/2022.1/mpi/latest/lib:/opt/slurm/slurm/lib:/public1/soft/hdf5/1.8.18/lib:/public1/soft/oneAPI/2022.1/compiler/2022.0.0/linux/compiler/lib/intel64_lin:/public1/soft/gcc/9.3.0/lib64:${LIBRARY_PATH:-}"
export LD_LIBRARY_PATH="/public1/soft/oneAPI/2022.1/mpi/latest/lib/release:/public1/soft/oneAPI/2022.1/mpi/latest/lib:/opt/slurm/slurm/lib:/public1/soft/hdf5/1.8.18/lib:/public1/soft/oneAPI/2022.1/compiler/2022.0.0/linux/compiler/lib/intel64_lin:/public1/soft/gcc/9.3.0/lib64:${LD_LIBRARY_PATH:-}"
export PATH="/public1/soft/oneAPI/2022.1/mpi/latest/bin:$PATH"

# ★ 用 srun（2026-10-26 实测）：与 ch_center 场景**已验证成功**的路径一致。
#   Intel MPI 经 SLURM 的 PMI2 启动（SLURM 提供 libpmi2.so，必须在
#   LD_LIBRARY_PATH 里 —— 见 /public1/soft/oneAPI/2022.1/mpi/latest/lib/release:/public1/soft/oneAPI/2022.1/mpi/latest/lib:/opt/slurm/slurm/lib:/public1/soft/hdf5/1.8.18/lib:/public1/soft/oneAPI/2022.1/compiler/2022.0.0/linux/compiler/lib/intel64_lin:/public1/soft/gcc/9.3.0/lib64）。
#   ✗ 不用 mpirun：hydra bootstrap 在 SLURM 作业内与 SLURM 的进程分配
#     打架（实测作业 4924502：MPI_Init 处 abort，exit 46）。
srun -n ${SLURM_NTASKS:-7} ./flash4
echo "=== Output: $R ==="
