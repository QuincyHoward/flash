"""
FLASH LaserSlab1D 本地运行 Demo v2.2（独立运行文件夹 + 正确文件部署）
═════════════════════════════════════════════════════════════════

创建一个完全独立的仿真运行文件夹（包含所有必要输入文件 + 一键执行脚本），
然后自动部署到 WSL 中 FLASH 仿真所需的正确位置，并执行完整流程。

FLASH 文件部署说明:
  run/ 中的源文件 (Config, Makefile, .F90, .cn4, .par) → 复制到
  $FLASH_HOME/source/Simulation/SimulationMain/{SIM_USER_DIR}/LaserSlab_local/
  供 `./setup -auto {SIM_USER_DIR}/LaserSlab_local ...` 使用

  -objdir={SIM_USER_DIR}/LaserSlab_local → 编译目录为 $FLASH_HOME/{SIM_USER_DIR}/LaserSlab_local/
  -par_file=laserslab1d_demo.par → 默认 .par 文件在 SimulationMain 中

运行方式:
  cd E:/ProgramsPATH/AI/WorkBuddy/WorkBuddyFiles/AItest/Plan_for_py/PhySimX
  python -m flash.scenarios.flash_demo.demo_local.laserslab1d_local_demo

输出:
  demo_task/laserslab1d_local_demo/
    ├── run/                    ← 独立运行文件夹 (可一键执行)
    │   ├── laserslab1d_demo.par
    │   ├── Config / Makefile
    │   ├── *.F90 / *.cn4
    │   ├── run_flash.bat       ← Windows 一键脚本
    │   ├── run_flash.sh        ← WSL/Linux 一键脚本
    │   └── submit_flash.sh     ← SLURM 提交脚本
    └── output/                 ← 仿真输出 (HDF5 + 图像)
"""

import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

# 必须先设置 sys.path，否则后续无法导入 flash.credentials

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


# ── 用户信息（优先从 credentials 获取，再回落环境变量）──
def _get_sim_user_dir() -> str:
    """三层回落: credentials → 环境变量 → 'hello'"""
    try:
        from flash._core.credentials import get_user_name
        return get_user_name()
    except ImportError:
        pass
    return os.environ.get("FLASH_SIM_USER_DIR", "hello")

SIM_USER_DIR = _get_sim_user_dir()
WSL_DISTRO = os.environ.get("WSL_DISTRO", "Ubuntu-22.04")

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

print(f"  [Demo] PROJECT_ROOT = {PROJECT_ROOT}")
print(f"  [Demo] SIM_USER_DIR = {SIM_USER_DIR}")
print(f"  [Demo] WSL_DISTRO  = {WSL_DISTRO}")

DEMO_TASK_BASE = Path(__file__).parent / "demo_task" / "laserslab1d_local_demo"
DEMO_RUN_DIR = DEMO_TASK_BASE / "run"        # 独立运行文件夹 (staging)
DEMO_OUTPUT_DIR = DEMO_TASK_BASE / "output"


def wsl_cmd(cmd: str, timeout: int = 120) -> subprocess.CompletedProcess:
    """在 WSL 中执行命令"""
    return subprocess.run(
        ["wsl", "-d", WSL_DISTRO, "--", "bash", "-c", cmd],
        capture_output=True, text=True, timeout=timeout,
    )


def log(msg: str, level: str = "INFO"):
    tag = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]", "STEP": "[-]"}.get(level, "[i]")
    print(f"  {tag} {msg}")


