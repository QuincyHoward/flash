#!/bin/bash
# ============================================================
# FLASH 4.8 — WSL 一键安装脚本
# Hello FLASH! 快速上手版
# ============================================================
# 用途: 在 WSL (Ubuntu) 中一键安装 FLASH 4.8
#       安装到 ~/${FLASH_SIM_USER_DIR:-<用户名>}/FLASH/FLASH4.8/
#       <用户名> 通过 flash._core.credentials 设置 (默认 hello)
#
# 使用方法:
#   bash install_flash_wsl.sh [源码包目录]
#
#   源码包目录默认为脚本同级目录 (即 hello_flash/ 文件夹)
#   需要以下文件:
#     FLASH4.8.tar.gz
#     mpich-3.2.tar.gz
#     hdf5-1.8.12.tar.gz
#     hypre-2.9.0b.tar.gz
#
# 幂等性: 已完成的步骤会自动跳过，中断后可继续执行
# ============================================================
set -eo pipefail

# ============================================================
# 路径配置 (可修改)
# ============================================================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PKG_DIR="${1:-${PKG_DIR:-$SCRIPT_DIR}}"

# 用户名解析: FLASH_SIM_USER_DIR 环境变量 → flash._core.credentials → 默认 hello
# 用户名必须通过 flash._core.credentials 设置, 请勿硬编码
source "$SCRIPT_DIR/flash_user_lib.sh"
export FLASH_SIM_USER_DIR="${FLASH_SIM_USER_DIR:-$(resolve_flash_user)}"

# FLASH 安装到 ~/${FLASH_SIM_USER_DIR}/FLASH/FLASH4.8
# FLASH_USER_HOME 仅作旧环境变量兼容 (值已动态化, 不含硬编码用户名)
export FLASH_USER_HOME="${FLASH_USER_HOME:-$HOME/$FLASH_SIM_USER_DIR}"
export FLASH_PARENT="${FLASH_PARENT:-$FLASH_USER_HOME/FLASH}"
export FLASH_HOME="${FLASH_HOME:-$FLASH_PARENT/FLASH4.8}"
export BUILD_DIR="${BUILD_DIR:-$HOME/tmp_flash_build}"

# 依赖库安装路径
export MPI_PATH="${MPI_PATH:-/usr/local/mpich}"
export HDF5_PATH="${HDF5_PATH:-/usr/local/hdf5}"
export HYPRE_PATH="${HYPRE_PATH:-/usr/local/hypre}"

# 源码包文件名
MPICH_TAR="mpich-3.2.tar.gz"
MPICH_DIR="mpich-3.2"
HDF5_TAR="hdf5-1.8.12.tar.gz"
HDF5_DIR="hdf5-1.8.12"
HYPRE_TAR="hypre-2.9.0b.tar.gz"
HYPRE_DIR="hypre-2.9.0b"
FLASH_TAR="FLASH4.8.tar.gz"

NPROC="${NPROC:-$(nproc)}"
START_TIME=$(date +%s)

# ============================================================
# 颜色输出
# ============================================================
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
info()    { echo -e "${CYAN}[INFO]${RESET} $*"; }
ok()      { echo -e "${GREEN}[ OK ]${RESET} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET} $*"; }
err()     { echo -e "${RED}[ERR ]${RESET} $*" >&2; }
step()    { echo -e "\n${BOLD}${CYAN}========================================${RESET}"; \
            echo -e "${BOLD}${CYAN}  $*${RESET}"; \
            echo -e "${BOLD}${CYAN}========================================${RESET}"; }

# ============================================================
# sudo 检测
# ============================================================
if [ "$(id -u)" -eq 0 ]; then
    SUDO=""
else
    SUDO="sudo"
fi

