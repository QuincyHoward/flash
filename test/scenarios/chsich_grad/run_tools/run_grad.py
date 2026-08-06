"""
run_grad.py — GradDensSandwich HE-CH-Si-CH-HE FLASH 仿真运行 (双击可执行)

渐变密度 CH 层 + 超高斯脉冲 (order=4, 1ns FWHM, 5e14 W/cm²)

CH 密度梯度控制:
  ch_posx_1 / ch_dens_1 — 控制点 1 (位置, 密度)
  ch_posx_2 / ch_dens_2 — 控制点 2 (位置, 密度)
  两点间线性插值, 对称分布

用法:
  python run_grad.py                          # 默认运行
  python run_grad.py --no-simulate            # 仅生成输入文件
  python run_grad.py --ch-pos1 1e-4 --ch-dens1 0.01  # 自定义梯度
"""

from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap: find flash project root
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "__init__.py").exists() and (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT.parent
for _p in [str(_PARENT), str(_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np


# ============================================================
#  主运行函数
# ============================================================

def run_grad(
    sim_rhoPoly: float = 0.15,
    sim_rhoTarg: float = 2.33,
    sim_targHeight: float = 0.15e-4,
    # CH 密度梯度: 激活对数 (0=无梯度, N=使用前N组)
    ch_num: int = 0,
    # CH 密度梯度控制点 — 最多 10 组
    ch_posx_1: float = 0.0,  ch_dens_1: float = 0.0,
    ch_posx_2: float = 0.0,  ch_dens_2: float = 0.0,
    ch_posx_3: float = 0.0,  ch_dens_3: float = 0.0,
    ch_posx_4: float = 0.0,  ch_dens_4: float = 0.0,
    ch_posx_5: float = 0.0,  ch_dens_5: float = 0.0,
    ch_posx_6: float = 0.0,  ch_dens_6: float = 0.0,
    ch_posx_7: float = 0.0,  ch_dens_7: float = 0.0,
    ch_posx_8: float = 0.0,  ch_dens_8: float = 0.0,
    ch_posx_9: float = 0.0,  ch_dens_9: float = 0.0,
    ch_posx_10: float = 0.0, ch_dens_10: float = 0.0,
    # 超高斯脉冲参数
    pulse_peak: float = 5e14,
    pulse_fwhm: float = 1.0e-9,
    pulse_order: int = 4,
    pulse_npts: int = 120,
    simulate: bool = True,
    flash_timeout: int = 900,
    force_recompile: bool = True,  # 默认强制 setup+make
) -> dict:
    """运行 GradDensSandwich HE-CH-Si-CH-HE FLASH 仿真。

    Args:
        sim_rhoPoly: CH 回退密度 (g/cm³)
        sim_polyHeight: CH 半厚 (cm)
        sim_rhoTarg: Si 密度 (g/cm³)
        sim_targHeight: Si 半厚 (cm)
        ch_posx_1, ch_dens_1: CH 密度梯度控制点 1 (cm, g/cm³)
        ch_posx_2, ch_dens_2: CH 密度梯度控制点 2 (cm, g/cm³)
        pulse_peak: 激光峰值功率 (W/cm²)
        pulse_fwhm: 超高斯 FWHM (s)
        pulse_order: 超高斯阶次
        pulse_npts: 脉冲离散点数
        simulate: True=运行 FLASH, False=仅生成输入文件
        flash_timeout: WSL FLASH 超时 (秒)

    Returns:
        dict: {run_dir, result_h5, plots, simulated, success}
    """
    from flash.scenarios.registry import get_scenario
    from flash.scenarios.simulator import FlashSimulatorEngine
    from flash.scenarios.collision_compression.grad_dens_sandwich import (
        make_super_gaussian_pulse,
    )

    sc = get_scenario("grad_dens_sandwich")
    engine = FlashSimulatorEngine(sc, verbose=True)

    # ── 生成超高斯脉冲 ──
    pulse_data = make_super_gaussian_pulse(
        peak_power=pulse_peak,
        center_time=pulse_fwhm * 0.6,  # 中心在 0.6 * FWHM
        fwhm=pulse_fwhm,
        order=pulse_order,
        n_points=pulse_npts,
        time_start=0.0,
        time_end=pulse_fwhm * 1.2,
    )
    pulse_times = [t for t, _ in pulse_data]
    pulse_powers = [p for _, p in pulse_data]
    sim_tmax = max(pulse_times) + 0.2e-9

    params_override = {
        "sim_rhoPoly": sim_rhoPoly,
        "sim_rhoTarg": sim_rhoTarg,
        "sim_targHeight": sim_targHeight,
        # CH 密度梯度
        "ch_num": ch_num,
        "ch_posx_1": ch_posx_1,   "ch_dens_1": ch_dens_1,
        "ch_posx_2": ch_posx_2,   "ch_dens_2": ch_dens_2,
        "ch_posx_3": ch_posx_3,   "ch_dens_3": ch_dens_3,
        "ch_posx_4": ch_posx_4,   "ch_dens_4": ch_dens_4,
        "ch_posx_5": ch_posx_5,   "ch_dens_5": ch_dens_5,
        "ch_posx_6": ch_posx_6,   "ch_dens_6": ch_dens_6,
        "ch_posx_7": ch_posx_7,   "ch_dens_7": ch_dens_7,
        "ch_posx_8": ch_posx_8,   "ch_dens_8": ch_dens_8,
        "ch_posx_9": ch_posx_9,   "ch_dens_9": ch_dens_9,
        "ch_posx_10": ch_posx_10, "ch_dens_10": ch_dens_10,
        "laser_times": pulse_times,
        "laser_powers": pulse_powers,
        "tmax": sim_tmax,
        "output_t_max": sim_tmax,
    }

    # Collect gradient pairs based on ch_num
    _all_pairs = [(ch_posx_1, ch_dens_1), (ch_posx_2, ch_dens_2),
                  (ch_posx_3, ch_dens_3), (ch_posx_4, ch_dens_4),
                  (ch_posx_5, ch_dens_5), (ch_posx_6, ch_dens_6),
                  (ch_posx_7, ch_dens_7), (ch_posx_8, ch_dens_8),
                  (ch_posx_9, ch_dens_9), (ch_posx_10, ch_dens_10)]
    _active_pairs = _all_pairs[:max(0, ch_num)]
    _poly_height_span = abs(_active_pairs[-1][0] - _active_pairs[0][0]) if len(_active_pairs) >= 2 else 0.0

    print(f"\n{'='*70}")
    print(f"  GradDensSandwich — HE-CH-Si-CH-HE 渐变密度 CH")
    print(f"  CH foam: ch_num={ch_num}, {_poly_height_span*1e4:.0f} um span "
          f"(= abs(ch_posx_{ch_num} - ch_posx_1))")
    print(f"  Active gradient points: {len(_active_pairs)}")
    for _idx, (p, d) in enumerate(_active_pairs, 1):
        print(f"    point {_idx}:  |x| = {p*1e4:.2f} um  →  rho = {d:.2e} g/cm³")
    print(f"  Si: {sim_targHeight*1e4:.2f} um, {sim_rhoTarg:.2e} g/cm³")
    print(f"  Pulse: super-Gaussian (order={pulse_order}, FWHM={pulse_fwhm*1e9:.1f}ns, "
          f"peak={pulse_peak:.1e} W/cm²)")
    print(f"  Pulse segments: {len(pulse_times)}")
    print(f"  tmax:  {sim_tmax*1e9:.1f} ns  simulate={'ON' if simulate else 'OFF'}")
    print(f"{'='*70}\n")

    # ── 预诊断图: 仿真前写入正确 run_id 的 sim_input/ ──
    _par_content = sc.build_par(params_override)
    _pre_figs = _generate_pre_plots_from_par(_par_content)

    # 预测下一个 run_id (与 engine._next_run_id 一致)
    _runs_dir = Path(__file__).resolve().parent / ("runs_" + sc.name.split("_sandwich")[0] + "_sandwich")
    _runs_dir.mkdir(parents=True, exist_ok=True)
    _existing_ids = []
    for _d in _runs_dir.iterdir():
        if _d.is_dir() and _d.name.isdigit() and len(_d.name) == 6:
            _existing_ids.append(int(_d.name))
    _next_rid = f"{max(_existing_ids) + 1 if _existing_ids else 1:06d}"

    # 写入 sim_input/ (创建 run_dir 会使 _next_run_id 递增, 因此用固定 run_id 传给引擎)
    _sim_in_dir = _runs_dir / _next_rid / "sim_input"
    _sim_in_dir.mkdir(parents=True, exist_ok=True)
    for _fname, _fdata in _pre_figs.items():
        (_sim_in_dir / _fname).write_bytes(_fdata)
    print(f"  ✅ pre-sim plots → {_sim_in_dir}/")

    # 抑制引擎的旧版预诊断图生成
    import flash.scenarios.simulator as _sim_mod
    _orig_pre_diag = _sim_mod._generate_pre_diagnosis
    _sim_mod._generate_pre_diagnosis = lambda *a, **kw: None

    out = engine.run(
        params_override=params_override,
        run_flash=simulate,
        keep_flash_raw=True,
        flash_timeout=flash_timeout if simulate else 1,
        run_id=_next_rid,
        force_recompile=force_recompile,
    )
    run_dir = Path(out.run_dir)

    # 恢复引擎预诊断函数, 运行后覆盖确保正确
    _sim_mod._generate_pre_diagnosis = _orig_pre_diag
    for _fname, _fdata in _pre_figs.items():
        (run_dir / "sim_input" / _fname).write_bytes(_fdata)

    if not simulate:
        sim_input = run_dir / "sim_input"
        db_in = run_dir / "database" / "flash_in"
        print(f"\n  ⏭  仿真关闭, 仅生成输入文件:")
        print(f"     .par:     {(sim_input / (sc.sim_name + '.par'))}")
        print(f"     .sh:      {sim_input / 'run_flash.sh'}")
        print(f"     params:   {db_in / 'input_params.json'}")
        return {"run_dir": run_dir, "result_h5": None,
                "plots": {}, "simulated": False, "success": True}

    if not out.success:
        print(f"  ❌ FLASH 运行失败")
        return {"run_dir": run_dir, "result_h5": None,
                "simulated": True, "success": False}

    print(f"  ✅ 运行成功")
    print(f"  ✅ result.h5: {out.result_h5_path}")
    print(f"  ✅ chk: {out.n_chk} 文件")

    plots = _generate_post_plots(run_dir, out)

    print(f"\n  🎉 完成 — run_dir: {run_dir}")
    return {
        "run_dir": run_dir,
        "result_h5": Path(out.result_h5_path) if out.result_h5_path else None,
        "plots": plots,
        "simulated": True,
        "success": True,
    }


# ============================================================
#  预诊断图 — 初始密度 + 激光脉冲
# ============================================================

def _generate_pre_plots_from_par(par_content: str) -> dict:
    """从 .par 文件内容字符串解析参数, 生成预诊断图, 返回 {filename: bytes}.

    在仿真前调用, 不依赖磁盘文件, 输出为内存字节流。
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # ── PPT-friendly plot style (fonts >= 18, English only) ──
    try:
        from output_processors.plotter.plot_style import apply_plot_style
        apply_plot_style()
    except ImportError:
        pass
    from io import BytesIO

    plt.rcParams.update({"font.size": 18, "axes.labelsize": 20,
                         "axes.titlesize": 22, "legend.fontsize": 18,
                         "lines.linewidth": 2.5, "savefig.dpi": 200})

    # ── Parse par content string ──
    par = {}
    for line in par_content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip()
        try:
            if v.lower() in (".true.", ".false."):
                par[k] = v.lower() == ".true."
            else:
                par[k] = float(v)
        except ValueError:
            par[k] = v

    # ── Extract params from par ──
    xmin = float(par.get("xmin", -0.045))
    xmax = float(par.get("xmax", 0.045))
    half = (xmax - xmin) / 2
    targ_h = float(par.get("sim_targHeight", 0.15e-4))
    rho_targ = float(par.get("sim_rhoTarg", 2.33))
    rho_cham = float(par.get("sim_rhoCham", 1e-6))
    ch_num = int(par.get("ch_num", 0))
    n_pts = 5000

    # ── Build CH gradient from par data ──
    _pos, _den = [], []
    for i in range(1, min(ch_num, 10) + 1):
        px = float(par.get(f"ch_posx_{i}", 0.0))
        pd = float(par.get(f"ch_dens_{i}", 0.0))
        _pos.append(px)
        _den.append(pd)

    def _grad_dens(ax):
        if ch_num <= 0 or not _pos:
            return None
        if ax <= _pos[0]:
            return _den[0]
        if ax >= _pos[-1]:
            return _den[-1]
        for i in range(len(_pos) - 1):
            if _pos[i] <= ax <= _pos[i+1]:
                f = (ax - _pos[i]) / (_pos[i+1] - _pos[i])
                return _den[i] + f * (_den[i+1] - _den[i])
        return _den[-1]

    poly_span = abs(_pos[-1] - _pos[0]) if len(_pos) >= 2 else 0.0

    # ── Extract laser pulse from par ──
    pulse_t, pulse_p = [], []
    n_sec = int(par.get("ed_numberOfSections_1", 0))
    for i in range(1, n_sec + 1):
        t = par.get(f"ed_time_1_{i}")
        p = par.get(f"ed_power_1_{i}")
        if t is not None and p is not None:
            pulse_t.append(float(t))
            pulse_p.append(float(p))
    peak_p = max(pulse_p) if pulse_p else 0.0

    # ── 1. initial_density.png ──
    x_full = np.linspace(-half, half, n_pts)
    dens_full = np.full_like(x_full, rho_cham)
    for i in range(len(x_full)):
        ax = abs(x_full[i])
        if ax <= targ_h:
            dens_full[i] = rho_targ
        elif ax <= poly_span:
            d = _grad_dens(ax)
            dens_full[i] = d if d is not None else 0.15

    fig, (ax_full, ax_zoom) = plt.subplots(2, 1, figsize=(14, 12), sharey=False)

    ax_full.plot(x_full * 1e4, dens_full, "k-", lw=2.5)
    ax_full.axvspan(-targ_h * 1e4, targ_h * 1e4, alpha=0.15, color="orange", label="Si target")
    ax_full.axvspan(-poly_span * 1e4, poly_span * 1e4, alpha=0.08, color="green",
                     label=f"CH gradient ({poly_span*2*1e4:.0f} um)")
    ax_full.set_ylabel("Density (g/cm³)")
    ax_full.set_title("Initial Density Distribution (He-CH-Si-CH-He, Gradient CH)", fontweight="bold")
    ax_full.legend(loc="upper right")
    ax_full.set_xlim(-half * 1e4, half * 1e4)
    ymax = max(max(dens_full) * 1.15, rho_cham * 1.5)
    ax_full.set_ylim(0, ymax)
    ax_full.grid(True, alpha=0.3)
    ax_full.tick_params(labelsize=14)
    if rho_targ > 0:
        ax_full.annotate(f"Si {rho_targ:.2f} g/cm³\n({targ_h*1e4:.2f} um)",
                         xy=(0, rho_targ), xytext=(half*0.3*1e4, rho_targ*1.05), color="orange", fontweight="bold",
                         arrowprops=dict(arrowstyle="->", color="orange", lw=1.5))

    # Lower zoom
    zoom_um = 1.0
    nz = 2000
    xz = np.linspace(-zoom_um * 1e-4, zoom_um * 1e-4, nz)
    dens_z = np.full_like(xz, rho_cham)
    for i in range(len(xz)):
        ax = abs(xz[i])
        if ax <= targ_h:
            dens_z[i] = rho_targ
        elif ax <= poly_span:
            d = _grad_dens(ax)
            dens_z[i] = d if d is not None else 0.15

    ax_zoom.plot(xz * 1e4, dens_z, "k-", lw=2.5)
    si_hz = targ_h * 1e4
    ax_zoom.axvspan(-si_hz, si_hz, alpha=0.30, color="orange")
    ax_zoom.axvline(x=0, color="orange", linestyle="--", alpha=0.7, lw=2)
    ax_zoom.axhline(y=rho_targ, xmin=0.45, xmax=0.55, color="orange",
                     linestyle=":", alpha=0.6, lw=2)
    ax_zoom.text(0, rho_targ * 0.7, f"Si {rho_targ:.2f}", color="orange", fontweight="bold",
                  ha="center", va="center",
                  bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                            edgecolor="orange", alpha=0.9))
    if poly_span > 0:
        phz = min(poly_span * 1e4, zoom_um)
        ax_zoom.axvspan(-phz, phz, alpha=0.08, color="green")
        if ch_num >= 2:
            for px_val, pd_val in zip(_pos, _den):
                pum = px_val * 1e4
                if pum <= zoom_um:
                    ax_zoom.plot(pum, pd_val, "o", color="green", ms=6, zorder=5)
                    if pd_val > 0:
                        ax_zoom.annotate(f"rho={pd_val:.3f}", (pum, pd_val),
                                          (pum + 0.15, pd_val * 1.15), color="green",
                                          arrowprops=dict(arrowstyle="->", color="green", lw=0.8))

    ax_zoom.set_xlabel("x (um)")
    ax_zoom.set_ylabel("Density (g/cm3)")
    ax_zoom.set_title(f"Center +/-{zoom_um:.0f} um Zoom", fontweight="bold")
    ax_zoom.set_xlim(-zoom_um, zoom_um)
    ax_zoom.set_ylim(0, max(dens_z) * 1.25)
    ax_zoom.grid(True, alpha=0.3)
    ax_zoom.tick_params(labelsize=14)

    pl = (f"Pulse: {len(pulse_t)} sections, peak={peak_p:.2e} W/cm2 | "
          f"ch_num={ch_num}, CH span={poly_span*1e4:.0f} um | "
          f"params from .par file")
    fig.suptitle(pl, y=0.02, color="#444444", fontfamily="monospace")

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    buf1 = BytesIO()
    fig.savefig(buf1, format="png", bbox_inches="tight", dpi=200)
    plt.close(fig)
    _initial_bytes = buf1.getvalue()

    # ── 2. laser_pulse.png ──
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(np.array(pulse_t) * 1e12, np.array(pulse_p) / 1e14, "r-", lw=3.0)
    ax.set_xlabel("Time (ps)")
    ax.set_ylabel("Power (x1e14 W/cm2)")
    ax.set_title("Laser Pulse from .par file", fontweight="bold")
    ax.tick_params(labelsize=16)
    ax.grid(True, alpha=0.25, linestyle="--")

    ann = [
        f"  CH gradient: {ch_num} pts, span={poly_span*1e4:.0f} um",
        f"    rho range: {min(_den):.4f} ~ {max(_den):.4f} g/cm3" if _den else "",
        f"  Si target: {targ_h*1e4:.2f} um, {rho_targ:.2f} g/cm3",
        f"  Pulse: {len(pulse_t)} sections, peak={peak_p:.2e} W/cm2",
        f"  Te init: 3500 K",
        f"  (data from .par, pre-simulation)",
    ]
    ann_text = "\n".join(l for l in ann if l)
    ax.text(0.97, 0.97, ann_text, transform=ax.transAxes, color="#333333",
            verticalalignment="top", horizontalalignment="right",
            fontfamily="monospace",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                      edgecolor="gray", alpha=0.85))

    buf2 = BytesIO()
    fig.savefig(buf2, format="png", dpi=200)
    plt.close(fig)
    _laser_bytes = buf2.getvalue()

    print(f"  ✅ pre-sim plots generated (init_dens={len(_initial_bytes)}B, laser={len(_laser_bytes)}B)")
    return {
        "initial_density.png": _initial_bytes,
        "laser_pulse.png": _laser_bytes,
    }


# ============================================================
#  后处理诊断图 — chsich04 风格窗口评分 + 绘图
# ============================================================

# 窗口评分参数 (chsich04 风格)
_WINDOW1_PS = 600.0    # Phase 1 窗口宽度 (ps)
_WINDOW_PS = 300.0     # Phase 2 窗口宽度 (ps)
_STEP_PS = 10.0        # 滑动步长 (ps)
_TELE_BASE_K = 1.276e6  # 110 eV → K
_NELE_BASE = 1.4e23     # nele 基线
_CV_BASE = 0.05         # CV 基线 (5%)
_MIN_PTS = 20           # 窗口最少点数


def _sliding_window_best(
    times_s: np.ndarray,
    tele: np.ndarray,
    nele: np.ndarray,
    tele_base: float = _TELE_BASE_K,
    nele_base: float = _NELE_BASE,
    cv_base: float = _CV_BASE,
) -> dict:
    """两阶段嵌套滑动窗口 (同 chsich04):
    Phase 1: 600ps 全局搜索, score = min(tele_norm, nele_norm), 最大化
    Phase 2: 在 Phase 1 范围内 300ps, score = -max(g1_raw, g2_raw), 最小化 g0
    Phase 2 窗口严格不越出 Phase 1 边界 (min(end, best1_end)).
    """
    n_pts = len(times_s)
    if n_pts < 20:
        return {"tele_mean": 0.0, "nele_mean": 0.0, "tele_norm": 0.0, "nele_norm": 0.0,
                "cv_tele": 0.0, "cv_nele": 0.0, "w_start_ns": 0.0, "w_end_ns": 0.3,
                "txn_min": 0.0, "g1_raw": 0.0, "g2_raw": 0.0, "g0_unclipped": 0.0,
                "best_g0": float('inf'), "phase1_range_ns": (0.0, 0.0)}

    step_s = _STEP_PS * 1e-12
    win1_s = _WINDOW1_PS * 1e-12
    win2_s = _WINDOW_PS * 1e-12
    dt = times_s[-1] - times_s[0]
    min_1_pts = max(20, int(win1_s / dt * n_pts * 0.5))
    min_2_pts = max(20, int(win2_s / dt * n_pts * 0.5))

    # ── Phase 1: 600ps 基线优先搜索 (只搜索完整 600ps, 不截断) ──
    best1_score = -1.0
    best1_start = 0
    best1_end = min(n_pts, int(np.searchsorted(times_s, times_s[0] + win1_s, side="left")))

    # 找到 Phase 1 最后一个起始: start+600ps <= 数据末端
    _max_start_p1 = 0
    while _max_start_p1 < n_pts:
        if times_s[_max_start_p1] + win1_s > times_s[-1]:
            break
        _max_start_p1 += 1

    start = 0
    while start < _max_start_p1:
        t_start = times_s[start]
        t_end = t_start + win1_s
        end = int(np.searchsorted(times_s, t_end, side="left"))
        if end - start >= min_1_pts:
            tn = float(np.mean(tele[start:end])) / tele_base
            nn = float(np.mean(nele[start:end])) / nele_base
            score = min(tn, nn)
            if score > best1_score:
                best1_score = score
                best1_start, best1_end = start, end
        next_t = times_s[start] + step_s
        next_idx = int(np.searchsorted(times_s, next_t, side="left"))
        start = next_idx if next_idx > start else start + 1

    # Phase 1 的连续时间范围 (用于显示)
    _p1_start_ns = float(times_s[best1_start] * 1e9)
    _p1_end_ns = _p1_start_ns + _WINDOW1_PS / 1000.0  # 连续时间, 不含舍入

    # ── Phase 2: 在 Phase 1 范围内 300ps 约束精炼 (只搜索完整 300ps, 不截断) ──
    best2_g0 = float('inf')
    result = {
        "tele_mean": 0.0, "nele_mean": 0.0,
        "tele_norm": 0.0, "nele_norm": 0.0,
        "cv_tele": 0.0, "cv_nele": 0.0,
        "w_start_ns": 0.0, "w_end_ns": _WINDOW_PS / 1000.0,
        "txn_min": 0.0,
        "g1_raw": 0.0, "g2_raw": 0.0, "g0_unclipped": 0.0,
        "best_g0": float('inf'),
        "phase1_range_ns": (_p1_start_ns, _p1_end_ns),
    }

    # 找到 Phase 2 最后一个起始: start+300ps <= Phase1 连续末端
    _max_start_2 = best1_start
    while _max_start_2 < best1_end:
        if times_s[_max_start_2] + win2_s > _p1_end_ns * 1e-9:
            break
        _max_start_2 += 1

    start = best1_start
    while start < _max_start_2:
        t_start = times_s[start]
        t_end = t_start + win2_s
        end = int(np.searchsorted(times_s, t_end, side="left"))
        end = min(end, n_pts)
        if end - start >= min_2_pts:
            tw = tele[start:end]
            nw = nele[start:end]
            tm = float(np.mean(tw))
            nm = float(np.mean(nw))
            tn = tm / tele_base if tele_base > 0 else 0.0
            nn = nm / nele_base if nele_base > 0 else 0.0
            cv_t = float(np.std(tw.astype(np.float64)) / np.mean(tw)) if np.mean(tw) != 0 else 0.0
            cv_n = float(np.std(nw.astype(np.float64)) / np.mean(nw)) if np.mean(nw) != 0 else 0.0
            g1_raw = 1.0 - min(tn, nn)
            g2_raw = max(cv_t, cv_n) / cv_base - 1.0
            g0 = max(g1_raw, g2_raw)
            if g0 < best2_g0:
                best2_g0 = g0
                _w2_start_ns = float(times_s[start] * 1e9)
                result = {
                    "tele_mean": tm, "nele_mean": nm,
                    "tele_norm": tn, "nele_norm": nn,
                    "cv_tele": cv_t, "cv_nele": cv_n,
                    "w_start_ns": _w2_start_ns,
                    "w_end_ns": _w2_start_ns + _WINDOW_PS / 1000.0,
                    "txn_min": min(tn, nn),
                    "g1_raw": g1_raw, "g2_raw": g2_raw,
                    "g0_unclipped": g0, "best_g0": best2_g0,
                    "phase1_range_ns": result["phase1_range_ns"],
                }
        next_t = times_s[start] + step_s
        next_idx = int(np.searchsorted(times_s, next_t, side="left"))
        start = next_idx if next_idx > start else start + 1

    return result


def _plot_time_series(
    times_ns: np.ndarray,
    txn: np.ndarray,
    tele_K: np.ndarray,
    nele: np.ndarray,
    dens: np.ndarray,
    win: dict,
    save_path: str,
) -> str:
    """chsich04 风格 4 面板时序图: txn / tele(eV) / nele / dens"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    tele_eV = tele_K / 11604.5  # K → eV

    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
    colors = ["#555555", "#D85A30", "#378ADD", "#639922"]
    labels = ["TXN (tele × nele)", "Tele (eV)", "Nele (cm⁻³)", "Dens (g/cm³)"]
    data = [txn, tele_eV, nele, dens]
    units = ["", "eV", "cm⁻³", "g/cm³"]

    for idx, (ax, d, c, lb, u) in enumerate(zip(axes, data, colors, labels, units)):
        ax.plot(times_ns, d, color=c, lw=2.0)
        # Phase 1 (600ps) highlight
        p1_start, p1_end = win["phase1_range_ns"]
        ax.axvspan(p1_start, p1_end, alpha=0.06, color="blue", label="Phase 1 (600ps)")
        ax.axvline(x=p1_start, color="blue", ls=":", lw=0.8, alpha=0.4)
        ax.axvline(x=p1_end, color="blue", ls=":", lw=0.8, alpha=0.4)
        # Phase 2 (300ps) highlight
        ax.axvspan(win["w_start_ns"], win["w_end_ns"], alpha=0.12,
                    color="green", label="Best window (300ps)")
        ax.axvline(x=win["w_start_ns"], color="green", ls="--", lw=1.2, alpha=0.5)
        ax.axvline(x=win["w_end_ns"], color="green", ls="--", lw=1.2, alpha=0.5)

        # Info box in top-right
        if idx == 0:
            info = f"txn_min={win['txn_min']:.4f}\nG[0]'={win['g0_unclipped']:.4f}"
        elif idx == 1:
            info = f"mean={win['tele_mean']/11604.5:.1f} eV\nCV={win['cv_tele']:.4f}"
        elif idx == 2:
            info = f"mean={win['nele_mean']:.2e}\nCV={win['cv_nele']:.4f}"
        else:
            dw = dens[:50]
            info = f"CH ρ≈{float(np.mean(dw[dw>0])):.3f} g/cm³" if np.any(dw > 0) else ""

        ax.text(0.97, 0.95, info, transform=ax.transAxes,
                verticalalignment="top", horizontalalignment="right",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="wheat",
                          edgecolor="gray", alpha=0.7))

        ax.set_ylabel(u)
        ax.tick_params(labelsize=12)
        ax.grid(True, alpha=0.2)

    axes[0].set_title(f"TXN / Tele / Nele / Dens Time Series\n"
                       f"Window: {win['w_start_ns']:.2f} ~ {win['w_end_ns']:.2f} ns", fontweight="bold")
    axes[-1].set_xlabel("Time (ns)")
    plt.tight_layout()
    fig.savefig(save_path, dpi=200)
    plt.close(fig)
    return save_path


def _plot_txn_time_series(
    times_ns: np.ndarray,
    tele_K: np.ndarray,
    nele: np.ndarray,
    win: dict,
    save_path: str,
) -> str:
    """chsich04 风格双轴精修图: 左红 Tele(eV) + 右蓝 Nele(cm⁻³)"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    tele_eV = tele_K / 11604.5
    tele_base_eV = _TELE_BASE_K / 11604.5
    nele_base = _NELE_BASE

    fig, ax1 = plt.subplots(figsize=(14, 7))

    color_t = "#D85A30"
    color_n = "#378ADD"

    ax1.plot(times_ns, tele_eV, color=color_t, lw=2.5, label="Tele (eV)")
    ax1.axhline(y=tele_base_eV, color=color_t, ls="--", lw=1.5, alpha=0.6,
                 label=f"Tele base ({tele_base_eV:.1f} eV)")
    ax1.set_xlabel("Time (ns)")
    ax1.set_ylabel("Tele (eV)", color=color_t)
    ax1.tick_params(axis="y", labelcolor=color_t, labelsize=14)
    ax1.tick_params(axis="x", labelsize=14)

    ax2 = ax1.twinx()
    ax2.plot(times_ns, nele, color=color_n, lw=2.0, ls="--",
              label="Nele (cm⁻³)")
    ax2.axhline(y=nele_base, color=color_n, ls=":", lw=1.5, alpha=0.6,
                 label=f"Nele base ({nele_base:.1e} cm⁻³)")
    ax2.set_ylabel("Nele (cm⁻³)", color=color_n)
    ax2.tick_params(axis="y", labelcolor=color_n, labelsize=14)

    # Phase 1 (600ps) highlight
    p1s, p1e = win["phase1_range_ns"]
    ax1.axvspan(p1s, p1e, alpha=0.06, color="blue", label="Phase 1 (600ps)")
    ax1.axvline(x=p1s, color="blue", ls=":", lw=1.0, alpha=0.4)
    ax1.axvline(x=p1e, color="blue", ls=":", lw=1.0, alpha=0.4)
    # Phase 2 (300ps) window
    ax1.axvspan(win["w_start_ns"], win["w_end_ns"], alpha=0.10,
                 color="green", label="Best window")
    ax1.axvline(x=win["w_start_ns"], color="green", ls="--", lw=1.5, alpha=0.6)
    ax1.axvline(x=win["w_end_ns"], color="green", ls="--", lw=1.5, alpha=0.6)

    # Info box (右上角)
    g0_hard = max(0.0, win["g0_unclipped"])
    p1s, p1e = win["phase1_range_ns"]
    info_lines = (
        f"Phase 1 (600ps): [{p1s:.2f}, {p1e:.2f}] ns\n"
        f"Phase 2 (300ps): [{win['w_start_ns']:.2f}, {win['w_end_ns']:.2f}] ns\n"
        f"txn_min = {win['txn_min']:.4f}\n"
        f"Tele: {win['tele_mean']/11604.5:.1f} eV (CV={win['cv_tele']:.4f})\n"
        f"Nele: {win['nele_mean']:.2e} cm⁻³ (CV={win['cv_nele']:.4f})\n"
        f"G[0]' (unclipped) = {win['g0_unclipped']:.4f}\n"
        f"  g1_raw (baseline) = {win['g1_raw']:.4f}\n"
        f"  g2_raw (fluct.)   = {win['g2_raw']:.4f}\n"
        f"G[0] (hard) = {g0_hard:.4f}"
    )
    ax1.text(0.97, 0.97, info_lines, transform=ax1.transAxes, color="#333333", fontfamily="monospace",
             verticalalignment="top", horizontalalignment="right",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="wheat",
                       edgecolor="gray", alpha=0.80))

    # Legend combined
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", framealpha=0.85)

    ax1.set_title("Tele & Nele Evolution (Center ±1 μm)", fontweight="bold")
    ax1.grid(True, alpha=0.15)

    plt.tight_layout()
    fig.savefig(save_path, dpi=200)
    plt.close(fig)
    return save_path


def _plot_spatial(data: dict, save_path: str, win: dict):
    """Tele/Nele 空间剖面 → analysis_spatial.png (chsich04 风格)"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import cm

    x_cm = data["x_cm"]
    tele_2d = data["tele_2d"]
    nele_2d = data["nele_2d"]
    t = data["times_s"]
    times_ns = t * 1e9
    EV_PER_K = 11604.5

    center = x_cm[len(x_cm)//2]
    zoom_cm = 5e-4
    zoom_mask = np.abs(x_cm - center) <= zoom_cm
    n_ts = min(20, len(t))
    sel_idx = np.linspace(0, len(t)-1, n_ts, dtype=int)
    cmap = cm.viridis

    plt.rcParams.update({"font.size": 14, "axes.labelsize": 16,
                         "axes.titlesize": 18, "figure.dpi": 200})
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    for row, field, ylabel in [(0, tele_2d, "Tele (eV)"), (1, nele_2d, "Nele (cm-3)")]:
        for col, (xdata, title) in enumerate([(x_cm, "Full Range"), (x_cm[zoom_mask], "Center +/-5 um")]):
            ax = axes[row, col]
            for idx in sel_idx:
                color = cmap(idx / len(t))
                vals = field[idx, :] / EV_PER_K if row == 0 else field[idx, :]
                if col == 0:
                    ax.plot(xdata * 1e4, vals, color=color, lw=1, alpha=0.7)
                else:
                    zoom_vals = field[idx, zoom_mask]
                    zv = zoom_vals / EV_PER_K if row == 0 else zoom_vals
                    ax.plot(xdata * 1e4, zv, color=color, lw=1.5, alpha=0.8)
            ax.set_xlabel("Position (um)")
            ax.set_ylabel(ylabel)
            ax.set_title(title)
            ax.grid(True, alpha=0.3)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0, vmax=max(times_ns)))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes, location="right", shrink=0.6)
    cbar.set_label("Time (ns)")
    fig.suptitle("Tele & Nele Spatial Profiles", fontweight="bold")
    plt.tight_layout(rect=[0, 0, 0.95, 0.96])
    fig.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _plot_time_spatial(data: dict, save_path: str):
    """时空演化 imshow → analysis_time_spatial.png (chsich04 风格)"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    t = data["times_s"]
    x_cm = data["x_cm"]
    tele_2d = data["tele_2d"]
    nele_2d = data["nele_2d"]
    dens_2d = data["dens_2d"]
    txn_2d = data.get("txn_2d", tele_2d * nele_2d)
    EV_PER_K = 11604.5

    center = x_cm[len(x_cm)//2]
    zoom_cm = 5e-4
    zoom_mask = np.abs(x_cm - center) <= zoom_cm
    x_zoom = x_cm[zoom_mask] * 1e4
    times_ns = t * 1e9

    fields = {
        "TXN": txn_2d[:, zoom_mask],
        "Te (eV)": tele_2d[:, zoom_mask] / EV_PER_K,
        "Nele (cm-3)": nele_2d[:, zoom_mask],
        "Dens (g/cm3)": dens_2d[:, zoom_mask],
    }

    plt.rcParams.update({"font.size": 14, "axes.labelsize": 16,
                         "axes.titlesize": 18, "figure.dpi": 200})
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for ax, (name, arr) in zip(axes.flat, fields.items()):
        im = ax.pcolormesh(x_zoom, times_ns, arr, shading="auto")
        ax.set_xlabel("x (um)")
        ax.set_ylabel("Time (ns)")
        ax.set_title(name)
        fig.colorbar(im, ax=ax, shrink=0.8)

    fig.suptitle("Space-Time Evolution (Center +/-5 um)", fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(save_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _generate_post_plots(run_dir: Path, out) -> dict:
    """生成后处理诊断图 — chsich04 风格, 含2D空间图"""
    import h5py
    NA = 6.02214076e23  # Avogadro

    sim_output_plots = run_dir / "sim_output_plots"
    sim_output_plots.mkdir(parents=True, exist_ok=True)
    plots = {}
    h5_path = Path(out.result_h5_path) if out.result_h5_path else None
    if not h5_path or not h5_path.exists():
        return plots

    # ── 读取 result.h5 (含2D空间数据) ──
    with h5py.File(str(h5_path), "r") as f:
        t = np.array(f["t"][:], dtype=float)
        x = np.array(f["x"][:], dtype=float)
        tele_2d = np.array(f["tele"][()], dtype=float)
        ye_2d = np.array(f["ye"][()], dtype=float)
        dens_2d = np.array(f["dens"][()], dtype=float)
    nele_2d = ye_2d * dens_2d * NA
    txn_2d = tele_2d * nele_2d

    # 中心 ±1um 平均 (1D 时序)
    center_idx = x.shape[0] // 2
    mask = np.abs(x - x[center_idx]) <= 1e-4  # 1 um
    tele_1d = np.mean(tele_2d[:, mask], axis=1)
    nele_1d = np.mean(nele_2d[:, mask], axis=1)
    dens_1d = np.mean(dens_2d[:, mask], axis=1)
    txn_1d = tele_1d * nele_1d

    if len(t) < 2:
        return plots

    # 均匀网格插值 (10ps 间隔)
    from scipy.interpolate import interp1d
    dt = t[-1] - t[0]
    n_grid = max(2, int(dt / 1e-11) + 1)
    grid_s = np.linspace(t[0], t[-1], n_grid)
    grid_ns = grid_s * 1e9

    tele_g = interp1d(t, tele_1d, kind="linear", bounds_error=False,
                       fill_value="extrapolate")(grid_s)
    nele_g = interp1d(t, nele_1d, kind="linear", bounds_error=False,
                       fill_value="extrapolate")(grid_s)
    dens_g = interp1d(t, dens_1d, kind="linear", bounds_error=False,
                       fill_value="extrapolate")(grid_s)

    data = {
        "times_s": t, "x_cm": x,
        "tele_K": tele_1d, "nele": nele_1d, "dens": dens_1d,
        "tele_2d": tele_2d, "nele_2d": nele_2d,
        "dens_2d": dens_2d, "txn_2d": txn_2d,
    }

    # 两阶段窗口评分
    win = _sliding_window_best(grid_s, tele_g, nele_g)
    p1 = win["phase1_range_ns"]
    print(f"  Phase 1 (600ps): [{p1[0]:.2f}, {p1[1]:.2f}] ns  score={win['txn_min']:.4f}")
    print(f"  Phase 2 (300ps): G[0]'={win['g0_unclipped']:.4f} "
          f"(g1={win['g1_raw']:.4f}, g2={win['g2_raw']:.4f})")
    print(f"  Best window: {win['w_start_ns']:.2f} ~ {win['w_end_ns']:.2f} ns")

    txn_arr = tele_g * nele_g

    # 1. Four-panel time series (含 Phase 1 高亮)
    ts_path = sim_output_plots / "analysis_time_series.png"
    try:
        _plot_time_series(grid_ns, txn_arr, tele_g, nele_g,
                          dens_g, win, str(ts_path))
        if ts_path.exists():
            plots["time_series"] = ts_path
            print(f"  → {ts_path}")
    except Exception as e:
        print(f"  ⚠ time_series failed: {e}")

    # 2. Spatial profiles
    sp_path = sim_output_plots / "analysis_spatial.png"
    try:
        _plot_spatial(data, str(sp_path), win)
        if sp_path.exists():
            plots["spatial"] = sp_path
            print(f"  → {sp_path}")
    except Exception as e:
        print(f"  ⚠ spatial failed: {e}")

    # 3. Time-spatial imshow
    tsp_path = sim_output_plots / "analysis_time_spatial.png"
    try:
        _plot_time_spatial(data, str(tsp_path))
        if tsp_path.exists():
            plots["time_spatial"] = tsp_path
            print(f"  → {tsp_path}")
    except Exception as e:
        print(f"  ⚠ time_spatial failed: {e}")

    # 4. Dual-axis txn time series
    txn_path = sim_output_plots / "analysis_txn_time_series.png"
    try:
        _plot_txn_time_series(grid_ns, tele_g, nele_g,
                              win, str(txn_path))
        if txn_path.exists():
            plots["txn_timeseries"] = txn_path
            print(f"  → {txn_path}")
    except Exception as e:
        print(f"  ⚠ txn plot failed: {e}")

    return plots


# ============================================================
#  CLI 入口
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="GradDensSandwich HE-CH-Si-CH-HE FLASH 仿真",
        epilog="""