def main():
    print("\n" + "=" * 60)
    print(" FLASH LaserSlab1D local run Demo (v2.2)")
    print(f" User dir: {SIM_USER_DIR}")
    print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # ── 构建自定义仿真路径 ────────────────────────
    sim_path = f"{SIM_USER_DIR}/LaserSlab_local"
    objdir = f"{SIM_USER_DIR}/LaserSlab_local"
    par_filename = "laserslab1d_demo.par"
    flash_home = f"~/{SIM_USER_DIR}/FLASH/FLASH4.8"

    # ── 步骤 1: 生成全部输入文件到独立运行文件夹 ──
    print("\n[步骤 1] 生成全部输入文件到独立运行文件夹")
    print("-" * 50)

    try:
        from flash.input_gen import create_input_files
        from flash.input_gen.gen_shell_script import ShellScriptGenerator
    except ImportError as e:
        log(f"导入失败: {e}", "ERROR")
        return None

    # 构建完整的 setup 命令
    setup_cmd = ShellScriptGenerator.build_setup_cmd(
        sim_path=sim_path,
        objdir=objdir,
        parfile=par_filename,
    )
    log(f"SETUP_CMD: {setup_cmd}")
    log(f"  sim_path: {sim_path}  (→ SimulationMain/{sim_path}/)")
    log(f"  -objdir:  {objdir}   (→ $FLASH_HOME/{objdir}/)")
    log(f"  -parfile: {par_filename} (→ SimulationMain/{sim_path}/)")

    DEMO_RUN_DIR.mkdir(parents=True, exist_ok=True)
    result = create_input_files(
        output_dir=str(DEMO_RUN_DIR),
        dimension=1,
        simulation_name="LaserSlab1d_demo",
        target_material="aluminum",
        chamber_gas="helium",
        n_beams=1,
        par_filename=par_filename,
        generate_scripts=True,
        copy_eos_files=True,
        setup_cmd=setup_cmd,
        sim_user_dir=SIM_USER_DIR,
    )
    log(f"已生成 {len(result)} 个文件到 {DEMO_RUN_DIR}/:")
    for ftype, fpath in result.items():
        log(f"  - {Path(fpath).name}")

    # ── 步骤 2: 检查 WSL 环境 ──────────────────
    print("\n[步骤 2] 检查 WSL 环境")
    print("-" * 50)

    r = wsl_cmd("echo 'WSL_OK'", timeout=10)
    if "WSL_OK" not in r.stdout:
        log(f"WSL 不可用: {r.stderr[:200]}", "ERROR")
        log("请确保 WSL 已安装并配置", "ERROR")
        return None
    log("WSL 环境正常 ✓")

    # 检查 FLASH_HOME 是否存在
    flash_home_wsl = flash_home.replace("~", "/root")
    r = wsl_cmd(f"test -d '{flash_home_wsl}' && echo 'HOME_OK' || echo 'HOME_MISSING'", timeout=10)
    if "HOME_OK" not in r.stdout:
        log(f"FLASH 源码目录不存在: {flash_home_wsl}", "WARN")
        log("Demo 将先复制源文件到 SimulationMain，然后执行 setup + make 创建编译目录", "INFO")
    else:
        log(f"FLASH 源码目录存在: {flash_home_wsl} ✓")

    # ── 步骤 3: 复制文件到 WSL 暂存目录并执行 ──
    # run_flash.sh 会处理:
    #   1) 复制源文件到 SimulationMain/sim_path/
    #   2) 执行 setup + make
    #   3) 复制 .par/.cn4 到编译目录
    #   4) 运行 FLASH
    #   5) 收集输出到 outputfiles/
    print("\n[步骤 3] 部署到 WSL 并运行 FLASH")
    print("-" * 50)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir_wsl = f"/tmp/flash_demo_local_{run_id}"
    wsl_cmd(f"mkdir -p {run_dir_wsl}", timeout=10)

    # 复制所有文件到 WSL 暂存目录
    n_copied = 0
    for f in DEMO_RUN_DIR.iterdir():
        if f.is_file():
            f_wsl = str(f).replace("\\", "/").replace("E:/", "/mnt/e/")
            r = wsl_cmd(f"cp '{f_wsl}' {run_dir_wsl}/", timeout=10)
            if r.returncode == 0:
                n_copied += 1
            else:
                log(f"复制失败: {f.name}", "WARN")
    log(f"已复制 {n_copied} 个文件到 {run_dir_wsl}")

    # 执行 run_flash.sh（包含 SimulationMain 复制 + setup + make + run）
    log("正在运行 FLASH 完整流程...")
    log(f"  脚本位置: {run_dir_wsl}/run_flash.sh")
    log(f"  SimulationMain 目标: {flash_home}/source/Simulation/SimulationMain/{sim_path}/")

    r = wsl_cmd(f"cd {run_dir_wsl} && bash run_flash.sh 2>&1 | tail -100", timeout=360)

    log(f"FLASH 返回码: {r.returncode}")
    if r.stdout.strip():
        log(f"输出（末 800 字符）:")
        for line in r.stdout.strip().splitlines()[-20:]:
            log(f"  {line}")

    if r.returncode != 0:
        log("FLASH 执行失败，请检查日志", "ERROR")
        r_log = wsl_cmd(f"cat {run_dir_wsl}/flash_run.log 2>/dev/null | tail -30", timeout=10)
        if r_log.stdout.strip():
            log(f"FLASH 日志: {r_log.stdout.strip()[-500:]}")
    else:
        log("FLASH 仿真完成 ✓")

    # ── 步骤 4: 下载 HDF5 输出 ──────────────
    print("\n[步骤 4] 下载 HDF5 输出文件")
    print("-" * 50)

    # 输出文件被 run_flash.sh 收集到 {run_dir_wsl}/outputfiles/
    h5_files_wsl = []
    r = wsl_cmd(f"ls {run_dir_wsl}/outputfiles/*chk* {run_dir_wsl}/outputfiles/*plt* 2>/dev/null | head -50", timeout=10)
    if r.stdout.strip():
        h5_files_wsl = [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]

    if not h5_files_wsl:
        # 再试试 run_dir_wsl 本身
        r = wsl_cmd(f"find {run_dir_wsl} -name '*chk*' -o -name '*plt*' 2>/dev/null | head -30", timeout=10)
        h5_files_wsl = [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]

    if not h5_files_wsl:
        log("WSL 中未找到输出文件", "WARN")
        r2 = wsl_cmd(f"ls -la {run_dir_wsl}/ 2>/dev/null; ls -la {run_dir_wsl}/outputfiles/ 2>/dev/null", timeout=10)
        log(f"运行目录: {r2.stdout.strip()[:500]}")
    else:
        log(f"找到 {len(h5_files_wsl)} 个输出文件")
        for hf in h5_files_wsl[:5]:
            log(f"  - {Path(hf).name}")

        # 直接通过 WSL 的 /mnt/e/ 挂载复制到 Windows
        DEMO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_win = str(DEMO_OUTPUT_DIR).replace("\\", "/").replace("E:", "/mnt/e")

        # 复制所有 chk 和 plt 文件
        r_cp = wsl_cmd(
            f"cp {run_dir_wsl}/outputfiles/*chk* '{out_win}/' 2>/dev/null; "
            f"cp {run_dir_wsl}/outputfiles/*plt* '{out_win}/' 2>/dev/null; "
            f"cp {run_dir_wsl}/outputfiles/flash_run.log '{out_win}/' 2>/dev/null; "
            f"echo 'CP_DONE'",
            timeout=120,
        )
        if "CP_DONE" in r_cp.stdout:
            log("输出文件已复制到本地 ✓")

    # 列出本地输出 (FLASH 输出文件名不含 .h5 后缀, 使用 *chk* 和 *plt* 模式)
    h5_local = (
        list(DEMO_OUTPUT_DIR.glob("*chk*"))
        + list(DEMO_OUTPUT_DIR.glob("*plt*"))
        + list(DEMO_OUTPUT_DIR.glob("*.h5"))
    )
    if h5_local:
        log(f"本地输出文件: {len(h5_local)} 个")
        for hf in h5_local[:5]:
            log(f"  - {hf.name}")
    else:
        log("本地输出目录为空，可能复制过程有误", "WARN")
        log(f"  输出路径: {DEMO_OUTPUT_DIR}")

    # ── 步骤 5: 使用 output_processors 分析 ──
    print("\n[步骤 5] 使用 output_processors 分析输出")
    print("-" * 50)

    if not h5_local:
        log("无输出文件可分析", "WARN")
    else:
        try:
            from flash.output_processors.loader import FlashDataLoader
            from flash.output_processors.plotter import FlashPlotter

            h5_file = [f for f in h5_local if "chk" in f.name]
            if not h5_file:
                h5_file = h5_local
            h5_file = h5_file[0]
            log(f"加载: {h5_file.name}")

            loader = FlashDataLoader(str(h5_file))
            container = loader.load(compute_derived=True)
            log(f"维度: {container.ndim}D")
            log(f"变量数: {len(container.data)}")

            plot_dir = DEMO_OUTPUT_DIR / "plots"
            plot_dir.mkdir(exist_ok=True)

            plotter = FlashPlotter(container)
            plot_path = plot_dir / "dens_distribution.png"
            plotter.plot("dens", save_path=str(plot_path), title="Density Distribution (LaserSlab1D Local)")
            log(f"密度图: {plot_path} ✓")

            if len(h5_local) > 1:
                for i, hf in enumerate(h5_local[:min(5, len(h5_local))]):
                    try:
                        c = FlashDataLoader(str(hf)).load(compute_derived=True)
                        FlashPlotter(c).plot("dens", save_path=str(plot_dir / f"dens_t{i:04d}.png"), title=f"Density t={c.simulation_time:.2e}s")
                    except Exception:
                        pass
                log(f"多时间步图: {min(5, len(h5_local))} 张 ✓")

        except ImportError as e:
            log(f"output_processors 导入失败: {e}", "WARN")
        except Exception as e:
            log(f"分析失败: {e}", "WARN")

    # ── 完成 ─────────────────────────────────
    print("\n" + "=" * 60)
    print(" 全流程完成!")
    print(f"  独立运行文件夹: {DEMO_RUN_DIR}")
    log(f"    包含一键执行脚本:")
    log(f"      * run_flash.bat  (Windows WSL)")
    log(f"      * run_flash.sh   (WSL/Linux)")
    log(f"      * submit_flash.sh (SLURM)")
    log(f"  可直接执行: cd {DEMO_RUN_DIR} && bash run_flash.sh")
    print(f"  仿真输出: {DEMO_OUTPUT_DIR}")
    print(f"  HDF5 文件: {len(h5_local) if h5_local else 0} 个")
    log(f"  FLASH 文件部署说明:")
    log(f"    源文件 → $FLASH_HOME/source/Simulation/SimulationMain/{sim_path}/")
    log(f"    编译   → $FLASH_HOME/{objdir}/")
    print(f"  SETUP_CMD: {setup_cmd}")
    print("=" * 60)

    return {"run_dir": str(DEMO_RUN_DIR), "output_dir": str(DEMO_OUTPUT_DIR)}


if __name__ == "__main__":
    result = main()
    if result:
        print("\n Demo 成功!")
    else:
        print("\n Demo 失败!")
        sys.exit(1)
