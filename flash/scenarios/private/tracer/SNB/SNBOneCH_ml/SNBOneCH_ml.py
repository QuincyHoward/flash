"""
SNBOneCH_ml 场景 — OneCH_ml 几何/材料 + SNB 非局域热传导模型
═══════════════════════════════════════════════════════════════════

由 OneCH_ml (tracer 家族) 与 SNBtest/Test/t001 (SNB 家族) 联合派生 (2026-09-08)：
几何结构、8 物种 12 区分层、材料表、激光脉冲**严格取自 OneCH_ml**
(经 import build_species_defs 同源复用)；热传导改用 **SNB 模型**
(Schurtz–Nicolaï–Busquet 非局域电子热传导, 群分辨多群实现)。

与 OneCH_ml 的唯一物理差异: 电子热传导由 local (Spitzer + flux limiter)
换为 SNB 非局域模型; 其余 (几何/物种/材料/激光/MGD 辐射/边界) 完全一致。
因此两场景输出可直接做 local vs nonlocal 热输运对比。

**必须在 SNB 专用 FLASH 代码 (FLASHSNB) 中编译运行** — SNB 物理由
SimulationMain 单元内 9 个覆盖文件承载 (setup 的 Simulation 单元后置
覆盖机制替换 physics 同名文件), 常用场景 FLASH 无这些文件:

    diff_advanceTherm.F90            # SNB 群分辨热流 (QENL/QESH/GRQX...)
    mgd_qesh.F90                     # 多群 SH 热流权重 (不完全伽马积分)
    Conductivity.F90                 # 增强泛型 Conductivity (fullState)
    Driver_evolveFlash.F90           # SNB 驱动循环
    Grid_advanceDiffusion.F90        # SNB 扩散推进
    hy_uhd_DataReconstructNormalDir_PPM.F90 / hy_uhd_dataReconstOneStep.F90 /
    hy_uhd_getRiemannState.F90 / hy_uhd_ragelike.F90   # slopeLimiters 模块名修正

以上 9 个文件部署时从 WSL FLASHSNB 的 SNB_1D_laser 单元**原样复制**
(与物种无关, 已核查无 sim_/Simulation_data 引用), 不入库 (License §3)。

  * 1D 笛卡尔域 x=[-0.04, 0.01] cm，FLASH_3T
  * ★ 网格: +ug 均匀网格为默认 (SNB 铁律, 2026-09-08 实测: 同几何 +ug 全档
    稳定跑通 1e-10 而 AMR lrefine9 必炸)。+ug 只建 iProcs 块 level-1 网格
    (par nblockx/lrefine 被无视), dx=域宽/(iProcs*nxb), 且 nproc 必须严格
    等于 iProcs (块数≠进程数 → Logfile_open io_status=29 + MPI_Abort)。
    默认 nxb=128, iProcs=131 → dx=500um/(131*128)=0.0298 um ≤ 0.03 um
    (薄层 0.1um 分辨需求; 1042 进程 @nxb=16 等分辨率配置超出 NC-E 192 核,
    大块少进程是唯一同时适配两超算的方案)。0.1um 薄层在 dx 0.03um 下仅
    ~3 格点。AMR 降级为 --amr 可选项 (历史基线, objdir/basenm 独立)。
  * 单光束 0.351um 激光（透镜 x=-1.0，靶 x=0），82 点功率脉冲
  * 8 物种 12 区分层（delta=0.1um, L1=1um, L2=2um, L3=3um, L4=4um,
    L6=6um, D=50um; 示踪层间距均为 samp）— 同 OneCH_ml:

      x < 0                        cham [氦 He, 1e-6 g/cm^3]
      0        < x < delta         shld [碳氢 CH, 1.0 g/cm^3]
      delta    < x < L1            samp [碳氢 CH, 1.0 g/cm^3]
      L1       < x < L1+delta      tar1 [碳氢 CH]  ← 示踪薄层 1
      ... (tar2@L2, tar3@L3, tar4@L4, tar6@L6, 同 OneCH_ml)
      L6+delta < x < L6+delta+D    samp [碳氢 CH]
      其余                          cham [氦 He]

  * 8 物种标记: cham/shld/samp/tar1/tar2/tar3/tar4/tar6 (全 CH 固体层
    1.0 g/cm^3, 290.11375 K; cham 为 He 1e-6)
  * MGD 10 能群辐射，tabular EOS/opacity (ionmix4)
  * SNB 运行参数 (取自 t001 SNB 基线): useDIffuseTherm=.true.,
    diff_eleFlMode=fl_harmonic, diff_eleFlCoef=0.06, cfl=0.2;
    plot 输出 SNB 诊断变量 QESH/QESX/QESY/GRQX/GRAQ/CORQ/MFPE/QENL

用法:
  cd <flash 包目录>
  python -m flash.scenarios.private.tracer.SNB.SNBOneCH_ml.SNBOneCH_ml
      默认: 生成输入 → 部署 → setup → make → 运行 → 收集 (WSL FLASHSNB)
  python -m ... SNBOneCH_ml --generate-only      # 只生成 FLASHSNB 输入文件
  python -m ... SNBOneCH_ml                      # 一键全默认 (ug, dx≈0.0298um, tmax=2e-10)
  python -m ... SNBOneCH_ml --tmax 1.0e-11       # 覆写 tmax (首跑验证规范)
  python -m ... SNBOneCH_ml --skip-setup --skip-make   # 复用已编译 flash4
  python -m ... SNBOneCH_ml --nproc 131          # MPI 进程数 (=par iProcs, +ug 强制相等)
  python -m ... SNBOneCH_ml --probe-cores 4,8,16,24 --probe-tmax 2.0e-10
  python -m ... SNBOneCH_ml --amr                # 历史基线: AMR lrefine9 (需重编译)
"""

import sys
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# 统一 stdout/stderr 为 UTF-8，避免 GBK 控制台报错
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ── Bootstrap: 定位 flash 包根目录 ─────────────────────────
_ROOT = Path(__file__).resolve().parent
for _ in range(15):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _get_sim_user_dir() -> str:
    from flash.scenarios.runner import get_sim_user_dir as _sud
    return _sud()


SIM_USER_DIR = _get_sim_user_dir()

# ── 可配置参数 (几何/材料/激光严格同 OneCH_ml) ─────────────
config_constants = {
    # 分层几何 (μm): 同 OneCH_ml
    "delta_um": 0.1,
    "L1_um": 1.0,
    "L2_um": 2.0,
    "L3_um": 3.0,
    "L4_um": 4.0,
    "L6_um": 6.0,
    "D_um": 50.0,
    # 仿真结束时间 (s)。首跑验证用 --tmax 1.0e-11; 平台核数探测与
    # 正式 +ug 运行默认 2.0e-10 (2026-09-08 用户设定)。
    "tmax": 2.0e-10,
    # 仿真域 (cm), 同 OneCH_ml
    "xmin": -0.04,
    "xmax": 0.01,
    # ★ 网格: +ug 均匀网格默认 — dx = 域宽/(iprocs*nxb)
    #   0.03um 目标 (薄层 0.1um): 需 iprocs*nxb ≥ 500um/0.03um = 16,667
    #   → nxb=128, iprocs=131 (dx=0.0298um, 131 核; nxb=16 需 1042 核超 NC-E)
    "nxb": 128,
    "iprocs": 131,
    # (--amr 历史基线用: AMR 网格参数, +ug 下被无视)
    "nblockx": 8,
    "lrefine_max": 9,
    "lrefine_min": 1,
    "lrefine_min_init": 9,
    # 输出频率 (同 OneCH_ml)
    "plot_interval_step": 2000,
    "checkpoint_interval_step": 400,
    # 维度
    "dimension": 1,
    # MPI 进程数 (=par iProcs, +ug 下必须严格等于块数; --nproc 可覆写)
    "nprocs": 131,
    # SNB 热传导基线参数 (取自 t001 flash.par, SNB 使用方法)
    "diff_eleFlMode": "fl_harmonic",
    "diff_eleFlCoef": 0.06,
    "cfl": 0.2,   # 0.1 试跑无效 (t≈8.9e-11 仍爆) → 回退 0.2 基线 (2026-09-08)
    # 初始温度 [K] (全物种统一; 290.11375=室温基线; --t-init 可覆写,
    # 3500K 实验: 提高低密度 He 格点内能储备, 尝试规避 1e-10 负内能失稳)
    "t_initial": 290.11375,
    # CH 物种 EOS/opacity 表。★ 实测 2026-09-08: CH-QC-1-001 温度网格下限
    # 2.0 eV (~23,200 K), 室温初值 0.025 eV 在表外 (EOS 钳位, 物理不严格);
    # CH/He-BADGER 下限 0.01 eV 覆盖室温且 10 群一致 — 但换 BADGER 后启动瞬态
    # 更早发散 (l9: 4.4e-12, l8: 7.9e-13, l7: 2.3e-11, 全部 < 1e-11 冒烟线),
    # QC 钳位客观上起阻尼作用 (l9 存活至 8.9e-11)。故工作基线暂留 QC;
    # 启用 BADGER 需先解决 He|CH 界面启动瞬态 (过渡区/初压平衡)。
    "ch_cn4": "CH-QC-1-001.cn4",   # 工作基线 (启动稳定); BADGER 见下方注释
    # 运行控制 (+ug 基线, t001 实证: 1.10/2e-12 下 1e-10 全档稳定)。
    # (--amr 历史基线才需要 1.05/2e-14 收紧稳定化, 见 --amr 分支)
    "tstep_change_factor": 1.10,
    "dtmax": 2.0e-12,
}

