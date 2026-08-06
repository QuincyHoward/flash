#!/bin/bash
# ============================================================
# FLASH LaserSlab 1D — 仿真运行 + 结果收集 + 密度分析
# ============================================================
# 用途:
#   1. 运行 LaserSlab 1D 仿真 (mpirun)
#   2. 检测 HDF5 输出文件
#   3. 复制到 outputfiles/hdf5files/laserslab1d/
#   4. 调用 analyze_density.py 生成密度演化图
#
# 前提: 已执行 install_flash_wsl.sh 完成安装
#
# 使用方法:
#   bash run_and_collect.sh
# ============================================================
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ============================================================
# 路径配置
# ============================================================
# 用户名解析: FLASH_SIM_USER_DIR 环境变量 → flash._core.credentials → 默认 hello
# 用户名必须通过 flash._core.credentials 设置, 请勿硬编码
source "$SCRIPT_DIR/flash_user_lib.sh"
export FLASH_SIM_USER_DIR="${FLASH_SIM_USER_DIR:-$(resolve_flash_user)}"

# FLASH_USER_HOME 仅作旧环境变量兼容 (值已动态化, 不含硬编码用户名)
FLASH_USER_HOME="${FLASH_USER_HOME:-$HOME/$FLASH_SIM_USER_DIR}"
FLASH_HOME="${FLASH_HOME:-$FLASH_USER_HOME/FLASH/FLASH4.8}"
MPI_PATH="${MPI_PATH:-/usr/local/mpich}"
HDF5_PATH="${HDF5_PATH:-/usr/local/hdf5}"
HYPRE_PATH="${HYPRE_PATH:-/usr/local/hypre}"

FLASH_EXE="$FLASH_HOME/object/flash4"
SIM_SRC_DIR="$FLASH_HOME/source/Simulation/SimulationMain/LaserSlab"
RUN_DIR="$FLASH_HOME/run_laserslab"

# 输出目录 (在 hello_flash/ 文件夹内)
HDF5_COLLECT_DIR="$SCRIPT_DIR/outputfiles/hdf5files/laserslab1d"
PLOTS_DIR="$SCRIPT_DIR/outputfiles/plots"

# ============================================================
# 颜色输出
# ============================================================
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
info()  { echo -e "${CYAN}[INFO]${RESET} $*"; }
ok()    { echo -e "${GREEN}[ OK ]${RESET} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${RESET} $*"; }
err()   { echo -e "${RED}[ERR ]${RESET} $*" >&2; }
step()  { echo -e "\n${BOLD}${CYAN}========================================${RESET}"; \
          echo -e "${BOLD}${CYAN}  $*${RESET}"; \
          echo -e "${BOLD}${CYAN}========================================${RESET}"; }

START_TIME=$(date +%s)

echo -e "${BOLD}"
echo "  ╔══════════════════════════════════════════╗"
echo "  ║   FLASH LaserSlab 1D — 仿真 & 分析      ║"
echo "  ║   $(date '+%Y-%m-%d %H:%M:%S')                     ║"
echo "  ╚══════════════════════════════════════════╝"
echo -e "${RESET}"

# ============================================================
# 环境刷新
# ============================================================
export PATH="$MPI_PATH/bin:$HDF5_PATH/bin:$PATH"
export LD_LIBRARY_PATH="$MPI_PATH/lib:$HDF5_PATH/lib:$HYPRE_PATH/lib:${LD_LIBRARY_PATH:-}"

# ============================================================
# 前置检查
# ============================================================
step "[检查] 安装状态"

if [ ! -f "$FLASH_EXE" ]; then
    err "未找到 FLASH 可执行文件: $FLASH_EXE"
    err "请先执行: bash install_flash_wsl.sh"
    exit 1
fi
ok "FLASH 可执行文件: $FLASH_EXE ($(du -sh "$FLASH_EXE" | cut -f1))"

if ! command -v mpirun &>/dev/null; then
    err "未找到 mpirun，请检查 MPI 安装: $MPI_PATH"
    exit 1
fi
ok "mpirun: $(which mpirun)"

# ============================================================
# Step 1 — 检测是否已有仿真结果
# ============================================================
step "[1/4] 检测已有仿真结果"

if ls "$RUN_DIR/"*hdf5_chk_* &>/dev/null 2>&1; then
    _cnt=$(ls "$RUN_DIR/"*hdf5_chk_* 2>/dev/null | wc -l)
    warn "检测到 $RUN_DIR 中已有 $_cnt 个 checkpoint 文件"
    echo ""
    echo -e "  选择操作:"
    echo -e "    ${BOLD}1${RESET}) 使用已有仿真结果 (跳过仿真，直接收集分析)"
    echo -e "    ${BOLD}2${RESET}) 重新运行仿真 (删除旧结果)"
    echo ""

    if [ -t 0 ]; then
        read -r -p "  请选择 [1/2] (默认=1): " CHOICE
        CHOICE="${CHOICE:-1}"
    else
        # 非交互模式，默认使用已有结果
        CHOICE="1"
        info "非交互模式，自动使用已有仿真结果"
    fi

    if [ "$CHOICE" = "2" ]; then
        info "删除旧仿真结果..."
        rm -rf "$RUN_DIR"
        NEED_RUN=1
    else
        info "使用已有仿真结果"
        NEED_RUN=0
    fi
else
    NEED_RUN=1
fi

# ============================================================
# Step 2 — 运行 LaserSlab 1D 仿真
# ============================================================
step "[2/4] 运行 LaserSlab 1D 仿真"

