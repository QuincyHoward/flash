"""t004 —— 「辐射开关」2×2 受控矩阵 的**唯一参数源**
═══════════════════════════════════════════════════════════════════════════════

目的 (用户需求)
--------------
单另设置脚本, 分别在 **FL-SH 侧** 与 **SNB 侧** 各跑「开启辐射 / 关闭辐射」两个
仿真, 共 **4 个仿真**, 并做四腿对比。

关辐射的**权威机制** (用户指定参考 tracer 家族 `_F` 后缀变体)
------------------------------------------------------------
`flash/scenarios/private/tracer/VCH_ml_F/VCH_ml_F.py:293-303` 明文:

    # 关闭辐射输运 (F 变体, RADIATION_OFF=True) — 机制学习自参考
    # ReDo042sp_CH042sp*umF vs *umL 对比: 源码/setup/编译完全不变
    # (Makefile/全部 F90 逐字节相同), **纯运行时关闭三处开关**:
    #   rt_useMGD   .true. → .false.   (MGD 多群辐射输运)
    #   useOpacity  .true. → .false.   (不透明度)
    #   useRadTrans          → .false. (辐射输运总开关)

即 **关辐射是纯 par 改动, 零源码改动**。

★ SNB 侧的关键差异 (t003 已查明)
-------------------------------
SNB 侧**不能**只靠 par 三开关 —— 因为作者 `Driver_evolveFlash.F90:301,325`
的 `call RadTrans(...)` 被**注释掉**了: 辐射在 SNB 腿**本来就永不推进**,
par 三开关形同虚设 (开也开不起来)。
→ 故 SNB 侧两腿**统一使用 t003 的 `radON` 驱动变体**(恢复 RadTrans),
  再用与 FL-SH **完全相同的 par 三开关**来开/关辐射。
  这样两侧的"关辐射"手段逐字一致, 四腿对比才受控。

四腿矩阵
--------
| 腿 | 树 | Driver | diff_advanceTherm | par 辐射三开关 |
|---|---|---|---|---|
| `flsh/radon`  | 标准     | 原生 (本就调用 RadTrans) | 原生        | **.true.**(默认) |
| `flsh/radoff` | 标准     | 原生                    | 原生        | **.false. ×3**   |
| `snb/radon`   | FLASHSNB | `radON` 变体            | 作者 SNB 版 | **.true.**       |
| `snb/radoff`  | FLASHSNB | `radON` 变体            | 作者 SNB 版 | **.false. ×3**   |

同侧两腿**共用 objdir 与二进制**(辐射是纯 par 开关) → 每侧只编译一次, 跑两次。

几何/激光/材料/网格/时间积分全部**继承 t003**(即作者示例 `SNB_1D_laser`),
保证与 t003 结论可直接互引。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# ── 继承 t003 的全部物理参数与 WSL 工具 ──────────────────────
_T004 = Path(__file__).resolve().parent.parent          # .../Test/t004
_T003_COMMON = _T004.parent / "t003" / "common"
if str(_T003_COMMON) not in sys.path:
    sys.path.insert(0, str(_T003_COMMON))

import t003_common as T3  # noqa: E402

# ── 再导出 t003 的共享量 (调用方统一从本模块取) ──────────────
PARAMS = T3.PARAMS                 # 几何/激光/辐射/时间积分 (权威)
GRID = T3.GRID                     # +ug 网格
SETUP_BASE = T3.SETUP_BASE
NOFBS_FLAG = T3.NOFBS_FLAG
SHARED_FILES = T3.SHARED_FILES
SHARED_CN4 = T3.SHARED_CN4
SNB_OVERRIDES = T3.SNB_OVERRIDES
DIFF_THERM_FILE = T3.DIFF_THERM_FILE
TREE_PATCHES = T3.TREE_PATCHES
PLOT_VARS = T3.PLOT_VARS
EXAMPLE_DIR = T3.EXAMPLE_DIR
SRC_SNB_DIR = T3.SRC_SNB_DIR

log = T3.log
stamp = T3.stamp
run_wsl = T3.run_wsl
wsl_path = T3.wsl_path
find_tree = T3.find_tree
tree_exists = T3.tree_exists
wsl_mkdir = T3.wsl_mkdir
collect_outputs = T3.collect_outputs
setup_flags = T3.setup_flags
dx_um = T3.dx_um

T004_DIR = _T004
DOCS_DIR = _T004 / "docs"
RESULT_DIR = _T004 / "results"
# t003 的诊断变体目录 (radON Driver / limiterON 热传导源)
T003_VARIANTS = _T004.parent / "t003" / "variants"

# ── 关辐射的 par 三开关 (权威: tracer VCH_ml_F.py:300-303) ────
RAD_OFF_SWITCHES: Dict[str, Any] = {
    "rt_useMGD": False,
    "useOpacity": False,
    "useRadTrans": False,
}
# 开启辐射时**显式写回**真值, 避免继承示例 par 的隐式默认造成歧义
RAD_ON_SWITCHES: Dict[str, Any] = {
    "rt_useMGD": True,
    "useOpacity": True,
    "useRadTrans": True,
}

# ── 输出 tag (= t004/sim_<model>/<tag>) ──────────────────────
TAG_ON = "radon"
TAG_OFF = "radoff"


def leg_cfg(model: str, rad_on: bool) -> Dict[str, Any]:
    """返回四腿之一的配置。

    model: "flsh" | "snb";  rad_on: True=辐射开 / False=辐射关
    """
    tag = TAG_ON if rad_on else TAG_OFF
    return {
        "model": model,
        "rad_on": rad_on,
        "tag": tag,
        "label": f"{T3.LEGS[model]['label']} / rad {'ON' if rad_on else 'OFF'}",
        "short": f"{T3.LEGS[model]['label']}-{'radON' if rad_on else 'radOFF'}",
        # 同侧两腿共用树/单元/objdir (辐射是纯 par 开关 → 一份二进制跑两次)
        "tree": T3.LEGS[model]["tree"],
        "sim_name": f"T004_{model.upper()}",           # 同侧共用
        "objdir": f"T004_{model.upper()}_obj",         # 同侧共用
        "basenm": f"t004{model}_{tag}_",               # 每腿独立 → 输出不撞
        "log_file": f"t004{model}_{tag}.log",
        "par_file": f"t004{model}_{tag}.par",
        "has_snb": model == "snb",
        "diff_eleFlMode": "fl_harmonic",               # 两腿统一 (t003 结论)
        "diff_eleFlCoef": 0.06,
        # SNB 侧强制用 radON 驱动; FL-SH 侧用原生 (本就调用 RadTrans)
        "driver_variant": "radon" if model == "snb" else "example",
        "rad_switches": RAD_ON_SWITCHES if rad_on else RAD_OFF_SWITCHES,
    }


# 四腿全集 (顺序固定, 便于遍历与出图)
LEG_KEYS = [("flsh", True), ("flsh", False), ("snb", True), ("snb", False)]
LEGS: Dict[str, Dict[str, Any]] = {
    f"{m}_{('on' if r else 'off')}": leg_cfg(m, r) for m, r in LEG_KEYS
}


# ── 目录 (覆盖 t003 的; 使绘图层可直接复用) ──────────────────
def leg_dir(model: str) -> Path:
    return T004_DIR / ("sim_" + model)


def leg_input_dir(model: str) -> Path:
    """同侧两腿共用一个 flash_input (单元/Config/Makefile 相同, 仅 par 不同)。"""
    return leg_dir(model) / "flash_input"


def leg_output_dir(model: str) -> Path:
    return leg_dir(model) / "flash_output"


def resolve_outdir(model: str, tag: str = "") -> Path:
    """t004/sim_<model>/flash_output/<tag>; 无 tag 回退到 flash_output。"""
    base = leg_output_dir(model)
    if tag:
        d = base / tag
        if d.exists():
            return d
    return base


def results_dir(sub: str = "") -> Path:
    d = RESULT_DIR / sub if sub else RESULT_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def dx_um_from_igridsize(igridsize: int) -> float:
    return T3.dx_um_from_igridsize(igridsize)
