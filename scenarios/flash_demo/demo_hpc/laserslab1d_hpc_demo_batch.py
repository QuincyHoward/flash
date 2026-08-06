"""
FLASH LaserSlab1D 超算批量运行 Demo (v1.0)
═════════════════════════════════════════════════════════════════════

使用不同的功率因子进行多个仿真，提交到不同队列/节点，
对比不同功率下的物理结果。

功率因子:
  - 每个仿真通过修改 .par 文件中的 ed_power* 参数实现
  - 功率因子 = 相对于基准功率的倍数 (如 0.5, 1.0, 2.0)

运行方式:
  cd PhySimX
  python -m physimx_sim.flash.scenarios.flash_demo.demo_hpc.laserslab1d_hpc_demo_batch

输出:
  demo_task/laserslab1d_hpc_demo_batch/
    ├── run_power_0.5/          ← 各功率独立运行文件夹
    ├── run_power_1.0/
    ├── run_power_1.5/
    ├── run_power_2.0/
    ├── output/                  ← 下载的 HDF5 输出
    └── plots/                   ← 对比图像
"""

import sys
import os
import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

# 必须先设置 sys.path，否则无法导入 flash.credentials

# Bootstrap: find flash project root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "__init__.py").exists() and (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))


# ── 用户信息（优先从 credentials 读取，再找环境变量，最后用 "hello"）──
def _get_sim_user_dir() -> str:
    """三层回落: credentials → env var → 'hello'"""
    try:
        from flash._core.credentials import get_user_name
        return get_user_name()
    except ImportError:
        pass
    return os.environ.get("FLASH_SIM_USER_DIR", "hello")

SIM_USER_DIR = _get_sim_user_dir()

DEMO_TASK_BASE = Path(__file__).parent / "demo_task" / "laserslab1d_hpc_demo_batch"
DEMO_RUN_BASE = DEMO_TASK_BASE / "run"         # 存放各功率运行文件夹
DEMO_OUTPUT_DIR = DEMO_TASK_BASE / "output"
DEMO_PLOT_DIR = DEMO_TASK_BASE / "plots"

# 超算 FLASH 环境配置
FLASH_HOME = f"~/{SIM_USER_DIR}/FLASH/FLASH4.8"
MODULES_LOAD = (
    "module purge 2>/dev/null; "
    "source /public1/soft/modules/module.sh 2>/dev/null; "
    "module load mpich/3.2-gcc9.3 2>/dev/null; "
    "module load hdf5/1.8.18 2>/dev/null"
)

# ── 功率因子配置 ──
POWER_FACTORS = [0.5, 1.0, 1.5, 2.0]  # 基准功率的倍数

# ── SLURM 队列配置 ──
# 注意: 用户 scfa2696 只有 v5_192 分区的提交权限。
#       "queue" 和 "all" 分区均不可用。
#       如需多分区分发, 先用 test/remote_connect/test_sbatch.py 测试可用分区。
SLURM_PARTITIONS = [
    "v5_192",
]

# 各队列可用节点数
NODES_PER_PARTITION = {
    "v5_192": 1,
}


def log(msg: str, level: str = "INFO"):
    tag = {"INFO": "", "OK": "[OK]", "WARN": "[WARN]", "ERROR": "[ERROR]", "STEP": ">>>"}.get(level, " ")
    print(f"  {tag} {msg}")


# ── 辅助: 修改 .par 文件功率 ──────────────────────

def _modify_power_in_par(par_path: Path, power_factor: float) -> None:
    """修改 .par 文件中的功率参数。

    查找 ed_power* 相关的行，将功率值乘以 power_factor。
    """
    content = par_path.read_text(encoding="utf-8")

    # 匹配 ed_power 开头的行
    def replace_power(match):
        prefix = match.group(1)
        value_str = match.group(2)
        try:
            orig_value = float(value_str)
            new_value = orig_value * power_factor
            return f"{prefix}{new_value:.6e}"
        except ValueError:
            return match.group(0)

    new_content = re.sub(
        r'(ed_power\w*\s*=\s*)([\d.eE+\-]+)',
        replace_power,
        content,
    )

    par_path.write_text(new_content, encoding="utf-8")
    log(f"  power factor {power_factor} applied to {par_path.name}")


# ── 步骤 1: 生成各功率的输入文件 ──────────────────

