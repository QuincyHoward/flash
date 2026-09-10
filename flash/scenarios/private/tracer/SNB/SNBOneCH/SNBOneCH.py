"""
SNBOneCH 场景 — 最小两区 SNB 场景, +ug 均匀网格分辨率研究
═══════════════════════════════════════════════════════════════════

★ 铁律 (2026-09-08 用户明确): **SNB 模式必须使用 +ug 均匀网格**。
  SNB 非局域热传导 (Schurtz–Nicolaï–Busquet) 的群分辨热流沿平均自由程
  跨多格点积分, AMR 粗细界面是天然破缺点; SNB_1D_laser 参考单元与全部
  t001 验证均在 +ug 下完成。SNBOneCH_ml 曾用 AMR (lrefine9) 运行并出现
  启动瞬态失稳 — 本场景即为此对照: 同一 He|CH 界面, 强制 +ug。

由 SNBOneCH_ml 简化派生 (2026-09-08):
  * 只用两种材料: x < 0 为 cham (氦 He, 1e-6 g/cm^3),
                  x > 0 为 targ (CH,  1.0 g/cm^3), 界面 x = 0。
  * 只用两个物种标记: cham, targ (初始 species 由 x<0/>0 决定)。
  * 几何无薄层 → +ug 均匀网格精度可适当降低, 用于**测试网格精度的影响**。

+ug 网格特性 (t001 实测): 只建 iProcs 块 level-1 网格, par 的
nblockx/lrefine 被无视, 网格间距 dx = 域宽/(iProcs·nxb)。
域 [-0.04, 0.01] cm (宽 0.05 cm), nxb=8 (t001 基线):

    iProcs =  4  →  dx = 15.6 um
    iProcs =  8  →  dx =  7.8 um   (默认, 接近 t001 的 9.4 um)
    iProcs = 16  →  dx =  3.9 um
    iProcs = 32  →  dx =  2.0 um
    iProcs = 64  →  dx =  0.98 um

分辨率扫描 (--sweep 8,16,32,64): 二进制只编译一次, 各档仅改 par 的
iProcs + mpiexec -n, 输出收集到 flash_output/sweep_ip<N>/。

**必须在 SNB 专用 FLASH 代码 (FLASHSNB) 中编译运行** — 与 SNBOneCH_ml
相同的 9 个单元覆盖文件 (8 个随场景 flash_input 归档 + mgd_qesh.F90
部署时从 FLASHSNB SNB_1D_laser 单元复制) 与 2 个树级 physics 补丁。

材料表 (t001 +ug 验证基线, 均为 BADGER 族 10 群):
  cham → He-BADGER-TOPS-Final.cn4
  targ → CH-BADGER-TOPS-Final.cn4
运行控制 (t001 +ug 验证基线): tstep_change_factor=1.10, cfl=0.2,
dtmax=2.0e-12, 初始温度 290.11375 K (室温)。

用法:
    python SNBOneCH.py --generate-only          # 只生成输入文件
    python SNBOneCH.py --tmax 1.0e-10           # 默认 iprocs=8 单跑
    python SNBOneCH.py --sweep 8,16,32,64 --tmax 1.0e-10   # 分辨率扫描
    python SNBOneCH.py --skip-setup --skip-make # 复用已有 objdir/flash4
"""

import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── 仓库根定位 (pyproject.toml 锚点, 与 SNBOneCH_ml 同模式) ──
_ROOT = Path(__file__).resolve().parent
for _ in range(15):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ── 可配置参数 ────────────────────────────────────────────
config_constants = {
    # 仿真域 (cm), 同 SNBOneCH_ml / OneCH_ml 家族
    "xmin": -0.04,
    "xmax": 0.01,
    # 仿真结束时间 (s)。首跑验证规范: --tmax 1.0e-11; 分辨率研究: 1.0e-10
    "tmax": 1.0e-10,
    # +ug 均匀网格: 块数 = iProcs (par nblockx/lrefine 被无视)
    # dx = (xmax-xmin)/(iProcs*nxb); nxb=8 (t001 基线)
    "nxb": 8,
    "iprocs": 8,          # 默认 8 块 → dx ≈ 7.8 um (接近 t001 的 9.4 um)
    # 输出频率: 时间触发 (1e-11 s ≈ 每档 10 帧, 便于跨档对比)
    "plot_interval_time": 1.0e-11,
    "checkpoint_interval_step": 400,
    # 维度
    "dimension": 1,
    # SNB 热传导基线参数 (t001 flash.par — +ug 验证基线)
    "diff_eleFlMode": "fl_harmonic",
    "diff_eleFlCoef": 0.06,
    "cfl": 0.2,
    "tstep_change_factor": 1.10,   # t001 +ug 基线 (ml 场景的 1.05 为 AMR 细网格所需)
    "dtmax": 2.0e-12,              # t001 +ug 基线 (ml 场景的 2e-14 为 AMR 细网格所需)
    # 初始温度 [K] (全物种统一, 室温基线)
    "t_initial": 290.11375,
    # 材料表 (t001 +ug 验证基线; 两表均 BADGER 族 10 群, 温度下限 0.01 eV 覆盖室温)
    "he_cn4": "He-BADGER-TOPS-Final.cn4",
    "ch_cn4": "CH-BADGER-TOPS-Final.cn4",
    # 材料 (ρ g/cm^3; 界面 x=0: x<0 cham 氦气, x>0 targ CH 固体)
    "rho_cham": 1.0e-6,
    "rho_targ": 1.0,
}

# FLASH setup 标志 (FLASHSNB; ★ +ug 强制均匀网格 — SNB 铁律; t001 基线)
SETUP_FLAGS = (
    "-1d +cartesian +ug -nxb=8 +hdf5typeio "
    "species=cham,targ "
    "+mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 "
    "ed_maxPulseSections=300"
)

# 仿真/对象/par 命名
SIM_NAME = "SNBOneCH"             # FLASHSNB 内 SimulationMain 单元名
OBJDIR = "SNBOneCH_obj"           # setup -objdir=
PAR_FILENAME = "snbonech.par"
BASENM = "snbonech_"              # 输出基名: snbonech_hdf5_plt_cnt_* 等
LOG_FILE = "snbonech.log"

# 物种列表 (顺序即 FLASH 物种常量顺序)
SPECIES_LIST = ["cham", "targ"]

