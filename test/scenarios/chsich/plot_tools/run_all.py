"""
run_all.py — 一键生成所有精修图 (双击可执行)

自动查找最新的 .par 和 result.h5, 生成:
  1. initial_density.png    — 初始密度分布 (双面板)
  2. laser_pulse.png        — 激光脉冲 + 结构参数
  3. analysis_time_series.png — Tele(eV)+Nele 精修时序

所有输出保存到当前目录。
"""

from __future__ import annotations

import sys
from pathlib import Path

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

# Also add test/scenarios/ for local imports (chsich, etc.)
_SCENARIOS_ROOT = _ROOT / "test" / "scenarios"
if _SCENARIOS_ROOT.exists() and str(_SCENARIOS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCENARIOS_ROOT))

from chsich.plot_tools.par_reader import find_latest_par, find_latest_result_h5
from chsich.plot_tools.plot_initial_density import plot_initial_density_from_par
from chsich.plot_tools.plot_laser_pulse import plot_laser_pulse_from_par
from chsich.plot_tools.plot_tele_nele import plot_tele_nele_from_h5


def run_all(output_dir: str | Path = ".", run_id: str | None = None) -> dict:
    """一键生成所有精修图。

    Args:
        output_dir: 输出目录
        run_id: 指定运行 ID, None=取最新
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  thin_layer_sandwich 精修图 — 一键生成")
    print("=" * 60)

    # 查找数据 (runs 目录: chsich/run_tools/runs_thin_layer_sandwich_si/)
    runs_dir = Path(__file__).resolve().parent.parent / "run_tools" / "runs_thin_layer_sandwich_si"
    par_path = find_latest_par(runs_dir, run_id)
    h5_path = find_latest_result_h5(runs_dir, run_id)
    print(f"  .par:       {par_path.name}")
    print(f"  result.h5:  {h5_path.name}")
    if run_id:
        print(f"  run_id:     {run_id}")
    print()

    results = {}

    # 1. initial_density.png
    print("── 1. initial_density.png ──")
    r1 = plot_initial_density_from_par(par_path, output_dir / "initial_density.png")
    results["initial_density"] = r1
    print()

    # 2. laser_pulse.png
    print("── 2. laser_pulse.png ──")
    r2 = plot_laser_pulse_from_par(par_path, output_dir / "laser_pulse.png")
    results["laser_pulse"] = r2
    print()

    # 3. analysis_time_series.png
    print("── 3. analysis_time_series.png ──")
    r3 = plot_tele_nele_from_h5(h5_path, output_dir / "analysis_time_series.png")
    results["analysis_time_series"] = r3
    print()

    print("=" * 60)
    print(f"  ✅ 全部完成 — 3 张图已保存到 {output_dir.resolve()}")
    print("=" * 60)
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="一键生成所有精修图")
    parser.add_argument("--run-id", type=str, default=None,
                        help="指定运行 ID, 如 000002 (默认最新)")
    args = parser.parse_args()
    run_all(run_id=args.run_id)
