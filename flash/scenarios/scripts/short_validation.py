#!/usr/bin/env python
"""公开场景极短验证 —— 三个 public 场景一键跑（tmax = 1e-13 s）

用途
----
极短验证只回答一个问题：**输入能否生成、FLASH 能否启动并写出首帧**。
它**不产生物理结果**（1e-13 s 内激光尚未有效加热靶材）。

    python flash/scenarios/scripts/short_validation.py
    python flash/scenarios/scripts/short_validation.py --tmax 1e-13
    python flash/scenarios/scripts/short_validation.py --scene ch_center

★ 三个场景都走**统一入口** `python -m flash.scenarios.cli run <场景>`，
  缺省 `--mode auto`（平台自适应）：
    Windows + WSL  → wsl        （Windows 驱动 → WSL 内跑 FLASH）
    WSL / Linux    → local      （本机直跑）
    超算登录节点   → 明确报错   （引擎型场景只承接本机执行，见 catalog 策略）

★ 与 `run_demo.py` 的区别：run_demo 走**引擎**（registry 声明式场景），
  本脚本走**统一 CLI**（catalog）——后者同时覆盖 ch_center 的场景脚本路径，
  因此能顺带验证"场景脚本 + 引擎"两条执行体是否一致。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
for _ in range(10):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    _ROOT = None
if _ROOT is not None and str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

PUBLIC_SCENES = ["ch_center", "grad_dens_sandwich", "thin_layer_sandwich_si"]

#: 各场景"正式仿真"改哪里（与 run_demo.py 的 WHERE_TO_CHANGE 对应）
WHERE_TO_CHANGE = {
    "ch_center": ("ch_center/laserslab1d_local_custom.py: config_constants['tmax_multiplier']"
                  "（tmax = 脉冲总时长 × multiplier）"),
    "grad_dens_sandwich": "grad_dens_sandwich/defaults.py: DEFAULT_TMAX",
    "thin_layer_sandwich_si": "thin_layer_sandwich/defaults_si.py: DEFAULT_TMAX",
}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="公开场景极短验证（tmax 默认 1e-13 s，仅确认链路通畅）")
    ap.add_argument("--scene", action="append", default=None,
                    help="场景名，可重复；默认跑全部三个公开场景")
    ap.add_argument("--tmax", type=float, default=1e-13,
                    help="仿真结束时间（秒）。默认 1e-13 = 极短验证")
    ap.add_argument("--mode", default="auto",
                    help="执行目标：auto(默认，平台自适应) | local | wsl")
    args = ap.parse_args()

    targets = args.scene or PUBLIC_SCENES
    py = sys.executable
    print("=" * 72)
    print(f" 公开场景极短验证  tmax = {args.tmax:.3e} s   mode = {args.mode}")
    print("=" * 72)
    print(" 场景:", ", ".join(targets))
    print(" ★ 极短验证**不产生物理结果**，仅确认：输入生成 → FLASH 启动 → 首帧写出")
    for t in targets:
        print(f"     · {t}: 正式仿真改 {WHERE_TO_CHANGE.get(t, '（未登记）')}")
    print("-" * 72)

    results = []
    for name in targets:
        cmd = [py, "-m", "flash.scenarios.cli", "run", name,
               "--tmax", f"{args.tmax:g}", "--mode", args.mode]
        print(f"\n[{name}] {' '.join(cmd)}")
        t0 = time.time()
        rc = subprocess.run(cmd, cwd=str(_ROOT)).returncode
        dt = time.time() - t0
        results.append((name, rc == 0, dt))
        print(f"[{name}] {'✓ 通过' if rc == 0 else '✗ 失败 (rc=%d)' % rc}  ({dt:.1f} s)")

    print("\n" + "=" * 72)
    ok = [r for r in results if r[1]]
    print(f"汇总: {len(ok)}/{len(results)} 通过")
    for name, good, dt in results:
        print(f"  {'✓' if good else '✗'} {name:24s} {dt:6.1f} s")
    print("=" * 72)
    if ok:
        print("提醒：以上为**极短验证**，正式仿真请按上面的位置改回真实 tmax。")
    return 0 if len(ok) == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
