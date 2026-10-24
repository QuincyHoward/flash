"""
FLASH LaserSlab1D Custom Simulation v1.1
═══════════════════════════════════════════

可配置参数的一维对称域 LaserSlab 仿真。
CH 靶居中 (Z06_0.50-Z01_0.50-20260708_0850.cn4, ch_mix)，两侧真空
(Z02_1.00-20260708_0851.cn4, helium_hires)，两束 351nm 激光相向入射。
（EOS 表均来自 Gen_eos_op_data，随 Gitee 分发，不依赖 FLASH 分发原始表。）

配置文件生成 → 上传超算 → FLASH 运行 → 上传分析脚本 → 下载结果

用法:
  cd <flash 包目录>
  python -m flash.scenarios.flash_demo.new_struture.ch_center.laserslab1d_local_custom

或直接运行:
  python laserslab1d_local_custom.py

可配置参数 (修改 config_constants 字典):
  L0_um:           仿真域半宽 (μm), 默认 100
  sim_targetHeight_um: 靶半宽 (μm),  默认 30
  sim_rhoTarg:     靶密度 (g/cm^3),  默认 1.0
  peak_power:      激光峰值功率密度 (W/cm^2), 默认 5e14
  wavelength_um:   激光波长 (μm),    默认 0.351

输出:
  flash_input/     ← 完整 FLASH 输入文件
  flash_output/plots/  ← 分析结果 PNG
"""

import sys
import os
import re
import time
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

# 统一 stdout/stderr 为 UTF-8（errors="replace"），避免 GBK 控制台
# (Windows 默认代码页 936) 打印 ✓/中文时抛 UnicodeEncodeError。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")



# ── 运行模式 ─────────────────────────────────────────
# "auto"      : **默认**，按平台自适应判定（推荐）
#                  Windows 有 WSL        → wsl      （wsl.exe → bash run_flash.sh）
#                  WSL / Linux 宿主      → local    （bash run_flash.sh）
#                  HPC 登录/计算节点     → hpc-insitu（本机 sbatch）
#                  ↳ 判定表唯一实现在 flash.flash_run.execution.resolve_target
# "wsl"       : 本地 WSL 运行 FLASH（无需 SSH/超算，快速测试）
# "local"     : 本机 Linux（含 WSL 内部）直接运行，不套 wsl.exe
# "hpc-remote": 超算 RemoteSession（上传→提交→分析→下载）
# 覆盖优先级: main(mode=...) > 环境变量 FLASH_RUN_MODE > 本行 RUN_MODE
RUN_MODE = "auto"

# ── 本地分析提取模式 ────────────────────────────────
# 本地分析/绘图使用的 AMR 数据提取方案:
#   "yt":   基于 yt 库 (extract_var_with_yt, 需本地安装 yt)
#   "h5py": 纯 h5py yt 风格 (extract_var_yt_style, 无 yt 依赖)
# 一键切换即修改此行; 也可用环境变量 FLASH_EXTRACTION_MODE 覆盖
# (模式字典/优先级统一见 flash.output_processors.extraction_modes)
EXTRACTION_MODE = "yt"


# ── 路径设置 ──────────────────────────────────────────

# Bootstrap: find flash project root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))


# ── RemoteSession 导入 ───────────────────────────────
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

# ── 用户信息（统一走 runner.get_sim_user_dir）──
def _get_sim_user_dir() -> str:
    from flash.scenarios.runner import get_sim_user_dir as _sud
    return _sud()


SIM_USER_DIR = _get_sim_user_dir()

# ── 超算环境配置 ──
# FLASH 安装前缀。优先级（09-10 新增自动发现）：
#   1. 环境变量 FLASH_SIM_USER_DIR（get_sim_user_dir 已作最高优先级处理）
#   2. 凭据里的用户名 → ~/<user>/FLASH/FLASH4.8
#   3. ★ 自动扫描 $HOME —— 离线机 / 干净克隆没有 credentials.enc，
#      get_sim_user_dir() 会回落 'hello'，而实际装在别处（如 ~/QC）。
#      扫描判据：同时存在 setup 与 source/Simulation/SimulationMain。
#   4. 都找不到 ⇒ 保留原路径，由 run_flash.sh 报出可操作的错误。
try:
    from flash.scenarios.runner import discover_flash_home as _discover
    FLASH_HOME = _discover() or f"~/{SIM_USER_DIR}/FLASH/FLASH4.8"
except Exception:            # noqa: BLE001 —— 发现失败不该阻断脚本导入
    FLASH_HOME = f"~/{SIM_USER_DIR}/FLASH/FLASH4.8"

MODULES_LOAD = (
    "module purge 2>/dev/null; "
    "source /public1/soft/modules/module.sh 2>/dev/null; "
    "module load mpich/3.2-gcc9.3 2>/dev/null; "
    "module load hdf5/1.8.18 2>/dev/null"
)

# ── 可配置参数 ────────────────────────────────────────
config_constants = {
    # 仿真域 (对称域 [-L0, L0])
    "L0_um": 100,
    # 靶半宽 (CH 范围为 [-sim_targetHeight, sim_targetHeight])
    "sim_targetHeight_um": 30,
    # 靶密度 (g/cm^3), 后续作为变量
    "sim_rhoTarg": 1.0,
    # CH 原子量/序数
    "ms_targA": 6.5,
    "ms_targZ": 3.5,
    # 激光参数
    "wavelength_um": 0.351,
    "peak_power": 5e14,  # W/cm^2 (1D)
    "pulse_duration_ns": 1.0,  # 平顶时长 (ns)
    "rise_fall_ps": 40,  # 上升/下降沿 (ps)
    # 透镜位置 (±cm)
    "laser_lens_cm": 1.0,
    # 仿真时间
    "tmax_multiplier": 1.1,  # tmax = pulse_duration * multiplier
    "dtmax": 1e-12,
    # 输出频率
    "plot_interval_step": 5,
    "checkpoint_interval_step": 20,
    # 网格
    "nblockx": 4,
    "lrefine_max": 4,
    # 边界
    "xl_boundary": "outflow",
    "xr_boundary": "outflow",
    # MPI
    "nprocs": 4,
    # 分析区域 (CH 中心区域范围)
    "analysis_half_width_um": 5.0,
}

# ── 脚本路径 ──────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
INPUT_DIR = SCRIPT_DIR / "flash_input"
OUTPUT_DIR = SCRIPT_DIR / "flash_output"
PLOTS_DIR = OUTPUT_DIR / "plots"

# ── 日志工具 ──────────────────────────────────────────


def log(msg: str, level: str = "INFO"):
    tag = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]", "STEP": "[-]"}.get(level, "[i]")
    print(f"  {tag} {msg}")


# =====================================================================
# 步骤 1: 生成 FLASH 输入文件
# =====================================================================


