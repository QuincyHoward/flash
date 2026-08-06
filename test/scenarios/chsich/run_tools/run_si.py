"""
run_si.py — Si/CH/He 三层靶 FLASH 仿真运行 + 后处理诊断图 (双击可执行)

脉冲数据通过 pulse_shapes.py 的 _QUICK_EDIT_ED_DATA 控制:
  打开 test/scenarios/chsich/pulse_helpers/pulse_shapes.py
  找到 _QUICK_EDIT_ED_DATA 直接修改 (time, power) 列表。
  把整个赋值删掉 → 自动回落为梯形方波。

仿真开关:
  --simulate / --no-simulate: 控制是否执行真实 FLASH 仿真

用法:
  python run_si.py                         # 默认 (使用 pulse_shapes.py 数据)
  python run_si.py --no-simulate           # 仅生成输入文件
  python run_si.py --ch-thick 50e-4        # 自定义靶参数
"""

from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap: find flash project root
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT
for _p in [str(_PARENT), str(_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 脉冲辅助路径
_CHSICH_DIR = Path(__file__).resolve().parent.parent
if str(_CHSICH_DIR) not in sys.path:
    sys.path.insert(0, str(_CHSICH_DIR))

from pulse_helpers import resolve_pulse_data

import numpy as np


# ============================================================
#  主运行函数
# ============================================================

def run_si(
    sim_rhoPoly: float = 0.1,
    sim_polyHeight: float = 90e-4,
    sim_rhoTarg: float = 2.33,
    sim_targHeight: float = 0.15e-4,
    simulate: bool = True,
    flash_timeout: int = 900,
) -> dict:
    """运行 Si/CH/He 三层靶 FLASH 仿真。

    脉冲数据从 pulse_shapes.py 的 _QUICK_EDIT_ED_DATA 读取。
    未定义时自动回落为梯形方波。

    Args:
        sim_rhoPoly: CH 密度 (g/cm³)
        sim_polyHeight: CH 半厚 (cm)
        sim_rhoTarg: Si 密度 (g/cm³)
        sim_targHeight: Si 半厚 (cm)
        simulate: True=运行 FLASH, False=仅生成输入文件
        flash_timeout: WSL FLASH 超时 (秒)

    Returns:
        dict: {run_dir, result_h5, plots, simulated, success}
    """
    from flash.scenarios.registry import get_scenario
    from flash.scenarios.simulator import FlashSimulatorEngine

    sc = get_scenario("thin_layer_sandwich_si")
    engine = FlashSimulatorEngine(sc, verbose=True)

    # ── 解析脉冲: 从 _QUICK_EDIT_ED_DATA 读取, 空则回落 ──
    pulse_data = resolve_pulse_data()
    pulse_times = [t for t, _ in pulse_data]
    pulse_powers = [p for _, p in pulse_data]
    sim_tmax = max(pulse_times) + 0.2e-9

    params_override = {
        "sim_rhoPoly": sim_rhoPoly,
        "sim_polyHeight": sim_polyHeight,
        "sim_rhoTarg": sim_rhoTarg,
        "sim_targHeight": sim_targHeight,
        "laser_times": pulse_times,
        "laser_powers": pulse_powers,
        "tmax": sim_tmax,
        "output_t_max": sim_tmax,
    }

    print(f"\n{'='*60}")
    print(f"  Si/CH/He — LaserSlab 1D")
    print(f"  CH: {sim_polyHeight*1e4:.0f} um, {sim_rhoPoly:.3f} g/cm³")
    print(f"  Si: {sim_targHeight*1e4:.2f} um, {sim_rhoTarg:.2f} g/cm³")
    print(f"  Pulse: {len(pulse_times)} segments")
    for k in range(len(pulse_times)):
        print(f"  ed_time_1_{k+1} = {pulse_times[k]:.4e}  "
              f"ed_power_1_{k+1} = {pulse_powers[k]:.4e}")
    print(f"  tmax:  {sim_tmax*1e9:.1f} ns  simulate={'ON' if simulate else 'OFF'}")
    print(f"{'='*60}\n")

    # ── 引擎运行 ──
    out = engine.run(
        params_override=params_override,
        run_flash=simulate,
        keep_flash_raw=True,
        flash_timeout=flash_timeout if simulate else 1,
    )
    run_dir = Path(out.run_dir)

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
#  后处理诊断图
# ============================================================

def _generate_post_plots(run_dir: Path, out) -> dict:
    from flash.scenarios.collision_compression.thin_layer_sandwich.analysis.core import (
        sliding_window_txn, interpolate_to_uniform_grid,
    )
    from flash.scenarios.collision_compression.thin_layer_sandwich.analysis.txn import (
        plot_time_series as plot_txn_timeseries,
    )
    from flash.scenarios.collision_compression.thin_layer_sandwich.analysis.dens import (
        plot_tele_nele_spatial_profiles,
    )
    from flash.scenarios.collision_compression.thin_layer_sandwich.analysis.timespatial import (
        plot_time_spatial,
    )
    from flash.scenarios.collision_compression.thin_layer_sandwich.io.flash_reader import (
        build_raw_from_engine, NA,
    )
    from flash.scenarios.collision_compression.thin_layer_sandwich.viz.plot_tele_nele_v2 import (
        plot_tele_nele_v2,
    )

    sim_output_plots = run_dir / "sim_output_plots"
    sim_output_plots.mkdir(parents=True, exist_ok=True)
    plots = {}

    if not out.result_h5_path or not Path(out.result_h5_path).exists():
        return plots

    raw = build_raw_from_engine(Path(out.result_h5_path),
                                center_half_width_um=1.0, verbose=False)
    t_arr = raw["times_s"]
    fields_raw = raw["fields"]
    if len(t_arr) < 2 or "tele" not in fields_raw:
        return plots

    grid_s, interp = interpolate_to_uniform_grid(t_arr, fields_raw)
    tele_arr = interp.get("tele", np.zeros_like(grid_s))
    nele_arr = interp.get("nele",
                          interp.get("ye", np.zeros_like(grid_s))
                          * interp.get("dens", np.zeros_like(grid_s)) * NA)
    txn_arr = tele_arr * nele_arr
    dens_arr = interp.get("dens", np.zeros_like(grid_s))

    txn_window = sliding_window_txn(grid_s, txn_arr, tele_arr, nele_arr)
    txn_p = plot_txn_timeseries(grid_s, txn_arr, tele_arr, nele_arr,
                                 txn_window, str(sim_output_plots / "analysis_txn"),
                                 dens_series=dens_arr)
    plots.update(txn_p)

    try:
        ts_path = sim_output_plots / "analysis_time_series.png"
        plot_tele_nele_v2(Path(out.result_h5_path), ts_path,
                          window_start_ns=txn_window["best_start_ns"],
                          window_end_ns=txn_window["best_end_ns"])
        if ts_path.exists():
            plots["tele_nele_timeseries"] = ts_path
    except Exception as e:
        print(f"  ⚠ tele/nele 图失败: {e}")

    try:
        sp = plot_tele_nele_spatial_profiles(
            run_dir / "sim_output", sim_output_plots, center_zoom_um=None)
        if sp:
            plots.update(sp)
    except Exception:
        pass

    try:
        tsp = plot_time_spatial(Path(out.result_h5_path),
                                sim_output_plots / "analysis_time_spatial.png")
        plots["timespatial"] = tsp
    except Exception as e:
        print(f"  ⚠ 时空演化图失败: {e}")

    return plots


# ============================================================
#  CLI 入口 (仅保留靶参数 + 仿真开关)
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Si/CH/He FLASH 仿真 — 脉冲数据从 pulse_shapes.py 读取",
        epilog="""
脉冲设置:
  打开 test/scenarios/chsich/pulse_helpers/pulse_shapes.py
  修改 _QUICK_EDIT_ED_DATA 的 (time, power) 列表。
  把整个赋值删掉 → 自动回落为梯形方波。

示例:
  python run_si.py                         # 默认运行
  python run_si.py --no-simulate           # 仅生成输入文件
  python run_si.py --ch-thick 50e-4        # 自定义 CH 厚度
""",
    )

    # ── 靶参数 ──
    parser.add_argument("--ch-density", type=float, default=0.080)
    parser.add_argument("--ch-thick", type=float, default=140e-4)
    parser.add_argument("--si-density", type=float, default=2.33)
    parser.add_argument("--si-thick", type=float, default=0.15e-4)

    # ── 仿真开关 ──
    parser.add_argument("--simulate", action="store_true", default=True)
    parser.add_argument("--no-simulate", dest="simulate", action="store_false")
    parser.add_argument("--timeout", type=int, default=900)

    args = parser.parse_args()

    # ── 检查并运行 ──
    _SCRIPT_DIR = Path(__file__).resolve().parent
    runs_dir = _SCRIPT_DIR / "runs_thin_layer_sandwich_si"
    runs_dir.mkdir(parents=True, exist_ok=True)

    if args.simulate:
        import subprocess
        # 快速检查 WSL flash4 是否存在
        try:
            r = subprocess.run(
                ["wsl", "bash", "-lc",
                 "ls ~/FLASH/FLASH4.8/hello/object_grid_rede_si_*/flash4 2>/dev/null | head -1"],
                capture_output=True, text=True, timeout=5)
            if r.stdout.strip():
                print("✅ WSL 已有编译的 flash4")
            else:
                print("ℹ FLASH 引擎将自动编译 (如需要)")
        except Exception:
            print("ℹ FLASH 引擎将自动编译 (如需要)")

    result = run_si(
        sim_rhoPoly=args.ch_density,
        sim_polyHeight=args.ch_thick,
        sim_rhoTarg=args.si_density,
        sim_targHeight=args.si_thick,
        simulate=args.simulate,
        flash_timeout=args.timeout,
    )

    mode = "仿真完成" if result.get("success") and result.get("simulated") else \
           "仿真失败" if result.get("simulated") else \
           "仅生成输入文件"
    print(f"\n  📋 {mode}")
    print(f"  📁 run_dir: {result['run_dir']}")
    if result.get("result_h5"):
        print(f"  📊 result.h5: {result['result_h5']}")
