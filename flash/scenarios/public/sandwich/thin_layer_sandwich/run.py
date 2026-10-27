#!/usr/bin/env python
"""场景薄启动器 —— cd 到本目录后: python run.py [--mode auto] [--tmax ...] [--dry-run]

★ 去注册化三件套之一（目录 + scene.json + run.py）；
  全部场景的 run.py 内容逐字节相同，实现在 flash/scenarios/launcher.py。
"""
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _ in range(12):
    if (_HERE / "pyproject.toml").exists():
        break
    _HERE = _HERE.parent
else:
    raise SystemExit("[X] 无法定位仓库根（需含 pyproject.toml）")
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from flash.scenarios.launcher import run_from_dir

raise SystemExit(run_from_dir(Path(__file__).resolve().parent, sys.argv[1:]))
