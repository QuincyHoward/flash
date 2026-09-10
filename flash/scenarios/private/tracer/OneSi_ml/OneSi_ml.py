"""
OneSi_ml 场景 — 1D 多薄层单一纯材料 (硅 Si) 示踪靶烧蚀仿真
═══════════════════════════════════════════════════════════════════

由 OneCH_ml 场景派生 (2026-09-02)：结构/物种/几何完全一致, 唯一物理差异是
**全部固体层 (shld/samp/tar1/tar2/tar3/tar4/tar6) 为同一种纯材料 Si**
(密度 2.329 g/cm^3 常温固体密度, EOS/不透明度表 Z14_1.00-20260708_0850.cn4,
A=28.0855, Z=14) — 单一纯材料烧蚀仿真, shld/tar* 物种标记仅用于
诊断追踪不同深度的材料运动 (无成分界面, 只有物种标记界面)。

与 OneCH_ml 的唯一物理差异: 固体层材质 CH → Si (含 shld/samp/tar* 全部
固体物种); 腔室 cham 仍为稀氦 He (1e-6 g/cm^3)。

  * 1D 笛卡尔域 x=[-0.04, 0.01] cm，FLASH_3T，NXB=16，MAXBLOCKS=4096
  * 单光束 0.351um 激光（透镜 x=-1.0，靶 x=0），82 点功率脉冲
  * 8 物种 12 区分层（delta=0.1um, L1=1um, L2=2um, L3=3um, L4=4um,
    L6=6um, D=50um; 示踪层间距均为 samp）:

      x < 0                        cham [氦 He, 1e-6 g/cm^3]
      0        < x < delta         shld [硅 Si, 2.329 g/cm^3]  ← 表面层标记
      delta    < x < L1            samp [硅 Si, 2.329 g/cm^3]
      L1       < x < L1+delta      tar1 [硅 Si]  ← 示踪薄层 1
      L1+delta < x < L2            samp [硅 Si]
      L2       < x < L2+delta      tar2 [硅 Si]  ← 示踪薄层 2
      L2+delta < x < L3            samp [硅 Si]
      L3       < x < L3+delta      tar3 [硅 Si]  ← 示踪薄层 3
      L3+delta < x < L4            samp [硅 Si]
      L4       < x < L4+delta      tar4 [硅 Si]  ← 示踪薄层 4
      L4+delta < x < L6            samp [硅 Si]
      L6       < x < L6+delta      tar6 [硅 Si]  ← 示踪薄层 6
      L6+delta < x < L6+delta+D    samp [硅 Si]
      其余 (x<-0.04 域外 / x>56.1um)  cham [氦 He]

  * 8 物种标记: cham/shld/samp/tar1/tar2/tar3/tar4/tar6。固体层初始均为
    常温 (290.11375 K) 固体密度 2.329 g/cm^3 纯 Si; 各标记层物质相同, 用独立
    物种标记以便诊断追踪 (材质单一 → 烧蚀过程无材料界面)。
  * MGD 6 能群辐射（Gen_eos_op_data 表族结构, 十倍程边界 0.1 eV → 1e5 eV;
    腔室 He 表同步采用同族 6 群 Z02 表, 与 ch_center 场景先例一致）,
    tabular EOS/opacity (ionmix4)。
  * 时间: 默认 tmax=1.0e-11 s (极短验证); 正式物理运行手动改 1.6e-9
    或用 --tmax 覆盖。

用法:
  cd <flash 包目录>
  python -m flash.scenarios.private.tracer.OneSi_ml.OneSi_ml   # 默认 tmax=1.0e-11
  python flash/scenarios/private/tracer/OneSi_ml/OneSi_ml.py --tmax 1.6e-9
"""

import sys
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# 统一 stdout/stderr 为 UTF-8，避免 GBK 控制台报错
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ── BEGIN SCENE VARS (家族各脚本仅此块+docstring 不同; build_sic_family.py 换块生成) ──
SCENE_NAME = "OneSi_ml"                      # 场景名 → SIM_NAME/par 文件名/图题/SLURM 作业名
MAT_LABEL = "Si"                             # 固体材料标签 (硅)
MAT_TABLE = "Z14_1.00-20260708_0850.cn4"     # EOS/不透明度表 (Z14=Si; 表名 1.00 为生成标称密度)
MAT_RHO = 2.329                              # 固体密度 g/cm^3 (常温固体密度; 表内密度网格为离子数密度, 覆盖充足)
MAT_A = 28.0855                              # 摩尔质量 g/mol
MAT_Z = 14.0                                 # 核电荷数
RADIATION_OFF = False                        # True=关闭辐射输运 (F 变体: 三开关 .false.)
# ── END SCENE VARS ──────────────────────────────────────────────────────────

# ── Bootstrap: 定位 flash 包根目录 ─────────────────────────
_ROOT = Path(__file__).resolve().parent
for _ in range(14):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _get_sim_user_dir() -> str:
    from flash.scenarios.runner import get_sim_user_dir as _sud
    return _sud()


SIM_USER_DIR = _get_sim_user_dir()

# 运行模式: "wsl" 本机 WSL 运行; "hpc" 超算(paramiko 分阶段驱动)
# 一键切换即修改此行; 也可用环境变量 FLASH_RUN_MODE 覆盖
RUN_MODE = "wsl"

# ── 可配置参数 ────────────────────────────────────────────
config_constants = {
    # 分层几何 (μm): delta=屏蔽层/示踪层厚度, L1/L2/L3/L4/L6=示踪层外边界
    # (累积位置, cm 值见 sim_tarXRadius), D=尾部 samp 厚度
    "delta_um": 0.1,
    "L1_um": 1.0,
    "L2_um": 2.0,
    "L3_um": 3.0,
    "L4_um": 4.0,
    "L6_um": 6.0,
    "D_um": 50.0,
    # 仿真结束时间 (s)。验证阶段为极短值 1.0e-11 (脚本默认);
    # 正式物理运行手动改回 1.6e-9 或用 --tmax 1.6e-9 覆盖。
    "tmax": 1.0e-11,
    # 仿真域 (cm)
    "xmin": -0.04,
    "xmax": 0.01,
    # 网格
    "nblockx": 8,
    "lrefine_max": 9,
    # 输出频率 (与基准一致: plotFileIntervalStep=2000, checkpointFileIntervalStep=400)
    "plot_interval_step": 2000,
    "checkpoint_interval_step": 400,
    # 维度 (用于按装置×维度自动配置资源核数)
    "dimension": 1,
    # MPI 进程数: None → 按装置×维度自动计算; 显式指定则覆盖
    "nprocs": None,
    # 超算 SLURM 分区/ntasks: None → 生成器按维度自动计算
    "slurm_partition": "v5_192",
    "slurm_ntasks": None,
}

