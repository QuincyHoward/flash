"""
FLASH LaserSlab1D 超算运行 Demo v4.0（超算端绘图版 · 一键完成）
═══════════════════════════════════════════════════════════════════════════════

一键执行所有流程（超算端直接完成绘图分析，不下载 HDF5 原始文件）：
1. 加载SSH凭据
2. 生成输入文件（带时间戳，每次运行独立目录）
3. 上传到超算
4. 运行FLASH仿真
5. 超算端直接绘图分析（不下载原始HDF5，仅传输轻量图片）
6. 下载绘图结果图片到本地

特点:
  - 每次运行自动添加时间戳，目录不覆盖
  - 超算端用 h5py+matplotlib 直接生成图片，避免下载GB级HDF5文件
  - 备用方案：超算端绘图失败时自动回退到"下载HDF5+本地绘图"
  - 真正一键完成全流程

运行方式:
  cd E:/ProgramsPATH/AI/WorkBuddy/WorkBuddyFiles/AItest/Plan_for_py/PhySimX
  python physimx_sim/src/physimx_sim/flash/flash_demo/laserslab1d_supercomputer_demo.py
"""

import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

# 抑制 MSMPI 警告
os.environ['MPI4PY_DISABLE_DLOPEN'] = '1'
os.environ['MPICH_RANK'] = '0'

# 必须先设置 sys.path，否则无法导入 flash.credentials
# 脚本位置: .../physimx_sim/src/physimx_sim/flash/flash_demo/demo_hpc/laserslab1d_supercomputer_demo.py
# flash 包目录: .../physimx_sim/src/physimx_sim/flash/
# 需要将 physimx_sim 包根目录加入 sys.path，即 flash 的父目录

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

# 路径计算: 脚本位于 flash/flash_demo/demo_hpc/
_SCRIPT_DIR = Path(__file__).resolve().parent            # .../flash/flash_demo/demo_hpc/
_FLASH_DIR = _SCRIPT_DIR.parent.parent                   # .../flash/ (flash 包目录)
_PKG_ROOT = _FLASH_DIR.parent                            # .../physimx_sim/ (内层, Python 包根)
SRC_DIR = _PKG_ROOT.parent                               # .../src/
PHYSMX_SIM_MOD = SRC_DIR.parent                          # .../physimx_sim/ (外层)
PROJECT_ROOT = PHYSMX_SIM_MOD.parent                     # .../PhySimX/ (项目根)

# 也添加到 Python 路径 (确保后续 imports 可用)
sys.path.insert(0, str(_PKG_ROOT))

print(f"[Demo] PROJECT_ROOT = {PROJECT_ROOT}")
print(f"[Demo] PYTHONPATH 已添加: {_PKG_ROOT}")
print(f"[Demo] SIM_USER_DIR  = {SIM_USER_DIR}")

# 时间戳：每次运行独立目录，格式 laserslab1d_supercomputer_demo_YYYYMMDD_HHMMSS
_RUN_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
DEMO_TASK_BASE = Path(__file__).parent / "demo_task" / f"laserslab1d_supercomputer_demo_{_RUN_TIMESTAMP}"
DEMO_RUN_DIR = DEMO_TASK_BASE / "run"        # 独立运行文件夹 (staging)
DEMO_OUTPUT_DIR = DEMO_TASK_BASE / "output"     # 仿真输出 (HDF5 + 图像)
DEMO_PLOT_DIR = DEMO_TASK_BASE / "plots"      # 绘图输出（本地备份）
REMOTE_PLOT_DIR_NAME = "plots_remote"         # 超算端图片目录名

# 超算 FLASH 环境配置
FLASH_HOME = f"~/{SIM_USER_DIR}/FLASH/FLASH4.8"
MODULES_LOAD = (
    "module purge 2>/dev/null; "
    "source /public1/soft/modules/module.sh 2>/dev/null; "
    "module load mpich/3.2-gcc9.3 2>/dev/null; "
    "module load hdf5/1.8.18 2>/dev/null"
)


def log(msg: str, level: str = "INFO"):
    tag = {"INFO": "", "OK": "[OK]", "WARN": "[WARN]", "ERROR": "[ERROR]", "STEP": ">>>"}.get(level, "  ")
    print(f"  {tag} {msg}")