# ── SNB 单元覆盖文件 (与 SNBOneCH_ml 相同; 9 个全部随场景归档, ──
# ── 权威来源 = WSL FLASHSNB SNB_1D_laser 工作副本 (含 6 补丁修复);
# ── 注意 src/SNB_1D_laser 原始包源未打补丁, 不可直接复制使用) ──
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
# 全部 9 个本地归档 (2026-09-08 修正: 从 WSL 工作树同步, 含 mgd_qesh)
_LOCAL_OVERRIDE_FILES = SNB_OVERRIDE_FILES

# FLASHSNB 树级 physics 补丁 (t001 修复; 部署时缺失则从 t001 归档补齐)
_TREE_PATCHES = (
    "physics/Diffuse/DiffuseMain/Diffuse_computeDt.F90",
    "physics/Hydro/HydroMain/unsplit/hy_uhd_getFaceFlux.F90",
)
# 本地参考: SNBOneCH_ml flash_input (覆盖文件已归档) 与 t001 归档
# 路径: private/tracer/SNB/SNBOneCH → parent.parent = private/tracer/SNB
_ML_INPUT = Path(__file__).resolve().parent.parent / "SNBOneCH_ml" / "flash_input"
_SRC_UNIT = Path(__file__).resolve().parent.parent / (
    "SNBtest/src/SNB/SNB_1D_laser/SNB_1D_laser")
_T001_DIR = Path(__file__).resolve().parent.parent / "SNBtest/Test/t001"

# SNB Config 追加段: 18 个 SNB 诊断 VARIABLE (取自 SNB_1D_laser Config)
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

# plot_var 白名单: 基础量 + 2 物种 + SNB 诊断 (QENL=非局域热流, QESH=SH 热流)
_PLOT_VARS = ["dens", "depo", "tele", "tion", "trad", "ye", "sumy",
              "cham", "targ", "fllm",
              "QESH", "QESX", "QESY", "GRQX", "GRAQ", "CORQ", "MFPE", "QENL"]

# 输出文件 glob (FLASH hdf5typeio 无 .h5 后缀)
OUTPUT_GLOBS = ("snbonech*",)

# 场景目录
SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_DIR = SCRIPT_DIR / "flash_input"
OUTPUT_DIR = SCRIPT_DIR / "flash_output"


def log(msg: str, level: str = "INFO"):
    tag = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]", "STEP": "[-]"}.get(level, "[i]")
    print(f"  {tag} {msg}")


def _dx_um(iprocs: int, cfg: Dict[str, Any]) -> float:
    """+ug 均匀网格间距 [um]: 域宽/(iProcs·nxb)。"""
    return (cfg["xmax"] - cfg["xmin"]) / (iprocs * cfg["nxb"]) * 1e4


# ── 步骤 1: 生成 FLASHSNB 输入文件 ─────────────────────────
def _build_par_text(cfg: Dict[str, Any], iprocs: int) -> str:
    """构建 .par 文件内容 (CH_FLASH_PAR 基线 + SNB/t001 +ug 覆写)。"""
    from flash.input_gen.gen_par import ParGeneratorExtended
    from flash.scenarios.private.tracer._par_layers import CH_FLASH_PAR

    tmp_params = dict(CH_FLASH_PAR)
    # 剔除 shld/samp 物种键与未用几何键 (精确前缀/键名, 不能模糊匹配
    # "targ" — 会误删激光 ed_targetX_1)。targ 键全部保留 (targ=CH 材料)。
    _DEL_PREFIXES = (
        "eos_shld", "op_shld", "ms_shld",
        "eos_samp", "op_samp", "ms_samp",
        "sim_rhoShld", "sim_teleShld", "sim_tionShld", "sim_tradShld",
        "sim_rhoSamp", "sim_teleSamp", "sim_tionSamp", "sim_tradSamp",
        "plot_var", "refine_var", "refine_cutoff", "deref_cutoff",
    )
    _DEL_KEYS = {
        "basenm", "log_file",
        "sim_shldRadius", "sim_sampRadius", "sim_targetRadius",
        "sim_targetHeight", "sim_sampHeight",
    }
    for k in list(tmp_params):
        if k.startswith(_DEL_PREFIXES) or k in _DEL_KEYS:
            del tmp_params[k]

    par_gen = ParGeneratorExtended(simulation_name=SIM_NAME, dimension=1)
    par_gen._params.clear()
    for k, v in tmp_params.items():
        par_gen.set(k, v)
    # targ = CH 材料 (CH_FLASH_PAR 模板 targ 默认即 CH, A=6.509 Z=3.5;
    # 表换为 CH-BADGER — t001 +ug 验证基线, 覆盖室温温度网格)
    par_gen.set("sim_rhoTarg", cfg["rho_targ"])
    par_gen.set("eos_targTableFile", cfg["ch_cn4"])
    par_gen.set("op_targFileName", cfg["ch_cn4"])
    # cham = He (模板默认即 He-BADGER; 显式重申)
    par_gen.set("sim_rhoCham", cfg["rho_cham"])
    par_gen.set("eos_chamTableFile", cfg["he_cn4"])
    par_gen.set("op_chamFileName", cfg["he_cn4"])
    # 初始温度覆写 (运行时真正生效的是 par 的 sim_tele*/tion*/trad*)
    for _zone in ("Cham", "Targ"):
        par_gen.set(f"sim_tele{_zone}", cfg["t_initial"])
        par_gen.set(f"sim_tion{_zone}", cfg["t_initial"])
        par_gen.set(f"sim_trad{_zone}", cfg["t_initial"])
    # 网格: +ug 均匀网格 — 网格由 iProcs·nxb 决定, nblockx/lrefine 被
    # 无视 (t001 实测); 保留占位并置 1 以免 lrefine_min_init>lrefine_max
    par_gen.set("nblockx", iprocs)
    par_gen.set("lrefine_max", 1)
    par_gen.set("lrefine_min", 1)
    par_gen.set("lrefine_min_init", 1)
    # 运行控制
    par_gen.set("tmax", cfg["tmax"])
    par_gen.set("plotFileIntervalTime", cfg["plot_interval_time"])
    par_gen.set("checkpointFileIntervalStep", cfg["checkpoint_interval_step"])
    par_gen.set("basenm", BASENM)
    par_gen.set("log_file", LOG_FILE)
    # SNB 热传导基线 (t001 flash.par — SNB 使用方法)
    par_gen.set("useDIffuseTherm", True)     # Diffuse 单元热传导开关 (SNB 必需)
    par_gen.set("diff_eleFlMode", cfg["diff_eleFlMode"])   # fl_harmonic
    par_gen.set("diff_eleFlCoef", cfg["diff_eleFlCoef"])   # 0.06
    par_gen.set("cfl", cfg["cfl"])                          # 0.2 (t001 基线)
    par_gen.set("use_3dFullCTU", True)       # t001 SNB 基线
    par_gen.set("eos_maxNewton", 5000)       # t001 SNB 基线
    par_gen.set("tstep_change_factor", cfg["tstep_change_factor"])  # 1.10
    par_gen.set("dtmax", cfg["dtmax"])                      # 2.0e-12
    # 进程分解 (+ug: 块数 = iProcs; 必须与 mpiexec -n 一致)
    par_gen.set("iProcs", iprocs)
    # plotfile 输出变量白名单 (基础量 + SNB 诊断)
    for i, v in enumerate(_PLOT_VARS, start=1):
        par_gen.set(f"plot_var_{i}", f"{v:<4s}")
    return par_gen.generate()