# ============================================================
# 环境预检 (供 Agent AI 微调适配参考)
# ============================================================
preflight_check() {
    info "── 环境预检 ──────────────────────────────"
    info "系统:      $(uname -sr) $(uname -m)"
    if [ -f /etc/os-release ]; then
        info "发行版:    $(grep PRETTY_NAME /etc/os-release | cut -d'=' -f2 | tr -d '\"')"
    fi
    info "CPU 核数:  $(nproc)"
    info "内存:      $(free -g 2>/dev/null | awk '/Mem:/{print $2" GB"}')"
    info "默认编译器:"
    for c in gcc g++ gfortran make; do
        if command -v "$c" >/dev/null 2>&1; then
            info "  $c: $($c --version 2>/dev/null | head -1)"
        else
            warn "  $c: 未安装 (安装脚本会自动安装)"
        fi
    done
    # 检查 gcc-9 / gfortran-9 (FLASH 4.8 推荐编译器)
    if command -v gcc-9 >/dev/null 2>&1; then
        info "gcc-9:     $(gcc-9 --version | head -1)"
    else
        warn "gcc-9:     未安装 (新版本 Ubuntu 需由 Agent 适配或从旧源安装)"
    fi
    info "python:    $(python3 --version 2>&1)"
    info "── 预检结束 ──────────────────────────────"
}

# ============================================================
# 环境刷新 (在当前 shell 中立即生效)
# ============================================================
refresh_env() {
    export MPI_HOME="$MPI_PATH"
    export PATH="$MPI_PATH/bin:$HDF5_PATH/bin:$PATH"
    export LD_LIBRARY_PATH="$MPI_PATH/lib:$HDF5_PATH/lib:$HYPRE_PATH/lib:${LD_LIBRARY_PATH:-}"
    export HDF5_HOME="$HDF5_PATH"
    export HDF5_ROOT="$HDF5_PATH"
    export HYPRE_HOME="$HYPRE_PATH"
}

# ============================================================
# 将环境变量写入 ~/.bashrc (幂等)
# ============================================================
write_bashrc() {
    local mark="# >>> FLASH env (auto-generated) <<<"
    if grep -q "FLASH env (auto-generated)" "$HOME/.bashrc" 2>/dev/null; then
        sed -i "/# >>> FLASH env/,/# <<< FLASH env/d" "$HOME/.bashrc"
    fi
    cat >> "$HOME/.bashrc" << BEOF
${mark}
export MPI_HOME=${MPI_PATH}
export HDF5_HOME=${HDF5_PATH}
export HDF5_ROOT=${HDF5_PATH}
export HYPRE_HOME=${HYPRE_PATH}
export PATH=\$MPI_HOME/bin:\$HDF5_HOME/bin:\$PATH
export LD_LIBRARY_PATH=\$MPI_HOME/lib:\$HDF5_HOME/lib:\$HYPRE_HOME/lib:\${LD_LIBRARY_PATH:-}
# <<< FLASH env
BEOF
    ok "~/.bashrc 已写入 FLASH 环境变量"
}

# ============================================================
# 幂等检测
# ============================================================
is_mpich_ok()    { [ -x "$MPI_PATH/bin/mpicc" ]; }
is_hdf5_ok()     { [ -f "$HDF5_PATH/lib/libhdf5.a" ] || [ -f "$HDF5_PATH/lib/libhdf5.so" ]; }
is_hypre_ok()    { ls "$HYPRE_PATH/lib/libHYPRE"* &>/dev/null 2>&1; }
is_flash_setup() { [ -f "$FLASH_HOME/Makefile.h" ]; }
is_flash_built() { [ -f "$FLASH_HOME/object/flash4" ]; }

# ============================================================
# Banner
# ============================================================
echo -e "${BOLD}"
echo "  ╔════════════════════════════════════════╗"
echo "  ║   FLASH 4.8 — Hello FLASH! WSL 安装   ║"
echo "  ║   $(date '+%Y-%m-%d %H:%M:%S')                   ║"
echo "  ╚════════════════════════════════════════╝"
echo -e "${RESET}"
info "源码包目录:  $PKG_DIR"
info "编译缓存:    $BUILD_DIR"
info "FLASH 路径:  $FLASH_HOME"
info "MPI 路径:    $MPI_PATH"
info "HDF5 路径:   $HDF5_PATH"
info "HYPRE 路径:  $HYPRE_PATH"
info "CPU 核心:    $NPROC"
info "用户:        $(whoami)  (uid=$(id -u))"
echo ""

# 环境预检 (Agent 微调适配依据)
preflight_check
echo ""