def get_ssh_client(cred: Dict[str, Any]):
    """创建 paramiko SSH 客户端并连接。"""
    try:
        import paramiko
    except ImportError:
        log("需要 paramiko 库，正在安装...", "INFO")
        subprocess.run([sys.executable, "-m", "pip", "install", "paramiko"], check=True)
        import paramiko

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs = {
        "hostname": cred["host"],
        "port": cred.get("port", 22),
        "username": cred["username"],
        "timeout": 15,
    }
    if cred.get("key_filename"):
        connect_kwargs["key_filename"] = cred["key_filename"]
    elif cred.get("password"):
        connect_kwargs["password"] = cred["password"]
    else:
        log("无密码或密钥，尝试 SSH agent...", "WARN")

    client.connect(**connect_kwargs)
    return client


def ssh_cmd(cred: Dict[str, Any], cmd: str, timeout: int = 60) -> Dict[str, Any]:
    """在超算上通过 paramiko SSH 执行命令。"""
    client = get_ssh_client(cred)
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        stdout_str = stdout.read().decode("utf-8", errors="replace")
        stderr_str = stderr.read().decode("utf-8", errors="replace")
        exit_code = stdout.channel.recv_exit_status()
        return {
            "returncode": exit_code,
            "stdout": stdout_str,
            "stderr": stderr_str,
        }
    finally:
        client.close()


def sftp_upload(cred: Dict[str, Any], local_path: str, remote_path: str):
    """通过 paramiko SFTP 上传文件。"""
    client = get_ssh_client(cred)
    try:
        sftp = client.open_sftp()
        sftp.put(local_path, remote_path)
    finally:
        sftp.close()
        client.close()


def download_all_outputs(cred: Dict[str, Any], remote_output_dir: str, local_output_dir: Path, max_retries: int = 3):
    """
    从超算下载所有输出文件（支持断点续传和重试）
    """
    log("正在下载输出文件...", "STEP")
    
    # 获取远程文件列表
    r = ssh_cmd(cred, f"ls {remote_output_dir}/*plt* {remote_output_dir}/*chk* 2>/dev/null", timeout=30)
    remote_files = [l.strip() for l in r["stdout"].strip().splitlines() if l.strip()]
    
    if not remote_files:
        log("远程未找到输出文件", "WARN")
        return []
    
    log(f"远程找到 {len(remote_files)} 个输出文件")
    
    # 创建本地目录
    local_output_dir.mkdir(parents=True, exist_ok=True)
    
    # 下载文件（支持重试）
    downloaded = []
    failed = []
    
    for i, remote_path in enumerate(remote_files):
        filename = Path(remote_path).name
        local_path = str(local_output_dir / filename)
        
        # 检查是否已下载
        if Path(local_path).exists():
            downloaded.append(local_path)
            continue
        
        # 下载（带重试）
        for attempt in range(max_retries):
            try:
                # 重新连接SSH（避免超时）
                client = get_ssh_client(cred)
                sftp = client.open_sftp()
                sftp.get(remote_path, local_path)
                sftp.close()
                client.close()
                
                downloaded.append(local_path)
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    log(f"  重试 {attempt+1}/{max_retries}: {filename}", "WARN")
                    import time
                    time.sleep(2)
                else:
                    failed.append((remote_path, str(e)))
                    log(f"  下载失败: {filename}: {e}", "ERROR")
        
        if (i + 1) % 20 == 0:
            log(f"  进度: {i+1}/{len(remote_files)} ({((i+1)/len(remote_files)*100):.1f}%)")
    
    log(f"下载完成: 成功 {len(downloaded)}, 失败 {len(failed)}", "OK")
    if failed:
        log(f"失败文件:", "WARN")
        for rf, err in failed[:5]:
            log(f"  - {Path(rf).name}: {err}")
    
    return downloaded


