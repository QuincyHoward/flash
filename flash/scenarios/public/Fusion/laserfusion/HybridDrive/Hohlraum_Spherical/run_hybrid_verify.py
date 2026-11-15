"""
FLASH Hybrid-Drive Spherical Hohlraum (HD) Geometry Verification v1.0
══════════════════════════════════════════════════════════════════════

2D 柱坐标 (r-z) 混合驱动几何构型验证：
  Au 球形黑腔 (内半径 2.72 mm, 壁厚 30 um, 两极 LEH 半径 1.43 mm)
  + 中心 CH 球壳靶丸 (R=1.0 mm, 壳厚 150 um, 内 He 气 1e-3 g/cc)
  + 腔内 He 充气 0.96 mg/cm^3 + 腔外 He 真空 1e-6 g/cc

混合驱动 (HD) 参考: 贺贤土院士 HD 方案 —— ID 激光经 LEH 入射球形黑腔
内壁转热 X 射线预压缩靶丸, DD 激光再沿径向直照预压缩靶丸 ("推土机"
增压效应; MRE 10, 057401 (2025), 神光-100kJ 实验; Nat. Commun. HD 实验)。
本场景为球腔几何验证 (与 Hohlraum_AuCH 圆柱腔同尺度对照)。

极短时间验证: tmax = 1e-13 s, 不做实际物理仿真 (激光/传导全关,
辐射 MGD 10 群同源配置), 仅初始化网格 + 少量流体步, 核对材料分布。

用法:
  cd <flash 包目录>
  python flash/scenarios/public/Fusion/laserfusion/HybridDrive/Hohlraum_Spherical/run_hybrid_verify.py

输出:
  outputfiles/run_NNNNNN/   ← FLASH chk/plt 产物
  flash_output/plots/       ← 几何验证图 (dens + 4 物种分布)
  flash_output/geometry_check.json ← 定量核对结果
"""

import json
import math
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# 统一 stdout/stderr 为 UTF-8 (errors="replace"), 避免 GBK 控制台抛
# UnicodeEncodeError。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── 运行模式 ─────────────────────────────────────────
# 覆盖优先级: main(mode=...) > 环境变量 FLASH_RUN_MODE > 本行 RUN_MODE
RUN_MODE = "auto"

# ── 路径设置 ──────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_ROOT = _ROOT.resolve()
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_DIR = SCRIPT_DIR / "flash_input"     # FLASH 源文件在 flash_input/ 子目录
OUTPUT_DIR = SCRIPT_DIR / "flash_output"
PLOTS_DIR = OUTPUT_DIR / "plots"

PAR_FILE = "hyhohl.par"

# EOS 表: 10 群统一再生表 (2026-11-08 gen_hohlraum10.py, 与 Hohlraum_AuCH 同源)
EOS_TABLES = [
    ("he_10g", "Z02_1.00-20261108_2013.cn4"),              # He (cham + cgas)
    ("ch_10g", "Z06_0.50-Z01_0.50-20261108_2013.cn4"),     # CH (caps)
    ("au_10g", "Z79_1.00-20261108_2014.cn4"),              # Au (gold)
]

# ── 几何定量采样点 (r, z) [cm] + 期望主导物种 + 期望密度 ──
SAMPLE_POINTS = [
    # (名称, r, z, 物种, 期望密度 g/cc)
    ("gold_wall_equator",  0.2735, 0.0000, "gold", 19.32),
    ("gold_wall_45deg",    0.1934, 0.1934, "gold", 19.32),
    ("leh_fill_hole",      0.1400, 0.2360, "cham", 9.6e-4),
    ("caps_shell_pole",    0.0000, 0.0925, "caps", 1.0),
    ("caps_shell_equator", 0.0925, 0.0000, "caps", 1.0),
    ("cgas_center",        0.0000, 0.0000, "cgas", 1.0e-3),
    ("cham_fill_cavity",   0.1500, 0.1500, "cham", 9.6e-4),
    ("cham_vacuum_out",    0.3200, 0.0000, "cham", 1.0e-6),
    ("cham_vacuum_polar",  0.0500, 0.3000, "cham", 1.0e-6),
]

# ── 绘图变量与画幅 ──
PLOT_VARS = ["dens", "cham", "cgas", "caps", "gold"]
PLOT_XLIM = (0.0, 0.34)
PLOT_YLIM = (-0.34, 0.34)
PLOT_TITLE = "Hybrid-drive spherical hohlraum material map (2D r-z, t=1e-13 s)"
WORKDIR_DEFAULT = "/root/flash_hy_work"


