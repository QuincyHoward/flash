#!/bin/bash
# ============================================================
# FLASH 4.8 — 超算首次配置安装方案
# HPC First Setup Script (Paracloud / SLURM 环境)
# ============================================================
# 用途: 在超算（天河/Paracloud/HPC）上首次配置 FLASH
#       安装到 ~/${FLASH_SIM_USER_DIR:-<用户名>}/FLASH/FLASH4.8/
#       <用户名> 通过 flash._core.credentials 设置 (默认 hello)
#
# 超算环境特点:
#   - 使用 module 系统加载 MPI/HDF5 (无需从源码编译)
#   - HYPRE 需从源码编译 (module 通常不提供)
#   - 使用 SLURM sbatch 提交作业
#   - 无 root/sudo 权限
#
# 使用步骤:
#   1. 将 FLASH4.8.tar.gz / hypre-2.9.0b.tar.gz 上传到超算
#   2. 加载 module 环境
#   3. 执行本脚本
#
# 目前此脚本为"准备阶段"，不执行实际安装
# ============================================================

# ============================================================
# ⚠️  此脚本仅供参考和准备，不自动执行
#     请逐步手动执行或确认后取消注释运行
# ============================================================

set -e

# ============================================================
# 路径配置 (根据超算账号修改)
# ============================================================
# 示例: Paracloud 超算路径 (用户名通过 flash._core.credentials 设置, 勿硬编码)
# HPC_USER="sch0348"
# HPC_HOST="172.16.0.1"   # 超算登录节点 IP
# HPC_FLASH_HOME="/public1/wshome/ws173/${HPC_USER}/FLASH/FLASH4.8"

# 用户名解析: FLASH_SIM_USER_DIR 环境变量 → flash._core.credentials → 默认 hello
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/flash_user_lib.sh"
FLASH_SIM_USER_DIR="${FLASH_SIM_USER_DIR:-$(resolve_flash_user)}"

# FLASH_USER_HOME 仅作旧环境变量兼容 (值已动态化, 不含硬编码用户名)
FLASH_USER_HOME="${HOME}/${FLASH_SIM_USER_DIR}"
FLASH_PARENT="${FLASH_USER_HOME}/FLASH"
FLASH_HOME="${FLASH_PARENT}/FLASH4.8"
LOCAL_BUILD="${FLASH_USER_HOME}/FLASH/local"       # HYPRE 本地安装 (无 root)

HYPRE_PATH="${LOCAL_BUILD}/hypre"

HYPRE_TAR="hypre-2.9.0b.tar.gz"
HYPRE_DIR="hypre-2.9.0b"
FLASH_TAR="FLASH4.8.tar.gz"

# ============================================================
# Step 0 — 检查超算 module 环境
# ============================================================
echo "========================================"
echo "  [0/5] 检查 module 环境"
echo "========================================"

# 注意: 具体 module 名称因超算而异，以下为 Paracloud 示例
# source /public1/soft/modules/module.sh
# module load hdf5/1.8.18
# module load mpich/3.2-gcc9.3

# 验证 MPI 和 HDF5 已加载
echo "验证环境..."
echo "  mpicc:    $(which mpicc 2>/dev/null || echo '未找到 - 请先 module load mpich')"
echo "  h5pcc:    $(which h5pcc 2>/dev/null || echo '未找到 - 请先 module load hdf5')"
echo "  gfortran: $(which gfortran-9 2>/dev/null || which gfortran 2>/dev/null || echo '未找到')"
echo ""

# 设置从 module 获取的路径
MPI_PATH="$(dirname $(dirname $(which mpicc 2>/dev/null || echo '/usr/bin/mpicc')) 2>/dev/null || echo '/usr/local/mpich')"
HDF5_PATH="$(dirname $(dirname $(which h5pcc 2>/dev/null || echo '/usr/bin/h5pcc')) 2>/dev/null || echo '/usr/local/hdf5')"

echo "  MPI_PATH:  ${MPI_PATH}"
echo "  HDF5_PATH: ${HDF5_PATH}"
echo ""

# ============================================================
# Step 1 — 编译 HYPRE (无 sudo，安装到用户目录)
# ============================================================
echo "========================================"
echo "  [1/5] 编译 HYPRE → ${HYPRE_PATH}"
echo "========================================"

if ls "${HYPRE_PATH}/lib/libHYPRE"* &>/dev/null 2>&1; then
    echo "  SKIP: HYPRE 已安装"