def generate_input_files(cfg: Dict[str, Any]) -> Dict[str, str]:
    """生成所有 FLASH 输入文件。

    使用 gen_* 子包，通过 API 调用配置自定义参数。
    同时生成预诊断图 (初始密度、激光脉冲)。

    Args:
        cfg: 配置参数字典 (config_constants)

    Returns:
        {文件类型: 文件路径} 字典
    """
    from flash.input_gen.gen_par import ParGeneratorExtended
    from flash.input_gen.gen_par.generator import BeamConfig
    from flash.input_gen.gen_par.materials import Material
    from flash.input_gen.gen_config import ConfigGenerator
    from flash.input_gen.gen_makefile import MakefileGenerator
    from flash.input_gen.gen_sim_data import SimDataGenerator
    from flash.input_gen.gen_sim_init import SimInitGenerator
    from flash.input_gen.gen_sim_initblock import BlockGenerator, GridBuilder
    from flash.input_gen.gen_eos_op import EOSOpacityGenerator
    from flash.input_gen.gen_shell_script import ShellScriptGenerator
    from flash.input_gen.gen_checker.ploter import DensityPlotter, PulsePlotter

    import numpy as np

    # ── 计算物理量 ──────────────────────────────────
    L0_cm = cfg["L0_um"] * 1e-4       # μm → cm
    target_half_cm = cfg["sim_targetHeight_um"] * 1e-4
    vac_half_cm = L0_cm - target_half_cm

    pulse_total_ns = cfg["pulse_duration_ns"] + 2 * cfg["rise_fall_ps"] * 1e-3  # ns
    tmax = pulse_total_ns * 1e-9 * cfg["tmax_multiplier"]
    # `tmax_override_s`（由 main(tmax=...) 注入）：只改**终止时间**，
    # 物理设置（脉冲波形/网格/EOS/激光）逐字不变 ⇒ 跨模式对比仍属同一算例。
    _ov = cfg.get("tmax_override_s")
    if _ov:
        tmax = float(_ov)
        log(f"   tmax 覆盖为 {tmax:.3e} s（仅缩短终止时间，物理设置不变）", "WARN")

    sim_path = f"{SIM_USER_DIR}/LaserSlab_ChCenter"
    objdir = f"{SIM_USER_DIR}/LaserSlab_ChCenter"
    par_filename = "laserslab_chcenter.par"

    result: Dict[str, str] = {}

    log("=" * 50, "STEP")
    log(f"   L0 = {cfg['L0_um']} um  ({L0_cm*1e4:.0f} um)")
    log(f"   靶半宽 = {cfg['sim_targetHeight_um']} um  ({target_half_cm*1e4:.0f} um)")
    log(f"   真空 = {vac_half_cm*1e4:.0f} um  (两侧)")
    log(f"   ρ靶 = {cfg['sim_rhoTarg']} g/cm^3")
    log(f"   波长 = {cfg['wavelength_um']} um")
    log(f"   峰值功率 = {cfg['peak_power']:.1e} W/cm^2")
    log(f"   tmax = {tmax:.2e} s")

    # ── 1. ParGeneratorExtended ─────────────────────
    log("  [1/8] 生成 .par 文件...", "STEP")
    par_gen = ParGeneratorExtended(
        simulation_name="LaserSlab1d_custom",
        dimension=1,
    )

    # 域参数
    par_gen.set_domain(xmin=-L0_cm, xmax=L0_cm, nblockx=cfg["nblockx"])
    par_gen.set("lrefine_max", cfg["lrefine_max"])
    par_gen.set("lrefine_min", 1)

    # 靶材几何参数
    par_gen.set("sim_targetHeight", target_half_cm)
    par_gen.set("sim_vacuumHeight", vac_half_cm)
    par_gen.set("sim_targetRadius", 1.0)

    # 靶材物理参数
    par_gen.set("sim_rhoTarg", cfg["sim_rhoTarg"])
    par_gen.set("ms_targA", cfg["ms_targA"])
    par_gen.set("ms_targZ", cfg["ms_targZ"])
    par_gen.set("sim_teleTarg", 290.11375)
    par_gen.set("sim_tionTarg", 290.11375)
    par_gen.set("sim_tradTarg", 290.11375)

    # 腔室参数 (稀 He)
    par_gen.set("sim_rhoCham", 1e-6)
    par_gen.set("ms_chamA", 4.002602)
    par_gen.set("ms_chamZ", 2.0)
    par_gen.set("sim_teleCham", 290.11375)
    par_gen.set("sim_tionCham", 290.11375)
    par_gen.set("sim_tradCham", 290.11375)

    # EOS 文件 (ch_mix CH靶 + helium_hires 氦; 均来自 Gen_eos_op_data, 随 Gitee 分发)
    par_gen.set("eos_targEosType", "eos_tab")
    par_gen.set("eos_targSubType", "ionmix4")
    par_gen.set("eos_targTableFile", "Z06_0.50-Z01_0.50-20260708_0850.cn4")
    par_gen.set("eos_chamEosType", "eos_tab")
    par_gen.set("eos_chamSubType", "ionmix4")
    par_gen.set("eos_chamTableFile", "Z02_1.00-20260708_0851.cn4")

    # Opacity 文件
    par_gen.set("op_targAbsorb", "op_tabpa")
    par_gen.set("op_targEmiss", "op_tabpe")
    par_gen.set("op_targTrans", "op_tabro")
    par_gen.set("op_targFileType", "ionmix4")
    par_gen.set("op_targFileName", "Z06_0.50-Z01_0.50-20260708_0850.cn4")
    par_gen.set("op_chamAbsorb", "op_tabpa")
    par_gen.set("op_chamEmiss", "op_tabpe")
    par_gen.set("op_chamTrans", "op_tabro")
    par_gen.set("op_chamFileType", "ionmix4")
    par_gen.set("op_chamFileName", "Z02_1.00-20260708_0851.cn4")

    # 边界条件
    par_gen.set("xl_boundary_type", cfg["xl_boundary"])
    par_gen.set("xr_boundary_type", cfg["xr_boundary"])
    par_gen.set("diff_eleXlBoundaryType", "neumann")
    par_gen.set("diff_eleXrBoundaryType", "neumann")
    par_gen.set("rt_mgdXlBoundaryType", "vacuum")
    par_gen.set("rt_mgdXrBoundaryType", "vacuum")

    # 时间参数
    par_gen.set_time(
        tmax=tmax,
        dtinit=1e-15,
        dtmin=1e-16,
        dtmax=cfg["dtmax"],
    )
    par_gen.set("nend", 10000000)

    # 输出频率
    par_gen.set("plotFileIntervalStep", cfg["plot_interval_step"])
    par_gen.set("checkpointFileIntervalStep", cfg["checkpoint_interval_step"])

    # 绘图变量 (包含 cham, targ 用于材料追踪)
    plot_vars = ["dens", "depo", "tele", "tion", "trad", "ye", "sumy", "cham", "targ", "lase"]
    for i, v in enumerate(plot_vars, 1):
        par_gen.set(f"plot_var_{i}", v)

    # 细化变量
    par_gen.set("refine_var_1", "dens")
    par_gen.set("refine_var_2", "tele")

    # ── 脉冲设置 (两束共用同一脉冲) ────────────────
    rise_s = cfg["rise_fall_ps"] * 1e-12
    pulse_s = cfg["pulse_duration_ns"] * 1e-9
    times = [0.0, rise_s, pulse_s + rise_s, pulse_s + 2 * rise_s]
    powers = [0.0, cfg["peak_power"], cfg["peak_power"], 0.0]
    par_gen.set_pulse(times, powers)

    # ── 光束设置 (两束相向) ────────────────────────
    lens_cm = cfg["laser_lens_cm"]
    beam1 = BeamConfig(
        beam_id=1, lens_x=-lens_cm, target_x=0.0, pulse_number=1,
        wavelength=cfg["wavelength_um"], cross_section_type="uniform",
        number_of_rays=1, grid_type="regular1D", grid_radial_tics=512,
    )
    beam2 = BeamConfig(
        beam_id=2, lens_x=lens_cm, target_x=0.0, pulse_number=1,
        wavelength=cfg["wavelength_um"], cross_section_type="uniform",
        number_of_rays=1, grid_type="regular1D", grid_radial_tics=512,
    )
    par_gen.set_beams([beam1, beam2])
    par_gen.set("ed_maxRayCount", 10000)
    par_gen.set("ed_gradOrder", 2)
    par_gen.set("ed_useLaserIO", False)
    par_gen.set("ed_laserIOMaxNumberOfPositions", 10000)
    par_gen.set("ed_laserIOMaxNumberOfRays", 128)

    par_path = par_gen.save(str(INPUT_DIR / par_filename))
    result["par"] = str(par_path)
    log(f"    .par → {par_path.name} ✓")

    # ── 2. ConfigGenerator ──────────────────────────
    log("  [2/8] 生成 Config 文件...", "STEP")
    target_mat = Material(
        name="Polystyrene", file="Z06_0.50-Z01_0.50-20260708_0850.cn4",
        rho=cfg["sim_rhoTarg"], A=cfg["ms_targA"], Z=cfg["ms_targZ"],
    )
    chamber_mat = Material(
        name="Helium", file="Z02_1.00-20260708_0851.cn4",
        rho=1e-6, A=4.002602, Z=2.0,
    )
    config_gen = ConfigGenerator()
    config_path = config_gen.save(
        str(INPUT_DIR / "Config"), simulation_path=sim_path,
        target_material=target_mat, chamber_gas=chamber_mat,
    )
    result["config"] = str(config_path)
    log(f"    Config → Config ✓")

    # ── 3-5. 生成其他源文件 ────────────────────────
    log("  [3/8] 生成 Makefile...", "STEP")
    MakefileGenerator().save(str(INPUT_DIR / "Makefile"))
    result["makefile"] = str(INPUT_DIR / "Makefile")

    log("  [4/8] 生成 Simulation_data.F90...", "STEP")
    SimDataGenerator().save(str(INPUT_DIR / "Simulation_data.F90"))
    result["sim_data"] = str(INPUT_DIR / "Simulation_data.F90")

    log("  [5/8] 生成 Simulation_init.F90...", "STEP")
    SimInitGenerator().save(str(INPUT_DIR / "Simulation_init.F90"))
    result["sim_init"] = str(INPUT_DIR / "Simulation_init.F90")

    # ── 6. Simulation_initBlock.F90 (自定义 GridBuilder) ─
    log("  [6/8] 生成 Simulation_initBlock.F90 (自定义对称域)...", "STEP")
    builder = GridBuilder(dim=1, geometry="cartesian", domain=(-L0_cm, L0_cm))
    builder.set_material("cham", rho=1e-6, tele=290.11375, tion=290.11375, trad=290.11375)
    builder.set_material("targ", rho=cfg["sim_rhoTarg"], tele=290.11375, tion=290.11375, trad=290.11375)
    builder.add_region("vacuum_left", species="cham", x_range=(-L0_cm, -target_half_cm), is_target=False)
    builder.add_region("target", species="targ", x_range=(-target_half_cm, target_half_cm), is_target=True)
    builder.add_region("vacuum_right", species="cham", x_range=(target_half_cm, L0_cm), is_target=False)

    block_gen = BlockGenerator(simulation_name="LaserSlab1d_custom", sim_path=sim_path)
    block_gen.build(builder)
    block_path = block_gen.save(str(INPUT_DIR / "Simulation_initBlock.F90"))
    result["sim_initblock"] = str(block_path)
    log(f"    Simulation_initBlock.F90 ({len(builder.regions)} regions) ✓")

    # ── 7. EOS/Opacity 文件 ────────────────────────
    log("  [7/8] 复制 EOS 文件...", "STEP")
    eos_gen = EOSOpacityGenerator()
    # 使用随 Gitee 分发的自研 ionmix 表（Gen_eos_op_data/，任何克隆均有）：
    #   ch_mix        → Z06_0.50-Z01_0.50-...cn4 (C0.5-H0.5 CH 靶, ntemp=51)
    #   helium_hires  → Z02_1.00-...cn4 (纯氦, ntemp=51)
    # 不再依赖 FLASH 分发原始表（polystyrene-imx-008 / he-imx-005，*.cn4 被
    # .gitignore 排除，仓库不含，新克隆会缺失）。
    # 注意: .par 中 eos_targTableFile / op_targFileName 引用与下方文件名必须一致。
    ps_copy = eos_gen.copy_eos_file("ch_mix", str(INPUT_DIR))
    he_copy = eos_gen.copy_eos_file("helium_hires", str(INPUT_DIR))
    if ps_copy:
        result["eos_polystyrene"] = str(ps_copy)
        log(f"    {ps_copy.name} ✓")
    else:
        log("    Z06_0.50-Z01_0.50-20260708_0850.cn4 复制失败!", "ERROR")
    if he_copy:
        result["eos_helium"] = str(he_copy)
        log(f"    {he_copy.name} ✓")
    else:
        log("    Z02_1.00-20260708_0851.cn4 复制失败!", "ERROR")

    # ── 8. 运行脚本 ────────────────────────────────
    log("  [8/8] 生成运行脚本...", "STEP")
    setup_cmd = ShellScriptGenerator.build_setup_cmd(
        sim_path=sim_path, objdir=objdir, parfile=par_filename,
        flags="-1d +cartesian -nxb=16 +hdf5typeio species=cham,targ +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=6",
    )
    script_config = {
        "sim_user_dir": SIM_USER_DIR, "dimension": 1,
        "platform": "hpc/scfa2696", "setup_cmd": setup_cmd,
        "nprocs": cfg["nprocs"], "sim_path": sim_path, "object_dir": objdir,
        # FLASH_HOME 用 $HOME/<user> 形式（生成器输出为
        # FLASH_HOME="$HOME/hello/FLASH/FLASH4.8"，双引号内 $HOME 可展开；
        # 若用 ~ 会被双引号包裹而无法展开，导致目录检查失败）。
        # ★ 09-10：用上面解析出的 FLASH_HOME，不再按 SIM_USER_DIR 重新拼 ——
        #   自动发现到 ~/QC 时，凭据里的用户名仍是 'hello'，重拼会指错目录。
        "flash_home": FLASH_HOME if FLASH_HOME.startswith("$HOME/") else (
            FLASH_HOME.replace("~", "$HOME", 1)
            if FLASH_HOME.startswith("~") else FLASH_HOME
        ),
    }
    script_gen = ShellScriptGenerator(config=script_config)
    script_gen.save(str(INPUT_DIR / "run_flash.sh"), "wsl", par_file=par_filename)
    script_gen.save(str(INPUT_DIR / "submit_flash.sh"), "slurm", par_file=par_filename)
    result["script_wsl"] = str(INPUT_DIR / "run_flash.sh")
    result["script_slurm"] = str(INPUT_DIR / "submit_flash.sh")
    log(f"    run_flash.sh   ✓")
    log(f"    submit_flash.sh ✓")

    # ── 预诊断绘图 ─────────────────────────────────
    log("  绘制预诊断图...", "STEP")
    try:
        dp = DensityPlotter()
        x_sample, dens_sample, _ = builder.sample_1d(n_points=500)
        dp.plot_1d(x_sample, dens_sample,
                   region_boundaries=[("CH target", target_half_cm)],
                   title="Initial Density Distribution (1D Custom)",
                   save_path=str(INPUT_DIR / "initial_density.png"))
        log(f"    initial_density.png ✓")
    except Exception as e:
        log(f"    密度图失败: {e}", "WARN")

    try:
        pp = PulsePlotter()
        times_np = np.array(times)
        powers_np = np.array(powers)
        pp.plot_multi_pulse(
            [(times_np, powers_np), (times_np, powers_np)],
            labels=["Beam 1 (left)", "Beam 2 (right)"],
            title=f"Laser Pulse (λ={cfg['wavelength_um']}um, {cfg['peak_power']:.1e} W/cm²)",
            save_path=str(INPUT_DIR / "laser_pulse.png"),
        )
        log(f"    laser_pulse.png ✓")
    except Exception as e:
        log(f"    脉冲图失败: {e}", "WARN")

    log(f"  输入文件总数: {len(result)}", "OK")
    return result


