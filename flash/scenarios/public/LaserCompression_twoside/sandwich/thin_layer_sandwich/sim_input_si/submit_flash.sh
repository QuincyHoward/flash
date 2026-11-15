#!/bin/bash
# =====================================================================
# 提交脚本（**薄委托**）—— 2026-10-26 架构调整
#
# ★ 为什么是薄委托：上一版把完整的 sbatch 作业体（拷源文件 → setup →
#   编译 → 运行）**内联在场景模板里**，于是同一件事有两份实现
#   （本文件 + 统一提交入口）⇒ 必然漂移。
#   实测已漂移过一次：模板里写着"编译放登录节点"（已被计算节点实测证伪），
#   而统一入口里写的是"编译放计算节点 scratch"。
#
# ⇒ 现在：**作业体只有一份**，由 flash.flash_run.remote.job_scripts 渲染
#   （stage → build → run → archive，全程在计算节点节点本地 scratch）。
#   场景层只声明"场景是什么"（见 flash.scenarios.core.hpc_job）。
#
# 用法（推荐 —— 统一入口，负责生成输入 + 渲染 + 提交）：
#   python -m flash.scenarios.core.cli submit thin_layer_sandwich_si --run-id 000002
#
# 用法（本文件 —— 兜底，直接 sbatch 已生成好的输入）：
#   sbatch submit_flash.sh 000002
# =====================================================================
set -e
# ★ 本场景的 FLASH 单元名固定为 `grid_rede`（**不带** run_id 后缀），
#   与统一提交入口 flash.scenarios.core.hpc_job 的声明一致。
SIM_NAME="grid_rede"
SCENE_NAME="thin_layer_sandwich_si"
RUN_ID="${2:-000001}"

echo "[submit_flash] 兜底路径（直接 sbatch 已生成的输入）。"
echo "[submit_flash] 推荐：python -m flash.scenarios.core.cli submit $SCENE_NAME --run-id $RUN_ID"
echo "[submit_flash] （统一入口会在计算节点 scratch 内完成 拷贝→setup→编译→运行→归档）"

# 装置参数（Intel MPI / HDF5 路径）由 flash.flash_run.env.devices 统一提供
# （架构护栏 R-SCENE-05）；生成器在写文件时渲染进脚本。
# ★ 占位符必须**独占一行**（不能接在注释行尾）：否则渲染后首条 export
#   会被注释吞掉、后续行裸露执行 ⇒ bash 语法错（实测作业 4924488
#   "line 25: ）。: command not found"）。
export PATH=/public1/soft/oneAPI/2022.1/mpi/latest/bin:$PATH
export LIBRARY_PATH=/public1/soft/oneAPI/2022.1/mpi/latest/lib/release:/public1/soft/oneAPI/2022.1/mpi/latest/lib:${LIBRARY_PATH:-}
export LD_LIBRARY_PATH=/public1/soft/oneAPI/2022.1/mpi/latest/lib/release:/public1/soft/oneAPI/2022.1/mpi/latest/lib:/public1/soft/hdf5/1.8.18/lib:${LD_LIBRARY_PATH:-}

F=$HOME/${FLASH_SIM_USER_DIR:-QC}/FLASH/FLASH4.8
S=$F/source/Simulation/SimulationMain/QC/${SIM_NAME}
O=$F/QC/object_${SIM_NAME}
# 产物目录放**并行盘**：计算节点跑完的 chk 在登录节点看不到节点本地盘。
R="${SLURM_SUBMIT_DIR:-$PWD}/run_${SIM_NAME}_${RUN_ID}_$$"