# FLASH setup 标志 (wsl/hpc 共用) — 8 物种
# 注: 关辐射 (_F 变体) 为纯运行时 .par 开关, setup/编译完全不变 (+mgd 保留)
SETUP_FLAGS = (
    "-1d +cartesian -nxb=16 +hdf5typeio species=cham,shld,samp,tar1,tar2,tar3,tar4,tar6 "
    "+mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 "
    "ed_maxPulseSections=300 -maxblocks=4096"
)

# 仿真/对象/par 命名 (各场景唯一, 避免相互覆盖 objdir)
SIM_NAME = f"LaserSlab_{SCENE_NAME}"
PAR_FILENAME = f"laserslab_{SCENE_NAME.lower()}.par"

# 规范物理参数（沿用水脉冲/MGD 等内嵌字典, 自包含）
from flash.scenarios.private.tracer._par_layers import CH_FLASH_PAR

# 场景目录
SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_DIR = SCRIPT_DIR / "flash_input"
OUTPUT_DIR = SCRIPT_DIR / "flash_output"
PLOTS_DIR = OUTPUT_DIR / "plots"

# 物种列表 (绘图/生成器共用, 顺序即 FLASH 物种常量顺序)
SPECIES_LIST = ["cham", "shld", "samp", "tar1", "tar2", "tar3", "tar4", "tar6"]

# 腔室 He 表: Gen_eos_op_data 族 6 能群表 (与固体层 Si/C 表群结构一致)。
# 注意: BADGER 族 He 表 (He-BADGER-TOPS-Final.cn4) 为 10 能群, 与 6 群的
# Si/C 表混用会触发 op_readIonmix4Tables "bad size of IONMIX4 energy group
# grid" abort — FLASH 要求全部物种不透明度表能群数一致。
# 同族 6 群 He 表 Z02_1.00-20260708_0851.cn4 与 ch_center 场景先例一致。
CHAM_TABLE = "Z02_1.00-20260708_0851.cn4"


def log(msg: str, level: str = "INFO"):
    tag = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]", "STEP": "[-]"}.get(level, "[i]")
    print(f"  {tag} {msg}")


# ── 物种定义 (单一纯材料多薄层场景) ─────────────────────────
def build_species_defs(delta_cm: float, L1: float, L2: float, L3: float,
                       L4: float, L6: float, D: float) -> List[dict]:
    """构建 8 物种定义：cham=He, shld/samp/tar1/tar2/tar3/tar4/tar6=同一纯材料。

    单一纯材料烧蚀场景: 全部固体层 (shld/samp/tar*) 材质相同 (MAT_TABLE,
    密度 MAT_RHO), 物种标记仅用于诊断追踪不同深度的材料运动。
    几何经 radius/height (+ radius_param/height_param) 声明为 FLASH
    运行时参数 (Config 默认值 + Simulation_data 声明 + Simulation_init
    读取), Simulation_initBlock 的区域边界引用这些参数表达式 —
    **只改 .par 中的参数值即可改变场景几何, 无需改代码**:

        sim_shldRadius = delta   (屏蔽层/示踪薄层厚度)
        sim_tar1Radius = L1      (tar1 层外边界累积位置)
        sim_tar2Radius = L2
        sim_tar3Radius = L3
        sim_tar4Radius = L4
        sim_tar6Radius = L6
        sim_sampHeight = D       (尾部 samp 厚度)
    """
    he_file = CHAM_TABLE
    return [
        # 腔室: 稀氦 (区域外默认物种)
        {"name": "cham", "file": he_file, "rho": 1.0e-6, "A": 4.002602, "Z": 2.0},
        # 表面层: 纯材料 (厚度 = delta)
        {"name": "shld", "file": MAT_TABLE, "rho": MAT_RHO, "A": MAT_A,
         "Z": MAT_Z, "radius": delta_cm},
        # 基体层: 纯材料 (samp 多次出现; height = 尾部 samp 厚度 D)
        {"name": "samp", "file": MAT_TABLE, "rho": MAT_RHO, "A": MAT_A,
         "Z": MAT_Z, "height": D},
        # 示踪薄层 1-4, 6: 纯材料标记 (radius = 累积外边界 L1/L2/L3/L4/L6)
        {"name": "tar1", "file": MAT_TABLE, "rho": MAT_RHO, "A": MAT_A,
         "Z": MAT_Z, "radius": L1, "radius_param": "sim_tar1Radius"},
        {"name": "tar2", "file": MAT_TABLE, "rho": MAT_RHO, "A": MAT_A,
         "Z": MAT_Z, "radius": L2, "radius_param": "sim_tar2Radius"},
        {"name": "tar3", "file": MAT_TABLE, "rho": MAT_RHO, "A": MAT_A,
         "Z": MAT_Z, "radius": L3, "radius_param": "sim_tar3Radius"},
        {"name": "tar4", "file": MAT_TABLE, "rho": MAT_RHO, "A": MAT_A,
         "Z": MAT_Z, "radius": L4, "radius_param": "sim_tar4Radius"},
        {"name": "tar6", "file": MAT_TABLE, "rho": MAT_RHO, "A": MAT_A,
         "Z": MAT_Z, "radius": L6, "radius_param": "sim_tar6Radius"},
    ]


