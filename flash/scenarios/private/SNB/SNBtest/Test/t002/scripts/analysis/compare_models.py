"""t002 对比分析 —— SNB (非局域) vs FL-SH (限流 Spitzer-Härm)

用法 (在 t002 目录下):
    python scripts/analysis/compare_models.py --tag cmp_2e-10
    python scripts/analysis/compare_models.py --tag full_1ns --target-ns 1.0

产出 (results/<tag>/):
    cmp_dens_profiles.png      密度剖面 (两腿 + 多时刻)
    cmp_tele_profiles.png      电子温度剖面 (两腿 + 多时刻)
    cmp_tele_diff_map.png      Δtele = SNB - FL-SH 的 x-t 图
    cmp_heat_flux.png          电子热流 q = -kappa*grad(T) 两腿对比 + SNB CORQ
    cmp_limiter.png            通量限制因子 fllm(x)
    summary.md / summary.json  参数与关键量汇总表

绘图规范: 全英文标签, 字号 >= 18 pt, DPI >= 450, 线宽 >= 2。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_T002 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_T002 / "common"))

import t002_common as C  # noqa: E402

import numpy as np                      # noqa: E402
import matplotlib                       # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt         # noqa: E402

from flash.output_processors.loader import FlashDataLoader  # noqa: E402

# ── 绘图规范 (用户要求: 英文 / >=18pt / 高 DPI / 粗线) ──────────
plt.rcParams.update({
    "font.size": 20, "axes.titlesize": 24, "axes.labelsize": 22,
    "xtick.labelsize": 20, "ytick.labelsize": 20, "legend.fontsize": 18,
    "axes.linewidth": 2.0, "xtick.major.width": 2.0, "ytick.major.width": 2.0,
    "lines.linewidth": 2.4, "font.family": "DejaVu Sans",
    "figure.max_open_warning": 0,
})

COLORS = {"flsh": "tab:blue", "snb": "tab:red"}
LABELS = {"flsh": "FL-SH (flux-limited, local)", "snb": "SNB (nonlocal)"}
ERG_TO_W = 1.0e-7      # erg/s -> W


# ══════════════════════════════════════════════════════════════
def list_plt(outdir: Path) -> List[Path]:
    """列出 plt 文件 (排除 forced 帧, 按编号升序)。"""
    files = [p for p in sorted(outdir.glob("*plt_cnt*")) if "forced" not in p.name]
    if not files:
        files = sorted(outdir.glob("*plt_cnt*"))
    return files


def load_frame(path: Path) -> Optional[Dict[str, Any]]:
    """读取单帧: {t, x, key(lower)}。+ug 均匀网格无需叶子块过滤。

    ★ FLASH 的 HDF5 plt 里变量名是**小写** (dens/tele/cond/fllm/qesx/corq/mfpe...),
    而 par 的 plot_var 白名单写的是大写 —— 阅读端必须统一折成小写键, 否则
    QESX/CORQ 这类诊断量会全部查不到 (曾导致热流图右 panel 空白)。
    """
    try:
        c = FlashDataLoader(str(path)).load(compute_derived=False)
    except Exception as exc:  # noqa: BLE001
        C.log(f"    读取失败 {path.name}: {exc}", "WARN")
        return None
    x = np.asarray(c.x).ravel()
    if x.size == 0:
        return None
    order = np.argsort(x)
    frame: Dict[str, Any] = {"t": float(c.simulation_time), "x_um": x[order] * 1e4}
    for k, v in c.data.items():
        a = np.asarray(v).ravel()
        if a.size == x.size:
            frame[str(k).lower()] = a[order]
    return frame


def pick(series: List[Dict[str, Any]], t_target: float) -> Optional[Dict[str, Any]]:
    """按最近时刻挑帧。"""
    if not series:
        return None
    return min(series, key=lambda r: abs(r["t"] - t_target))


def pair_frames(series: Dict[str, List[Dict[str, Any]]]
                ) -> List[Tuple[float, Dict[str, Any], Dict[str, Any]]]:
    """把两腿的帧按**最近时刻**配对 (不要求时刻严格相等)。

    两腿的 plt 触发步不同, 末帧时刻会有 ~1e-13 s 级差异 (如 0.1501 vs 0.1500 ns),
    直接用时刻集合求交会得到空集 —— 曾导致 Δtele 时空图被跳过。
    以帧数较多的一腿为基准, 逐帧在另一腿中找最近帧; 仅保留时间偏差 < 半帧间隔的配对。
    """
    a, b = series.get("flsh", []), series.get("snb", [])
    if not a or not b:
        return []
    base, other = (a, b) if len(a) >= len(b) else (b, a)
    if len(base) >= 2:
        dt = np.median(np.diff([r["t"] for r in base]))
    else:
        dt = max(base[0]["t"], 1e-12)
    out: List[Tuple[float, Dict[str, Any], Dict[str, Any]]] = []
    for fr in base:
        cand = pick(other, fr["t"])
        if cand is None:
            continue
        if len(base) == 1 or abs(cand["t"] - fr["t"]) <= 0.5 * dt + 1e-18:
            # 保证返回顺序恒为 (flsh, snb)
            if len(a) >= len(b):
                out.append((fr["t"], fr, cand))
            else:
                out.append((fr["t"], cand, fr))
    return out


def load_series(outdir: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for f in list_plt(outdir):
        fr = load_frame(f)
        if fr is not None:
            out.append(fr)
    out.sort(key=lambda r: r["t"])
    return out


def pick_nearest(series: List[Dict[str, Any]], t_target: float) -> Optional[Dict[str, Any]]:
    return pick(series, t_target)


def heat_flux(frame: Dict[str, Any]) -> Optional[np.ndarray]:
    """由 cond (kappa) 与 tele 计算电子热流 q = -kappa * dT/dx [W/cm^2]。

    键统一小写 (见 load_frame)。中心差分; cond/tele 均为 cell-centered。
    """
    if "cond" not in frame or "tele" not in frame:
        return None
    x = frame["x_um"]
    k = np.asarray(frame["cond"], dtype=float)
    T = np.asarray(frame["tele"], dtype=float)
    dx_cm = np.gradient(x) * 1e-4          # um -> cm
    dT = np.gradient(T, edge_order=2)
    return -k * dT / dx_cm * ERG_TO_W      # cond: erg/(cm s K) -> W/cm^2


# ══════════════════════════════════════════════════════════════
def _subsample(ser: List[Dict[str, Any]], max_n: int) -> List[Dict[str, Any]]:
    """帧数过多时等间隔抽样 (始终保留首末帧), 避免图例/配色被淹没。"""
    if max_n <= 0 or len(ser) <= max_n:
        return ser
    idx = np.unique(np.linspace(0, len(ser) - 1, max_n).round().astype(int))
    return [ser[i] for i in idx]


def fig_profiles(series: Dict[str, List[Dict[str, Any]]], var: str,
                 target_ns: float, save: Path, ylabel: str,
                 logy: bool = False, zoom: Optional[Tuple[float, float]] = None,
                 xlim: Optional[Tuple[float, float]] = None,
                 max_frames: int = 6,
                 ylim: Optional[Tuple[float, float]] = None) -> None:
    """两腿多时刻剖面线图 (帧数过多时自动抽样; 图例置于坐标区外)。"""
    fig, ax = plt.subplots(figsize=(15, 7.5), constrained_layout=True)
    cmaps = {"flsh": plt.get_cmap("Blues"), "snb": plt.get_cmap("Reds")}
    ls = {"flsh": "-", "snb": "--"}
    for model, ser_full in series.items():
        ser = _subsample(ser_full, max_frames)
        if not ser:
            continue
        ts = [r["t"] for r in ser]
        t0, t1 = min(ts), max(ts)
        for fr in ser:
            if var not in fr:
                continue
            frac = (0.32 + 0.66 * (fr["t"] - t0) / max(t1 - t0, 1e-30)
                    if len(ser) > 1 else 0.85)
            lab = f"{C.LEGS[model]['label']}  t={fr['t']*1e9:.3f} ns"
            y = np.asarray(fr[var], dtype=float)
            m = y > 0 if logy else np.ones_like(y, bool)
            ax.plot(fr["x_um"][m], y[m], lw=2.4, color=cmaps[model](frac),
                    ls=ls[model], label=lab)
    if logy:
        ax.set_yscale("log")
    if ylim:
        ax.set_ylim(*ylim)
    ax.set_xlabel(r"x [$\mu$m]")
    ax.set_ylabel(ylabel)
    ax.grid(True, which="both", alpha=0.25, lw=0.8)
    ax.set_xlim(xlim if xlim else zoom)
    n_show = len(_subsample(series.get("flsh", []), max_frames))
    n_show += len(_subsample(series.get("snb", []), max_frames))
    ax.set_title(f"{var} profiles — SNB vs FL-SH   "
                 f"(target t = {target_ns:.3f} ns; {n_show} curves shown)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10),
              ncol=4, fontsize=15, framealpha=0.9)
    fig.savefig(str(save), dpi=450)
    plt.close(fig)
    C.log(f"    {save.name} ✓")


def fig_tele_diff_map(series: Dict[str, List[Dict[str, Any]]], save: Path,
                      xlim: Tuple[float, float] = (-20.0, 40.0),
                      ylim_ns: Optional[float] = None) -> bool:
    """Δtele(x,t) 图: 两腿按最近时刻配对后在公共 x 网格上求差 (SNB - FL-SH)。"""
    pairs = pair_frames(series)
    if len(pairs) < 2:
        C.log(f"  可配对帧数 {len(pairs)} < 2, 跳过 Δtele 时空图", "WARN")
        return False
    xg = np.linspace(*xlim, 600)
    tt = np.array([p[0] for p in pairs]) * 1e9          # ns
    diff = np.empty((len(pairs), xg.size))
    for i, (_, fa, fb) in enumerate(pairs):
        Ta = np.interp(xg, fa["x_um"], fa["tele"])
        Tb = np.interp(xg, fb["x_um"], fb["tele"])
        diff[i] = Tb - Ta
    fig, ax = plt.subplots(figsize=(13, 6.5), constrained_layout=True)
    X, T = np.meshgrid(xg, tt)
    vmax = float(np.nanpercentile(np.abs(diff), 99)) or 1.0
    pc = ax.pcolormesh(X, T, diff, shading="auto", cmap="RdBu_r",
                       vmin=-vmax, vmax=vmax)
    cb = fig.colorbar(pc, ax=ax)
    cb.set_label(r"$\Delta T_e = T_e^{SNB} - T_e^{FL\text{-}SH}$  [K]")
    ax.set_xlabel(r"x [$\mu$m]")
    ax.set_ylabel("t [ns]")
    if ylim_ns:
        ax.set_ylim(0, ylim_ns)
    ax.set_title(r"Electron temperature difference  $\Delta T_e(x,t)$")
    fig.savefig(str(save), dpi=450)
    plt.close(fig)
    C.log(f"    {save.name} ✓ ({len(pairs)} 配对帧)")
    return True


def fig_heat_flux(series: Dict[str, List[Dict[str, Any]]], save: Path,
                  xlim: Tuple[float, float] = (-20.0, 40.0)) -> None:
    """左: 局域热流 q = -kappa*grad(T) [W/cm^2] (两腿) + SNB 腿自带 QESX。
    右: SNB 非局域源 CORQ [W/cm^3] 与电子平均自由程 MFPE [cm] (双 y 轴)。

    ⚠ 单位注意: QESX 是**热流** (erg/cm^2/s), CORQ 是**能量源项/散度**
    (erg/cm^3/s), 两者量级差 ~1e10, 不可同轴绘制 —— 故分置左右两图。
    """
    fig, axes = plt.subplots(1, 2, figsize=(19, 7), constrained_layout=True)

    # ── 左: 局域热流 ─────────────────────────────────────
    for model, ser in series.items():
        if not ser:
            continue
        fr = ser[-1]
        q = heat_flux(fr)
        if q is None:
            continue
        m = (fr["x_um"] >= xlim[0]) & (fr["x_um"] <= xlim[1])
        axes[0].plot(fr["x_um"][m], q[m], lw=2.6, color=COLORS[model],
                     label=f"{C.LEGS[model]['label']} $-\\kappa\\nabla T$ "
                           f"(t={fr['t']*1e9:.3f} ns)")
    fr_snb = series.get("snb", [None])[-1] if series.get("snb") else None
    if fr_snb is not None and "qesx" in fr_snb:
        m = (fr_snb["x_um"] >= xlim[0]) & (fr_snb["x_um"] <= xlim[1])
        axes[0].plot(fr_snb["x_um"][m],
                     np.asarray(fr_snb["qesx"])[m] * ERG_TO_W, lw=2.2,
                     color="tab:orange", ls="--",
                     label="SNB QESX (SH flux diagnostic)")
    axes[0].set_xlabel(r"x [$\mu$m]")
    axes[0].set_ylabel(r"$q_e$  [W/cm$^2$]")
    axes[0].set_title("Local electron heat flux")
    axes[0].grid(True, alpha=0.25, lw=0.8)
    axes[0].legend(loc="best", fontsize=15)

    # ── 右: SNB 非局域源 + 平均自由程 ────────────────────
    if fr_snb is not None:
        m = (fr_snb["x_um"] >= xlim[0]) & (fr_snb["x_um"] <= xlim[1])
        if "corq" in fr_snb:
            axes[1].plot(fr_snb["x_um"][m],
                         np.asarray(fr_snb["corq"])[m] * ERG_TO_W, lw=2.6,
                         color="tab:red",
                         label="CORQ (SNB nonlocal source)")
        if "mfpe" in fr_snb:
            ax2 = axes[1].twinx()
            ax2.loglog(fr_snb["x_um"][m], np.asarray(fr_snb["mfpe"])[m], lw=2.2,
                       color="tab:green", ls=":",
                       label=r"MFPE ($\lambda_{mfp}$)")
            ax2.set_ylabel(r"$\lambda_{mfp}$ [cm]", color="tab:green")
            ax2.tick_params(axis="y", labelcolor="tab:green")
    axes[1].set_xlabel(r"x [$\mu$m]")
    axes[1].set_ylabel(r"SNB source  [W/cm$^3$]")
    axes[1].set_title("SNB nonlocal energy source and mean free path")
    axes[1].grid(True, alpha=0.25, lw=0.8)
    h1, l1 = axes[1].get_legend_handles_labels()
    if not h1:
        axes[1].text(0.5, 0.5, "no SNB diagnostics in frame",
                     transform=axes[1].transAxes, ha="center", va="center",
                     fontsize=18, color="gray")
    else:
        axes[1].legend(loc="upper left", fontsize=15)
    fig.suptitle("Electron heat flux and SNB nonlocal source (final frame)",
                 fontsize=24, fontweight="bold")
    fig.savefig(str(save), dpi=450)
    plt.close(fig)
    C.log(f"    {save.name} ✓")


def fig_peak_vs_time(series: Dict[str, List[Dict[str, Any]]], save: Path) -> None:
    """峰值电子温度 / 峰值密度随时间的演化 (两腿对比)。"""
    fig, axes = plt.subplots(1, 2, figsize=(19, 7), constrained_layout=True)
    for model, ser in series.items():
        if not ser:
            continue
        t = np.array([r["t"] for r in ser]) * 1e9
        tmax_te = np.array([np.max(r["tele"]) for r in ser])
        tmax_de = np.array([np.max(r["dens"]) for r in ser])
        axes[0].plot(t, tmax_te, lw=2.6, color=COLORS[model],
                     marker="o", ms=7, label=C.LEGS[model]["label"])
        axes[1].plot(t, tmax_de, lw=2.6, color=COLORS[model],
                     marker="o", ms=7, label=C.LEGS[model]["label"])
    axes[0].set_xlabel("t [ns]")
    axes[0].set_ylabel(r"max $T_e$ [K]")
    axes[0].set_title(r"Peak electron temperature vs time")
    axes[1].set_xlabel("t [ns]")
    axes[1].set_ylabel(r"max $\rho$ [g/cm$^3$]")
    axes[1].set_title(r"Peak density vs time")
    for ax in axes:
        ax.grid(True, alpha=0.25, lw=0.8)
        ax.legend(loc="best", fontsize=17)
    fig.suptitle("Global maxima evolution — SNB vs FL-SH", fontsize=24,
                 fontweight="bold")
    fig.savefig(str(save), dpi=450)
    plt.close(fig)
    C.log(f"    {save.name} ✓")


def fig_limiter(series: Dict[str, List[Dict[str, Any]]], save: Path,
                xlim: Tuple[float, float] = (-20.0, 40.0)) -> None:
    fig, ax = plt.subplots(figsize=(13, 6.5), constrained_layout=True)
    for model, ser in series.items():
        if not ser:
            continue
        fr = ser[-1]
        if "fllm" not in fr:
            continue
        m = (fr["x_um"] >= xlim[0]) & (fr["x_um"] <= xlim[1])
        ax.plot(fr["x_um"][m], np.asarray(fr["fllm"])[m], lw=2.6,
                color=COLORS[model],
                label=f"{C.LEGS[model]['label']} "
                      f"({C.LEGS[model]['diff_eleFlMode']})")
    ax.set_xlabel(r"x [$\mu$m]")
    ax.set_ylabel(r"flux limiter factor $3\lambda$  (1 = unlimited)")
    ax.set_ylim(-0.05, 1.10)
    ax.grid(True, alpha=0.25, lw=0.8)
    ax.set_title("Flux limiter factor along x (final frame)")
    ax.legend(loc="best", fontsize=16)
    fig.savefig(str(save), dpi=450)
    plt.close(fig)
    C.log(f"    {save.name} ✓")


def write_summary(series: Dict[str, List[Dict[str, Any]]], outdir: Path,
                  tag: str, wall: Dict[str, str]) -> None:
    lines = ["# t002 对比测试汇总 (SNB vs FL-SH)", "",
             f"- tag: `{tag}`", f"- 生成时间: {C.stamp()}", "",
             "## ⚠ 差异归因声明 (必读)", "",
             "两腿**同时**存在两个差异因素, 观测到的 ΔTe / Δq 是两者叠加, "
             "**不得**归因于单一因素:", "",
             "| 因素 | FL-SH 腿 | SNB 腿 |", "|---|---|---|",
             "| 限流模式 `diff_eleFlMode` | `fl_minmax` (coef 0.06) | "
             "**`fl_none`** (无限制) |",
             "| 非局域 SNB 修正项 (`CORQ -> TELE`) | 无 | **有** |", "",
             "可分离性证据: 见 `cmp_limiter.png` 的 FL-SH `fllm` (=3λ) 剖面 —— "
             "`fllm≈1` 处限流器未激活 (该处差异主要来自 SNB 项); "
             "`fllm<1` 处两因素均有贡献。", ""]
    lines += ["| 项 | FL-SH | SNB |", "|---|---|---|"]
    rows = [
        ("FLASH 树", "标准 FLASH4.8", "FLASHSNB FLASH4.8"),
        ("diff_eleFlMode", "fl_minmax (coef 0.06)", "fl_none"),
        ("网格", "nxb=64, iProcs=8 → 512 格",
         "nxb=64, iProcs=8 → 512 格"),
        ("域", "[-400, 100] µm", "[-400, 100] µm"),
        ("激光", "5e14 W/cm2, 351 nm, 梯形 50ps/1ns/50ps",
         "5e14 W/cm2, 351 nm, 梯形 50ps/1ns/50ps"),
    ]
    for r in rows:
        lines.append("| " + " | ".join(r) + " |")
    for model in ("flsh", "snb"):
        ser = series.get(model, [])
        if not ser:
            continue
        ncell = ser[-1]["x_um"].size
        t_end = ser[-1]["t"]
        rows2 = [
            (f"{C.LEGS[model]['label']} 末帧", f"t = {t_end*1e9:.4f} ns",
             f"格数 = {ncell}"),
            (f"{C.LEGS[model]['label']} 峰值 tele",
             f"{np.max(ser[-1]['tele']):.4g} K",
             f"墙钟 {wall.get(model, 'N/A')}"),
        ]
        for r in rows2:
            lines.append("| " + " | ".join(r) + " |")
    lines += ["", "## 各帧最大值", "",
              "| 腿 | t [ns] | max dens | max tele [K] | max trad [K] |",
              "|---|---|---|---|---|"]
    for model in ("flsh", "snb"):
        for fr in series.get(model, []):
            lines.append(f"| {C.LEGS[model]['label']} | {fr['t']*1e9:.4f} | "
                         f"{np.max(fr['dens']):.4g} | {np.max(fr['tele']):.4g} | "
                         f"{np.max(fr['trad']):.4g} |")
    (outdir / "summary.md").write_text("\n".join(lines) + "\n",
                                       encoding="utf-8", newline="\n")
    data = {m: [{"t": r["t"], "ncell": int(r["x_um"].size),
                 "max_tele": float(np.max(r["tele"])),
                 "max_dens": float(np.max(r["dens"])),
                 "max_trad": float(np.max(r["trad"]))} for r in s]
            for m, s in series.items()}
    (outdir / "summary.json").write_text(json.dumps(data, indent=2),
                                         encoding="utf-8", newline="\n")
    C.log("    summary.md / summary.json ✓")


def read_walltime(model: str, tag: str) -> str:
    p = C.leg_output_dir(model) / (tag or "") / "walltime.txt"
    if not p.exists():
        p = C.leg_output_dir(model) / "walltime.txt"
    if not p.exists():
        return "N/A"
    lines = [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not lines:
        return "N/A"
    parts = lines[-1].split("\t")
    return f"{parts[3]} s" if len(parts) >= 4 else "N/A"


# ══════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="t002 SNB vs FL-SH 对比分析")
    ap.add_argument("--tag", default="cmp_2e-10", help="输出子目录名")
    ap.add_argument("--target-ns", type=float, default=None,
                    help="剖面图目标时刻 [ns]; 默认取末帧")
    ap.add_argument("--zoom", default="-20,40", help="局部放大范围 [µm] (a,b)")
    ap.add_argument("--max-frames", type=int, default=6,
                    help="每条腿在剖面图中最多绘制的帧数 (等间隔抽样, 默认 6)")
    ap.add_argument("--ylim-te", default=None,
                    help="tele 剖面 y 轴范围 (a,b); 如 0,2e8")
    args = ap.parse_args()

    z0, z1 = (float(v) for v in args.zoom.split(","))
    zoom = (z0, z1)

    print("\n" + "=" * 72)
    print(f" t002 对比分析: SNB vs FL-SH   tag={args.tag}   {C.stamp()}")
    print("=" * 72)

    series: Dict[str, List[Dict[str, Any]]] = {}
    for model in ("flsh", "snb"):
        d = C.leg_output_dir(model) / args.tag
        if not d.exists():
            d = C.leg_output_dir(model)
        series[model] = load_series(d)
        C.log(f"{C.LEGS[model]['label']}: {len(series[model])} 帧 ← {d}", "OK")
        for fr in series[model]:
            C.log(f"    t={fr['t']*1e9:.4f} ns  ncell={fr['x_um'].size}  "
                  f"maxTele={np.max(fr['tele']):.4g} K  vars={len(fr)-2}")

    if not any(series.values()):
        C.log("无可用数据", "ERROR")
        return 1

    outdir = C.RESULT_DIR / args.tag
    outdir.mkdir(parents=True, exist_ok=True)

    t_target = (args.target_ns * 1e-9 if args.target_ns
                else max((s[-1]["t"] for s in series.values() if s), default=0.0))
    C.log(f"目标时刻 t = {t_target*1e9:.4f} ns", "INFO")

    # 剖面图标题按 ns 显示 (曾误把秒当 ns 传入 → 标题恒为 0.000 ns)
    ylim_te = (tuple(float(v) for v in args.ylim_te.split(","))
               if args.ylim_te else None)
    nf = args.max_frames
    fig_profiles(series, "dens", t_target * 1e9,
                 outdir / "cmp_dens_profiles.png",
                 r"Density [g/cm$^3$]", logy=True, xlim=zoom, max_frames=nf)
    fig_profiles(series, "tele", t_target * 1e9,
                 outdir / "cmp_tele_profiles.png",
                 r"Electron temperature [K]", logy=False, xlim=zoom,
                 max_frames=nf, ylim=ylim_te)
    fig_profiles(series, "trad", t_target * 1e9,
                 outdir / "cmp_trad_profiles.png",
                 r"Radiation temperature [K]", logy=False, xlim=zoom,
                 max_frames=nf)
    fig_heat_flux(series, outdir / "cmp_heat_flux.png", xlim=zoom)
    fig_limiter(series, outdir / "cmp_limiter.png", xlim=zoom)
    fig_peak_vs_time(series, outdir / "cmp_peak_vs_time.png")
    fig_tele_diff_map(series, outdir / "cmp_tele_diff_map.png", xlim=zoom)

    wall = {m: read_walltime(m, args.tag) for m in ("flsh", "snb")}
    write_summary(series, outdir, args.tag, wall)
    C.log(f"结果目录: {outdir}", "OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