def log(msg: str, level: str = "INFO"):
    tag = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]",
           "STEP": "[-]"}.get(level, "[i]")
    print(f"  {tag} {msg}")


# =====================================================================
# 步骤 1: 输入文件就绪检查 + EOS 表复制
# =====================================================================

REQUIRED_FILES = [
    "Config", "Makefile", "Simulation_data.F90", "Simulation_init.F90",
    "Simulation_initBlock.F90", PAR_FILE, "run_flash.sh",
]


def ensure_input_files() -> bool:
    """检查场景静态输入文件; EOS 表缺失时从 Gen_eos_op_data 注册表复制。"""
    log("检查 FLASH 输入文件...", "STEP")
    missing = [f for f in REQUIRED_FILES if not (INPUT_DIR / f).is_file()]
    if missing:
        log(f"缺失必须文件: {missing}", "ERROR")
        return False
    log(f"  {len(REQUIRED_FILES)} 个源文件就绪 ✓")

    # ── EOS 表复制 (canonical 名 → eos_op_data) ──
    ok = True
    for canonical, fname in EOS_TABLES:
        dst = INPUT_DIR / fname
        if dst.is_file():
            log(f"  {fname} 已就绪")
            continue
        try:
            from flash.input_gen.gen_eos_op import EOSOpacityGenerator
            gen = EOSOpacityGenerator()
            copied = gen.copy_eos_file(canonical, str(INPUT_DIR))
            if copied and Path(copied).is_file():
                log(f"  {fname} ← {canonical} ✓")
            else:
                log(f"  copy_eos_file({canonical}) 失败", "ERROR")
                ok = False
        except Exception as e:  # noqa: BLE001
            log(f"  EOS 表复制异常 ({canonical}): {e}", "ERROR")
            ok = False
    return ok


# =====================================================================
# 步骤 2-3: WSL 运行 (setup → make → run → collect)
# =====================================================================

def _to_wsl_path(win_path: Path) -> str:
    """归一为 WSL 路径 (/mnt/<drive>/...), 幂等。"""
    s = str(win_path)
    if s.startswith("/"):
        return s
    if ":" not in s:
        return s.replace("\\", "/")
    drive, rest = s.split(":", 1)
    return "/mnt/" + drive.lower() + rest.replace("\\", "/")


def _tail_lines(path: Path, n: int = 25, max_len: int = 160) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    lines = data.splitlines()
    return "\n".join(l[:max_len] for l in lines[-n:])


