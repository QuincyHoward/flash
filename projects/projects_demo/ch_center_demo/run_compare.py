#!/usr/bin/env python3
"""ch_center 双密度对比 — 本地 WSL 仿真运行器

对 ch_center 场景用两种 CH 靶密度 (sim_rhoTarg) 分别运行 FLASH,
生成对比数据集。

用法:
  python run_compare.py                     # 双密度完整运行 (WSL)
  python run_compare.py --dry-run           # 仅生成输入, 不运行 FLASH
  python run_compare.py --dens 0.5,2.0      # 自定义密度列表
  python run_compare.py --run-id 000001     # 自定义起始 run_id
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

# ── Bootstrap: 定位 flash 包根目录 ──
_HERE = Path(__file__).resolve().parent          # .../projects_demo/ch_center_demo
_PROJ_PKG = _HERE.parent                         # .../projects_demo
_PROJECTS = _PROJ_PKG.parent                     # .../projects
_FLASH_ROOT = _PROJECTS.parent                   # .../flash
_PARENT = _FLASH_ROOT.parent                     # .../sim (含 flash 包)
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from flash.scenarios.registry import get_scenario
from flash.scenarios.simulator import FlashSimulatorEngine

# 默认对比密度 (g/cm³)
DEFAULT_DENSITIES = [0.5, 2.0]
DEFAULT_RUNS_DIR = _HERE / "runs_ch_center_compare"


def run_compare(
    densities=None,
    runs_dir=None,
    start_run_id=1,
    run_flash=True,
    verbose=True,
):
    """运行双密度对比仿真。

    Returns:
        list of SimulationOutput
    """
    densities = densities or DEFAULT_DENSITIES
    runs_dir = Path(runs_dir or DEFAULT_RUNS_DIR)
    scenario = get_scenario("ch_center")
    engine = FlashSimulatorEngine(scenario, verbose=verbose)

    print("=" * 64)
    print("  ch_center 双密度对比 — 本地 WSL 仿真")
    print("=" * 64)
    print(f"  场景: {scenario.name} ({scenario.description})")
    print(f"  密度方案: {densities} g/cm³")
    print(f"  运行目录: {runs_dir}")
    print(f"  执行 FLASH: {run_flash}")
    print()

    results = []
    for i, dens in enumerate(densities):
        run_id = f"{start_run_id + i:06d}"
        label = f"dens_{dens:g}"
        print(f"\n{'─' * 50}")
        print(f"  ▶ [{label}] sim_rhoTarg = {dens} g/cm³  (run_id={run_id})")
        print(f"{'─' * 50}")

        out = engine.run(
            params_override={
                "sim_rhoTarg": dens,
                # 演示参数: 粗网格 + 短时仿真, 保证本地 WSL 快速完成
                # (ch_center 默认 lrefine_max=5/tmax=1.2ns 需数小时)
                "lrefine_max": 4,
                "nblockx": 4,
                "tmax": 2.0e-10,
                "output_t_max": 2.0e-10,
                "output_t_step": 5e-12,
            },
            runs_dir=str(runs_dir),
            run_id=run_id,
            run_flash=run_flash,
            flash_timeout=600,
            force_recompile=False,   # 复用编译缓存
        )
        results.append(out)

        # 摘要
        print(f"\n  结果: success={out.success}")
        print(f"    run_dir:  {out.run_dir}")
        print(f"    result:   {out.result_h5_path}")
        print(f"    n_chk:    {out.n_chk}, n_timesteps: {out.n_timesteps}")
        if out.error_message:
            print(f"    error:    {out.error_message}")

    # 保存运行摘要
    summary = {
        "scenario": scenario.name,
        "densities": [float(d) for d in densities],
        "runs_dir": str(runs_dir),
        "results": [
            {
                "run_id": f"{start_run_id + i:06d}",
                "dens": float(dens),
                "success": out.success,
                "run_dir": str(out.run_dir),
                "result_h5": str(out.result_h5_path),
                "n_chk": out.n_chk,
            }
            for i, (dens, out) in enumerate(zip(densities, results))
        ],
    }
    summary_path = runs_dir / "compare_summary.json"
    runs_dir.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n  对比摘要已保存: {summary_path}")
    return results


def main():
    parser = argparse.ArgumentParser(description="ch_center 双密度对比运行器")
    parser.add_argument("--dens", default=None,
                        help="密度列表, 逗号分隔 (默认: 0.5,2.0)")
    parser.add_argument("--runs-dir", default=None, help="运行根目录")
    parser.add_argument("--run-id", default=1, type=int, help="起始 run_id (默认 1)")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅生成输入文件, 不运行 FLASH")
    args = parser.parse_args()

    densities = None
    if args.dens:
        densities = [float(x.strip()) for x in args.dens.split(",")]

    run_compare(
        densities=densities,
        runs_dir=args.runs_dir,
        start_run_id=args.run_id,
        run_flash=not args.dry_run,
    )


if __name__ == "__main__":
    main()
