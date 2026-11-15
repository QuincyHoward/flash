"""
FLASH Z-Pinch Be-Liner Geometry Verification v1.0 (1D cylindrical)
════════════════════════════════════════════════════════════════════

1D 圆柱 Z 箍缩几何构型验证（复用 FLASH4.8 官方模块 magnetoHD/ZPinch，
不加修改；运行参数由场景专用 gen_inputs.py 生成，暂不并入 input_gen/）：

  r ∈ [0, 0.5] cm 均匀网格（UG 128 格, iProcs=8, nxb=16）
  * fill (DD 气) : r < 0.29 cm,      ρ = 3e-2 g/cc, T = 100 eV（预热）
  * line (Be liner): 0.29 ≤ r ≤ 0.348 cm, ρ = 1.848 g/cc, T = 0.5 eV
  * vacu (真空):    r > 0.348 cm,    ρ = 1e-5 g/cc, T = 0.5 eV（max/minTemp 锁定）

物理配置（官方 stock）：+usm3t MHD + MGD 6 群（0.1-1e5 eV）+ Circuit
FileInput 电流驱动（current.dat, ns vs. MA）+ JiHeld 传导 + DaviesWen
磁阻 + HLLD。极短验证 tmax=1e-12 s（t≈0 电流≈0，纯初始构型检查）。

用法:
  cd <flash 包目录>
  python flash/scenarios/public/Fusion/zpinch/ZPinch_BeLiner/run_zpinch_verify.py

输出:
  outputfiles/run_NNNNNN/   ← FLASH chk/plt 产物
  flash_output/plots/       ← 径向剖面图（dens + 3 物种分数）
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
INPUT_DIR = SCRIPT_DIR / "flash_input"     # 生成产物 (par/current.dat/run_flash.sh)
OUTPUT_DIR = SCRIPT_DIR / "flash_output"
PLOTS_DIR = OUTPUT_DIR / "plots"

PAR_FILE = "zpinch_be.par"

# ── 几何定量采样点 r [cm] + 期望主导物种 + 期望密度 ──
SAMPLE_POINTS = [
    # (名称, r, 物种, 期望密度 g/cc)
    ("fill_axis",    0.15,  "fill", 3.0e-2),   # DD 气 (stock 30.e-3)
    ("fill_mid",     0.25,  "fill", 3.0e-2),
    ("liner_shell",  0.3175, "line", 1.848),   # Be liner 中部
    ("vacuum_out",   0.45,  "vacu", 1.0e-5),   # 外部真空
]

# ── 绘图设置 ──
PLOT_RMAX = 0.5
PLOT_TITLE = "Z-pinch Be-liner radial profile (1D cylindrical, t=1e-12 s)"
WORKDIR_DEFAULT = "/root/flash_zp_work"


def log(msg: str, level: str = "INFO"):
    tag = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]",
           "STEP": "[-]"}.get(level, "[i]")
    print(f"  {tag} {msg}")


# =====================================================================
# 步骤 1: 输入生成 (专用脚本) + 就绪检查
# =====================================================================

REQUIRED_FILES = [PAR_FILE, "current.dat", "run_flash.sh"]


def ensure_input_files() -> bool:
    """调用场景专用 gen_inputs.py 生成 par/current.dat, 并检查就绪。"""
    log("生成场景输入 (gen_inputs.py)...", "STEP")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "zpinch_gen_inputs", SCRIPT_DIR / "gen_inputs.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rc = mod.main(INPUT_DIR)
        if rc != 0:
            log("gen_inputs.main() 返回非零", "ERROR")
            return False
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        log(f"输入生成失败: {e}", "ERROR")
        return False

    missing = [f for f in REQUIRED_FILES if not (INPUT_DIR / f).is_file()]
    if missing:
        log(f"缺失必须文件: {missing}", "ERROR")
        return False
    log(f"  {len(REQUIRED_FILES)} 个输入就绪 ✓")
    return True


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
    run_log_name = "temp_delete/logs/wsl_console.log"
    console_log = logs_dir / run_log_name
    try:
        console_log.unlink()
    except OSError:
        pass

    _wd = os.environ.get("FLASH_RUN_WORKDIR", "").strip() or WORKDIR_DEFAULT
    os.environ["FLASH_RUN_WORKDIR"] = _wd
    log(f"隔离变量: FLASH_RUN_WORKDIR={_wd} (WSL ext4)")

    # ★ wsl.exe 会把复合命令在顶层 ;/&& 处拆分 ⇒ 全部逻辑收进脚本文件
    _wrap = INPUT_DIR / "temp_delete" / "run_flash_wsl.sh"
    _wrap.write_bytes(
        ("#!/bin/bash\n"
         "# 由 run_zpinch_verify.py 自动生成 —— 规避 wsl.exe 命令串拆分\n"
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
    log("首次运行需编译 FLASH (usm3t MHD 全量), 可能耗时 5~20 分钟 ...")

    flash_rc, console_txt = _run_wsl_with_progress(
        cmd, console_log, interval=120.0, timeout=7200.0)

    combined = console_txt.strip()
    log(combined[-3000:] if len(combined) > 3000 else combined)
    wsl_log = logs_dir / "wsl_run.log"
    wsl_log.write_text(combined, encoding="utf-8", errors="replace")

    flash_exit = flash_rc if flash_rc is not None else -1
    m = re.search(r"FLASH_EXIT_CODE=(\d+)", combined)
    if m:
        flash_exit = int(m.group(1))
    if flash_exit != 0:
        log(f"FLASH 运行失败 (exit={flash_exit}), 完整日志: {wsl_log}", "ERROR")
        return False, ""
    log(f"FLASH 运行成功 ✓ (完整日志: {wsl_log})")

    collect_dir = ""
    m2 = re.search(r"output ->\s*(\S+)", combined)
    if m2:
        collect_dir = m2.group(1)
        if collect_dir.startswith("/mnt/"):
            drive = collect_dir[5].upper()
            collect_dir = drive + ":" + collect_dir[6:].replace("/", "\\")
    else:
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
# 步骤 4: 几何验证分析 (1D 径向剖面)
# =====================================================================

def _read_time_scalar(h5_path) -> "float | None":
    """读取仿真时间: 兼容 chk (group) 与 plt (name/value 复合数据集)。"""
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


def _load_1d_profile(h5_path: Path, var_names: list[str]):
    """读取 1D UG HDF5, 拼接全域径向剖面。

    FLASH 1D HDF5: 变量数据集 shape=(nblocks, 1, 1, nx), 最后轴 = IAXIS(r)。
    "coordinates" 为块中心 (nblocks, 1), "block size" 为块内物理尺寸。
    返回 (r_array[N], {var: value_array[N]}) 或 None。
    """
    import h5py
    import numpy as np

    with h5py.File(str(h5_path), "r") as f:
        if "coordinates" not in f or "block size" not in f:
            return None
        coords = f["coordinates"][:]      # (nblocks, 1) 块中心
        bsize = f["block size"][:]        # (nblocks, 1) 块尺寸
        NXB = 16                          # -nxb=16 (run_flash.sh SETUP_CMD)
        rs, data = [], {v: [] for v in var_names}
        order = np.argsort(coords[:, 0])  # 按块中心排序保证拼接有序
        for b in order:
            ax0 = coords[b, 0] - bsize[b, 0] / 2.0
            dx = bsize[b, 0] / NXB
            xs = ax0 + (np.arange(NXB) + 0.5) * dx
            rs.append(xs)
            for vn in var_names:
                if vn not in f:
                    data[vn].append(np.full(NXB, float("nan")))
                    continue
                arr = np.asarray(f[vn][b]).reshape(-1)
                data[vn].append(arr[:NXB])
        r = np.concatenate(rs)
        prof = {v: np.concatenate(a) for v, a in data.items()}
        idx = np.argsort(r)
        return r[idx], {v: a[idx] for v, a in prof.items()}


def _plot_1d_profile(r, prof, out_dir: Path) -> list[str]:
    """绘制 1D 径向剖面图 (科研插图规范: 英文, Times New Roman, ≥18pt)。"""
    import matplotlib
    import numpy as np
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 18,
        "axes.labelsize": 20,
        "axes.titlesize": 18,
        "xtick.labelsize": 18,
        "ytick.labelsize": 18,
    })

    saved = []
    # ── 1) 密度剖面 (log) + 构型标注 ──
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.semilogy(r, np.maximum(prof["dens"], 1e-7), "k-", lw=2, label="dens")
    for x0, x1, lab, c in [(0, 0.29, "DD fill", "#9ecae1"),
                           (0.29, 0.348, "Be liner", "#fdae6b"),
                           (0.348, 0.5, "vacuum", "#d9d9d9")]:
        ax.axvspan(x0, x1, alpha=0.25, color=c)
        ax.text((x0 + x1) / 2, 2.5, lab,
                ha="center", va="top", fontsize=16)
    ax.set_xlabel("Radius r [cm]")
    ax.set_ylabel("Density [g/cm$^3$]")
    ax.set_xlim(0, PLOT_RMAX)
    ax.set_ylim(1e-6, 1e1)
    ax.set_title(PLOT_TITLE)
    ax.legend(loc="center left", fontsize=16)
    ax.grid(alpha=0.3)
    p1 = out_dir / "dens_profile.png"
    fig.savefig(p1, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved.append(p1)

    # ── 2) 物种分数剖面 ──
    fig, ax = plt.subplots(figsize=(10, 6))
    for vn, lab, c in [("fill", "fill (DD gas)", "#1f77b4"),
                       ("line", "line (Be liner)", "#ff7f0e"),
                       ("vacu", "vacu (tracer)", "#2ca02c")]:
        ax.plot(r, prof[vn], lw=2, color=c, label=lab)
    ax.set_xlabel("Radius r [cm]")
    ax.set_ylabel("Mass fraction")
    ax.set_xlim(0, PLOT_RMAX)
    ax.set_ylim(-0.05, 1.1)
    ax.set_title("Species mass fractions")
    ax.legend(fontsize=16)
    ax.grid(alpha=0.3)
    p2 = out_dir / "species_profile.png"
    fig.savefig(p2, dpi=180, bbox_inches="tight")
    plt.close(fig)
    saved.append(p2)
    log(f"  1D 剖面图完成: {', '.join(p.name for p in saved)}")
    return saved


def analyze_geometry(collect_dir: str) -> bool:
    """读取 HDF5 输出: 绘制径向剖面 + 定量采样核对。"""
    print("\n[步骤 4/4] 几何验证分析 (1D 径向剖面)")
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

    vars_need = ["dens", "fill", "line", "vacu"]
    loaded = None
    try:
        loaded = _load_1d_profile(h5, vars_need)
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        log(f"剖面读取失败: {e}", "WARN")
    if loaded is None:
        return False
    r, prof = loaded
    plot_ok = False
    try:
        saved = _plot_1d_profile(r, prof, PLOTS_DIR)
        plot_ok = bool(saved)
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        log(f"剖面绘图失败: {e}", "WARN")

    # ── 定量采样核对 ──
    checks = []
    all_ok = True
    for name, rq, spec, rho_exp in SAMPLE_POINTS:
        i = int(np.argmin(np.abs(r - rq)))
        rho = float(prof["dens"][i])
        frac = float(prof[spec][i])
        dens_ok = (not math.isnan(rho)) and (abs(rho - rho_exp) / rho_exp < 1.0)
        spec_ok = (not math.isnan(frac)) and (frac >= 0.9)
        ok = bool(dens_ok and spec_ok)
        if not ok:
            all_ok = False
        checks.append({"name": name, "r_cm": rq, "r_sampled_cm": float(r[i]),
                       "species": spec, "rho_expected": rho_exp,
                       "rho_sampled": rho, "species_fraction": frac, "ok": ok})
        status = "OK " if ok else "FAIL"
        log(f"  [{status}] {name:14s} (r={rq:.4f}) "
            f"ρ={rho:.3e} (期望 {rho_exp:.1e}) X({spec})={frac:.4f}")

    report = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "source_file": h5.name,
        "simulation_time_s": sim_time,
        "plot_ok": plot_ok,
        "all_geometry_checks_passed": all_ok,
        "checks": checks,
    }
    out_json = OUTPUT_DIR / "geometry_check.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    log(f"核对报告: {out_json}")

    print("\n" + "=" * 65)
    if all_ok:
        print(" 几何验证通过: DD 充气/Be liner/真空 三区分布全部吻合!")
    else:
        print(" 几何验证存在 FAIL 项, 请查看上方采样表与 geometry_check.json")
    print(f"  剖面图:  {PLOTS_DIR}")
    print("=" * 65)
    return all_ok


# =====================================================================
# 主入口
# =====================================================================

def main(mode: str | None = None) -> bool:
    print("\n" + "=" * 65)
    print(" FLASH Z-Pinch Be-Liner Geometry Verification v1.0 (1D cyl)")
    print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)
    print("""
  几何构型 (1D 圆柱 r ∈ [0, 0.5] cm, 官方 magnetoHD/ZPinch stock):
    DD 充气: r < 0.29 cm,  ρ = 3e-2 g/cc, T = 100 eV (预热)
    Be liner: 0.29 ≤ r ≤ 0.348 cm, ρ = 1.848 g/cc, T = 0.5 eV
    真空:     r > 0.348 cm, ρ = 1e-5 g/cc (T 锁定 0.5 eV)
  验证: tmax = 1e-12 s (极短, t≈0 电流≈0, 纯初始构型检查)
  输入: gen_inputs.py 装配 (input_gen 隔离模块生成; current.dat 留场景)
""")

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

    print("\n[步骤 1/4] 生成输入 + 就绪检查")
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
    import numpy as np  # noqa: F401  (采样需要, 提前校验环境)
    success = main()
    if success:
        print("\n 几何验证全流程成功结束!")
    else:
        print("\n 几何验证失败!")
        sys.exit(1)