mkdir -p "$S"
# ★★ sbatch 下 `$0` = spool 目录里的脚本副本（/var/spool/slurm/d/jobNNNN/），
#   **不是**提交目录 ⇒ `dirname "$0"` 解析出的路径里没有 par/cn4
#   ⇒ 作业立刻 FAILED："cp: cannot stat '.../jobNNNN/*.par': No such file"
#   ⇒ 优先用 SLURM_SUBMIT_DIR（提交时的 cwd），退回 PWD。
#   ★ glob 在 [ ] 内不展开 ⇒ 用 compgen 计数做判据。
SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$PWD}"
_n_par=$(compgen -G "$SCRIPT_DIR/*.par" | wc -l)
if [ "$_n_par" -eq 0 ]; then
    echo "  SCRIPT_DIR 无 par 文件，回退 dirname \$0"
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
fi
echo "  SCRIPT_DIR = $SCRIPT_DIR (par x $(compgen -G "$SCRIPT_DIR/*.par" | wc -l))"

cd $F
# ★★ 编译位置（2026-10-26 实测**修正**）：
#   上一版把「编译必须放登录节点」当成铁律，据此让登录节点预编译。
#   **计算节点实测证伪**（作业 4924747/4924748/4924752/4924760）：
#     · GPFS 上 os.walk 2811 文件 = 0.2 s、建 500 符号链接 = 1.08 s
#     · setup_depends.py = 21.7 s（不是"11 分钟不出 .o"）
#     · 计算节点 scratch 上 setup = 2 s、make -j16 = 31 s（1550 个 .o）
#   ⇒ 真正的规律是：**别把编译中间产物写在慢速共享盘上**，
#     而不是"只能在登录节点编译"。
#   ⇒ 统一入口把编译放在**计算节点的节点本地 scratch** 内完成；
#     本兜底路径 objdir 在共享盘上 ⇒ make 慢，但正确。
if [ -x "$O/flash4" ]; then
    echo "  [compile] 二进制已存在（上次编译产物），跳过 make"
else
    if [ ! -f "$O/Makefile" ]; then
        echo "  [FATAL] objdir 无 Makefile —— 请用统一提交入口："
        echo "         python -m flash.scenarios.core.cli submit $SCENE_NAME --run-id $RUN_ID"
        exit 2
    fi
    cd $O
    make -j7
fi

mkdir -p "$R"
cp $O/flash4 "$R"/
cp "$S"/*.cn4 "$R"/
cp "$S"/grid_rede.par "$R"/flash.par
cd "$R"
# ★★ 运行阶段环境（两阶段策略，实测必需）：
#   编译/链接阶段**必须无模块**（module 会屏蔽 oneAPI 自带的 libmpifort
#   ⇒ 链接期 'cannot find -lmpifort/-lmpi'）；
#   但**运行阶段需要模块** —— 二进制依赖 libgfortran.so.5 与
#   libhdf5.so.10，这两个库只在模块环境里可见。
# ★★ module purge 必须；★★ **不加载 mpich/3.2-gcc9.3**（它把 LD_LIBRARY_PATH
#   指向 Intel 2018 的 MPI ⇒ 与 oneAPI 2022.1 编译的二进制版本不匹配
#   ⇒ MPI_Init 处 SIGSEGV forrtl severe(174)，实测作业 4924506）。
module purge >/dev/null 2>&1
module load hdf5/1.8.18 >/dev/null 2>&1
export LIBRARY_PATH="/public1/soft/intel/2018/compilers_and_libraries_2018.2.199/linux/mpi/intel64/lib:/opt/slurm/slurm/lib:/public1/soft/hdf5/1.8.18/lib:/public1/soft/oneAPI/2022.1/compiler/2022.0.0/linux/compiler/lib/intel64_lin:/public1/soft/gcc/9.3.0-new/lib64:${LIBRARY_PATH:-}";export LD_LIBRARY_PATH="/public1/soft/intel/2018/compilers_and_libraries_2018.2.199/linux/mpi/intel64/lib:/opt/slurm/slurm/lib:/public1/soft/hdf5/1.8.18/lib:/public1/soft/oneAPI/2022.1/compiler/2022.0.0/linux/compiler/lib/intel64_lin:/public1/soft/gcc/9.3.0-new/lib64:${LD_LIBRARY_PATH:-}";export PATH="/public1/soft/intel/2018/compilers_and_libraries_2018.2.199/linux/mpi/intel64/bin:$PATH"
# ★ 用 srun（已验证成功的路径）：Intel MPI 经 SLURM 的 PMI2 启动
#   （SLURM 的 libpmi2.so 必须在 LD_LIBRARY_PATH 里，见 /public1/soft/intel/2018/compilers_and_libraries_2018.2.199/linux/mpi/intel64/lib:/opt/slurm/slurm/lib:/public1/soft/hdf5/1.8.18/lib:/public1/soft/oneAPI/2022.1/compiler/2022.0.0/linux/compiler/lib/intel64_lin:/public1/soft/gcc/9.3.0-new/lib64）。
#   ✗ 不用 mpirun：hydra bootstrap 在 SLURM 作业内 MPI_Init 处 abort
#     （实测作业 4924502 exit 46）。
srun -n ${SLURM_NTASKS:-7} ./flash4
echo "=== Output: $R ==="