# ── 步骤 1: 生成 FLASH 输入文件 ───────────────────────────
def generate_input_files(cfg: Dict[str, Any]) -> Dict[str, str]:
    from flash.input_gen.gen_par import ParGeneratorExtended
    from flash.input_gen.gen_config import ConfigGenerator
    from flash.input_gen.gen_makefile import MakefileGenerator
    from flash.input_gen.gen_sim_data import SimDataGenerator
    from flash.input_gen.gen_sim_init import SimInitGenerator
    from flash.input_gen.gen_sim_initblock import BlockGenerator, GridBuilder
    from flash.input_gen.gen_shell_script import ShellScriptGenerator

    delta_cm = cfg["delta_um"] * 1e-4
    L1 = cfg["L1_um"] * 1e-4
    L2 = cfg["L2_um"] * 1e-4
    L3 = cfg["L3_um"] * 1e-4
    L4 = cfg["L4_um"] * 1e-4
    L6 = cfg["L6_um"] * 1e-4
    D = cfg["D_um"] * 1e-4

    species_defs = build_species_defs(delta_cm, L1, L2, L3, L4, L6, D)
    sim_path = f"{SIM_USER_DIR}/{SIM_NAME}"
    objdir = f"{SIM_USER_DIR}/{SIM_NAME}"
    par_filename = PAR_FILENAME

    from flash.scenarios.runner import default_nprocs
    # 维度感知资源默认值: 未显式指定时按装置×维度自动计算
    nprocs = cfg["nprocs"] or default_nprocs(cfg["dimension"], is_hpc=False)
    slurm_ntasks = cfg["slurm_ntasks"] or default_nprocs(cfg["dimension"], is_hpc=True)

    result: Dict[str, str] = {}
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. par（内嵌规范参数 CH_FLASH_PAR + 物种/几何/材质覆写）──
    log("  [1/9] 生成 .par 文件...", "STEP")
    tmp_params = dict(CH_FLASH_PAR)
    # 新场景无 targ 物种且 samp 不声明几何参数: 显式剔除 targ 物种专属键。
    # 注意不能用 "targ" in k 模糊匹配 — 会误删激光 ed_targetX_1 (target⊃targ)!
    _TARG_KEYS = {
        "sim_targetRadius", "sim_targetHeight",
        "sim_rhoTarg", "sim_teleTarg", "sim_tionTarg", "sim_tradTarg",
        "ms_targA", "ms_targZ", "ms_targZMin",
    }
    for k in list(tmp_params):
        if k in _TARG_KEYS or k.startswith(("op_targ", "eos_targ")) \
                or k == "sim_sampRadius" \
                or k.startswith("plot_var"):
            del tmp_params[k]
    # Gen_eos_op_data 表族 (Z14/Z06_*) 为 6 能群结构 (表第 4 行 nEnergyGroups=6,
    # 表内不存边界, FLASH 仅校验群数), par 必须用 6 群 MGD 结构 — 否则
    # op_readIonmix4Tables "bad size of IONMIX4 energy group grid" abort。
    # 先清除 CH_FLASH_PAR 的 10 群边界 rt_mgdBounds_8..11 (bounds_1..7 随后覆写)。
    for k in ("rt_mgdBounds_8", "rt_mgdBounds_9", "rt_mgdBounds_10",
              "rt_mgdBounds_11"):
        tmp_params.pop(k, None)
    par_gen = ParGeneratorExtended(simulation_name=SIM_NAME, dimension=1)
    # 清除维度默认参数，仅保留规范参数 + 下方覆写，避免未注册参数混入 par
    par_gen._params.clear()
    for k, v in tmp_params.items():
        par_gen.set(k, v)
    # 覆写: 几何 (与 OneCH_ml 完全一致的 12 区分层)
    # 分层几何全部经运行时参数控制 (Simulation_initBlock 引用这些参数),
    # 只改 .par 中以下 7 个值即可改变场景几何, 无需改代码:
    #   [0, shldR] shld | [shldR, tar1R] samp | [tar1R, tar1R+shldR] tar1 |
    #   [tar1R+shldR, tar2R] samp | [tar2R, tar2R+shldR] tar2 |
    #   [tar2R+shldR, tar3R] samp | [tar3R, tar3R+shldR] tar3 |
    #   [tar3R+shldR, tar4R] samp | [tar4R, tar4R+shldR] tar4 |
    #   [tar4R+shldR, tar6R] samp | [tar6R, tar6R+shldR] tar6 |
    #   [tar6R+shldR, tar6R+shldR+sampH] samp | 其余 cham
    par_gen.set("sim_shldRadius", delta_cm)             # delta (示踪层/屏蔽层厚度)
    par_gen.set("sim_tar1Radius", L1)                   # L1
    par_gen.set("sim_tar2Radius", L2)                   # L2
    par_gen.set("sim_tar3Radius", L3)                   # L3
    par_gen.set("sim_tar4Radius", L4)                   # L4 = 4.0e-4 cm
    par_gen.set("sim_tar6Radius", L6)                   # L6 = 6.0e-4 cm
    par_gen.set("sim_sampHeight", D)                    # D
    # 覆写: 腔室 He 表 → 同族 6 能群表 (CH_FLASH_PAR 默认 BADGER 10 群表)
    par_gen.set("eos_chamTableFile", CHAM_TABLE)
    par_gen.set("op_chamFileName", CHAM_TABLE)
    # 覆写: 材质 — 全部固体层单一纯材料 (CH_FLASH_PAR 中 shld/samp 默认为
    # CH 的 ms_*/eos_*/op_* 值, 必须逐项覆写; tar* 无 par 默认, 由 Config
    # 按 species_defs 生成 ms_tarXA/ms_tarZ/sim_rhoTarX 默认, 此处显式
    # 覆写 sim_rhoTarX 以自文档化)
    par_gen.set("sim_rhoShld", MAT_RHO)
    par_gen.set("ms_shldA", MAT_A)                      # 默认 6.509 (CH) → MAT_A
    par_gen.set("ms_shldZ", MAT_Z)                      # 默认 3.5 (CH) → MAT_Z
    par_gen.set("eos_shldTableFile", MAT_TABLE)
    par_gen.set("op_shldFileName", MAT_TABLE)
    par_gen.set("sim_rhoSamp", MAT_RHO)
    par_gen.set("ms_sampA", MAT_A)                      # 默认 6.509 (CH) → MAT_A
    par_gen.set("ms_sampZ", MAT_Z)                      # 默认 3.5 (CH) → MAT_Z
    par_gen.set("eos_sampTableFile", MAT_TABLE)
    par_gen.set("op_sampFileName", MAT_TABLE)
    for tar in ("tar1", "tar2", "tar3", "tar4", "tar6"):
        par_gen.set(f"sim_rho{tar.capitalize()}", MAT_RHO)
        par_gen.set(f"eos_{tar}EosType", "eos_tab")
        par_gen.set(f"eos_{tar}SubType", "ionmix4")
        par_gen.set(f"eos_{tar}TableFile", MAT_TABLE)
        par_gen.set(f"op_{tar}Absorb", "op_tabpa")
        par_gen.set(f"op_{tar}Emiss", "op_tabpe")
        par_gen.set(f"op_{tar}Trans", "op_tabro")
        par_gen.set(f"op_{tar}FileType", "ionmix4")
        par_gen.set(f"op_{tar}FileName", MAT_TABLE)
    # 覆写: MGD 能群结构 — 匹配 Gen_eos_op_data 表族 6 能群
    # (十倍程边界 0.1 eV → 1e5 eV, 与 ch_center 场景对同族表的先例一致;
    #  _F 变体 useOpacity=.false. 不读表, 此结构无害保留)
    par_gen.set("rt_mgdNumGroups", 6)
    for _i, _b in enumerate((0.1, 1.0, 10.0, 100.0, 1000.0, 1.0e4, 1.0e5),
                            start=1):
        par_gen.set(f"rt_mgdBounds_{_i}", _b)
    # 覆写: 关辐射 (_F 变体)
    # ReDo042sp_CH042sp*umF8.00e-02 vs *umL8.00e-02 对比: 源码/setup/编译
    # 完全不变 (Makefile/全部 F90 逐字节相同), 纯运行时关闭三处开关:
    #   rt_useMGD  .true. → .false.   (MGD 多群辐射输运)
    #   useOpacity .true. → .false.   (不透明度)
    #   useRadTrans 补充置 .false.    (辐射输运总开关)
    # 其余 rt_mgd*/op_* 参数原样保留 (关闭后不生效, 与基准 par 一致)。
    if RADIATION_OFF:
        par_gen.set("rt_useMGD", False)
        par_gen.set("useOpacity", False)
        par_gen.set("useRadTrans", False)
    # 覆写: 运行控制
    par_gen.set("tmax", cfg["tmax"])
    par_gen.set("plotFileIntervalStep", cfg["plot_interval_step"])
    par_gen.set("checkpointFileIntervalStep", cfg["checkpoint_interval_step"])
    # 覆写: plotfile 输出变量白名单 (模板为 4 物种旧列表且含已删除的 targ;
    # FLASH 只输出 plot_var_N 白名单内的变量, 必须与 8 物种对齐)
    _PLOT_VARS = ["dens", "depo", "tele", "tion", "trad", "ye", "sumy",
                  "cham", "shld", "samp", "tar1", "tar2", "tar3", "tar4",
                  "tar6", "fllm"]
    for i, v in enumerate(_PLOT_VARS, start=1):
        par_gen.set(f"plot_var_{i}", f"{v:<4s}")
    par_path = par_gen.save(str(INPUT_DIR / par_filename))
    result["par"] = str(par_path)
    log(f"    .par → {par_path.name} ✓")

    # ── 2. Config（8 物种注册, eos/op PARAMETER 自动生成）──
    log("  [2/9] 生成 Config (8 species)...", "STEP")
    config_path = ConfigGenerator().save(
        str(INPUT_DIR / "Config"), simulation_path=sim_path, species_defs=species_defs,
    )
    result["config"] = str(config_path)
    log(f"    Config → Config ✓")

    # ── 3. Makefile (Simulation 片段) ─────────────────────
    log("  [3/9] 生成 Makefile...", "STEP")
    MakefileGenerator().save(str(INPUT_DIR / "Makefile"), sim_path=sim_path)
    result["makefile"] = str(INPUT_DIR / "Makefile")

    # ── 4. Simulation_data.F90 ────────────────────────────
    log("  [4/9] 生成 Simulation_data.F90...", "STEP")
    SimDataGenerator().save(str(INPUT_DIR / "Simulation_data.F90"), species=species_defs)
    result["sim_data"] = str(INPUT_DIR / "Simulation_data.F90")

    # ── 5. Simulation_init.F90 ────────────────────────────
    log("  [5/9] 生成 Simulation_init.F90...", "STEP")
    SimInitGenerator().save(str(INPUT_DIR / "Simulation_init.F90"), params={"species": species_defs})
    result["sim_init"] = str(INPUT_DIR / "Simulation_init.F90")

    # ── 6. Simulation_initBlock.F90（8 物种 12 区分层）──────
    log("  [6/9] 生成 Simulation_initBlock.F90 (8 species, 12 regions)...", "STEP")
    builder = GridBuilder(dim=1, geometry="cartesian", domain=(cfg["xmin"], cfg["xmax"]))
    for sp in species_defs:
        builder.set_material(sp["name"], rho=sp["rho"], tele=290.11375,
                             tion=290.11375, trad=290.11375)
    # 分层边界: 数值 x_range 供采样/预诊断; x_expr (参数表达式) 供
    # Simulation_initBlock 代码生成 — 几何由 .par 运行时参数控制。
    # 未命中区域 → cham 兜底 (x<0 与 x>L6+delta+D)。
    builder.add_region(
        "shld", species="shld", x_range=(0.0, delta_cm),
        x_expr=("0.0", "sim_shldRadius"))
    builder.add_region(
        "samp_1", species="samp", x_range=(delta_cm, L1),
        x_expr=("sim_shldRadius", "sim_tar1Radius"))
    builder.add_region(
        "tar1", species="tar1", x_range=(L1, L1 + delta_cm),
        x_expr=("sim_tar1Radius", "sim_tar1Radius + sim_shldRadius"))
    builder.add_region(
        "samp_2", species="samp", x_range=(L1 + delta_cm, L2),
        x_expr=("sim_tar1Radius + sim_shldRadius", "sim_tar2Radius"))
    builder.add_region(
        "tar2", species="tar2", x_range=(L2, L2 + delta_cm),
        x_expr=("sim_tar2Radius", "sim_tar2Radius + sim_shldRadius"))
    builder.add_region(
        "samp_3", species="samp", x_range=(L2 + delta_cm, L3),
        x_expr=("sim_tar2Radius + sim_shldRadius", "sim_tar3Radius"))
    builder.add_region(
        "tar3", species="tar3", x_range=(L3, L3 + delta_cm),
        x_expr=("sim_tar3Radius", "sim_tar3Radius + sim_shldRadius"))
    builder.add_region(
        "samp_4", species="samp", x_range=(L3 + delta_cm, L4),
        x_expr=("sim_tar3Radius + sim_shldRadius", "sim_tar4Radius"))
    builder.add_region(
        "tar4", species="tar4", x_range=(L4, L4 + delta_cm),
        x_expr=("sim_tar4Radius", "sim_tar4Radius + sim_shldRadius"))
    builder.add_region(
        "samp_5", species="samp", x_range=(L4 + delta_cm, L6),
        x_expr=("sim_tar4Radius + sim_shldRadius", "sim_tar6Radius"))
    builder.add_region(
        "tar6", species="tar6", x_range=(L6, L6 + delta_cm),
        x_expr=("sim_tar6Radius", "sim_tar6Radius + sim_shldRadius"))
    builder.add_region(
        "samp_rear", species="samp",
        x_range=(L6 + delta_cm, L6 + delta_cm + D),
        x_expr=("sim_tar6Radius + sim_shldRadius",
                "sim_tar6Radius + sim_shldRadius + sim_sampHeight"))
    block_gen = BlockGenerator(
        simulation_name=SIM_NAME, sim_path=sim_path, species=SPECIES_LIST,
    )
    block_gen.build(builder)
    block_path = block_gen.save(str(INPUT_DIR / "Simulation_initBlock.F90"))
    result["sim_initblock"] = str(block_path)
    log(f"    Simulation_initBlock.F90 ({len(builder.regions)} regions) ✓")

    # ── 7. EOS/opacity .cn4（多级查找复制到 flash_input）──
    log("  [7/9] 复制 EOS/opacity 表...", "STEP")

    def _copy_cn4(filename: str, aliases) -> bool:
        """按 注册表别名 → eos_op_data 递归 → 旧仓库兜底 的顺序复制 .cn4。

        注意: copy_eos_file 源缺失时返回 None 而非抛异常, 必须显式校验。
        Si/C 表 (Z14/Z06_*) 位于 eos_op_data/Gen_eos_op_data/ 子目录,
        未收录注册表 — 走 rglob 按文件名递归查找 (别名占位必失败后兜底)。
        """
        from flash.input_gen.gen_eos_op import EOSOpacityGenerator
        # 1) 注册表别名路径 (注册表与数据布局一致时直接命中)
        dst = EOSOpacityGenerator().copy_eos_file(aliases[0], INPUT_DIR)
        if dst is not None and Path(dst).exists():
            return True
        # 2) eos_op_data 递归按文件名查找 (容忍平铺/子目录布局差异)
        data_root = _ROOT / "flash" / "input_gen" / "gen_eos_op" / "eos_op_data"
        for cand in data_root.rglob(filename):
            shutil.copyfile(cand, INPUT_DIR / filename)
            log(f"    {filename} ← {cand.relative_to(data_root)}", "INFO")
            return True
        # 3) 旧仓库兜底 (flash_c; 新克隆仓库表尚未补齐时的过渡方案)
        legacy = _ROOT.parent / "flash_c" / "flash" / "input_gen" / "gen_eos_op" / "eos_op_data"
        if legacy.is_dir():
            for cand in legacy.rglob(filename):
                shutil.copyfile(cand, INPUT_DIR / filename)
                log(f"    {filename} ← 旧仓库兜底: {cand.relative_to(legacy)}", "WARN")
                return True
        log(f"    {filename} 缺失 (注册表/数据目录/旧仓库均未找到)", "ERROR")
        return False

    ok_all = True
    for filename, aliases in (
        (CHAM_TABLE, (CHAM_TABLE,)),
        (MAT_TABLE, (MAT_TABLE,)),
    ):
        if not _copy_cn4(filename, aliases):
            ok_all = False
    if not ok_all:
        log("EOS/opacity 表不齐全, 终止 (FLASH 将因缺表 abort)", "ERROR")
        return result

    # ── 8. run_flash.sh (wsl) + submit_flash.sh (hpc) ────
    log("  [8/9] 生成运行脚本 (wsl + hpc)...", "STEP")
    setup_cmd = ShellScriptGenerator.build_setup_cmd(
        sim_path=sim_path, objdir=objdir, parfile=par_filename, flags=SETUP_FLAGS,
    )
    # FLASH 输出收集目录: {场景}/flash_output/outputfiles — 生成脚本与
    # runner.WslSpec.outputfiles_dir 两端必须一致
    from flash.scenarios.runner import _to_wsl_path
    collect_dir_wsl = _to_wsl_path(OUTPUT_DIR / "outputfiles")
    wsl_config = {
        "sim_user_dir": SIM_USER_DIR, "dimension": cfg["dimension"],
        "platform": "local", "setup_cmd": setup_cmd,
        "nprocs": nprocs, "sim_path": sim_path, "object_dir": objdir,
        "flash_home": f"$HOME/{SIM_USER_DIR}/FLASH/FLASH4.8",
        "collect_dir": collect_dir_wsl,
    }
    ShellScriptGenerator(config=wsl_config).save(
        str(INPUT_DIR / "run_flash.sh"), "wsl", par_file=par_filename,
    )
    result["script_wsl"] = str(INPUT_DIR / "run_flash.sh")
    log(f"    run_flash.sh ✓")
    hpc_config = {
        "sim_user_dir": SIM_USER_DIR, "dimension": cfg["dimension"],
        "platform": "hpc", "setup_cmd": setup_cmd,
        "nprocs": slurm_ntasks,
        "sim_path": sim_path, "object_dir": objdir,
        "par_file": par_filename, "flash_home": f"$HOME/{SIM_USER_DIR}/FLASH/FLASH4.8",
        "flash_exe": "flash4", "build_cores": 32,
        "slurm_partition": cfg.get("slurm_partition", "v5_192"),
        "slurm_nodes": 1, "slurm_ntasks": slurm_ntasks,
        "slurm_job_name": SCENE_NAME, "slurm_walltime": "24:00:00",
        "slurm_modules": ["mpich/3.2-gcc9.3", "hdf5/1.8.18"],
        # srun 直启 oneAPI MPI 在本集群 PMI2 握手失败, 用 mpiexec 实测正常
        "slurm_mpi_runner": "mpiexec",
        # 模块加载后补 source oneAPI setvars: Makefile.h 硬编码 oneAPI mpiifort,
        # 作业中 module purge 会清掉其环境变量导致链接找不到 -lmpifort/-lmpi
        "slurm_env_lines": [
            "source /public1/soft/oneAPI/2022.1/setvars.sh >/dev/null 2>&1 || true",
        ],
    }
    ShellScriptGenerator(config=hpc_config).save(
        str(INPUT_DIR / "submit_flash.sh"), "slurm", par_file=par_filename,
    )
    result["script_hpc"] = str(INPUT_DIR / "submit_flash.sh")
    log(f"    submit_flash.sh ✓")

    # ── 9. 预诊断图 (激光脉冲 + 初始密度分层, gen_checker.ploter) ──
    log("  [9/9] 生成预诊断图 (gen_checker.ploter)...", "STEP")
    try:
        import numpy as np
        from flash.input_gen.gen_checker.ploter import PulsePlotter, DensityPlotter

        # (a) 激光脉冲时间-功率曲线 (ed_time_1_* / ed_power_1_*, s / W)
        tsec = sorted((int(k.rsplit("_", 1)[1]), v)
                      for k, v in tmp_params.items() if k.startswith("ed_time_1_"))
        psec = sorted((int(k.rsplit("_", 1)[1]), v)
                      for k, v in tmp_params.items() if k.startswith("ed_power_1_"))
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

        # (b) 初始密度分层 (GridBuilder 均匀采样 + 区域边界标注)
        xs, dens1d, _ = builder.sample_1d(n_points=4000)
        bounds = [("shld", 0.0), ("samp", delta_cm), ("tar1", L1),
                  ("samp", L1 + delta_cm), ("tar2", L2), ("samp", L2 + delta_cm),
                  ("tar3", L3), ("samp", L3 + delta_cm),
                  ("tar4", L4), ("samp", L4 + delta_cm),
                  ("tar6", L6), ("samp", L6 + delta_cm),
                  ("end", L6 + delta_cm + D)]
        DensityPlotter().plot_1d(
            xs, dens1d, region_boundaries=list(bounds),
            title=f"Initial Density Layers ({SCENE_NAME}, pure {MAT_LABEL})",
            save_path=INPUT_DIR / "pre_diag_initial_density.png")
        log(f"    pre_diag_initial_density.png ✓")
        result["pre_diag_density"] = str(INPUT_DIR / "pre_diag_initial_density.png")
    except Exception as exc:  # noqa: BLE001
        log(f"预诊断图生成失败 (不影响仿真): {exc}", "WARN")

    log(f"  输入文件总数: {len(result)}", "OK")
    return result