# ============================================================
# Step 0 — 系统依赖
# ============================================================
step "[0/6] 系统依赖安装"

$SUDO apt-get update -y -qq 2>&1 | tail -1

info "安装编译工具和库..."
$SUDO apt-get install -y -qq \
    gcc g++ gfortran \
    gcc-9 g++-9 gfortran-9 \
    make \
    python3 python3-pip python-is-python3 \
    zlib1g-dev \
    libopenblas-dev liblapack-dev liblapacke-dev \
    wget \
    2>&1 | tail -5

# 设置 gcc-9 为默认 (MPICH 3.2 ABI 兼容性要求)
$SUDO update-alternatives --install /usr/bin/gcc     gcc     /usr/bin/gcc-9     50 2>/dev/null || true
$SUDO update-alternatives --install /usr/bin/g++     g++     /usr/bin/g++-9     50 2>/dev/null || true
$SUDO update-alternatives --install /usr/bin/gfortran gfortran /usr/bin/gfortran-9 50 2>/dev/null || true
$SUDO update-alternatives --set gcc     /usr/bin/gcc-9     2>/dev/null || true
$SUDO update-alternatives --set g++     /usr/bin/g++-9     2>/dev/null || true
$SUDO update-alternatives --set gfortran /usr/bin/gfortran-9 2>/dev/null || true

# 确保 python 命令存在
if ! command -v python &>/dev/null; then
    $SUDO ln -sf "$(command -v python3)" /usr/local/bin/python 2>/dev/null || true
fi

ok "gcc:      $(gcc --version 2>/dev/null | head -1)"
ok "gfortran: $(gfortran --version 2>/dev/null | head -1)"

# ============================================================
# Step 1 — 准备源码包
# ============================================================
step "[1/6] 准备源码包"

mkdir -p "$BUILD_DIR"
local_missing=0

for pkg in "$MPICH_TAR" "$HDF5_TAR" "$HYPRE_TAR" "$FLASH_TAR"; do
    if [ -f "$PKG_DIR/$pkg" ]; then
        cp -n "$PKG_DIR/$pkg" "$BUILD_DIR/" 2>/dev/null || true
        ok "找到: $pkg  ($(du -sh "$PKG_DIR/$pkg" | cut -f1))"
    else
        err "缺失: $PKG_DIR/$pkg"
        local_missing=1
    fi
done

if [ "$local_missing" -eq 1 ]; then
    echo ""
    err "源码包不完整！请将以下文件放入 $PKG_DIR:"
    err "  $MPICH_TAR  $HDF5_TAR  $HYPRE_TAR  $FLASH_TAR"
    echo ""
    err "下载地址请参见:"
    err "  - hello_flash/README.md 章节 b (完整下载地址表)"
    err "  - hello_flash/README.md 章节 b (FLASH 相关软件包的获取与下载)"
    echo ""
    err "提示: 也可通过 Agent AI 助手自动完成下载与适配 (推荐, 见 README 章节「推荐方法」)。"
    exit 1
fi

# ============================================================
# Step 2 — 编译安装 MPICH 3.2
# ============================================================
step "[2/6] 编译安装 MPICH 3.2"

if is_mpich_ok; then
    warn "跳过: MPICH 已安装 ($MPI_PATH)"
    refresh_env
else
    cd "$BUILD_DIR"
    rm -rf "$MPICH_DIR"
    tar -xzf "$MPICH_TAR"
    cd "$MPICH_DIR"

    info "配置 MPICH (使用 gcc-9)..."
    ./configure --prefix="$MPI_PATH" \
        CC=gcc-9 CXX=g++-9 FC=gfortran-9 F77=gfortran-9 \
        2>&1 | tail -3

    info "编译 MPICH ($NPROC 核心)..."
    make -j"$NPROC" 2>&1 | tail -3

    info "安装 MPICH..."
    $SUDO make install 2>&1 | tail -3

    refresh_env
    ok "MPICH: $(mpicc --version 2>&1 | head -1)"
fi

# ============================================================
# Step 3 — 编译安装 HDF5 1.8.12 (并行 + Fortran)
# ============================================================
step "[3/6] 编译安装 HDF5 1.8.12"