def generate_input_files(cfg: Dict[str, Any]) -> Dict[str, str]:
    """生成全部 FLASHSNB 输入文件到 flash_input/。

    产物: snbonech.par / Config / Makefile / Simulation_data.F90 /
    Simulation_init.F90 / Simulation_initBlock.F90 / 2 张 .cn4 表 /
    run_flash.sh / 预诊断图。8 个 SNB 覆盖 F90 从 SNBOneCH_ml/flash_input
    归档复制 (权威来源 = WSL 工作树副本, 含 QENL 续行符/slopeLimiters
    模块名修复; 缺失时回落 WSL SNB_1D_laser 参考单元)。
    """
    from flash.input_gen.gen_config import ConfigGenerator
    from flash.input_gen.gen_sim_data import SimDataGenerator
    from flash.input_gen.gen_sim_init import SimInitGenerator
    from flash.input_gen.gen_sim_initblock import BlockGenerator, GridBuilder

    sim_path = SIM_NAME          # FLASHSNB 内单元: SimulationMain/SNBOneCH
    iprocs = cfg["iprocs"]

    # 物种定义 (cham=He, targ=CH; 无 radius/height 运行时参数 —
    # 几何固定为 x<0 cham / x>0 targ, 界面 x=0 写死在 initBlock)
    species_defs = [
        {"name": "cham", "file": cfg["he_cn4"], "rho": cfg["rho_cham"],
         "A": 4.002602, "Z": 2.0},
        {"name": "targ", "file": cfg["ch_cn4"], "rho": cfg["rho_targ"],
         "A": 6.509, "Z": 3.5},
    ]

    result: Dict[str, str] = {}
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. par (CH_FLASH_PAR 基线 + t001 +ug 覆写) ──────────
    log("  [1/8] 生成 .par 文件 (t001 +ug 基线)...", "STEP")
    par_text = _build_par_text(cfg, iprocs)
    par_path = INPUT_DIR / PAR_FILENAME
    par_path.write_text(par_text, encoding="utf-8", newline="\n")
    result["par"] = str(par_path)
    log(f"    .par → {par_path.name} ✓ (iProcs={iprocs}, "
        f"dx≈{_dx_um(iprocs, cfg):.2f} um)")

    # ── 2. Config (2 物种注册 + 18 个 SNB VARIABLE) ─────────
    log("  [2/8] 生成 Config (2 species + SNB variables)...", "STEP")
    cfg_path = ConfigGenerator().save(
        str(INPUT_DIR / "Config"), simulation_path=sim_path, species_defs=species_defs,
    )
    txt = cfg_path.read_text(encoding="utf-8", newline="\n")
    cfg_path.write_text(txt.rstrip("\n") + "\n" + SNB_CONFIG_VARIABLES,
                        encoding="utf-8", newline="\n")
    result["config"] = str(cfg_path)
    log(f"    Config ✓ (+{SNB_CONFIG_VARIABLES.count('VARIABLE')} SNB variables)")

    # ── 3. Makefile (Simulation 单元: Simulation_data + mgd_qesh) ──
    log("  [3/8] 生成 Makefile...", "STEP")
    mk_path = INPUT_DIR / "Makefile"
    mk_path.write_text(
        "# SNBOneCH Simulation unit makefile (SNB model)\n"
        "# mgd_qesh.o: SNB 多群 SH 热流权重 (FLASHSNB 专用, 无同名 physics 文件)\n"
        "Simulation += Simulation_data.o mgd_qesh.o\n",
        encoding="utf-8", newline="\n")
    result["makefile"] = str(mk_path)

    # ── 4. Simulation_data.F90 ────────────────────────────
    log("  [4/8] 生成 Simulation_data.F90...", "STEP")
    SimDataGenerator().save(str(INPUT_DIR / "Simulation_data.F90"), species=species_defs)
    result["sim_data"] = str(INPUT_DIR / "Simulation_data.F90")

    # ── 5. Simulation_init.F90 ────────────────────────────
    log("  [5/8] 生成 Simulation_init.F90...", "STEP")
    SimInitGenerator().save(str(INPUT_DIR / "Simulation_init.F90"), params={"species": species_defs})
    result["sim_init"] = str(INPUT_DIR / "Simulation_init.F90")

    # ── 6. Simulation_initBlock.F90 (2 物种, x<0 cham / x>0 targ) ──
    log("  [6/8] 生成 Simulation_initBlock.F90 (2 species, 1 region)...", "STEP")
    builder = GridBuilder(dim=1, geometry="cartesian", domain=(cfg["xmin"], cfg["xmax"]))
    for sp in species_defs:
        builder.set_material(sp["name"], rho=sp["rho"], tele=cfg["t_initial"],
                             tion=cfg["t_initial"], trad=cfg["t_initial"])
    # targ 区: x ∈ [0, xmax] (数值边界 — 界面 x=0 为场景固定几何);
    # 默认 (未命中) 物种 = cham → x < 0 全为氦气。
    builder.add_region("targ_main", species="targ",
                       x_range=(0.0, cfg["xmax"]))
    block_gen = BlockGenerator(
        simulation_name=SIM_NAME, sim_path=sim_path, species=SPECIES_LIST,
    )
    block_gen.build(builder)
    block_path = block_gen.save(str(INPUT_DIR / "Simulation_initBlock.F90"))
    result["sim_initblock"] = str(block_path)
    log(f"    Simulation_initBlock.F90 ({len(builder.regions)} region) ✓")

    # ── 7. SNB 覆盖 F90 归档 (从 SNBOneCH_ml/flash_input 复制) ──
    log("  [7/8] 归档 SNB 覆盖 F90 + 复制 EOS/opacity 表...", "STEP")
    for f in _LOCAL_OVERRIDE_FILES:
        src = _ML_INPUT / f
        if not src.exists():
            src = _SRC_UNIT / f
        if src.exists():
            shutil.copyfile(src, INPUT_DIR / f)
        else:
            log(f"    {f} 本地无归档 (部署时将从 WSL 参考单元复制)", "WARN")
    log(f"    {len(_LOCAL_OVERRIDE_FILES)} 覆盖 F90 ✓ (WSL 工作树权威版本)")

    from flash.input_gen.gen_eos_op import EOSOpacityGenerator

    def _copy_cn4(filename: str, aliases) -> bool:
        dst = EOSOpacityGenerator().copy_eos_file(aliases[0], INPUT_DIR)
        if dst is not None and Path(dst).exists():
            return True
        data_root = _ROOT / "flash" / "input_gen" / "gen_eos_op" / "eos_op_data"
        for cand in data_root.rglob(filename):
            shutil.copyfile(cand, INPUT_DIR / filename)
            log(f"    {filename} ← {cand.relative_to(data_root)}", "INFO")
            return True
        if _ML_INPUT.exists() and (_ML_INPUT / filename).exists():
            shutil.copyfile(_ML_INPUT / filename, INPUT_DIR / filename)
            log(f"    {filename} ← SNBOneCH_ml/flash_input", "INFO")
            return True
        log(f"    {filename} 缺失 (注册表/数据目录/场景归档均未找到)", "ERROR")
        return False

    ok_all = True
    for filename, aliases in (
        ("He-BADGER-TOPS-Final.cn4", ("he_badger",)),
        ("CH-BADGER-TOPS-Final.cn4", ("ch_badger",)),
    ):
        if not _copy_cn4(filename, aliases):
            ok_all = False
    if not ok_all:
        log("EOS/opacity 表不齐全, 终止 (FLASH 将因缺表 abort)", "ERROR")
        return result

    # ── 8. run_flash.sh (WSL 手动一键) + 预诊断图 ─────────
    log("  [8/8] 生成 run_flash.sh + 预诊断图...", "STEP")
    _write_run_flash_sh(cfg, iprocs)
    result["script_wsl"] = str(INPUT_DIR / "run_flash.sh")
    log("    run_flash.sh ✓")

    try:
        import numpy as np
        from flash.input_gen.gen_checker.ploter import PulsePlotter, DensityPlotter
        from flash.scenarios.private.tracer._par_layers import CH_FLASH_PAR
        # 激光脉冲 82 段来自 CH_FLASH_PAR 模板 (ed_* 键在 par 中未被删除)
        tsec = sorted((int(k.rsplit("_", 1)[1]), v)
                      for k, v in CH_FLASH_PAR.items() if k.startswith("ed_time_1_"))
        psec = sorted((int(k.rsplit("_", 1)[1]), v)
                      for k, v in CH_FLASH_PAR.items() if k.startswith("ed_power_1_"))
        if tsec and psec:
            times_ns = np.array([v for _, v in tsec]) * 1e9
            powers_w = np.array([v for _, v in psec])
            PulsePlotter().plot_pulse(
                times_ns, powers_w,
                title=f"Laser Pulse ({len(tsec)} sections)",
                save_path=INPUT_DIR / "pre_diag_laser_pulse.png",
                beam_label="Beam 1 (0.351 um)")
            log(f"    pre_diag_laser_pulse.png ✓ ({len(tsec)} sections)")
            result["pre_diag_laser"] = str(INPUT_DIR / "pre_diag_laser_pulse.png")
        xs, dens1d, _ = builder.sample_1d(n_points=4000)
        DensityPlotter().plot_1d(
            xs, dens1d, region_boundaries=[("targ (CH)", 0.0)],
            title="Initial Density (SNBOneCH: He|CH interface at x=0)",
            save_path=INPUT_DIR / "pre_diag_initial_density.png")
        log("    pre_diag_initial_density.png ✓")
        result["pre_diag_density"] = str(INPUT_DIR / "pre_diag_initial_density.png")
    except Exception as exc:  # noqa: BLE001
        log(f"预诊断图生成失败 (不影响仿真): {exc}", "WARN")

    log(f"  输入文件总数: {len(result)}", "OK")
    return result


