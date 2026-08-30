"""check_chk_products.py — layer_tracer_CH_ml chk 产物设计正确性检查
═══════════════════════════════════════════════════════════════════

检查 *chk* 检查点文件 (非 plt) 的:
  1. 密度分布随时间变化  → chk_dens_timespace.png + chk_dens_profiles.png
  2. 物质标记分布随时间变化 → chk_species_timespace.png (8 物种 0/1 阶跃)

用法:
  python check_chk_products.py <chk_dir> [--out out_dir]

读取走 flash.output_processors.FlashDataLoader (extraction_mode="yt",
只取叶子块), chk 与 plt 同为 FLASH HDF5 结构, 含全部 unknown 变量。
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_ROOT = Path(__file__).resolve().parent
for _ in range(14):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from flash.output_processors.loader import FlashDataLoader

SPECIES = ["cham", "shld", "samp", "tar1", "tar2", "tar3", "tar4", "tar6"]
COLORS = {"cham": "tab:blue", "shld": "tab:green", "samp": "tab:red",
          "tar1": "tab:purple", "tar2": "tab:orange", "tar3": "tab:brown",
          "tar4": "tab:olive", "tar6": "tab:pink"}
# 设计预期: 各示踪层外边界 (um) 与厚度 delta=0.1um
EXPECT = {"shld": (0.0, 0.1), "tar1": (1.0, 1.1), "tar2": (2.0, 2.1),
          "tar3": (3.0, 3.1), "tar4": (4.0, 4.1), "tar6": (6.0, 6.1)}

plt.rcParams.update({
    "font.size": 18, "axes.titlesize": 21, "axes.labelsize": 19,
    "xtick.labelsize": 17, "ytick.labelsize": 17, "legend.fontsize": 14,
    "axes.linewidth": 2.0, "font.family": "DejaVu Sans",
})


def load_chk(chk: Path):
    """读取单个 chk → (time_s, x_cm, {var: 1d array})。"""
    c = FlashDataLoader(str(chk)).load(compute_derived=False,
                                       extraction_mode="yt")
    x = np.asarray(c.x).ravel()
    data = {}
    for var in ["dens"] + SPECIES:
        if var in c.data:
            data[var] = np.asarray(c.data[var]).ravel()
    return float(c.simulation_time), x, data


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("chk_dir")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    chk_dir = Path(args.chk_dir)
    out = Path(args.out) if args.out else chk_dir.parent.parent / "plots" / chk_dir.name
    out.mkdir(parents=True, exist_ok=True)

    chks = sorted(chk_dir.glob("*hdf5_chk*"))
    print(f"[i] 发现 {len(chks)} 个 chk 文件: {chk_dir}")
    if not chks:
        print("[X] 无 chk 文件")
        return 1

    records = []
    for f in chks:
        try:
            t, x, data = load_chk(f)
        except Exception as exc:  # noqa: BLE001
            print(f"[!] 跳过 {f.name}: {exc}")
            continue
        if x.size == 0 or "dens" not in data:
            continue
        records.append((t, x, data))
        print(f"    {f.name}: t={t:.4e} s, {x.size} cells, vars={sorted(data)}")
    if not records:
        print("[X] 无有效 chk 记录")
        return 1

    records.sort(key=lambda r: r[0])
    n = len(records)

    # ── 1. 密度时空图 (chk) ────────────────────────────────
    xmin = min(r[1].min() for r in records)
    xmax = max(r[1].max() for r in records)
    x_common = np.linspace(xmin, xmax, 4096)
    dens = np.empty((n, x_common.size))
    for i, (_, x, d) in enumerate(records):
        dens[i] = np.interp(x_common, x, d["dens"], left=np.nan, right=np.nan)
    t = np.array([r[0] for r in records])

    fig, ax = plt.subplots(figsize=(12, 6))
    X, T = np.meshgrid(x_common * 1e4, t * 1e9)
    pc = ax.pcolormesh(X, T, np.log10(np.maximum(dens, 1e-30)),
                       shading="auto", cmap="viridis")
    fig.colorbar(pc, ax=ax, label=r"$\log_{10}(\rho)$ [g/cm$^3$]")
    ax.set_xlabel(r"x [$\mu$m]")
    ax.set_ylabel("t [ns]")
    ax.set_title(f"chk density x-t map ({n} checkpoints)")
    fig.tight_layout()
    fig.savefig(out / "chk_dens_timespace.png", dpi=300)
    plt.close(fig)
    print(f"[OK] {out/'chk_dens_timespace.png'}")

    # ── 2. 密度剖面线图 (首/中/末 3 帧, zoom 固体区) ────────
    picks = sorted({0, n // 2, n - 1})
    fig, ax = plt.subplots(figsize=(12, 6))
    for i in picks:
        tt, x, d = records[i]
        m = (x * 1e4 >= -5) & (x * 1e4 <= 12)
        ax.semilogy(x[m] * 1e4, np.maximum(d["dens"][m], 1e-12), lw=2.2,
                    label=f"t = {tt*1e9:.4g} ns")
    ax.set_xlabel(r"x [$\mu$m]")
    ax.set_ylabel(r"Density [g/cm$^3$]")
    ax.set_title("chk density profiles (chk-based)")
    ax.set_xlim(-5, 12)
    ax.grid(True, which="both", alpha=0.25, lw=0.8)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "chk_dens_profiles.png", dpi=450)
    plt.close(fig)
    print(f"[OK] {out/'chk_dens_profiles.png'}")

    # ── 3. 物质标记时空图 (chk, 每物种一面板) ───────────────
    sps = [sp for sp in SPECIES if all(sp in r[2] for r in records)]
    fields = {sp: np.empty((n, x_common.size)) for sp in sps}
    for i, (_, x, d) in enumerate(records):
        o = np.argsort(x)
        for sp in sps:
            fields[sp][i] = np.interp(x_common, x[o], d[sp][o],
                                      left=np.nan, right=np.nan)
    fig, axes = plt.subplots(len(sps), 1, figsize=(10, 2.4 * len(sps)),
                             sharex=True, constrained_layout=True)
    axes = np.atleast_1d(axes)
    for ax, sp in zip(axes, sps):
        pcm = ax.pcolormesh(X, T, fields[sp], shading="auto",
                            cmap="viridis", vmin=0.0, vmax=1.0)
        ax.set_ylabel("t [ns]")
        ax.set_title(sp, loc="left", fontsize=14, fontweight="bold")
        ax.set_xlim(-2, 12)
        fig.colorbar(pcm, ax=ax, pad=0.01, label="fraction")
    axes[-1].set_xlabel(r"x [$\mu$m]")
    fig.suptitle("chk species fraction x-t maps (linear 0-1)",
                 fontsize=18, fontweight="bold")
    fig.savefig(out / "chk_species_timespace.png", dpi=300)
    plt.close(fig)
    print(f"[OK] {out/'chk_species_timespace.png'}")

    # ── 4. 数值核验: 末帧各标记层中心位置与 0/1 纯度 ────────
    t_last, x_last, d_last = records[-1]
    print("\n=== 设计正确性数值核验 (末帧) ===")
    ok_all = True
    for sp, (lo, hi) in EXPECT.items():
        if sp not in d_last:
            print(f"  {sp}: 变量缺失!")
            ok_all = False
            continue
        f = d_last[sp]
        inside = (x_last * 1e4 >= lo + 0.01) & (x_last * 1e4 <= hi - 0.01)
        outside = ((x_last * 1e4 >= lo - 0.5) & (x_last * 1e4 <= hi + 0.5)
                   & ~inside)
        v_in = float(np.mean(f[inside])) if inside.any() else float("nan")
        v_out_max = float(np.max(f[outside])) if outside.any() else float("nan")
        ok = (abs(v_in - 1.0) < 1e-6) and (v_out_max < 1e-6)
        ok_all &= ok
        print(f"  {sp} 层 [{lo:.1f},{hi:.1f}]um: 层内均值={v_in:.3e} "
              f"(期望1), 层外max={v_out_max:.3e} (期望0) → "
              f"{'OK' if ok else 'FAIL'}")
    # samp 基体: 在 [shldR, L6+delta] 内减去 6 个示踪层后的区域应为 1
    if "samp" in d_last:
        f = d_last["samp"]
        m = (x_last * 1e4 > 0.1) & (x_last * 1e4 < 6.1)
        for lo, hi in EXPECT.values():
            m &= ~((x_last * 1e4 >= lo + 0.02) & (x_last * 1e4 <= hi - 0.02))
        v = float(np.mean(f[m])) if m.any() else float("nan")
        print(f"  samp 基体区 (扣除示踪层): 均值={v:.3e} (期望1) → "
              f"{'OK' if abs(v-1.0) < 1e-6 else 'FAIL'}")
        ok_all &= abs(v - 1.0) < 1e-6
    print(f"=== 总体: {'PASS' if ok_all else 'FAIL'} ===")
    return 0 if ok_all else 2


if __name__ == "__main__":
    sys.exit(main())