# ── 分析: 数据提取助手 (经 flash/output_processors, 默认 yt 模式) ──
def _load_leaf_profile(plt_path: Path, var: str = "dens"):
    """经 flash.output_processors 提取单变量剖面 (叶子块, 默认 yt 模式)。

    使用 FlashDataLoader.load(extraction_mode="yt") — 该路径走
    FlashHDF5File.extract_var_with_yt，只取 node_type==1 的叶子块。
    注意: 不带 extraction_mode 的默认 load() 走 read_var，不过滤非叶子
    父块，在物性界面会产生陈旧粗网格混合值伪影，勿用于剖面分析。

    Returns:
        (time_s, x_cm, values)；读取失败返回 (0.0, None, None)。
    """
    import numpy as np
    from flash.output_processors.loader import FlashDataLoader
    try:
        c = FlashDataLoader(str(plt_path)).load(
            compute_derived=False, extraction_mode="yt")
        x = np.asarray(c.x).ravel()
        v = c.data.get(var)
        if v is None or x.size == 0:
            return 0.0, None, None
        return float(c.simulation_time), x, np.asarray(v).ravel()
    except Exception as exc:  # noqa: BLE001
        log(f"    读取失败 {plt_path.name}: {exc}", "WARN")
        return 0.0, None, None


