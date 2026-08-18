"""
layer_tracer_CH 场景 — 1D 分层示踪靶 (CH) 仿真
═══════════════════════════════════════════════

复现 private/tracer/tmp/layer_tracer_CH 的 FLASH 输入配置（来自
runfiles_CH_CH_*um8.00e-022026），通过多物种 input_gen 生成器重建：

  * 1D 笛卡尔域 x=[-0.04, 0.01] cm，FLASH_3T，NXB=16，MAXBLOCKS=1024
  * 单光束 0.351um 激光（透镜 x=-1.0，靶 x=0），82 点功率脉冲
  * 4 物种分层：cham(He) → samp(CH) → targ(CH) → samp(CH)
    （首层厚度由 layer_samp_um 控制，即 tmp 命名中的 01/02/03um）
  * MGD 10 能群辐射，tabular EOS/opacity（ionmix4）

物理参数（82 点脉冲、MGD 群边界、扩散/热交换/水动力学等）均从 tmp
runfiles 的 flash.par 程序化提取，避免转录错误；仅把可调层厚度参数化。

用法:
  cd <flash 包目录>
  python -m flash.scenarios.private.tracer.layer_tracer_CH.layer_tracer_CH
"""

import sys
import os
import re
import time
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

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
    try:
        from flash._core.credentials import get_user_name
        return get_user_name()
    except ImportError:
        pass
    return os.environ.get("FLASH_SIM_USER_DIR", "hello")


SIM_USER_DIR = _get_sim_user_dir()

# ── 可配置参数 ────────────────────────────────────────────
config_constants = {
    # 首层(CH)示踪层厚度 (μm)，对应 tmp 命名 01/02/03um
    "layer_samp_um": 2.0,
    # 仿真域 (cm)
    "xmin": -0.04,
    "xmax": 0.01,
    # 网格
    "nblockx": 8,
    "lrefine_max": 9,
    # 输出频率（覆写 tmp 的 2000，保证 dens 时空图有足够时间序列）
    "plot_interval_step": 1000,
    "checkpoint_interval_step": 400,
    # MPI
    "nprocs": 4,
}

# 规范来源目录：tmp runfiles（物理参数/脉冲/EOS 的权威来源）
TMP_RUNFILES = (
    Path(__file__).resolve().parent.parent
    / "tmp" / "layer_tracer_CH"
    / "runfiles_CH_CH_02um8.00e-022026"
)

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


# ── tmp flash.par → 参数字典 ──────────────────────────────
def _parse_par_value(v: str):
    v = v.strip()
    if v.startswith('"') and v.endswith('"'):
        return v[1:-1]
    if v in (".true.", ".false."):
        return v == ".true."
    # 尝试数值
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def load_tmp_par(tmp_dir: Path) -> Dict[str, Any]:
    """读取 tmp flash.par 全部参数（去注释），返回 {key: value}。"""
    par_file = tmp_dir / "flash.par"
    params: Dict[str, Any] = {}
    for line in par_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        k, v = line.split("=", 1)
        params[k.strip()] = _parse_par_value(v)
    return params


# ── 步骤 1: 生成 FLASH 输入文件 ───────────────────────────
def generate_input_files(cfg: Dict[str, Any]) -> Dict[str, str]:
    from flash.input_gen.gen_par import ParGeneratorExtended
    from flash.input_gen.gen_config import ConfigGenerator
    from flash.input_gen.gen_makefile import MakefileGenerator
    from flash.input_gen.gen_sim_data import SimDataGenerator
    from flash.input_gen.gen_sim_init import SimInitGenerator
    from flash.input_gen.gen_sim_initblock import BlockGenerator, GridBuilder
    from flash.input_gen.gen_shell_script import ShellScriptGenerator

    if not TMP_RUNFILES.exists():
        raise RuntimeError(f"tmp 规范目录不存在: {TMP_RUNFILES}")

    species_defs = build_species_defs(cfg["layer_samp_um"])
    sim_path = f"{SIM_USER_DIR}/LaserSlab_custom"
    objdir = f"{SIM_USER_DIR}/LaserSlab_custom"
    par_filename = "laserslab_custom.par"

    result: Dict[str, str] = {}
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. par（从 tmp flash.par 提取全部物理参数）───────
    log("  [1/8] 生成 .par 文件...", "STEP")
    tmp_params = load_tmp_par(TMP_RUNFILES)
    par_gen = ParGeneratorExtended(simulation_name="LaserSlab_custom", dimension=1)
    # 清除维度默认参数，仅保留 tmp 规范参数 + 下方覆写，避免未注册参数混入 par
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
    # 分层边界（与 tmp 一致: 0 → samp → targ → samp → 域外 cham）
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

    # ── 7. EOS/opacity .cn4（从 tmp 复制）─────────────────
    log("  [7/8] 复制 EOS/opacity 表...", "STEP")
    eos_names = ["He-BADGER-TOPS-Final.cn4", "CH-QC-1-001.cn4"]
    for f in eos_names:
        src = TMP_RUNFILES / f
        if src.exists():
            (INPUT_DIR / f).write_bytes(src.read_bytes())
            log(f"    {f} ✓")
        else:
            log(f"    {f} 缺失!", "ERROR")

    # ── 8. run_flash.sh ───────────────────────────────────
    log("  [8/8] 生成运行脚本...", "STEP")
    setup_cmd = ShellScriptGenerator.build_setup_cmd(
        sim_path=sim_path, objdir=objdir, parfile=par_filename,
        flags="-1d +cartesian -nxb=16 +hdf5typeio species=cham,shld,samp,targ "
              "+mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 "
              "ed_maxPulseSections=300 -maxblocks=4096",
    )
    script_config = {
        "sim_user_dir": SIM_USER_DIR, "dimension": 1,
        "platform": "local", "setup_cmd": setup_cmd,
        "nprocs": cfg["nprocs"], "sim_path": sim_path, "object_dir": objdir,
        "flash_home": f"$HOME/{SIM_USER_DIR}/FLASH/FLASH4.8",
    }
    script_gen = ShellScriptGenerator(config=script_config)
    script_gen.save(str(INPUT_DIR / "run_flash.sh"), "wsl", par_file=par_filename)
    result["script_wsl"] = str(INPUT_DIR / "run_flash.sh")
    log(f"    run_flash.sh ✓")

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