# =====================================================================
# 步骤 2: 通过 RemoteSession 上传文件
# =====================================================================


def upload_to_hpc(session: RemoteSession, remote_dir: str) -> bool:
    """上传 flash_input/ 全部文件到超算。

    Args:
        session: RemoteSession 实例
        remote_dir: 远程目标目录

    Returns:
        True 如果全部成功
    """
    log("  [deploy] 上传文件到超算...", "STEP")
    files = [f for f in INPUT_DIR.iterdir() if f.is_file()]
    # 附加上传分析脚本（与输入文件同机制上传，确保步骤 4 可用）
    analysis_script = SCRIPT_DIR / "hpc_analyze_ch_center.py"
    if analysis_script.exists():
        files.append(analysis_script)
    success = 0
    for f in files:
        # ★ 2026-10-24：remote_path 必须是**文件全路径**（不带尾斜杠）——
        #   sftp.put 对以 "/" 结尾的目标报 OSError: Failure（实测复现，
        #   上传 0/18 全败）；旧写法 f"{remote_dir}/" 双重踩雷（另一雷是
        #   `~` 不展开，已在 main() 侧改为绝对路径）。
        ok = session.upload(str(f), f"{remote_dir}/{f.name}")
        if ok:
            success += 1
        else:
            log(f"    上传失败: {f.name}", "WARN")
    log(f"  已上传 {success}/{len(files)} 个文件到 {remote_dir}", "OK")
    return success == len(files)


# =====================================================================
# 步骤 3: 远程执行 FLASH
# =====================================================================