if is_hdf5_ok; then
    warn "跳过: HDF5 已安装 ($HDF5_PATH)"
    refresh_env
else
    cd "$BUILD_DIR"
    rm -rf "$HDF5_DIR"
    tar -xzf "$HDF5_TAR"
    cd "$HDF5_DIR"

    # 确保 gfortran 命令存在 (HDF5 configure 需要 bare gfortran)
    if ! command -v gfortran &>/dev/null; then
        _gf=$(which gfortran-9 2>/dev/null || echo "")
        [ -n "$_gf" ] && $SUDO ln -sf "$_gf" /usr/local/bin/gfortran 2>/dev/null || true
    fi

    # HDF5 parallel: CC=mpicc, FC=gfortran (bare), MPI 头文件/库通过 flags 注入
    MPI_INC="-I$MPI_PATH/include"
    MPI_LIB="-L$MPI_PATH/lib"

    info "配置 HDF5 (parallel + Fortran)..."
    ./configure --prefix="$HDF5_PATH" \
        --enable-parallel \
        --enable-fortran \
        CC=mpicc FC=gfortran F77=gfortran \
        FCFLAGS="$MPI_INC" FFLAGS="$MPI_INC" \
        LIBS="$MPI_LIB -lmpi -lmpifort" \
        2>&1 | tail -3

    info "编译 HDF5 ($NPROC 核心)..."
    make -j"$NPROC" 2>&1 | tail -3

    info "安装 HDF5..."
    $SUDO make install 2>&1 | tail -3

    refresh_env
    ok "HDF5 已安装到 $HDF5_PATH"
fi

# ============================================================
# Step 4 — 编译安装 HYPRE 2.9.0b
# ============================================================
step "[4/6] 编译安装 HYPRE 2.9.0b"

if is_hypre_ok; then
    warn "跳过: HYPRE 已安装 ($HYPRE_PATH)"
    refresh_env
else
    cd "$BUILD_DIR"
    rm -rf "$HYPRE_DIR"
    tar -xzf "$HYPRE_TAR"
    cd "$HYPRE_DIR/src"

    info "配置 HYPRE..."
    ./configure --prefix="$HYPRE_PATH" \
        CC=mpicc CXX=mpicxx FC=gfortran-9 F77=gfortran-9 \
        2>&1 | tail -3

    info "编译 HYPRE ($NPROC 核心)..."
    make -j"$NPROC" 2>&1 | tail -3

    info "安装 HYPRE..."
    $SUDO make install 2>&1 | tail -3

    refresh_env
    ok "HYPRE 已安装到 $HYPRE_PATH"
fi

# ============================================================
# Step 5 — 解压 FLASH 4.8，配置 Makefile.h
# ============================================================
step "[5/6] 安装 FLASH 4.8 → $FLASH_HOME"

if is_flash_setup; then
    warn "跳过: FLASH 已解压配置 ($FLASH_HOME)"
    refresh_env
