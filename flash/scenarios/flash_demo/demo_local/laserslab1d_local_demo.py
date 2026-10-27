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
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))


# ── 运行模式 ─────────────────────────────────────────
# 本 Demo 仅实现 wsl 本机运行; 切换 hpc 请用 trace/center 场景的共享 runner。
# 一键切换即修改此行; 也可用环境变量 FLASH_RUN_MODE 覆盖 (resolve_run_mode 统一规则)
RUN_MODE = "wsl"


# ── 用户信息（统一走 runner.get_sim_user_dir: credentials → env → hello）──
def _get_sim_user_dir() -> str:
    from flash.scenarios.core.runner import get_sim_user_dir as _sud
    return _sud()

SIM_USER_DIR = _get_sim_user_dir()
WSL_DISTRO = os.environ.get("WSL_DISTRO", "Ubuntu-22.04")

PROJECT_ROOT = _PARENT

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

    from flash.scenarios.core.runner import resolve_run_mode
    run_mode = resolve_run_mode(RUN_MODE)
    log(f"运行模式: {run_mode} (RUN_MODE={RUN_MODE}, env FLASH_RUN_MODE={os.environ.get('FLASH_RUN_MODE', '-')})", "INFO")
    if run_mode != "wsl":
        log("demo_local 仅实现 wsl 运行; hpc 请使用 trace/center 场景的共享 runner", "ERROR")
        return False

    # ── 构建自定义仿真路径 ────────────────────────
    sim_path = f"{SIM_USER_DIR}/LaserSlab_local"
    objdir = f"{SIM_USER_DIR}/LaserSlab_local"
    par_filename = "laserslab1d_demo.par"
    flash_home = f"~/{SIM_USER_DIR}/FLASH/FLASH4.8"
    flash_home_wsl_fallback = f"/root/{SIM_USER_DIR}/FLASH/FLASH4.8"

    # ── 步骤 0: 检查 WSL 环境并探测 FLASH 安装 ──────────────────
    # ★ 必须排在"生成脚本"之前: run_flash.sh 里 FLASH_HOME 是**生成时写死**的,
    #   事后探测到不同路径也得重新生成脚本, 否则脚本仍指向错误目录。
    print("\n[步骤 0] 检查 WSL 环境与 FLASH 安装")
    print("-" * 50)

    r = wsl_cmd("echo 'WSL_OK'", timeout=10)
    if "WSL_OK" not in r.stdout:
        log(f"WSL 不可用: {r.stderr[:200]}", "ERROR")
        log("请确保 WSL 已安装并配置", "ERROR")
        return None
    log("WSL 环境正常 ✓")

    # ── 探测真实可用的 FLASH 引擎树 ─────────────────
    # ★ 为什么要探测而不是信任 `~/{SIM_USER_DIR}/FLASH/FLASH4.8`:
    #   1) 该路径不存在时脚本会静默失败 (且返回码被管道吞掉 → 报"仿真完成") ;
    #   2) 该路径存在但**不是引擎树**时 (实测曾出现 flash-sim 仓库克隆占据该路径,
    #      只有 source/Simulation 被当 staging 用), setup/make 一样跑不通。
    #   ⇒ 用 FLASH 的真正标志物判据: <root>/setup (可执行) + SimulationMain/ 存在。
    #   ★ 必须用 find 而非 shell glob (`for d in "$HOME"/*/FLASH/FLASH4.8`):
    #     经 Windows → wsl.exe → bash -c 三层传参后, glob 展开的 `*` 会被
    #     命令行解析吃掉, 结果**无输出也无报错**(09-23 实测, 静默漏过)。
    #     find 是单命令、无需 shell 展开, 跨层稳定。
    r = wsl_cmd(
        'find "$HOME" -maxdepth 3 -type d -name FLASH4.8 2>/dev/null',
        timeout=30,
    )
    roots = [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]
    candidates = []
    for root in roots:
        chk = wsl_cmd(
            f'if [ -f "{root}/setup" ] && [ -d "{root}/source/Simulation/SimulationMain" ]; '
            f'then echo OK; else echo NO; fi',
            timeout=15,
        )
        if "OK" in chk.stdout:
            candidates.append(root)
    if candidates:
        if len(candidates) > 1:
            log(f"发现 {len(candidates)} 个 FLASH 安装:", "WARN")
            for c in candidates:
                log(f"  - {c}")
            # ★ 优先取与 SIM_USER_DIR 一致的那个 (~/<user>/FLASH/FLASH4.8),
            #   否则用户会困惑"为什么用的是别人的目录"。
            preferred = f"/root/{SIM_USER_DIR}/FLASH/FLASH4.8"
            if preferred in candidates:
                candidates = [preferred] + [c for c in candidates if c != preferred]
                log(f"优先采用与 SIM_USER_DIR({SIM_USER_DIR}) 一致的: {preferred}", "INFO")
        flash_home = candidates[0]        # ★ 用探测到的真实路径 (形如 /root/QC/FLASH/FLASH4.8)
        log(f"FLASH 引擎树: {flash_home} ✓ (含 setup + SimulationMain)")
    else:
        log(f"未探测到可用 FLASH 引擎树, 按用户名推导: {flash_home_wsl_fallback}", "WARN")
        r2 = wsl_cmd(
            f"test -f '{flash_home_wsl_fallback}/setup' && echo OK || echo NO",
            timeout=10,
        )
        if "OK" not in r2.stdout:
            log(f"该路径也不存在 setup: {flash_home_wsl_fallback}", "ERROR")
            log("请先在 WSL 中解压并配置 FLASH4.8 (需含 setup 与 source/Simulation/SimulationMain),", "ERROR")
            log("或用环境变量 FLASH_SIM_USER_DIR 指定安装用户名后重试", "ERROR")
            return None
        flash_home = flash_home_wsl_fallback

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
        flash_home=flash_home,   # ★ 关键: 否则 run_flash.sh 拿到不带用户名的
                                  #   默认 $HOME/FLASH/FLASH4.8 ⇒ [1/5] 直接 exit 1
    )
    log(f"已生成 {len(result)} 个文件到 {DEMO_RUN_DIR}/:")
    for ftype, fpath in result.items():
        log(f"  - {Path(fpath).name}")

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
    log(f"  FLASH_HOME: {flash_home}")
    log(f"  SimulationMain 目标: {flash_home}/source/Simulation/SimulationMain/{sim_path}/")

    # ★★ 关键: 不能写成 `bash run_flash.sh 2>&1 | tail -100` ——
    #   管道的 $? 是**最后一个命令 (tail)** 的返回码, 恒为 0,
    #   于是 FLASH 内部 `exit 1` 也被吞掉 ⇒ 打印"仿真完成 ✓"、退出码 0、
    #   最终"Demo 成功!", 但 output/ 为空 (本次故障的真表象)。
    #   ⇒ 把返回码写进**独立文件**再读回; 同时把完整日志落盘便于事后查。
    #   (不依赖 stdout 里的标记行: echo 与 tail 的输出在管道里可能交错丢行,
    #    09-23 实测导致 rc 被误判为 -1 而误报"Demo 失败")
    log_file = f"{run_dir_wsl}/demo_console.log"
    rc_file = f"{run_dir_wsl}/demo_flash_rc.txt"
    r = wsl_cmd(
        f"cd {run_dir_wsl} && bash run_flash.sh > {log_file} 2>&1; "
        f"echo $? > {rc_file}; tail -60 {log_file}",
        timeout=7200,
    )

    # 读取 FLASH 的真实返回码 (Python 侧 returncode 不可信: 整体命令最后是 tail)
    flash_rc = None
    r_rc = wsl_cmd(f"cat {rc_file} 2>/dev/null", timeout=15)
    if r_rc.stdout.strip():
        try:
            flash_rc = int(r_rc.stdout.strip().splitlines()[0])
        except ValueError:
            flash_rc = None
    if flash_rc is None:
        flash_rc = -1
        log("未能解析 FLASH 返回码 (脚本可能未正常启动)", "ERROR")

    log(f"FLASH 真实返回码: {flash_rc}  (bash 层返回码 {r.returncode} 不可信, 已忽略)")
    if r.stdout.strip():
        log("输出（末 60 行）:")
        for line in r.stdout.strip().splitlines()[-25:]:
            log(f"  {line}")

    flash_failed = flash_rc != 0
    if flash_failed:
        log(f"FLASH 执行失败 (rc={flash_rc})，完整日志: {log_file}", "ERROR")
        r_log = wsl_cmd(f"grep -nE 'ERROR|Error|error:|Abort|STOP|No such' {log_file} 2>/dev/null | head -15", timeout=15)
        if r_log.stdout.strip():
            log("错误行:", "ERROR")
            for line in r_log.stdout.strip().splitlines()[:15]:
                log(f"  {line}")
    else:
        log("FLASH 仿真完成 ✓")

    # 拉完整日志回本地 (便于 Windows 侧查看, 也避免 /tmp 被清理后无从排查)
    try:
        DEMO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_win = str(DEMO_OUTPUT_DIR).replace("\\", "/").replace("E:", "/mnt/e")
        wsl_cmd(f"cp {log_file} '{out_win}/demo_console.log' 2>/dev/null; echo OK", timeout=30)
    except Exception as e:  # noqa: BLE001
        log(f"日志回传失败（非致命）: {e}", "WARN")

    # ── 步骤 4: 下载 HDF5 输出 ──────────────
    print("\n[步骤 4] 下载 HDF5 输出文件")
    print("-" * 50)

    # 输出文件被 run_flash.sh 收集到 {run_dir_wsl}/outputfiles/run_NNNNNN/
    # ★ 必须用 find -name 而不是 `ls outputfiles/*chk*`:
    #   run_flash.sh 的自动 run_id 机制会把产物放进**子目录** run_NNNNNN/,
    #   单层 glob 匹配不到 ⇒ 即使 FLASH 成功也会报"未找到输出文件"。
    h5_files_wsl = []
    r = wsl_cmd(
        f"find {run_dir_wsl}/outputfiles -type f \\( -name '*chk*' -o -name '*plt*' -o -name '*.h5' \\) "
        f"2>/dev/null | head -80",
        timeout=15,
    )
    if r.stdout.strip():
        h5_files_wsl = [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]

    if not h5_files_wsl:
        # 再扫整个暂存目录 (覆盖自定义收集路径的情形)
        r = wsl_cmd(
            f"find {run_dir_wsl} -type f \\( -name '*chk*' -o -name '*plt*' -o -name '*.h5' \\) "
            f"2>/dev/null | head -40",
            timeout=15,
        )
        h5_files_wsl = [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]

    if not h5_files_wsl:
        if flash_failed:
            log(f"FLASH 本身失败 (rc={flash_rc}), 无输出文件属预期结果", "ERROR")
        else:
            log("FLASH 返回 0 但未找到输出文件 —— 检查 par 的 chk/plt 输出配置", "ERROR")
        r2 = wsl_cmd(
            f"echo '--- 暂存目录 ---'; find {run_dir_wsl} -maxdepth 2 2>/dev/null | head -20; "
            f"echo '--- objdir 产物 ---'; ls -la {flash_home}/{objdir}/*.h5 2>/dev/null | head -5 || echo 'objdir 内无 h5'",
            timeout=15,
        )
        for line in r2.stdout.strip().splitlines()[:20]:
            log(f"  {line}")
    else:
        log(f"找到 {len(h5_files_wsl)} 个输出文件")
        for hf in h5_files_wsl[:5]:
            log(f"  - {hf}")

        # 直接通过 WSL 的 /mnt/e/ 挂载复制到 Windows (逐文件 cp, 兼容子目录布局)
        DEMO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_win = str(DEMO_OUTPUT_DIR).replace("\\", "/").replace("E:", "/mnt/e")

        n_cp = 0
        for hf in h5_files_wsl:
            # 文件名可能同名 (不同 run_NNNNNN 下) ⇒ 加 run 目录前缀避免互相覆盖
            parent = hf.rsplit("/", 1)[0].rsplit("/", 1)[-1] if "/" in hf else ""
            name = hf.rsplit("/", 1)[-1]
            dst_name = f"{parent}_{name}" if parent.startswith("run_") else name
            r_cp = wsl_cmd(f"cp '{hf}' '{out_win}/{dst_name}' 2>/dev/null && echo OK", timeout=30)
            if "OK" in r_cp.stdout:
                n_cp += 1
        log(f"输出文件已复制到本地: {n_cp}/{len(h5_files_wsl)} ✓")

        r_log = wsl_cmd(f"find {run_dir_wsl}/outputfiles -name 'flash_run.log' 2>/dev/null | head -1", timeout=10)
        if r_log.stdout.strip():
            wsl_cmd(f"cp '{r_log.stdout.strip()}' '{out_win}/flash_run.log' 2>/dev/null; echo OK", timeout=30)

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
        if flash_failed:
            log("无输出文件可分析 (FLASH 未成功运行)", "ERROR")
        else:
            log("无输出文件可分析 —— 检查 par 是否配置了 chk/plt 文件输出", "ERROR")
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
    n_h5 = len(h5_local) if h5_local else 0
    # ★ 成功判据: FLASH rc==0 **且** 确有输出文件。
    #   原实现只看"流程跑完"就返回 dict ⇒ __main__ 打印 "Demo 成功!" 并 exit 0,
    #   掩盖了"零输出"这一实质失败 (本次故障的直接表现)。
    ok = (not flash_failed) and n_h5 > 0
    if ok:
        print(" 全流程完成!")
    else:
        print(" 全流程未成功!")

    print(f"  独立运行文件夹: {DEMO_RUN_DIR}")
    log(f"    包含一键执行脚本:")
    log(f"      * run_flash.bat  (Windows WSL)")
    log(f"      * run_flash.sh   (WSL/Linux)")
    log(f"      * submit_flash.sh (SLURM)")
    log(f"  可直接执行: cd {DEMO_RUN_DIR} && bash run_flash.sh")
    print(f"  仿真输出: {DEMO_OUTPUT_DIR}")
    print(f"  HDF5 文件: {n_h5} 个")
    log(f"  FLASH_HOME: {flash_home}")
    log(f"    源文件 → $FLASH_HOME/source/Simulation/SimulationMain/{sim_path}/")
    log(f"    编译   → $FLASH_HOME/{objdir}/")
    print(f"  SETUP_CMD: {setup_cmd}")
    if not ok:
        log(f"失败原因: FLASH 返回码 {flash_rc}, 输出文件 {n_h5} 个", "ERROR")
        log(f"排查入口: {DEMO_OUTPUT_DIR}/demo_console.log", "ERROR")
    print("=" * 60)

    return {
        "run_dir": str(DEMO_RUN_DIR),
        "output_dir": str(DEMO_OUTPUT_DIR),
        "flash_rc": flash_rc,
        "n_outputs": n_h5,
        "ok": ok,
        # 失败时返回 None, 使 __main__ 打印 "Demo 失败!" 并 exit 1
    } if ok else None


if __name__ == "__main__":
    result = main()
    if result:
        print("\n Demo 成功!")
    else:
        print("\n Demo 失败!")
        sys.exit(1)