def run_flash_on_hpc(session: RemoteSession, remote_dir: str) -> Tuple[bool, str]:
    """通过 RemoteSession 远程执行 FLASH 仿真。

    先尝试 sbatch 提交 SLURM, 失败则降级为直接 bash run_flash.sh。

    Returns:
        (success_flag, actual_output_dir_path)
    """
    log("  [run] 远程提交 FLASH 作业...", "STEP")

    # ── 转换 .sh 换行符 ─────────────────────────
    session.run(
        f"cd {remote_dir} && sed -i 's/\\r$//' *.sh 2>/dev/null; echo CONVERT_DONE",
        timeout=10,
    )

    # ── NC-E 铁律: 可选禁用 module purge/load ────
    # QC 通用树的 Makefile.h 按 Intel MPI (-lmpi -lmpifort) 链接，MPI 库依赖
    # NC-E 默认 oneAPI 环境（无 -L 硬路径）；`module purge` + `module load
    # mpich/3.2` 会换掉 MPI 栈 ⇒ 链接期 "cannot find -lmpifort/-lmpi"
    # (2026-10-22 in-situ 冒烟两轮实测, 同 SNBOneCH_m._hpc_env_block 铁律:
    #  "NC-E 登录已含 oneAPI, 禁 module purge")。
    # FLASH_NO_MODULE_PURGE=1 时注释掉 submit_flash.sh 的**全部 module 行**，
    # 作业继承默认 oneAPI 环境（HDF5 的 -L 已硬编码在链接行）。
    if os.environ.get("FLASH_NO_MODULE_PURGE", "").strip().lower() in ("1", "true"):
        session.run(
            f"cd {remote_dir} && "
            f"sed -i 's/^module /# module (FLASH_NO_MODULE_PURGE) /' "
            f"submit_flash.sh && echo MODULES_DISABLED", timeout=10)
        log("  [run] FLASH_NO_MODULE_PURGE=1 → 已注释全部 module 行 (保留 oneAPI 默认环境)")
        # ★ 链接期补 Intel MPI 库路径: QC 树 Makefile.h 链接 -lmpi -lmpifort
        #   (Intel MPI 2022.1, 路径取自登录节点 LIBRARY_PATH 实测)；作业计算节点
        #   的链接搜索路径不含它 ⇒ 必须显式注入 LIBRARY_PATH/LD_LIBRARY_PATH。
        # ★★★ 2026-10-24 运行时符号错误修复（作业 4921721 FAILED 127）★★★
        #   libmpifort.so.12 只在 mpi/latest/**lib**/，且 MPII_F_TRUE 是**导入**
        #   符号（nm: U），必须由 mpi/latest/**lib/release**/libmpi.so.12 提供
        #   （nm: R 已定义）。旧注入把 LD_LIBRARY_PATH 写成
        #   `mpi/latest/release`（**不存在的目录，笔误**）⇒ 计算节点环境里其它
        #   libmpi.so.12 副本（intelpython 内置精简 MPI 等）抢先加载 ⇒
        #   `symbol lookup error: libmpifort.so.12: undefined symbol: MPII_F_TRUE`。
        #   现改为与登录节点默认环境一致的 lib/release:lib 顺序，确保 libmpi
        #   先于任何 inherited 副本解析到带该符号的版本。
        impi_env = (
            "export LIBRARY_PATH=/public1/soft/oneAPI/2022.1/mpi/latest/lib/release:"
            "/public1/soft/oneAPI/2022.1/mpi/latest/lib:$LIBRARY_PATH\n"
            "export LD_LIBRARY_PATH=/public1/soft/oneAPI/2022.1/mpi/latest/lib/release:"
            "/public1/soft/oneAPI/2022.1/mpi/latest/lib:$LD_LIBRARY_PATH\n"
        )
        session.run(
            f"cd {remote_dir} && "
            f"cat > flash_impi_env.sh << 'IMPI_EOF'\n{impi_env}IMPI_EOF\n"
            f"sed -i '/^set -e/a source ./flash_impi_env.sh' submit_flash.sh && "
            f"echo IMPI_ENV_INJECTED", timeout=30)
        # ★ 注入命令曾漏 cd → sed 在 $HOME 下找不到文件静默失败 (日志勿无条件打成功)
        out, _, _ = session.run(
            f"grep -c flash_impi_env {remote_dir}/submit_flash.sh", timeout=30)
        if (out or "").strip() == "1":
            log("  [run] 已注入 Intel MPI 库路径 (flash_impi_env.sh)", "OK")
        else:
            log("  [run] ⚠ Intel MPI 路径注入失败 — 链接期可能 -lmpi 缺失", "WARN")

    # ── 尝试 SLURM 提交 ──────────────────────────
    # ★ 2026-10-24 实测缺陷：此处原为 `timeout=30`，但 NC-E 上
    #   `source /public1/soft/modules/module.sh` + 两次 `module load`
    #   本身就要 40~60s ⇒ `Command ... timed out after 30 seconds`，
    #   而作业其实**已经提交成功**（队列里能看到 RUNning 的作业）。
    #   结果是"作业在跑、封装层报 FAIL"—— 比失败更糟：会导致重复提交。
    #   现放宽到 180s，并在超时后回查队列，避免把已提交当失败。
    sbatch_cmd = f"cd {remote_dir} && {MODULES_LOAD} && sbatch submit_flash.sh 2>&1"
    _t0 = time.time()
    try:
        out, err, code = session.run(sbatch_cmd, timeout=180)
    except Exception as exc:  # noqa: BLE001 - 超时也要判断是否已提交
        log(f"    提交调用异常: {type(exc).__name__}; 回查队列判断是否已提交", "WARN")
        out, err, code = "", "", 1
    log(f"    提交返回 rc={code} 耗时 {time.time() - _t0:.0f}s")
    if code != 0 or "Submitted batch job" not in (out or ""):
        # 回查：刚提交的作业名 = FLASH_batch（见 submit_flash.sh 的 #SBATCH --job-name）
        # ★ 回查逻辑放在执行层（slurm_control.latest_job_by_name），
        #   场景层不得内联队列命令 —— 否则护栏债务会因修 bug 而增长。
        from flash.flash_run.remote.slurm_control import (
            RemoteExecutor,
            latest_job_by_name,
        )

        job_probe = latest_job_by_name(RemoteExecutor(session), "FLASH_batch")
        if job_probe:
            out = f"Submitted batch job {job_probe.split()[0]}"
            code = 0
            log(f"    回查确认已提交: {out}", "OK")

    if code == 0 and "Submitted batch job" in out:
        job_id = out.strip().split()[-1]
        log(f"    SLURM 作业已提交! Job ID: {job_id}")

        # 等待作业完成
        log("    等待作业完成 (每 15s 轮询)...", "INFO")
        max_wait = 3600
        start = time.time()
        while (time.time() - start) < max_wait:
            s_out, _, _ = session.run(
                f"sacct -j {job_id} --format=State --noheader 2>/dev/null | head -1",
                timeout=10,
            )
            state = s_out.strip()
            log(f"    状态: {state}")
            if state in ("COMPLETED", "COMPLETING"):
                log(f"    作业 {job_id} 完成!", "OK")
                break
            elif state in ("FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL"):
                log(f"    作业 {job_id} 失败: {state}", "ERROR")
                return False, ""
            time.sleep(15)
        else:
            log(f"    等待超时 (>1h)", "WARN")
    else:
        # SLURM 不可用, 降级为直接运行
        log("    SLURM 不可用, 降级为直接运行 run_flash.sh", "WARN")
        flash_cmd = (
            f"cd {remote_dir} && "
            f"{MODULES_LOAD} && "
            "bash run_flash.sh 2>&1 | tail -50"
        )
        log("    正在运行 (可能耗时数分钟)...", "INFO")
        out, err, code = session.run(flash_cmd, timeout=1800)
        log(f"    FLASH 返回码: {code}")
        if out.strip():
            for line in out.strip().splitlines()[-15:]:
                log(f"      {line}")

    # ── 验证输出 ────────────────────────────────
    # ★ 2026-10-24：`head -1` 取字典序**最旧**的 outputfiles_* —— insitu 模式
    #   （remote_dir=flash_input，多轮复用）会命中上一轮的产物目录，把旧 run 的
    #   chk 当成本轮结果（实测复现：3 个 outputfiles_* 时指向 11:20 的旧目录）。
    #   目录名带时间戳 ⇒ `sort | tail -1` 即最新一轮；hpc-remote 每轮独立
    #   remote_dir，行为不变。
    out, _, _ = session.run(
        f"ls -d {remote_dir}/outputfiles_* 2>/dev/null | sort | tail -1 || "
        f"ls {remote_dir}/outputfiles/*chk* 2>/dev/null | head -1 || "
        f"echo NO_CHK",
        timeout=10,
    )
    if "NO_CHK" in out or not out.strip():
        log("    未找到输出文件!", "WARN")
        return False, ""

    actual_output = out.strip()
    n_chk_out, _, _ = session.run(f"ls {actual_output}/*chk* 2>/dev/null | wc -l", timeout=10)
    try:
        n_chk = int(n_chk_out.strip())
        log(f"    找到 {n_chk} 个 checkpoint 文件 ✓", "OK")
    except ValueError:
        log(f"    输出目录: {actual_output}", "OK")
    return True, actual_output


# =====================================================================
# 步骤 4: 上传分析脚本并运行
# =====================================================================


def upload_and_run_analysis(
    session: RemoteSession, remote_dir: str, actual_output_dir: str,
    analysis_script_path: Path, cfg: Dict[str, Any],
) -> bool:
    """上传 HPC 分析脚本并远程执行。

    Args:
        session: RemoteSession 实例
        remote_dir: 远程目录
        analysis_script_path: 分析脚本本地路径
        cfg: 配置字典

    Returns:
        True 如果分析成功
    """
    log("  [analyze] 运行分析脚本 (已由 upload_to_hpc 一并上传)...", "STEP")
    log(f"    hpc_analyze_ch_center.py 已在远端")

    analysis_hw = cfg["analysis_half_width_um"] * 1e-4
    L0_cm = cfg["L0_um"] * 1e-4

    # ── 分析 python 三级回退链 (2026-10-22 三模式统一) ────
    #   ① FLASH_HPC_PYTHON env 显式指定
    #   ② $HOME/.venv-hpc-nce/bin/python (离线部署 venv, h5py3.14+yt4.4 已就位)
    #   ③ module load python/3.9.6 (旧路, 唯一带 h5py 的模块 → WARN 保留)
    #   ④ 系统 python3 → 均失败则回退本地分析
    def _remote_py_candidates() -> List[str]:
        cands: List[str] = []
        env_py = os.environ.get("FLASH_HPC_PYTHON", "").strip()
        if env_py:
            cands.append(env_py)
        out, _, _ = session.run(
            "test -x $HOME/.venv-hpc-nce/bin/python && echo VENV_OK", timeout=10)
        if "VENV_OK" in (out or ""):
            cands.append("$HOME/.venv-hpc-nce/bin/python")
        cands.append("module")     # 旧路: module load python/3.9.6
        cands.append("python3")
        return cands

    def _analyze_with(py_expr: str) -> Tuple[int, str]:
        if py_expr == "module":
            cmd = (f"cd {remote_dir} && "
                   f"module purge 2>/dev/null; "
                   f"module load python/3.9.6 2>/dev/null; "
                   f"export PYTHONIOENCODING=utf-8 && "
                   f"python hpc_analyze_ch_center.py ")
        else:
            cmd = (f"cd {remote_dir} && "
                   f"export PYTHONIOENCODING=utf-8 && "
                   f"{py_expr} hpc_analyze_ch_center.py ")
        cmd += (f"--input-dir {actual_output_dir} "
                f"--output-dir {remote_dir}/analysis_plots "
                f"--center-half-width {analysis_hw} "
                f"--L0 {L0_cm} 2>&1")
        out, err, code = session.run(cmd, timeout=600)
        return code, out or ""

    analysis_done = False
    for i, cand in enumerate(_remote_py_candidates()):
        label = ("FLASH_HPC_PYTHON" if i == 0 and os.environ.get("FLASH_HPC_PYTHON")
                 else ".venv-hpc-nce" if cand.startswith("$HOME")
                 else "module python/3.9.6 (旧路)" if cand == "module"
                 else "系统 python3")
        log(f"  [analyze] 尝试分析 ({label})...", "STEP")
        code, out = _analyze_with(cand)
        log(f"    返回码: {code}")
        if out.strip():
            for line in out.strip().splitlines()[-10:]:
                log(f"      {line}")
        out, _, _ = session.run(
            f"ls {remote_dir}/analysis_plots/*.png 2>/dev/null | wc -l", timeout=10)
        try:
            if int(out.strip()) > 0:
                log(f"    HPC 生成 PNG ✓ ({label})", "OK")
                analysis_done = True
                break
        except ValueError:
            pass
    if not analysis_done:
        log("    分析全部失败, 回退到本地分析", "WARN")
        return False
    return True


# =====================================================================
# hpc-insitu（模式⑤）+ hpc-remote 包目录工作目录（模式④）— 2026-10-22
# =====================================================================


class _LocalHpcShim:
    """in-situ 会话垫片：驱动脚本已在超算上时，用 LocalExecutor 顶替
    RemoteSession（run 签名兼容）；upload/download 为同机拷贝/直通。
    ★ 绝不 SSH 自连。"""

    def __init__(self) -> None:
        from flash.flash_run.remote.slurm_control import LocalExecutor
        self._exe = LocalExecutor()

    def run(self, cmd: str, timeout: int = 120):
        return self._exe.run(cmd, timeout=timeout)

    def upload(self, local: str, remote: str) -> bool:
        # in-situ: 本地路径即远端路径；仅在两者不同时拷贝
        try:
            lp, rp = Path(local), Path(remote)
            if lp.resolve() != rp.resolve():
                rp.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(lp, rp)
        except OSError as e:
            log(f"  [shim.upload] {e}", "WARN")
            return False
        return True

    def download(self, remote: str, local: str) -> bool:
        try:
            rp, lp = Path(remote), Path(local)
            if rp.resolve() != lp.resolve():
                lp.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(rp, lp)
        except OSError as e:
            log(f"  [shim.download] {e}", "WARN")
            return False
        return True