else
    # 创建 ~/${FLASH_SIM_USER_DIR}/FLASH 目录
    mkdir -p "$FLASH_PARENT"
    cd "$FLASH_PARENT"
    rm -rf "FLASH4.8"

    info "解压 FLASH 4.8..."
    tar -xzf "$BUILD_DIR/$FLASH_TAR"
    ok "解压完成: $FLASH_HOME"

    # 复制 Makefile.h 模板
    TEMPLATE="$FLASH_HOME/sites/Prototypes/Linux/Makefile.h"
    if [ ! -f "$TEMPLATE" ]; then
        err "Makefile.h 模板不存在: $TEMPLATE"
        exit 1
    fi
    cp "$TEMPLATE" "$FLASH_HOME/Makefile.h"
    ok "已复制 Makefile.h 模板"

    # 替换路径
    sed -i "s|^MPI_PATH\s*=.*|MPI_PATH = $MPI_PATH|"    "$FLASH_HOME/Makefile.h"
    sed -i "s|^HDF5_PATH\s*=.*|HDF5_PATH = $HDF5_PATH|"  "$FLASH_HOME/Makefile.h"
    sed -i "s|^HYPRE_PATH\s*=.*|HYPRE_PATH = $HYPRE_PATH|" "$FLASH_HOME/Makefile.h"
    info "  MPI_PATH  => $MPI_PATH"
    info "  HDF5_PATH => $HDF5_PATH"
    info "  HYPRE_PATH=> $HYPRE_PATH"

    # 添加 LIB_LAPACK (FLASH 编译需要)
    if ! grep -q "^LIB_LAPACK" "$FLASH_HOME/Makefile.h"; then
        sed -i "/^HYPRE_PATH/a LIB_LAPACK = -llapack -lblas -lgfortran" "$FLASH_HOME/Makefile.h"
        ok "  已添加 LIB_LAPACK = -llapack -lblas -lgfortran"
    fi

    # 注释掉 FLASHBINARY ifeq 块 (导致编译错误)
    _sl=$(grep -n "FLASHBINARY" "$FLASH_HOME/Makefile.h" 2>/dev/null | head -1 | cut -d: -f1) || true
    if [ -n "$_sl" ]; then
        _el=$(tail -n +"$_sl" "$FLASH_HOME/Makefile.h" | grep -n "^endif" 2>/dev/null | head -1 | cut -d: -f1) || true
        if [ -n "$_el" ]; then
            _el=$((_sl + _el - 1))
            sed -i "${_sl},${_el}s/^/#/" "$FLASH_HOME/Makefile.h"
            ok "  已注释 FLASHBINARY ifeq 块 (行 ${_sl}-${_el})"
        fi
    fi

    refresh_env
    echo ""
    info "Makefile.h 关键路径:"
    grep -E "^(MPI_PATH|HDF5_PATH|HYPRE_PATH|LIB_LAPACK)" "$FLASH_HOME/Makefile.h" 2>/dev/null || true
fi

# 写入 ~/.bashrc
write_bashrc

# ============================================================
# Step 6 — 编译 FLASH (LaserSlab 1D)
# ============================================================
step "[6/6] 编译 FLASH LaserSlab 1D"

if is_flash_built; then
    warn "跳过: FLASH 已编译 ($(du -sh "$FLASH_HOME/object/flash4" 2>/dev/null | cut -f1))"
else
    cd "$FLASH_HOME"
    rm -rf object/

    info "FLASH setup (LaserSlab 1D)..."
    ./setup -auto LaserSlab -1d +cartesian -nxb=16 +hdf5typeio \
        species=cham,targ +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 \
        -objdir=object -parfile=example1d.par 2>&1 | tail -10

    echo ""
    info "编译 FLASH ($NPROC 核心)..."
    cd object/
    make -j"$NPROC" 2>&1 | tail -5

    if [ -f flash4 ]; then
        ok "FLASH 编译成功！($(du -sh flash4 | cut -f1))"
    else
        err "FLASH 编译失败！请检查编译日志。"
        exit 1
    fi
fi

# ============================================================
# 安装完成摘要
# ============================================================
ELAPSED=$(( $(date +%s) - START_TIME ))
H=$(( ELAPSED/3600 )); M=$(( (ELAPSED%3600)/60 )); S=$(( ELAPSED%60 ))

echo ""
echo -e "${BOLD}${GREEN}"
echo "  ╔════════════════════════════════════════╗"
echo "  ║   FLASH 4.8 安装完成！                 ║"
printf "  ║   耗时: %dh %02dm %02ds                       ║\n" $H $M $S
echo "  ╚════════════════════════════════════════╝"
echo -e "${RESET}"
echo ""
echo -e "  FLASH 主目录:  ${BOLD}$FLASH_HOME${RESET}"
echo -e "  可执行文件:    ${BOLD}$FLASH_HOME/object/flash4${RESET}"
echo -e "  MPI:           $MPI_PATH"
echo -e "  HDF5:          $HDF5_PATH"
echo -e "  HYPRE:         $HYPRE_PATH"
echo ""
echo -e "  下一步: ${BOLD}bash run_and_collect.sh${RESET}"
echo -e "          (运行 LaserSlab 仿真并生成分析图表)"
echo ""
echo -e "  ${YELLOW}提示: 重新打开终端后环境变量自动生效${RESET}"
echo -e "  ${YELLOW}或执行: source ~/.bashrc${RESET}"
echo ""