def _run_wsl_with_progress(cmd: str, console_log: Path,
                           interval: float = 120.0,
                           timeout: float = 7200.0) -> tuple[int, str]:
    """WSL 执行命令, 每 interval 秒回显日志尾部 (长任务保活可见)。"""
    start = time.monotonic()
    if os.name == "nt":
        argv = ["wsl", "bash", "-c", cmd]
    else:
        argv = ["bash", "-c", cmd]
    proc = subprocess.Popen(argv, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    last_report = start
    while proc.poll() is None:
        now = time.monotonic()
        if now - last_report >= interval:
            last_report = now
            elapsed = int(now - start)
            tail = _tail_lines(console_log)
            if tail.strip():
                log(f"[{elapsed}s] FLASH 运行中, 最近输出:")
                print(tail)
            else:
                log(f"[{elapsed}s] 尚无输出 (可能仍在 setup/编译阶段)...")
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


def run_wsl() -> tuple[bool, str]:
    """本地 WSL 运行 FLASH (setup→编译→运行→收集)。返回 (成功, 收集目录)。"""
    print("\n[步骤 2/4] 本地 WSL 部署 (无需上传)")
    print("-" * 50)
    wsl_dir = _to_wsl_path(INPUT_DIR)
    run_sh = INPUT_DIR / "run_flash.sh"
    if not run_sh.is_file():
        log(f"run_flash.sh 不存在: {run_sh}", "ERROR")
        return False, ""

    print("\n[步骤 3/4] WSL 运行 FLASH 仿真 (setup→编译→运行→收集)")
    print("-" * 50)
    logs_dir = INPUT_DIR / "temp_delete" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    run_log_name = "wsl_console.log"
    console_log = logs_dir / run_log_name
    try:
        console_log.unlink()
    except OSError:
        pass

    # 运行隔离 (与 ch_center/Hohlraum 场景同机制):
    #   FLASH_RUN_WORKDIR → WSL ext4 独立工作目录 (避免 drvfs HDF5 MPI-IO 问题)
    #   FLASH_COLLECT_DIR → 留空, run_flash.sh 自动分配 outputfiles/run_NNNNNN
    _wd = os.environ.get("FLASH_RUN_WORKDIR", "").strip() or WORKDIR_DEFAULT
    os.environ["FLASH_RUN_WORKDIR"] = _wd
    log(f"隔离变量: FLASH_RUN_WORKDIR={_wd} (WSL ext4)")

    # ★ wsl.exe 会把复合命令在顶层 ;/&& 处拆分 ⇒ 全部逻辑收进脚本文件
    _wrap = INPUT_DIR / "temp_delete" / "run_flash_wsl.sh"
    _wrap.write_bytes(
        ("#!/bin/bash\n"
         "# 由 run_hybrid_verify.py 自动生成 —— 规避 wsl.exe 命令串拆分\n"
         "set -u\n"
         'WSL_DIR="$1"; WORKDIR="$2"; LOG="$3"\n'
         'cd "$WSL_DIR" || exit 1\n'
         'export FLASH_RUN_WORKDIR="$WORKDIR"\n'
         "sed -i 's/\\r$//' run_flash.sh 2>/dev/null\n"
         'bash run_flash.sh > "$LOG" 2>&1\n'
         "rc=$?\n"
         'echo "FLASH_EXIT_CODE=$rc" >> "$LOG"\n'
         "exit $rc\n").encode(),
    )
    cmd = (f"bash '{_to_wsl_path(_wrap)}' '{wsl_dir}' "
           f"'{_to_wsl_path(Path(_wd))}' '{run_log_name}'")
    log(f"执行: wsl bash -c \"{cmd[:100]}...\"")
    log("首次运行需编译 FLASH, 可能耗时 5~20 分钟 ...")

    flash_rc, console_txt = _run_wsl_with_progress(
        cmd, console_log, interval=120.0, timeout=7200.0)

    combined = console_txt.strip()
    log(combined[-3000:] if len(combined) > 3000 else combined)
    wsl_log = logs_dir / "wsl_run.log"
    wsl_log.write_text(combined, encoding="utf-8", errors="replace")

    # 哨兵优先 (内层真相), 无哨兵才信进程 rc
    flash_exit = flash_rc if flash_rc is not None else -1
    m = re.search(r"FLASH_EXIT_CODE=(\d+)", console_txt)
    if m:
        flash_exit = int(m.group(1))
    if flash_exit != 0:
        log(f"FLASH 运行失败 (exit={flash_exit}), 完整日志: {wsl_log}", "ERROR")
        return False, ""
    log(f"FLASH 运行成功 ✓ (完整日志: {wsl_log})")

    # 从日志解析收集目录 (run_flash.sh 输出 "output -> <dir>")
    collect_dir = ""
    m2 = re.search(r"output ->\s*(\S+)", combined)
    if m2:
        collect_dir = m2.group(1)
        # WSL 内路径 → Windows 路径 (场景目录在 /mnt/e 下)
        if collect_dir.startswith("/mnt/"):
            drive = collect_dir[5].upper()
            collect_dir = drive + ":" + collect_dir[6:].replace("/", "\\")
    else:
        # 兜底: 找最新 run_NNNNNN
        cands = sorted(SCRIPT_DIR.glob("outputfiles/run_*"))
        if cands:
            collect_dir = str(cands[-1])
    if not collect_dir or not Path(collect_dir).exists():
        log(f"未找到输出收集目录: {collect_dir!r}", "ERROR")
        return False, ""
    h5s = sorted(Path(collect_dir).glob("*chk*")) or sorted(Path(collect_dir).glob("*plt*"))
    if not h5s:
        log(f"收集目录无 HDF5 产物: {collect_dir}", "ERROR")
        return False, ""
    log(f"找到 {len(h5s)} 个 HDF5 输出: {collect_dir}", "OK")
    return True, collect_dir


# =====================================================================
# 步骤 4: 几何验证分析
# =====================================================================

def _read_time_scalar(h5_path) -> "float | None":
    """读取仿真时间: 兼容 chk (group of datasets) 与 plt (name/value 复合数据集)。"""
    import h5py
    try:
        with h5py.File(str(h5_path), "r") as f:
            if "real scalars" not in f:
                return None
            rs = f["real scalars"]
            if isinstance(rs, h5py.Group):
                if "time" in rs:
                    return float(rs["time"][0])
                return None
            arr = rs[:]
            if arr.dtype.names and "name" in arr.dtype.names:
                for row in arr:
                    if row["name"].decode().strip().lower() == "time":
                        return float(row["value"])
            return None
    except Exception:  # noqa: BLE001
        return None


def _sample_point_h5py(h5_path: Path, r: float, z: float,
                       var_names: list[str]) -> dict[str, float] | None:
    """直接读 plot/chk HDF5, 在 AMR 叶块中找包含 (r,z) 的格心并取样。

    返回 {变量名: 格心值}; 找不到叶块或布局异常时返回 None。
    FLASH AMR HDF5 布局 (plot/chk 相同):
      - "coordinates" = **块中心** 物理坐标 (实测验证: 轴线块 coords[0]==size/2)
      - "block size"  = 块内部物理尺寸
      - 变量数据集 2D 时 shape=(nblocks, nz=1, ny, nx), 无 guard cell,
        最后两轴 (ny, nx) 对应 (JAXIS=z, IAXIS=r)。
    ★ 本场景 setup 固定 -nxb=16 -nyb=16。
    """
    import h5py
    import numpy as np

    NXB = 16   # -nxb=16 (r 方向块内格数)
    NYB = 16   # -nyb=16 (z 方向块内格数)

    with h5py.File(str(h5_path), "r") as f:
        if "coordinates" not in f or "bounding box" not in f:
            return None
        coords = f["coordinates"][:]          # (nblocks, ndim) 块中心物理坐标
        bsize = f["block size"][:]            # (nblocks, ndim) 块内部物理尺寸
        node_types = None
        if "node type" in f:
            node_types = f["node type"][:]

        # ── 定位包含采样点的叶块 ──
        blk = -1
        for b in range(coords.shape[0]):
            if node_types is not None and int(node_types[b]) != 1:
                continue
            ax0 = coords[b, 0] - bsize[b, 0] / 2.0     # ★ coords 是块中心
            ay0 = coords[b, 1] - bsize[b, 1] / 2.0
            if ax0 <= r <= ax0 + bsize[b, 0] and ay0 <= z <= ay0 + bsize[b, 1]:
                blk = b
                break
        if blk < 0:
            return None

        ax0 = coords[blk, 0] - bsize[blk, 0] / 2.0
        ay0 = coords[blk, 1] - bsize[blk, 1] / 2.0
        dx = bsize[blk, 0] / NXB
        dy = bsize[blk, 1] / NYB

        out: dict[str, float] = {}
        for vn in var_names:
            if vn not in f:
                out[vn] = float("nan")
                continue
            dset = f[vn]
            nx_ds = dset.shape[-1]
            ny_ds = dset.shape[-2]
            i_int = min(max(int((r - ax0) / dx), 0), NXB - 1)
            j_int = min(max(int((z - ay0) / dy), 0), NYB - 1)
            data = np.asarray(dset[blk]).reshape(ny_ds, nx_ds)
            out[vn] = float(data[j_int, i_int])
        return out


def _plot_amr_maps(h5_path: Path, out_dir: Path) -> list[str]:
    """逐叶块 pcolormesh 绘制 2D AMR 材料分布图 (多级 AMR 安全)。

    科研插图规范: 全英文, Times New Roman, 字号 >= 18pt。
    返回保存的图片路径列表。
    """
    import h5py
    import matplotlib
    import numpy as np
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap, LogNorm

    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 18,
        "axes.labelsize": 20,
        "axes.titlesize": 20,
        "xtick.labelsize": 18,
        "ytick.labelsize": 18,
    })

    saved = []
    with h5py.File(str(h5_path), "r") as f:
        coords = f["coordinates"][:]
        bsize = f["block size"][:]
        nt = f["node type"][:] if "node type" in f else None
        vars_avail = [v for v in ["dens"] + PLOT_VARS[1:] if v in f]
        leaf_blocks = []
        for b in range(coords.shape[0]):
            if nt is not None and int(nt[b]) != 1:
                continue
            entry = {"x0": coords[b, 0] - bsize[b, 0] / 2.0,
                     "y0": coords[b, 1] - bsize[b, 1] / 2.0,
                     "dx": bsize[b, 0] / 16.0, "dy": bsize[b, 1] / 16.0,
                     "data": {}}
            for vn in vars_avail:
                entry["data"][vn] = np.asarray(f[vn][b]).reshape(16, 16)
            leaf_blocks.append(entry)
    nb_leaf = len(leaf_blocks)

    # ── 1) 材料分类图 (dominant species): 最直观的几何验证 ──
    dom_order = PLOT_VARS[1:]                       # cham, cgas, caps
    mat_cmap = ListedColormap(["#9ecae1", "#74c476", "#fdae6b", "#6b6ecf"])
    mat_norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5], mat_cmap.N)
    fig, ax = plt.subplots(figsize=(9, 9))
    for e in leaf_blocks:
        dom = np.argmax(np.stack([e["data"][v] for v in dom_order]),
                        axis=0).astype(float)
        xe = e["x0"] + np.arange(17) * e["dx"]
        ye = e["y0"] + np.arange(17) * e["dy"]
        ax.pcolormesh(xe, ye, dom, cmap=mat_cmap, norm=mat_norm, shading="flat")
    cbar = fig.colorbar(matplotlib.cm.ScalarMappable(cmap=mat_cmap, norm=mat_norm),
                        ax=ax, ticks=[0, 1, 2, 3])
    cbar.ax.set_yticklabels(["He fill/vac", "He capsule gas", "CH shell", "Au wall"])
    ax.set_xlabel("Radius r [cm]")
    ax.set_ylabel("Axial z [cm]")
    ax.set_aspect("equal")
    ax.set_title(PLOT_TITLE)
    ax.set_xlim(*PLOT_XLIM)
    ax.set_ylim(*PLOT_YLIM)
    p1 = out_dir / "material_map.png"
    fig.savefig(p1, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved.append(p1)

    # ── 2) 密度图 (log) + 各物种质量分数 ──
    panel_spec = [("dens", "Density [g/cm$^3$]", LogNorm(vmin=1e-6, vmax=30), "log")]
    for vn in dom_order:
        panel_spec.append((vn, f"{vn} mass fraction", None, "linear"))
    ncols = 2
    nrows = math.ceil(len(panel_spec) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(13, 6 * nrows))
    axes = np.atleast_1d(axes).ravel()
    for ax, (vn, label, norm, mode) in zip(axes, panel_spec):
        for e in leaf_blocks:
            xe = e["x0"] + np.arange(17) * e["dx"]
            ye = e["y0"] + np.arange(17) * e["dy"]
            data = np.maximum(e["data"][vn], 1e-12) if mode == "log" else e["data"][vn]
            ax.pcolormesh(xe, ye, data, norm=norm, shading="flat", cmap="inferno")
        ax.set_xlabel("Radius r [cm]")
        ax.set_ylabel("Axial z [cm]")
        ax.set_aspect("equal")
        ax.set_title(label)
        ax.set_xlim(*PLOT_XLIM)
        ax.set_ylim(*PLOT_YLIM)
        if mode == "log":
            fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap="inferno"),
                         ax=ax, label=label)
    for ax in axes[len(panel_spec):]:
        ax.axis("off")   # 多余面板留空
    p2 = out_dir / "geometry_maps.png"
    fig.savefig(p2, dpi=150, bbox_inches="tight")
    plt.close(fig)
    saved.append(p2)
    log(f"  AMR 分布图完成 ({nb_leaf} leaf blocks): "
        f"{', '.join(p.name for p in saved)}")
    return saved


