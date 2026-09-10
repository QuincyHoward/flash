# -*- coding: utf-8 -*-
"""三机 (WSL / NC-E / BSCC-T6) SNBOneCH_ml 一致性检验 + 速度对比.

用法:
    python compare_machines.py            # 对比 flash_output/ 下三机输出
    python compare_machines.py --plot     # 额外输出叠加剖面图

输出目录约定 (SNBOneCH_ml.py 生成):
    flash_output/                    WSL: snbonech_* + walltime_wsl.txt
    flash_output/hpc_flash_ssh/      NC-E
    flash_output/hpc_flash_ssh_2/    BSCC-T6
"""
import re
import sys
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent.parent.parent.parent.parent.parent.parent  # 仓库根 (含 flash 包)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_DIR = SCRIPT_DIR.parent.parent / "flash_output"  # SNBOneCH_ml/flash_output
MACHINES = [
    ("WSL (4/8/16 proc)", OUT_DIR, "walltime_wsl.txt"),
    ("NC-E (flash_ssh)", OUT_DIR / "hpc_flash_ssh", "wsl_run_snbonech.log"),
    ("BSCC (flash_ssh_2)", OUT_DIR / "hpc_flash_ssh_2", "wsl_run_snbonech.log"),
]
VARS = ["dens", "tele", "tion", "qenl"]


def final_plt(outdir: Path):
    """终态 plt: 优先 forced 帧 (tmax 精确对齐), 否则最末常规帧。"""
    if not outdir.is_dir():
        return None
    fs = sorted(outdir.glob("snbonech_forced_hdf5_plt_cnt_*"))
    if not fs:
        fs = sorted(outdir.glob("snbonech_hdf5_plt_cnt_*"))
    return fs[-1] if fs else None


def wall_seconds(outdir: Path, source: str) -> float:
    """墙钟: WSL 读 walltime_wsl.txt; HPC 读收集日志中的 WALL_SECONDS 行。"""
    p = outdir / source
    if not p.is_file():
        return float("nan")
    txt = p.read_text(encoding="utf-8", errors="replace")
    if source.endswith("wsl.txt"):
        try:
            return float(txt.strip().splitlines()[0])
        except (ValueError, IndexError):
            return float("nan")
    m = re.search(r"WALL_SECONDS=([0-9.eE+-]+)", txt)
    return float(m.group(1)) if m else float("nan")


def load_state(f: Path):
    """载入终态 plt: (x, {var: arr}, time)。非叶子块过滤 (load 规范)。"""
    from flash.output_processors.loader import FlashDataLoader
    c = FlashDataLoader(str(f)).load(compute_derived=False, extraction_mode="yt")
    x = np.asarray(c.x, dtype=float).ravel()
    data = {}
    for v in VARS:
        arr = c.data.get(v)
        if arr is not None:
            data[v] = np.asarray(arr, dtype=float).ravel()
    return x, data, float(c.simulation_time)


def main() -> int:
    ap_plot = "--plot" in sys.argv
    states, walls = {}, {}
    print("=" * 74)
    print(" 三机一致性检验 + 速度对比 (SNBOneCH_ml 终态)")
    print("=" * 74)
    for name, outdir, wsrc in MACHINES:
        f = final_plt(outdir)
        if f is None:
            print(f"  ✗ {name}: 无 plt ({outdir})")
            continue
        try:
            x, data, t = load_state(f)
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ {name}: 读取失败 {f.name}: {exc}")
            continue
        walls[name] = wall_seconds(outdir, wsrc)
        states[name] = (x, data, t, f)
        nvars = ", ".join(v for v in VARS if v in data)
        print(f"  ✓ {name}: {f.name}  t={t:.4e} s  vars=[{nvars}]  "
              f"wall={walls[name]:.1f} s")

    if len(states) < 2:
        print("可用机 <2, 无法对比")
        return 1

    # ── 速度表 ──
    print("\n── 速度对比 (tmax 内墙钟) ──")
    base_name = next(iter(walls))
    for name, w in walls.items():
        spd = f"  ({walls[base_name] / w:.2f}x vs {base_name})" if w == w else ""
        print(f"  {name:<22} {w:>10.1f} s{spd}")

    # ── 一致性: 两两逐变量相对偏差 (公共网格插值对齐) ──
    names = list(states)
    print("\n── 终态一致性 (rel diff = |a-b| / max(|a|,|b|,floor); 逐点插值对齐) ──")
    print("    max 含界面尖峰格点 (AMR 分块差异), median/P99.9 反映主体解一致性")
    floor = {"dens": 1e-12, "tele": 1.0, "tion": 1.0, "qenl": 1e-30}
    worst = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            na, nb = names[i], names[j]
            xa, da, _, _ = states[na]
            xb, db, _, _ = states[nb]
            for v in VARS:
                if v not in da or v not in db:
                    continue
                m = (da[v] != 0) | (db[v] != 0)
                if m.sum() == 0:
                    continue
                bi = np.interp(xa[m], xb, db[v])
                rel = np.abs(da[v][m] - bi) / np.maximum(
                    np.maximum(np.abs(da[v][m]), np.abs(bi)), floor[v])
                k = f"{na} vs {nb}"
                worst[(k, v)] = (float(rel.max()), float(np.median(rel)),
                                 float(np.percentile(rel, 99.9)))
    hdr = f"  {'机对':<40}" + "".join(
        f"{v:>21}" for v in VARS)
    print(hdr + "   (每格: max/median/P99.9)")
    pairs = sorted({k for k, _ in worst})
    for p in pairs:
        row = f"  {p:<40}"
        for v in VARS:
            t3 = worst.get((p, v))
            if t3 is None:
                row += f"{'—':>21}"
            else:
                row += f"  {t3[0]:.1e}/{t3[1]:.1e}/{t3[2]:.1e}"
        print(row)
    print("\n判读: rel diff ≲1e-6 完全一致; 1e-6~1e-3 MPI 分块/舍入级差异; "
          ">1e-3 需人工排查")

    # ── 可视化 ──
    if ap_plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        plt.rcParams.update({"font.size": 20, "axes.titlesize": 24,
                             "axes.labelsize": 22, "legend.fontsize": 17,
                             "font.family": "DejaVu Sans"})
        fig, axes = plt.subplots(2, 2, figsize=(15, 9), constrained_layout=True)
        colors = {"WSL": "#1f77b4", "NC-E": "#d62728", "BSCC": "#2ca02c"}
        for name, (x, data, t, _) in states.items():
            key = next((k for k in colors if name.startswith(k)), None)
            for ax, v in zip(axes.ravel(), VARS):
                if v in data:
                    m = data[v] != 0 if v != "dens" else np.ones_like(data[v], bool)
                    ax.semilogy(x[m] * 1e4, np.abs(data[v][m]) + 1e-300,
                                lw=2, color=colors.get(key), alpha=0.8,
                                label=name)
        for ax, v in zip(axes.ravel(), VARS):
            ax.set_title(v)
            ax.set_xlabel(r"x [$\mu$m]")
            ax.grid(alpha=0.3, lw=0.7)
        axes[0, 0].legend(loc="best")
        fig.suptitle("SNBOneCH_ml final-state cross-machine consistency")
        out_png = OUT_DIR / "cross_machine_consistency.png"
        fig.savefig(str(out_png), dpi=450)
        plt.close(fig)
        print(f"\n叠加剖面图: {out_png.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