# FLASH setup 标志 (FLASHSNB) — ★ 默认 +ug 均匀网格 (SNB 铁律)
SETUP_FLAGS_UG = (
    "-1d +cartesian +ug -nxb=128 +hdf5typeio "
    "species=cham,shld,samp,tar1,tar2,tar3,tar4,tar6 "
    "+mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 "
    "ed_maxPulseSections=300"
)
SETUP_FLAGS = SETUP_FLAGS_UG      # 默认 = +ug (--amr 时运行期切换为 AMR)

# --amr 历史基线 (lrefine9 精细网格; dx≈0.0153um, 需 tstep1.05/dtmax2e-14)
SETUP_FLAGS_AMR = (
    "-1d +cartesian -nxb=16 +hdf5typeio "
    "species=cham,shld,samp,tar1,tar2,tar3,tar4,tar6 "
    "+mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 "
    "ed_maxPulseSections=300 -maxblocks=4096"
)

# 仿真/对象/par 命名 (+ug 默认 / AMR 可选, objdir/basenm 隔离互不覆盖)
SIM_NAME = "SNBOneCH_ml"          # FLASHSNB 内 SimulationMain 单元名
OBJDIR = "SNBOneCH_ml_ug_obj"     # setup -objdir= (+ug 默认)
OBJDIR_AMR = "SNBOneCH_ml_obj"
PAR_FILENAME = "snbonech_ml.par"
BASENM = "snbonechug_"            # 输出基名 (+ug 默认)
BASENM_AMR = "snbonech_"
LOG_FILE = "snbonech.log"

# 物种列表 (顺序即 FLASH 物种常量顺序, 同 OneCH_ml)
from flash.scenarios.private.tracer.OneCH_ml.OneCH_ml import (
    SPECIES_LIST,
    build_species_defs,
)

# 规范物理参数（沿用水脉冲/MGD 等内嵌字典, 自包含）
from flash.scenarios.private.tracer._par_layers import CH_FLASH_PAR

# ── SNB 单元覆盖文件 (部署时从 FLASHSNB SNB_1D_laser 原样复制) ──
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

# FLASHSNB 树级 physics 补丁 (t001 修复; 部署时缺失则从 t001 归档补齐)
_TREE_PATCHES = (
    ("physics/Diffuse/DiffuseMain/Diffuse_computeDt.F90",),
    ("physics/Hydro/HydroMain/unsplit/hy_uhd_getFaceFlux.F90",),
)
# t001 归档目录 (相对本场景: private/tracer/SNB/SNBOneCH_ml → private/SNB/...)
# 注意恰好 3 层 parent 到 private; 多一层会指到 scenarios/ 导致补丁归档查不到
_T001_DIR = Path(__file__).resolve().parent.parent.parent / (
    "SNB/SNBtest/Test/t001")

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