def create_power_variants() -> Dict[float, Path]:
    """为每个功率因子生成独立的运行文件夹。

    Returns:
        {power_factor: run_dir_path}
    """
    from flash.input_gen import create_input_files
    from flash.input_gen.gen_shell_script import ShellScriptGenerator

    sim_path = f"{SIM_USER_DIR}/LaserSlab_batch"
    objdir = f"{SIM_USER_DIR}/LaserSlab_batch"
    par_filename = "laserslab_batch.par"

    setup_cmd = ShellScriptGenerator.build_setup_cmd(
        sim_path=sim_path, objdir=objdir, parfile=par_filename,
    )

    result_dirs: Dict[float, Path] = {}

    # 先生成基准文件到临时目录
    base_run_dir = DEMO_RUN_BASE / "base"
    if base_run_dir.exists():
        shutil.rmtree(str(base_run_dir))

    base_result = create_input_files(
        output_dir=str(base_run_dir),
        dimension=1,
        simulation_name="LaserSlab_batch",
        target_material="aluminum",
        chamber_gas="helium",
        n_beams=1,
        par_filename=par_filename,
        generate_scripts=True,
        copy_eos_files=True,
        setup_cmd=setup_cmd,
        sim_user_dir=SIM_USER_DIR,
        platform="hpc/scfa2696",
    )

    par_base_path = base_result.get("par")
    if not par_base_path:
        raise RuntimeError("基准 .par 文件未生成")

    # 为每个功率因子复制基准文件并修改功率
    for pf in POWER_FACTORS:
        run_dir = DEMO_RUN_BASE / f"power_{pf}"
        if run_dir.exists():
            shutil.rmtree(str(run_dir))
        shutil.copytree(str(base_run_dir), str(run_dir))

        # 修改 .par 中的功率
        par_path = run_dir / par_filename
        if par_path.exists():
            _modify_power_in_par(par_path, pf)

        # 修改 run_flash.sh 中的作业名
        script_path = run_dir / "run_flash.sh"
        if script_path.exists():
            content = script_path.read_text(encoding="utf-8")
            content = content.replace("LaserSlab_batch", f"LaserSlab_batch_p{pf}")
            script_path.write_text(content, encoding="utf-8")

        # 修改 submit_flash.sh 中的作业名
        submit_path = run_dir / "submit_flash.sh"
        if submit_path.exists():
            content = submit_path.read_text(encoding="utf-8")
            content = content.replace("LaserSlab_batch", f"LaserSlab_batch_p{pf}")
            submit_path.write_text(content, encoding="utf-8")

        result_dirs[pf] = run_dir
        log(f"  [power={pf}] → {run_dir}")

    # 清理基准目录
    shutil.rmtree(str(base_run_dir), ignore_errors=True)

    return result_dirs


# ── 步骤 2: 部署到超算 ──────────────────────────

def deploy_to_supercomputer(
    power_dirs: Dict[float, Path],
    credential_name: Optional[str] = None,
) -> Dict[float, str]:
    """将各功率的输入文件上传到超算。

    同时上传远程分析脚本 (remote_analysis.py) 到公共目录。

    Returns:
        {power_factor: remote_run_dir}
    """
    from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

    remote_dirs: Dict[float, str] = {}
    batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    log("\n[步骤 2] 上传到超算...")

    with RemoteSession(credential_name=credential_name, verbose=True) as session:
        # 创建批处理根目录
        batch_root = f"~/{SIM_USER_DIR}/AI/AItemp/flash_batch_{batch_id}"
        session.run(f"mkdir -p {batch_root}", timeout=10)

        for pf, local_dir in power_dirs.items():
            remote_dir = f"{batch_root}_p{pf}"
            log(f"  上传 power={pf} 到 {remote_dir}")

            # 创建远程目录
            session.run(f"mkdir -p {remote_dir}", timeout=10)

            # 上传所有文件
            for f in local_dir.iterdir():
                if f.is_file():
                    session.upload(str(f), f"{remote_dir}/")

            # 转换所有 .sh 文件为 Unix 换行符
            session.run(
                f"cd {remote_dir} && sed -i 's/\\r$//' *.sh 2>/dev/null; echo CONVERT_DONE",
                timeout=10,
            )

            remote_dirs[pf] = remote_dir

        # ── 上传远程分析脚本 ──
        script_local = Path(__file__).parent / "remote_analysis.py"
        if script_local.exists():
            analysis_dir = f"{batch_root}_analysis"
            session.run(f"mkdir -p {analysis_dir}", timeout=10)
            session.upload(str(script_local), f"{analysis_dir}/remote_analysis.py")
            session.run(f"chmod +x {analysis_dir}/remote_analysis.py", timeout=5)
            log(f"  分析脚本上传到 {analysis_dir}/remote_analysis.py")
            remote_dirs["_analysis_dir"] = analysis_dir
        else:
            log(f"  分析脚本未找到: {script_local}", "WARN")
            remote_dirs["_analysis_dir"] = ""

    return remote_dirs


# ── 步骤 4: 远程分析 + 下载结果 ─────────────────