def analyze_geometry(collect_dir: str) -> bool:
    """读取 HDF5 输出: 绘制几何分布图 + 定量采样核对。"""
    print("\n[步骤 4/4] 几何验证分析 (output_pro)")
    print("-" * 50)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    cdir = Path(collect_dir)
    plts = sorted(cdir.glob("*plt*"))
    chks = sorted(cdir.glob("*chk*"))
    h5 = plts[-1] if plts else (chks[-1] if chks else None)
    if h5 is None:
        log("无 HDF5 文件可分析", "ERROR")
        return False
    log(f"分析文件: {h5.name}")

    sim_time = _read_time_scalar(h5)
    log(f"  仿真时间 = {sim_time:.3e} s" if sim_time is not None else "  仿真时间未知")

    # ── 1) 分布图 (自研逐叶块 AMR 绘图) ──
    plot_ok = False
    try:
        saved = _plot_amr_maps(h5, PLOTS_DIR)
        plot_ok = bool(saved)
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        log(f"AMR 绘图失败: {e}", "WARN")

    # ── 2) 定量采样核对 (独立 h5py 路径) ──
    checks = []
    all_ok = True
    for name, r, z, spec, rho_exp in SAMPLE_POINTS:
        vals = _sample_point_h5py(h5, r, z, ["dens", spec])
        if vals is None:
            checks.append({"name": name, "r": r, "z": z, "ok": False,
                           "error": "no leaf block / bad layout"})
            all_ok = False
            continue
        rho = vals.get("dens", float("nan"))
        frac = vals.get(spec, float("nan"))
        # 容差: 密度 2 倍因子 (AMR 格心可能落在界面半格内), 物种分数 ≥ 0.9
        rho_finite = not math.isnan(rho)
        frac_finite = not math.isnan(frac)
        dens_ok = rho_finite and (abs(rho - rho_exp) / rho_exp < 1.0)
        spec_ok = frac_finite and (frac >= 0.9)
        ok = bool(dens_ok and spec_ok)
        if not ok:
            all_ok = False
        checks.append({"name": name, "r_cm": r, "z_cm": z, "species": spec,
                       "rho_expected": rho_exp, "rho_sampled": rho,
                       "species_fraction": frac, "ok": ok})
        status = "OK " if ok else "FAIL"
        log(f"  [{status}] {name:20s} (r={r:.4f}, z={z:+.4f}) "
            f"ρ={rho:.3e} (期望 {rho_exp:.1e}) X({spec})={frac:.4f}")

    report = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "source_file": h5.name,
        "simulation_time_s": None,
        "plot_ok": plot_ok,
        "all_geometry_checks_passed": all_ok,
        "checks": checks,
    }
    report["simulation_time_s"] = _read_time_scalar(h5)
    out_json = OUTPUT_DIR / "geometry_check.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    log(f"核对报告: {out_json}")

    print("\n" + "=" * 65)
    if all_ok:
        print(" 几何验证通过: Au 球壳/LEH/CH 壳/靶丸气/充气/真空 全部吻合!")
    else:
        print(" 几何验证存在 FAIL 项, 请查看上方采样表与 geometry_check.json")
    print(f"  分布图:  {PLOTS_DIR}")
    print("=" * 65)
    return all_ok


