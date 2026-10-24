"""统一场景 CLI —— 唯一实现入口
═════════════════════════════════════════════════════════════════════

★ 2026-10-24（解耦计划 B2）：

    python -m flash.scenarios.cli list
    python -m flash.scenarios.cli explain ch_center          # 只打印判定轨迹
    python -m flash.scenarios.cli run ch_center              # 默认 --mode auto
    python -m flash.scenarios.cli run SNBOneCH_ml --mode hpc-remote --tmax 1e-11

设计约束：
  * `--mode` 缺省 = `auto`（平台自适应）。显式值 / `FLASH_RUN_MODE` 永远优先。
  * 平台判定与策略校验由 `flash.flash_run.execution.resolve_target` 完成，
    **不在本文件里重写一遍**（否则又会出现"两套判定"）。
  * 退出码：0=成功；1=失败或被策略拒绝（便于 shell/CI 直接判）。
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from flash.flash_run.execution import (
    ExecOptions,
    explain_target,
    run_scene,
)


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m flash.scenarios.cli",
        description="flash-sim 统一场景入口（平台自适应，--mode auto 为默认）",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="列出可执行场景与允许的运行模式")

    p_exp = sub.add_parser("explain", help="只打印目标判定轨迹，不执行")
    p_exp.add_argument("scene")
    p_exp.add_argument("--mode", default="auto")

    p_run = sub.add_parser("run", help="运行场景")
    p_run.add_argument("scene")
    p_run.add_argument("--mode", default="auto",
                       help="auto(默认) | local | wsl | hpc-remote | hpc-insitu")
    p_run.add_argument("--account", default="", help="超算凭据名（默认 flash_ssh）")
    p_run.add_argument("--partition", default="")
    p_run.add_argument("--distro", default="", help="WSL 发行版（默认系统默认）")
    p_run.add_argument("--nproc", type=int, default=None)
    p_run.add_argument("--tmax", default=None, help="终止时间（秒），如 1e-11")
    p_run.add_argument("--with-plt", action="store_true", help="连 plt 一起回收")
    p_run.add_argument("--frames", type=int, default=0)
    p_run.add_argument("--skip-build", action="store_true")
    p_run.add_argument("--dry-run", action="store_true", help="只生成输入，不运行")
    p_run.add_argument("--explain-target", action="store_true")
    p_run.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    p_run.add_argument("args", nargs="*", help="透传给底层场景脚本的额外参数")
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    from flash.scenarios.catalog import get_scene, list_scenes

    ap = _build_parser()
    ns = ap.parse_args(argv)

    if ns.cmd == "list":
        print(f"{'场景':<16} {'允许模式':<34} 说明")
        print("-" * 96)
        for name, desc, allowed in list_scenes():
            print(f"{name:<16} {','.join(allowed):<34} {desc}")
        return 0

    try:
        scene = get_scene(ns.scene)
    except KeyError as exc:
        print(f"[X] {exc}", file=sys.stderr)
        return 1

    if ns.cmd == "explain":
        print(explain_target(ns.mode, scene.policy))
        return 0

    opts = ExecOptions(
        mode=ns.mode,
        account=ns.account,
        partition=ns.partition,
        distro=ns.distro,
        nproc=ns.nproc,
        tmax=ns.tmax,
        with_plt=ns.with_plt,
        frames=ns.frames,
        skip_build=ns.skip_build,
        dry_run=ns.dry_run,
        explain_only=ns.explain_target,
        extra={"args": tuple(ns.args)},
    )
    result = run_scene(scene, opts)

    if ns.json:
        print(json.dumps({
            "ok": result.ok,
            "target": result.target,
            "run_dir": str(result.run_dir) if result.run_dir else None,
            "collected": result.collected,
            "stats": result.stats,
            "reason": result.reason,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"\n[{'OK' if result.ok else 'FAIL'}] 场景={scene.name} target={result.target}")
        if result.run_dir:
            print(f"  运行目录: {result.run_dir}")
        if result.collected:
            print(f"  回收 {len(result.collected)} 个文件")
        if result.reason:
            print(f"  原因: {result.reason}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