def run_remote_analysis_and_download(
    remote_dirs: Dict[float, str],
    credential_name: Optional[str] = None,
) -> Dict[str, Path]:
    """在超算上运行分析脚本，然后下载分析结果到本地。

    HDF5 完整输出保留在超算上，只下载:
      - analysis_results.json   (摘要)
      - *_dens_comparison.png   (密度对比图)
      - *_tele_comparison.png   (温度对比图)
      - *_peak_density_vs_power.png (峰值对比图)

    Returns:
        {描述: 本地文件路径}
    """
    from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

    plot_paths: Dict[str, Path] = {}
    analysis_dir = remote_dirs.pop("_analysis_dir", "")
    if not analysis_dir:
        log("[步骤 4] 分析脚本未部署, 跳过远程分析", "WARN")
        return plot_paths

    DEMO_PLOT_DIR.mkdir(parents=True, exist_ok=True)

    log("\n[步骤 4] 在超算上运行分析...")
    log("  (HDF5 完整输出保留在超算, 仅下载分析结果)")

    # 构建每个功率的输出目录和功率因子列表
    power_dirs_list = []
    power_factors_list = []
    for pf in sorted(remote_dirs.keys()):
        rd = remote_dirs[pf]
        # 输出可能在 outputfiles/ 子目录或根目录
        power_dirs_list.append(rd)
        power_factors_list.append(str(pf))

    if not power_dirs_list:
        log("  无功率数据可分析", "WARN")
        return plot_paths

    with RemoteSession(credential_name=credential_name, verbose=True) as session:
        # 在远程执行分析
        output_prefix = f"{analysis_dir}/batch_results"
        dirs_arg = " ".join(power_dirs_list)
        powers_arg = " ".join(power_factors_list)

        # 超算可用 Python 版本 (通过 module 加载):
        #   python/3.9.6  有 h5py 3.3.0 + numpy 1.26.4 ✅
        #   python/3.10.8 无 h5py ❌
        #   python/3.8.6  无 h5py ❌
        # 优先加载 python/3.9.6 (有 h5py + numpy, 可提取数据)
        remote_cmd = (
            f"cd {analysis_dir} && "
            f"module load python/3.9.6 2>/dev/null; "
            f"export PYTHONIOENCODING=utf-8 && "
            f"python remote_analysis.py "
            f"--dirs {dirs_arg} "
            f"--powers {powers_arg} "
            f"--output {output_prefix} "
            f"2>&1"
        )
        log(f"  运行远程分析 (module load python/3.9.6)...")
        out, err, code = session.run(remote_cmd, timeout=600)
        log(f"  返回码: {code}")

        if code != 0:
            # 回退: 尝试 python3 (无 module load)
            remote_cmd2 = (
                f"cd {analysis_dir} && "
                f"export PYTHONIOENCODING=utf-8 && "
                f"python3 remote_analysis.py "
                f"--dirs {dirs_arg} "
                f"--powers {powers_arg} "
                f"--output {output_prefix} "
                f"2>&1"
            )
            log(f"  回退: 尝试 python3...")
            out, err, code = session.run(remote_cmd2, timeout=600)
            log(f"  返回码: {code}")

        if code != 0:
            # 最后回退: 尝试 python/3.8.6
            remote_cmd3 = (
                f"cd {analysis_dir} && "
                f"module load python/3.8.6 2>/dev/null; "
                f"export PYTHONIOENCODING=utf-8 && "
                f"python remote_analysis.py "
                f"--dirs {dirs_arg} "
                f"--powers {powers_arg} "
                f"--output {output_prefix} "
                f"2>&1"
            )
            log(f"  回退: 尝试 python/3.8.6...")
            out, err, code = session.run(remote_cmd3, timeout=600)
            log(f"  返回码: {code}")

        # 显示分析输出
        if out.strip():
            log(f"  分析输出:")
            for line in out.strip().splitlines()[-15:]:
                log(f"    {line}")
        if code != 0:
            log(f"  远程分析失败 (code={code})", "WARN")
            return plot_paths

        # ── 下载分析结果 ──
        log(f"\n  下载远程分析结果...")
        result_files = [
            ("json_summary", f"{output_prefix}.json"),
            ("dens_comparison", f"{output_prefix}_dens_comparison.png"),
            ("tele_comparison", f"{output_prefix}_tele_comparison.png"),
            ("peak_vs_power", f"{output_prefix}_peak_density_vs_power.png"),
            ("full_data", f"{output_prefix}_full.json"),
        ]

        for label, remote_path in result_files:
            local_path = str(DEMO_PLOT_DIR / f"batch_{Path(remote_path).name}")
            try:
                # 通过 scp 直接下载
                from flash.scenarios.flash_demo.demo_hpc.laserslab1d_hpc_demo_batch import _direct_scp_download
                from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import _resolve_route_and_credential
                route = _resolve_route_and_credential(credential_name)

                ok = _direct_scp_download(route, remote_path, local_path, timeout=60)
                if ok and os.path.exists(local_path):
                    plot_paths[label] = Path(local_path)
                    log(f"    {label}: {Path(local_path).name} ✓")
            except Exception as e:
                log(f"    {label}: 下载失败 - {e}", "WARN")

        log(f"  已下载 {len(plot_paths)} 个分析结果文件")

        # ── 本地回退绘图: 从下载的 JSON 生成对比图 ──
        if "full_data" in plot_paths:
            local_plots = _plot_from_json(str(plot_paths["full_data"]), str(DEMO_PLOT_DIR))
            plot_paths.update(local_plots)
            log(f"  本地回退绘图生成了 {len(local_plots)} 个图")
        elif "json_summary" in plot_paths:
            local_plots = _plot_from_json(str(plot_paths["json_summary"]), str(DEMO_PLOT_DIR))
            plot_paths.update(local_plots)

    return plot_paths


