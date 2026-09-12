"""t003 场景 —— SNB 非局域热传导烧蚀速率核查 的**唯一参数源**
═══════════════════════════════════════════════════════════════════════════════

目标 (用户需求)
--------------
核查「SNB 的质量烧蚀速率显著快于 FL-SH」这一现象是 **物理** 的
还是 **代码/设置** 的问题。

方法: 受控双仿真对比 —— 两腿除**电子热传导算法**外一切相同。

场景来源
--------
本场景忠实复现 SNB 作者提供的示例 **SNB_1D_laser**
(权威副本: `SNBtest/src/SNB/SNB_1D_laser/SNB_1D_laser/`):

    CH 靶板   x ∈ [-50, 0] µm   (ρ=1.04 g/cm³)
      └ 示踪层 tar3 @ [-2.2, -2.1] µm  (0.1 µm)
      └ 示踪层 tar2 @ [-0.1, 0] µm     (0.1 µm)
    He 腔体   x ∈ [0, 250] µm   (ρ=1e-6 g/cm³, 1.6 mbar)
    激光      从 x=+500 µm 处入射 (+x → -x), 0.351 µm, 1.5e14 W/cm²

作者的原始 setup 指令 (`src/SNB/运行指令.txt`):

    ./setup -auto SNB_1D_laser -1d +cartesian +ug -nxb=8 +hdf5typeio \\
            species=cham,tar1,tar2,tar3 +mtmmmt +laser +uhd3t +mgd \\
            mgd_meshgroups=10 -objdir=SNB_1D_laser

两腿设计 (★ 受控对比的关键)
--------------------------
| 项 | FL-SH 腿 | SNB 腿 |
|---|---|---|
| FLASH 树 | 标准 `~/QC/FLASH/FLASH4.8` | `~/QC/FLASH/FLASHSNB/FLASH4.8` |
| `diff_advanceTherm.F90` | 该树**原生**（纯限流 SH） | 作者 SNB 版（多群非局域） |
| 其余 7 个覆盖 F90 | 原生 | 作者版 |
| Config / Makefile / Simulation_* / cn4 | **完全相同** | **完全相同** |
| par 除 basenm/log_file/plot_var | **完全相同** | **完全相同** |

★ t002 的教训: 那次两腿的 `diff_eleFlMode` 不同 (fl_minmax vs fl_none),
  引入了额外变量; 本场景**两腿统一用示例作者的 `fl_harmonic`/0.06**, 
  把差异收窄到「SNB 多群非局域 vs 纯限流 SH」这一条。

几何权威来源
------------
`src/SNB/SNB_1D_laser/SNB_1D_laser/Simulation_initBlock.F90:119-130`
(逐行对应, 见 LAYERS 表)。域与材料常数来自同目录 `flash.par`。

⚠ 与示例的两处**有意偏离** (纯数值设置, 不改物理)
------------------------------------------------
1. **网格分辨率**: 示例 `-nxb=8` × 4 进程 = 仅 32 格 (dx≈9.4 µm),
   CH 板 (50 µm) 只有 ~5 格, **无法分辨烧蚀**。本场景用 `-nxb=128` × 8 进程
   = 1024 格 (dx≈0.293 µm), 并保留 +ug 均匀网格 (SNB 铁律)。
2. **输出策略**: 示例只给 `plotFileIntervalTime=1e-11`; 本场景**以 chk 为
   绘图数据源** (chk 71 键 vs plt 25 键, 且 float64), plt 仅留 3 帧作健全性检查。
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── 仓库根定位 (pyproject.toml 锚点) ─────────────────────────
_REPO_ROOT = Path(__file__).resolve().parent
for _ in range(16):
    if (_REPO_ROOT / "pyproject.toml").exists():
        break
    _REPO_ROOT = _REPO_ROOT.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ── 场景目录 ────────────────────────────────────────────────
T003_DIR = Path(__file__).resolve().parent.parent
SNBTEST_DIR = T003_DIR.parent.parent            # .../SNB/SNBtest
SRC_SNB_DIR = SNBTEST_DIR / "src" / "SNB"

# ★ 权威示例副本 (作者原版; 含 SNB 版 diff_advanceTherm.F90 与 flash.par)
EXAMPLE_DIR = SRC_SNB_DIR / "SNB_1D_laser" / "SNB_1D_laser"
# ★ 纯限流 SH 参考版 diff_advanceTherm.F90 (作者同时提供的"原版", 无 SNB 块)
STOCK_DIFF_SRC = SRC_SNB_DIR / "f90" / "diff_advanceTherm.F90"
STOCK_COND_SRC = SRC_SNB_DIR / "f90" / "Conductivity.F90"

DOCS_DIR = T003_DIR / "docs"
RESULT_DIR = T003_DIR / "results"

# ── 两腿定义 (唯一差异集中处) ────────────────────────────────
LEGS: Dict[str, Dict[str, Any]] = {
    "flsh": {
        "model": "flsh",
        "label": "FL-SH",
        "desc": "flux-limited Spitzer-Harm (local, 标准树原生 CPU 热传导)",
        "tree": "standard",
        "sim_name": "T003_FLSH",
        "objdir": "T003_FLSH_obj",
        "basenm": "t003flsh_",
        "log_file": "t003flsh.log",
        "par_file": "t003flsh.par",
        "has_snb": False,
        # ★ par 层面的物理开关与 SNB 腿**完全一致** (示例作者的取值)
        "diff_eleFlMode": "fl_harmonic",
        "diff_eleFlCoef": 0.06,
    },
    "snb": {
        "model": "snb",
        "label": "SNB",
        "desc": "SNB multigroup nonlocal electron transport（作者实现）",
        "tree": "snb",
        "sim_name": "T003_SNB",
        "objdir": "T003_SNB_obj",
        "basenm": "t003snb_",
        "log_file": "t003snb.log",
        "par_file": "t003snb.par",
        "has_snb": True,
        "diff_eleFlMode": "fl_harmonic",
        "diff_eleFlCoef": 0.06,
    },
}

# ── 从示例提取的物理参数 (权威副本) ──────────────────────────
PARAMS: Dict[str, Any] = {
    # 域 (示例 flash.par: xmin/xmax)
    "xmin": -50.0e-4,           # cm → -50 µm
    "xmax": 250.0e-4,           # cm → +250 µm
    "t_initial": 290.11375,     # K (室温)
    "smallX": 1.0e-99,
    # 4 物种
    "species": ["cham", "tar1", "tar2", "tar3"],
    "cham": {"cn4": "He-BADGER-TOPS-Final.cn4", "rho": 1.0e-6,
             "A": 4.002602, "Z": 2.0},
    "tar1": {"cn4": "CH-BADGER-TOPS-Final.cn4", "rho": 1.04,
             "A": 6.5, "Z": 3.5, "ZMin": 0.02},
    "tar2": {"cn4": "CH-BADGER-TOPS-Final.cn4", "rho": 1.04,
             "A": 6.5, "Z": 3.5, "ZMin": 0.02},
    "tar3": {"cn4": "CH-BADGER-TOPS-Final.cn4", "rho": 1.04,
             "A": 6.5, "Z": 3.5, "ZMin": 0.02},
    # ★ 分层几何: 逐行对应示例 Simulation_initBlock.F90:119-130
    #   (species, x_lo, x_hi) 单位 cm; cham 为**兜底**(其余区域)
    "layers": [
        ("tar1", -50.0e-4, -2.2e-4),    # CH 主靶 (initBlock: x<0 且 x>-50e-4)
        ("tar3", -2.2e-4, -2.1e-4),     # 示踪层 (initBlock: -2.2e-4<x<-2.1e-4)
        ("tar1", -2.1e-4, -0.1e-4),     # CH 主靶
        ("tar2", -0.1e-4, 0.0),         # 示踪层 (initBlock: -0.1e-4<x<0)
    ],
    "chamber": ("cham", 0.0, 250.0e-4),
    # 激光 (示例 flash.par ed_* 组)
    "laser": {
        "wavelength_um": 0.351,
        "n_sections": 4,
        "times": [0.0, 0.2e-9, 0.99e-9, 1.0e-9],
        "powers": [0.0, 1.5e14, 1.5e14, 0.0],
        "lensX": 500.0e-4,          # +500 µm → 激光沿 -x 入射
        "targetX": 0.0,
        "cross_section": "uniform",
        "n_rays": 1,
        "grid_type": "regular1D",
        "n_radial_tics": 512,
    },
    # 辐射 MGD: 10 群 (与 BADGER 表族一致; mgd_meshgroups=10 必须匹配)
    "radiation": {
        "rt_useMGD": True,
        "rt_mgdNumGroups": 10,
        "rt_mgdBounds": [1.0e-1, 3.981e-1, 1.585e0, 6.31e0, 2.51e1,
                         1.0e2, 3.981e2, 1.585e3, 6.31e3, 2.51e4, 1.0e5],
        "rt_mgdFlMode": "fl_larsen",
        "rt_mgdFlCoef": 1.0,
        "boundary": "vacuum",
        "op_tableEnergyTolerance": 1.0e-2,
    },
    # 时间积分 (示例 flash.par)
    "time": {
        "tstep_change_factor": 1.10,
        "cfl": 0.2,
        "dtinit": 1.0e-15,
        "dtmin": 1.0e-16,
        "dtmax": 2.0e-12,
        "nend": 10000000,
    },
    # 输出: ★ chk 为主 (绘图数据源), plt 仅 3 帧健全性检查
    #   示例 tmax=0.8 ns → chk 5e-11 ⇒ ⌊0.8e-9/5e-11⌋+1 = 17 帧 (≥10 时刻需求)
    "output": {
        "checkpointFileIntervalTime": 5.0e-11,
        "plotFileIntervalTime": 4.0e-10,
    },
    # 示例 flash.par 的 tmax
    "tmax": 0.8e-9,
    "tmax_short": 1.0e-11,      # 短时快速验证
}

# ── +ug 均匀网格 ────────────────────────────────────────────
# 示例仅 32 格 (dx≈9.4 µm) 无法分辨烧蚀 → 本场景 8×128 = 1024 格 (dx≈0.293 µm)
GRID: Dict[str, Any] = {
    "nxb": 128,
    "iprocs": 8,
    "iGridSize": 0,
    "dimension": 1,
}

# 示例运行指令中的 setup 片段 (逐字对齐, 仅 -nxb 数值随分辨率变化)
SETUP_BASE = ("-1d +cartesian +ug {nxb_flag} +hdf5typeio "
              "species=cham,tar1,tar2,tar3 +mtmmmt +laser +uhd3t +mgd "
              "mgd_meshgroups=10")
NOFBS_FLAG = "-nofbs"

# ── 文件分类 (★ 用户特别强调"注意那些文件的复制生成") ────────
# 共享件: 两腿**逐字节相同** (从示例原样复制)
SHARED_FILES = (
    "Config",
    "Makefile",
    "Simulation_data.F90",
    "Simulation_init.F90",
    "Simulation_initBlock.F90",
    "mgd_qesh.F90",           # Makefile 引用; 仓库原本缺失, 已从 WSL 工作副本归档
)
# 共享数据表 (EOS + opacity)
SHARED_CN4 = ("He-BADGER-TOPS-Final.cn4", "CH-BADGER-TOPS-Final.cn4")

# SNB 腿专属覆盖 F90 (作者的 7 个非 diff 覆盖; diff_advanceTherm 单独处理)
SNB_OVERRIDES = (
    "Conductivity.F90",
    "Driver_evolveFlash.F90",
    "Grid_advanceDiffusion.F90",
    "hy_uhd_DataReconstructNormalDir_PPM.F90",
    "hy_uhd_dataReconstOneStep.F90",
    "hy_uhd_getRiemannState.F90",
    "hy_uhd_ragelike.F90",
)
# ★ 两腿的核心差异文件: SNB 腿 = 作者 SNB 版; FL-SH 腿 = 不部署 (用标准树原生)
DIFF_THERM_FILE = "diff_advanceTherm.F90"

# FLASHSNB 树级 physics 补丁 (来自 t001 六补丁基线; SNB 腿需要)
TREE_PATCHES = (
    "physics/Diffuse/DiffuseMain/Diffuse_computeDt.F90",
    "physics/Hydro/HydroMain/unsplit/hy_uhd_getFaceFlux.F90",
)

# plot_var 白名单 (≤12; 超出项会被 FLASH 静默忽略)
# 注: chk 是绘图数据源, chk 不受白名单限制; 此白名单仅影响 plt 健全性检查帧。
PLOT_VARS = ["dens", "tele", "tion", "trad", "pele", "pres",
             "depo", "cond", "cham", "tar1", "tar2", "tar3"]


# ══════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════
def log(msg: str, level: str = "INFO") -> None:
    tag = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]",
           "STEP": "[-]"}.get(level, "[i]")
    print(f"  {tag} {msg}", flush=True)


def dx_um(nxb: int, iprocs: int) -> float:
    """+ug 固定块模式网格间距 [µm]。"""
    return (PARAMS["xmax"] - PARAMS["xmin"]) / (iprocs * nxb) * 1e4


def dx_um_from_igridsize(igridsize: int) -> float:
    return (PARAMS["xmax"] - PARAMS["xmin"]) / igridsize * 1e4


def leg_dir(model: str) -> Path:
    return T003_DIR / ("sim_" + model)


def leg_input_dir(model: str) -> Path:
    return leg_dir(model) / "flash_input"


def leg_output_dir(model: str) -> Path:
    return leg_dir(model) / "flash_output"


def setup_flags(nxb: Optional[int] = None) -> str:
    nxb_flag = f"-nxb={int(nxb)}" if nxb else NOFBS_FLAG
    return SETUP_BASE.format(nxb_flag=nxb_flag)


def wsl_path(win_path: Path) -> str:
    p = Path(win_path).resolve().as_posix()
    drive, rest = p.split(":", 1)
    return f"/mnt/{drive.lower()}/{rest.lstrip('/')}"


def run_wsl(cmd: str, distro: str = "Ubuntu-22.04", timeout: int = 7200,
            verbose: bool = False) -> Tuple[int, str]:
    """在 WSL 中执行命令, 返回 (exit_code, stdout+stderr)。

    ★ 铁律: `wsl bash -lc "<cmd>"` 存在**双层 bash 展开** —— 外层 shell 会先
    展开 $var/$?/$(...)。内联命令中禁止依赖 shell 变量与 `$?`, 一律在 Python
    端展开; 条件判定用 if/else 落盘标记。
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
    """探测 WSL 中的 FLASH 树根目录 (含 ./setup 与 ./source)。"""
    def _first_path(cmd: str) -> Optional[str]:
        for _ in range(3):
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
        distro, timeout=900)
    return "COLLECT_DONE" in out


def stamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")
