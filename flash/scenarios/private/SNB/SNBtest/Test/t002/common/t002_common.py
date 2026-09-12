"""t002 对比场景 —— 共享参数与工具的**唯一来源** (single source of truth)
═══════════════════════════════════════════════════════════════════════════════

场景: SNB (Schurtz–Nicolaï–Busquet 非局域电子热传导) vs FL-SH (限流 Spitzer-Härm)
      几何极简两区: x<0 cham (稀薄 He 真空) | x>0 targ (常温常压 CH)

设计原则
--------
1. 本模块**只定义参数与工具函数**, 不生成文件。两个仿真腿 (sim_flsh / sim_snb)
   的输入生成脚本 (scripts/generate/gen_t002_inputs.py) 都从这里取参, 从根本上
   消除两腿几何/激光/网格的手抄差异。
2. 两个仿真腿**必须跑在两棵独立的 FLASH 树上**:
     - FL-SH → 标准树 ~/<user>/FLASH/FLASH4.8
     - SNB   → FLASHSNB 树 ~/<user>/FLASH/FLASHSNB/FLASH4.8
   原因 (源码事实): SNB 非局域热流在 diff_advanceTherm.F90 的 `if(NDIM==1)` 分支内
   **无条件执行**, Config 里没有对应 PARAMETER, 不存在 par 开关 → 标准树里
   拿不到纯限流 (FL-SH) 结果, FLASHSNB 里也拿不到"关掉 SNB"的结果。

两腿唯一允许的差异 (其余参数必须逐字节一致)
--------------------------------------------
    tree / sim_name / objdir / basenm / log_file / par 文件名
    diff_eleFlMode  (FL-SH: fl_minmax ; SNB: fl_none)
    Config 的 18 个 SNB 诊断 VARIABLE + Makefile 的 mgd_qesh.o + 9 个 SNB 覆盖 F90
    plot_var 白名单

+ug 均匀网格分辨率法则 (源码: Grid/GridMain/UG/Grid_init.F90:186-194)
--------------------------------------------------------------------
    FIXEDBLOCKSIZE (setup 给了 -nxb=N):  总格数 = iProcs × nxb
    NON_FIXED      (不给 -nxb):          总格数 = iGridSize (par), 块 = iGridSize/iProcs
  → 分辨率**不是**只能靠核数提升: 固定块模式下加大 -nxb 即可; 非固定块模式下
    iGridSize 直接给定总格数, 分辨率与核数解耦。
  注意: +ug 下 **一个块一个进程**, 因此 nproc 必须严格等于 iProcs。
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── 仓库根定位 (pyproject.toml 锚点; 与其它场景同模式) ──────────
_REPO_ROOT = Path(__file__).resolve().parent
for _ in range(16):
    if (_REPO_ROOT / "pyproject.toml").exists():
        break
    _REPO_ROOT = _REPO_ROOT.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ── 场景目录 ────────────────────────────────────────────────
T002_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = T002_DIR / "docs"
RESULT_DIR = T002_DIR / "results"

# ── 两腿定义 (唯一差异集中处) ────────────────────────────────
LEGS: Dict[str, Dict[str, Any]] = {
    "flsh": {
        "model": "flsh",
        "label": "FL-SH",
        "desc": "flux-limited Spitzer-Harm (local)",
        "tree": "standard",                 # 标准 FLASH 树
        "sim_name": "T002_FLSH",
        "objdir": "T002_FLSH_obj",
        "basenm": "t002flsh_",
        "log_file": "t002flsh.log",
        "par_file": "t002flsh.par",
        "diff_eleFlMode": "fl_minmax",      # 用户指定: 限流模型 FL-SH
        "diff_eleFlCoef": 0.06,
        "has_snb": False,
    },
    "snb": {
        "model": "snb",
        "label": "SNB",
        "desc": "SNB nonlocal electron heat transport",
        "tree": "snb",                      # FLASHSNB 树
        "sim_name": "T002_SNB",
        "objdir": "T002_SNB_obj",
        "basenm": "t002snb_",
        "log_file": "t002snb.log",
        "par_file": "t002snb.par",
        "diff_eleFlMode": "fl_none",        # 用户指定: SNB 侧关掉通量限制器
        "diff_eleFlCoef": 0.06,
        "has_snb": True,
    },
}

# ── 共享物理参数 (两腿必须一致) ──────────────────────────────
PARAMS: Dict[str, Any] = {
    # 几何: 域 [-400, 100] µm = [-0.04, 0.01] cm
    "xmin": -0.04,
    "xmax": 0.01,
    # 界面位置 (cm): x<0 cham, x>=0 targ
    "interface_x": 0.0,
    # 初始化温度 (K)
    "t_initial": 290.11375,
    # 物种: cham = 稀薄 He (真空), targ = 常温常压 CH
    "species": ["cham", "targ"],
    "cham": {"cn4": "Z02_1.00-20260708_0851.cn4", "rho": 1.0e-6,
             "A": 4.002602, "Z": 2.0, "ZMin": 1.0e-23, "alias": "z02"},
    "targ": {"cn4": "Z06_0.50-Z01_0.50-20260708_0850.cn4", "rho": 1.0,
             "A": 6.5, "Z": 3.5, "ZMin": 0.02, "alias": "z06_chmix"},
    # 激光: 4 段梯形波 = 50 ps 上升 / 1.0 ns 平台 / 50 ps 下降, 左侧入射
    "laser": {
        "wavelength_um": 0.351,
        "peak_power": 5.0e14,          # W/cm^2 (1D 单光线, 单位面积功率)
        "n_sections": 4,
        "times": [0.0, 50.0e-12, 1.05e-9, 1.10e-9],
        "powers": [0.0, 5.0e14, 5.0e14, 0.0],
        "lensX": -1.0,
        "targetX": 0.0,
        "cross_section": "uniform",
        "n_rays": 1,
        "grid_type": "regular1D",
        "n_radial_tics": 512,
    },
    # 辐射 MGD: 与 Gen_eos_op_data 表族 (6 群) 一致
    "radiation": {
        "rt_useMGD": True,
        "rt_mgdNumGroups": 6,
        "rt_mgdBounds": [0.1, 1.0, 10.0, 100.0, 1000.0, 1.0e4, 1.0e5],
        "rt_mgdFlMode": "fl_harmonic",
        "rt_mgdFlCoef": 1.0,
        "boundary": "vacuum",
    },
    # 时间积分控制 (t001 SNB +ug 基线)
    "time": {
        "tstep_change_factor": 1.10,
        "cfl": 0.2,
        "dtinit": 1.0e-15,
        "dtmin": 1.0e-16,
        "dtmax": 2.0e-12,
    },
    # 输出
    # ★ 数据源策略 (2026-09-10 用户指定): **绘图一律用 chk, plt 弃用**。
    #   chk 是 FLASH 的完整重启快照, 变量覆盖度远高于 plt:
    #     实测 chk 含 71 键 (含 pion/eele/ye/sumy/gamc/game/mfpe/qenl/...),
    #     而 plt 受 plot_var 12 项上限约束只有 ~25 键。
    #   → chk 每帧约 0.6 MB (512 格), 完整 1.2 ns 跑 ~13 帧 ≈ 8 MB/腿, 可接受。
    #
    #   时间网格设计 (全脉冲 tmax_full = 1.20e-9 s, 含 50 ps 下降沿后余辉):
    #     checkpointFileIntervalTime = 8.0e-11 s → ⌊1.20e-9/8e-11⌋+1 = 16 帧
    #       (10 时刻剖面需求 ≥10 帧; 16 帧给等间隔抽样留出余量)
    #     plotFileIntervalTime      = 6.0e-10 s → 仅 3 帧, 只作启动健全性检查
    #   ★ 注意: chk 的步间开销 + IO 本身会影响墙钟, 但 chk 写盘 <1 s/帧, 可忽略。
    "output": {
        "plotFileIntervalTime": 6.0e-10,
        "checkpointFileIntervalTime": 8.0e-11,
    },
    # 边界条件
    "bc": {
        "xl_boundary_type": "outflow", "xr_boundary_type": "outflow",
        "yl_boundary_type": "outflow", "yr_boundary_type": "outflow",
        "zl_boundary_type": "outflow", "zr_boundary_type": "outflow",
        "diff_eleXlBoundaryType": "neumann", "diff_eleXrBoundaryType": "neumann",
        "diff_eleYlBoundaryType": "neumann", "diff_eleYrBoundaryType": "neumann",
        "diff_eleZlBoundaryType": "neumann", "diff_eleZrBoundaryType": "neumann",
    },
    # 默认 tmax: 对比测试用极短时间 (速度优先, 用户指定)
    "tmax": 2.0e-10,
    "tmax_full": 1.20e-9,
}

# ── +ug 均匀网格 (两腿完全相同) ──────────────────────────────
GRID: Dict[str, Any] = {
    "nxb": 64,          # 固定块模式: 总格数 = iprocs × nxb
    "iprocs": 8,        # +ug 下一个块一个进程 → mpiexec -n 必须等于此值
    "iGridSize": 0,     # 仅非固定块模式 (不给 -nxb) 使用; 0 = 不写该键
    "dimension": 1,
}

SETUP_BASE = ("-1d +cartesian +ug {nxb_flag} +hdf5typeio "
              "species=cham,targ +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 "
              "ed_maxPulseSections=300")

# ★ 非固定块模式必须显式给 `-nofbs`。
#   实测教训: 只"不给 -nxb"**不会**进入 NON_FIXED_BLOCKSIZE 分支 —— FLASH 默认
#   仍定义 FIXEDBLOCKSIZE 且 NXB=8, 于是 gr_gIndexSize = iProcs×8, par 的
#   iGridSize 被完全忽略 (实测 iProcs=8 → 64 格 / iProcs=16 → 128 格)。
#   开启方式见 bin/parseCmd.py:282 (`--nofbs` → fixedBlockSize=False) 与
#   bin/Readme.SetupVars:97; 快捷方式 `nofbs:-nofbs:+ug:parallelIO=True:`。
#   注意: `not fixedBlockSize` 会让 IO/IOMain/hdf5/Config 强制 DEFAULT parallel
#   (且 parallelIO=False 会 SETUPERROR), 故 -nofbs 与串行 HDF5 不兼容。
NOFBS_FLAG = "-nofbs"

# ── SNB 单元附加内容 (仅 SNB 腿) ─────────────────────────────
SNB_CONFIG_VARIABLES = """
# ── SNB nonlocal thermal conduction diagnostic variables ──
VARIABLE QESH
VARIABLE QEFL
VARIABLE QENL
VARIABLE NELE
VARIABLE MFPE
VARIABLE MFPR
VARIABLE QESX
VARIABLE QESY
VARIABLE GRQX
VARIABLE GRQY
VARIABLE GRAQ
VARIABLE CORQ
VARIABLE QEXG
VARIABLE QEYG
VARIABLE GRGX
VARIABLE GRGY
VARIABLE GRQG
VARIABLE COGQ
"""

# 9 个 SNB 覆盖 F90 (FLASHSNB 专用; 权威副本 = WSL FLASHSNB SNB_1D_laser 工作树,
# 经 SNBOneCH/flash_input 归档。src/SNB_1D_laser 原始包源未打补丁, 不可用)
SNB_OVERRIDE_FILES = (
    "diff_advanceTherm.F90",
    "mgd_qesh.F90",
    "Conductivity.F90",
    "Driver_evolveFlash.F90",
    "Grid_advanceDiffusion.F90",
    "hy_uhd_DataReconstructNormalDir_PPM.F90",
    "hy_uhd_dataReconstOneStep.F90",
    "hy_uhd_getRiemannState.F90",
    "hy_uhd_ragelike.F90",
)

# FLASHSNB 树级 physics 补丁 (t001 六补丁基线中的 #3/#4)
TREE_PATCHES = (
    "physics/Diffuse/DiffuseMain/Diffuse_computeDt.F90",
    "physics/Hydro/HydroMain/unsplit/hy_uhd_getFaceFlux.F90",
)

# plot_var 白名单
# ★ 铁律 1: FLASH 的 IO/IOMain/Config 只声明 `PARAMETER plot_var_1..12`
#   (两棵树实测均为 12), 超过 12 的条目会被静默忽略 ("ignoring unknown
#   parameter") —— 因此白名单**最多 12 项**, 且必须从 1 连续编号。
# ★ 铁律 2: plot_var 是**纯运行时参数** (IO_init.F90:240 经 RuntimeParameters_get
#   读取), 改白名单**无需重新 setup/make** —— 只要 PELE_VAR/PRES_VAR 已在
#   objdir/Flash.h 中定义 (两腿均满足: FL-SH 18/19/22, SNB 29/30/33)。
#
# 白名单设计 (面向绘图需求: tele/tion/trad/dens/pele/pres/nele)
#   nele **不入白名单**, 一律离线推导: nele = Ye·6.02e23·dens,
#     其中 Ye = zbarFrac/abarInv, abarInv = Σ_s X_s/A_s,
#          zbarFrac = Σ_s X_s·Z_s/A_s   (FLASH_MULTISPECIES 路径, 见
#          Eos_getAbarZbar.F90:130-152 与 SNB 源码 diff_advanceTherm.F90:432)
#   原因: FL-SH 腿无 NELE_VAR, 若只为 SNB 腿引入原生 nele 会让两腿**量纲口径
#   不一致** (SNB 原生 nele 在特定分支才更新)。离线推导对两腿完全同源。
#   交叉校验证据: SNB 腿原生 NELE 与离线推导 rel diff < 1e-6 (实测)。
PLOT_VARS_COMMON = ["dens", "tele", "tion", "trad", "pele", "pres", "depo",
                    "cham", "targ", "cond", "fllm"]
PLOT_VARS_BASE = PLOT_VARS_COMMON
PLOT_VARS_SNB = PLOT_VARS_COMMON + ["QESX"]   # 12 项上限


# ══════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════

def log(msg: str, level: str = "INFO") -> None:
    tag = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]",
           "STEP": "[-]"}.get(level, "[i]")
    print(f"  {tag} {msg}", flush=True)


def dx_um(nxb: int, iprocs: int, xmin: Optional[float] = None,
          xmax: Optional[float] = None) -> float:
    """+ug 固定块模式网格间距 [µm]: 域宽/(iProcs·nxb)。"""
    xmin = PARAMS["xmin"] if xmin is None else xmin
    xmax = PARAMS["xmax"] if xmax is None else xmax
    return (xmax - xmin) / (iprocs * nxb) * 1e4


def dx_um_from_igridsize(igridsize: int) -> float:
    """+ug 非固定块模式网格间距 [µm]: 域宽/iGridSize。"""
    return (PARAMS["xmax"] - PARAMS["xmin"]) / igridsize * 1e4


def total_cells(nxb: int, iprocs: int) -> int:
    """固定块模式全局格数 = iProcs × nxb。"""
    return iprocs * nxb


def leg_dir(model: str) -> Path:
    return T002_DIR / ("sim_" + model)


def leg_input_dir(model: str) -> Path:
    return leg_dir(model) / "flash_input"


def leg_output_dir(model: str) -> Path:
    return leg_dir(model) / "flash_output"


def setup_flags(nxb: Optional[int] = None, fixed_blocksize: bool = True) -> str:
    """构造 setup 命令行片段。

    Args:
        nxb: 固定块模式的每块格数; None 或 fixed_blocksize=False → 非固定块模式
             (改为传 `-nofbs`, 全局格数由 par 的 iGridSize 决定)。
    """
    if fixed_blocksize and nxb:
        nxb_flag = f"-nxb={int(nxb)}"
    else:
        nxb_flag = NOFBS_FLAG
    return SETUP_BASE.format(nxb_flag=nxb_flag).replace("  ", " ").strip()


def wsl_path(win_path: Path) -> str:
    """Windows 绝对路径 → WSL /mnt/<drive>/... 路径。"""
    p = Path(win_path).resolve().as_posix()
    drive, rest = p.split(":", 1)
    return f"/mnt/{drive.lower()}/{rest.lstrip('/')}"


def run_wsl(cmd: str, distro: str = "Ubuntu-22.04", timeout: int = 7200,
            verbose: bool = False) -> Tuple[int, str]:
    """在 WSL 中执行命令, 返回 (exit_code, stdout+stderr)。

    ★ 铁律: `wsl bash -lc "<cmd>"` 存在**双层 bash 展开** —— 外层 shell 会先
    展开 $var/$?/$(...)。因此内联命令中禁止依赖 shell 循环变量或 `$?`,
    一律在 Python 端展开; 需要条件判定时用 if/else 落盘标记。
    """
    if verbose:
        log(f"执行: {cmd[:160]}{'...' if len(cmd) > 160 else ''}")
    try:
        p = subprocess.run(["wsl", "-d", distro, "bash", "-lc", cmd],
                           capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"[timeout after {timeout}s]"


def find_tree(model: str, distro: str = "Ubuntu-22.04") -> Optional[str]:
    """探测 WSL 中的 FLASH 树根目录 (含 ./setup 与 ./source)。

    model="flsh" → 标准树 ~/<user>/FLASH/FLASH4.8  (与 runner.user_flash_home 一致)
    model="snb"  → FLASHSNB 树 ~/<user>/FLASH/FLASHSNB/FLASH4.8

    注意: 这里的命令经 subprocess argv 传给 wsl (不经过 Windows shell), 因此
    `$HOME` 不会被外层展开。但 `wsl -lc` 登录 shell 可能打印横幅, 故逐行过滤,
    只接受以 '/' 开头且形如路径的行。
    """
    def _first_path(cmd: str) -> Optional[str]:
        for attempt in range(3):          # 首次 wsl 可能冷启动超时, 重试
            code, out = run_wsl(cmd, distro, timeout=120)
            for line in out.splitlines():
                s = line.strip()
                if s.startswith("/") and "/FLASH" in s:
                    return s.rstrip("/")
            if code != 124:
                break
        return None

    if model == "snb":
        p = _first_path('find "$HOME" -maxdepth 4 -type d -name FLASHSNB 2>/dev/null')
        if not p:
            return None
        cand = f"{p}/FLASH4.8"
        code, out = run_wsl(f'test -d "{cand}" && echo "{cand}"', distro, timeout=90)
        return cand if cand in out else None
    return _first_path('ls -d "$HOME"/*/FLASH/FLASH4.8 2>/dev/null')


def tree_exists(root: str, distro: str = "Ubuntu-22.04") -> bool:
    code, out = run_wsl(
        f'test -x "{root}/setup" && test -d "{root}/source" && echo TREE_OK',
        distro, timeout=90)
    return "TREE_OK" in out


def wsl_mkdir(path_wsl: str, distro: str = "Ubuntu-22.04") -> None:
    run_wsl(f'mkdir -p "{path_wsl}"', distro, timeout=60)


def collect_outputs(objdir: str, basenm: str, log_file: str, out_dir: Path,
                    run_log: str, distro: str = "Ubuntu-22.04") -> bool:
    """把 objdir 中的输出拷回 Windows, 并在 WSL 侧删除 (用后即转)。"""
    out_wsl = wsl_path(out_dir)
    wsl_mkdir(out_wsl, distro)
    code, out = run_wsl(
        f'cp -f "{objdir}"/{basenm}* "{objdir}"/{log_file} '
        f'"{objdir}"/{run_log} "{out_wsl}"/ 2>/dev/null; '
        f'rm -f "{objdir}"/{basenm}* {basenm}* 2>/dev/null; echo COLLECT_DONE',
        distro, timeout=600)
    return "COLLECT_DONE" in out


def stamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")