# plot_var 白名单: OneCH_ml 变量 + SNB 诊断 (QENL=非局域热流, QESH=SH 热流)
_PLOT_VARS = ["dens", "depo", "tele", "tion", "trad", "ye", "sumy",
              "cham", "shld", "samp", "tar1", "tar2", "tar3", "tar4",
              "tar6", "fllm",
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


# ── 步骤 1: 生成 FLASHSNB 输入文件 ─────────────────────────
def generate_input_files(cfg: Dict[str, Any]) -> Dict[str, str]:
    """生成全部 FLASHSNB 输入文件到 flash_input/。

    产物: snbonech_ml.par / Config / Makefile / Simulation_data.F90 /
    Simulation_init.F90 / Simulation_initBlock.F90 / 2 张 .cn4 表 /
    run_flash.sh / 预诊断图。单元内 SNB 物理覆盖文件 (9 个 .F90) 在
    部署阶段从 FLASHSNB SNB_1D_laser 单元复制, 不落盘本目录。
    """
    from flash.input_gen.gen_par import ParGeneratorExtended
    from flash.input_gen.gen_config import ConfigGenerator
    from flash.input_gen.gen_sim_data import SimDataGenerator
    from flash.input_gen.gen_sim_init import SimInitGenerator
    from flash.input_gen.gen_sim_initblock import BlockGenerator, GridBuilder

    delta_cm = cfg["delta_um"] * 1e-4
    L1 = cfg["L1_um"] * 1e-4
    L2 = cfg["L2_um"] * 1e-4
    L3 = cfg["L3_um"] * 1e-4
    L4 = cfg["L4_um"] * 1e-4
    L6 = cfg["L6_um"] * 1e-4
    D = cfg["D_um"] * 1e-4

    species_defs = build_species_defs(delta_cm, L1, L2, L3, L4, L6, D)
    sim_path = SIM_NAME          # FLASHSNB 内单元: SimulationMain/SNBOneCH_ml
    par_filename = PAR_FILENAME

    from flash.scenarios.runner import default_nprocs
    nprocs = cfg["nprocs"] or default_nprocs(cfg["dimension"], is_hpc=False)

    result: Dict[str, str] = {}
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. par（CH_FLASH_PAR 基线 + SNB 覆写）───────────────
    log("  [1/8] 生成 .par 文件 (SNB 基线)...", "STEP")
    tmp_params = dict(CH_FLASH_PAR)
    # 同 OneCH_ml: 剔除 targ 物种专属键与未用几何键 (不能用 "targ" in k
    # 模糊匹配 — 会误删激光 ed_targetX_1)。
    _TARG_KEYS = {
        "sim_targetRadius", "sim_targetHeight",
        "sim_rhoTarg", "sim_teleTarg", "sim_tionTarg", "sim_tradTarg",
        "ms_targA", "ms_targZ", "ms_targZMin",
    }
    for k in list(tmp_params):
        if k in _TARG_KEYS or k.startswith(("op_targ", "eos_targ")) \
                or k == "sim_sampRadius" \
                or k in ("basenm", "log_file") \
                or k.startswith("plot_var"):
            del tmp_params[k]
    par_gen = ParGeneratorExtended(simulation_name=SIM_NAME, dimension=1)
    par_gen._params.clear()
    for k, v in tmp_params.items():
        par_gen.set(k, v)
    # 覆写: 几何与材料 (与 OneCH_ml 完全一致; 分层几何经运行时参数控制)
    #   [0, shldR] shld | [shldR, tar1R] samp | [tar1R, tar1R+shldR] tar1 |
    #   [tar1R+shldR, tar2R] samp | [tar2R, tar2R+shldR] tar2 |
    #   [tar2R+shldR, tar3R] samp | [tar3R, tar3R+shldR] tar3 |
    #   [tar3R+shldR, tar4R] samp | [tar4R, tar4R+shldR] tar4 |
    #   [tar4R+shldR, tar6R] samp | [tar6R, tar6R+shldR] tar6 |
    #   [tar6R+shldR, tar6R+shldR+sampH] samp | 其余 cham
    par_gen.set("sim_shldRadius", delta_cm)             # delta
    par_gen.set("sim_tar1Radius", L1)                   # L1
    par_gen.set("sim_tar2Radius", L2)                   # L2
    par_gen.set("sim_tar3Radius", L3)                   # L3
    par_gen.set("sim_tar4Radius", L4)                   # L4 = 4.0e-4 cm
    par_gen.set("sim_tar6Radius", L6)                   # L6 = 6.0e-4 cm
    par_gen.set("sim_sampHeight", D)                    # D
    par_gen.set("sim_rhoShld", 1.0)
    par_gen.set("eos_shldTableFile", cfg["ch_cn4"])
    par_gen.set("op_shldFileName", cfg["ch_cn4"])
    par_gen.set("eos_sampTableFile", cfg["ch_cn4"])
    par_gen.set("op_sampFileName", cfg["ch_cn4"])
    # 初始温度覆写 (CH_FLASH_PAR 基线为室温 290.11375; cfg["t_initial"] 可调,
    # 注意 par 里的 sim_tele*/tion*/trad* 与 initBlock 的 builder.set_material
    # 是两套来源 — 运行时真正生效的是这里的 par 参数)
    for _zone in ("Cham", "Shld", "Samp"):
        par_gen.set(f"sim_tele{_zone}", cfg["t_initial"])
        par_gen.set(f"sim_tion{_zone}", cfg["t_initial"])
        par_gen.set(f"sim_trad{_zone}", cfg["t_initial"])
    for _tar in ("Tar1", "Tar2", "Tar3", "Tar4", "Tar6"):
        par_gen.set(f"sim_tele{_tar}", cfg["t_initial"])
        par_gen.set(f"sim_tion{_tar}", cfg["t_initial"])
        par_gen.set(f"sim_trad{_tar}", cfg["t_initial"])
    for tar in ("tar1", "tar2", "tar3", "tar4", "tar6"):
        par_gen.set(f"eos_{tar}EosType", "eos_tab")
        par_gen.set(f"eos_{tar}SubType", "ionmix4")
        par_gen.set(f"eos_{tar}TableFile", cfg["ch_cn4"])
        par_gen.set(f"op_{tar}Absorb", "op_tabpa")
        par_gen.set(f"op_{tar}Emiss", "op_tabpe")
        par_gen.set(f"op_{tar}Trans", "op_tabro")
        par_gen.set(f"op_{tar}FileType", "ionmix4")
        par_gen.set(f"op_{tar}FileName", cfg["ch_cn4"])
    # 覆写: 网格 (AMR 模式; 注: 网格间距公式
    #   res = dir_delta/(nxb*nblock*2^(lrefine-1))
    #   = 0.05/(16*8*2^8) ≈ 1.53e-6 cm ≈ 0.0153 um @ lrefine 9)
    par_gen.set("nblockx", cfg["nblockx"])
    par_gen.set("lrefine_max", cfg["lrefine_max"])
    par_gen.set("lrefine_min", cfg["lrefine_min"])
    par_gen.set("lrefine_min_init", cfg["lrefine_min_init"])
    par_gen.set("refine_var_1", "dens")
    par_gen.set("refine_var_2", "tele")
    # 覆写: 运行控制
    par_gen.set("tmax", cfg["tmax"])
    par_gen.set("plotFileIntervalStep", cfg["plot_interval_step"])
    par_gen.set("checkpointFileIntervalStep", cfg["checkpoint_interval_step"])
    # 覆写: 输出命名 (SNB 场景独立基名, 避免与 OneCH_ml 输出混淆)
    par_gen.set("basenm", BASENM)
    par_gen.set("log_file", LOG_FILE)
    # 覆写: SNB 热传导基线 (t001 flash.par — SNB 使用方法)
    par_gen.set("useDIffuseTherm", True)     # Diffuse 单元热传导开关 (SNB 必需)
    par_gen.set("diff_eleFlMode", cfg["diff_eleFlMode"])   # fl_harmonic
    par_gen.set("diff_eleFlCoef", cfg["diff_eleFlCoef"])   # 0.06
    par_gen.set("cfl", cfg["cfl"])                          # 0.2 (SNB 基线)
    par_gen.set("use_3dFullCTU", True)       # t001 SNB 基线
    par_gen.set("eos_maxNewton", 5000)       # t001 SNB 基线
    # 覆写: 启动瞬态稳定化 (实测必要 — 否则 He|CH 界面发散, 见 config_constants 注)
    par_gen.set("tstep_change_factor", cfg["tstep_change_factor"])  # 1.05
    par_gen.set("dtmax", cfg["dtmax"])                      # 2.0e-14
    # 覆写: 进程分解 (1D 沿 x; 必须与 mpiexec -n 一致)
    par_gen.set("iProcs", nprocs)
    # 覆写: plotfile 输出变量白名单 (OneCH_ml 变量 + SNB 诊断变量)
    for i, v in enumerate(_PLOT_VARS, start=1):
        par_gen.set(f"plot_var_{i}", f"{v:<4s}")
    par_path = par_gen.save(str(INPUT_DIR / par_filename))
    result["par"] = str(par_path)
    log(f"    .par → {par_path.name} ✓ (iProcs={nprocs})")

    # ── 2. Config（8 物种注册 + 18 个 SNB VARIABLE）─────────
    log("  [2/8] 生成 Config (8 species + SNB variables)...", "STEP")
    cfg_path = ConfigGenerator().save(
        str(INPUT_DIR / "Config"), simulation_path=sim_path, species_defs=species_defs,
    )
    # 追加 SNB 诊断 VARIABLE 段 (ConfigGenerator 不含 SNB 变量)
    txt = cfg_path.read_text(encoding="utf-8", newline="\n")
    cfg_path.write_text(txt.rstrip("\n") + "\n" + SNB_CONFIG_VARIABLES,
                        encoding="utf-8", newline="\n")
    result["config"] = str(cfg_path)
    log(f"    Config ✓ (+{SNB_CONFIG_VARIABLES.count('VARIABLE')} SNB variables)")

    # ── 3. Makefile (Simulation 单元: Simulation_data + mgd_qesh) ──
    log("  [3/8] 生成 Makefile...", "STEP")
    mk_path = INPUT_DIR / "Makefile"
    mk_path.write_text(
        "# SNBOneCH_ml Simulation unit makefile (SNB model)\n"
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

    # ── 6. Simulation_initBlock.F90（8 物种 12 区分层, 同 OneCH_ml）──
    log("  [6/8] 生成 Simulation_initBlock.F90 (8 species, 12 regions)...", "STEP")
    builder = GridBuilder(dim=1, geometry="cartesian", domain=(cfg["xmin"], cfg["xmax"]))
    for sp in species_defs:
        builder.set_material(sp["name"], rho=sp["rho"], tele=cfg["t_initial"],
                             tion=cfg["t_initial"], trad=cfg["t_initial"])
    # 分层边界: 数值 x_range 供采样/预诊断; x_expr (参数表达式) 供
    # Simulation_initBlock 代码生成 — 几何由 .par 运行时参数控制。
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
    log("  [7/8] 复制 EOS/opacity 表...", "STEP")

    def _copy_cn4(filename: str, aliases) -> bool:
        """按 注册表别名 → eos_op_data 递归 → 旧仓库兜底 的顺序复制 .cn4。"""
        from flash.input_gen.gen_eos_op import EOSOpacityGenerator
        dst = EOSOpacityGenerator().copy_eos_file(aliases[0], INPUT_DIR)
        if dst is not None and Path(dst).exists():
            return True
        data_root = _ROOT / "flash" / "input_gen" / "gen_eos_op" / "eos_op_data"
        for cand in data_root.rglob(filename):
            shutil.copyfile(cand, INPUT_DIR / filename)
            log(f"    {filename} ← {cand.relative_to(data_root)}", "INFO")
            return True
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
        ("He-BADGER-TOPS-Final.cn4", ("he_badger",)),
        ("CH-BADGER-TOPS-Final.cn4", ("ch_badger",)),
        ("CH-QC-1-001.cn4", ("ch_qc",)),
    ):
        if not _copy_cn4(filename, aliases):
            ok_all = False
    if not ok_all:
        log("EOS/opacity 表不齐全, 终止 (FLASH 将因缺表 abort)", "ERROR")
        return result

    # ── 8. run_flash.sh (WSL 手动一键) + 预诊断图 ─────────
    log("  [8/8] 生成 run_flash.sh + 预诊断图...", "STEP")
    _write_run_flash_sh(cfg, nprocs)
    result["script_wsl"] = str(INPUT_DIR / "run_flash.sh")
    log(f"    run_flash.sh ✓")

    try:
        import numpy as np
        from flash.input_gen.gen_checker.ploter import PulsePlotter, DensityPlotter
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
        xs, dens1d, _ = builder.sample_1d(n_points=4000)
        bounds = [("shld", 0.0), ("samp", delta_cm), ("tar1", L1),
                  ("samp", L1 + delta_cm), ("tar2", L2), ("samp", L2 + delta_cm),
                  ("tar3", L3), ("samp", L3 + delta_cm),
                  ("tar4", L4), ("samp", L4 + delta_cm),
                  ("tar6", L6), ("samp", L6 + delta_cm),
                  ("end", L6 + delta_cm + D)]
        DensityPlotter().plot_1d(
            xs, dens1d, region_boundaries=list(bounds),
            title="Initial Density Layers (SNBOneCH_ml)",
            save_path=INPUT_DIR / "pre_diag_initial_density.png")
        log(f"    pre_diag_initial_density.png ✓")
        result["pre_diag_density"] = str(INPUT_DIR / "pre_diag_initial_density.png")
    except Exception as exc:  # noqa: BLE001
        log(f"预诊断图生成失败 (不影响仿真): {exc}", "WARN")

    log(f"  输入文件总数: {len(result)}", "OK")
    return result


def _write_run_flash_sh(cfg: Dict[str, Any], nprocs: int) -> None:
    """生成 run_flash.sh — WSL 手动一键流水线 (部署→setup→make→运行→收集)。

    与 py 驱动 deploy_and_run() 同逻辑; 环境变量开关:
    SKIP_SETUP / SKIP_MAKE / SKIP_DEPLOY / TMAX / NPROC。
    强制 LF 换行 (WSL bash 不接受 CRLF)。
    """
    species_csv = ",".join(SPECIES_LIST)
    setup_cmd = (
        f"./setup -auto {SIM_NAME} {SETUP_FLAGS} -objdir={OBJDIR}"
    )
    overrides = " ".join(SNB_OVERRIDE_FILES)
    sh = f"""#!/usr/bin/env bash
# SNBOneCH_ml one-click pipeline (FLASHSNB, WSL) — generated by SNBOneCH_ml.py
# Env switches: SKIP_SETUP=1 SKIP_MAKE=1 SKIP_DEPLOY=1 TMAX=1.0e-11 NPROC={nprocs}
set -u
SNB_HOME="${{SNB_HOME:-$(find "$HOME" -maxdepth 3 -type d -name FLASHSNB 2>/dev/null | head -1)/FLASH4.8}}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OBJ="$SNB_HOME/{OBJDIR}"
UNIT="$SNB_HOME/source/Simulation/SimulationMain/{SIM_NAME}"
REF_UNIT="$SNB_HOME/source/Simulation/SimulationMain/SNB_1D_laser"
NPROC="${{NPROC:-{nprocs}}}"
echo "== SNBOneCH_ml pipeline (FLASHSNB: $SNB_HOME) =="

# 0) tree-level physics patches (t001 fixes; idempotent)
if [ -z "${{SKIP_DEPLOY:-}}" ]; then
  T001="$SCRIPT_DIR/../../../SNB/SNBtest/Test/t001/source_patches"
  for rel in physics/Diffuse/DiffuseMain/Diffuse_computeDt.F90 \
             physics/Hydro/HydroMain/unsplit/hy_uhd_getFaceFlux.F90; do
    if [ ! -f "$SNB_HOME/source/$rel" ] && [ -f "$T001/$rel" ]; then
      mkdir -p "$SNB_HOME/source/$(dirname "$rel")"
      cp -f "$T001/$rel" "$SNB_HOME/source/$rel"
      echo "  patch synced: $rel"
    fi
  done

  # 1) deploy unit: generated files + SNB override files (verbatim from SNB_1D_laser)
  mkdir -p "$UNIT"
  cp -f "$SCRIPT_DIR"/Config "$SCRIPT_DIR"/Makefile \
        "$SCRIPT_DIR"/Simulation_data.F90 "$SCRIPT_DIR"/Simulation_init.F90 \
        "$SCRIPT_DIR"/Simulation_initBlock.F90 "$SCRIPT_DIR"/*.cn4 "$UNIT"/ || exit 1
  for f in {overrides}; do
    cp -f "$REF_UNIT/$f" "$UNIT/$f" || exit 1
  done
  echo "  unit deployed: $UNIT"
fi

# 2) setup
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


# ── WSL 执行助手 (run_snb.py 同模式) ───────────────────────
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
    """在 WSL $HOME 下探测 SNB 专用 FLASH 根目录 (FLASHSNB/FLASH4.8)。

    不依赖用户名拼路径、不硬编码: find -name FLASHSNB 自动定位。
    """
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
        for rel in ("physics/Diffuse/DiffuseMain/Diffuse_computeDt.F90",
                    "physics/Hydro/HydroMain/unsplit/hy_uhd_getFaceFlux.F90"):
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

        # 1) 部署单元: 生成 5 件套 + cn4 + 8 个 SNB 覆盖文件
        #    覆盖文件优先取场景 flash_input (自包含, 2026-09-08 起随场景归档),
        #    缺失时回落 SNB_1D_laser 参考单元; 显式逐文件 cp (双层展开下 for 不可用)
        log("部署 SimulationMain 单元 (SNBOneCH_ml)...", "STEP")
        cp_gen = " && ".join(
            f'( test -f {wsl_in}/{f} && cp -f {wsl_in}/{f} "{unit}/{f}" || '
            f'cp -f "{ref_unit}/{f}" "{unit}/{f}" )' for f in SNB_OVERRIDE_FILES)
        code, out = run_wsl(
            f'mkdir -p "{unit}" && '
            f'cp -f {wsl_in}/Config {wsl_in}/Makefile '
            f'{wsl_in}/Simulation_data.F90 {wsl_in}/Simulation_init.F90 '
            f'{wsl_in}/Simulation_initBlock.F90 {wsl_in}/*.cn4 "{unit}/" && '
            f'{cp_gen} && '
            f'ls "{unit}" | wc -l && echo DEPLOY_OK',
            distro, timeout=120)
        if "DEPLOY_OK" not in out:
            log(f"单元部署失败: {out[-400:]}", "ERROR")
            return False
        log(f"单元已部署: {unit} (SNB 覆盖文件优先取场景 flash_input)", "OK")

    # 2) setup
    if not skip_setup:
        setup_cmd = (f"./setup -auto {SIM_NAME} {SETUP_FLAGS} -objdir={OBJDIR}")
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
        log("setup 完成 (objdir 已生成)", "OK")
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
        # make 退出码经 if/else 落盘判定 (双层展开下 $? 不可用; 且 make 输出
        # 含 error 字样的源文件名会让 grep 误报, 不能 grep 判定)
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

    # 4) par → objdir (覆写 tmax)
    run_wsl(f'cp -f {wsl_in}/{PAR_FILENAME} {obj}/flash.par', distro, timeout=60)
    if tmax:
        run_wsl(
            f'cd {obj} && sed -i "s/^tmax.*/tmax           = {tmax}/" flash.par && '
            f'grep -n "^tmax" flash.par', distro, timeout=60)
        log(f"tmax 覆写: {tmax}", "OK")

    # 5) 运行 + 收集 (输出用后即转 flash_output/, WSL 不占空间)
    # RUN_EXIT 用 if/else 落盘 — 双层展开下 $? 会被外层 shell 提前展开为 0
    log(f"运行 FLASH: mpiexec -n {nproc} ./flash4 ...", "STEP")
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
    log(f"运行 {'成功' if ok else '异常'} (输出已收集到 flash_output/) — "
        f"WSL 运行墙钟 {_run_wall:.1f} s ({nproc} proc)", "OK" if ok else "ERROR")
    # 速度记录 (供三机对比脚本读取)
    (OUTPUT_DIR / "walltime_wsl.txt").write_text(
        f"{_run_wall:.2f}\n", encoding="utf-8", newline="\n")
    return ok


# ── HPC (超算) 执行 — run_snb_hpc.py 同模式 ────────────────
# 凭据/分区 (每账号独立; 身份一律走凭据系统, 不硬编码)
HPC_PARTITION = {"flash_ssh": "v5_192", "flash_ssh_2": "v6_384"}
ACCOUNT_TAG = {"flash_ssh": "nce", "flash_ssh_2": "bscc"}


class _HpcRemote:
    """RemoteSession 封装 (凭据动态路由; paramiko 单层 shell, $ 变量安全)。"""

    def __init__(self, account: str):
        self.account = account
        self.session = None

    def __enter__(self):
        from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession
        self.session = RemoteSession(credential_name=self.account, verbose=True)
        self.session.__enter__()
        return self

    def __exit__(self, *a):
        self.session.__exit__(*a)

    def run(self, cmd: str, timeout: int = 120):
        out, err, code = self.session.run(cmd, timeout=timeout)
        return out, err, code

    def upload(self, local: str, remote: str) -> bool:
        return self.session.upload(local, remote)

    def download(self, remote: str, local: str) -> bool:
        return self.session.download(remote, local)


def _remote_snb_home() -> str:
    return f"~/{SIM_USER_DIR}/FLASH/FLASHSNB/FLASH4.8"


def _hpc_env_block(snb_home: str, account: str) -> str:
    """sbatch 作业内环境块 (t001 实测铁律: 禁 module purge / module load 不生效,
    显式 export; NC-E 补 hdf5 运行库; BSCC 需 gcc9.3 + mpich + hdf5 全量)。"""
    h5 = ("H5LIB=$(grep -E '^HDF5_PATH[[:space:]]*=' "
          f"{snb_home}/Makefile.h | head -1 | "
          "sed 's/^HDF5_PATH[[:space:]]*=[[:space:]]*//')\n"
          '[ -n "$H5LIB" ] && export LD_LIBRARY_PATH="$H5LIB/lib:$LD_LIBRARY_PATH"\n')
    if account == "flash_ssh":
        return "# NC-E: 登录已含 oneAPI (禁 module purge); 显式补 HDF5 运行库\n" + h5
    return (
        "# BSCC-T6: gcc9.3 + mpich (mpif90 wrapper 按 PATH 选 gfortran)\n"
        "export PATH=/public1/soft/gcc/9.3.0-new/bin:/public1/soft/mpich/3.2/bin:$PATH\n"
        "export H5LIB=$(grep -E '^HDF5_PATH[[:space:]]*=' "
        f"{snb_home}/Makefile.h | head -1 | "
        "sed 's/^HDF5_PATH[[:space:]]*=[[:space:]]*//')\n"
        '[ -n "$H5LIB" ] && export LD_LIBRARY_PATH='
        '"/public1/soft/gcc/9.3.0-new/lib64:/public1/soft/miniforge/24.11/lib:'
        '$H5LIB/lib:/public1/soft/mpich/3.2/lib:$LD_LIBRARY_PATH"\n'
    )


def _hpc_detect_partition(remote: "_HpcRemote", account: str) -> str:
    """sinfo 首行可能是不可用分区 (NC-E 'all inact') → avail=up + 已知映射优先。"""
    known = HPC_PARTITION
    try:
        out, _, _ = remote.run("sinfo -s 2>/dev/null", timeout=30)
        up, default = [], None
        for line in out.splitlines():
            cols = line.split()
            if not cols or cols[0] in ("PARTITION", "AVAIL"):
                continue
            if cols[0].endswith("*"):
                default = cols[0].rstrip("*")
            if len(cols) > 1 and cols[1].startswith("up"):
                up.append(cols[0].rstrip("*"))
        if account in known and known[account] in up:
            return known[account]
        if up:
            return up[0]
        if default:
            return default
    except Exception:  # noqa: BLE001
        pass
    return known.get(account, "v5_192")


def _hpc_wait_job(remote: "_HpcRemote", job_id: str, marker: str,
                  out_glob: str, timeout: int = 3600) -> bool:
    """sacct 轮询至 COMPLETED/FAILED, 并确认 marker。

    长作业 (timeout>7200) 轮询间隔自动放宽到 60s, 减少 SSH 连接次数。"""
    interval = 20 if timeout <= 7200 else 60
    start = time.time()
    last = ""
    while time.time() - start < timeout:
        out, _, _ = remote.run(
            f"sacct -j {job_id} --format=State --noheader 2>/dev/null | head -1",
            timeout=30)
        state = out.strip().splitlines()[0] if out.strip() else ""
        if state != last:
            log(f"[作业] JobID={job_id} 状态: {state or '(无记录)'} "
                f"(已等待 {int(time.time()-start)}s)", "OK" if state == "RUNNING" else "STEP")
            last = state
        if state == "COMPLETED":
            out2, _, _ = remote.run(
                f"grep -l '{marker}' {out_glob} 2>/dev/null | head -1; "
                f"tail -6 {out_glob} 2>/dev/null", timeout=30)
            if marker in out2:
                return True
            log(f"[作业] COMPLETED 但 marker 未确认 (人工核验): {out2[-200:]}", "WARN")
            return True
        if state in ("FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL", "OUT_OF_MEMORY"):
            log(f"[作业] 失败: {state}", "ERROR")
            out3, _, _ = remote.run(f"tail -25 {out_glob} 2>/dev/null", timeout=30)
            log(f"[作业] 输出尾部:\n{out3[-1800:]}", "ERROR")
            return False
        time.sleep(interval)
    log(f"[作业] JobID={job_id} 等待超时 ({timeout}s)", "ERROR")
    return False


def run_hpc(account: str, tmax: Optional[str], nproc: int,
            skip_build: bool = False, partition: str = "",
            skip_run: bool = False, poll_timeout: int = 7200) -> int:
    """超算端到端: 连接 → 上传单元包 → sbatch(部署+setup+make) → sbatch(运行)
    → 收集。远端 FLASHSNB 源码树复用 t001 部署 (缺失时报错提示)。"""
    snb_home = _remote_snb_home()
    tag = ACCOUNT_TAG.get(account, account)
    setup_cmd = f"./setup -auto {SIM_NAME} {SETUP_FLAGS} -objdir={OBJDIR}"
    overrides = " ".join(SNB_OVERRIDE_FILES)
    deploy_dir = "~/SNBOneCH_ml_deploy"

    print("=" * 64)
    print(f" SNBOneCH_ml HPC — 账号: {account} (tag {tag})")
    print(f" 远端 FLASHSNB: {snb_home}")
    print("=" * 64)

    with _HpcRemote(account) as remote:
        out, _, _ = remote.run(
            "which sbatch >/dev/null 2>&1 && echo SBATCH_OK; echo USER=$(whoami)",
            timeout=30)
        log(f"远端: {out.strip()[:120]}", "OK")
        out, _, _ = remote.run(f"ls -d {snb_home}/setup 2>/dev/null || echo NO_SETUP",
                               timeout=30)
        if "NO_SETUP" in out:
            log(f"远端 FLASHSNB 树不存在: {snb_home} (先跑 t001 --account {account} 部署)",
                "ERROR")
            return 1
        partition = partition or _hpc_detect_partition(remote, account)
        log(f"SLURM 分区: {partition}", "OK")
        # 每节点核数 (run/probe 的 -N 必须按它算: -N 1 塞不下超单节点核数
        # 的任务 → sbatch 报 "Requested node configuration is not available")
        out, _, _ = remote.run(
            f"sinfo -h -p {partition} -o \"%c\" | head -1", timeout=30)
        try:
            cores_per_node = int(out.strip().splitlines()[0])
        except (ValueError, IndexError):
            cores_per_node = 48
        nodes = max(1, -(-nproc // cores_per_node))   # ceil
        log(f"每节点核数: {cores_per_node} → {nproc} 任务需 -N {nodes}", "OK")

        # 1) 打包 + 上传单元文件 (本场景 py 生成的 FLASHSNB 输入 + par + 表)
        pkg = INPUT_DIR / f"_snbonech_unit_{tag}.tar.gz"
        import tarfile
        unit_files = (["Config", "Makefile", "Simulation_data.F90",
                       "Simulation_init.F90", "Simulation_initBlock.F90",
                       PAR_FILENAME,
                       "He-BADGER-TOPS-Final.cn4", "CH-QC-1-001.cn4",
                       "CH-BADGER-TOPS-Final.cn4"]
                      + list(SNB_OVERRIDE_FILES))
        with tarfile.open(pkg, "w:gz") as tf:
            for f in unit_files:
                tf.add(INPUT_DIR / f, arcname=f)
        remote.run(f"mkdir -p {deploy_dir}", timeout=30)
        if not remote.upload(str(pkg), f"{deploy_dir}/unit.tar.gz"):
            log("单元包上传失败", "ERROR")
            return 1
        pkg.unlink(missing_ok=True)
        log(f"单元包已上传并解压 ({len(unit_files)} 文件)", "OK")

        # 2) 构建/部署作业 (远端 shell 单层, for 循环安全)
        env_block = _hpc_env_block(snb_home, account)
        build_sh = f"""#!/bin/bash
#SBATCH --job-name=SNB1CH_b_{tag}
#SBATCH -p {partition}
#SBATCH -N 1
#SBATCH --ntasks=8
#SBATCH --output=build_%j_out.txt
#SBATCH --error=build_%j_err.txt
set -e
{env_block}cd {deploy_dir} && tar xzf unit.tar.gz
UNIT={snb_home}/source/Simulation/SimulationMain/{SIM_NAME}
REF={snb_home}/source/Simulation/SimulationMain/SNB_1D_laser
mkdir -p "$UNIT"
cp -f Config Makefile Simulation_data.F90 Simulation_init.F90 \\
      Simulation_initBlock.F90 *.cn4 "$UNIT"/
for f in {overrides}; do
  if [ -f "$f" ]; then cp -f "$f" "$UNIT/$f" || exit 9;   # 场景自包含优先
  else cp -f "$REF/$f" "$UNIT/$f" || exit 9; fi           # 回落参考单元
done
echo UNIT_DEPLOYED $(ls "$UNIT" | wc -l)
# Makefile.h 防御: 常规树已验证版覆盖 (保留 HYPRE_PATH; 已 .wsl 备份则跳过)
NORM=~/{SIM_USER_DIR}/FLASH/FLASH4.8
if [ -f "$NORM/Makefile.h" ] && [ ! -f {snb_home}/Makefile.h.hpc_bak ]; then
  cp {snb_home}/Makefile.h {snb_home}/Makefile.h.hpc_bak
  cp "$NORM/Makefile.h" {snb_home}/Makefile.h
  echo MAKEFILE_H_FROM_NORMAL
fi
cd {snb_home} && rm -rf {OBJDIR}
{setup_cmd} > setup.log 2>&1 || {{ tail -20 setup.log; echo SETUP_FAIL; exit 2; }}
ls -d {OBJDIR} && echo SETUP_OK
cd {OBJDIR}
make hy_slopeLimiters.o Conductivity_interface.o Conductivity_fullState.o 2>&1 | tail -2
if make -j8 > make.log 2>&1; then echo MAKE_OK; else echo MAKE_FAIL; tail -25 make.log; exit 3; fi
ls -la flash4 && echo BUILD_OK
"""
        local_sh = INPUT_DIR / f"_hpc_build_{tag}.sh"
        local_sh.write_text(build_sh, encoding="utf-8", newline="\n")
        if not remote.upload(str(local_sh), f"{deploy_dir}/build.sh"):
            log("构建脚本上传失败", "ERROR")
            return 1
        local_sh.unlink(missing_ok=True)
        out, _, _ = remote.run(
            f"chmod +x {deploy_dir}/build.sh && bash -n {deploy_dir}/build.sh && "
            f"echo SCRIPT_OK", timeout=30)
        if "SCRIPT_OK" not in out:
            log(f"构建脚本校验失败: {out[-200:]}", "ERROR")
            return 1

        if skip_build:
            out, _, _ = remote.run(
                f"ls {snb_home}/{OBJDIR}/flash4 2>/dev/null || echo NO_FLASH4",
                timeout=30)
            if "NO_FLASH4" in out:
                log("--skip-build 但远端 flash4 不存在", "ERROR")
                return 1
            log("跳过构建 (复用远端 flash4)", "OK")
        else:
            log("提交构建作业 (单元部署+setup+make)...", "STEP")
            out, _, _ = remote.run(
                f"cd {deploy_dir} && sbatch build.sh 2>&1", timeout=60)
            m = re.search(r"Submitted batch job (\d+)", out)
            if not m:
                log(f"sbatch 提交失败: {out[-300:]}", "ERROR")
                return 1
            log(f"构建 JobID={m.group(1)}", "OK")
            if not _hpc_wait_job(remote, m.group(1), "BUILD_OK",
                                 f"{deploy_dir}/build_*_out.txt", timeout=3600):
                return 1

        if skip_run:
            log("--skip-run (build-only): 构建完成, 跳过运行", "OK")
            return 0

        # 3) 运行作业
        run_sh = f"""#!/bin/bash
#SBATCH --job-name=SNB1CH_r_{tag}
#SBATCH -p {partition}
#SBATCH -N {nodes}
#SBATCH --ntasks={nproc}
#SBATCH --output=run_%j_out.txt
#SBATCH --error=run_%j_err.txt
set -e
{env_block}cd {snb_home}/{OBJDIR}
rm -f {BASENM}* wsl_run_snbonech.log
cp -f {deploy_dir}/{PAR_FILENAME} flash.par
sed -i "s/^iProcs.*/iProcs = {nproc}/" flash.par
if [ -n "{tmax or ''}" ]; then
  sed -i 's/^tmax.*/tmax           = {tmax}/' flash.par
fi
date +%s.%N > _t_start
if mpiexec -n {nproc} ./flash4 > wsl_run_snbonech.log 2>&1; then
  echo RUN_EXIT=0 >> wsl_run_snbonech.log
else
  echo RUN_EXIT_NZ >> wsl_run_snbonech.log
fi
date +%s.%N > _t_end
W=$(echo "$(cat _t_end) - $(cat _t_start)" | bc -l)
echo "WALL_SECONDS=$W" >> wsl_run_snbonech.log
tail -4 wsl_run_snbonech.log
echo RUN_DONE
"""
        local_sh = INPUT_DIR / f"_hpc_run_{tag}.sh"
        local_sh.write_text(run_sh, encoding="utf-8", newline="\n")
        if not remote.upload(str(local_sh), f"{deploy_dir}/run.sh"):
            log("运行脚本上传失败", "ERROR")
            return 1
        local_sh.unlink(missing_ok=True)
        out, _, _ = remote.run(
            f"chmod +x {deploy_dir}/run.sh && bash -n {deploy_dir}/run.sh && "
            f"echo SCRIPT_OK", timeout=30)
        if "SCRIPT_OK" not in out:
            log(f"运行脚本校验失败: {out[-200:]}", "ERROR")
            return 1
        log(f"提交运行作业 (tmax={tmax or 'par 内置'}, nproc={nproc})...", "STEP")
        out, _, _ = remote.run(f"cd {deploy_dir} && sbatch run.sh 2>&1", timeout=60)
        m = re.search(r"Submitted batch job (\d+)", out)
        if not m:
            log(f"sbatch 提交失败: {out[-300:]}", "ERROR")
            return 1
        run_job = m.group(1)
        log(f"运行 JobID={run_job}", "OK")
        if not _hpc_wait_job(remote, run_job, "RUN_DONE",
                             f"{deploy_dir}/run_*_out.txt", timeout=poll_timeout):
            return 1

        # 4) 读取墙钟 + 收集输出
        out, _, _ = remote.run(
            f"cat {snb_home}/{OBJDIR}/wsl_run_snbonech.log | tail -3; "
            f"echo ---; "
            f"sacct -j {run_job} --format=Elapsed --noheader 2>/dev/null | head -1",
            timeout=30)
        log(f"运行日志尾部 + 作业 Elapsed:\n{out.strip()[:500]}", "OK")
        out_dir = OUTPUT_DIR / f"hpc_{account}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out, _, _ = remote.run(
            f"cd {snb_home}/{OBJDIR} && ls {BASENM}* wsl_run_snbonech.log 2>/dev/null; "
            f"echo LIST_END", timeout=30)
        names = [l.strip() for l in out.splitlines()
                 if l.strip() and l.strip() != "LIST_END"]
        log(f"收集 {len(names)} 个输出文件...", "STEP")
        for n in names:
            remote.run(f"cp -f {snb_home}/{OBJDIR}/{n} ~/SNB1CH_out_{n} 2>/dev/null || true",
                       timeout=30)
            if remote.download(f"~/SNB1CH_out_{n}", str(out_dir / n)):
                log(f"  ✓ {n}")
                remote.run(f"rm -f ~/SNB1CH_out_{n}", timeout=20)
            else:
                # 下载失败保留远端暂存副本, 避免文件永久丢失 (可后续手动补取)
                log(f"  ✗ {n} (远端暂存 ~/SNB1CH_out_{n} 已保留)", "WARN")
        remote.run(
            f"cd {snb_home}/{OBJDIR} && rm -f {BASENM}* wsl_run_snbonech.log _t_start _t_end",
            timeout=30)
        log(f"收集完成 → {out_dir.name}/ (远端输出已清理)", "OK")
        return 0


# ── 核数探测 (--probe-cores, wsl/hpc 双路径) ───────────────
def probe_cores_wsl(snb_home: str, distro: str, cores: List[int],
                    probe_tmax: str) -> Dict[int, float]:
    """WSL 核数探测: 每核数 sed iProcs + tmax=probe_tmax 跑一次, 返回墙钟。"""
    obj = f"{snb_home}/{OBJDIR}"
    wsl_in = wsl_path(INPUT_DIR)
    run_wsl(f'cp -f {wsl_in}/{PAR_FILENAME} {obj}/flash.par', distro, timeout=60)
    run_wsl(f'cd {obj} && sed -i "s/^tmax.*/tmax           = {probe_tmax}/" flash.par',
            distro, timeout=60)
    results: Dict[int, float] = {}
    for n in cores:
        run_wsl(f'cd {obj} && sed -i "s/^iProcs.*/iProcs = {n}/" flash.par',
                distro, timeout=60)
        log(f"探测 nproc={n} (tmax={probe_tmax}) ...", "STEP")
        t0 = time.time()
        run_wsl(
            f'cd {obj} && rm -f {BASENM}* probe_{n}.log && '
            f'if mpiexec -n {n} ./flash4 > probe_{n}.log 2>&1; then '
            f'echo PROBE_OK >> probe_{n}.log; else echo PROBE_FAIL >> probe_{n}.log; fi',
            distro, timeout=7200)
        wall = time.time() - t0
        code, out = run_wsl(f'cd {obj} && tail -2 probe_{n}.log', distro, timeout=60)
        ok = "PROBE_OK" in out or "reached max SimTime" in out
        results[n] = wall if ok else float("inf")
        log(f"  nproc={n}: {wall:.1f} s  {'OK' if ok else 'FAIL: ' + out[-120:]}",
            "OK" if ok else "ERROR")
    run_wsl(f'cd {obj} && rm -f {BASENM}*', distro, timeout=60)
    return results


def probe_cores_hpc(account: str, cores: List[int], probe_tmax: str,
                    partition: str = "") -> Dict[int, float]:
    """超算核数探测: 单 sbatch 作业内循环各核数 (ntasks=核数上限, mpiexec -n N)。"""
    snb_home = _remote_snb_home()
    tag = ACCOUNT_TAG.get(account, account)
    deploy_dir = "~/SNBOneCH_ml_deploy"
    env_block = _hpc_env_block(snb_home, account)
    nmax = max(cores)
    # 循环体 (远端单层 shell, $ 变量安全)
    loops = []
    for n in cores:
        loops.append(
            f'sed -i "s/^iProcs.*/iProcs = {n}/" flash.par\n'
            f'rm -f {BASENM}* probe_{n}.log _p0 _p1\n'
            f'date +%s.%N > _p0\n'
            f'if mpiexec -n {n} ./flash4 > probe_{n}.log 2>&1; then '
            f'echo PROBE_OK >> probe_{n}.log; else echo PROBE_FAIL >> probe_{n}.log; fi\n'
            f'date +%s.%N > _p1\n'
            f'W=$(echo "$(cat _p1) - $(cat _p0)" | bc -l)\n'
            f'echo "PROBE_WALL_{n}=$W"\n'
            f'tail -2 probe_{n}.log\n')

    with _HpcRemote(account) as remote:
        partition = partition or _hpc_detect_partition(remote, account)
        # 每节点核数 → -N (超单节点的 ntasks 必须配节点数, 否则 sbatch 拒绝)
        out, _, _ = remote.run(
            f"sinfo -h -p {partition} -o \"%c\" | head -1", timeout=30)
        try:
            _cpn = int(out.strip().splitlines()[0])
        except (ValueError, IndexError):
            _cpn = 48
        probe_nodes = max(1, -(-nmax // _cpn))
        log(f"HPC 探测 [{tag}]: 分区 {partition}, {max(cores)} 任务需 -N {probe_nodes}")
        # probe_sh 必须在分区探测之后构建 (否则 #SBATCH -p 为空 → sbatch 拒绝)
        probe_sh = f"""#!/bin/bash
#SBATCH --job-name=SNB1CH_p_{tag}
#SBATCH -p {partition}
#SBATCH -N {probe_nodes}
#SBATCH --ntasks={nmax}
#SBATCH --output=probe_%j_out.txt
#SBATCH --error=probe_%j_err.txt
set -e
{env_block}cd {snb_home}/{OBJDIR}
cp -f {deploy_dir}/{PAR_FILENAME} flash.par
sed -i 's/^tmax.*/tmax           = {probe_tmax}/' flash.par
{"".join(loops)}
echo PROBE_DONE
"""
        local_sh = INPUT_DIR / f"_hpc_probe_{tag}.sh"
        local_sh.write_text(probe_sh, encoding="utf-8", newline="\n")
        remote.run(f"mkdir -p {deploy_dir}", timeout=30)
        if not remote.upload(str(local_sh), f"{deploy_dir}/probe.sh"):
            log("探测脚本上传失败", "ERROR")
            local_sh.unlink(missing_ok=True)
            return {}
        local_sh.unlink(missing_ok=True)
        out, _, _ = remote.run(
            f"chmod +x {deploy_dir}/probe.sh && bash -n {deploy_dir}/probe.sh && "
            f"echo SCRIPT_OK", timeout=30)
        if "SCRIPT_OK" not in out:
            log(f"探测脚本校验失败: {out[-200:]}", "ERROR")
            return {}
        log(f"提交核数探测作业 ({cores}, tmax={probe_tmax}, 分区 {partition})...", "STEP")
        out, _, _ = remote.run(f"cd {deploy_dir} && sbatch probe.sh 2>&1", timeout=60)
        m = re.search(r"Submitted batch job (\d+)", out)
        if not m:
            log(f"sbatch 提交失败: {out[-300:]}", "ERROR")
            return {}
        log(f"探测 JobID={m.group(1)}", "OK")
        if not _hpc_wait_job(remote, m.group(1), "PROBE_DONE",
                             f"{deploy_dir}/probe_*_out.txt", timeout=7200):
            return {}
        out2, _, _ = remote.run(
            f"grep -E 'PROBE_WALL|PROBE_OK|PROBE_FAIL|nproc|reached max' "
            f"{deploy_dir}/probe_*_out.txt 2>/dev/null", timeout=30)
        results: Dict[int, float] = {}
        for line in out2.splitlines():
            m2 = re.match(r"PROBE_WALL_(\d+)=(\S+)", line.strip())
            if m2:
                try:
                    results[int(m2.group(1))] = float(m2.group(2))
                except ValueError:
                    pass
        # probe 日志尾部已含 PROBE_OK/FAIL 检查 (wait_job 的 out2 已打印)
        remote.run(f"cd {snb_home}/{OBJDIR} && rm -f {BASENM}* _p0 _p1", timeout=30)
        for n in cores:
            log(f"  [HPC {tag}] nproc={n}: {results.get(n, float('inf')):.1f} s")
        return results


def recommend_cores(results: Dict[int, float]) -> Optional[int]:
    """从探测结果推荐最优核数 (墙钟最小且成功)。"""
    good = {n: w for n, w in results.items() if w == w and w != float("inf")}
    if not good:
        return None
    return min(good, key=good.get)


# ── 分析: 运行后快速密度剖面 (验证判读) ────────────────────
def analyze_quick(outdir: Path) -> int:
    """收集后快速分析: 全 plt 帧密度剖面 + SNB 变量非零检查。"""
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
    files = sorted(outdir.glob("*plt_cnt*"))
    if not files:
        log(f"无 plt 输出: {outdir}", "WARN")
        return 0
    # 密度剖面 (时间渐变色)
    fig, ax = plt.subplots(figsize=(13, 6.5), constrained_layout=True)
    cmap = plt.get_cmap("viridis")
    n = 0
    snb_nonzero = {}
    for f in files:
        try:
            c = FlashDataLoader(str(f)).load(compute_derived=False,
                                             extraction_mode="yt")
        except Exception as exc:  # noqa: BLE001
            log(f"    跳过 {f.name}: {exc}", "WARN")
            continue
        x = np.asarray(c.x).ravel()
        d = np.asarray(c.data.get("dens", [])).ravel()
        if x.size == 0 or d.size == 0:
            continue
        n += 1
        t = float(c.simulation_time)
        m = d > 0
        ax.semilogy(x[m] * 1e4, d[m], lw=2.2, color=cmap(0.2 + 0.7 * min(n, 5) / 5),
                    label=f"t = {t * 1e9:.4g} ns")
        # SNB 变量非零检查 (任一帧)
        for v in ("qesh", "qenl", "corq", "mfpe"):
            arr = c.data.get(v)
            if arr is not None:
                snb_nonzero[v] = max(snb_nonzero.get(v, 0.0),
                                     float(np.nanmax(np.abs(np.asarray(arr).ravel()))))
    ax.set_xlabel(r"x [$\mu$m]")
    ax.set_ylabel(r"Density [g/cm$^3$]")
    ax.set_title("Density profiles (SNBOneCH_ml)")
    ax.grid(True, which="both", alpha=0.25, lw=0.8)
    if n:
        ax.legend(loc="best", fontsize=16)
        fig.savefig(str(outdir / "dens_profiles.png"), dpi=450)
    plt.close(fig)
    log(f"    dens_profiles.png ✓ ({n} plt frames)")
    for v, mx in snb_nonzero.items():
        log(f"    SNB 变量 {v.upper()} max|.| = {mx:.3e} "
            f"{'✓ 非零' if mx > 0 else '(全零 — 检查 SNB 激活)'}")
    return n


# ── 主流程 ────────────────────────────────────────────────
def _par_tmax_ok(tmax: float) -> bool:
    """检查已生成 par 的 tmax 与当前 cfg 一致 (相对容差 1e-12)。"""
    p = INPUT_DIR / PAR_FILENAME
    if not p.exists():
        return False
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^\s*tmax\s*=\s*([0-9.eE+-]+)", line.split("#")[0])
        if m:
            try:
                return abs(float(m.group(1)) - tmax) <= 1e-12 * abs(tmax)
            except ValueError:
                return False
    return False


def _par_tinit_ok(t_init: float) -> bool:
    """检查已生成 par 的初始温度 (sim_teleCham) 与当前 cfg 一致 (相对容差 1e-9)。"""
    p = INPUT_DIR / PAR_FILENAME
    if not p.exists():
        return False
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^\s*sim_teleCham\s*=\s*([0-9.eE+-]+)", line.split("#")[0])
        if m:
            try:
                return abs(float(m.group(1)) - t_init) <= 1e-9 * max(1.0, abs(t_init))
            except ValueError:
                return False
    return False


def _par_iprocs_ok(nproc: int) -> bool:
    """检查已生成 par 的 iProcs 与运行 nproc 一致 (+ug 下块数=iProcs, 必须匹配)。"""
    pth = INPUT_DIR / PAR_FILENAME
    if not pth.exists():
        return False
    for line in pth.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^\s*iProcs\s*=\s*(\d+)", line.split("#")[0])
        if m:
            return int(m.group(1)) == nproc
    return False


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(
        description="SNBOneCH_ml: OneCH_ml 几何/材料 + SNB 模型 (FLASHSNB; wsl/hpc 一行切换)")
    ap.add_argument("--mode", default=None, choices=["wsl", "hpc"],
                    help="运行模式: wsl=本地 WSL, hpc=超算 (默认 wsl; 可用 FLASH_RUN_MODE 环境变量)")
    ap.add_argument("--account", default="flash_ssh",
                    choices=["flash_ssh", "flash_ssh_2"],
                    help="hpc 模式凭据账号 (flash_ssh=NC-E, flash_ssh_2=BSCC-T6)")
    ap.add_argument("--generate-only", action="store_true",
                    help="只生成 FLASHSNB 输入文件, 不部署/编译/运行")
    ap.add_argument("--skip-deploy", action="store_true",
                    help="跳过单元部署 (复用 FLASHSNB 内已部署单元)")
    ap.add_argument("--skip-setup", action="store_true",
                    help="跳过 setup (复用现有 objdir; 仅 wsl)")
    ap.add_argument("--skip-make", action="store_true",
                    help="跳过 make (复用现有 flash4; wsl 直通 / hpc 走 --skip-build)")
    ap.add_argument("--skip-build", action="store_true",
                    help="hpc: 跳过远端部署+setup+make (复用远端 flash4)")
    ap.add_argument("--partition", default="",
                    help="hpc: SLURM 分区 (默认按账号自动探测)")
    ap.add_argument("--tmax", default=None,
                    help="覆写仿真结束时间 (s), 如 1.0e-11 (首跑验证规范)")
    ap.add_argument("--nproc", type=int, default=None,
                    help="MPI 进程数 (默认 131; +ug 下必须等于 par iProcs=块数)")
    ap.add_argument("--distro", default="Ubuntu-22.04", help="WSL 发行版")
    ap.add_argument("--probe-cores", default=None,
                    help="核数探测: 逗号分隔候选核数 (如 4,8,16,32), "
                         "以极短 tmax 各跑一次后打印推荐核数并退出")
    ap.add_argument("--probe-tmax", default=None,
                    help="核数探测用极短结束时间 (默认 2.0e-12 s)")
    ap.add_argument("--t-init", type=float, default=None,
                    help="覆写全物种初始温度 [K] (默认 290.11375; 如 3500 稳定性实验)")
    ap.add_argument("--amr", action="store_true",
                    help="历史基线: AMR lrefine9 网格 (objdir=SNBOneCH_ml_obj, "
                         "basenm=snbonech_, tstep=1.05/dtmax=2e-14; 需重编译)。"
                         "默认 (不带本开关) 为 +ug 均匀网格 — SNB 铁律")
    ap.add_argument("--poll-timeout", type=int, default=7200,
                    help="hpc: 运行作业轮询上限秒数 (默认 7200; 长跑如 1.6ns "
                         "预计 8h+ 需显式加大, 如 43200)")
    args = ap.parse_args()

    if args.amr:
        # 运行期切换全局为 AMR 历史基线 (默认已是 +ug)
        globals()["SETUP_FLAGS"] = SETUP_FLAGS_AMR
        globals()["OBJDIR"] = OBJDIR_AMR
        globals()["BASENM"] = BASENM_AMR

    print("\n" + "=" * 65)
    print(" FLASH SNBOneCH_ml (OneCH_ml geometry + SNB model, FLASHSNB)")
    print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)
    cfg = dict(config_constants)
    if args.tmax is not None:
        cfg["tmax"] = float(args.tmax)
    if args.t_init is not None:
        cfg["t_initial"] = float(args.t_init)
    if args.amr:
        cfg.update({"tstep_change_factor": 1.05, "dtmax": 2.0e-14})
    nproc = args.nproc or cfg["nprocs"] or 4
    # par iProcs 必须与 mpiexec -n 一致 (+ug 块数=iProcs; AMR 下不匹配同样致命:
    # 实测 +ug 4块/16进程 → Logfile_open io_status=29 → MPI_Abort)
    cfg["nprocs"] = nproc
    mode = (args.mode or os.environ.get("FLASH_RUN_MODE", "wsl")).lower()
    print(f"\n  几何/材料: 同 OneCH_ml (8 物种 12 区, 域 [{cfg['xmin']}, {cfg['xmax']}] cm)")
    print(f"  模型: SNB 非局域热传导 (FLASHSNB 专用, 单元 {SIM_NAME})")
    if not args.amr:
        _dx = (cfg["xmax"] - cfg["xmin"]) / (nproc * cfg["nxb"]) * 1e4
        print(f"  网格: ★ +ug 均匀网格 (SNB 铁律) — dx=500um/({nproc}*{cfg['nxb']})"
              f"≈{_dx:.4g} um (目标 0.03um), objdir={OBJDIR}")
    else:
        print(f"  网格: AMR 历史基线 nblockx={cfg['nblockx']}, lrefine_max={cfg['lrefine_max']}"
              f", objdir={OBJDIR}")
    print(f"  模式: {mode}" + (f" / 账号 {args.account}" if mode == "hpc" else ""))
    print(f"  tmax={cfg['tmax']:.3e} s, nproc={nproc}")
    print("=" * 65)

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from flash.input_gen.gen_checker import DependencyChecker
        missing = DependencyChecker(INPUT_DIR).missing_standard()
        if missing or not _par_tmax_ok(cfg["tmax"]) \
                or not _par_tinit_ok(cfg["t_initial"]) \
                or not _par_iprocs_ok(cfg["nprocs"]):
            if missing:
                log(f"缺失 {len(missing)} 项必须文件: {missing}", "WARN")
            elif not _par_tmax_ok(cfg["tmax"]):
                log("par 中 tmax 与当前配置不符, 重新生成输入文件", "INFO")
            else:
                log(f"par 初始温度与当前配置不符 ({cfg['t_initial']:.2f} K), "
                    f"重新生成输入文件", "INFO")
            generate_input_files(cfg)
        else:
            log("FLASHSNB 输入文件已就绪, 无需重新生成", "OK")
    except Exception as e:
        log(f"输入文件检查/生成失败: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return 1

    if args.generate_only:
        log("--generate-only: 输入文件生成完毕", "OK")
        return 0

    # ── 核数探测模式 (--probe-cores): 极短 tmax 逐核数计时 → 推荐 → 退出 ──
    if args.probe_cores:
        cores = [int(c) for c in re.split(r"[,\s]+", args.probe_cores.strip()) if c]
        probe_tmax = args.probe_tmax or "2.0e-10"
        log(f"核数探测模式: cores={cores}, probe_tmax={probe_tmax}", "STEP")
        if mode == "hpc":
            with _HpcRemote(args.account) as remote:
                out, _, _ = remote.run(
                    f"ls {_remote_snb_home()}/{OBJDIR}/flash4 2>/dev/null "
                    f"|| echo NO_FLASH4", timeout=30)
            if "NO_FLASH4" in out:
                log("远端 flash4 不存在, 先执行构建 (build-only)...", "STEP")
                rc = run_hpc(args.account, tmax=None, nproc=max(cores),
                             skip_build=False, partition=args.partition,
                             skip_run=True)
                if rc != 0:
                    return rc
            results = probe_cores_hpc(args.account, cores, probe_tmax,
                                      partition=args.partition)
        else:
            snb_home = find_snb_home(args.distro)
            if not snb_home:
                log("无法定位 FLASHSNB (WSL)", "ERROR")
                return 1
            code, out = run_wsl(
                f"ls {snb_home}/{OBJDIR}/flash4 2>/dev/null || echo NO_FLASH4",
                args.distro, timeout=60)
            if "NO_FLASH4" in out:
                log(f"WSL objdir 无 flash4 ({snb_home}/{OBJDIR}), "
                    f"请先跑一次完整流程完成编译", "ERROR")
                return 1
            results = probe_cores_wsl(snb_home, args.distro, cores, probe_tmax)
        rec = recommend_cores(results)
        if rec is not None:
            log(f"★ 推荐核数: {rec} (墙钟 {results[rec]:.1f} s "
                f"@ tmax={probe_tmax})", "OK")
            print("PROBE_RESULTS=" + ", ".join(
                f"{n}:{w:.1f}s" for n, w in sorted(results.items())))
            print(f"RECOMMENDED_CORES={rec}")
            return 0
        log("探测全部失败, 无法推荐核数", "ERROR")
        return 1

    if mode == "hpc":
        return run_hpc(args.account,
                       tmax=str(args.tmax) if args.tmax else None,
                       nproc=nproc,
                       skip_build=args.skip_build or args.skip_make,
                       partition=args.partition,
                       poll_timeout=args.poll_timeout)

    snb_home = find_snb_home(args.distro)
    if not snb_home:
        log("无法定位 FLASHSNB (WSL $HOME 下 find -name FLASHSNB 无结果)", "ERROR")
        return 1
    log(f"SNB 专用 FLASH 根目录: {snb_home}", "OK")

    ok = deploy_and_run(
        snb_home, cfg, args.distro, nproc,
        tmax=str(args.tmax) if args.tmax else None,
        skip_deploy=args.skip_deploy, skip_setup=args.skip_setup,
        skip_make=args.skip_make)
    if ok:
        try:
            analyze_quick(OUTPUT_DIR)
        except Exception as exc:  # noqa: BLE001
            log(f"快速分析失败 (不影响仿真): {exc}", "WARN")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