def _write_run_flash_sh(cfg: Dict[str, Any], iprocs: int) -> None:
    """生成 run_flash.sh — WSL 手动一键流水线 (部署→setup→make→运行→收集)。

    与 py 驱动 deploy_and_run() 同逻辑; 环境变量开关:
    SKIP_SETUP / SKIP_MAKE / SKIP_DEPLOY / TMAX / NPROC。
    强制 LF 换行 (WSL bash 不接受 CRLF)。
    """
    setup_cmd = f"./setup -auto {SIM_NAME} {SETUP_FLAGS} -objdir={OBJDIR}"
    overrides = " ".join(_LOCAL_OVERRIDE_FILES)
    sh = f"""#!/usr/bin/env bash
# SNBOneCH one-click pipeline (FLASHSNB, WSL) — generated by SNBOneCH.py
# Env switches: SKIP_SETUP=1 SKIP_MAKE=1 SKIP_DEPLOY=1 TMAX=1.0e-10 NPROC={iprocs}
set -u
SNB_HOME="${{SNB_HOME:-$(find "$HOME" -maxdepth 3 -type d -name FLASHSNB 2>/dev/null | head -1)/FLASH4.8}}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OBJ="$SNB_HOME/{OBJDIR}"
UNIT="$SNB_HOME/source/Simulation/SimulationMain/{SIM_NAME}"
REF_UNIT="$SNB_HOME/source/Simulation/SimulationMain/SNB_1D_laser"
NPROC="${{NPROC:-{iprocs}}}"
echo "== SNBOneCH pipeline (FLASHSNB: $SNB_HOME, +ug NPROC=$NPROC) =="

# 0) tree-level physics patches (t001 fixes; idempotent)
if [ -z "${{SKIP_DEPLOY:-}}" ]; then
  T001="$SCRIPT_DIR/../../../SNBtest/Test/t001/source_patches"
  for rel in physics/Diffuse/DiffuseMain/Diffuse_computeDt.F90 \
             physics/Hydro/HydroMain/unsplit/hy_uhd_getFaceFlux.F90; do
    if [ ! -f "$SNB_HOME/source/$rel" ] && [ -f "$T001/$rel" ]; then
      mkdir -p "$SNB_HOME/source/$(dirname "$rel")"
      cp -f "$T001/$rel" "$SNB_HOME/source/$rel"
      echo "  patch synced: $rel"
    fi
  done

  # 1) deploy unit: generated files + SNB override files
  #    (8 个本地归档优先; mgd_qesh.F90 从 SNB_1D_laser 参考单元复制)
  mkdir -p "$UNIT"
  cp -f "$SCRIPT_DIR"/Config "$SCRIPT_DIR"/Makefile \\
        "$SCRIPT_DIR"/Simulation_data.F90 "$SCRIPT_DIR"/Simulation_init.F90 \\
        "$SCRIPT_DIR"/Simulation_initBlock.F90 "$SCRIPT_DIR"/*.cn4 "$UNIT"/ || exit 1
  for f in {overrides}; do
    if [ -f "$SCRIPT_DIR/$f" ]; then cp -f "$SCRIPT_DIR/$f" "$UNIT/$f" || exit 1;
    else cp -f "$REF_UNIT/$f" "$UNIT/$f" || exit 1; fi
  done
  cp -f "$REF_UNIT/mgd_qesh.F90" "$UNIT/mgd_qesh.F90" || exit 1
  echo "  unit deployed: $UNIT"
fi

# 2) setup (+ug 强制均匀网格 — SNB 铁律)
if [ -z "${{SKIP_SETUP:-}}" ]; then
  cd "$SNB_HOME" && rm -rf "$OBJ"
  {setup_cmd} || exit 1
  cd "$OBJ" && ln -sf ../source/Simulation/SimulationMain/{SIM_NAME}/mgd_qesh.F90 mgd_qesh.F90 2>/dev/null
  echo "  setup done"
fi
[ -d "$OBJ" ] || {{ echo "objdir missing, run setup first"; exit 1; }}

# 3) make (race fix: pre-build key modules)
if [ -z "${{SKIP_MAKE:-}}" ]; then
  cd "$OBJ"
  make hy_slopeLimiters.o Conductivity_interface.o Conductivity_fullState.o 2>&1 | tail -3
  make -j4 2>&1 | tail -20 || exit 1
  [ -x flash4 ] || {{ echo "flash4 not built"; exit 1; }}
  echo "  build done"
fi

# 4) run
cp -f "$SCRIPT_DIR/{PAR_FILENAME}" "$OBJ/flash.par"
if [ -n "${{TMAX:-}}" ]; then
  sed -i "s/^tmax.*/tmax           = $TMAX/" "$OBJ/flash.par"
fi
cd "$OBJ" && rm -f {BASENM}* wsl_run_snbonech.log
mpiexec -n "$NPROC" ./flash4 > wsl_run_snbonech.log 2>&1
echo "RUN_EXIT=$?" | tee -a wsl_run_snbonech.log
tail -3 wsl_run_snbonech.log

# 5) collect
COLLECT="${{FLASH_COLLECT_DIR:-$SCRIPT_DIR/outputfiles}}"
mkdir -p "$COLLECT"
cp -f "$OBJ"/{BASENM}* "$OBJ"/wsl_run_snbonech.log "$OBJ"/{LOG_FILE} "$COLLECT"/ 2>/dev/null
rm -f "$OBJ"/{BASENM}*
echo "  collected to $COLLECT"
echo "== pipeline done =="
"""
    (INPUT_DIR / "run_flash.sh").write_text(sh, encoding="utf-8", newline="\n")


