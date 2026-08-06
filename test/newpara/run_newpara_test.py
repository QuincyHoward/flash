"""
FLASH NewPara Multi-Zone Test — 编排脚本
═══════════════════════════════════════

测试目标:
  从 LaserSlabca1d (2物种) 扩展为 3物种 (cham/targ/targ2),
  所有区域边界和材料属性由 .par 参数控制（增量边界算法）。
  
流程:
  1. 通过 WSL bash 复制源文件 → setup → make → run
  2. 收集 HDF5 输出
  3. 用 output_processors 读取 plt_cnt_0000 密度网格
  4. 绘制密度分布图验证三区结构

参考:
  - ReDo042sp_CH042sp3umF8.00e-02/ (4物种多区模式)
  - docs/newparaset/README.md (新参数5步流程)
"""

import sys
import os
import subprocess
from pathlib import Path

# Bootstrap: find flash project root
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

# ── 路径设置 ──────────────────────────────────────────
TEST_DIR = Path(__file__).parent
FLASH_INPUT_DIR = TEST_DIR / "flash_input"
OUTPUT_DIR = TEST_DIR / "output"
PLOTS_DIR = OUTPUT_DIR / "plots"

# ── WSL 配置 ──────────────────────────────────────────
FLASH_HOME = "~/FLASH/FLASH4.8"
OBJ_DIR = "LaserSlab_newpara_test"
SIM_PATH = "LaserSlab_newpara_test"
SIM_SRC_DIR = f"{FLASH_HOME}/source/Simulation/SimulationMain/{SIM_PATH}"
FLASH_BIN = f"{FLASH_HOME}/{OBJ_DIR}/flash4"
PAR_FILE = "laserslab_newpara.par"

SETUP_CMD = (
    f"cd {FLASH_HOME} && "
    f"./setup -auto {SIM_PATH} -1d +cartesian -nxb=16 +hdf5typeio "
    f"species=cham,targ,targ2 +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10 "
    f"-objdir={OBJ_DIR} -parfile={PAR_FILE}"
)


def _to_wsl(path: Path) -> str:
    """将 Windows Path 转换为 WSL /mnt/ 路径。"""
    drive = path.drive[0].lower()
    return f"/mnt/{drive}{path.as_posix()[2:]}"


def wsl_run(cmd: str, timeout: int = 600) -> tuple:
    """在 WSL 中执行命令并返回 (stdout, stderr, returncode)。"""
    full_cmd = f"wsl bash -c '{cmd}'"
    result = subprocess.run(
        full_cmd, shell=True, capture_output=True, text=True, timeout=timeout
    )
    return result.stdout, result.stderr, result.returncode


def log(msg: str, level: str = "INFO"):
    tag = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]", "STEP": "[-]"}.get(level, "[i]")
    print(f"  {tag} {msg}")


def step_copy_sources() -> bool:
    """Step 1: 复制源文件到 WSL FLASH SimulationMain 目录。"""
    log("复制源文件到 WSL...", "STEP")
    # 创建远程目录
    cmd = f"mkdir -p {SIM_SRC_DIR}"
    out, err, code = wsl_run(cmd, timeout=10)
    if code != 0:
        log(f"创建目录失败: {err}", "ERROR")
        return False

    # 复制文件
    files_to_copy = [
        "Config", "Makefile", 
        "Simulation_data.F90", "Simulation_init.F90", "Simulation_initBlock.F90",
        "al-imx-003.cn4", "he-imx-005.cn4", "polystyrene-imx-008.cn4",
        PAR_FILE,
    ]
    for fname in files_to_copy:
        src = str(FLASH_INPUT_DIR / fname).replace("\\", "/")
        # 用 wslpath 或 _to_wsl 将本地路径转为分发的 WSL 路径
        wsl_input_dir = _to_wsl(FLASH_INPUT_DIR)
        cmd = f"cp {wsl_input_dir}/{fname} {SIM_SRC_DIR}/"
        out, err, code = wsl_run(cmd, timeout=10)
        if code != 0:
            log(f"  复制失败 {fname}: {err}", "WARN")
        else:
            log(f"  {fname} ✓")

    log("源文件复制完成", "OK")
    return True


def step_setup_and_make() -> bool:
    """Step 2: 执行 setup + make。"""
    log("执行 setup...", "STEP")
    out, err, code = wsl_run(SETUP_CMD, timeout=60)
    if code != 0:
        log(f"setup 失败:\n{out}\n{err}", "ERROR")
        return False
    log("setup 成功 ✓")

    log("执行 make -j4...", "STEP")
    make_cmd = f"cd {FLASH_HOME}/{OBJ_DIR} && make -j4 2>&1"
    out, err, code = wsl_run(make_cmd, timeout=600)
    if code != 0:
        log(f"make 失败 (exit={code}):\n{out[-2000:]}", "ERROR")
        return False
    log("make 成功 ✓")
    return True