def _resolve_hpc_pkg_root(session) -> str:
    """远端 flash_sim 包根（模式④ runs 外置契约的锚点）。

    优先级: FLASH_HPC_PKG_ROOT > $HOME/PhySimX/PhySimX/simulation/flash/flash_sim。
    hpc-remote 需绝对路径（SFTP 不展开 ~），经 session 探测 $HOME。"""
    env = os.environ.get("FLASH_HPC_PKG_ROOT", "").strip()
    if env.startswith("/"):
        return env
    out, _, _ = session.run("printf '%s' \"$HOME\"", timeout=10)
    home = (out or "").strip()
    return f"{home}/PhySimX/PhySimX/simulation/flash/flash_sim"


def main_hpc_insitu(cfg: Dict[str, Any]) -> bool:
    """hpc-insitu 主流程：驱动已在超算登录节点（.venv-hpc-nce）。

    复用 hpc-remote 的 run_flash_on_hpc / upload_and_run_analysis（run 签名
    兼容，经 _LocalHpcShim 顶替 SSH）；重活（FLASH/分析）仍走 sbatch 作业。
    产物外置 runs_root()/ch_center/run_NNNNNN/（包目录 git 干净）。"""
    from flash.flash_run.remote.slurm_control import LocalExecutor, sbatch_available
    from flash.scenarios.runner import allocate_run_id, run_id_name, runs_root

    exe = LocalExecutor()
    if not sbatch_available(exe):
        log("当前环境无 sbatch/sacct —— hpc-insitu 只能在超算上运行 "
            "(Windows 请用 --mode hpc / FLASH_RUN_MODE=hpc)", "ERROR")
        return False

    runs_dir = runs_root() / "ch_center"
    run_id = allocate_run_id(runs_dir)
    run_dir = runs_dir / run_id_name(run_id)
    (run_dir / "output").mkdir(parents=True, exist_ok=True)
    (run_dir / "plots").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    log(f"runs 目录: {run_dir} (run_id={run_id:06d}, 输出外置契约)", "OK")

    shim = _LocalHpcShim()
    remote_dir = str(INPUT_DIR)          # 登录节点上 INPUT_DIR 即"远端"目录

    flash_ok, actual_output = run_flash_on_hpc(shim, remote_dir)
    if not flash_ok:
        log("FLASH 运行失败! 跳过分析。", "WARN")
        return False

    analysis_script = SCRIPT_DIR / "hpc_analyze_ch_center.py"
    analysis_ok = False
    if analysis_script.exists():
        # ★ 2026-10-24：insitu 没有 upload_to_hpc 步骤，分析脚本不在
        #   flash_input/ 里 ⇒ 远端 `python hpc_analyze_ch_center.py` 必然
        #   FileNotFoundError（实测两轮分析全败）。先就地拷入再跑。
        try:
            shutil.copy2(analysis_script, INPUT_DIR / analysis_script.name)
        except OSError as e:
            log(f"分析脚本拷入 flash_input 失败: {e}", "WARN")
        analysis_ok = upload_and_run_analysis(
            shim, remote_dir, actual_output, analysis_script, cfg)
    else:
        log(f"分析脚本不存在: {analysis_script}", "WARN")

    # 分析 PNG → runs plots 目录（外置契约）
    plots_src = INPUT_DIR / "analysis_plots"
    if plots_src.is_dir():
        for p in plots_src.glob("*.png"):
            shutil.copy2(p, run_dir / "plots" / p.name)
    # chk 产物 → runs output 目录（chk-only，fetch_policy）
    #   FLASH_COLLECT_DIR 生效时（批量矩阵）改投该目录，与 local/wsl/hpc-remote
    #   三种模式落同一处，便于跨模式逐帧对比。
    _alt = os.environ.get("FLASH_COLLECT_DIR", "").strip()
    out_dst = Path(_alt) if _alt else (run_dir / "output")
    out_dst.mkdir(parents=True, exist_ok=True)
    try:
        from flash.flash_run.remote.fetch_policy import select_fetch_files
        outp = Path(actual_output)
        if outp.is_dir():
            # ★ 2026-10-24：basenm 传空串 ⇒ classify_names 的 prefix 过滤
            #   （只放行 wsl_run_/basenm 前缀）把全部 chk 滤掉 ⇒ "收集 0 文件"
            #   的静默失败（实测复现）。basenm 从 .par 解析（权威来源，
            #   形如 basenm = "lasslab_"），解析不到才回落空串。
            _basenm = ""
            for _pf in sorted(INPUT_DIR.glob("*.par")):
                _m = re.search(r'^\s*basenm\s*=\s*"([^"]+)"',
                               _pf.read_text(encoding="utf-8", errors="replace"),
                               re.MULTILINE)
                if _m:
                    _basenm = _m.group(1)
                    break
            picked, stats = select_fetch_files(
                [p.name for p in outp.iterdir() if p.is_file()],
                basenm=_basenm, with_plt=False)
            for n in picked:
                shutil.copy2(outp / n, out_dst / n)
            log(f"就地收集 {len(picked)} 文件 (basenm={_basenm!r}, "
                f"plt 跳过={stats['plt_skipped']}) → {out_dst}", "OK")
    except Exception as e:  # noqa: BLE001
        log(f"chk 收集跳过: {e}", "WARN")

    print("\n" + "=" * 65)
    print(" hpc-insitu 全流程完成!")
    print(f"  runs 目录: {run_dir}")
    print(f"  分析图像:  {run_dir / 'plots'} (n={len(list((run_dir / 'plots').glob('*.png')))})")
    print("=" * 65)
    # ★ 2026-10-24：旧判据 `(run_dir / "output").is_dir()` 恒为真（目录在建
    #   run_dir 时就建好了）⇒ "分析失败但 FLASH 成功"也会报成功，属 G6 同类
    #   静默失败。现要求：分析成功 **或** 确有产物（chk/plt）落地 —— 产物
    #   包括 FLASH_COLLECT_DIR（批量矩阵模式，chk 直接落那里，runs/output
    #   反而为空），三者任一非空即认。
    _alt = os.environ.get("FLASH_COLLECT_DIR", "").strip()
    _collect_has = bool(list(Path(_alt).glob("*chk*"))) if _alt else False
    _has_artifacts = bool(list((run_dir / "output").glob("*")) or
                          list((run_dir / "plots").glob("*.png")) or
                          _collect_has)
    return bool(analysis_ok or _has_artifacts)


# =====================================================================
# 步骤 5: 下载分析结果
# =====================================================================


def download_analysis_results(session: RemoteSession, remote_dir: str) -> int:
    """从超算下载分析 PNG 图到本地 plots 目录。

    Args:
        session: RemoteSession 实例
        remote_dir: 远程目录

    Returns:
        下载的文件数
    """
    log("  [download] 下载分析结果...", "STEP")

    # 获取远程 PNG 列表
    out, _, _ = session.run(
        f"ls {remote_dir}/analysis_plots/*.png 2>/dev/null || "
        f"find {remote_dir} -name '*.png' 2>/dev/null || echo NO_PNG",
        timeout=10,
    )
    if "NO_PNG" in out or not out.strip():
        log("    远程未找到 PNG 文件!", "WARN")
        return 0

    remote_files = [l.strip() for l in out.strip().splitlines() if l.strip() and '.png' in l]

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    for rf in remote_files:
        local_path = str(PLOTS_DIR / Path(rf).name)
        ok = session.download(rf, local_path)
        if ok:
            downloaded += 1
            log(f"    {Path(rf).name} ✓")
        else:
            log(f"    下载失败: {rf}", "WARN")

    log(f"  下载 {downloaded} 个文件到 {PLOTS_DIR}", "OK")
    return downloaded


# =====================================================================
# 主编排函数
# =====================================================================



def _to_wsl_path(win_path: Path) -> str:
    """归一为 WSL 路径（/mnt/<drive>/...），**幂等**。

    例: E:\\PhySimX\\...\\flash_input → /mnt/e/PhySimX/.../flash_input

    ★ 09-10 修复：**已在 WSL 内运行时**（离线机常直接把仓库放在 /mnt/e 下，
      用 Linux 解释器执行本脚本），传入的已是 `/mnt/e/...` 形式 ——
      旧实现无条件按 `:` 分割 ⇒ `ValueError: not enough values to unpack`
      ⇒ 步骤 2 直接崩。此处先识别已有 WSL 路径并原样返回。
    """
    s = str(win_path)
    # 已是 WSL / POSIX 绝对路径 ⇒ 原样返回（幂等的关键）
    if s.startswith("/"):
        return s
    if ":" not in s:                      # 相对路径等异常形态，交给调用方报错
        return s.replace("\\", "/")
    drive, rest = s.split(":", 1)
    return "/mnt/" + drive.lower() + rest.replace("\\", "/")


def _tail_lines(path: Path, n: int = 25, max_len: int = 160) -> str:
    """读取文件末尾 n 行（运行中日志），每行截断到 max_len 字符。

    日志文件可能正被 WSL 侧追加写入；读不到时返回空串。
    """
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    lines = data.splitlines()
    return "\n".join(l[:max_len] for l in lines[-n:])


