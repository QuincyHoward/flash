#!/bin/bash
# ============================================================
# Hello FLASH! — 一键完整流程入口
# ============================================================
# 功能: 一键执行 FLASH 完整流程
#   Step 1: 安装 FLASH 到 ~/${FLASH_SIM_USER_DIR:-<用户名>}/FLASH/FLASH4.8/
#           <用户名> 通过 flash._core.credentials 设置 (默认 hello)
#   Step 2: 运行 LaserSlab 1D 仿真
#   Step 3: 收集 HDF5 输出文件
#   Step 4: 生成密度时空演化分析图
#
# 使用方法:
#   bash run_hello_flash.sh [--skip-install]
#
#   --skip-install  : 跳过安装步骤 (已安装时使用)
#
# 源码包放置要求:
#   hello_flash/
#   ├── FLASH4.8.tar.gz
#   ├── mpich-3.2.tar.gz
#   ├── hdf5-1.8.12.tar.gz
#   └── hypre-2.9.0b.tar.gz
#
# 如果源码包在 flash_src/ 目录, 脚本会自动查找
# ============================================================
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 用户名解析: FLASH_SIM_USER_DIR 环境变量 → flash._core.credentials → 默认 hello
# 用户名必须通过 flash._core.credentials 设置, 请勿硬编码
source "$SCRIPT_DIR/flash_user_lib.sh"
export FLASH_SIM_USER_DIR="${FLASH_SIM_USER_DIR:-$(resolve_flash_user)}"

# ============================================================
# 颜色输出
# ============================================================
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
info()  { echo -e "${CYAN}[INFO]${RESET} $*"; }
ok()    { echo -e "${GREEN}[ OK ]${RESET} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${RESET} $*"; }
err()   { echo -e "${RED}[ERR ]${RESET} $*" >&2; }

SKIP_INSTALL=0
for arg in "$@"; do
    case "$arg" in
        --skip-install) SKIP_INSTALL=1 ;;
        --help|-h)
            echo "Usage: bash run_hello_flash.sh [--skip-install]"
            echo "  --skip-install  跳过安装步骤（已安装时使用）"
            exit 0 ;;
    esac
done

TOTAL_START=$(date +%s)

echo -e "${BOLD}"
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║                                              ║"
echo "  ║   Hello FLASH!  一键安装 + 仿真 + 分析      ║"
echo "  ║                                              ║"
echo "  ║   $(date '+%Y-%m-%d %H:%M:%S')                         ║"
echo "  ╚══════════════════════════════════════════════╝"
echo -e "${RESET}"

# ============================================================
# 自动查找源码包目录
# ============================================================
PKG_DIR="$SCRIPT_DIR"

# 检查 hello_flash/ 内是否有源码包，否则往上找 flash_src/
if [ ! -f "$PKG_DIR/FLASH4.8.tar.gz" ]; then
    # 尝试 ../../../../flash_src (项目结构中的位置)
    # hello_flash → flash_demo → scenarios → flash/ → flash_src
    CANDIDATE="$(cd "$SCRIPT_DIR/../../.." && pwd)/flash_src"
    if [ -f "$CANDIDATE/FLASH4.8.tar.gz" ]; then
        PKG_DIR="$CANDIDATE"
        info "自动找到源码包目录: $PKG_DIR"
    fi
fi

# 若仍未找到源码包, 给出明确指引 (而非报错后让用户不知所措)
if [ ! -f "$PKG_DIR/FLASH4.8.tar.gz" ]; then
    echo ""
    err "未找到 FLASH4.8.tar.gz 源码包!"
    err "请先完成 README「前期准备工作」章节 b: 下载 FLASH 相关软件包"
    err "下载链接见 hello_flash/README.md 章节 b, 下载后放入 $PKG_DIR 或 flash_src/ 目录"
    err ""
    err "推荐方式: 通过 Agent AI 助手自动完成下载与适配 (见 README「推荐方法」章节)"
    exit 1
fi

# ============================================================
# Step 1: 安装 FLASH
# ============================================================
if [ "$SKIP_INSTALL" -eq 0 ]; then
    echo ""
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${BOLD}  阶段 1/2: 安装 FLASH 4.8 到 ~/$FLASH_SIM_USER_DIR/FLASH/${RESET}"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo ""

    INSTALL_SH="$SCRIPT_DIR/install_flash_wsl.sh"
    if [ ! -f "$INSTALL_SH" ]; then
        err "安装脚本不存在: $INSTALL_SH"
        exit 1
    fi

    bash "$INSTALL_SH" "$PKG_DIR"
    ok "安装阶段完成"
else
    warn "已跳过安装阶段 (--skip-install)"
fi

# ============================================================
# Step 2: 仿真 + 收集 + 分析
# ============================================================
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}  阶段 2/2: 仿真运行 + 结果收集 + 密度分析${RESET}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

RUN_SH="$SCRIPT_DIR/run_and_collect.sh"
if [ ! -f "$RUN_SH" ]; then
    err "运行脚本不存在: $RUN_SH"
    exit 1
fi

bash "$RUN_SH"
ok "仿真分析阶段完成"

# ============================================================
# 最终摘要
# ============================================================
ELAPSED=$(( $(date +%s) - TOTAL_START ))
H=$(( ELAPSED/3600 )); M=$(( (ELAPSED%3600)/60 )); S=$(( ELAPSED%60 ))

echo ""
echo -e "${BOLD}${GREEN}"
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║                                              ║"
echo "  ║   Hello FLASH!  全部流程完成！               ║"
printf "  ║   总耗时: %dh %02dm %02ds                          ║\n" $H $M $S
echo "  ║                                              ║"
echo "  ╚══════════════════════════════════════════════╝"
echo -e "${RESET}"
echo ""
echo -e "  输出结果位于:"
echo -e "  📁 ${BOLD}$SCRIPT_DIR/outputfiles/${RESET}"
echo -e "     ├── hdf5files/laserslab1d/   HDF5 checkpoint 文件"
echo -e "     └── plots/                   密度演化分析图表"
echo ""
echo -e "  ${CYAN}快速查看图表:${RESET}"
echo -e "  explorer.exe \"\$(wslpath -w $SCRIPT_DIR/outputfiles/plots)\""
echo ""