# =====================================================================
# 主入口
# =====================================================================

def main(mode: str | None = None) -> bool:
    print("\n" + "=" * 65)
    print(" FLASH Direct-Drive CH Capsule Geometry Verification v1.0")
    print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)
    print("""
  几何构型 (2D 柱坐标 r-z, 混合驱动 HD 参考):
    Au 球形黑腔: 内半径 2.72mm, 壁厚 30um, 两极 LEH (半径 1.43mm)
    中心 CH 靶丸: 外半径 1.0mm, 壳厚 150um, 内 He 气 1e-3 g/cc
    腔内 He 充气 0.96 mg/cm^3; 腔外 He 真空 1e-6 g/cc
  验证: tmax = 1e-13 s (极短, 激光/传导关, 辐射 MGD 10 群同源配置)
""")

    # ── 运行模式判定 (与 ch_center 同机制) ──
    from flash.flash_run.execution import DEFAULT_POLICY, ExecutionTargetError, resolve_target
    _explicit = (mode or "").strip() or os.environ.get(
        "FLASH_RUN_MODE", "").strip() or RUN_MODE
    try:
        run_mode, _trace = resolve_target(_explicit, DEFAULT_POLICY)
    except ExecutionTargetError as exc:
        log("运行模式判定失败", "ERROR")
        for _line in str(exc).splitlines():
            print("  " + _line)
        return False
    for _line in _trace:
        print("  " + _line)

    print("\n[步骤 1/4] 检查输入文件 + EOS 表")
    print("-" * 50)
    if not ensure_input_files():
        return False

    if run_mode in ("wsl", "local"):
        ok, collect_dir = run_wsl()
        if not ok:
            return False
        return analyze_geometry(collect_dir)

    log(f"模式 {run_mode} 暂未在本场景实现 (几何验证仅需 wsl/local)", "ERROR")
    return False


if __name__ == "__main__":
    success = main()
    if success:
        print("\n 几何验证全流程成功结束!")
    else:
        print("\n 几何验证失败!")
        sys.exit(1)