def _run_wsl_with_progress(cmd: str, console_log: Path,
                           interval: float = 120.0,
                           timeout: float = 7200.0) -> Tuple[int, str]:
    """在 WSL 中执行命令，运行期间每隔 interval 秒回显一段实际日志。

    用 Popen 轮询替代阻塞的 subprocess.run：长时 FLASH 仿真期间用户能
    每 120s 看到一小段真实输出（编译进度/网格细化/时间步进等），确认
    代码在推进而非卡死。

    Args:
        cmd: 交给 `wsl bash -c` 执行的命令串（输出重定向到 console_log）。
        console_log: WSL 侧写出的日志文件（Windows 路径）。
        interval: 进度回显间隔（秒）。
        timeout: 总超时（秒），超出则 kill 进程并抛 TimeoutExpired。

    Returns:
        (WSL 返回码, 日志文件当前全部内容)。
    """
    start = time.monotonic()
    # ★ 09-10 修复：**已在 Linux/WSL 内运行**时不要再套一层 `wsl`——
    #   WSL 内部没有 `wsl` 命令（旧实现 Popen(["wsl","bash","-c",...])
    #   ⇒ FileNotFoundError: 未找到 wsl 命令 ⇒ 步骤 3 直接失败）。
    #   离线机常把仓库放在 /mnt/e 下并用 Linux 解释器直接跑本脚本，
    #   此时 `bash -c` 就是正确调用。Windows 上则仍走 wsl 中转。
    if os.name == "nt":
        argv = ["wsl", "bash", "-c", cmd]
    else:
        argv = ["bash", "-c", cmd]
    proc = subprocess.Popen(
        argv,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    last_report = start
    while proc.poll() is None:
        now = time.monotonic()
        if now - last_report >= interval:
            last_report = now
            elapsed = int(now - start)
            tail = _tail_lines(console_log)
            if tail.strip():
                log(f"[{elapsed}s] FLASH 运行中，最近输出:")
                print(tail)
            else:
                log(f"[{elapsed}s] 尚无输出（可能仍在 setup/编译阶段）...")
        if now - start > timeout:
            proc.kill()
            proc.wait()
            raise subprocess.TimeoutExpired(cmd, timeout)
        time.sleep(5)
    rc = proc.wait()
    console_txt = ""
    if console_log.exists():
        console_txt = console_log.read_text(encoding="utf-8", errors="replace")
    return rc, console_txt


def main_wsl(cfg: Dict[str, Any]) -> bool:
    """本地 WSL 运行 FLASH（替代超算 RemoteSession 流程）。

    步骤 2（部署）: 无需上传，run_flash.sh 与输入文件已在本地 flash_input/。
    步骤 3（运行）: wsl bash run_flash.sh（完整流水线: setup→编译→运行→收集）。
    步骤 4/5（分析）: 本地 output_processors 分析 flash_input/outputfiles/ 的 HDF5。
    """
    # ── 步骤 2: WSL 本地部署 ─────────────────────
    print("\n[步骤 2/5] 本地 WSL 部署（无需上传）")
    print("-" * 50)
    wsl_dir = _to_wsl_path(INPUT_DIR)
    log(f"WSL 工作目录: {wsl_dir}")
    run_sh = INPUT_DIR / "run_flash.sh"
    if not run_sh.exists():
        log(f"run_flash.sh 不存在: {run_sh}", "ERROR")
        return False
    log("输入文件已就绪（run_flash.sh / Config / Makefile / *.F90 / *.cn4 / *.par）")

    # ── 步骤 3: WSL 运行 FLASH ───────────────────
    print("\n[步骤 3/5] WSL 运行 FLASH 仿真 (setup→编译→运行→收集)")
    print("-" * 50)
    # 输出重定向到 WSL 内日志文件 + 追加退出码，再从 Windows 侧读取：
    #   wsl.exe 从无控制台/非交互上下文 (如某些 IDE 子进程) 启动时，
    #   stdout 管道捕获可能静默为空。写文件绕开该问题（退出码由包装脚本
    #   的 FLASH_EXIT_CODE 哨兵 + wsl.exe 进程 rc 双通道带回，见上方注释）。
    run_log_name = "wsl_console.log"
    console_log = INPUT_DIR / run_log_name
    try:
        console_log.unlink()
    except OSError:
        pass
    # ★ 运行隔离（2026-10-24）：FLASH_RUN_WORKDIR / FLASH_COLLECT_DIR 经
    #   包装脚本传进 WSL（不依赖 wsl.exe 是否透传 Windows 进程环境，不可控）。
    #   FLASH_RUN_WORKDIR  每轮独立 cwd  → 并发安全 + 不收集历史 chk
    #   FLASH_COLLECT_DIR  每轮独立收纳  → 产物按轮归档
    _wd = os.environ.get("FLASH_RUN_WORKDIR", "").strip()
    _cd = os.environ.get("FLASH_COLLECT_DIR", "").strip()
    if _wd:
        log(f"隔离变量: FLASH_RUN_WORKDIR={_wd}")
    if _cd:
        log(f"隔离变量: FLASH_COLLECT_DIR={_cd}")
    # ★★★ 2026-10-24 假成功修复（模式测试首跑实测复现，代价：一次完整跑崩）★★★
    # 本机 wsl.exe 会把 `bash -c` 命令串在**顶层 `;` / `&&` / `||`** 处拆成
    # 多次独立执行（实测：`false; echo $?`→0；`X=5; echo $X`→空；
    # `false > log 2>&1 && echo RC=0 || echo RC=$?` → 恒写 RC=0；
    # 只有最后一片段的 rc 能透传）。⇒ 复合命令、env 前缀、行内哨兵**全部不可信**：
    # 旧写法 `... ; echo "FLASH_EXIT_CODE=$?"` 的哨兵段在全新 shell 里执行，
    # $? 恒为 0 ⇒ FLASH 崩溃（exit 134，57 个部分 chk）被报成"运行成功"。
    # 解法：全部逻辑收进**脚本文件**（bash 正常解析，无拆分），wsl 侧只发
    # 一条简单命令 `bash <wrapper> <args...>`（rc 正常透传，实测 134→134）。
    _wrap = INPUT_DIR / "run_flash_wsl.sh"
    # ★ write_bytes + 显式 \n：Windows 上 write_text 会写成 CRLF，bash 解析
    #   "$1"\r 之类直接崩（实测 rc=2 无日志）——本机 .gitattributes 也规定 LF。
    _wrap.write_bytes(
        ("#!/bin/bash\n"
         "# 由 main_wsl 自动生成 —— 规避 wsl.exe 命令串拆分（2026-10-24，勿手改）\n"
         "set -u\n"
         'WSL_DIR="$1"; WORKDIR="$2"; COLLECT="$3"; LOG="$4"\n'
         'cd "$WSL_DIR" || exit 1\n'
         'export FLASH_RUN_WORKDIR="$WORKDIR" FLASH_COLLECT_DIR="$COLLECT"\n'
         'bash run_flash.sh > "$LOG" 2>&1\n'
         "rc=$?\n"
         'echo "FLASH_EXIT_CODE=$rc" >> "$LOG"\n'
         "exit $rc\n").encode("utf-8"),
    )
    cmd = (
        f"bash '{_to_wsl_path(_wrap)}' '{wsl_dir}' "
        f"'{_to_wsl_path(Path(_wd)) if _wd else '/tmp'}' "
        f"'{_to_wsl_path(Path(_cd)) if _cd else '/tmp'}' '{run_log_name}'"
    )
    log(f"执行: wsl bash -c \"{cmd[:100]}...\"")
    log("首次运行需编译 FLASH，可能耗时 10~60 分钟 ...")

    # 无任何有效输出时重试：WSL 冷启动/VM 竞态等瞬态故障表现为
    # 立即返回 rc!=0 且 stdout/stderr 与日志文件均为空，非真实 FLASH 失败。
    max_attempts = 3
    attempt = 0
    flash_rc = None
    console_txt = ""
    while attempt < max_attempts:
        attempt += 1
        if attempt > 1:
            log(f"WSL 返回无有效输出，重试 ({attempt}/{max_attempts})...", "WARN")
        try:
            flash_rc, console_txt = _run_wsl_with_progress(
                cmd, console_log, interval=120.0, timeout=7200.0,
            )
        except FileNotFoundError:
            log("未找到 wsl 命令。请确认已安装 WSL (wsl --install) 并设置默认发行版。", "ERROR")
            return False
        except subprocess.TimeoutExpired:
            log("WSL 运行超时 (2 小时)", "ERROR")
            return False

        combined = console_txt.strip()
        # 退出码判定以**哨兵**为权威（包装脚本写入，2026-10-24 起可信；
        # wsl.exe 进程 rc 是简单命令的透传，同样可信）：
        #   · 有哨兵 ⇒ 命令完整执行过（无论成败），无需重试；
        #   · 无哨兵 + 有输出 + rc=0 ⇒ 旧形态脚本，按成功收下；
        #   · 无哨兵 + 有输出 + rc!=0 ⇒ 真实失败，带诊断输出；
        #   · 完全无输出 ⇒ WSL 冷启动/VM 竞态等瞬态故障，重试。
        _has_marker = re.search(r"FLASH_EXIT_CODE=(\d+)", console_txt) is not None
        if _has_marker or combined:
            break
        log(f"WSL 无输出 (exit={flash_rc})，疑似冷启动/捕获异常，5s 后重试...", "WARN")
        time.sleep(5)

    if flash_rc is None:
        log("WSL 启动失败 (多次重试后仍无输出)", "ERROR")
        return False

    # 提取 WSL 内 FLASH 退出码：哨兵优先（内层真相），无哨兵才信进程 rc
    flash_exit = flash_rc if flash_rc is not None else -1
    m = re.search(r"FLASH_EXIT_CODE=(\d+)", console_txt)
    if m:
        flash_exit = int(m.group(1))

    log(combined[-3000:] if len(combined) > 3000 else combined)
    wsl_log = INPUT_DIR / "wsl_run.log"
    wsl_log.write_text(combined, encoding="utf-8", errors="replace")
    if flash_exit != 0:
        log(f"FLASH 运行失败 (exit={flash_exit})，完整日志: {wsl_log}", "ERROR")
        return False
    log(f"FLASH 运行成功 ✓ (完整日志: {wsl_log})")

    # 检查输出（FLASH_COLLECT_DIR 生效时产物不在 INPUT_DIR/outputfiles）
    _collect = os.environ.get("FLASH_COLLECT_DIR", "").strip()
    outdir = Path(_collect) if _collect else (INPUT_DIR / "outputfiles")
    h5s = (
        sorted(outdir.glob("*chk*"))
        or sorted(outdir.glob("*plt*"))
        or sorted(outdir.glob("*.h5"))
    )
    if not h5s:
        log(f"未找到 HDF5 输出文件: {outdir}", "ERROR")
        return False
    log(f"找到 {len(h5s)} 个 HDF5 输出: {outdir}")

    # ── 步骤 4/5: 本地分析输出 ──────────────────
    print("\n[步骤 4/5] 本地分析输出 (output_processors)")
    print("-" * 50)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from flash.output_processors.loader import FlashDataLoader
        from flash.output_processors.plotter import FlashPlotter

        container = FlashDataLoader(str(h5s[0])).load(
            compute_derived=True, extraction_mode=EXTRACTION_MODE,
        )
        for var, fname in [
            ("dens", "dens_wsl.png"),
            ("tele", "tele_wsl.png"),
            ("trad", "trad_wsl.png"),
        ]:
            try:
                FlashPlotter(container).plot(
                    var, save_path=str(PLOTS_DIR / fname),
                    title=f"{var} (WSL Local)",
                )
                log(f"    {fname} ✓")
            except Exception as e:
                log(f"    绘制 {var} 失败: {e}", "WARN")
    except Exception as e:
        log(f"本地分析失败: {e}", "WARN")

    print("\n" + "=" * 65)
    print(" WSL 全流程完成!")
    print(f"  输入文件目录: {INPUT_DIR}")
    print(f"  输出结果目录: {INPUT_DIR / 'outputfiles'}")
    print(f"  分析图像目录: {PLOTS_DIR}")
    print("=" * 65)
    return True


def main(credential_name: Optional[str] = None,
         mode: Optional[str] = None,
         tmax: Optional[float] = None):
    """唯一入口。`mode`/`tmax` 为空时分别回落到 FLASH_RUN_MODE / RUN_MODE 与场景默认值。

    ★ 2026-10-24：`mode` 缺省 = auto（平台自适应）。判定只走
      `flash.flash_run.execution.resolve_target`，**不在本文件里另写一套**。
    """
    print("\n" + "=" * 65)
    print(" FLASH LaserSlab1D Custom Simulation v1.1")
    print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    cfg = dict(config_constants)

    # ── 运行模式判定（先于任何生成/上传：模式不同则行为不同）──
    from flash.flash_run.execution import (
        DEFAULT_POLICY,
        ExecutionTargetError,
        resolve_target,
    )
    _explicit = (mode or "").strip() or os.environ.get("FLASH_RUN_MODE", "").strip() or RUN_MODE
    try:
        run_mode, _trace = resolve_target(_explicit, DEFAULT_POLICY)
    except ExecutionTargetError as exc:
        log("运行模式判定失败", "ERROR")
        for _line in str(exc).splitlines():
            print("  " + _line)
        return False
    for _line in _trace:
        print("  " + _line)

    if tmax:
        # 只改终止时间：脉冲/网格/EOS/激光逐字不变 ⇒ 跨模式对比仍是同一算例
        cfg["tmax_override_s"] = float(tmax)

    # ── 参数摘要 ──
    print(f"\n  参数配置:")
    print(f"    域: [{-cfg['L0_um']}, {cfg['L0_um']}] um")
    print(f"    靶: [{-cfg['sim_targetHeight_um']}, {cfg['sim_targetHeight_um']}] um")
    print(f"    rho_targ = {cfg['sim_rhoTarg']} g/cm^3")
    print(f"    激光: 2束 × {cfg['peak_power']:.1e} W/cm^2")
    print(f"    波长: {cfg['wavelength_um']} um")
    print(f"    脉冲: {cfg['pulse_duration_ns']} ns (平顶), {cfg['rise_fall_ps']} ps (边沿)")
    print(f"    分析区域: [{ -cfg['analysis_half_width_um']}, {cfg['analysis_half_width_um']}] um")
    print("=" * 65)

    # ── 步骤 1: 检查 FLASH 仿真必须文件，缺失则生成 ──
    # 仓库不发布 par/Makefile/Config/F90/cn4 等生成文件（flash_input/ 被
    # .gitignore 排除），先经 gen_checker 检查 7 项必须文件：
    #   已就绪 → 直接下一步；缺失 → 调用 input_gen 生成器自动生成。
    print("\n[步骤 1/5] 检查 FLASH 仿真必须文件（gen_checker）")
    print("-" * 50)
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from flash.input_gen.gen_checker import DependencyChecker

        missing = DependencyChecker(INPUT_DIR).missing_standard()
        if missing:
            log(f"缺失 {len(missing)} 项必须文件: {missing}", "WARN")
            log("自动调用 input_gen 生成器生成必须文件 ...", "INFO")
            generate_input_files(cfg)
            # 生成后复查
            missing2 = DependencyChecker(INPUT_DIR).missing_standard()
            if missing2:
                log(f"生成后仍有 {len(missing2)} 项缺失: {missing2}", "ERROR")
                log("请查看上方生成日志定位错误，或运行 "
                    "python flash/scenarios/center_evolution/ch_center/gen_flash_inputs.py --force 重试",
                    "ERROR")
                return False
            log(f"必须文件已生成: {INPUT_DIR}")
        else:
            log("FLASH 仿真必须文件已就绪（gen_checker 检查通过），无需重新生成", "OK")

        # ── 生成物**陈旧**检查：存在 ≠ 可用 ──
        # 旧版 run_flash.sh 不认识 FLASH_RUN_WORKDIR，所有运行共用 objdir，
        # 短 tmax 只覆盖 chk_0000..N，Step 6 的 `cp *chk*` 会把上一轮的
        # chk_N+1.. 一并收集 ⇒ 跨模式对比数据被静默污染。缺能力标记即重建。
        _sh = INPUT_DIR / "run_flash.sh"
        try:
            _sh_txt = _sh.read_text(encoding="utf-8", errors="replace")
        except OSError:
            _sh_txt = ""
        if _sh.is_file() and "FLASH_RUN_WORKDIR" not in _sh_txt:
            log("run_flash.sh 为旧版生成物（不支持 FLASH_RUN_WORKDIR 运行隔离），"
                "按当前生成器重建", "WARN")
            generate_input_files(cfg)

        log(f"输入文件目录: {INPUT_DIR}")

        # ── 步骤 1.5: 文件内在关联检查（check_relations）──
        # 在"文件都存在"之上，进一步校验 7 个文件之间的内容一致性
        # （.par 引用 ↔ Config DATAFILES ↔ 磁盘 .cn4 / sim_* 参数 ↔ F90 /
        #   维度/光束/脉冲 / 脚本装配），详见 gen_checker/GEN_CHECKER_GUIDE.md。
        log("进行文件内在关联检查 (check_relations)...", "STEP")
        try:
            from flash.input_gen.gen_checker import RelationChecker

            rc = RelationChecker(INPUT_DIR, verbose=False)
            rc.run_all()
            if not rc.all_passed():
                failed = rc.failed()
                log(f"内在关联检查发现 {len(failed)} 处不一致，请修正后重试:", "ERROR")
                for r in failed:
                    log(f"    [FAIL] {r.rule_id}: {r.message}", "ERROR")
                log("若为新增自定义关联误报，可在 gen_checker/relations/ 扩展/调整规则。",
                    "WARN")
                return False
            log(f"内在关联检查通过（{len(rc.results())} 条规则全部通过/跳过）", "OK")
        except Exception as e:
            log(f"内在关联检查执行异常（不阻断流程）: {e}", "WARN")
    except Exception as e:
        log(f"输入文件检查/生成失败: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False

    # ── 运行模式分支 ────────────────────────────
    # local / wsl 共用本地流水线（Linux 宿主不再套 wsl.exe，见 _run_wsl_with_progress）
    log(f"运行模式: {run_mode} (explicit={_explicit!r}, env FLASH_RUN_MODE={os.environ.get('FLASH_RUN_MODE', '-')})", "INFO")
    if run_mode in ("wsl", "local"):
        return main_wsl(cfg)
    if run_mode == "hpc-insitu":
        return main_hpc_insitu(cfg)

    # ── 步骤 2-5: 通过 RemoteSession 连接超算 ────
    print("\n[步骤 2/5] 连接超算并部署 (RemoteSession)")
    print("-" * 50)
    log("正在通过凭据系统连接超算 (自动选择最佳路由)...")

    try:
        with RemoteSession(credential_name=credential_name, verbose=True) as session:
            log("SSH 连接成功 ✓")

            # 创建远程目录 — ★ 工作目录双模式 (2026-10-22 三模式统一):
            #   FLASH_HPC_WORKDIR=temp (默认, 模式③) → AI/Aitemp 一次性目录
            #   FLASH_HPC_WORKDIR=runs (模式④)       → flash_sim_runs/ch_center/hpc_{ts}
            #     (flash_sim 包同级, 输出外置契约; setup/make 仍在 FLASH 树 objdir)
            workdir_mode = os.environ.get("FLASH_HPC_WORKDIR", "temp").strip().lower()
            remote_run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            # ★ 2026-10-24：remote_dir 必须解析成**绝对路径**再交给 SFTP ——
            #   paramiko 的 sftp 不展开 `~`（实测：文件落进字面 `~/QC/...`
            #   垃圾目录，上传看似成功实则全部落错位置）。先经 shell 探一次
            #   $HOME（exec 通道可靠），失败即明确报错，绝不静默用 ~ 形式。
            _home_out, _, _ = session.run("printf '%s' \"$HOME\"", timeout=15)
            _home = (_home_out or "").strip()
            if not _home.startswith("/"):
                log(f"无法解析远端 $HOME（得到 {_home!r}），中止上传", "ERROR")
                return False
            if workdir_mode == "runs":
                _pkg_root = _resolve_hpc_pkg_root(session)
                remote_dir = f"{_pkg_root.parent}/flash_sim_runs/ch_center/hpc_{remote_run_id}"
                log(f"工作目录模式: runs (包目录契约, 模式④)")
            else:
                remote_dir = f"{_home}/{SIM_USER_DIR}/AI/AItemp/flash_custom_{remote_run_id}"
            session.run(f"mkdir -p {remote_dir}", timeout=10)
            log(f"远程目录: {remote_dir}")

            # 上传文件
            upload_ok = upload_to_hpc(session, remote_dir)
            if not upload_ok:
                log("部分文件上传失败, 继续尝试运行", "WARN")

            # ── 步骤 3: 远程运行 FLASH ──────────
            print("\n[步骤 3/5] 远程运行 FLASH 仿真")
            print("-" * 50)
            flash_ok, actual_output = run_flash_on_hpc(session, remote_dir)
            if not flash_ok:
                log("FLASH 运行失败! 跳过分析。", "WARN")
                return False
            log(f"    输出目录: {actual_output}")

            # 批量矩阵（FLASH_COLLECT_DIR 生效）: 无条件回传 chk，
            # 与 local/wsl 落在同一目录，供跨模式逐帧 dens/nele 对比。
            if os.environ.get("FLASH_COLLECT_DIR", "").strip():
                download_hdf5_to_local(session, remote_dir, actual_output,
                                       with_plt=False)

            # ── 步骤 4: 上传并运行分析脚本 ──────
            print("\n[步骤 4/5] 上传并运行 HPC 分析脚本")
            print("-" * 50)
            analysis_script = SCRIPT_DIR / "hpc_analyze_ch_center.py"
            if not analysis_script.exists():
                log(f"分析脚本不存在: {analysis_script}", "ERROR")
                return False

            analysis_ok = upload_and_run_analysis(
                session, remote_dir, actual_output, analysis_script, cfg,
            )

            # ── 步骤 5: 下载分析结果 ────────────
            print("\n[步骤 5/5] 下载分析结果")
            print("-" * 50)

            if analysis_ok:
                n_dl = download_analysis_results(session, remote_dir)
                if n_dl > 0:
                    log(f"分析图像已保存到: {PLOTS_DIR}", "OK")
                else:
                    # 回退: 下载 HDF5 到本地分析
                    log("未下载到 PNG, 尝试下载 HDF5...", "INFO")
                    download_hdf5_to_local(session, remote_dir, actual_output)
            else:
                log("HPC 分析失败, 下载 HDF5 到本地分析...", "WARN")
                download_hdf5_to_local(session, remote_dir, actual_output)

    except RuntimeError as e:
        log(f"SSH 连接失败: {e}", "ERROR")
        log("请确保已配置凭据: python -m flash._core.credentials.manage", "INFO")
        log("或者手动上传文件到超算并运行 "
            "(账户/线路统一配置于 ~/.physimx/flash/hpc_accounts.json):", "INFO")
        # 提示命令中的 user@host 从明文 JSON 读取, 不在脚本内硬编码
        _hint_user, _hint_host = "<user>", "<host>"
        try:
            from flash._core.credentials.hpc_config import (
                get_hpc_routes, get_hpc_ssh_username,
            )
            _u = get_hpc_ssh_username("flash_ssh")
            _rs = get_hpc_routes("flash_ssh")
            if _u:
                _hint_user = _u.split("@")[0]
            if _rs:
                _hint_host = _rs[0]["host"]
        except Exception:  # noqa: BLE001
            pass
        log(f"  scp -r {INPUT_DIR}/* {_hint_user}@{_hint_host}:{remote_dir}/", "INFO")
        return False

    # ── 完成 ──
    print("\n" + "=" * 65)
    print(" 全流程完成!")
    print(f"  输入文件目录: {INPUT_DIR}")
    print(f"  输出结果目录: {OUTPUT_DIR}")
    print(f"  分析图像目录: {PLOTS_DIR}")
    print("=" * 65)
    return True


def download_hdf5_to_local(session: RemoteSession, remote_dir: str,
                           actual_output_dir: str = "",
                           with_plt: bool = False):
    """下载 HDF5 文件到本地供 output_processors 分析。

    ★ with_plt=False (默认, 2026-09-16 chk-only 全场景定案, 策略源
    flash/flash_run/remote/fetch_policy.py): 只回传 chk; 本地分析
    FlashDataLoader 本就优先 chk。

    Args:
        session: RemoteSession 实例
        remote_dir: 远程任务目录（回退查找用）
        actual_output_dir: FLASH 实际输出目录（run_flash_on_hpc 返回，
            形如 .../outputfiles_20260811_192104）
        with_plt: True 时连 plt 一起下载（默认不取）
    """
    # 优先使用实际输出目录；否则在 remote_dir 下扫描 outputfiles*
    search_dirs = []
    if actual_output_dir:
        search_dirs.append(actual_output_dir)
    search_dirs.append(f"{remote_dir}/outputfiles")
    search_dirs.append(f"{remote_dir}/outputfiles_*")

    # ★ 2026-10-24 模式测试：head -50 是交互模式的上限，但批量矩阵
    #   （FLASH_COLLECT_DIR 生效）需要**全部帧**做跨模式时序对比 ——
    #   短 tmax 跑 50+ chk 时旧上限会静默截断，导致对比数据缺尾帧。
    #   现改为 FLASH_LS_LIMIT 可配（默认 50，行为不变；批量模式置大）。
    try:
        _ls_limit = int(os.environ.get("FLASH_LS_LIMIT", "50"))
    except ValueError:
        _ls_limit = 50
    if _ls_limit <= 0:
        _ls_limit = 100000
    ls_cmd = " || ".join(
        f"ls {d}/*chk* {d}/*plt* 2>/dev/null | head -{_ls_limit}"
        for d in search_dirs
    ) + " || echo NO_H5"
    out, _, _ = session.run(ls_cmd, timeout=15)
    if "NO_H5" in out or not out.strip():
        log("    未找到 HDF5 文件", "WARN")
        return

    remote_files = [l.strip() for l in out.strip().splitlines() if l.strip()]
    # ★ chk-only 默认 (2026-09-16 全场景定案, 策略源
    #   flash/flash_run/remote/fetch_policy.py): plt 不回传; with_plt=True 才取。
    #   importlib 按路径加载策略模块, 避免 import flash 包副作用。
    import importlib.util as _ilu
    _fp = None
    for _root in Path(__file__).resolve().parents:
        _f = _root / "flash" / "flash_run" / "remote" / "fetch_policy.py"
        if _f.is_file():
            _spec = _ilu.spec_from_file_location("_fetch_policy", _f)
            _fp = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_fp)
            break
    if _fp is None:
        raise ImportError("fetch_policy.py not found above " + str(__file__))
    if not with_plt:
        _nplt = sum(1 for f in remote_files if _fp.is_plt(Path(f).name))
        remote_files = [f for f in remote_files if not _fp.is_plt(Path(f).name)]
        if _nplt:
            log(f"    ★ chk-only 模式: 跳过 {_nplt} 个 plt 文件 "
                f"(with_plt=True 可改)", "INFO")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # 批量矩阵（FLASH_COLLECT_DIR）需要**全部**帧做时序对比；交互模式仍只取 10 个
    # （多取会让一次性运行等很久且通常用不到）。
    _dest = Path(os.environ["FLASH_COLLECT_DIR"]) if os.environ.get(
        "FLASH_COLLECT_DIR", "").strip() else OUTPUT_DIR
    _dest.mkdir(parents=True, exist_ok=True)
    try:
        _limit = int(os.environ.get("FLASH_FETCH_LIMIT", "10"))
    except ValueError:
        _limit = 10
    _picked = remote_files if _limit <= 0 else remote_files[:_limit]
    n = 0
    for rf in _picked:
        local_path = str(_dest / Path(rf).name)
        ok = session.download(rf, local_path)
        if ok:
            n += 1
    log(f"  下载 {n} 个 HDF5 文件到 {_dest}", "OK")

    if n > 0:
        try:
            from flash.output_processors.loader import FlashDataLoader
            from flash.output_processors.plotter import FlashPlotter
            h5_files = sorted(_dest.glob("*chk*")) or sorted(_dest.glob("*plt*"))
            if h5_files:
                container = FlashDataLoader(str(h5_files[0])).load(
                    compute_derived=True, extraction_mode=EXTRACTION_MODE,
                )
                FlashPlotter(container).plot(
                    "dens", save_path=str(PLOTS_DIR / "dens_local.png"),
                    title="Density (Local Analysis)",
                )
                log(f"    dens_local.png ✓")
        except Exception as e:
            log(f"    本地分析失败: {e}", "WARN")


if __name__ == "__main__":
    success = main()
    if success:
        print("\n 仿真流程成功结束!")
    else:
        print("\n 仿真流程失败!")
        sys.exit(1)