# ── 分析: dens 时空图 ─────────────────────────────────────
def plot_density_timespace(outdir: Path, save_path: Path) -> int:
    """读取全部 plt HDF5，制作 dens(x,t) 时空彩图。

    Returns:
        成功写入的 plt 文件数。
    """
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt_files = sorted(outdir.glob("*plt_cnt*")) or sorted(outdir.glob("*plt*"))
    # 排除 tmax 强制输出的 "forced" 帧，避免打乱时间顺序
    plt_files = [f for f in plt_files if "forced" not in f.name]
    if not plt_files:
        log(f"无 plt 文件: {outdir}", "WARN")
        return 0

    records: List[tuple] = []
    xmin = xmax = None
    for f in plt_files:
        t, x, d = _load_leaf_profile(f, "dens")
        if x is None or x.size == 0 or d.size == 0:
            continue
        if xmin is None or x.min() < xmin:
            xmin = x.min()
        if xmax is None or x.max() > xmax:
            xmax = x.max()
        records.append((float(t), x, d))

    if xmin is None or not records:
        log("未能读取密度剖面", "WARN")
        return 0
    if len(records) < 2:
        log(f"仅 {len(records)} 个非 forced plt 帧 (tmax 极小验证运行的正常情况), "
            "单帧无法构成时空图, 跳过 dens_timespace.png", "WARN")
        return len(records)

    # 按仿真时间升序排列
    records.sort(key=lambda r: r[0])
    times = [r[0] for r in records]

    # 公共 x 网格：取所有帧的最大分辨率长度，插值对齐后组 2D 数组
    x_common = np.linspace(xmin, xmax, 4096)
    dens = np.empty((len(records), x_common.size))
    for i, (_, x_i, d_i) in enumerate(records):
        dens[i] = np.interp(x_common, x_i, d_i, left=np.nan, right=np.nan)

    dens_log = np.log10(np.maximum(dens, 1.0e-30))

    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 6))
    t = np.asarray(times)
    X, T = np.meshgrid(x_common, t)
    pc = ax.pcolormesh(X * 1e4, T * 1e9, dens_log, shading="auto", cmap="viridis")
    cbar = fig.colorbar(pc, ax=ax)
    cbar.set_label(r"$\log_{10}(\rho)$ [g/cm$^3$]")
    ax.set_xlabel(r"x [$\mu$m]")
    ax.set_ylabel("t [ns]")
    ax.set_title(f"Density x-t map ({SCENE_NAME})")
    fig.tight_layout()
    fig.savefig(str(save_path), dpi=150)
    plt.close(fig)
    log(f"    {save_path.name} ✓ ({len(plt_files)} plt files)")
    return len(plt_files)