# ── WSL 运行 ──────────────────────────────────────────────
def _to_wsl_path(win_path: Path) -> str:
    s = str(win_path)
    drive, rest = s.split(":", 1)
    return "/mnt/" + drive.lower() + rest.replace("\\", "/")


def _tail_lines(path: Path, n: int = 25, max_len: int = 160) -> str:
    """读取文件末尾 n 行（运行中日志），每行截断到 max_len 字符。"""
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
    每 120s 看到一小段真实输出（编译进度/网格细化/时间步进等）。

    Returns:
        (WSL 返回码, 日志文件当前全部内容)。
    """
    start = time.monotonic()
    proc = subprocess.Popen(
        ["wsl", "bash", "-c", cmd],
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
    wsl_dir = _to_wsl_path(INPUT_DIR)
    run_sh = INPUT_DIR / "run_flash.sh"
    if not run_sh.exists():
        log(f"run_flash.sh 不存在: {run_sh}", "ERROR")
        return False

    print("\n[WSL] 运行 FLASH (setup→编译→运行→收集)")
    print("-" * 50)
    run_log_name = "wsl_console.log"
    console_log = INPUT_DIR / run_log_name
    try:
        console_log.unlink()
    except OSError:
        pass
    cmd = (
        f"cd {wsl_dir} && bash run_flash.sh > {run_log_name} 2>&1; "
        f"echo \"FLASH_EXIT_CODE=$?\" >> {run_log_name}"
    )
    log(f"执行: wsl bash -c \"{cmd[:100]}...\"")
    log("首次运行需编译 FLASH，可能耗时 10~60 分钟 ...")

    # 清理旧输出/旧 objdir，确保用新 setup 标志重编译且无残留文件污染
    log("清理旧 objdir 与本地输出...", "STEP")
    for p in [INPUT_DIR / "outputfiles", PLOTS_DIR]:
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
            p.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["wsl", "bash", "-c",
             f"cd {wsl_dir} && rm -f wsl_run.log {run_log_name} flash_run.log "
             "&& rm -rf ~/QC/FLASH/FLASH4.8/QC/LaserSlab_custom"],
            capture_output=True, timeout=120,
        )
    except Exception:
        pass

    max_attempts = 3
    flash_rc = None
    console_txt = ""
    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            log(f"WSL 返回无有效输出，重试 ({attempt}/{max_attempts})...", "WARN")
        try:
            flash_rc, console_txt = _run_wsl_with_progress(
                cmd, console_log, interval=120.0, timeout=7200.0,
            )
        except FileNotFoundError:
            log("未找到 wsl 命令。请确认已安装 WSL。", "ERROR")
            return False
        except subprocess.TimeoutExpired:
            log("WSL 运行超时 (2 小时)", "ERROR")
            return False
        combined = console_txt.strip()
        if flash_rc == 0 and console_txt.strip():
            break
        if flash_rc != 0 and combined:
            break
        log(f"WSL 无输出 (exit={flash_rc})，5s 后重试...", "WARN")
        time.sleep(5)

    if flash_rc is None:
        log("WSL 启动失败 (多次重试后仍无输出)", "ERROR")
        return False

    # 优先解析 run_flash.sh 自身输出的 "FLASH exit code: N"（可靠，不受管道影响）
    flash_exit = 1
    m = re.findall(r"FLASH exit code:\s*(\d+)", console_txt)
    if m:
        flash_exit = int(m[-1])
    if "DRIVER_ABORT:" in console_txt or "Driver_abort called" in console_txt:
        flash_exit = 1

    log(combined[-3000:] if len(combined) > 3000 else combined)
    wsl_log = INPUT_DIR / "wsl_run.log"
    wsl_log.write_text(combined, encoding="utf-8", errors="replace")
    if flash_exit != 0:
        log(f"FLASH 运行失败 (exit={flash_exit})，完整日志: {wsl_log}", "ERROR")
        return False
    log(f"FLASH 运行成功 ✓ (完整日志: {wsl_log})")

    outdir = INPUT_DIR / "outputfiles"
    h5s = sorted(outdir.glob("*plt_cnt*")) or sorted(outdir.glob("*chk*"))
    if not h5s:
        log(f"未找到 HDF5 输出: {outdir}", "ERROR")
        return False
    log(f"找到 {len(h5s)} 个 HDF5 输出: {outdir}")

    print("\n[分析] 制作 dens 时空彩图")
    print("-" * 50)
    plot_density_timespace(outdir, PLOTS_DIR / "dens_timespace.png")

    print("\n" + "=" * 65)
    print(" WSL 全流程完成!")
    print(f"  输入文件目录: {INPUT_DIR}")
    print(f"  输出结果目录: {outdir}")
    print(f"  分析图像目录: {PLOTS_DIR}")
    print("=" * 65)
    return True


def main():
    print("\n" + "=" * 65)
    print(" FLASH layer_tracer_CH Simulation")
    print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)
    cfg = dict(config_constants)
    print(f"\n  参数配置:")
    print(f"    域: [{cfg['xmin']}, {cfg['xmax']}] cm")
    print(f"    首层(CH)厚度: {cfg['layer_samp_um']} um")
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

    return main_wsl(cfg)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