CH 密度梯度:
  最多 10 组 (ch_posx_i, ch_dens_i), 默认 0=未使用
  CGS 单位: 位置 cm, 密度 g/cm³
  sim_polyHeight = max(active ch_posx), 不在 .par 中设置

示例:
  python run_grad.py                              # 用 6 组默认
  python run_grad.py --no-simulate                # 仅生成输入文件
  python run_grad.py --ch-pos5 500e-5 --ch-dens5 0.8  # 自定义控制点
""",
    )

    # ── 靶参数 ──
    parser.add_argument("--ch-density", type=float, default=0.15)
    parser.add_argument("--si-density", type=float, default=2.33)
    parser.add_argument("--si-thick", type=float, default=0.15e-4)

    # ── CH 密度梯度: ch_num + num 组控制点 ──
    parser.add_argument("--ch-num", type=int, default=7)
    parser.add_argument("--ch-pos1", type=float, default=0.15e-4)
    parser.add_argument("--ch-dens1", type=float, default=1000.0e-3)

    parser.add_argument("--ch-pos2", type=float, default=1.15e-4)
    parser.add_argument("--ch-dens2", type=float, default=1000.0e-3)

    parser.add_argument("--ch-pos3", type=float, default=1.2e-4)
    parser.add_argument("--ch-dens3", type=float, default=1.0e-6)

    parser.add_argument("--ch-pos4", type=float, default=30.0e-4)
    parser.add_argument("--ch-dens4", type=float, default=1.0e-6)

    parser.add_argument("--ch-pos5", type=float, default=30.5e-4)
    parser.add_argument("--ch-dens5", type=float, default=80.0e-3)

    parser.add_argument("--ch-pos6", type=float, default=90.0e-4)
    parser.add_argument("--ch-dens6", type=float, default=180.0e-3)

    parser.add_argument("--ch-pos7", type=float, default=90.5e-4)
    parser.add_argument("--ch-dens7", type=float, default=1e-6)

    parser.add_argument("--ch-pos8", type=float, default=0)
    parser.add_argument("--ch-dens8", type=float, default=0)
    parser.add_argument("--ch-pos9", type=float, default=0)
    parser.add_argument("--ch-dens9", type=float, default=0)
    parser.add_argument("--ch-pos10", type=float, default=0)
    parser.add_argument("--ch-dens10", type=float, default=0)

    # ── 激光脉冲 ──
    parser.add_argument("--pulse-peak", type=float, default=5e14)
    parser.add_argument("--pulse-fwhm", type=float, default=1.0e-9)
    parser.add_argument("--pulse-order", type=int, default=4)

    # ── 仿真开关 ──
    parser.add_argument("--simulate", action="store_true", default=True)
    parser.add_argument("--no-simulate", dest="simulate", action="store_false")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--use-cache", action="store_true", default=False)

    args = parser.parse_args()

    _SCRIPT_DIR = Path(__file__).resolve().parent
    runs_dir = _SCRIPT_DIR / "runs_grad_dens_sandwich"
    runs_dir.mkdir(parents=True, exist_ok=True)

    if args.simulate:
        import subprocess
        try:
            r = subprocess.run(
                ["wsl", "bash", "-lc",
                 "ls ~/$FLASH_SIM_USER_DIR/FLASH/FLASH4.8/$FLASH_SIM_USER_DIR/flash4_grad_dens_sandwich.bin 2>/dev/null"],
                capture_output=True, text=True, timeout=5)
            if r.stdout.strip():
                print(f"  ✅ cached flash4: {r.stdout.strip()}")
            else:
                print("ℹ 无缓存 flash4, 引擎将自动编译")
        except Exception:
            print("ℹ FLASH 引擎将自动编译 (如需要)")

    result = run_grad(
        sim_rhoPoly=args.ch_density,
        sim_rhoTarg=args.si_density,
        sim_targHeight=args.si_thick,
        ch_num=args.ch_num,
        ch_posx_1=args.ch_pos1,  ch_dens_1=args.ch_dens1,
        ch_posx_2=args.ch_pos2,  ch_dens_2=args.ch_dens2,
        ch_posx_3=args.ch_pos3,  ch_dens_3=args.ch_dens3,
        ch_posx_4=args.ch_pos4,  ch_dens_4=args.ch_dens4,
        ch_posx_5=args.ch_pos5,  ch_dens_5=args.ch_dens5,
        ch_posx_6=args.ch_pos6,  ch_dens_6=args.ch_dens6,
        ch_posx_7=args.ch_pos7,  ch_dens_7=args.ch_dens7,
        ch_posx_8=args.ch_pos8,  ch_dens_8=args.ch_dens8,
        ch_posx_9=args.ch_pos9,  ch_dens_9=args.ch_dens9,
        ch_posx_10=args.ch_pos10, ch_dens_10=args.ch_dens10,
        pulse_peak=args.pulse_peak,
        pulse_fwhm=args.pulse_fwhm,
        pulse_order=args.pulse_order,
        simulate=args.simulate,
        flash_timeout=args.timeout,
        force_recompile=not args.use_cache,
    )

    mode = "仿真完成" if result.get("success") and result.get("simulated") else \
           "仿真失败" if result.get("simulated") else \
           "仅生成输入文件"
    print(f"\n  📋 {mode}")
    print(f"  📁 run_dir: {result['run_dir']}")
    if result.get("result_h5"):
        print(f"  📊 result.h5: {result['result_h5']}")