# ── 分析: 不同时刻密度剖面线图 ────────────────────────────
def plot_density_profiles(outdir: Path, save_path: Path,
                          zoom_range=(-5.0, 10.0)) -> int:
    """读取全部 plt HDF5，绘制不同时刻的密度空间分布线图。

    布局: 左 = 全域总览; 右 = x∈zoom_range (um) 局部放大。
    对数 y 轴密度 (g/cm^3)，线性 x 轴位置 (um)，
    线颜色按仿真时间渐变 (viridis)，用于快速判断初始场搭建是否正确。

    Returns:
        成功读取的 plt 文件数。
    """
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # PPT 级绘图规范: 全英文 + 大字号 + 粗线 + 高分辨率
    plt.rcParams.update({
        "font.size": 20, "axes.titlesize": 24, "axes.labelsize": 22,
        "xtick.labelsize": 20, "ytick.labelsize": 20, "legend.fontsize": 18,
        "axes.linewidth": 2.0, "xtick.major.width": 2.0,
        "ytick.major.width": 2.0, "font.family": "DejaVu Sans",
    })

    plt_files = sorted(outdir.glob("*plt_cnt*")) or sorted(outdir.glob("*plt*"))
    if not plt_files:
        log(f"无 plt 文件: {outdir}", "WARN")
        return 0

    records: List[tuple] = []
    for f in plt_files:
        t, x, d = _load_leaf_profile(f, "dens")
        if x is None or x.size == 0 or d.size == 0:
            continue
        records.append((float(t), x, d))
    if not records:
        log("未能读取密度剖面", "WARN")
        return 0

    # 按仿真时间升序, 颜色随时间渐变
    records.sort(key=lambda r: r[0])
    times = np.array([r[0] for r in records])
    t_min, t_span = times.min(), max(times.max() - times.min(), 1.0e-30)
    cmap = plt.get_cmap("viridis")

    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(17, 6.5), constrained_layout=True)
    for ax, xlim, title in (
        (axes[0], None, "Full domain"),
        (axes[1], zoom_range, f"Zoom x = [{zoom_range[0]:.0f}, {zoom_range[1]:.0f}] " + r"$\mu$m"),
    ):
        for (t, x, d) in records:
            frac = 0.05 + 0.90 * (t - t_min) / t_span
            m = d > 0
            ax.semilogy(x[m] * 1e4, d[m], lw=2.2, color=cmap(frac),
                        label=f"t = {t * 1e9:.4g} ns")
        ax.set_xlabel(r"x [$\mu$m]")
        ax.set_ylabel(r"Density [g/cm$^3$]")
        ax.set_title(title)
        ax.set_xlim(xlim)
        ax.grid(True, which="both", alpha=0.25, lw=0.8)
    # 图例只放右图 (时间条目相同, 避免重复)
    axes[1].legend(loc="upper left", fontsize=16, framealpha=0.9, ncol=2)
    fig.suptitle(f"Density profiles at different times ({SCENE_NAME})",
                 fontsize=24, fontweight="bold")
    fig.savefig(str(save_path), dpi=450)
    plt.close(fig)
    log(f"    {save_path.name} ✓ ({len(records)} plt files)")
    return len(records)