# ── WSL 执行助手 (SNBOneCH_ml 同模式) ──────────────────────
def run_wsl(cmd: str, distro: str, timeout: int = 7200) -> Tuple[int, str]:
    """在 WSL 中执行命令, 返回 (exit_code, 输出)。"""
    log(f"执行: {cmd[:150]}{'...' if len(cmd) > 150 else ''}")
    try:
        p = subprocess.run(
            ["wsl", "-d", distro, "bash", "-lc", cmd],
            capture_output=True, text=True, timeout=timeout,
        )
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"[timeout after {timeout}s]"


def wsl_path(win_path: Path) -> str:
    """Windows 绝对路径 -> WSL /mnt/... 路径。"""
    drive = win_path.drive.lower().rstrip(":")
    rest = win_path.as_posix().split(":", 1)[1] if ":" in win_path.as_posix() else win_path.as_posix()
    return f"/mnt/{drive}/{rest.lstrip('/')}"


def find_snb_home(distro: str) -> Optional[str]:
    """在 WSL $HOME 下探测 SNB 专用 FLASH 根目录 (FLASHSNB/FLASH4.8)。"""
    code, out = run_wsl(
        'find "$HOME" -maxdepth 3 -type d -name FLASHSNB 2>/dev/null | head -1',
        distro, timeout=60)
    p = out.strip()
    if not p:
        return None
    code2, out2 = run_wsl(
        f'ls -d "{p}/FLASH4.8" >/dev/null 2>&1 && echo F4_OK', distro, timeout=60)
    return f"{p}/FLASH4.8" if "F4_OK" in out2 else None


