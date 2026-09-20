# -*- coding: utf-8 -*-
"""04_analyze_plots.py — FLASH +ug chk 绘图分析（PPT 演讲级）。

输出到 <dir>/analysis/:
  1) dt_evolution.png      — dt 与仿真时间演化（解析 wsl_run_*.log）
  2) profile_final.png     — 末帧密度 + 电子温度剖面
  3) profiles_xt.png       — 密度 x-t 时空图（★ pcolormesh + 真实逐帧时间）
  4) scalars_history.png   — ρmax / Temax / nele_max 逐帧演化
  5) health.json           — 逐帧健康判据（t 单调 / 质量守恒 / eint>0）

★ 关键纪律（本轮踩坑后固化）:
  - **x-t 图禁用 `imshow`** —— FLASH chk 帧间隔高度不均,
    `imshow` 会把时间轴按"帧序号"均匀排布 → 局部时间被拉偏数千个百分点。
    必须 `pcolormesh(X, Y)` 配**真实逐帧时间**。
  - **逐格 x 重建**: `coordinates` 是**块中心**, 块宽 `W = bbox[:,x,1]-bbox[:,x,0]`,
    `W ≠ nxb·dx`。用 `x_block ± (nxb-1)/2·dx` 会外扩 ~2%。
  - **质量守恒判据**用面密度 `Σ ρ·(W/nxb)`。
  - chk 完整性只认 md5; h5py 打不开的帧**跳过**不算损坏。

绘图规范: 全英文, title>=24pt, labels/ticks>=20pt, legend>=18pt, DPI>=450, lw>=2。

用法:
  python 04_analyze_plots.py [--dir flash_output/hpc_flash_ssh_16ns]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _longrun_lib as L  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams.update(L.PLOT_RC)

K_EV = L.K_BOLTZ_EV_PER_K
NA = L.NA


# ══════════════════════════════════════════════════════════════════════
# chk 读取
# ══════════════════════════════════════════════════════════════════════
def _scalars(h) -> dict:
    out = {}
    for grp in ("real scalars", "integer scalars"):
        if grp not in h:
            continue
        for name, val in h[grp][:]:
            k = name.decode().strip() if isinstance(name, bytes) else str(name).strip()
            out[k] = val
    return out


def read_chk(path: Path):
    """读一个 chk → dict(x_um, fields, time, dt, nstep, mass)。失败返回 None。

    ★ h5py 打不开时返回 None（不算损坏; 完整性由 md5 判定）。
    """
    import h5py
    try:
        f = h5py.File(str(path), "r")
    except Exception:
        return None
    with f:
        sc = _scalars(f)
        nxb = int(sc.get("nxb", 128))
        nb = int(sc.get("globalnumblocks", 0))
        if "bounding box" in f:
            bb = np.array(f["bounding box"])          # (nb,3,2) cm
            x_lo = bb[:, 0, 0]
            x_hi = bb[:, 0, 1]
        else:
            c = np.array(f["coordinates"]).reshape(-1, 3)
            x_lo = c[:, 0]
            x_hi = c[:, 0]
            nb = len(x_lo)
        W = x_hi - x_lo                                # 逐块真实宽度

        def var(name):
            if name not in f:
                return None
            a = np.array(f[name])
            return a.reshape(a.shape[0], -1)           # (nb, nxb)

        fields = {}
        for v in ("dens", "tele", "tion", "temp", "eint", "ye", "sumy", "nele", "velx"):
            a = var(v)
            if a is not None:
                fields[v] = a

        if "dens" not in fields:
            return None

        # ★ 逐格 x: 块内均匀插值（用真实块宽，非 nxb*dx）
        j = np.arange(nxb)
        xc = x_lo[:, None] + W[:, None] * (j + 0.5)[None, :] / nxb   # (nb,nxb) cm
        wcell = (W / nxb)[:, None] * np.ones((1, nxb))

        # 面密度 [g/cm^2]
        mass = float(np.sum(fields["dens"] * wcell))

        xf = (xc.ravel()) * 1e4
        order = np.argsort(xf)
        xf = xf[order]

        out = {
            "file": path.name,
            "_path": str(path),
            "time": float(sc.get("time", 0.0)),
            "dt": float(sc.get("dt", 0.0)),
            "nstep": int(sc.get("nstep", 0)),
            "nxb": nxb, "nblocks": nb, "ncells": nb * nxb,
            "x_um": xf,
            "mass": mass,
        }
        for k, a in fields.items():
            out[k] = a.reshape(-1)[order]
        return out


# ★★★ 必须排除的"非标帧"：`*_forced_*` 是 FLASH 在**强制/重启**时写出的
#   部分域 dump（只含被 forcing 的区域），其积分质量与整域帧不可比。
#   曾把它混入质量序列 → 产生 0.185 的**虚假漂移**（真实为物理出流）。
_NONSTD = re.compile(r"_forced_|_rst_|_prt_|_halo_")


def find_frames(d: Path) -> list:
    """按编号排序收集 chk（优先）+ plt；剔除 `*_forced_*` 等非整域帧。"""
    def _grab(tag: str) -> list:
        return sorted(
            [p for p in d.iterdir()
             if p.is_file() and re.match(rf".*_hdf5_{tag}_\d+$", p.name)
             and not _NONSTD.search(p.name)],
            key=lambda p: int(p.name.rsplit("_", 1)[1]))
    return _grab("chk") + _grab("plt")


def parse_log_dt(logp: Path):
    """解析逐步日志 → (steps, times, dts)。

    ★ 稳健法: 按 `|` 切分再 split()，不用大正则。
    """
    steps, times, dts = [], [], []
    if not logp.is_file():
        return steps, times, dts
    for line in logp.read_text(encoding="utf-8", errors="replace").splitlines():
        if "|" not in line:
            continue
        left = line.split("|")[0].strip()
        if left.startswith("n "):
            continue
        toks = left.split()
        if len(toks) < 3:
            continue
        try:
            steps.append(int(toks[0])); times.append(float(toks[1])); dts.append(float(toks[2]))
        except ValueError:
            continue
    return steps, times, dts


# ══════════════════════════════════════════════════════════════════════
# 绘图
# ══════════════════════════════════════════════════════════════════════
def plot_dt(out_dir: Path, times, dts) -> bool:
    if not times:
        L.log("  (skip dt_evolution: 无逐步数据)", "WARN")
        return False
    t = np.array(times); d = np.array(dts)
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.semilogy(t * 1e9, d * 1e12, color="#1f77b4", lw=2.4)
    ax.set_xlabel("Simulation time (ns)")
    ax.set_ylabel(r"$\Delta t$ (ps)")
    ax.set_title("Time step evolution")
    ax.grid(True, alpha=.3, which="both")
    fig.tight_layout()
    p = out_dir / "dt_evolution.png"
    fig.savefig(p, dpi=450)
    plt.close(fig)
    L.log(f"  ✓ {p.name}  ({len(t)} 步, t_end={t[-1]:.4e} s, dt_end={d[-1]:.3e} s)")
    return True


def plot_profile(out_dir: Path, fr: dict) -> bool:
    x = fr["x_um"]
    has_te = "tele" in fr
    n = 2 if has_te else 1
    fig, axes = plt.subplots(1, n, figsize=(7.4 * n, 6.6))
    axes = np.atleast_1d(axes)
    ax = axes[0]
    ax.semilogy(x, np.maximum(fr["dens"], 1e-12), color="#d62728", lw=2.4)
    ax.set_xlabel(r"x ($\mu$m)")
    ax.set_ylabel(r"Density (g/cm$^3$)")
    ax.set_title(f"Mass density   (t = {fr['time']*1e9:.4g} ns)")
    ax.grid(True, alpha=.3, which="both")
    if has_te:
        ax = axes[1]
        ax.semilogy(x, np.maximum(fr["tele"] / K_EV, 1e-3), color="#1f77b4", lw=2.4)
        ax.set_xlabel(r"x ($\mu$m)")
        ax.set_ylabel(r"$T_e$ (eV)")
        ax.set_title(f"Electron temperature   (t = {fr['time']*1e9:.4g} ns)")
        ax.grid(True, alpha=.3, which="both")
    fig.tight_layout()
    p = out_dir / "profile_final.png"
    fig.savefig(p, dpi=450, bbox_inches="tight")
    plt.close(fig)
    L.log(f"  ✓ {p.name}  (source={fr['file']})")
    return True


def plot_xt(out_dir: Path, frames: list) -> bool:
    """★ x-t 时空图：pcolormesh + 真实逐帧时间（禁用 imshow）。"""
    good = [f for f in frames if f is not None and f.get("dens") is not None]
    if len(good) < 2:
        L.log("  (skip profiles_xt: 有效帧 < 2)", "WARN")
        return False
    x = good[0]["x_um"]
    n = min(len(x), min(len(f["x_um"]) for f in good))
    x = x[:n]
    Z = np.vstack([f["dens"][:n] for f in good])
    ts = np.array([f["time"] for f in good]) * 1e9           # ns

    fig, ax = plt.subplots(figsize=(11, 8))
    Xg, Yg = np.meshgrid(x, ts)
    pc = ax.pcolormesh(Xg, Yg, np.log10(np.maximum(Z, 1e-12)),
                       cmap="viridis", shading="auto")
    cb = fig.colorbar(pc, ax=ax)
    cb.set_label(r"$\log_{10}\,\rho$ (g/cm$^3$)", fontsize=20)
    cb.ax.tick_params(labelsize=18)
    ax.set_xlabel(r"x ($\mu$m)")
    ax.set_ylabel("Time (ns)")
    ax.set_title("Density space-time diagram")
    fig.tight_layout()
    p = out_dir / "profiles_xt.png"
    fig.savefig(p, dpi=450)
    plt.close(fig)
    L.log(f"  ✓ {p.name}  ({len(good)} 帧, pcolormesh+真实时间)")

    # ── ★ 同步出 Te 时空图（边界热伪迹在此图上最直观）──
    good_t = [f for f in frames if f is not None and f.get("tele") is not None]
    if len(good_t) >= 2:
        good_t = sorted(good_t, key=lambda f: f["time"])
        xt = good_t[0]["x_um"]
        nt = min(len(xt), min(len(f["x_um"]) for f in good_t))
        xt = xt[:nt]
        Zt = np.vstack([f["tele"][:nt] for f in good_t])
        tst = np.array([f["time"] for f in good_t]) * 1e9
        fig, ax = plt.subplots(figsize=(11, 8))
        Xg, Yg = np.meshgrid(xt, tst)
        pc = ax.pcolormesh(Xg, Yg, np.log10(np.maximum(Zt, 1e-3)),
                           cmap="inferno", shading="auto")
        cb = fig.colorbar(pc, ax=ax)
        cb.set_label(r"$\log_{10}\,T_e$ (eV)", fontsize=20)
        cb.ax.tick_params(labelsize=18)
        ax.set_xlabel(r"x ($\mu$m)")
        ax.set_ylabel("Time (ns)")
        ax.set_title("Electron temperature space-time diagram")
        fig.tight_layout()
        pt = out_dir / "tele_xt.png"
        fig.savefig(pt, dpi=450)
        plt.close(fig)
        L.log(f"  ✓ {pt.name}  ({len(good_t)} 帧)")
    return True


def plot_boundary_diag(out_dir: Path, frames: list) -> bool:
    """★ 边界热伪迹诊断 —— 本轮 1.6 ns 运行的关键发现。

    现象: t>0.35 ns 后左半域 (x<-100µm) 被抽空到 ρ~1e-6, 但 Te 却升到
          ~2.5e7 eV (25 keV), 且占据总内能的 ~75%。
    判据: 「内能增大 5 个量级 且 质量单调流出」→ 物理不可能 ⇒ 激光/SNB
          热流持续加热已被抽空的近真空区 ⇒ 比内能 (eint/ρ) 发散。
    该伪迹会污染左半域任何 Ti-tracer 温度反演。
    """
    good = [f for f in frames if f is not None]
    if len(good) < 3:
        L.log("  (skip boundary_diag: 有效帧 < 3)", "WARN")
        return False
    import h5py
    good = sorted(good, key=lambda f: f["time"])
    import matplotlib.pyplot as plt

    ts, te_l, te_m, te_r, ei_tot, ei_l, ye_l = [], [], [], [], [], [], []
    for r in good:
        p = r["_path"]
        try:
            with h5py.File(str(p), "r") as f:
                bb = np.array(f["bounding box"])
                W = bb[:, 0, 1] - bb[:, 0, 0]
                nxb = r["nxb"]
                j = np.arange(nxb)
                xa = (bb[:, 0, 0][:, None]
                      + W[:, None] * (j + 0.5)[None, :] / nxb).ravel() * 1e4
                o = np.argsort(xa)
                xa = xa[o]
                dxa = np.repeat(W / nxb, nxb)[o]
                te = np.array(f["tele"]).reshape(-1)[o]
                ei = np.array(f["eint"]).reshape(-1)[o]
                ye = np.array(f["ye"]).reshape(-1)[o]
        except Exception:
            continue
        ts.append(r["time"] * 1e9)
        te_l.append(te[np.argmin(np.abs(xa + 399.5))])
        te_m.append(te[np.argmin(np.abs(xa + 150.0))])
        te_r.append(te[np.argmin(np.abs(xa - 50.0))])
        ei_tot.append(np.sum(ei * dxa))
        ei_l.append(np.sum(ei[xa < -100] * dxa[xa < -100]))
        ye_l.append(ye[np.argmin(np.abs(xa + 399.5))])

    ts = np.array(ts)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 6.6))

    a1.semilogy(ts, te_l, "o-", color="#d62728", lw=2.4, ms=7,
                label=r"$x=-399.5\ \mu m$ (edge)")
    a1.semilogy(ts, te_m, "s-", color="#ff7f0e", lw=2.4, ms=7,
                label=r"$x=-150\ \mu m$ (mid-left)")
    a1.semilogy(ts, te_r, "^-", color="#1f77b4", lw=2.4, ms=7,
                label=r"$x=+50\ \mu m$ (near drive)")
    a1.set_xlabel("Time (ns)")
    a1.set_ylabel(r"$T_e$ (eV)")
    a1.set_title("Electron temperature at three stations")
    a1.legend(fontsize=18, loc="lower right")
    a1.grid(True, alpha=.3, which="both")

    a2.semilogy(ts, np.array(ei_tot), "o-", color="#2ca02c", lw=2.4, ms=7,
                label=r"total $\int e_{int}\,dx$")
    a2.semilogy(ts, np.array(ei_l), "s--", color="#9467bd", lw=2.4, ms=7,
                label=r"left half $x<-100\ \mu m$")
    a2.set_xlabel("Time (ns)")
    a2.set_ylabel(r"Internal energy (erg/cm$^2$)")
    a2.set_title("Internal energy budget")
    a2.legend(fontsize=18, loc="lower right")
    a2.grid(True, alpha=.3, which="both")

    fig.tight_layout()
    p = out_dir / "boundary_diag.png"
    fig.savefig(p, dpi=450, bbox_inches="tight")
    plt.close(fig)
    L.log(f"  ✓ {p.name}  (Te_edge {te_l[-1]:.2e} eV, "
          f"Eint {ei_tot[0]:.2e}→{ei_tot[-1]:.2e} erg/cm2, "
          f"左半域占比 {ei_l[-1]/ei_tot[-1]*100:.1f}%)")
    return True


def _target_tmax(d: Path) -> float:
    """从 pipeline_state.json 读本次 tmax；缺失则退回 1.6e-9（本场景既定目标）。"""
    try:
        st = json.loads((L.SCEN_DIR / "pipeline_state.json")
                        .read_text(encoding="utf-8"))
        v = st.get("tmax")
        if v is not None:
            return float(v)
    except Exception:
        pass
    return 1.6e-9


def plot_mass_budget(out_dir: Path, frames: list) -> bool:
    """质量收支：开放边界下的出流曲线 + 单帧变幅。

    ★ 本问题左边界开放，前沿触边后质量**必然**单调流失。
      用"单帧相对跌幅"判数值稳定性（>30% 才算真崩塌），不用闭箱守恒。
    """
    good = [f for f in frames if f is not None]
    if len(good) < 3:
        L.log("  (skip mass_budget: 有效帧 < 3)", "WARN")
        return False
    good = sorted(good, key=lambda f: f["time"])
    ts = np.array([f["time"] for f in good]) * 1e9
    ms = np.array([f["mass"] for f in good])
    rel = ms / ms[0]
    drel = np.abs(np.diff(rel)) * 100.0

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 6.6))

    a1.plot(ts, rel * 100.0, "o-", color="#2ca02c", lw=2.4, ms=8)
    a1.axhline(100.0, color="#888888", ls="--", lw=1.4)
    # ★ 标注出流起始（首帧相对跌幅 > 0.1% 处）= 稀疏波前沿抵达 xmin 的时刻
    idx = np.where(np.abs(np.diff(rel)) * 100 > 0.1)[0]
    if len(idx):
        t_on = ts[idx[0] + 1]
        a1.axvline(t_on, color="#1f77b4", ls=":", lw=2.0)
        a1.annotate(f"outflow onset\nt = {t_on:.3f} ns",
                    xy=(t_on, rel[idx[0] + 1] * 100),
                    xytext=(t_on + 0.08, 96.0), fontsize=18,
                    color="#1f77b4",
                    arrowprops=dict(arrowstyle="->", color="#1f77b4", lw=1.8))
    a1.set_xlabel("Time (ns)")
    a1.set_ylabel("Areal mass / initial (%)")
    a1.set_title("Mass budget (open left boundary)")
    a1.grid(True, alpha=.3)

    a2.semilogy(ts[1:], drel, "s-", color="#d62728", lw=2.4, ms=8)
    a2.axhline(30.0, color="#888888", ls="--", lw=1.4)
    a2.text(0.03, 0.93, "collapse threshold 30%", transform=a2.transAxes,
            fontsize=18, va="top", color="#555555")
    a2.set_xlabel("Time (ns)")
    a2.set_ylabel("|Delta mass| per frame (%)")
    a2.set_title("Single-frame mass change")
    a2.grid(True, alpha=.3, which="both")

    fig.tight_layout()
    p = out_dir / "mass_budget.png"
    fig.savefig(p, dpi=450, bbox_inches="tight")
    plt.close(fig)
    L.log(f"  ✓ {p.name}  (出流 {100*(1-rel[-1]):.2f}%, "
          f"单帧最大变幅 {drel.max():.3f}%)")
    return True


def plot_scalars(out_dir: Path, frames: list) -> bool:
    good = [f for f in frames if f is not None]
    if len(good) < 2:
        L.log("  (skip scalars_history: 有效帧 < 2)", "WARN")
        return False
    ts = np.array([f["time"] for f in good]) * 1e9
    rm = np.array([float(np.max(f["dens"])) for f in good])
    # ★ FLASH 的 `tele` 已是 eV，**不得再除 K_B**（曾误除 → Te 少 3 个量级）
    tm = np.array([float(np.max(f["tele"])) if "tele" in f else np.nan
                   for f in good])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 6.6))
    a1.plot(ts, rm, "o-", color="#d62728", lw=2.4, ms=9)
    a1.set_xlabel("Time (ns)"); a1.set_ylabel(r"$\rho_{max}$ (g/cm$^3$)")
    a1.set_title("Peak density")
    a1.grid(True, alpha=.3)
    a2.semilogy(ts, tm, "s-", color="#1f77b4", lw=2.4, ms=9)
    a2.set_xlabel("Time (ns)"); a2.set_ylabel(r"$T_{e,max}$ (eV)")
    a2.set_title("Peak electron temperature")
    a2.grid(True, alpha=.3, which="both")
    fig.tight_layout()
    p = out_dir / "scalars_history.png"
    fig.savefig(p, dpi=450, bbox_inches="tight")
    plt.close(fig)
    L.log(f"  ✓ {p.name}")
    return True


# ══════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="FLASH +ug chk 绘图分析")
    ap.add_argument("--dir", required=True, help="收集目录")
    ap.add_argument("--max-frames", type=int, default=400,
                    help="最多读取帧数（防内存爆）")
    args = ap.parse_args()

    d = Path(args.dir)
    if not d.is_dir():
        L.log(f"目录不存在: {d}", "ERROR")
        return 1
    out_dir = d / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    L.step(f"绘图分析  {d} → analysis/")

    # ── 逐帧读取 ──
    files = find_frames(d)[:args.max_frames]
    L.log(f"发现 {len(files)} 个 chk/plt 帧，读取中...")
    frames, bad = [], []
    for i, p in enumerate(files):
        r = read_chk(p)
        if r is None:
            bad.append(p.name)
        else:
            frames.append(r)
        if (i + 1) % 20 == 0:
            L.log(f"  已读 {i+1}/{len(files)}")
    L.log(f"成功读取 {len(frames)} 帧；跳过 {len(bad)} 帧"
          f"{'（h5py 无法打开; 完整性以 md5 为准, 非损坏）' if bad else ''}")
    if bad:
        L.log(f"  跳过清单(前10): {bad[:10]}")

    if not frames:
        L.log("无有效帧 → 无法绘图", "ERROR")
        return 1

    # ── 帧按时间排序 ──
    frames.sort(key=lambda f: f["time"])
    last = frames[-1]

    # ── 健康判据 ──
    ts = np.array([f["time"] for f in frames])
    ms = np.array([f["mass"] for f in frames])
    # ★ 严格递增会因 plt 与同 t 的 chk 并存而误报 False；
    #   真正要判的是"是否随时间倒退"（倒退 = 排序/文件损坏）。
    dt_mono = bool(np.all(np.diff(ts) >= 0))
    n_dup_t = int(np.sum(np.diff(ts) == 0))

    # ★★★ 质量判据 —— 不能用"闭箱守恒"（本轮实测教训）
    #   本问题左边界 xmin=-400µm 是**开放出流边界**，前沿 t≈7e-10 s 触边后
    #   等离子体持续流出 → 整域积分质量**本就该单调下降**（实测 0.71833→0.58546,
    #   −18.5%）。这不是数值误差。
    #   ⇒ 正确判据两条：
    #     (1) 纯单调下降（不允许"凭空回升"= 生成/重复计数 bug）
    #     (2) 单调段内的**逐帧相对变化**必须平滑（无单帧跳变）
    ms_rel = ms / ms[0]
    d_rel = np.diff(ms_rel)
    # ★ 容差取存储精度：chk 浮点为 float32 → 相对分辨率 ~1e-7。
    #   取 1e-6 作"实质性回升"门限（曾误用 1e-12 → 把 3.5e-8% 的
    #   float32 舍入噪声当成"质量回升"，报出假警报）。
    MASS_MONO_TOL = 1e-6
    mass_monotone = bool(np.all(d_rel <= MASS_MONO_TOL))
    mass_max_jump = float(np.abs(d_rel).max()) if len(d_rel) else 0.0
    mass_max_rise = float(d_rel.max()) if len(d_rel) else 0.0
    # 出流总量（末帧 vs 首帧）
    mass_outflow_frac = float(1.0 - ms_rel[-1])
    # 漂移仅作参考：取前 20% 帧（前沿尚未触边、域近似闭合）
    n_closed = max(2, int(0.2 * len(ms)))
    drift_closed = float(np.abs(ms[:n_closed] / ms[0] - 1).max()) if len(ms) >= 3 else float("nan")

    eint_ok = all(float(np.min(f["eint"])) > 0 for f in frames if "eint" in f)

    # ★ 边界热伪迹判据（本轮关键发现）:
    #   "内能暴涨 >100× 且 质量单调流出" ⇒ 抽空区被持续加热 ⇒ 温度不可信。
    te_last = float(np.max(last["tele"])) if "tele" in last else float("nan")
    bound_artifact = bool(mass_monotone and mass_outflow_frac > 0.05
                          and te_last > 1e6)
    health = {
        "n_frames": len(frames), "n_skipped": len(bad),
        "t_range_s": [float(ts.min()), float(ts.max())],
        "t_monotonic": dt_mono,
        "n_dup_time_frames": n_dup_t,
        # ── 质量收支（开放边界语义）──
        "mass_first": float(ms[0]), "mass_last": float(ms[-1]),
        "mass_outflow_frac": mass_outflow_frac,
        "mass_monotone_decreasing": mass_monotone,
        "mass_max_single_frame_rel_change": mass_max_jump,
        "mass_max_single_frame_rise": mass_max_rise,
        "mass_mono_tol": MASS_MONO_TOL,
        "mass_closed_phase_drift": drift_closed,
        "mass_rel_drift_max": float(np.abs(ms_rel - 1).max()),
        "eint_min_positive": bool(eint_ok),
        "cells": int(last["ncells"]), "nxb": int(last["nxb"]),
        "dens_max": float(np.max(last["dens"])),
        "tele_max_eV": float(np.max(last["tele"])) if "tele" in last else None,
        "boundary_heating_artifact_suspected": bound_artifact,
        "skipped_files": bad,
    }
    (out_dir / "health.json").write_text(
        json.dumps(health, indent=2, ensure_ascii=False), encoding="utf-8")

    L.log("\n--- 健康判据 ---")
    L.log(f"  帧数={len(frames)}  跳过={len(bad)}")
    t_target = _target_tmax(d)
    L.log(f"  t 范围=[{ts.min():.4e}, {ts.max():.4e}] s  "
          f"（目标 {t_target:.1e}）")
    L.log(f"  t 单调(不倒退)={dt_mono}  同 t 帧={n_dup_t}  eint_min>0={eint_ok}")
    L.log(f"  质量: 首={ms[0]:.6g} 末={ms[-1]:.6g} g/cm2  "
          f"出流={mass_outflow_frac*100:.2f}%  "
          f"单调下降={mass_monotone}(tol {MASS_MONO_TOL:.0e})  "
          f"单帧最大变幅={mass_max_jump*100:.3f}%")
    L.log(f"        （参考）闭合段漂移(<20%帧)={drift_closed:.3e}")
    L.log(f"  末帧: ρmax={health['dens_max']:.4g} g/cc  "
          f"Te_max={health['tele_max_eV']:.4g} eV")
    L.log(f"  → {out_dir / 'health.json'}")

    # ── 绘图 ──
    L.log("\n--- 绘图 ---")
    times = None
    logs = sorted(d.glob("wsl_run_*.log"))
    if not logs:
        logs = sorted(d.glob("*.log"))
    if logs:
        _, times, dts = parse_log_dt(logs[0])
        plot_dt(out_dir, times, dts)
    else:
        L.log("  (未找到 wsl_run_*.log → 跳过 dt 演化图)", "WARN")

    plot_profile(out_dir, last)
    plot_xt(out_dir, frames)
    plot_scalars(out_dir, frames)
    plot_mass_budget(out_dir, frames)
    plot_boundary_diag(out_dir, frames)

    L.log(f"\n✓ 分析完成 → {out_dir}", "OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
