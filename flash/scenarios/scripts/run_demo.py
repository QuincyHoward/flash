#!/usr/bin/env python
"""公开示例场景的统一极短验证入口。

用途：拿到 flash-sim 包后，用一条命令确认环境是否可用 ——
输入能否生成、FLASH 能否 setup/编译/启动、能否写出首帧。

    python flash/scenarios/public/run_demo.py --list
    python flash/scenarios/public/run_demo.py --scene ch_center --tmax 1e-11
    python flash/scenarios/public/run_demo.py --all --tmax 1e-11

★ 极短验证不产生物理结果（见 flash/scenarios/hints.py 的说明）。
  正式仿真请按横幅提示修改时间参数，或省略 --tmax 用场景默认值。
"""
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

# 源码工作区模式: 把仓库根注入 sys.path（wheel 安装时自然找不到，跳过）
_ROOT = Path(__file__).resolve().parent
for _ in range(10):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    _ROOT = None
if _ROOT is not None and str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from flash.scenarios.hints import is_short_run, short_validation_notice  # noqa: E402
from flash.scenarios.registry import get_scenario, list_scenarios  # noqa: E402
from flash.scenarios.simulator import FlashSimulatorEngine  # noqa: E402

# 每个示例的"正式仿真改哪里"（与各场景实际代码位置对应，改动代码时请同步）
WHERE_TO_CHANGE = {
    "ch_center": (
        "ch_center/__init__.py: params['tmax']（默认 1.2e-9 s）\n"
        "       或 ch_center/laserslab1d_local_custom.py: cfg['tmax_multiplier']\n"
        "       （tmax = 脉冲总时长 × multiplier，默认 1.1）"
    ),
    "grad_dens_sandwich": (
        "grad_dens_sandwich/defaults.py: DEFAULT_TMAX = 1.4e-9 s\n"
        "       或调用时传 params={'tmax': <秒>}"
    ),
    "thin_layer_sandwich_si": (
        "thin_layer_sandwich/defaults_si.py: DEFAULT_TMAX = 1.2e-9 s\n"
        "       或调用时传 params={'tmax': <秒>}"
    ),
}

PUBLIC_SCENES = ["ch_center", "grad_dens_sandwich", "thin_layer_sandwich_si"]


def _fmt(res) -> str:
    """把 SimulationOutput 的关键信息压成一行。"""
    bits = []
    for attr in ("run_id", "run_dir", "n_frames", "status"):
        if hasattr(res, attr):
            v = getattr(res, attr)
            if v is not None:
                bits.append(f"{attr}={v}")
    return " ".join(bits) if bits else repr(res)[:80]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="公开示例场景极短验证（确认环境可用，不产生物理结果）")
    ap.add_argument("--scene", action="append", default=None,
                    help="场景名，可重复；默认用 public 下的三个示例")
    ap.add_argument("--all", action="store_true", help="跑全部公开示例")
    ap.add_argument("--list", action="store_true", help="列出已注册场景后退出")
    ap.add_argument("--tmax", type=float, default=1e-11,
                    help="仿真结束时间（秒）。默认 1e-11 = 极短验证")
    ap.add_argument("--runs-dir", default=None, help="运行输出目录")
    ap.add_argument("--no-flash", action="store_true",
                    help="只生成输入不跑 FLASH（dry_run）")
    args = ap.parse_args()

    if args.list:
        print("已注册场景：")
        for name, desc in list_scenarios():
            mark = "★" if name in PUBLIC_SCENES else " "
            print(f"  {mark} {name:24s} {desc}")
        print("\n★ = 公开示例（run_demo.py 默认跑这些）")
        return 0

    targets = args.scene or (PUBLIC_SCENES if args.all or not args.scene else [])
    if not targets:
        targets = PUBLIC_SCENES

    if is_short_run(args.tmax):
        short_validation_notice(
            tmax_s=args.tmax,
            scene_name=", ".join(targets),
            where="\n".join(f"     • {t}: {WHERE_TO_CHANGE.get(t, '（未登记）')}"
                            for t in targets),
            extra="极短验证通过后，记得用正式 tmax 重跑一遍再出图。",
        )

    results = []
    for name in targets:
        print(f"\n{'─' * 72}\n[{name}] 开始\n{'─' * 72}")
        try:
            scenario = get_scenario(name)
            engine = FlashSimulatorEngine(scenario)
            res = engine.run(
                params_override={"tmax": args.tmax},
                runs_dir=args.runs_dir,
                dry_run=args.no_flash,
                flash_timeout=1800,
            )
            results.append((name, True, _fmt(res)))
            print(f"[{name}] ✓ 完成: {_fmt(res)}")
        except Exception as exc:  # noqa: BLE001
            results.append((name, False, f"{type(exc).__name__}: {exc}"[:200]))
            print(f"[{name}] ✗ 失败: {type(exc).__name__}: {exc}")
            traceback.print_exc(limit=3)

    print(f"\n{'=' * 72}")
    ok = [r for r in results if r[1]]
    print(f"汇总: {len(ok)}/{len(results)} 通过")
    for name, good, msg in results:
        print(f"  {'✓' if good else '✗'} {name:24s} {msg}")
    print("=" * 72)
    if is_short_run(args.tmax):
        print("提醒：以上为极短验证（tmax=%.1e s），正式仿真请按上方面板修改时间参数。"
              % args.tmax)
    return 0 if len(ok) == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