# ── 步骤 2: 部署 + 编译 + 运行 + 收集 (WSL FLASHSNB) ───────
def deploy_and_run(snb_home: str, cfg: Dict[str, Any], distro: str,
                   nproc: int, tmax: Optional[str],
                   skip_deploy: bool, skip_setup: bool, skip_make: bool) -> bool:
    obj = f"{snb_home}/{OBJDIR}"
    unit = f"{snb_home}/source/Simulation/SimulationMain/{SIM_NAME}"
    ref_unit = f"{snb_home}/source/Simulation/SimulationMain/SNB_1D_laser"
    wsl_in = wsl_path(INPUT_DIR)
    wsl_out = wsl_path(OUTPUT_DIR)

    # 0) 树级 physics 补丁 (t001 修复; 缺失才复制, 幂等)
    # 注意: wsl bash -lc "<cmd>" 存在双层 bash 展开 (外层先展开 $var),
    # 内联命令严禁依赖 shell 循环变量/$? — 一律 Python 端展开。
    if not skip_deploy:
        t001_wsl = wsl_path(_T001_DIR / "source_patches")
        for rel in _TREE_PATCHES:
            tgt_dir = os.path.dirname(rel)
            code, out = run_wsl(
                f'test -f "{snb_home}/source/{rel}" && echo HAVE || '
                f'( test -f "{t001_wsl}/{rel}" && '
                f'mkdir -p "{snb_home}/source/{tgt_dir}" && '
                f'cp -f "{t001_wsl}/{rel}" "{snb_home}/source/{rel}" && echo SYNCED )',
                distro, timeout=60)
            if "HAVE" in out:
                log(f"树补丁已存在: {rel.rsplit('/', 1)[-1]}", "OK")
            elif "SYNCED" in out:
                log(f"树补丁同步: {rel.rsplit('/', 1)[-1]}", "OK")
            else:
                log(f"树补丁缺失且无归档: {rel} (若编译报泛型错误请检查 t001 归档)", "WARN")

        # 1) 部署单元: 生成 5 件套 + cn4 + 8 个本地覆盖 F90 + mgd_qesh (WSL 树)
        log("部署 SimulationMain 单元 (SNBOneCH)...", "STEP")
        cp_local = " && ".join(
            f'( test -f {wsl_in}/{f} && cp -f {wsl_in}/{f} "{unit}/{f}" || '
            f'cp -f "{ref_unit}/{f}" "{unit}/{f}" )' for f in _LOCAL_OVERRIDE_FILES)
        code, out = run_wsl(
            f'mkdir -p "{unit}" && '
            f'cp -f {wsl_in}/Config {wsl_in}/Makefile '
            f'{wsl_in}/Simulation_data.F90 {wsl_in}/Simulation_init.F90 '
            f'{wsl_in}/Simulation_initBlock.F90 {wsl_in}/*.cn4 "{unit}/" && '
            f'{cp_local} && '
            f'cp -f "{ref_unit}/mgd_qesh.F90" "{unit}/mgd_qesh.F90" && '
            f'ls "{unit}" | wc -l && echo DEPLOY_OK',
            distro, timeout=120)
        if "DEPLOY_OK" not in out:
            log(f"单元部署失败: {out[-400:]}", "ERROR")
            return False
        log(f"单元已部署: {unit}", "OK")

    # 2) setup
    if not skip_setup:
        setup_cmd = f"./setup -auto {SIM_NAME} {SETUP_FLAGS} -objdir={OBJDIR}"
        run_wsl(f'cd {snb_home} && rm -rf {obj} && {setup_cmd} 2>&1 | tail -15',
                distro, timeout=600)
        code, out = run_wsl(f'ls -d {obj} && echo OBJ_OK', distro, timeout=60)
        if "OBJ_OK" not in out:
            log(f"setup 失败: {out[-400:]}", "ERROR")
            return False
        # 防御: objdir 内 mgd_qesh.F90 链接 (单元 Makefile 已声明, setup 通常自动)
        run_wsl(
            f'cd {obj} && ln -sf ../source/Simulation/SimulationMain/{SIM_NAME}/mgd_qesh.F90 '
            f'mgd_qesh.F90 2>/dev/null; true', distro, timeout=60)
        log("setup 完成 (+ug 均匀网格, objdir 已生成)", "OK")
    else:
        code, out = run_wsl(f'ls -d {obj} && echo OBJ_OK', distro, timeout=60)
        if "OBJ_OK" not in out:
            log(f"objdir 不存在, 请先 setup: {obj}", "ERROR")
            return False

    # 3) 编译 (竞态防御: 先单独编关键模块)
    if not skip_make:
        log("编译 (先预编关键模块再 -j4, 约 10~30 分钟)...", "STEP")
        run_wsl(
            f'cd {obj} && make hy_slopeLimiters.o Conductivity_interface.o '
            f'Conductivity_fullState.o 2>&1 | tail -3', distro, timeout=600)
        # make 退出码经 if/else 落盘判定 (双层展开下 $? 不可用)
        code, out = run_wsl(
            f'cd {obj} && if make -j4 > make_snb.log 2>&1; then echo MAKE_OK; '
            f'else echo MAKE_FAIL; fi; tail -12 make_snb.log; '
            f'ls -la flash4 2>/dev/null || echo NO_FLASH4',
            distro, timeout=3600)
        build_ok = "MAKE_OK" in out and "NO_FLASH4" not in out
        if not build_ok:
            log(f"编译异常: {out[-800:]}", "ERROR")
            return False
        log("编译完成 (flash4 已生成)", "OK")

    return _run_and_collect(snb_home, cfg, distro, nproc, tmax,
                            outdir=OUTPUT_DIR, tag="")