def step_run_flash() -> bool:
    """Step 3: 复制 EOS + .par 到 obj_dir 并运行 FLASH。"""
    log("复制输入文件到运行目录...", "STEP")
    copy_cmd = (
        f"cd {FLASH_HOME}/{OBJ_DIR} && "
        f"cp {SIM_SRC_DIR}/*.cn4 ./ && "
        f"cp {SIM_SRC_DIR}/{PAR_FILE} ./"
    )
    out, err, code = wsl_run(copy_cmd, timeout=10)
    if code != 0:
        log(f"复制输入文件失败: {err}", "WARN")

    log("运行 FLASH 仿真...", "STEP")
    run_cmd = f"cd {FLASH_HOME}/{OBJ_DIR} && mpirun -np 1 ./flash4 -par_file {PAR_FILE} 2>&1"
    out, err, code = wsl_run(run_cmd, timeout=600)
    log(f"FLASH 返回码: {code}")
    if code != 0:
        log(f"FLASH 运行失败:\n{out[-1500:]}", "ERROR")
        return False
    # 打印最后几行
    for line in out.strip().splitlines()[-10:]:
        log(f"  {line}")
    return True


def step_collect_output() -> list:
    """Step 4: 收集 HDF5 文件到本地 output/ 目录。"""
    log("收集 HDF5 输出文件...", "STEP")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 列出远程 HDF5 文件
    ls_cmd = f"ls {FLASH_HOME}/{OBJ_DIR}/lasslab_hdf5_* 2>/dev/null | head -20"
    out, err, code = wsl_run(ls_cmd, timeout=10)
    remote_files = [f.strip() for f in out.strip().splitlines() if f.strip()]
    if not remote_files:
        log("未找到 HDF5 输出文件!", "WARN")
        return []

    # 通过 WSL 复制到本地 output/
    wsl_output_dir = _to_wsl(OUTPUT_DIR)
    collected = []
    for rf in remote_files[:10]:
        fname = os.path.basename(rf)
        cp_cmd = f"cp {rf} {wsl_output_dir}/{fname}"
        out2, err2, code2 = wsl_run(cp_cmd, timeout=30)
        if code2 == 0:
            collected.append(fname)
            log(f"  {fname} ✓")
        else:
            log(f"  复制失败 {fname}", "WARN")

    log(f"已收集 {len(collected)} 个文件", "OK")
    return collected


def step_plot_density(h5_files: list):
    """Step 5: 用 output_processors 绘制密度分布图。"""
    if not h5_files:
        log("没有 HDF5 文件可绘图", "WARN")
        return

    # 找第一个 plt 文件
    plt_files = [f for f in h5_files if "plt_cnt" in f]
    chk_files = [f for f in h5_files if "chk" in f]
    target = plt_files[0] if plt_files else (chk_files[0] if chk_files else h5_files[0])
    h5_path = str(OUTPUT_DIR / target)

    log(f"分析密度网格: {target}", "STEP")

    try:
        from flash.output_processors.loader import FlashDataLoader
        from flash.output_processors.plotter import FlashPlotter

        PLOTS_DIR.mkdir(parents=True, exist_ok=True)
        container = FlashDataLoader(h5_path).load()

        # 密度分布图
        plot_path = str(PLOTS_DIR / "dens_profile.png")
        FlashPlotter(container).plot(
            "dens", save_path=plot_path,
            title=f"Density Profile – NewPara Multi-Zone Test ({target})",
        )
        log(f"  密度图: {plot_path} ✓")

        # 打印密度统计
        dens = container.get_data("dens")
        print(f"  Density: min={dens.min():.6e}, max={dens.max():.4f}, mean={dens.mean():.4f}")

        if "targ2" in container.get_data_names():
            targ2 = container.get_data("targ2")
            targ = container.get_data("targ")
            cham = container.get_data("cham")
            log(f"  targ2 max: {targ2.max():.2e}, targ max: {targ.max():.2e}, cham max: {cham.max():.2e}", "INFO")

    except ImportError:
        log("output_processors 不可用，跳过绘图", "WARN")
    except Exception as e:
        log(f"绘图失败: {e}", "WARN")


def main():
    print("=" * 65)
    print(" FLASH NewPara Multi-Zone Test")
    print("=" * 65)

    # 确保目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    # 步骤 1: 复制源文件
    print("\n[Step 1/5] 复制源文件到 WSL")
    print("-" * 50)
    if not step_copy_sources():
        log("步骤1失败", "ERROR")
        return False

    # 步骤 2: Setup + Make
    print("\n[Step 2/5] 编译 FLASH")
    print("-" * 50)
    if not step_setup_and_make():
        log("步骤2失败", "ERROR")
        return False

    # 步骤 3: 运行
    print("\n[Step 3/5] 运行 FLASH 仿真")
    print("-" * 50)
    if not step_run_flash():
        log("步骤3失败", "ERROR")
        return False

    # 步骤 4: 收集输出
    print("\n[Step 4/5] 收集 HDF5 输出")
    print("-" * 50)
    h5_files = step_collect_output()
    if not h5_files:
        log("步骤4失败", "ERROR")
        return False

    # 步骤 5: 绘制密度图
    print("\n[Step 5/5] 绘制密度分布图")
    print("-" * 50)
    step_plot_density(h5_files)

    print("\n" + "=" * 65)
    print(" 测试完成!")
    print(f"  输出: {OUTPUT_DIR}")
    print(f"  图:   {PLOTS_DIR}")
    print("=" * 65)
    return True


if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ 测试流程成功!")
    else:
        print("\n❌ 测试流程失败!")
        sys.exit(1)