else
    BUILD_TMP="${HOME}/tmp_flash_build"
    mkdir -p "${BUILD_TMP}"

    if [ ! -f "${BUILD_TMP}/${HYPRE_TAR}" ] && [ -f "./${HYPRE_TAR}" ]; then
        cp "./${HYPRE_TAR}" "${BUILD_TMP}/"
    fi

    if [ ! -f "${BUILD_TMP}/${HYPRE_TAR}" ]; then
        echo "  错误: 找不到 ${HYPRE_TAR}"
        echo "  请将压缩包放在当前目录并重新运行"
        exit 1
    fi

    cd "${BUILD_TMP}"
    rm -rf "${HYPRE_DIR}"
    tar -xzf "${HYPRE_TAR}"
    cd "${HYPRE_DIR}/src"

    mkdir -p "${HYPRE_PATH}"

    echo "  配置 HYPRE..."
    ./configure --prefix="${HYPRE_PATH}" \
        CC=mpicc CXX=mpicxx FC=gfortran F77=gfortran \
        2>&1 | tail -3

    echo "  编译 HYPRE ($(nproc) 核心)..."
    make -j"$(nproc)" 2>&1 | tail -3

    echo "  安装 HYPRE..."
    make install 2>&1 | tail -3

    echo "  HYPRE 安装完成: ${HYPRE_PATH}"
fi

# ============================================================
# Step 2 — 解压 FLASH 4.8
# ============================================================
echo "========================================"
echo "  [2/5] 解压 FLASH 4.8 → ${FLASH_HOME}"
echo "========================================"

if [ -f "${FLASH_HOME}/Makefile" ]; then
    echo "  SKIP: FLASH 已存在"
else
    if [ ! -f "./${FLASH_TAR}" ]; then
        echo "  错误: 找不到 ${FLASH_TAR}"
        exit 1
    fi

    mkdir -p "${FLASH_PARENT}"
    cd "${FLASH_PARENT}"
    rm -rf "FLASH4.8"
    tar -xzf "${OLDPWD}/${FLASH_TAR}"
    echo "  解压完成: ${FLASH_HOME}"
fi

# ============================================================
# Step 3 — 配置 Makefile.h
# ============================================================
echo "========================================"
echo "  [3/5] 配置 Makefile.h"
echo "========================================"

TEMPLATE="${FLASH_HOME}/sites/Prototypes/Linux/Makefile.h"
MAKEFILE_H="${FLASH_HOME}/Makefile.h"

if [ ! -f "${MAKEFILE_H}" ]; then
    if [ ! -f "${TEMPLATE}" ]; then
        echo "  错误: Makefile.h 模板不存在: ${TEMPLATE}"
        exit 1
    fi
    cp "${TEMPLATE}" "${MAKEFILE_H}"
    echo "  已复制模板: ${MAKEFILE_H}"
fi

# 更新路径
sed -i "s|^MPI_PATH\s*=.*|MPI_PATH = ${MPI_PATH}|"    "${MAKEFILE_H}"
sed -i "s|^HDF5_PATH\s*=.*|HDF5_PATH = ${HDF5_PATH}|"  "${MAKEFILE_H}"
sed -i "s|^HYPRE_PATH\s*=.*|HYPRE_PATH = ${HYPRE_PATH}|" "${MAKEFILE_H}"
echo "  MPI_PATH   => ${MPI_PATH}"
echo "  HDF5_PATH  => ${HDF5_PATH}"
echo "  HYPRE_PATH => ${HYPRE_PATH}"

# 添加 LAPACK
if ! grep -q "^LIB_LAPACK" "${MAKEFILE_H}"; then
    sed -i "/^HYPRE_PATH/a LIB_LAPACK = -llapack -lblas -lgfortran" "${MAKEFILE_H}"
    echo "  + LIB_LAPACK = -llapack -lblas -lgfortran"
fi

# 注释掉 FLASHBINARY ifeq 块
_sl=$(grep -n "FLASHBINARY" "${MAKEFILE_H}" 2>/dev/null | head -1 | cut -d: -f1) || true
if [ -n "$_sl" ]; then
    _el=$(tail -n +"$_sl" "${MAKEFILE_H}" | grep -n "^endif" 2>/dev/null | head -1 | cut -d: -f1) || true
    [ -n "$_el" ] && _el=$((_sl + _el - 1)) && sed -i "${_sl},${_el}s/^/#/" "${MAKEFILE_H}" || true
