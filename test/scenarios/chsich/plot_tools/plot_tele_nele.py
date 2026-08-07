"""
plot_tele_nele.py — 从 result.h5 绘制 Tele(eV)+Nele 精修图 (双击可执行)

从引擎 result.h5 读取 CH 中心区域数据, 生成含基线 + 手动窗口 的时序图。
窗口中 Tele 基线、Nele 基线可通过 CLI 参数自定义。

用法:
  python plot_tele_nele.py                            # 自动查找最新 result.h5
  python plot_tele_nele.py --h5 /path/to/result.h5
  python plot_tele_nele.py --save out.png --window-start 0.4 --window-end 0.7
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Bootstrap: find flash project root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

# Also add test/scenarios/ for local imports (chsich, etc.)
_SCENARIOS_ROOT = _ROOT / "test" / "scenarios"
if _SCENARIOS_ROOT.exists() and str(_SCENARIOS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCENARIOS_ROOT))

# Windows 控制台 (GBK) 下强制 UTF-8 输出, 避免上标字符 UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def plot_tele_nele_from_h5(
    h5_path: str | Path,
    save_path: str | Path = "analysis_time_series.png",
    *,
    center_half_width_um: float = 1.0,
    window_start_ns: float | None = None,
    window_end_ns: float | None = None,
    xlim_ns: tuple[float, float] | None = None,
    ylim_tele_eV: tuple[float, float] | None = None,
    ylim_nele: tuple[float, float] | None = None,
    tele_base_K: float = 1.2e6,
    nele_base: float = 1.4e23,
    dpi: int = 300,
) -> Path:
    """从 result.h5 绘制 Tele(eV)+Nele 精修图。

    Args:
        h5_path: result.h5 路径
        save_path: PNG 保存路径
        center_half_width_um: 中心区域半宽 (um)
        window_start_ns: 手动窗口起始 (ns), None=自动
        window_end_ns: 手动窗口结束 (ns), None=自动
        tele_base_K: Tele 基线 (K), 默认 1.2e6
        nele_base: Nele 基线 (cm⁻³), 默认 1.4e23
        dpi: 输出 DPI
    """
    # 使用 viz 子包中的精修脚本
    from flash.scenarios.collision_compression.thin_layer_sandwich.viz.plot_tele_nele_v2 import (
        plot_tele_nele_v2,
    )

    return plot_tele_nele_v2(
        Path(h5_path),
        Path(save_path),
        center_half_width_um=center_half_width_um,
        window_start_ns=window_start_ns,
        window_end_ns=window_end_ns,
        xlim_ns=xlim_ns,
        ylim_tele_eV=ylim_tele_eV,
        ylim_nele=ylim_nele,
        tele_base_K=tele_base_K,
        nele_base=nele_base,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="从 result.h5 绘制 Tele/Nele 精修图")
    parser.add_argument("--run-id", type=str, default='000212',
                        help="指定运行 ID, 如 000003 (默认最新)")
    parser.add_argument("--save", type=str, default="analysis_time_series.png",
                        help="PNG 保存路径")
    parser.add_argument("--window-start", type=float, default=1.2,
                        help="手动窗口起始 (ns), 默认自动计算")
    parser.add_argument("--window-end", type=float, default=1.5,
                        help="手动窗口结束 (ns), 默认自动计算")
    parser.add_argument("--xlim", type=float, nargs=2, default=None,
                        metavar=("XMIN", "XMAX"),
                        help="横轴时间范围, 如 --xlim 0 1.2")
    parser.add_argument("--tele-base", type=float, default=1.2e6,
                        help="Tele 基线 (K), 默认 1.2e6")
    parser.add_argument("--nele-base", type=float, default=1.4e23,
                        help="Nele 基线 (cm⁻³), 默认 1.4e23")
    parser.add_argument("--dpi", type=int, default=300,
                        help="输出 DPI")
    parser.add_argument("--ylim-tele", type=float, nargs=2, default=[0,300],
                        metavar=("TMIN", "TMAX"),
                        help="Tele 左轴范围 (eV), 如 --ylim-tele 0 3000")
    parser.add_argument("--ylim-nele", type=float, nargs=2, default=[0,3e23],
                        metavar=("NMIN", "NMAX"),
                        help="Nele 右轴范围 (cm⁻³), 如 --ylim-nele 0 1e23")
    args = parser.parse_args()

    from chsich.plot_tools.par_reader import find_latest_result_h5
    runs_dir = Path(__file__).resolve().parent.parent / "run_tools" / "runs_thin_layer_sandwich_si"
    h5_path = find_latest_result_h5(runs_dir, args.run_id)
    print(f"使用 result.h5: {h5_path}")

    plot_tele_nele_from_h5(
        h5_path,
        args.save,
        window_start_ns=args.window_start,
        window_end_ns=args.window_end,
        xlim_ns=tuple(args.xlim) if args.xlim else None,
        ylim_tele_eV=tuple(args.ylim_tele) if args.ylim_tele else None,
        ylim_nele=tuple(args.ylim_nele) if args.ylim_nele else None,
        tele_base_K=args.tele_base,
        nele_base=args.nele_base,
        dpi=args.dpi,
    )