if [ "$NEED_RUN" -eq 1 ]; then
    rm -rf "$RUN_DIR"
    mkdir -p "$RUN_DIR"
    cd "$RUN_DIR"

    # 复制 EOS 表
    info "复制 EOS 数据表..."
    cp "$SIM_SRC_DIR/al-imx-003.cn4" "$RUN_DIR/" 2>/dev/null && ok "  + al-imx-003.cn4" || warn "  未找到 al-imx-003.cn4"
    cp "$SIM_SRC_DIR/he-imx-005.cn4"  "$RUN_DIR/" 2>/dev/null && ok "  + he-imx-005.cn4"  || warn "  未找到 he-imx-005.cn4"

    # 复制参数文件
    if [ -f "$SIM_SRC_DIR/example1d.par" ]; then
        cp "$SIM_SRC_DIR/example1d.par" "$RUN_DIR/flash.par"
        ok "  + flash.par"
    else
        err "找不到 example1d.par: $SIM_SRC_DIR/example1d.par"
        exit 1
    fi

    echo ""
    info "启动 FLASH 仿真 (mpirun -np 1)..."
    info "日志: $RUN_DIR/flash_output.log"
    echo ""

    "$MPI_PATH/bin/mpirun" -np 1 "$FLASH_EXE" 2>&1 | \
        tee "$RUN_DIR/flash_output.log" | \
        grep -E "(Wrote|Step|completed|exiting|ERROR|SUCCESS|tmax|nend|WARNING)" || true

    echo ""

    # 验证输出
    _chk_cnt=$(ls "$RUN_DIR/"*hdf5_chk_* 2>/dev/null | wc -l || echo 0)
    if [ "$_chk_cnt" -gt 0 ]; then
        ok "仿真成功！生成了 $_chk_cnt 个 checkpoint 文件"
        ls -lh "$RUN_DIR/"*hdf5_chk_* 2>/dev/null
    else
        err "仿真失败：未找到 checkpoint 文件！"
        err "请检查日志: $RUN_DIR/flash_output.log"
        echo ""
        warn "日志末尾 (最后20行):"
        tail -20 "$RUN_DIR/flash_output.log" 2>/dev/null || true
        exit 1
    fi
else
    _chk_cnt=$(ls "$RUN_DIR/"*hdf5_chk_* 2>/dev/null | wc -l || echo 0)
    ok "使用已有仿真结果：$_chk_cnt 个 checkpoint 文件"
fi

# ============================================================
# Step 3 — 收集 HDF5 文件
# ============================================================
step "[3/4] 收集 HDF5 文件 → outputfiles/hdf5files/laserslab1d/"

mkdir -p "$HDF5_COLLECT_DIR"

_copied=0
for f in "$RUN_DIR/"*hdf5_chk_*; do
    [ -f "$f" ] || continue
    cp "$f" "$HDF5_COLLECT_DIR/"
    _copied=$((_copied+1))
done

# 也复制 plt 文件 (如有)
for f in "$RUN_DIR/"*hdf5_plt_*; do
    [ -f "$f" ] || continue
    cp "$f" "$HDF5_COLLECT_DIR/"
    _copied=$((_copied+1))
done

if [ "$_copied" -gt 0 ]; then
    ok "已复制 $_copied 个 HDF5 文件到:"
    ok "  $HDF5_COLLECT_DIR"
    ls -lh "$HDF5_COLLECT_DIR/"
else
    err "未复制任何 HDF5 文件"
    exit 1
fi

# ============================================================
# Step 4 — 安装 Python 依赖 + 运行密度分析
# ============================================================
step "[4/4] 密度分析 → outputfiles/plots/"

mkdir -p "$PLOTS_DIR"

info "安装 Python 依赖 (h5py, numpy, matplotlib)..."
python3 -m pip install --quiet h5py numpy matplotlib 2>&1 | tail -3 || \
    $SUDO pip3 install --quiet h5py numpy matplotlib 2>&1 | tail -3 || true

ANALYZE_PY="$SCRIPT_DIR/analyze_density.py"

if [ ! -f "$ANALYZE_PY" ]; then
    err "找不到分析脚本: $ANALYZE_PY"
    exit 1
fi

info "运行密度分析脚本..."
python3 "$ANALYZE_PY"

# 验证图表输出
_png_cnt=$(ls "$PLOTS_DIR/"*.png 2>/dev/null | wc -l || echo 0)
if [ "$_png_cnt" -gt 0 ]; then
    ok "成功生成 $_png_cnt 张分析图表:"
    ls -lh "$PLOTS_DIR/"*.png
else
    warn "未生成 PNG 图表，请检查分析脚本输出"
fi

# ============================================================
# 完成摘要
# ============================================================
ELAPSED=$(( $(date +%s) - START_TIME ))
H=$(( ELAPSED/3600 )); M=$(( (ELAPSED%3600)/60 )); S=$(( ELAPSED%60 ))

echo ""
echo -e "${BOLD}${GREEN}"
echo "  ╔════════════════════════════════════════╗"
echo "  ║   仿真 & 分析 全部完成！               ║"
printf "  ║   耗时: %dh %02dm %02ds                       ║\n" $H $M $S
echo "  ╚════════════════════════════════════════╝"
echo -e "${RESET}"
echo ""
echo -e "  HDF5 文件:  ${BOLD}$HDF5_COLLECT_DIR/${RESET}"
echo -e "  分析图表:   ${BOLD}$PLOTS_DIR/${RESET}"
echo -e "  仿真日志:   $RUN_DIR/flash_output.log"
echo ""