fi

echo ""
grep -E "^(MPI_PATH|HDF5_PATH|HYPRE_PATH|LIB_LAPACK)" "${MAKEFILE_H}"
echo ""

# ============================================================
# Step 4 — 编译 FLASH (LaserSlab 1D)
# ============================================================
echo "========================================"
echo "  [4/5] 编译 FLASH LaserSlab 1D"
echo "========================================"

# 设置环境变量
export HYPRE_HOME="${HYPRE_PATH}"
export LD_LIBRARY_PATH="${MPI_PATH}/lib:${HDF5_PATH}/lib:${HYPRE_PATH}/lib:${LD_LIBRARY_PATH:-}"
export PATH="${MPI_PATH}/bin:${HDF5_PATH}/bin:${PATH}"

if [ -f "${FLASH_HOME}/object/flash4" ]; then
    echo "  SKIP: FLASH 已编译"
else
    cd "${FLASH_HOME}"
    rm -rf object/

    echo "  FLASH setup..."
    ./setup -auto LaserSlab -1d +cartesian -nxb=16 +hdf5typeio \
        species=cham,targ +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 \
        -objdir=object -parfile=example1d.par 2>&1 | tail -10

    echo "  编译中..."
    cd object/
    make -j"$(nproc)" 2>&1 | tail -5

    if [ -f flash4 ]; then
        echo "  编译成功: $(du -sh flash4 | cut -f1)"
    else
        echo "  编译失败！"
        exit 1
    fi
fi

# ============================================================
# Step 5 — 生成 SLURM 提交脚本
# ============================================================
echo "========================================"
echo "  [5/5] 生成 SLURM 作业提交脚本"
echo "========================================"

RUN_DIR="${FLASH_HOME}/run_laserslab"
SLURM_SCRIPT="${FLASH_HOME}/submit_laserslab1d.slurm"

mkdir -p "${RUN_DIR}"

cat > "${SLURM_SCRIPT}" << SLURM_EOF
#!/bin/bash
#SBATCH --job-name=FLASH_LaserSlab1D
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --time=01:00:00
#SBATCH --output=${RUN_DIR}/flash_%j.log
#SBATCH --error=${RUN_DIR}/flash_%j.err

# ── 加载超算 module (根据实际超算修改) ──
# source /public1/soft/modules/module.sh
# module load hdf5/1.8.18
# module load mpich/3.2-gcc9.3

# ── 设置环境变量 ──
export HYPRE_HOME="${HYPRE_PATH}"
export LD_LIBRARY_PATH="\${HYPRE_HOME}/lib:\${LD_LIBRARY_PATH:-}"

# ── 准备运行目录 ──
SIM_SRC="${FLASH_HOME}/source/Simulation/SimulationMain/LaserSlab"
cd "${RUN_DIR}"

# 复制必要文件
cp "\${SIM_SRC}/al-imx-003.cn4" . 2>/dev/null || true
cp "\${SIM_SRC}/he-imx-005.cn4"  . 2>/dev/null || true
cp "\${SIM_SRC}/example1d.par"   flash.par

# ── 运行 FLASH ──
echo "启动 FLASH 仿真: \$(date)"
mpirun -np \${SLURM_NTASKS} ${FLASH_HOME}/object/flash4
echo "仿真完成: \$(date)"

# ── 验证输出 ──
CHK_COUNT=\$(ls *hdf5_chk_* 2>/dev/null | wc -l || echo 0)
echo "生成 checkpoint 文件数: \${CHK_COUNT}"
SLURM_EOF

echo "  SLURM 脚本已生成: ${SLURM_SCRIPT}"
echo ""
echo "  提交作业命令:"
echo "    sbatch ${SLURM_SCRIPT}"
echo ""

# ============================================================
# 完成摘要
# ============================================================
echo ""
echo "========================================"
echo "  超算 FLASH 配置完成!"
echo "========================================"
echo ""
echo "  FLASH 主目录:  ${FLASH_HOME}"
echo "  可执行文件:    ${FLASH_HOME}/object/flash4"
echo "  SLURM 脚本:    ${SLURM_SCRIPT}"
echo ""
echo "  提交仿真作业:"
echo "    sbatch ${SLURM_SCRIPT}"
echo ""
echo "  查看作业状态:"
echo "    squeue -u \$(whoami)"
echo ""