def run_remote_plotting(cred: Dict[str, Any], remote_run_dir: str, remote_plot_dir: str) -> bool:
    """
    在超算上运行绘图脚本，直接生成图片（不下载 HDF5 原始文件）
    返回是否成功
    """
    log("正在超算端执行绘图分析...", "STEP")
    
    # 1. 上传 remote_plot_script.py 到超算
    remote_script_path = f"{remote_run_dir}/remote_plot_script.py"
    local_script_path = str(Path(__file__).parent / "remote_plot_script.py")
    
    if not Path(local_script_path).exists():
        log(f"本地绘图脚本不存在: {local_script_path}", "ERROR")
        return False
    
    try:
        sftp_upload(cred, local_script_path, remote_script_path)
        log(f"已上传绘图脚本到超算: {remote_script_path}", "OK")
    except Exception as e:
        log(f"上传绘图脚本失败: {e}", "ERROR")
        return False
    
    # 2. 先检查远程输出目录是否有文件
    remote_output_dir = f"{remote_run_dir}/outputfiles/"
    check_cmd = f"ls {remote_output_dir} 2>/dev/null | head -20"
    r_check = ssh_cmd(cred, check_cmd, timeout=30)
    if r_check["returncode"] == 0 and r_check["stdout"].strip():
        log(f"远程输出目录内容（前20行）:\n{r_check['stdout'][:800]}", "INFO")
    else:
        log(f"远程输出目录为空或不存在: {remote_output_dir}", "WARN")
    
    # 3. 在超算上运行绘图脚本
    # 使用 bash -l 确保 module 命令可用（登录 shell）
    # 将 stderr 重定向到 stdout，方便捕获全部输出
    plot_cmd = (
        f"bash -l -c '"
        f"cd {remote_run_dir} && "
        f"mkdir -p {remote_plot_dir} && "
        f"module purge 2>/dev/null; "
        f"source /public1/soft/modules/module.sh 2>/dev/null; "
        f"module load python/3.9.6 2>/dev/null && "
        f"python {remote_run_dir}/remote_plot_script.py "
        f"--input_dir {remote_output_dir} "
        f"--output_dir {remote_plot_dir} "
        f"' 2>&1"
    )
    
    log("正在超算端运行绘图脚本（可能需要1-2分钟）...", "INFO")
    r = ssh_cmd(cred, plot_cmd, timeout=300)
    
    # 修复：正确的键名是 "stderr"（不是 "stderr"）
    rc = r["returncode"]
    stdout_text = r.get("stdout", "")
    stderr_text = r.get("stderr", "")
    
    if rc != 0:
        log(f"超算端绘图失败, 返回码: {rc}", "ERROR")
        # 打印更多输出以便调试
        if stdout_text:
            for line in stdout_text.strip().splitlines()[-20:]:
                print(f"    [stdout] {line}")
        if stderr_text:
            for line in stderr_text.strip().splitlines()[-10:]:
                print(f"    [stderr] {line}")
        return False
    else:
        log("超算端绘图完成 ✓", "OK")
        # 打印超算端输出（最后800字符，约20行）
        if stdout_text:
            for line in stdout_text.strip().splitlines()[-20:]:
                print(f"    {line}")
        return True


def download_plot_images(cred: Dict[str, Any], remote_plot_dir: str, local_plot_dir: Path) -> list:
    """
    从超算下载绘图结果图片（仅 PNG 文件，不下载 HDF5 原始文件）
    """
    log("正在下载绘图结果图片...", "STEP")
    
    # 获取远程图片文件列表
    r = ssh_cmd(cred, f"ls {remote_plot_dir}/*.png 2>/dev/null", timeout=30)
    remote_files = [l.strip() for l in r["stdout"].strip().splitlines() if l.strip() and l.strip().endswith('.png')]
    
    if not remote_files:
        log("远程未找到 PNG 图片文件", "WARN")
        return []
    
    log(f"远程找到 {len(remote_files)} 张图片")
    
    # 创建本地目录
    local_plot_dir.mkdir(parents=True, exist_ok=True)
    
    # 下载文件
    downloaded = []
    for i, remote_path in enumerate(remote_files):
        filename = Path(remote_path).name
        local_path = str(local_plot_dir / filename)
        
        try:
            client = get_ssh_client(cred)
            sftp = client.open_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()
            client.close()
            
            downloaded.append(local_path)
            log(f"  ✓ {filename}", "OK")
        except Exception as e:
            log(f"  下载失败: {filename}: {e}", "ERROR")
        
        if (i + 1) % 10 == 0:
            log(f"  进度: {i+1}/{len(remote_files)}")
    
    log(f"图片下载完成: {len(downloaded)}/{len(remote_files)} 张", "OK")
    return downloaded


