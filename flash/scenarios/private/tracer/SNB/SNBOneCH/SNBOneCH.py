#!/usr/bin/env python3
"""SNBOneCH —— OneCH_ml 几何/材料 + SNB 非局域热传导（**双标记**版）
═══════════════════════════════════════════════════════════════════════════════

定位
----
与 `tracer/SNB/SNBOneCH_ml` 同族，但**只用两个物种标记**：`cham` + `targ`。
物理设置（域/密度/材料/激光/辐射/EOS/流体）**严格取自 `tracer/OneCH_ml`**，
仅把电子热传导换成 **SNB 模型**，因此两场景（local vs nonlocal）可直接对比。

与 OneCH_ml 的关系
------------------
| 项 | OneCH_ml | 本场景 |
|---|---|---|
| 域 | `x ∈ [-0.04, 0.01]` cm | 同 |
| 固体靶 | CH，`x ∈ [0, 56.1]` µm，1.0 g/cm³ | 同（合并为单层） |
| 腔室 | He，1.0e-6 g/cm³ | 同 |
| 激光 | 0.351 µm，82 段，透镜 x=-1.0 | 同 |
| 表 | He-BADGER + CH-QC-1-001 | 同 |
| 物种 | 8 标记（cham/shld/samp/tar1/2/3/4/6） | **2 标记（cham/targ）** |
| 热传导 | Spitzer + flux limiter（限流 local） | **SNB 非局域多群** |
| 网格 | AMR lrefine 9 | **`+ug` 均匀网格**（SNB 铁律） |

SNB 设置（本场景默认）
----------------------
1. **辐射默认开启**：`rt_useMGD` / `useOpacity` / `useRadTrans` 三开关全 `.true.`，
   且 SNB 腿使用 **radON 驱动变体**（作者原版把 `call RadTrans` 注释了）。
2. **默认 `diff_eleFlMode = "fl_none"`**：项目约定（该键在 SNB 电子路径上实测为
   **no-op**，见 `SNB/docs/05_坑位清单.md` P1 更正块）。
3. **`gr_hypreUseFloor = .false.`**：★★★ SNB 崩塌真正主因，**硬校验**（见下）。
4. **首次使用场景必须重新编译**：`run_scene.py` 以构建指纹判定，
   指纹不一致或 `flash4` 缺失时**无视 `--skip-setup/--skip-make`** 强制 setup+make。

实现方式
--------
本脚本**不重复实现** SNB 物理与部署逻辑，全部复用核心模块 `SNB/SNB`：
* F90 覆盖件 ← `SNB/SNB/source/snb_package/`
* par 基线     ← 仿 `SNBOneCH_ml`：`_par_layers.CH_FLASH_PAR` + SNB 覆写
* 部署/setup/make/运行/收集 ← `SNB/SNB/scripts/run/run_scene.py`
* chk 健康检查 ← `SNB/SNB/scripts/analysis/chk_probe.py`
本脚本只负责**生成 2 标记的单元文件（Config/Makefile/Simulation_*/initBlock）+ par**。

用法
----
    PY=C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe
    cd flash/scenarios/private/tracer/SNB/SNBOneCH

    $PY SNBOneCH.py --stage generate      # 生成场景输入（不编译）
    $PY SNBOneCH.py --stage smoke         # ★ 先短时 (tmax=1e-11) 验证可跑通
    $PY SNBOneCH.py --stage full          # 正式时间 (默认 2.0e-10)
    $PY SNBOneCH.py --stage check         # chk 健康检查
    $PY SNBOneCH.py --stage plot          # 与 OneCH_ml 的 nele/tele/pele 对比图
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Bootstrap: 定位 flash 包根 ─────────────────────────────
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE
for _ in range(15):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

PY = sys.executable

# ── 复用 SNB 核心模块 ──────────────────────────────────────
def _find_snb_core() -> Path:
    """向上逐级查找 `SNB/SNB` 核心模块（同时含 scripts/ 与 source/）。

    本场景在 `private/tracer/SNB/SNBOneCH`，到核心模块要多跳一层
    （`private/SNB/SNB`），故除 `anc/SNB`、`anc.parent/SNB` 外，
    还要试 `anc/SNB/SNB`。不写死层数，便于目录整体搬迁。
    """
    for anc in [_HERE] + list(_HERE.parents):
        for cand in (anc / "SNB", anc.parent / "SNB", anc / "SNB" / "SNB"):
            if (cand / "scripts").is_dir() and (cand / "source").is_dir():
                return cand
    raise SystemExit(f"[X] 未找到 SNB 核心模块 (从 {_HERE} 向上搜索)")


SNB = _find_snb_core()
sys.path.insert(0, str(SNB / "scripts"))
sys.path.insert(0, str(SNB / "scripts" / "generate"))   # for `import gen_scene`
import snb_params as P                                    # noqa: E402

RUN_SCENE = SNB / "scripts" / "run" / "run_scene.py"
PROBE = SNB / "scripts" / "analysis" / "chk_probe.py"
SNB_PKG = SNB / "source" / "snb_package"
TABLES = SNB / "source" / "tables"

# ── 物理设置: **严格取自 OneCH_ml** ────────────────────────
from flash.scenarios.private.tracer._par_layers import CH_FLASH_PAR   # noqa: E402
from flash.scenarios.private.tracer.OneCH_ml.OneCH_ml import (        # noqa: E402
    config_constants as ONECH_CFG,
)

# OneCH_ml 的分层几何 → 本场景合并为**单层固体靶**
DELTA_UM = ONECH_CFG["delta_um"]      # 0.1
L6_UM = ONECH_CFG["L6_um"]            # 6.0
D_UM = ONECH_CFG["D_um"]              # 50.0
SOLID_UM = L6_UM + DELTA_UM + D_UM    # 56.1 µm —— 与 OneCH_ml 固体区完全相同
XMIN = ONECH_CFG["xmin"]              # -0.04 cm
XMAX = ONECH_CFG["xmax"]              # 0.01 cm

# ── 场景常量 ──────────────────────────────────────────────
SIM_NAME = "SNBOneCH"
PAR_FILENAME = "snb_onech.par"
PAR_FILENAME_SMOKE = "snb_onech_smoke.par"
BASENM = "snbonech_"
BASENM_SMOKE = "snbonech_smoke_"
LOG_FILE = "snbonech.log"
LOG_FILE_SMOKE = "snbonech_smoke.log"
SPECIES_LIST = ["cham", "targ"]

NXB = 128
IPROCS = 16              # +ug: mpiexec -n 必须 == iProcs (24 核机上留余量)
N_GROUPS = 10
DTMAX = 2.0e-14          # ★★ SNB 并列前提 (docs/08)
# ★ 2026-09-12: 正式时间由 2.0e-10 延长到 **1.6e-9**，与 OneCH_ml 的规范 tmax 对齐
#   （0.2 ns 太短，靶尚未充分压缩/烧蚀，与 FL-SH 侧不可比）。
TMAX_FULL = 1.6e-9
TMAX_SMOKE = 1.0e-11     # ★ 首跑验证规范
CHK_DT_FULL = 2.0e-11    # 1.6 ns → 81 帧
CHK_DT_SMOKE = 1.0e-12
PLT_DT = 5.0e-11         # 1.6 ns → 32 帧
T_INIT = 290.11375

# 表: 与 OneCH_ml 完全相同
HE_CN4 = "He-BADGER-TOPS-Final.cn4"
CH_CN4 = "CH-QC-1-001.cn4"

SCENE = _HERE / "scene"
IMAGES = _HERE / "images"
LOGS = _HERE / "logs"
INP = SCENE / "sim_snb" / "flash_input"
FO = SCENE / "flash_output" / "sim_snb"


def log(msg: str, level: str = "INFO") -> None:
    tag = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]",
           "STEP": "[-]"}.get(level, "[i]")
    print(f"  {tag} {msg}", flush=True)


# ══════════════════════════════════════════════════════════════
# 物种定义（2 标记）
# ══════════════════════════════════════════════════════════════
def build_species_defs() -> List[dict]:
    """cham(He) + targ(CH)。

    密度/材料同 OneCH_ml：`sim_rhoCham=1e-6`、`sim_rhoTarg=1.0`、CH 表与
    He 表均与 OneCH_ml 一致；固体靶半径经运行时参数 `sim_targRadius`
    传给 `Simulation_initBlock`，**只改 par 即可调整靶厚**。
    """
    return [
        {"name": "cham", "file": HE_CN4, "rho": 1.0e-6,
         "A": 4.002602, "Z": 2.0},
        {"name": "targ", "file": CH_CN4, "rho": 1.0,
         "A": 6.509, "Z": 3.5, "ZMin": 1e-23,
         "radius": SOLID_UM * 1e-4, "radius_param": "sim_targRadius"},
    ]


# ══════════════════════════════════════════════════════════════
# par: CH_FLASH_PAR(OneCH_ml 基线) + SNB 覆写
# ══════════════════════════════════════════════════════════════
# 与 OneCH_ml 不同的**唯一**一类键 = SNB 热传导 + 步长 + 辐射开关 + `+ug` 网格。
# 其余（几何/物种/材料/激光/EOS/流体/边界）全部保持 OneCH_ml 原值。
SNB_OVERRIDE: Dict[str, Any] = {
    # ── 热传导（SNB）──────────────────────────────────────
    "useDiffuse": True, "useDIffuseTherm": True, "useConductivity": True,
    "diff_useEleCond": True,
    "diff_eleFlMode": P.CONDUCTION["diff_eleFlMode"],   # 默认 fl_none（项目约定）
    "diff_eleFlCoef": P.CONDUCTION["diff_eleFlCoef"],
    "diff_thetaImplct": 1.0,
    "diff_anisoCondForEle": False,
    "dt_diff_factor": 1.0e100,
    # ★★★ 承重键：FLASH 默认 .true. → SNB 多群解失真 → 崩塌
    "gr_hypreUseFloor": False,
    "useHeatexchange": True, "hx_dtFactor": 1.0e100, "rt_dtFactor": 1.0e100,
    # ── 时间积分（SNB 稳定化）────────────────────────────
    "tstep_change_factor": 1.10, "cfl": 0.2,
    "dtinit": 1.0e-15, "dtmin": 1.0e-16, "dtmax": DTMAX,
    # ── 辐射：默认开启（三开关）──────────────────────────
    "rt_useMGD": True, "useOpacity": True, "useRadTrans": True,
    # ── `+ug` 均匀网格（SNB 铁律）────────────────────────
    "nblockx": 1, "lrefine_max": 1, "lrefine_min": 1, "lrefine_min_init": 1,
}
# 双标记场景需剔除的**其它物种**键（FLASH 会因未注册参数报错）
_ABSENT = ("shld", "samp")
# ★ plot_var 白名单 ≤12 项、从 1 连续编号（第 13 项起被静默忽略）。
#   含 SNB 诊断量 `fllm`（限流因子）与 `cond`（电导率）便于核查热流路径。
_PLOT_VARS = ["dens", "depo", "tele", "tion", "trad", "ye", "sumy",
              "cham", "targ", "fllm", "cond", "pres"]


def build_par(tmax: float, chk_dt: float, basenm: str, log_file: str,
              tag: str) -> str:
    """生成 par 文本。基线 = OneCH_ml 的 CH_FLASH_PAR；叠加 SNB 覆写。"""
    p: Dict[str, Any] = dict(CH_FLASH_PAR)

    # ① 剔除缺失物种的键
    drop = []
    for k in p:
        kl = k.lower()
        if any(f"_{s}" in kl or kl.endswith(s) for s in _ABSENT):
            drop.append(k)
    for k in drop:
        del p[k]
    p.pop("sim_sampRadius", None)
    p.pop("sim_sampHeight", None)
    p.pop("sim_shldRadius", None)
    # ★ 剔除两类 CH_FLASH_PAR 残留、而本场景 Config **未声明**的键
    #   (FLASH 对未注册参数会报错):
    #     · sim_targetRadius/Height —— 属旧版场景初始化, input_gen 生成的
    #       Config 不声明 (本场景用 sim_targRadius)
    #     · ms_*ZMin —— 生成器把 ZMin 映射为 `sim_zmin<Cap>`, 不声明 ms_*ZMin
    import re as _re
    for k in ("sim_targetRadius", "sim_targetHeight"):
        p.pop(k, None)
    for k in list(p):
        if _re.match(r"ms_\w+ZMin$", k):
            del p[k]
    for k in list(p):
        if k.startswith("plot_var"):
            del p[k]

    # ② SNB 覆写
    p.update(SNB_OVERRIDE)

    # ③ 场景覆写
    p["xmin"], p["xmax"] = XMIN, XMAX
    p["tmax"] = tmax
    p["iProcs"] = IPROCS
    p["rt_mgdNumGroups"] = N_GROUPS
    p["checkpointFileIntervalTime"] = chk_dt
    p["plotFileIntervalTime"] = PLT_DT
    p["basenm"], p["log_file"] = basenm, log_file
    p["run_comment"] = f"SNBOneCH (cham+targ, SNB nonlocal, radiation ON) [{tag}]"
    p["restart"] = False
    p["checkpointFileNumber"] = 0
    p["plotFileNumber"] = 0
    # ★ 不要写 Step 变体: 与 Time 是 OR 双触发, 会导致额外输出
    p.pop("plotFileIntervalStep", None)
    p.pop("checkpointFileIntervalStep", None)

    # ④ 物种 / 材料（2 标记）
    for sp in build_species_defs():
        cap = sp["name"].capitalize()
        p[f"sim_rho{cap}"] = sp["rho"]
        p[f"sim_tele{cap}"] = T_INIT
        p[f"sim_tion{cap}"] = T_INIT
        p[f"sim_trad{cap}"] = T_INIT
        p[f"ms_{sp['name']}A"] = sp["A"]
        p[f"ms_{sp['name']}Z"] = sp["Z"]
        # ★ `ZMin` 的 par 键是 `sim_zmin<Cap>`（input_gen 的 Config 如此声明）,
        #   不是 `ms_*ZMin`。
        if sp.get("ZMin") is not None:
            p[f"sim_zmin{cap}"] = sp["ZMin"]
        p[f"eos_{sp['name']}EosType"] = "eos_tab"
        p[f"eos_{sp['name']}SubType"] = "ionmix4"
        p[f"eos_{sp['name']}TableFile"] = sp["file"]
        p[f"op_{sp['name']}Absorb"] = "op_tabpa"
        p[f"op_{sp['name']}Emiss"] = "op_tabpe"
        p[f"op_{sp['name']}Trans"] = "op_tabro"
        p[f"op_{sp['name']}FileType"] = "ionmix4"
        p[f"op_{sp['name']}FileName"] = sp["file"]
    p["sim_targRadius"] = SOLID_UM * 1e-4     # 固体靶厚度 (cm)

    # ⑤ plot_var 白名单 (≤12 项, 从 1 连续编号)
    for i, v in enumerate(_PLOT_VARS, start=1):
        p[f"plot_var_{i}"] = v

    # ⑥ 格式化
    return _emit(p)


def _fmt(v: Any) -> str:
    if isinstance(v, bool):
        return ".true." if v else ".false."
    if isinstance(v, float):
        return f"{v:.10e}" if (v and (abs(v) < 1e-3 or abs(v) > 1e5)) else f"{v:.10g}"
    if isinstance(v, str):
        return f'"{v}"'
    return str(v)


def _emit(p: Dict[str, Any]) -> str:
    lines = ["# " + "=" * 74,
             "# SNBOneCH —— OneCH_ml 几何/材料 + SNB 非局域热传导 (2 标记: cham+targ)",
             "# 由 SNBOneCH.py 生成; 基线 = tracer/OneCH_ml 的 CH_FLASH_PAR + SNB 覆写",
             "# " + "=" * 74]
    for k in sorted(p):
        lines.append(f"{k:<41}= {_fmt(p[k])}")
    return "\n".join(lines) + "\n"


# ══════════════════════════════════════════════════════════════
# 生成场景输入
# ══════════════════════════════════════════════════════════════
SINGLE_F90 = ("Config", "Makefile", "Simulation_data.F90", "Simulation_init.F90",
              "Simulation_initBlock.F90")


def stage_generate(args) -> int:
    print("\n" + "=" * 78)
    print(" 阶段 generate —— 生成 SNBOneCH 场景输入 (2 标记: cham + targ)")
    print("=" * 78)
    log(f"SNB 核心模块: {SNB}")
    log(f"物理基线: tracer/OneCH_ml (CH_FLASH_PAR)")
    log(f"固体靶: 0 → {SOLID_UM:.2f} µm @ 1.0 g/cm³ CH; 域 [{XMIN}, {XMAX}] cm")

    if not SNB_PKG.is_dir():
        log(f"缺 SNB 覆盖件目录: {SNB_PKG}", "ERROR")
        return 1
    INP.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)

    # ① SNB 的 9 个覆盖 F90（含 radON 驱动变体）
    import gen_scene as G                                   # noqa: PLC0415
    n = 0
    for f in G.SNB_F90:
        src = SNB_PKG / f
        if not src.exists():
            log(f"缺 F90: {src}", "ERROR")
            return 1
        shutil.copyfile(src, INP / f)
        n += 1
    # ★ radON 驱动变体: 作者原版把 call RadTrans 注释了 → 辐射永不推进
    radon = SNB / "variants" / "Driver_evolveFlash_radON.F90"
    if not radon.exists():
        log(f"缺 radON 驱动变体: {radon} (先跑 tools_local/make_variants.py)", "ERROR")
        return 1
    shutil.copyfile(radon, INP / "Driver_evolveFlash.F90")
    log(f"复制 {n} 个 SNB 覆盖 F90 + radON 驱动 ✓", "OK")

    # ② 单元框架 (2 物种) —— 用 input_gen 生成器
    log("生成 Config / Makefile / Simulation_* (2 物种)...", "STEP")
    from flash.input_gen.gen_config import ConfigGenerator
    from flash.input_gen.gen_makefile import MakefileGenerator
    from flash.input_gen.gen_sim_data import SimDataGenerator
    from flash.input_gen.gen_sim_init import SimInitGenerator
    from flash.input_gen.gen_sim_initblock import BlockGenerator, GridBuilder

    defs = build_species_defs()
    sim_path = f"tracer/SNB/{SIM_NAME}"

    # ★★ Config 必须以 **SNB 包自带 Config 为基座**：
    #    该 Config 声明的 REQUESTS（`Conductivity/ConductivityMain/SpitzerHighZ`、
    #    `Heatexchange/HeatexchangeMain/Spitzer`、`Diffuse/DiffuseMain/Unsplit`）
    #    与 **18 个 SNB 诊断 VARIABLE**（QESH/QESX/GRQX/MFPE/NELE/…）是 SNB
    #    覆盖件能否编译的前提；而 `input_gen` 生成的 Config **只有物种参数**、
    #    没有这些声明 → 编译期报一串
    #    "Symbol 'qesh_var' at (1) has no IMPLICIT type"（实测踩过）。
    #    做法：以 SNB Config 为基座 → 替换 `DATAFILES` → **追加**其未声明的物种参数。
    import re as _re2                                          # noqa: PLC0415
    ConfigGenerator().save(str(INP / "Config"), simulation_path=sim_path,
                           species_defs=defs)
    species_cfg = (INP / "Config").read_text(encoding="utf-8", errors="replace")
    base_cfg = (SNB_PKG / "Config").read_text(encoding="utf-8", errors="replace")
    # 基座里的 DATAFILES 指向 V/Ti 等本场景没有的表 → 全部剔除后重列
    base_cfg = "\n".join(ln for ln in base_cfg.splitlines()
                         if not ln.strip().upper().startswith("DATAFILES"))
    decl = set(_re2.findall(r"\bPARAMETER\s+(\w+)", base_cfg))
    add: List[str] = []
    pending: List[str] = []
    for ln in species_cfg.splitlines():
        m = _re2.match(r"\s*PARAMETER\s+(\w+)", ln)
        if m:
            if m.group(1) not in decl:
                add.extend(pending)
                add.append(ln)
                decl.add(m.group(1))
            pending = []
        elif ln.strip().startswith("D "):
            pending.append(ln)
    datafiles = "\n".join(f"DATAFILES {t}" for t in (HE_CN4, CH_CN4))
    (INP / "Config").write_text(
        base_cfg.rstrip("\n") + "\n\n"
        + "# ── 本场景用到的数据表 ──\n" + datafiles + "\n\n"
        + "# ── 本场景物种参数（由 input_gen 生成后追加）──\n"
        + "\n".join(add) + "\n",
        encoding="utf-8", newline="\n")
    log(f"Config 合并完成: SNB 基座 + {len(add)} 行物种参数 + {2} 张表", "OK")

    MakefileGenerator().save(str(INP / "Makefile"), sim_path=sim_path)
    SimDataGenerator().save(str(INP / "Simulation_data.F90"), species=defs)
    SimInitGenerator().save(str(INP / "Simulation_init.F90"),
                            params={"species": defs})

    # ★ Makefile 必须编译 `mgd_qesh.o`（SNB 多群 SH 热流权重）。
    #   生成器产出的 Makefile 不含它 → 链接期缺符号 → make 失败。
    mk = INP / "Makefile"
    txt = mk.read_text(encoding="utf-8", errors="replace")
    if "mgd_qesh.o" not in txt:
        mk.write_text(txt.rstrip("\n") +
                      "\nSimulation += Simulation_data.o mgd_qesh.o\n",
                      encoding="utf-8", newline="\n")
        log("Makefile 补充 mgd_qesh.o ✓", "OK")
    else:
        log("Makefile 已含 mgd_qesh.o ✓", "OK")

    # 几何: 单层固体靶 [0, SOLID_UM]，其余 cham（GridBuilder 未命中兜底）
    builder = GridBuilder(dim=1, geometry="cartesian", domain=(XMIN, XMAX))
    for sp in defs:
        builder.set_material(sp["name"], rho=sp["rho"], tele=T_INIT,
                             tion=T_INIT, trad=T_INIT)
    builder.add_region("targ", species="targ", x_range=(0.0, SOLID_UM * 1e-4),
                       x_expr=("0.0", "sim_targRadius"))
    block_gen = BlockGenerator(simulation_name=SIM_NAME, sim_path=sim_path,
                               species=SPECIES_LIST)
    block_gen.build(builder)
    block_gen.save(str(INP / "Simulation_initBlock.F90"))
    log("单元框架生成完成 (Config/Makefile/Simulation_*/initBlock) ✓", "OK")

    # ③ 表（多级查找: SNB 模块自带 → EOSOpacityGenerator 注册表 → 数据目录递归）
    #    ★ SNB 模块的 source/tables/ 只带 BADGER 族; OneCH_ml 用的
    #      CH-QC-1-001 需从 input_gen 的 eos_op 数据区取。
    def _copy_table(name: str, aliases) -> bool:
        src = TABLES / name
        if src.exists():
            shutil.copyfile(src, INP / name)
            return True
        try:
            from flash.input_gen.gen_eos_op import EOSOpacityGenerator
            EOSOpacityGenerator().copy_eos_file(aliases[0], INP)
            if (INP / name).exists():
                log(f"    {name} ← EOSOpacityGenerator 注册表", "INFO")
                return True
        except Exception as exc:                              # noqa: BLE001
            log(f"    注册表复制失败 ({name}): {exc}", "WARN")
        data_root = _ROOT / "flash" / "input_gen" / "gen_eos_op"
        for cand in data_root.rglob(name):
            shutil.copyfile(cand, INP / name)
            log(f"    {name} ← {cand.relative_to(data_root)}", "INFO")
            return True
        return False

    for _name, _aliases in ((HE_CN4, ("he_badger",)), (CH_CN4, ("ch_qc",))):
        if not _copy_table(_name, _aliases):
            log(f"缺表: {_name}（SNB 模块 / 注册表 / 数据目录均未找到）", "ERROR")
            return 1
    log(f"表复制完成: {HE_CN4}, {CH_CN4} ✓", "OK")

    # ④ par (短时 + 正式)
    (INP / PAR_FILENAME_SMOKE).write_text(
        build_par(TMAX_SMOKE, CHK_DT_SMOKE, BASENM_SMOKE, LOG_FILE_SMOKE, "smoke"),
        encoding="utf-8", newline="\n")
    (INP / PAR_FILENAME).write_text(
        build_par(TMAX_FULL, CHK_DT_FULL, BASENM, LOG_FILE, "full"),
        encoding="utf-8", newline="\n")
    log(f"par: {PAR_FILENAME} (tmax={TMAX_FULL:.1e}), "
        f"{PAR_FILENAME_SMOKE} (tmax={TMAX_SMOKE:.1e}) ✓", "OK")

    # ⑤ ★ 硬校验: 承重键必须落在生成的 par 里
    kv = _par_kv(INP / PAR_FILENAME)
    hard = {
        "gr_hypreUseFloor": ".false.",
        "diff_eleFlMode": f'"{P.CONDUCTION["diff_eleFlMode"]}"',
        "dtmax": _fmt(DTMAX),
        "rt_useMGD": ".true.", "useOpacity": ".true.", "useRadTrans": ".true.",
    }
    bad = [k for k, v in hard.items() if kv.get(k) != v]
    if bad:
        log(f"★ 承重键校验**失败**: {[(k, kv.get(k)) for k in bad]}", "ERROR")
        return 1
    log(f"承重键校验通过 ✓ ({', '.join(hard)})", "OK")

    # ⑥ 键集自检: 不得残留 Config 未声明的材料类键
    undecl = _undeclared_material_keys(INP / PAR_FILENAME, INP / "Config")
    if undecl:
        log(f"★ par 含未在 Config 声明的材料类键: {undecl} → 拒绝使用", "ERROR")
        return 1
    log("材料类键集自检通过 ✓ (无未声明键)", "OK")

    log(f"文件数: {len(list(INP.iterdir()))}", "OK")
    return 0


def _par_kv(p: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        s = ln.split("#", 1)[0].strip()
        if s and "=" in s:
            k, v = s.split("=", 1)
            out[k.strip()] = v.strip()
    return out


# 这些前缀键属**其它 FLASH 单元的 Config**（EOS / RadTrans），
# 不在场景自带的 Config 中声明，属正常。
_UNIT_WHITELIST = {"eos_useLogTables", "eos_maxNewton", "op_tableEnergyTolerance"}


def _undeclared_material_keys(par: Path, config: Path) -> List[str]:
    """★ 键集自检：par 中 `sim_/ms_/eos_/op_` 前缀的键必须在 Config 中声明。

    动机：par 基线取自 `CH_FLASH_PAR`（为 8 标记场景而设），直接搬到 2 标记
    场景会残留**未注册**的键（如 `sim_targetRadius`、`ms_targZMin`），
    FLASH 会因未注册参数报错。此项检查把这类错误拦在编译之前。
    """
    import re as _re
    decl = set()
    for ln in config.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _re.match(r"\s*PARAMETER\s+(\w+)", ln)
        if m:
            decl.add(m.group(1))
    return sorted(k for k in _par_kv(par)
                  if k.startswith(("sim_", "ms_", "eos_", "op_"))
                  and k not in decl and k not in _UNIT_WHITELIST)


# ══════════════════════════════════════════════════════════════
def _run(par: str, tag: str) -> int:
    """复用 SNB 核心模块的运行驱动（部署/setup/make/运行/收集/健康检查）。"""
    import subprocess                                      # noqa: PLC0415
    cmd = [PY, RUN_SCENE, "--scene", SCENE, "--side", "snb",
           "--par", par, "--tag", tag,
           "--nxb", NXB, "--iprocs", IPROCS,
           "--species", ",".join(SPECIES_LIST),
           "--tables", f"{HE_CN4},{CH_CN4}",
           "--pulse-sections", "300",
           "--out-root", SCENE / "flash_output"]
    print(f"\n{'='*78}\n $ {' '.join(str(c) for c in cmd)}\n{'='*78}", flush=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    with (LOGS / f"run_{tag}.log").open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(f"\n### {' '.join(str(c) for c in cmd)}\n")
    return subprocess.run([str(c) for c in cmd]).returncode


def stage_smoke(args) -> int:
    print("\n" + "=" * 78)
    print(f" 阶段 smoke —— 短时验证 (tmax={TMAX_SMOKE:.1e} s, chk={CHK_DT_SMOKE:.0e})")
    print(" ★ 规范: 新场景首跑必须短时验证, 通过后再跑正式时间")
    print("=" * 78)
    rc = stage_generate(args)
    if rc:
        return rc
    t0 = time.time()
    rc = _run(PAR_FILENAME_SMOKE, "smoke")
    log(f"smoke 结束 rc={rc}, 耗时 {time.time()-t0:.1f} s",
        "OK" if rc == 0 else "ERROR")
    return rc


def stage_full(args) -> int:
    print("\n" + "=" * 78)
    print(f" 阶段 full —— 正式运行 (tmax={TMAX_FULL:.1e} s, dtmax={DTMAX:.1e})")
    print("=" * 78)
    rc = stage_generate(args)
    if rc:
        return rc
    t0 = time.time()
    rc = _run(PAR_FILENAME, "full")
    log(f"full 结束 rc={rc}, 耗时 {time.time()-t0:.1f} s",
        "OK" if rc == 0 else "ERROR")
    return rc


def stage_check(args) -> int:
    import subprocess                                      # noqa: PLC0415
    print("\n" + "=" * 78)
    print(" 阶段 check —— chk 健康检查 (dt 钳位 / ρmax / 守恒)")
    print("=" * 78)
    rc = 0
    for tag in ("smoke", "full"):
        d = FO / tag
        if not d.is_dir():
            log(f"{tag}: 目录不存在, 跳过", "WARN")
            continue
        print(f"\n── {tag} ──")
        rc |= subprocess.run([PY, PROBE, "--dir", str(d),
                              "--expect-dtmax", f"{DTMAX:.6e}", "--brief"]).returncode
    return rc


def stage_plot(args) -> int:
    import subprocess                                      # noqa: PLC0415
    plot = _HERE / "plot_compare_onech.py"
    if not plot.exists():
        log(f"缺绘图脚本: {plot}", "ERROR")
        return 1
    cmd = [PY, plot, "--snb-scene", SCENE, "--out", IMAGES]
    print(f"\n{'='*78}\n $ {' '.join(str(c) for c in cmd)}\n{'='*78}", flush=True)
    return subprocess.run([str(c) for c in cmd]).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="SNBOneCH (cham+targ, SNB, 辐射开)")
    ap.add_argument("--stage",
                    choices=["all", "generate", "smoke", "full", "check", "plot"],
                    default="generate")
    args = ap.parse_args()

    print("\n" + "=" * 78)
    print(" SNBOneCH —— OneCH_ml 几何/材料 + SNB 非局域热传导 (2 标记)")
    print(f" 域 [{XMIN}, {XMAX}] cm; 固体靶 0→{SOLID_UM:.2f} µm CH 1.0; 腔 He 1e-6")
    print(f" 网格 +ug: iProcs={IPROCS} × nxb={NXB} = {IPROCS*NXB} 格, "
          f"dx≈{(XMAX-XMIN)/(IPROCS*NXB)*1e4:.4f} µm")
    print(f" SNB: 辐射**开**, diff_eleFlMode={P.CONDUCTION['diff_eleFlMode']}, "
          f"gr_hypreUseFloor=.false., dtmax={DTMAX:.1e}")
    print("=" * 78)

    t0 = time.time()
    rc = 0
    if args.stage == "generate":
        rc = stage_generate(args)
    elif args.stage in ("all", "smoke"):
        rc = stage_smoke(args)
        if args.stage == "all" and rc == 0:
            rc |= stage_check(args)
    elif args.stage == "full":
        rc = stage_full(args)
    elif args.stage == "check":
        rc = stage_check(args)
    elif args.stage == "plot":
        rc = stage_plot(args)

    print("\n" + "=" * 78)
    print(f" SNBOneCH 完成 — 耗时 {time.time()-t0:.1f} s, rc={rc}")
    print(f" 场景: {SCENE}")
    print("=" * 78)
    return rc


if __name__ == "__main__":
    sys.exit(main())