# ── 分析: 物种标记空间分布 (局部放大, 线性 y 轴) ──────────
def plot_species_zoom(outdir: Path, save_path: Path,
                      zoom_range=(-5.0, 10.0),
                      species=None) -> int:
    """读取叶子块物种质量分数，绘制局部放大 (默认 [-5,10] µm) 的
    各物种 (cham/shld/samp/tar1/tar2) 空间分布，线性 y 轴。

    快速核对多薄层物种标记初始化是否正确——每个空间位置应恰有
    一个物种为 1 (纯 cells 0/1 阶跃)；tar1/tar2/tar3/tar4/tar6 分别在
    L1/L2/L3/L4/L6 处厚度 delta 的薄层内为 1。

    Returns:
        成功读取的 plt 文件数。
    """
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if species is None:
        species = tuple(SPECIES_LIST)

    plt.rcParams.update({
        "font.size": 20, "axes.titlesize": 24, "axes.labelsize": 22,
        "xtick.labelsize": 20, "ytick.labelsize": 20, "legend.fontsize": 18,
        "axes.linewidth": 2.0, "xtick.major.width": 2.0,
        "ytick.major.width": 2.0, "font.family": "DejaVu Sans",
    })

    plt_files = sorted(outdir.glob("*plt_cnt*")) or sorted(outdir.glob("*plt*"))
    if not plt_files:
        log(f"无 plt 文件: {outdir}", "WARN")
        return 0

    colors = {"cham": "tab:blue", "shld": "tab:green", "samp": "tab:red",
              "tar1": "tab:purple", "tar2": "tab:orange", "tar3": "tab:brown",
              "tar4": "tab:olive", "tar6": "tab:pink"}
    styles = {"cham": "-", "shld": "--", "samp": "-",
              "tar1": "-.", "tar2": ":", "tar3": (0, (3, 1, 1, 1)),
              "tar4": (0, (5, 1)), "tar6": (0, (1, 1))}

    from flash.output_processors.loader import FlashDataLoader
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(13, 6.5), constrained_layout=True)
    n_read = 0
    for f in plt_files:
        try:
            c = FlashDataLoader(str(f)).load(
                compute_derived=False, extraction_mode="yt")
        except Exception as exc:  # noqa: BLE001
            log(f"    跳过 {f.name}: {exc}", "WARN")
            continue
        x = np.asarray(c.x).ravel()
        cols = {sp: np.asarray(c.data[sp]).ravel()
                for sp in species if sp in c.data}
        if x.size == 0 or not cols:
            continue
        n_read += 1
        t = float(c.simulation_time)
        m = (x * 1e4 >= zoom_range[0]) & (x * 1e4 <= zoom_range[1])
        if not np.any(m):
            continue
        for sp in species:
            if sp not in cols:
                continue
            ax.plot(x[m] * 1e4, cols[sp][m], lw=2.4, color=colors.get(sp),
                    ls=styles.get(sp, "-"),
                    label=f"{sp} (t = {t * 1e9:.4g} ns)")
    ax.set_xlabel(r"x [$\mu$m]")
    ax.set_ylabel("Mass fraction")
    ax.set_ylim(-0.05, 1.1)
    ax.set_xlim(zoom_range)
    ax.set_title(f"Species distribution, x = [{zoom_range[0]:.0f}, "
                 f"{zoom_range[1]:.0f}] " + r"$\mu$m (linear y)")
    ax.grid(True, alpha=0.3, lw=0.8)
    ax.legend(loc="center right", fontsize=17, framealpha=0.9)
    fig.suptitle(f"Species markers ({SCENE_NAME}, pure {MAT_LABEL})", fontsize=24,
                 fontweight="bold")
    fig.savefig(str(save_path), dpi=450)
    plt.close(fig)
    log(f"    {save_path.name} ✓ ({n_read} plt files)")
    return n_read


# ── 分析: 物种组分时空演化系列图 (全线性坐标) ─────────────
def plot_species_timespace(outdir: Path, save_path: Path,
                           xlim=(-20.0, 60.0)) -> int:
    """绘制 cham/shld/samp/tar1/tar2/tar3 组分随时间演化的系列时空图。

    布局: 6 个纵排面板 (每物种一个), 共享坐标轴。
    全部线性坐标: y = 时间 [ns], x = 位置 [um], 颜色 = 物种质量分数 (0-1)。

    Returns:
        成功读取的 plt 文件数。
    """
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from flash.output_processors.loader import FlashDataLoader

    plt.rcParams.update({
        "font.size": 16, "axes.titlesize": 18, "axes.labelsize": 17,
        "xtick.labelsize": 15, "ytick.labelsize": 15,
        "axes.linewidth": 1.8, "font.family": "DejaVu Sans",
    })

    plt_files = sorted(outdir.glob("*plt_cnt*"))
    plt_files = [f for f in plt_files if "forced" not in f.name]
    if len(plt_files) < 2:
        log(f"非 forced plt 少于 2 帧 ({len(plt_files)}), 跳过物种时空图", "WARN")
        return len(plt_files)

    records: List[tuple] = []
    xmin = xmax = None
    for f in plt_files:
        try:
            c = FlashDataLoader(str(f)).load(
                compute_derived=False, extraction_mode="yt")
        except Exception as exc:  # noqa: BLE001
            log(f"    跳过 {f.name}: {exc}", "WARN")
            continue
        x = np.asarray(c.x).ravel()
        if x.size == 0:
            continue
        if xmin is None or x.min() < xmin:
            xmin = x.min()
        if xmax is None or x.max() > xmax:
            xmax = x.max()
        frac = {sp: np.asarray(c.data[sp]).ravel()
                for sp in SPECIES_LIST if sp in c.data}
        records.append((float(c.simulation_time), x, frac))
    if len(records) < 2:
        log("有效帧不足, 跳过物种时空图", "WARN")
        return 0

    records.sort(key=lambda r: r[0])
    species = [sp for sp in SPECIES_LIST
               if all(sp in r[2] for r in records)]
    t = np.array([r[0] for r in records]) * 1e9          # ns
    x_common = np.linspace(xmin, xmax, 1600)             # cm
    fields = {sp: np.empty((len(records), x_common.size))
              for sp in species}
    for i, (_, x_i, frac) in enumerate(records):
        o = np.argsort(x_i)
        for sp in species:
            fields[sp][i] = np.interp(x_common, x_i[o], frac[sp][o],
                                      left=np.nan, right=np.nan)
    X_um, T_ns = np.meshgrid(x_common * 1e4, t)

    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(len(species), 1, figsize=(10, 2.6 * len(species)),
                             sharex=True, constrained_layout=True)
    axes = np.atleast_1d(axes)
    for ax, sp in zip(axes, species):
        pc = ax.pcolormesh(X_um, T_ns, fields[sp], shading="auto",
                           cmap="viridis", vmin=0.0, vmax=1.0)
        ax.set_ylabel("t [ns]")
        ax.set_title(sp, loc="left", fontsize=15, fontweight="bold")
        ax.set_xlim(xlim)
        cb = fig.colorbar(pc, ax=ax, pad=0.01)
        cb.set_label(f"{sp} fraction", fontsize=13)
    axes[-1].set_xlabel(r"x [$\mu$m]")
    fig.suptitle(f"Species fraction x-t maps ({SCENE_NAME}, linear)",
                 fontsize=18, fontweight="bold")
    fig.savefig(str(save_path), dpi=300)
    plt.close(fig)
    log(f"    {save_path.name} ✓ ({len(records)} frames, {len(species)} species)")
    return len(records)