def _plot_from_json(json_path: str, output_dir: str) -> Dict[str, Path]:
    """从下载的 JSON 文件回退生成对比图 (本地 matplotlib)。

    当远程超算无 matplotlib 时，使用此函数在本地生成对比图。

    Args:
        json_path: 下载的 JSON 文件路径 (full.json 或 summary.json)
        output_dir: 图像输出目录

    Returns:
        {图名: 路径} 字典
    """
    plot_paths: Dict[str, Path] = {}
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    try:
        import json as _json
        with open(json_path) as f:
            all_results = _json.load(f)
    except Exception as e:
        log(f"  JSON 加载失败: {e}", "WARN")
        return plot_paths

    # 检查是否有有效数据
    has_data = any("dens_peak" in r for r in all_results.values())
    has_ts = any("time_series" in r for r in all_results.values())
    has_coords = any("dens_x" in r for r in all_results.values())

    if not (has_data or has_ts or has_coords):
        log(f"  JSON 中无有效数据, 跳过本地绘图", "WARN")
        return plot_paths

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        # ── PPT-friendly plot style (fonts >= 18, English only) ──
        try:
            from output_processors.plotter.plot_style import apply_plot_style
            apply_plot_style()
        except ImportError:
            pass
        import numpy as np
    except ImportError:
        log(f"  matplotlib 不可用, 无法本地绘图", "WARN")
        return plot_paths

    prefix = "batch"
    log(f"\n[本地回退绘图] 从 JSON 生成 {sum(1 for r in all_results.values() if 'dens_peak' in r or 'time_series' in r)} 个功率的对比图...")

    # 图 1: 密度峰值 vs 功率因子
    powers = []
    peaks = []
    for key in sorted(all_results.keys()):
        r = all_results[key]
        if "dens_peak" in r:
            powers.append(r["power_factor"])
            peaks.append(r["dens_peak"])
    if powers:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(powers, peaks, "o-", linewidth=2, markersize=8)
        ax.set_xlabel("Power Factor")
        ax.set_ylabel("Peak Density (g/cm$^3$)")
        ax.set_title("Peak Density vs Power Factor (Local)")
        ax.grid(True, alpha=0.3)
        path = str(out / f"{prefix}_peak_density_vs_power.png")
        fig.savefig(path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        plot_paths["peak_vs_power"] = Path(path)
        log(f"  [OK] {prefix}_peak_density_vs_power.png")

    # 图 2: 密度峰值随时间演化
    if has_ts:
        fig, ax = plt.subplots(figsize=(10, 6))
        for key in sorted(all_results.keys()):
            r = all_results[key]
            ts = r.get("time_series", {})
            times = ts.get("times", [])
            dpeaks = ts.get("dens_peaks", [])
            if times and dpeaks:
                ax.plot(times, dpeaks, "o-", linewidth=1.5, markersize=4,
                        label="Power x" + str(r.get("power_factor", "")))
        if ax.lines:
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Peak Density (g/cm$^3$)")
            ax.set_title("Density Peak Evolution Over Time (Local)")
            ax.legend()
            path = str(out / f"{prefix}_dens_peak_vs_time.png")
            fig.savefig(path, dpi=200, bbox_inches="tight")
            plt.close(fig)
            plot_paths["dens_peak_vs_time"] = Path(path)
            log(f"  [OK] {prefix}_dens_peak_vs_time.png")
        else:
            plt.close(fig)

    # 图 3: 密度分布对比 (如有坐标数据)
    if has_coords:
        fig, ax = plt.subplots(figsize=(10, 6))
        for key in sorted(all_results.keys()):
            r = all_results[key]
            if "dens_x" in r and "dens_y" in r:
                ax.plot(r["dens_x"], r["dens_y"],
                        label="Power x" + str(r.get("power_factor", "")))
        if ax.lines:
            ax.set_xlabel("x (cm)")
            ax.set_ylabel("Density (g/cm$^3$)")
            ax.set_title("Density Distribution (Power Factor Comparison)")
            ax.legend()
            path = str(out / f"{prefix}_dens_comparison.png")
            fig.savefig(path, dpi=200, bbox_inches="tight")
            plt.close(fig)
            plot_paths["dens_comparison"] = Path(path)
            log(f"  [OK] {prefix}_dens_comparison.png")
        else:
            plt.close(fig)

    # 图 4: 密度剖面时间演化 (多子图)
    if has_ts:
        n_powers = sum(1 for k in all_results if "time_series" in all_results[k])
        if n_powers > 0:
            fig, axes = plt.subplots(1, n_powers, figsize=(6 * n_powers, 5), squeeze=False)
            for idx, key in enumerate(sorted(all_results.keys())):
                r = all_results[key]
                ts = r.get("time_series", {})
                profiles = ts.get("dens_profiles", [])
                if not profiles:
                    continue
                ax_i = axes[0][idx]
                for prof in profiles:
                    ax_i.plot(prof["x"], prof["y"],
                              label="t={:.2e}s".format(prof["time"]))
                ax_i.set_xlabel("x (cm)")
                ax_i.set_ylabel("Density (g/cm$^3$)")
                ax_i.set_title("Power x" + str(r.get("power_factor", "")))
                ax_i.legend()
            fig.tight_layout()
            path = str(out / f"{prefix}_dens_evolution.png")
            fig.savefig(path, dpi=200, bbox_inches="tight")
            plt.close(fig)
            plot_paths["dens_evolution"] = Path(path)
            log(f"  [OK] {prefix}_dens_evolution.png")

    log(f"  本地回退绘图完成, 共 {len(plot_paths)} 个图")
    return plot_paths


# ── 步骤 3: 远程执行 FLASH ───────────────────────

def run_flash_remotely(
    remote_dirs: Dict[float, str],
    credential_name: Optional[str] = None,
) -> Dict[float, bool]:
    """在超算上远程运行 FLASH 仿真。

    使用 sbatch 将不同功率的仿真提交到不同 SLURM 队列，
    实现真正的并行分发测试。如果 sbatch 失败，自动降级为
    直接运行 run_flash.sh。

    各任务的远程路径:
      run_flash.sh 会复制文件到:
        $FLASH_HOME/source/Simulation/SimulationMain/{SIM_USER_DIR}/LaserSlab_batch/
    """
    from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

    results: Dict[float, bool] = {}
    job_ids: Dict[float, str] = {}
    log("\n[步骤 3] 远程执行 FLASH (不同队列并行分发)...")

    # 过滤出数值类型 key (排除字符串辅助键如 "_analysis_dir")
    power_items = [(k, v) for k, v in remote_dirs.items() if isinstance(k, (int, float))]

    # 显示远程文件位置
    log("\n  [信息] 任务文件位置:")
    for pf, rd in sorted(power_items):
        simmain_path = (
            f"$FLASH_HOME/source/Simulation/SimulationMain/"
            f"{SIM_USER_DIR}/LaserSlab_batch/"
        )
        log(f"    power={pf}: 输入文件 → {rd}")
        log(f"                 SimulationMain → {simmain_path}")

    with RemoteSession(credential_name=credential_name, verbose=True) as session:
        # ── 3a: 尝试 sbatch 提交 ──
        log("\n  3a. 尝试 sbatch 提交到不同 SLURM 队列...")
        for i, (pf, remote_dir) in enumerate(sorted(power_items)):
            partition = SLURM_PARTITIONS[i % len(SLURM_PARTITIONS)]
            nodes = NODES_PER_PARTITION.get(partition, 1)
            job_name = f"FLASH_batch_p{pf}"

            log(f"  提交: power={pf}, 队列={partition}, 节点={nodes}, 作业名={job_name}")
            log(f"  远程目录: {remote_dir}")

            # 检查 submit_flash.sh
            out, _, _ = session.run(
                f"ls -la {remote_dir}/submit_flash.sh 2>/dev/null || echo MISSING",
                timeout=5,
            )
            if "MISSING" in out:
                log(f"  [WARN] {remote_dir}/submit_flash.sh 不存在, 跳过 sbatch", "WARN")
                results[pf] = False
                continue

            # 检查换行符
            out, _, _ = session.run(
                f"file {remote_dir}/submit_flash.sh | grep -c CRLF",
                timeout=5,
            )

            # 修改分区/作业名/任务数
            session.run(
                f"cd {remote_dir} && "
                f"sed -i 's/#SBATCH -p .*/#SBATCH -p {partition}/' submit_flash.sh && "
                f"sed -i 's/#SBATCH -J .*/#SBATCH -J {job_name}/' submit_flash.sh && "
                f"sed -i 's/#SBATCH --job-name=.*/#SBATCH --job-name={job_name}/' submit_flash.sh && "
                f"sed -i 's/#SBATCH -N .*/#SBATCH -N {nodes}/' submit_flash.sh",
                timeout=10,
            )

            # 提交作业
            out, err, code = session.run(
                f"cd {remote_dir} && sbatch submit_flash.sh 2>&1",
                timeout=15,
            )
            log(f"  sbatch 结果: {out.strip()[:300]}")

            match = re.search(r"Submitted batch job (\d+)", out)
            if match:
                job_id = match.group(1)
                job_ids[pf] = job_id
                log(f"  [OK] power={pf} → JobID={job_id}, 队列={partition}")
                log(f"       用 sacct -j {job_id} 或 squeue -u $USER 查看状态")
            else:
                log(f"  [WARN] sbatch 失败: {err[:200]}", "WARN")
                log(f"  [INFO] 降级为直接运行 run_flash.sh (不经过队列)...")
                results[pf] = False  # 标记为未完成, 后面用 fallback

        # ── 3b: 对 sbatch 失败的任务直接运行 ──
        fallen = [pf for pf in remote_dirs if pf not in job_ids and pf not in results]
        # 也包括 results[pf]==False 的, 排除非数值辅助键 (如 _analysis_dir)
        fallen = [pf for pf in remote_dirs if pf not in job_ids and isinstance(pf, (int, float))]

        if fallen:
            log(f"\n  3b. 对 {len(fallen)} 个 sbatch 失败的任务直接运行...")
            for pf in fallen:
                remote_dir = remote_dirs[pf]
                log(f"  直接运行: power={pf}, 目录={remote_dir}")
                flash_cmd = (
                    f"cd {remote_dir} && "
                    f"{MODULES_LOAD} && "
                    f"bash run_flash.sh 2>&1 | tail -50"
                )
                out, err, code = session.run(flash_cmd, timeout=600)

                log(f"  返回码: {code}")
                if out.strip():
                    for line in out.strip().splitlines()[-10:]:
                        log(f"  {line}")

                success = (code == 0)
                results[pf] = success
                log(f"  [{'OK' if success else 'FAIL'}] power={pf} 直接运行{'成功' if success else '失败'}")

        # ── 3c: 等待 sbatch 作业完成 ──
        if job_ids:
            log(f"\n  3c. 等待 {len(job_ids)} 个 sbatch 作业完成...")
            max_wait = 3600
            start_wait = time.time()

            while job_ids and (time.time() - start_wait) < max_wait:
                for pf, jid in list(job_ids.items()):
                    out, _, _ = session.run(
                        f"sacct -j {jid} --format=State --noheader 2>/dev/null | head -1",
                        timeout=10,
                    )
                    state = out.strip()
                    log(f"  power={pf} JobID={jid}: {state}")

                    if state in ("COMPLETED", "COMPLETING"):
                        results[pf] = True
                        del job_ids[pf]
                        log(f"  [OK] power={pf} 完成 ✓")
                    elif state in ("FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL"):
                        results[pf] = False
                        del job_ids[pf]
                        log(f"  [FAIL] power={pf} 失败: {state}", "ERROR")
                    elif state in ("PENDING", "RUNNING", ""):
                        pass

                if job_ids:
                    time.sleep(15)

            if job_ids:
                log(f"  [WARN] 以下作业超时: {job_ids}", "WARN")
                for pf in job_ids:
                    results[pf] = False

            success_count = sum(1 for v in results.values() if v)
            log(f"\n  [结果] {success_count}/{len(results)} 任务成功")

    return results


def _direct_scp_download(route: Dict[str, Any], remote_path: str, local_path: str,
                         timeout: int = 300) -> bool:
    """直接使用 SCP 下载 (绕过 session.download 的返回码问题)。"""
    pw, host, port, username = (route["password"], route["host"],
                                 route["port"], route["username"])

    # 查找 scp 可执行文件
    from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import _find_scp
    scp_exe = _find_scp()

    # 使用 .bat askpass (Windows 兼容)
    import platform as _plt
    is_win = _plt.system().lower() == "windows"
    askpass = tempfile.NamedTemporaryFile(
        mode="w", suffix=".bat" if is_win else ".sh",
        delete=False, newline="\r\n" if is_win else "\n",
    )
    if is_win:
        askpass.write("@echo off\n")
        askpass.write(f'echo {pw}\n')
    else:
        askpass.write("#!/bin/sh\n")
        askpass.write(f'echo "{pw}"\n')
    askpass.close()
    if not is_win:
        os.chmod(askpass.name, 0o755)

    env = os.environ.copy()
    env["SSH_ASKPASS"] = askpass.name
    env["DISPLAY"] = ":0"

    try:
        r = subprocess.run([
            scp_exe, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=30",
            "-P", str(port),
            f"{username}@{host}:{remote_path}", local_path,
        ], capture_output=True, text=True, timeout=timeout, env=env)
        return r.returncode == 0
    except Exception:
        return False
    finally:
        try:
            os.unlink(askpass.name)
        except OSError:
            pass


# ── 步骤 4: 下载关键结果 ───────────────────────

def download_results(
    remote_dirs: Dict[float, str],
    route: Dict[str, Any],
    credential_name: Optional[str] = None,
) -> Dict[float, List[Path]]:
    """从超算下载关键结果文件 (不下载全部 HDF5)。

    超算运行规范:
      - HDF5 文件留在超算上，不全部下载到本地
      - 只下载以下关键结果:
        1. 每个功率变体 1 个 checkpoint (第一个 chk 文件)
        2. flash_run.log (日志)
      - 分析在后续步骤中基于下载的 chk 文件进行
    """
    from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

    local_files: Dict[float, List[Path]] = {}
    log("\n[步骤 4] 下载关键结果文件 (仅 1 chk + 日志 每功率)...")
    log("  (HDF5 完整输出保留在超算上, 不全部下载)")

    with RemoteSession(credential_name=credential_name, verbose=True) as session:
        for pf, remote_dir in remote_dirs.items():
            pf_output_dir = DEMO_OUTPUT_DIR / f"power_{pf}"
            pf_output_dir.mkdir(parents=True, exist_ok=True)

            # 1. 查找输出目录 (submit_flash.sh 生成 outputfiles_* 时间戳目录)
            out_dir_cmd = (
                f"outdir=$(ls -d {remote_dir}/outputfiles_* 2>/dev/null | head -1); "
                f"if [ -z \"$outdir\" ]; then outdir={remote_dir}/outputfiles; fi; "
                f"echo \"$outdir\""
            )
            actual_outdir, _, _ = session.run(out_dir_cmd, timeout=10)
            actual_outdir = actual_outdir.strip()
            log(f"  power={pf}: 输出目录={actual_outdir}")

            # 2. 下载 flash_run.log
            log(f"  power={pf}: 下载日志...")
            session.run(
                f"cp {actual_outdir}/flash_run.log /tmp/flash_run_p{pf}.log 2>/dev/null || "
                f"cp {remote_dir}/flash_run.log /tmp/flash_run_p{pf}.log 2>/dev/null; "
                f"echo LOG_CP_DONE",
                timeout=10,
            )
            _direct_scp_download(
                route,
                f"/tmp/flash_run_p{pf}.log",
                str(pf_output_dir / "flash_run.log"),
                timeout=30,
            )

            # 3. 下载 1 个 checkpoint 文件 (第一个 chk)
            out, _, _ = session.run(
                f"ls {actual_outdir}/*chk_0000 2>/dev/null | head -1 || "
                f"ls {actual_outdir}/*chk* 2>/dev/null | head -1 || "
                f"echo NO_CHK",
                timeout=10,
            )
            chk_path = out.strip()
            if chk_path and chk_path != "NO_CHK":
                chk_name = Path(chk_path).name
                log(f"  power={pf}: 下载 checkpoint ({chk_name})...")
                # 先复制到 /tmp 避免路径问题
                session.run(
                    f"cp {chk_path} /tmp/{chk_name}_p{pf} 2>/dev/null; echo CP_DONE",
                    timeout=10,
                )
                ok = _direct_scp_download(
                    route,
                    f"/tmp/{chk_name}_p{pf}",
                    str(pf_output_dir / chk_name),
                    timeout=120,
                )
                if ok:
                    local_files[pf] = [pf_output_dir / chk_name]
                    log(f"    -> {pf_output_dir / chk_name} ✓")
                else:
                    log(f"    chk 下载失败, 跳过", "WARN")
            else:
                log(f"  power={pf}: 未找到 checkpoint 文件", "WARN")

            # 列出已下载的文件
            downloaded = list(pf_output_dir.iterdir())
            log(f"  power={pf}: 本地 {len(downloaded)} 个文件 ({', '.join(f.name for f in downloaded)})")

    return local_files


# ── 步骤 5: 分析并生成对比图 ─────────────────────

def analyze_and_plot(local_files: Dict[float, List[Path]]) -> Dict[str, Path]:
    """分析各功率输出并生成对比图。"""
    plot_paths: Dict[str, Path] = {}
    DEMO_PLOT_DIR.mkdir(parents=True, exist_ok=True)

    log("\n[步骤 5] 分析并生成对比图...")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        import h5py
        from flash.scenarios.flash_demo.demo_hpc._plot_utils import extract_1d_profile, save_density_plot
    except ImportError as e:
        log(f"绘图依赖导入失败: {e}", "WARN")
        return plot_paths

    # 收集各功率的密度分布
    all_power_data: Dict[float, tuple] = {}  # pf -> (x, y, sim_time)
    for pf in POWER_FACTORS:
        files = local_files.get(pf, [])
        chk_files = [f for f in files if "chk" in f.name]
        if not chk_files:
            continue
        try:
            x, y = extract_1d_profile(str(chk_files[0]), "dens")
            # 从 real scalars 读仿真时间 (compound, dict-style)
            with h5py.File(str(chk_files[0]), "r") as f:
                rs = f["real scalars"][:]
                sim_time = 0.0
                for rec in rs:
                    name = rec["name"].decode("utf-8").strip() if isinstance(rec["name"], bytes) else str(rec["name"]).strip()
                    if name == "time":
                        sim_time = float(rec["value"])
                        break
            all_power_data[pf] = (x, y, sim_time)
            log(f"  power={pf}: loaded {chk_files[0].name}", "INFO")
        except Exception as e:
            log(f"  power={pf}: 加载失败: {e}", "WARN")

    if not all_power_data:
        log("  [WARN] 无数据可分析")
        return plot_paths

    # ---- 图 1: 各功率密度分布对比 ----
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        for pf, (x, y, _) in sorted(all_power_data.items()):
            ax.plot(x, y, linewidth=1.5, label=f"Power x{pf}")
        ax.set_xlabel("x [cm]")
        ax.set_ylabel(r"Density [g/cm$^3$]")
        ax.set_title("Density Distribution (Power Factor Comparison)")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.savefig(str(DEMO_PLOT_DIR / "dens_comparison.png"), dpi=150, bbox_inches="tight")
        plt.close(fig)
        plot_paths["dens_comparison"] = DEMO_PLOT_DIR / "dens_comparison.png"
        log(f"  [OK] 密度对比图: dens_comparison.png")
    except Exception as e:
        log(f"  密度对比图失败: {e}", "WARN")

    # ---- 图 2: 各功率电子温度分布对比 ----
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        for pf in sorted(all_power_data.keys()):
            try:
                x_tele, y_tele = extract_1d_profile(
                    str([f for f in local_files.get(pf, []) if "chk" in f.name][0]),
                    "tele"
                )
                ax.plot(x_tele, y_tele, linewidth=1.5, label=f"Power x{pf}")
            except Exception:
                pass
        if ax.lines:
            ax.set_xlabel("x [cm]")
            ax.set_ylabel(r"Electron Temperature [K]")
            ax.set_title("Electron Temperature (Power Factor Comparison)")
            ax.legend()
            ax.grid(True, alpha=0.3)
            fig.savefig(str(DEMO_PLOT_DIR / "tele_comparison.png"), dpi=150, bbox_inches="tight")
            plt.close(fig)
            plot_paths["tele_comparison"] = DEMO_PLOT_DIR / "tele_comparison.png"
            log(f"  [OK] 电子温度对比图: tele_comparison.png")
        else:
            plt.close(fig)
    except Exception as e:
        log(f"  电子温度对比图失败: {e}", "WARN")

    # ---- 图 3: 密度峰值随功率变化 ----
    try:
        fig, ax = plt.subplots(figsize=(8, 5))
        powers = []
        peaks = []
        for pf, (x, y, _) in sorted(all_power_data.items()):
            powers.append(pf)
            peaks.append(float(np.max(y)))
        if powers:
            ax.plot(powers, peaks, "o-", linewidth=2, markersize=8)
            ax.set_xlabel("Power Factor")
            ax.set_ylabel("Peak Density [g/cm³]")
            ax.set_title("Peak Density vs Power Factor")
            ax.grid(True, alpha=0.3)
            fig.savefig(str(DEMO_PLOT_DIR / "peak_density_vs_power.png"), dpi=150, bbox_inches="tight")
            plt.close(fig)
            plot_paths["peak_vs_power"] = DEMO_PLOT_DIR / "peak_density_vs_power.png"
            log(f"  [OK] 峰值对比图: peak_density_vs_power.png")
    except Exception as e:
        log(f"  峰值对比图失败: {e}", "WARN")

    # ---- 图 4: 各功率独立密度图 ----
    for pf, (x, y, sim_time) in sorted(all_power_data.items()):
        try:
            plot_path = DEMO_PLOT_DIR / f"dens_power_{pf}.png"
            save_density_plot(x, y, str(plot_path),
                              title=f"Density (Power x{pf}, t={sim_time:.3e}s)")
            plot_paths[f"dens_p{pf}"] = plot_path
            log(f"  [OK] dens_power_{pf}.png")
        except Exception as e:
            log(f"  独立图 power={pf} 失败: {e}", "WARN")

    return plot_paths


# ── 主流程 ──────────────────────────────────────

def main(credential_name: Optional[str] = None):
    print("\n" + "=" * 60)
    print(" FLASH LaserSlab1D 超算批量运行 Demo (v1.0)")
    print(f" 用户目录: {SIM_USER_DIR}")
    print(f" 功率因子: {POWER_FACTORS}")
    print(f" SLURM 队列: {SLURM_PARTITIONS}")
    print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # ── 步骤 1: 生成各功率输入文件 ──
    print("\n[步骤 1] 生成各功率输入文件")
    print("-" * 50)
    DEMO_RUN_BASE.mkdir(parents=True, exist_ok=True)
    power_dirs = create_power_variants()
    log(f"已生成 {len(power_dirs)} 个功率变体")

    # ── 步骤 2: 上传到超算 ──
    remote_dirs = deploy_to_supercomputer(power_dirs, credential_name)

    # ── 步骤 3: 远程运行 ──
    run_results = run_flash_remotely(remote_dirs, credential_name)

    # ── 步骤 4: 远程分析 + 下载结果 ──
    plot_paths = run_remote_analysis_and_download(remote_dirs, credential_name)

    # ── 完成 ──
    print("\n" + "=" * 60)
    print(" 批量 Demo 完成!")
    print(f"  运行文件夹: {DEMO_RUN_BASE}")
    print(f"  图像目录: {DEMO_PLOT_DIR}")
    print(f"  HDF5 保留在超算上")
    print(f"  FLASH 安装: {FLASH_HOME}")
    print("=" * 60)

    return {
        "run_dir": str(DEMO_RUN_BASE),
        "plot_dir": str(DEMO_PLOT_DIR),
        "power_factors": POWER_FACTORS,
        "run_results": run_results,
        "plot_paths": {k: str(v) for k, v in plot_paths.items()},
    }


if __name__ == "__main__":
    result = main()
    if result:
        print("\n Demo 成功!")
    else:
        print("\n Demo 失败!")
        sys.exit(1)
