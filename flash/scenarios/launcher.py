# -*- coding: utf-8 -*-
"""launcher.py — 场景目录薄启动器统一实现（2026-10-27 去注册化）
════════════════════════════════════════════════════════════════════════════

★ 目的：让每个场景子目录里的一份 ``run.py``（内容逐字节相同）可以
  ``cd <场景目录> && python run.py [--mode auto] [--tmax ...]`` 直接跑。

★ 设计：**不产生第三条执行路径**。``run_from_dir`` 只做两件事：

    1. 读本目录 ``scene.json`` 拿场景名；
    2. 转编程式调用 ``flash.scenarios.cli.main(["run", name, *argv])``
       —— 策略校验、目标判定（resolve_target）、产物回收全部复用
       CLI 的一份实现（R-SCENE-02/03/04 合规：本模块无任何内联
       wsl/bash/sbatch 细节，无场景策略表）。

★ SNB 场景同样经此路径 —— ``SNB_POLICY`` 的"禁本地"在 CLI 内真实
  生效（本地误跑会被策略拒绝并给出 forbid_reason，属防呆特性）；
  超算上原脚本 ``python SNBOneCH_m.py all ...`` 直跑路径不变。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Sequence

__all__ = ["run_from_dir"]

_MANIFEST_NAME = "scene.json"


def run_from_dir(scene_dir: Path, argv: Sequence[str] = ()) -> int:
    """从场景目录启动：读 ``scene.json`` → 复用 CLI ``run`` 一条路径。

    Args:
        scene_dir: 场景目录（含 ``scene.json``）。
        argv: 传给 CLI 的额外参数（如 ``["--mode", "wsl"]``）。

    Returns:
        进程退出码（CLI main 的返回值）。
    """
    scene_dir = Path(scene_dir).resolve()
    mf = scene_dir / _MANIFEST_NAME
    if not mf.is_file():
        print(f"[X] {scene_dir} 缺 {_MANIFEST_NAME} —— 去注册化场景三件套"
              f"（目录 + scene.json + run.py）不完整", file=sys.stderr)
        return 2
    try:
        meta = json.loads(mf.read_text(encoding="utf-8"))
        name = str(meta["name"]).strip()
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[X] {mf} 非法（缺 name 或 JSON 损坏）: {e}", file=sys.stderr)
        return 2
    if not name:
        print(f"[X] {mf}: name 为空", file=sys.stderr)
        return 2

    from flash.scenarios.cli import main

    return int(main(["run", name, *argv]) or 0)