# ── 分析统一入口 (WSL 本地) ───────────────────────────────
def analyze_local_all(outdir: Path, save_path: Path) -> int:
    """WSL 本地分析: dens 时空彩图 + 密度剖面 + 物种分布 + 物种时空系列图。"""
    n = plot_density_timespace(outdir, save_path)
    try:
        plot_density_profiles(outdir, save_path.parent / "dens_profiles.png")
    except Exception as exc:  # noqa: BLE001
        log(f"密度剖面线图生成失败: {exc}", "WARN")
    try:
        plot_species_zoom(outdir, save_path.parent / "species_zoom.png")
    except Exception as exc:  # noqa: BLE001
        log(f"物种分布放大图生成失败: {exc}", "WARN")
    try:
        plot_species_timespace(outdir, save_path.parent / "species_timespace.png")
    except Exception as exc:  # noqa: BLE001
        log(f"物种时空系列图生成失败: {exc}", "WARN")
    return n


# ── HPC 远程分析命令 ──────────────────────────────────────
def remote_analysis_cmd(outdir: str) -> str:
    """超算端绘图分析 (脚本已由 runner 上传至 analysis 目录)。"""
    return (
        "source /public1/soft/modules/module.sh >/dev/null 2>&1; "
        "module purge >/dev/null 2>&1; module load python/3.9.6 >/dev/null 2>&1; "
        "export PYTHONIOENCODING=utf-8 && "
        f"python {SCENE_NAME}_remote_analysis.py "
        f"--outdir {outdir} --save dens_timespace.png --json summary.json 2>&1"
    )


def _par_tmax_ok(tmax: float) -> bool:
    """检查已生成 par 的 tmax 与当前 cfg 一致 (相对容差 1e-12)。

    用于 --tmax 覆盖后的再生成判定: 文件齐全但 tmax 不符时也必须重新
    生成 (批量统一控制时间的关键 — 否则旧 par 的 tmax 会静默生效)。
    """
    import re as _re
    p = INPUT_DIR / PAR_FILENAME
    if not p.exists():
        return False
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _re.match(r"^\s*tmax\s*=\s*([0-9.eE+-]+)", line.split("#")[0])
        if m:
            try:
                return abs(float(m.group(1)) - tmax) <= 1e-12 * abs(tmax)
            except ValueError:
                return False
    return False


def main():
    import argparse
    ap = argparse.ArgumentParser(
        description=f"{SCENE_NAME} (纯{MAT_LABEL}多薄层, wsl/hpc 一键切换)")
    ap.add_argument(
        "action", nargs="?", default=None,
        help="hpc 分阶段动作: all/upload/submit/monitor/analyze/download/status "
             "(默认按 RUN_MODE 完整运行)",
    )
    ap.add_argument(
        "--wait", type=int, default=0, help="hpc monitor 等待秒数 (默认不阻塞轮询一次)",
    )
    ap.add_argument(
        "--tmax", type=float, default=None,
        help="覆盖仿真结束时间 (s); 默认用 config_constants 中的规范值 (1.0e-11 极短验证)",
    )
    args = ap.parse_args()

    print("\n" + "=" * 65)
    print(f" FLASH {SCENE_NAME} Simulation (pure {MAT_LABEL} multi-layer)")
    print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)
    cfg = dict(config_constants)
    if args.tmax is not None:
        cfg["tmax"] = args.tmax
        log(f"tmax 覆盖: {cfg['tmax']:.3e} s", "OK")
    print(f"\n  参数配置:")
    print(f"    域: [{cfg['xmin']}, {cfg['xmax']}] cm")
    print(f"    材质: 全固体层纯 {MAT_LABEL} (表 {MAT_TABLE}, rho={MAT_RHO}, "
          f"A={MAT_A}, Z={MAT_Z})")
    print(f"    分层: shld[0.1um] | samp | tar1@{cfg['L1_um']}um | samp | "
          f"tar2@{cfg['L2_um']}um | samp | tar3@{cfg['L3_um']}um | samp | "
          f"tar4@{cfg['L4_um']}um | samp | tar6@{cfg['L6_um']}um | samp D={cfg['D_um']}um")
    print(f"    物种(8): cham(He),shld,samp,tar1,tar2,tar3,tar4,tar6 (全 {MAT_LABEL} "
          f"{MAT_RHO}); 辐射: {'关' if RADIATION_OFF else '开'}")
    print(f"    维度: {cfg['dimension']}D, tmax={cfg['tmax']:.1e} s")
    print("=" * 65)

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from flash.input_gen.gen_checker import DependencyChecker
        missing = DependencyChecker(INPUT_DIR).missing_standard()
        if missing or not _par_tmax_ok(cfg["tmax"]):
            if missing:
                log(f"缺失 {len(missing)} 项必须文件: {missing}", "WARN")
            else:
                log("par 中 tmax 与当前配置不符, 重新生成输入文件", "INFO")
            log("调用 input_gen 生成器生成必须文件 ...", "INFO")
            generate_input_files(cfg)
        else:
            log("FLASH 仿真必须文件已就绪，无需重新生成", "OK")
    except Exception as e:
        log(f"输入文件检查/生成失败: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False

    from flash.scenarios.runner import (
        HpcRunner, HpcSpec, WslSpec, resolve_run_mode, run_wsl, user_flash_home,
    )

    if args.action:
        run_mode = "hpc"
        log(f"分阶段动作: {args.action} (hpc)", "OK")
    else:
        run_mode = resolve_run_mode(RUN_MODE)
        log(f"运行模式: {run_mode}", "OK")

    if run_mode == "wsl":
        wsl_spec = WslSpec(
            input_dir=INPUT_DIR, output_dir=OUTPUT_DIR, plots_dir=PLOTS_DIR,
            objdir=f"{SIM_USER_DIR}/{SIM_NAME}",
            analyze_local=analyze_local_all,
            flash_home=user_flash_home(),
            outputfiles_dir=OUTPUT_DIR / "outputfiles",
        )
        return run_wsl(wsl_spec, cfg)

    hpc_spec = HpcSpec(
        name=SCENE_NAME,
        input_dir=INPUT_DIR, output_dir=OUTPUT_DIR, plots_dir=PLOTS_DIR,
        objdir=f"{SIM_USER_DIR}/{SIM_NAME}", flash_home=user_flash_home(),
        work_base=f"{user_flash_home()}/AI/Aitemp",
        remote_analysis_script=f"{SCENE_NAME}_remote_analysis.py",
        remote_analysis_cmd=remote_analysis_cmd,
    )
    runner = HpcRunner(hpc_spec)
    if args.action:
        return runner.staged(args.action, wait_seconds=args.wait or None)
    return runner.all(cfg)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