def _run_and_collect(snb_home: str, cfg: Dict[str, Any], distro: str,
                     nproc: int, tmax: Optional[str], outdir: Path,
                     tag: str) -> bool:
    """单次运行: par (含 iProcs=nproc) → objdir → mpiexec → 收集到 outdir。"""
    obj = f"{snb_home}/{OBJDIR}"
    wsl_in = wsl_path(INPUT_DIR)
    wsl_out = wsl_path(outdir)

    # par → objdir (按本次 iProcs 重新生成文本, 覆写 tmax)
    outdir.mkdir(parents=True, exist_ok=True)
    par_text = _build_par_text(dict(cfg, iprocs=nproc), nproc)
    if tmax:
        par_text = re.sub(r"(?m)^tmax\s*=.*$", f"tmax          = {tmax}", par_text)
    # par 全文 (~15KB) 不能内嵌进 wsl 命令行 (WinError 206 超长),
    # 必须本地落盘后经 /mnt 路径复制; 副本随输出归档供人工核查。
    par_local = outdir / f"par_ip{nproc}.par"
    par_local.write_text(par_text, encoding="utf-8", newline="\n")
    run_wsl(
        f'cp -f {wsl_path(par_local)} {obj}/flash.par && '
        f'grep -n "^tmax\\|^iProcs" {obj}/flash.par', distro, timeout=60)

    # 运行 + 收集 (RUN_EXIT 用 if/else 落盘 — 双层展开下 $? 会被提前展开)
    log(f"运行 FLASH: mpiexec -n {nproc} ./flash4 (dx≈{_dx_um(nproc, cfg):.2f} um)...", "STEP")
    _t0 = time.time()
    run_wsl(
        f'cd {obj} && rm -f {BASENM}* wsl_run_snbonech.log && '
        f'if mpiexec -n {nproc} ./flash4 > wsl_run_snbonech.log 2>&1; then '
        f'echo RUN_EXIT=0 >> wsl_run_snbonech.log; '
        f'else echo RUN_EXIT_NZ >> wsl_run_snbonech.log; fi', distro, timeout=7200)
    _run_wall = time.time() - _t0
    code, out = run_wsl(
        f'cd {obj} && tail -4 wsl_run_snbonech.log; echo; '
        f'ls {BASENM}* 2>/dev/null | wc -l', distro, timeout=120)
    print(out)
    code3, out3 = run_wsl(
        f'mkdir -p {wsl_out} && '
        f'cp -f {obj}/{BASENM}* {obj}/wsl_run_snbonech.log {obj}/{LOG_FILE} '
        f'{wsl_out}/ 2>/dev/null; '
        f'rm -f {obj}/{BASENM}*; echo COLLECT_DONE', distro, timeout=300)
    if "COLLECT_DONE" not in out3:
        log(f"输出收集失败: {out3[-300:]}", "ERROR")
        return False
    ok = "RUN_EXIT=0" in out or "reached max SimTime" in out
    log(f"运行 {'成功' if ok else '异常'} (输出已收集到 {outdir.name}/) — "
        f"WSL 运行墙钟 {_run_wall:.1f} s ({nproc} proc, dx≈{_dx_um(nproc, cfg):.2f} um)",
        "OK" if ok else "ERROR")
    (outdir / "walltime.txt").write_text(
        f"{nproc} {_dx_um(nproc, cfg):.4f} {_run_wall:.2f}\n",
        encoding="utf-8", newline="\n")
    return ok


# ── 分辨率扫描 ────────────────────────────────────────────
def run_sweep(snb_home: str, cfg: Dict[str, Any], distro: str,
              iprocs_list: List[int], tmax: Optional[str]) -> bool:
    """分辨率扫描: 二进制复用 (仅 par iProcs + mpiexec -n 变化)。

    各档输出收集到 flash_output/sweep_ip<N>/; 全部成功返回 True。
    """
    all_ok = True
    for ip in iprocs_list:
        print(f"\n--- sweep iProcs={ip} (dx≈{_dx_um(ip, cfg):.2f} um) ---")
        ok = _run_and_collect(
            snb_home, cfg, distro, ip, tmax,
            outdir=OUTPUT_DIR / f"sweep_ip{ip}", tag=f"ip{ip}")
        if not ok:
            log(f"iProcs={ip} 运行异常, 继续下一档", "WARN")
            all_ok = False
    return all_ok


def analyze_sweep(cfg: Dict[str, Any]) -> int:
    """跨档对比: 各 iProcs 档末帧密度剖面叠加 + 墙钟/dx 汇总表。"""
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from flash.output_processors.loader import FlashDataLoader

    plt.rcParams.update({
        "font.size": 20, "axes.titlesize": 24, "axes.labelsize": 22,
        "xtick.labelsize": 20, "ytick.labelsize": 20, "legend.fontsize": 18,
        "axes.linewidth": 2.0, "font.family": "DejaVu Sans",
    })
    sweeps = sorted(OUTPUT_DIR.glob("sweep_ip*"),
                    key=lambda p: int(p.name.replace("sweep_ip", "")))
    if not sweeps:
        log("无 sweep 输出目录", "WARN")
        return 0

    fig, ax = plt.subplots(figsize=(13, 6.5), constrained_layout=True)
    cmap = plt.get_cmap("plasma")
    rows = []
    n = 0
    for si, sd in enumerate(sweeps):
        ip = int(sd.name.replace("sweep_ip", ""))
        files = sorted(sd.glob("*plt_cnt*"))
        if not files:
            continue
        try:
            c = FlashDataLoader(str(files[-1])).load(compute_derived=False,
                                                     extraction_mode="yt")
        except Exception as exc:  # noqa: BLE001
            log(f"    跳过 {files[-1].name}: {exc}", "WARN")
            continue
        x = np.asarray(c.x).ravel()
        d = np.asarray(c.data.get("dens", [])).ravel()
        t = float(c.simulation_time)
        m = d > 0
        ax.semilogy(x[m] * 1e4, d[m], lw=2.4, color=cmap(0.15 + 0.75 * si / max(len(sweeps) - 1, 1)),
                    label=f"iProcs={ip} (dx≈{_dx_um(ip, cfg):.2f} um)")
        n += 1
        wt = ""
        wtf = sd / "walltime.txt"
        if wtf.exists():
            parts = wtf.read_text().split()
            if len(parts) >= 3:
                wt = f"{float(parts[2]):.1f} s"
        rows.append((ip, _dx_um(ip, cfg), t * 1e9, wt))

    ax.set_xlabel(r"x [$\mu$m]")
    ax.set_ylabel(r"Density [g/cm$^3$]")
    ax.set_title("SNBOneCH +ug resolution sweep: final density profiles")
    ax.grid(True, which="both", alpha=0.25, lw=0.8)
    if n:
        ax.legend(loc="best", fontsize=16)
        fig.savefig(str(OUTPUT_DIR / "sweep_dens_compare.png"), dpi=450)
    plt.close(fig)
    log(f"    sweep_dens_compare.png ✓ ({n} 档)")

    print("\n  分辨率扫描汇总:")
    print("  iProcs | dx [um]  | final t [ns] | walltime")
    print("  -------+----------+--------------+---------")
    for ip, dx, tns, wt in rows:
        print(f"  {ip:>6} | {dx:>7.3f} | {tns:>11.4g} | {wt}")
    return n


