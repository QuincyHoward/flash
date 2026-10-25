#!/bin/bash
#SBATCH --job-name=grid_rede --output=grid_rede_%j.log --partition=v5_192 --ntasks=4 --time=01:00:00
F=$HOME/${FLASH_SIM_USER_DIR:-QC}/FLASH/FLASH4.8;S=$F/source/Simulation/SimulationMain/QC/grid_rede;O=$F/QC/object_grid_rede
R="${SLURM_SUBMIT_DIR:-$PWD}/grid_rede_run_$$"
# ★★ 2026-10-26 实测修复：sbatch 下 `$0` = spool 目录里的脚本副本
#   （/var/spool/slurm/d/jobNNNN/），不是提交目录 ⇒ `dirname "$0"`
#   解析出的路径没有 par/cn4 ⇒ 作业立刻 FAILED
#   （grad_dens_sandwich 实测："cp: cannot stat '.../jobNNNN/*.par'"）。
#   ⇒ 优先 SLURM_SUBMIT_DIR，退回 PWD，最后才用 dirname（直接 bash 场景）。
D=${SLURM_SUBMIT_DIR:-$PWD};_np=$(compgen -G "$D/*.par" | wc -l);[ "$_np" -eq 0 ] && D=$(dirname "$0");echo "  D = $D (par x $(compgen -G "$D/*.par" | wc -l))"
# ★★ 2026-10-26 实测修复（链接失败 'ld: cannot find -lmpifort/-lmpi'）：
#   根因 = **任何 `module load` 都会污染 ifort/mpiifort 的隐式 MPI 库路径**
#   （module 设的 LIBRARY_PATH/CPATH 指向旧 Intel 2018 环境，屏蔽了
#     oneAPI 2022.1 自带的 libmpifort）⇒ 链接必 FAIL。
#   实测对照（超算）：无 module ⇒ OK；load mpich ⇒ FAIL；
#     load hdf5/1.8.18 ⇒ FAIL（连显式 -L 都救不回）。
#   ★ FLASH 的 Makefile.h 已**硬编码**绝对路径 ⇒ 本就不需要任何 module。
#   ⇒ 解法：不加载 module，改用绝对路径 + 显式 LIBRARY_PATH/LD_LIBRARY_PATH。
# ★ 装置参数**不在场景层硬编码**（架构护栏 R-SCENE-05）——
#   由 flash.flash_run.env.devices 统一提供，生成器渲染进脚本（占位符见下一行）。
#   ★ 占位符必须**独占一行**（不能接在注释行尾）：否则渲染后首条 export
#   会被注释吞掉、后续行裸露执行 ⇒ bash 语法错（超算作业 4924488 实测教训）。
export PATH=/public1/soft/oneAPI/2022.1/mpi/latest/bin:$PATH
export LIBRARY_PATH=/public1/soft/oneAPI/2022.1/mpi/latest/lib/release:/public1/soft/oneAPI/2022.1/mpi/latest/lib:${LIBRARY_PATH:-}
export LD_LIBRARY_PATH=/public1/soft/oneAPI/2022.1/mpi/latest/lib/release:/public1/soft/oneAPI/2022.1/mpi/latest/lib:/public1/soft/hdf5/1.8.18/lib:${LD_LIBRARY_PATH:-}

mkdir -p "$R"; cd $F
# ★★ 源文件拷贝 / setup / **编译**都**在登录节点**完成
#   （2026-10-26 实测）：FLASH 的 make 首步 setup_depends.py 要 os.walk
#   扫描 1500+ 源文件 —— 该步骤在**计算节点**上 11 分钟不出 .o
#   （objdir 1748 条目 / .o 恒为 0），在**登录节点**上秒级完成
#   （Makefile.Depend 352 KB）。⇒ 编译放登录节点，本脚本只运行。
#   ★ 兜底：若二进制不存在（登录节点编译被跳过），此处补编一次。
if [ -x "$O/flash4" ]; then
  echo "  [compile] 二进制已存在（登录节点已编译），跳过 make"
else
  if [ ! -f "$O/Makefile" ]; then
    echo "  [FATAL] objdir 无 Makefile —— 请用 deploy/hpc_deploy/submit_sandwich.py 提交"
    echo "         （它会在登录节点完成 拷贝→setup→编译）"
    exit 2
  fi
  cd $O; make -j7
fi
cp $O/flash4 "$R"/;cp "$S"/*.cn4 "$R"/;cp "$S"/grid_rede.par "$R"/flash.par;cd "$R"
# ★★ 2026-10-26 运行阶段环境（两阶段策略，实测必需）：
#   编译/链接阶段**必须无模块**（module 会屏蔽 oneAPI 自带的 libmpifort
#   ⇒ 链接期 'cannot find -lmpifort/-lmpi'）；
#   但**运行阶段需要模块** —— 二进制依赖 libgfortran.so.5 与
#   libhdf5.so.10，这两个库只在模块环境里可见（实测：加载模块后
#   `ldd flash4 | grep "not found"` 为空）。
# ★★ 运行阶段环境（2026-10-26 实测）：module purge 必须；★★ **不加载
#   mpich/3.2-gcc9.3**（它把 LD_LIBRARY_PATH 指向 Intel 2018 的 MPI ⇒
#   与 oneAPI 2022.1 编译的二进制版本不匹配 ⇒ MPI_Init SIGSEGV
#   forrtl severe(174)，实测作业 4924506）。只加载 hdf5/1.8.18。
module purge >/dev/null 2>&1
module load hdf5/1.8.18 >/dev/null 2>&1
export LIBRARY_PATH="/public1/soft/intel/2018/compilers_and_libraries_2018.2.199/linux/mpi/intel64/lib:/opt/slurm/slurm/lib:/public1/soft/hdf5/1.8.18/lib:/public1/soft/oneAPI/2022.1/compiler/2022.0.0/linux/compiler/lib/intel64_lin:/public1/soft/gcc/9.3.0-new/lib64:${LIBRARY_PATH:-}";export LD_LIBRARY_PATH="/public1/soft/intel/2018/compilers_and_libraries_2018.2.199/linux/mpi/intel64/lib:/opt/slurm/slurm/lib:/public1/soft/hdf5/1.8.18/lib:/public1/soft/oneAPI/2022.1/compiler/2022.0.0/linux/compiler/lib/intel64_lin:/public1/soft/gcc/9.3.0-new/lib64:${LD_LIBRARY_PATH:-}";export PATH="/public1/soft/intel/2018/compilers_and_libraries_2018.2.199/linux/mpi/intel64/bin:$PATH"
# ★ 用 srun（2026-10-26 实测）：与 ch_center 场景**已验证成功**的路径一致。
#   Intel MPI 经 SLURM 的 PMI2 启动（SLURM 的 libpmi2.so 必须在
#   LD_LIBRARY_PATH 里，见 /public1/soft/intel/2018/compilers_and_libraries_2018.2.199/linux/mpi/intel64/lib:/opt/slurm/slurm/lib:/public1/soft/hdf5/1.8.18/lib:/public1/soft/oneAPI/2022.1/compiler/2022.0.0/linux/compiler/lib/intel64_lin:/public1/soft/gcc/9.3.0-new/lib64）。
#   ✗ 不用 mpirun：hydra bootstrap 在 SLURM 作业内 MPI_Init 处 abort
#     （实测作业 4924502 exit 46）；✗ 不用无 PMI 路径的裸 srun
#     （报 "mpi/pmi2: invalid client request"，实测作业 4924491）。
srun -n ${SLURM_NTASKS:-4} ./flash4
