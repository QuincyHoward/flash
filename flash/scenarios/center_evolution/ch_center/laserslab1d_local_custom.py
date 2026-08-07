"""
FLASH LaserSlab1D Custom Simulation v1.1
═══════════════════════════════════════════

可配置参数的一维对称域 LaserSlab 仿真。
CH 靶居中 (polystyrene-imx-008.cn4)，两侧真空 (he-imx-005.cn4)，
两束 351nm 激光相向入射。

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
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

# ── 路径设置 ──────────────────────────────────────────

# Bootstrap: find flash project root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    _ROOT = None  # 已安装环境 (site-packages): 静默跳过
_PARENT = _ROOT
if _PARENT is not None and str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))


# ── RemoteSession 导入 ───────────────────────────────
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession, get_hpc_platform

# ── 用户信息（优先从 flash 凭证中心读取，再回落环境变量）──
def _get_sim_user_dir() -> str:
    """三层回落: credentials → 环境变量 → 'hello'"""
    try:
        from flash._core.credentials import get_user_name
        return get_user_name()
    except ImportError:
        pass
    return os.environ.get("FLASH_SIM_USER_DIR", "hello")

SIM_USER_DIR = _get_sim_user_dir()

# 超算环境配置
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

    sim_path = f"{SIM_USER_DIR}/LaserSlab_custom"
    objdir = f"{SIM_USER_DIR}/LaserSlab_custom"
    par_filename = "laserslab_custom.par"

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

    # EOS 文件 (polystyrene + helium)
    par_gen.set("eos_targEosType", "eos_tab")
    par_gen.set("eos_targSubType", "ionmix4")
    par_gen.set("eos_targTableFile", "polystyrene-imx-008.cn4")
    par_gen.set("eos_chamEosType", "eos_tab")
    par_gen.set("eos_chamSubType", "ionmix4")
    par_gen.set("eos_chamTableFile", "he-imx-005.cn4")

    # Opacity 文件
    par_gen.set("op_targAbsorb", "op_tabpa")
    par_gen.set("op_targEmiss", "op_tabpe")
    par_gen.set("op_targTrans", "op_tabro")
    par_gen.set("op_targFileType", "ionmix4")
    par_gen.set("op_targFileName", "polystyrene-imx-008.cn4")
    par_gen.set("op_chamAbsorb", "op_tabpa")
    par_gen.set("op_chamEmiss", "op_tabpe")
    par_gen.set("op_chamTrans", "op_tabro")
    par_gen.set("op_chamFileType", "ionmix4")
    par_gen.set("op_chamFileName", "he-imx-005.cn4")

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
        name="Polystyrene", file="polystyrene-imx-008.cn4",
        rho=cfg["sim_rhoTarg"], A=cfg["ms_targA"], Z=cfg["ms_targZ"],
    )
    chamber_mat = Material(
        name="Helium", file="he-imx-005.cn4",
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
    # .par/Config 中引用的是 polystyrene-imx-008.cn4 (CH 高分辨表, canonical=polystyrene_hi)
    ps_copy = eos_gen.copy_eos_file("polystyrene_hi", str(INPUT_DIR))
    he_copy = eos_gen.copy_eos_file("helium", str(INPUT_DIR))
    if ps_copy:
        result["eos_polystyrene"] = str(ps_copy)
        log(f"    polystyrene-imx-008.cn4 ✓")
    else:
        log("    polystyrene-imx-008.cn4 复制失败!", "ERROR")
    if he_copy:
        result["eos_helium"] = str(he_copy)
        log(f"    he-imx-005.cn4 ✓")
    else:
        log("    he-imx-005.cn4 复制失败!", "ERROR")

    # ── 8. 运行脚本 ────────────────────────────────
    log("  [8/8] 生成运行脚本...", "STEP")
    setup_cmd = ShellScriptGenerator.build_setup_cmd(
        sim_path=sim_path, objdir=objdir, parfile=par_filename,
        flags="-1d +cartesian -nxb=16 +hdf5typeio species=cham,targ +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10",
    )
    script_config = {
        "sim_user_dir": SIM_USER_DIR, "dimension": 1,
        "platform": get_hpc_platform(), "setup_cmd": setup_cmd,
        "nprocs": cfg["nprocs"], "sim_path": sim_path, "object_dir": objdir,
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
    success = 0
    for f in files:
        ok = session.upload(str(f), f"{remote_dir}/")
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

    # ── 尝试 SLURM 提交 ──────────────────────────
    sbatch_cmd = f"cd {remote_dir} && {MODULES_LOAD} && sbatch submit_flash.sh 2>&1"
    out, err, code = session.run(sbatch_cmd, timeout=30)

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
    out, _, _ = session.run(
        f"ls -d {remote_dir}/outputfiles_* 2>/dev/null | head -1 || "
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
    log("  [analyze] 上传分析脚本...", "STEP")
    ok = session.upload(str(analysis_script_path), f"{remote_dir}/")
    if not ok:
        log("    分析脚本上传失败!", "ERROR")
        return False
    log(f"    hpc_analyze_ch_center.py 已上传")

    analysis_hw = cfg["analysis_half_width_um"] * 1e-4
    L0_cm = cfg["L0_um"] * 1e-4

    # ── 尝试使用超算 python/3.9.6 (有 h5py) ────
    log("  [analyze] 运行分析 (module load python/3.9.6)...", "STEP")
    analyze_cmd = (
        f"cd {remote_dir} && "
        f"module purge 2>/dev/null; "
        f"module load python/3.9.6 2>/dev/null; "
        f"export PYTHONIOENCODING=utf-8 && "
        f"python hpc_analyze_ch_center.py "
        f"--input-dir {actual_output_dir} "
        f"--output-dir {remote_dir}/analysis_plots "
        f"--center-half-width {analysis_hw} "
        f"--L0 {L0_cm} "
        f"2>&1"
    )
    out, err, code = session.run(analyze_cmd, timeout=600)
    log(f"    返回码: {code}")
    if out.strip():
        for line in out.strip().splitlines()[-15:]:
            log(f"      {line}")

    if code != 0:
        # 回退: 尝试系统 python3
        log("    回退: 尝试系统 python3...", "INFO")
        analyze_cmd2 = (
            f"cd {remote_dir} && "
            f"export PYTHONIOENCODING=utf-8 && "
            f"python3 hpc_analyze_ch_center.py "
            f"--input-dir {remote_dir}/outputfiles "
            f"--output-dir {remote_dir}/analysis_plots "
            f"--center-half-width {analysis_hw} "
            f"--L0 {L0_cm} "
            f"2>&1 | tail -50"
        )
        out2, err2, code2 = session.run(analyze_cmd2, timeout=600)
        log(f"    回退返回码: {code2}")
        if out2.strip():
            for line in out2.strip().splitlines()[-10:]:
                log(f"      {line}")
        if code2 != 0:
            log("    分析全部失败, 回退到本地分析", "WARN")
            return False

    # 验证 PNG 输出
    out, _, _ = session.run(
        f"ls {remote_dir}/analysis_plots/*.png 2>/dev/null | wc -l", timeout=10,
    )
    try:
        n_png = int(out.strip())
        if n_png > 0:
            log(f"    HPC 生成 {n_png} 张 PNG ✓", "OK")
            return True
    except ValueError:
        pass
    log("    未找到 PNG 文件", "WARN")
    return False


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


def main(credential_name: Optional[str] = None):
    print("\n" + "=" * 65)
    print(" FLASH LaserSlab1D Custom Simulation v1.1")
    print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    cfg = dict(config_constants)

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

    # ── 步骤 1: 生成输入文件 ────────────────────
    print("\n[步骤 1/5] 生成 FLASH 输入文件")
    print("-" * 50)
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        generate_input_files(cfg)
        log(f"输入文件目录: {INPUT_DIR}")
    except Exception as e:
        log(f"输入文件生成失败: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False

    # ── 步骤 2-5: 通过 RemoteSession 连接超算 ────
    print("\n[步骤 2/5] 连接超算并部署 (RemoteSession)")
    print("-" * 50)
    log("正在通过凭据系统连接超算 (自动选择最佳路由)...")

    try:
        with RemoteSession(credential_name=credential_name, verbose=True) as session:
            log("SSH 连接成功 ✓")

            # 创建远程目录
            remote_run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            remote_dir = f"~/{SIM_USER_DIR}/AI/AItemp/flash_custom_{remote_run_id}"
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

            # ── 步骤 4: 上传并运行分析脚本 ──────
            print("\n[步骤 4/5] 上传并运行 HPC 分析脚本")
            print("-" * 50)
            analysis_script = SCRIPT_DIR / "hpc_analyze_ch_center.py"
            if not analysis_script.exists():
                log(f"分析脚本不存在: {analysis_script} → 降级为下载 HDF5 本地分析", "WARN")
                analysis_ok = False
            else:
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
        # 手动上传提示: 账号/主机从凭据动态获取, 不硬编码
        _hint_host, _hint_user = "", ""
        try:
            from flash._core.credentials import load_ssh_credentials
            _cred = load_ssh_credentials() or {}
            _hint_user = _cred.get("username") or _cred.get("ssh_username", "")
            _hint_host = _cred.get("host", "")
        except Exception:
            pass
        if _hint_user and _hint_host:
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


def download_hdf5_to_local(session: RemoteSession, remote_dir: str, output_dir: str = ""):
    """下载 HDF5 文件到本地供 output_processors 分析。

    Args:
        session: RemoteSession 实例
        remote_dir: 远程运行根目录
        output_dir: 实际输出目录 (如 {remote_dir}/outputfiles_<ts>),
                    为空时自动查找 (outputfiles/ 或 outputfiles_* 时间戳目录)。
    """
    # 优先使用已知输出目录; 否则自动查找 (兼容 outputfiles/ 与 outputfiles_<ts>)
    if output_dir:
        candidates = [output_dir]
    else:
        out, _, _ = session.run(
            f"ls -d {remote_dir}/outputfiles_* 2>/dev/null | head -1 || echo NONE",
            timeout=10,
        )
        ts_dir = out.strip()
        candidates = [ts_dir] if ts_dir and ts_dir != "NONE" else [f"{remote_dir}/outputfiles"]

    chk_cmd = " ".join(
        f"ls {c}/*chk* 2>/dev/null" for c in candidates
    )
    out, _, _ = session.run(
        f"{chk_cmd} | head -50 || echo NO_H5",
        timeout=10,
    )
    if "NO_H5" in out or not out.strip():
        # 最后兜底: 递归 find
        out, _, _ = session.run(
            f"find {remote_dir} \\( -name '*chk*' -o -name '*plt*' \\) 2>/dev/null | head -50 || echo NO_H5",
            timeout=15,
        )
    if "NO_H5" in out or not out.strip():
        log("    未找到 HDF5 文件", "WARN")
        return

    remote_files = [l.strip() for l in out.strip().splitlines() if l.strip()]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # 每次运行 FLASH 的 chk 内容不同 → 下载到按时间戳区分的子目录,
    # 避免覆盖旧数据 / 跳过同名文件导致"下载 0 个"。
    run_sub = OUTPUT_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_sub.mkdir(parents=True, exist_ok=True)
    n = 0
    for rf in remote_files[:10]:
        local_path = str(run_sub / Path(rf).name)
        ok = session.download(rf, local_path)
        if ok:
            n += 1
    log(f"  下载 {n} 个 HDF5 文件到 {run_sub}", "OK")
    if n > 0:
        latest_sub = OUTPUT_DIR / "latest"
        latest_sub.mkdir(parents=True, exist_ok=True)
        # 同步最新一份到 latest/ 供本地分析使用 (始终指向最新运行)
        for f in run_sub.iterdir():
            dst = latest_sub / f.name
            try:
                import shutil
                shutil.copy2(str(f), str(dst))
            except Exception:
                pass
        # 本地分析优先使用 latest/ (最新运行数据)
        h5_files = sorted(latest_sub.glob("*chk*")) or sorted(latest_sub.glob("*plt*"))
    else:
        h5_files = sorted(OUTPUT_DIR.glob("*chk*")) or sorted(OUTPUT_DIR.glob("*plt*"))

    if h5_files:
        try:
            from flash.output_processors.loader import FlashDataLoader
            from flash.output_processors.plotter import FlashPlotter
            PLOTS_DIR.mkdir(parents=True, exist_ok=True)
            container = FlashDataLoader(str(h5_files[0])).load(compute_derived=True)
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
