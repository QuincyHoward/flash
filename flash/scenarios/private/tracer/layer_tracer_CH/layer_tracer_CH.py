"""
layer_tracer_CH 场景 — 1D 分层示踪靶 (CH) 仿真
═══════════════════════════════════════════════

复现原 runfiles_CH_CH_*um8.00e-022026 的 FLASH 输入配置（物理参数
内嵌于同包 _par_layers.py），通过多物种 input_gen 生成器重建：

  * 1D 笛卡尔域 x=[-0.04, 0.01] cm，FLASH_3T，NXB=16，MAXBLOCKS=1024
  * 单光束 0.351um 激光（透镜 x=-1.0，靶 x=0），82 点功率脉冲
  * 4 物种分层：cham(He) → samp(CH) → targ(CH) → samp(CH)
    （首层厚度由 layer_samp_um 控制，即原 tmp 命名中的 01/02/03um）
  * MGD 10 能群辐射，tabular EOS/opacity（ionmix4）

物理参数（82 点脉冲、MGD 群边界、扩散/热交换/水动力学等）均来自
_par_layers.py 内嵌字典，避免转录错误；仅把可调层厚度参数化。

用法:
  cd <flash 包目录>
  python -m flash.scenarios.private.tracer.layer_tracer_CH.layer_tracer_CH
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# 统一 stdout/stderr 为 UTF-8，避免 GBK 控制台报错
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


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
    # 首层(CH)示踪层厚度 (μm)，对应原 runfiles 命名 01/02/03um
    "layer_samp_um": 2.0,
    # 仿真域 (cm)
    "xmin": -0.04,
    "xmax": 0.01,
    # 网格
    "nblockx": 8,
    "lrefine_max": 9,
    # 输出频率（覆写规范参数的 2000，保证 dens 时空图有足够时间序列）
    "plot_interval_step": 1000,
    "checkpoint_interval_step": 400,
    # 维度 (用于按装置×维度自动配置资源核数)
    "dimension": 1,
    # MPI 进程数: None → 按装置×维度自动计算; 显式指定则覆盖
    "nprocs": None,
    # 超算 SLURM 分区/ntasks: None → 生成器按维度自动计算
    "slurm_partition": "v5_192",
    "slurm_ntasks": None,
}

# FLASH setup 标志 (wsl/hpc 共用)
SETUP_FLAGS = (
    "-1d +cartesian -nxb=16 +hdf5typeio species=cham,shld,samp,targ "
    "+mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 "
    "ed_maxPulseSections=300 -maxblocks=4096"
)

# 规范物理参数（原 tmp flash.par 全文解析后内嵌于 _par_layers.py，自包含）
from flash.scenarios.private.tracer._par_layers import CH_FLASH_PAR

# 场景目录
SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_DIR = SCRIPT_DIR / "flash_input"
OUTPUT_DIR = SCRIPT_DIR / "flash_output"
PLOTS_DIR = OUTPUT_DIR / "plots"


def log(msg: str, level: str = "INFO"):
    tag = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]", "STEP": "[-]"}.get(level, "[i]")
    print(f"  {tag} {msg}")


# ── 物种定义 (CH 场景) ─────────────────────────────────────
def build_species_defs(layer_samp_um: float) -> List[dict]:
    """构建 4 物种定义。cham=He，shld/samp/targ=CH (同一张表)。

    几何字段仅用于 Simulation_data/Simulation_init 的运行时参数声明；
    Simulation_initBlock 的边界由 BlockGenerator 直接内联。
    """
    ch_file = "CH-QC-1-001.cn4"
    he_file = "He-BADGER-TOPS-Final.cn4"
    samp_cm = layer_samp_um * 1e-4
    return [
        # 腔室: 稀氦
        {"name": "cham", "file": he_file, "rho": 1.0e-6, "A": 4.002602, "Z": 2.0},
        # 屏蔽层 (零宽，几何上退化，仅占位)
        {"name": "shld", "file": ch_file, "rho": 1.0, "A": 6.509, "Z": 3.5, "radius": 0.0},
        # 示踪首层 (厚度 = layer_samp_um)
        {"name": "samp", "file": ch_file, "rho": 1.0, "A": 6.509, "Z": 3.5,
         "radius": samp_cm, "height": 1.0e-2},
        # 靶芯层 (0.1um)
        {"name": "targ", "file": ch_file, "rho": 1.0, "A": 6.509, "Z": 3.5,
         "radius": 1.0e-5, "height": 0.0,
         "radius_param": "sim_targetRadius", "height_param": "sim_targetHeight"},
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

    species_defs = build_species_defs(cfg["layer_samp_um"])
    sim_path = f"{SIM_USER_DIR}/LaserSlab_custom"
    objdir = f"{SIM_USER_DIR}/LaserSlab_custom"
    par_filename = "laserslab_custom.par"

    from flash.scenarios.runner import default_nprocs
    # 维度感知资源默认值: 未显式指定时按装置×维度自动计算
    nprocs = cfg["nprocs"] or default_nprocs(cfg["dimension"], is_hpc=False)
    slurm_ntasks = cfg["slurm_ntasks"] or default_nprocs(cfg["dimension"], is_hpc=True)

    result: Dict[str, str] = {}
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. par（内嵌规范参数 CH_FLASH_PAR + 覆写）───────
    log("  [1/8] 生成 .par 文件...", "STEP")
    tmp_params = dict(CH_FLASH_PAR)
    par_gen = ParGeneratorExtended(simulation_name="LaserSlab_custom", dimension=1)
    # 清除维度默认参数，仅保留规范参数 + 下方覆写，避免未注册参数混入 par
    par_gen._params.clear()
    for k, v in tmp_params.items():
        par_gen.set(k, v)
    # 覆写可调参数
    par_gen.set("sim_sampRadius", cfg["layer_samp_um"] * 1e-4)
    par_gen.set("plotFileIntervalStep", cfg["plot_interval_step"])
    par_gen.set("checkpointFileIntervalStep", cfg["checkpoint_interval_step"])
    par_path = par_gen.save(str(INPUT_DIR / par_filename))
    result["par"] = str(par_path)
    log(f"    .par → {par_path.name} ✓")

    # ── 2. Config（多物种注册）────────────────────────────
    log("  [2/8] 生成 Config (4 species)...", "STEP")
    config_path = ConfigGenerator().save(
        str(INPUT_DIR / "Config"), simulation_path=sim_path, species_defs=species_defs,
    )
    result["config"] = str(config_path)
    log(f"    Config → Config ✓")

    # ── 3. Makefile (Simulation 片段) ─────────────────────
    log("  [3/8] 生成 Makefile...", "STEP")
    MakefileGenerator().save(str(INPUT_DIR / "Makefile"), sim_path=sim_path)
    result["makefile"] = str(INPUT_DIR / "Makefile")

    # ── 4. Simulation_data.F90 ────────────────────────────
    log("  [4/8] 生成 Simulation_data.F90...", "STEP")
    SimDataGenerator().save(str(INPUT_DIR / "Simulation_data.F90"), species=species_defs)
    result["sim_data"] = str(INPUT_DIR / "Simulation_data.F90")

    # ── 5. Simulation_init.F90 ────────────────────────────
    log("  [5/8] 生成 Simulation_init.F90...", "STEP")
    SimInitGenerator().save(str(INPUT_DIR / "Simulation_init.F90"), params={"species": species_defs})
    result["sim_init"] = str(INPUT_DIR / "Simulation_init.F90")

    # ── 6. Simulation_initBlock.F90（多物种分层）───────────
    log("  [6/8] 生成 Simulation_initBlock.F90 (4 species)...", "STEP")
    samp_cm = cfg["layer_samp_um"] * 1e-4
    target_radius = 1.0e-5
    builder = GridBuilder(dim=1, geometry="cartesian", domain=(cfg["xmin"], cfg["xmax"]))
    for sp in species_defs:
        builder.set_material(sp["name"], rho=sp["rho"], tele=290.11375,
                             tion=290.11375, trad=290.11375)
    # 分层边界（与规范配置一致: 0 → samp → targ → samp → 域外 cham）
    builder.add_region("samp_front", species="samp", x_range=(0.0, samp_cm))
    builder.add_region("targ", species="targ",
                       x_range=(samp_cm, samp_cm + target_radius))
    builder.add_region("samp_rear", species="samp",
                       x_range=(samp_cm + target_radius, 1.021e-2))
    block_gen = BlockGenerator(
        simulation_name="LaserSlab_custom", sim_path=sim_path,
        species=["cham", "shld", "samp", "targ"],
    )
    block_gen.build(builder)
    block_path = block_gen.save(str(INPUT_DIR / "Simulation_initBlock.F90"))
    result["sim_initblock"] = str(block_path)
    log(f"    Simulation_initBlock.F90 ({len(builder.regions)} regions) ✓")

    # ── 7. EOS/opacity .cn4（从 gen_eos_op 规范库复制）────
    log("  [7/8] 复制 EOS/opacity 表...", "STEP")
    from flash.input_gen.gen_eos_op import EOSOpacityGenerator
    eos_aliases = ["he_badger", "ch_qc"]
    for alias in eos_aliases:
        try:
            EOSOpacityGenerator().copy_eos_file(alias, INPUT_DIR)
            log(f"    {alias} ✓")
        except FileNotFoundError as exc:
            log(f"    {alias} 缺失: {exc}", "ERROR")

    # ── 8. run_flash.sh (wsl) + submit_flash.sh (hpc) ────
    log("  [8/8] 生成运行脚本 (wsl + hpc)...", "STEP")
    setup_cmd = ShellScriptGenerator.build_setup_cmd(
        sim_path=sim_path, objdir=objdir, parfile=par_filename, flags=SETUP_FLAGS,
    )
    wsl_config = {
        "sim_user_dir": SIM_USER_DIR, "dimension": cfg["dimension"],
        "platform": "local", "setup_cmd": setup_cmd,
        "nprocs": nprocs, "sim_path": sim_path, "object_dir": objdir,
        "flash_home": f"$HOME/{SIM_USER_DIR}/FLASH/FLASH4.8",
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
        "slurm_job_name": "layer_tracer_CH", "slurm_walltime": "24:00:00",
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

    log(f"  输入文件总数: {len(result)}", "OK")
    return result


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
    from flash.output_processors.loader import FlashDataLoader

    plt_files = sorted(outdir.glob("*plt_cnt*")) or sorted(outdir.glob("*plt*"))
    # 排除 tmax 强制输出的 "forced" 帧，避免打乱时间顺序
    plt_files = [f for f in plt_files if "forced" not in f.name]
    if not plt_files:
        log(f"无 plt 文件: {outdir}", "WARN")
        return 0

    records: List[tuple] = []
    xmin = xmax = None
    for f in plt_files:
        c = FlashDataLoader(str(f)).load(compute_derived=False)
        x = np.asarray(c.x).ravel()
        d = np.asarray(c.get("dens")).ravel()
        if x.size == 0 or d.size == 0:
            continue
        if xmin is None or x.min() < xmin:
            xmin = x.min()
        if xmax is None or x.max() > xmax:
            xmax = x.max()
        records.append((float(c.simulation_time), x, d))

    if xmin is None or not records:
        log("未能读取密度剖面", "WARN")
        return 0

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
    ax.set_title("Density x-t map (layer_tracer_CH)")
    fig.tight_layout()
    fig.savefig(str(save_path), dpi=150)
    plt.close(fig)
    log(f"    {save_path.name} ✓ ({len(plt_files)} plt files)")
    return len(plt_files)


# ── HPC 远程分析命令 ──────────────────────────────────────
def remote_analysis_cmd(outdir: str) -> str:
    """超算端绘图分析 (脚本已由 runner 上传至 analysis 目录)。"""
    return (
        "source /public1/soft/modules/module.sh >/dev/null 2>&1; "
        "module purge >/dev/null 2>&1; module load python/3.9.6 >/dev/null 2>&1; "
        "export PYTHONIOENCODING=utf-8 && "
        f"python layer_tracer_CH_remote_analysis.py "
        f"--outdir {outdir} --save dens_timespace.png --json summary.json 2>&1"
    )


def main():
    import argparse
    ap = argparse.ArgumentParser(description="layer_tracer_CH (wsl/hpc 一键切换)")
    ap.add_argument(
        "action", nargs="?", default=None,
        help="hpc 分阶段动作: all/upload/submit/monitor/analyze/download/status "
             "(默认按 RUN_MODE 完整运行)",
    )
    ap.add_argument(
        "--wait", type=int, default=0, help="hpc monitor 等待秒数 (默认不阻塞轮询一次)",
    )
    args = ap.parse_args()

    print("\n" + "=" * 65)
    print(" FLASH layer_tracer_CH Simulation")
    print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)
    cfg = dict(config_constants)
    print(f"\n  参数配置:")
    print(f"    域: [{cfg['xmin']}, {cfg['xmax']}] cm")
    print(f"    首层(CH)厚度: {cfg['layer_samp_um']} um")
    print(f"    维度: {cfg['dimension']}D")
    print("=" * 65)

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from flash.input_gen.gen_checker import DependencyChecker
        missing = DependencyChecker(INPUT_DIR).missing_standard()
        if missing:
            log(f"缺失 {len(missing)} 项必须文件: {missing}", "WARN")
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
            objdir=f"{SIM_USER_DIR}/LaserSlab_custom",
            analyze_local=plot_density_timespace,
            flash_home=user_flash_home(),
        )
        return run_wsl(wsl_spec, cfg)

    hpc_spec = HpcSpec(
        name="layer_tracer_CH",
        input_dir=INPUT_DIR, output_dir=OUTPUT_DIR, plots_dir=PLOTS_DIR,
        objdir=f"{SIM_USER_DIR}/LaserSlab_custom", flash_home=user_flash_home(),
        work_base=f"{user_flash_home()}/AI/Aitemp",
        remote_analysis_script="layer_tracer_CH_remote_analysis.py",
        remote_analysis_cmd=remote_analysis_cmd,
    )
    runner = HpcRunner(hpc_spec)
    if args.action:
        return runner.staged(args.action, wait_seconds=args.wait or None)
    return runner.all(cfg)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