# ── 主流程 ────────────────────────────────────────────────
def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(
        description="SNBOneCH: 最小两区 SNB 场景 (+ug 均匀网格强制, 分辨率研究; FLASHSNB)")
    ap.add_argument("--generate-only", action="store_true",
                    help="只生成 FLASHSNB 输入文件, 不部署/编译/运行")
    ap.add_argument("--iprocs", type=int, default=None,
                    help="单跑模式的 iProcs (默认 8 → dx≈7.8um; +ug 块数=iProcs)")
    ap.add_argument("--tmax", default=None,
                    help="覆写仿真结束时间 (s), 如 1.0e-11 (首跑验证规范)")
    ap.add_argument("--sweep", default=None,
                    help="分辨率扫描: 逗号分隔 iProcs 列表 (如 8,16,32,64); "
                         "二进制只编译一次, 各档仅换 par 运行")
    ap.add_argument("--skip-deploy", action="store_true",
                    help="跳过单元部署 (复用 FLASHSNB 内已部署单元)")
    ap.add_argument("--skip-setup", action="store_true",
                    help="跳过 setup (复用现有 objdir)")
    ap.add_argument("--skip-make", action="store_true",
                    help="跳过 make (复用现有 flash4)")
    ap.add_argument("--no-analyze", action="store_true",
                    help="跳过运行后的密度剖面/扫汇分析图")
    ap.add_argument("--distro", default="Ubuntu-22.04", help="WSL 发行版")
    args = ap.parse_args()

    print("\n" + "=" * 65)
    print(" FLASH SNBOneCH (two-zone He|CH + SNB model, +ug mandatory, FLASHSNB)")
    print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)
    cfg = dict(config_constants)
    if args.tmax is not None:
        cfg["tmax"] = float(args.tmax)
    if args.iprocs is not None:
        cfg["iprocs"] = int(args.iprocs)
    nproc = cfg["iprocs"]
    sweep_list = None
    if args.sweep:
        sweep_list = [int(c) for c in re.split(r"[,\s]+", args.sweep.strip()) if c]
    print(f"\n  几何: x<0 cham (He {cfg['rho_cham']:g} g/cm^3) | "
          f"x>0 targ (CH {cfg['rho_targ']:g} g/cm^3), 域 [{cfg['xmin']}, {cfg['xmax']}] cm")
    print(f"  模型: SNB 非局域热传导 (FLASHSNB 专用, 单元 {SIM_NAME})")
    print(f"  网格: ★ +ug 均匀网格 (SNB 铁律) — dx = 0.05/(iProcs*8)")
    print(f"  模式: {'sweep ' + str(sweep_list) if sweep_list else 'single'} "
          f"iProcs={nproc} (dx≈{_dx_um(nproc, cfg):.2f} um)")
    print(f"  tmax={cfg['tmax']:.3e} s, tstep×{cfg['tstep_change_factor']}, "
          f"dtmax={cfg['dtmax']:.1e} (t001 +ug 基线)")
    print("=" * 65)

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from flash.input_gen.gen_checker import DependencyChecker
        missing = DependencyChecker(INPUT_DIR).missing_standard()
        if missing:
            log(f"缺失 {len(missing)} 项必须文件: {missing}", "WARN")
            generate_input_files(cfg)
        else:
            # par 需与当前 iProcs/tmax 一致, 否则重新生成
            par_ok = False
            p = INPUT_DIR / PAR_FILENAME
            if p.exists():
                txt = p.read_text(encoding="utf-8", errors="replace")
                m_ip = re.search(r"(?m)^\s*iProcs\s*=\s*(\d+)", txt)
                m_tm = re.search(r"(?m)^\s*tmax\s*=\s*([0-9.eE+-]+)", txt)
                par_ok = (m_ip and int(m_ip.group(1)) == nproc
                          and m_tm and abs(float(m_tm.group(1)) - cfg["tmax"])
                          <= 1e-12 * abs(cfg["tmax"]))
            if par_ok:
                log("FLASHSNB 输入文件已就绪, 无需重新生成", "OK")
            else:
                log("par 与当前配置 (iProcs/tmax) 不符, 重新生成输入文件", "INFO")
                generate_input_files(cfg)
    except Exception as e:
        log(f"输入文件检查/生成失败: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return 1

    if args.generate_only:
        log("--generate-only: 输入文件生成完毕", "OK")
        return 0

    # ── WSL 部署 + 编译 (一次性) ──
    snb_home = find_snb_home(args.distro)
    if not snb_home:
        log("WSL 中未找到 FLASHSNB (find $HOME -maxdepth 3 -name FLASHSNB)", "ERROR")
        return 1
    log(f"FLASHSNB: {snb_home}", "OK")

    if sweep_list:
        # 扫描模式: 部署/setup/make 一次, 然后逐档运行
        if not deploy_and_run(snb_home, dict(cfg, iprocs=sweep_list[0]), args.distro,
                              nproc=sweep_list[0], tmax=None,
                              skip_deploy=args.skip_deploy, skip_setup=args.skip_setup,
                              skip_make=True):
            return 1
        # make 单独步骤 (deploy_and_run 中 skip_make=True 时需补编译)
        obj = f"{snb_home}/{OBJDIR}"
        if not args.skip_make:
            code, out = run_wsl(
                f'cd {obj} && if make -j4 > make_snb.log 2>&1; then echo MAKE_OK; '
                f'else echo MAKE_FAIL; fi; tail -8 make_snb.log; '
                f'ls -la flash4 2>/dev/null || echo NO_FLASH4', args.distro, timeout=3600)
            if "MAKE_OK" not in out or "NO_FLASH4" in out:
                log(f"编译异常: {out[-600:]}", "ERROR")
                return 1
            log("编译完成 (flash4 已生成)", "OK")
        run_sweep(snb_home, cfg, args.distro, sweep_list, str(cfg["tmax"]))
        if not args.no_analyze:
            analyze_sweep(cfg)
        return 0

    # ── 单跑模式 ──
    ok = deploy_and_run(snb_home, cfg, args.distro, nproc=nproc,
                        tmax=str(cfg["tmax"]),
                        skip_deploy=args.skip_deploy, skip_setup=args.skip_setup,
                        skip_make=args.skip_make)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