def download_sample_hdf5(cred, remote_run_dir: str, local_dir: Path,
                         max_files: int = 5) -> list:
    """从超算下载少量 HDF5 plot 文件用于本地分析。
    
    仅下载 max_files 个文件（均匀采样），避免传输大量数据。
    """
    log("正在下载少量 HDF5 源文件用于本地分析...", "STEP")
    local_dir.mkdir(parents=True, exist_ok=True)
    
    # 查找远程 plt 文件（跳过 forced）
    r = ssh_cmd(cred, 
        f"ls {remote_run_dir}/outputfiles/*hdf5_plt_cnt_* 2>/dev/null | "
        f"grep -v forced | sort",
        timeout=30)
    remote_files = [l.strip() for l in r["stdout"].strip().splitlines() if l.strip()]
    
    if not remote_files:
        log("远程未找到 plot 文件", "WARN")
        return []
    
    # 均匀采样 max_files 个
    step = max(1, len(remote_files) // max_files)
    selected = [remote_files[i] for i in range(0, len(remote_files), step)][:max_files]
    
    log(f"远程 {len(remote_files)} 个 plt 文件，选取 {len(selected)} 个下载")
    downloaded = []
    for remote_path in selected:
        fname = Path(remote_path).name
        local_path = str(local_dir / fname)
        try:
            client = get_ssh_client(cred)
            sftp = client.open_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()
            client.close()
            downloaded.append(local_path)
            log(f"  ✓ {fname}")
        except Exception as e:
            log(f"  {fname}: {e}", "WARN")
    
    log(f"已下载 {len(downloaded)} 个 HDF5 文件到 {local_dir}/", "OK")
    return downloaded


def plot_density_vs_time(output_dir: Path, plot_dir: Path):
    """使用 h5py 读取 FLASH 1D HDF5 文件，绘制密度剖面。

    采用与 `plot_dens_easy_hpc.py` 一致的单元格中心坐标重建算法:
    - 无 yt 依赖
    - 单元格中心坐标 (非块中心/节点)
    - AMR 多块拼合 + 坐标去重
    """
    log("正在使用 h5py 生成密度剖面图...", "STEP")

    try:
        import h5py
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        # ── PPT-friendly plot style (fonts >= 18, English only) ──
        try:
            from output_processors.plotter.plot_style import apply_plot_style
            apply_plot_style()
        except ImportError:
            pass
        import numpy as np
    except ImportError as e:
        log(f"导入失败: {e}", "ERROR")
        return []

    # 查找 plot 文件（跳过 forced）
    all_files = sorted(output_dir.glob("*hdf5_plt_cnt_*"))
    plot_files = [f for f in all_files if "forced" not in f.name]

    if not plot_files:
        log("未找到 plot 文件，跳过绘图", "WARN")
        return []

    log(f"找到 {len(plot_files)} 个 plot 文件")
    plot_dir.mkdir(parents=True, exist_ok=True)

    # 读取所有时间步的数据
    times_s = []
    profiles = []  # (x, dens) 已排序去重

    for i, pf in enumerate(plot_files):
        try:
            with h5py.File(str(pf), "r") as f:
                # 读取时间
                if "current_time" in f.attrs:
                    time = float(f.attrs["current_time"])
                elif "real scalars" in f:
                    rs = f["real scalars"][:]
                    time = 0.0
                    for rec in rs:
                        name = rec["name"].decode("utf-8").strip() if isinstance(rec["name"], bytes) else str(rec["name"]).strip()
                        if name == "time":
                            time = float(rec["value"])
                            break
                else:
                    log(f"  {pf.name}: 无法读取时间, 跳过", "WARN")
                    continue

                if time <= 0:
                    continue

                # 读取密度和边界框
                raw = f["dens"][:]       # (nblocks, 1, 1, nx)
                bbox = f["bounding box"][:]  # (nblocks, 3, 2)

                # 单元格中心坐标重建
                nblocks, nz, ny, nx = raw.shape
                dense = np.squeeze(raw)  # (nblocks, nx) or (nx,)
                if dense.ndim == 1:
                    dense = dense.reshape(1, -1)

                x_list, d_list = [], []
                for b in range(nblocks):
                    xmin = float(bbox[b, 0, 0])
                    xmax = float(bbox[b, 0, 1])
                    dx = (xmax - xmin) / nx
                    xs = np.linspace(xmin + dx / 2, xmax - dx / 2, nx)
                    x_list.append(xs)
                    d_list.append(dense[b, :])

                x_all = np.concatenate(x_list)
                d_all = np.concatenate(d_list)

                # 排序 + 去重
                idx = np.argsort(x_all, kind="mergesort")
                x_sorted = x_all[idx]
                d_sorted = d_all[idx]
                unique_x, inverse = np.unique(x_sorted, return_inverse=True)
                if len(unique_x) < len(x_sorted):
                    d_unique = np.zeros_like(unique_x)
                    np.add.at(d_unique, inverse, d_sorted)
                    counts = np.bincount(inverse)
                    d_unique /= counts
                    x_final, d_final = unique_x, d_unique
                else:
                    x_final, d_final = x_sorted, d_sorted

                times_s.append(time)
                profiles.append((x_final, d_final))
                if (i + 1) % 20 == 0:
                    log(f"  {pf.name}  t={time:.4e}s ({i+1}/{len(plot_files)})", "INFO")
        except Exception as e:
            log(f"  {pf.name}: {e}", "WARN")

    if not times_s:
        log("没有成功读取任何数据", "ERROR")
        return []

    times_ns = np.array(times_s) * 1e9
    log(f"数据读取完成: {len(times_s)} 个时间步", "OK")

    plot_files_generated = []

    # ── 图 1: 各时间步独立密度图（选取部分）──
    n_plots = min(5, len(times_s))
    step = max(1, len(times_s) // n_plots)
    for i in range(n_plots):
        idx = min(i * step, len(times_s) - 1)
        xp, yp = profiles[idx]
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(xp, yp, "b-", linewidth=1.5)
        ax.set_xlabel("x [cm]")
        ax.set_ylabel(r"Density [g/cm$^3$]")
        ax.set_title(f"Density t={times_s[idx]:.3e}s")
        ax.grid(True, alpha=0.3)
        save_path = plot_dir / f"dens_t{i:04d}.png"
        fig.savefig(str(save_path), dpi=150, bbox_inches="tight")
        plt.close(fig)
        plot_files_generated.append(save_path)
        log(f"  ✓ {save_path.name}", "OK")

    # ── 图 2: 多时间点密度对比（h5py 单元格中心）──
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        n_curves = min(5, len(times_s))
        indices = np.linspace(0, len(times_s)-1, n_curves, dtype=int)
        colors = plt.cm.viridis(np.linspace(0, 1, n_curves))
        for idx, color in zip(indices, colors):
            xp, yp = profiles[idx]
            ax.plot(xp, yp, color=color, linewidth=1.5,
                    label=f't = {times_ns[idx]:.2f} ns')
        ax.set_xlabel("x [cm]")
        ax.set_ylabel(r"Density [g/cm$^3$]")
        ax.set_title("Density Profiles at Different Times (h5py cell-center)")
        ax.legend()
        ax.grid(True, alpha=0.3)
        save_path = plot_dir / "dens_multiple_times.png"
        fig.savefig(str(save_path), dpi=150, bbox_inches="tight")
        plt.close(fig)
        plot_files_generated.append(save_path)
        log(f"  ✓ {save_path.name}", "OK")
    except Exception as e:
        log(f"  多时间对比图失败: {e}", "WARN")

    # ── 图 3: 最后时刻密度剖面 ──
    try:
        xp, yp = profiles[-1]
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(xp, yp, "r-", linewidth=2)
        ax.set_xlabel("x [cm]")
        ax.set_ylabel(r"Density [g/cm$^3$]")
        ax.set_title(f"Final Density Profile t={times_ns[-1]:.2f} ns (h5py cell-center)")
        ax.grid(True, alpha=0.3)
        save_path = plot_dir / "dens_spatial_final.png"
        fig.savefig(str(save_path), dpi=150, bbox_inches="tight")
        plt.close(fig)
        plot_files_generated.append(save_path)
        log(f"  ✓ {save_path.name}", "OK")
    except Exception as e:
        log(f"  最终密度剖面失败: {e}", "WARN")

    # ── 图 4: 中心密度随时间变化 ──
    try:
        dens_center = []
        for xp, yp in profiles:
            mid = len(yp) // 2
            dens_center.append(yp[mid])
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(times_ns, dens_center, "b-", linewidth=2)
        ax.set_xlabel("Time (ns)")
        ax.set_ylabel(r"Density at Center [g/cm$^3$]")
        ax.set_title("Density at Center vs Time (h5py cell-center)")
        ax.grid(True, alpha=0.3)
        save_path = plot_dir / "dens_vs_time_center.png"
        fig.savefig(str(save_path), dpi=150, bbox_inches="tight")
        plt.close(fig)
        plot_files_generated.append(save_path)
        log(f"  ✓ {save_path.name}", "OK")
    except Exception as e:
        log(f"  中心密度时间演化失败: {e}", "WARN")

    log(f"所有图表已生成: {plot_dir}/", "OK")
    return plot_files_generated


def main():
    print("\n" + "=" * 60)
    print("  FLASH LaserSlab1D 超算运行 Demo (v4.1 h5py 版)")
    print(f"  用户目录: {SIM_USER_DIR}")
    print(f"  运行 ID: {_RUN_TIMESTAMP}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # ── 步骤1: 加载 SSH 凭据 ─────────────────────────────
    print("\n[步骤1] 加载 SSH 凭据...")
    print("-" * 50)
    
    try:
        from flash._core.credentials import load_ssh_credentials
    except ImportError:
        log("无法导入 flash._core.credentials", "ERROR")
        log("请确保 flash 包已正确安装", "ERROR")
        return None

    cred = load_ssh_credentials()
    if not cred:
        log("未找到 SSH 凭据", "ERROR")
        log("请先运行: python -m flash._core.credentials.manage", "INFO")
        return None
    
    log(f"已加载凭据: {cred.get('username', '?')}@{cred.get('host', '?')}", "OK")
    log(f"用户名: {SIM_USER_DIR}")
    
    # ── 步骤2: 生成全部输入文件 ────────────────────────
    print("\n[步骤2] 生成全部输入文件到独立运行文件夹")
    print("-" * 50)
    
    sim_path = f"{SIM_USER_DIR}/LaserSlab_hpc"
    objdir = f"{SIM_USER_DIR}/LaserSlab_hpc"
    par_filename = "laserslab1d_sc_demo.par"
    
    try:
        from flash.input_gen import create_input_files
        from flash.input_gen.gen_shell_script import ShellScriptGenerator
    except ImportError as e:
        log(f"导入失败: {e}", "ERROR")
        return None
    
    setup_cmd = ShellScriptGenerator.build_setup_cmd(
        sim_path=sim_path,
        objdir=objdir,
        parfile=par_filename,
    )
    log(f"SETUP_CMD: {setup_cmd}")
    
    DEMO_RUN_DIR.mkdir(parents=True, exist_ok=True)
    result = create_input_files(
        output_dir=str(DEMO_RUN_DIR),
        dimension=1,
        simulation_name="LaserSlab1d_sc_demo",
        target_material="aluminum",
        chamber_gas="helium",
        n_beams=1,
        par_filename=par_filename,
        generate_scripts=True,
        copy_eos_files=True,
        setup_cmd=setup_cmd,
        sim_user_dir=SIM_USER_DIR,
    )
    log(f"已生成 {len(result)} 个文件到 {DEMO_RUN_DIR}/")
    
    # ── 步骤3: 检查 SSH 连接 ─────────────────────────
    print("\n[步骤3] 检查 SSH 连接")
    print("-" * 50)
    
    try:
        r = ssh_cmd(cred, "echo 'SSH_OK'", timeout=15)
        if r["returncode"] != 0 or "SSH_OK" not in r["stdout"]:
            log(f"SSH 连接失败", "ERROR")
            return None
        log("SSH 连接成功 ✓", "OK")
    except Exception as e:
        log(f"SSH 连接异常: {e}", "ERROR")
        return None
    
    # ── 步骤4: 上传文件到超算并远程执行 ─────────
    print("\n[步骤4] 上传文件到超算并远程执行")
    print("-" * 50)
    
    remote_run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    remote_run_dir_rel = f"~/AI/AItemp/flash_sc_{remote_run_id}"
    
    r = ssh_cmd(cred, f"mkdir -p {remote_run_dir_rel} && cd {remote_run_dir_rel} && pwd", timeout=10)
    remote_run_dir = r["stdout"].strip()
    if not remote_run_dir:
        remote_run_dir = f"/home/{cred.get('username', '').split('@')[0]}/AI/AItemp/flash_sc_{remote_run_id}"
        log(f"使用 fallback 路径: {remote_run_dir}")
    else:
        log(f"远程临时目录: {remote_run_dir}")
    
    # 上传文件（输入文件 + 超算端绘图脚本）
    n_uploaded = 0
    for f in DEMO_RUN_DIR.iterdir():
        if f.is_file():
            remote_path = f"{remote_run_dir}/{f.name}"
            try:
                sftp_upload(cred, str(f), remote_path)
                n_uploaded += 1
            except Exception as e:
                log(f"上传失败: {f.name}: {e}")
    
    # 同时上传超算端绘图脚本（一键完成，不需手动上传）
    remote_script_path = f"{remote_run_dir}/remote_plot_script.py"
    local_script_path = str(Path(__file__).parent / "remote_plot_script.py")
    try:
        sftp_upload(cred, local_script_path, remote_script_path)
        n_uploaded += 1
        log(f"已上传绘图脚本: remote_plot_script.py")
    except Exception as e:
        log(f"上传绘图脚本失败: {e}", "WARN")
    
    log(f"已上传 {n_uploaded} 个文件到 {remote_run_dir}/")
    
    # 远程执行FLASH
    log("正在远程执行 FLASH 完整流程...", "INFO")
    flash_run_cmd = (
        f"cd {remote_run_dir} && "
        f"{MODULES_LOAD} && "
        f"bash run_flash.sh 2>&1 | tail -100"
    )
    r = ssh_cmd(cred, flash_run_cmd, timeout=600)
    
    if r["returncode"] != 0:
        log("远程 FLASH 执行失败", "ERROR")
        return None
    else:
        log("远程 FLASH 仿真完成 ✓", "OK")
    
    # ── 步骤5: 超算端绘图分析（不下载 HDF5 原始文件）──────────────────────
    print("\n[步骤5] 超算端绘图分析（不下载 HDF5 原始文件）")
    print("-" * 50)

    remote_plot_dir = f"{remote_run_dir}/{REMOTE_PLOT_DIR_NAME}"
    plot_success = run_remote_plotting(cred, remote_run_dir, remote_plot_dir)
    used_remote_plotting = plot_success

    if not plot_success:
        log("超算端绘图失败，尝试备选方案...", "WARN")
    
    # ── 步骤6: 下载超算端绘图图片（如果成功）──
    if plot_success:
        print("\n[步骤6] 下载超算端绘图图片")
        print("-" * 50)
        plot_files = download_plot_images(cred, remote_plot_dir, DEMO_PLOT_DIR)
        if plot_files:
            log(f"已下载 {len(plot_files)} 张图片到 {DEMO_PLOT_DIR}/", "OK")
        else:
            log("未下载到任何图片", "WARN")
    
    # ── 步骤7: 下载少量 HDF5 源文件 + h5py 本地分析 ──
    print("\n[步骤7] 下载 HDF5 源文件并用 h5py 本地分析")
    print("-" * 50)
    
    h5_dir = DEMO_OUTPUT_DIR / "hdf5_samples"
    downloaded_h5 = download_sample_hdf5(cred, remote_run_dir, h5_dir, max_files=5)
    
    if downloaded_h5:
        local_plots = plot_density_vs_time(h5_dir, DEMO_PLOT_DIR)
        if local_plots:
            log(f"h5py 本地分析完成: {len(local_plots)} 张图表", "OK")
            plot_success = True
    else:
        log("未下载到 HDF5 源文件，跳过 h5py 本地分析", "WARN")
    
    # ── 完成 ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  全流程完成!")
    print(f"  运行 ID: {_RUN_TIMESTAMP}")
    print(f"  输入文件: {DEMO_RUN_DIR}/")
    if used_remote_plotting:
        print(f"  ✓ 超算端绘图完成，图片已下载到: {DEMO_PLOT_DIR}/")
    if plot_success:
        print(f"  ✓ h5py 本地分析完成，图片: {DEMO_PLOT_DIR}/")
    print(f"  超算远程目录: {remote_run_dir}/")
    print(f"  SETUP_CMD: {setup_cmd}")
    print("=" * 60)
    
    return {
        "run_dir": str(DEMO_RUN_DIR),
        "output_dir": str(DEMO_OUTPUT_DIR),
        "plot_dir": str(DEMO_PLOT_DIR),
    }


if __name__ == "__main__":
    result = main()
    if result:
        print("\n✓ Demo 成功!")
    else:
        print("\n✗ Demo 失败!")
        sys.exit(1)
