"""
兼容壳: layer_tracer_Ti_hpc 的旧 CLI 已并入 layer_tracer_Ti 单入口。

旧 hpc 驱动 (paramiko 分阶段) 已泛化进 flash.scenarios.runner.HpcRunner,
本文件仅保留旧命令入口的等价转发, 避免破坏既有调用习惯。

等价新命令:
  python -m flash.scenarios.private.tracer.layer_tracer_Ti.layer_tracer_Ti <action>
  (action = all/upload/submit/monitor/analyze/download/status)

旧命令映射: gen→upload, submit, monitor, analyze, download
"""

import sys
from pathlib import Path

# ── Bootstrap: 定位 flash 包根目录 ─────────────────────────
_ROOT = Path(__file__).resolve().parent
for _ in range(14):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from flash.scenarios.private.tracer.layer_tracer_Ti.layer_tracer_Ti import main  # noqa: E402

# 旧动作名 → 新动作名
_ACTION_MAP = {
    "gen": "upload",
    "upload": "upload",
    "submit": "submit",
    "monitor": "monitor",
    "analyze": "analyze",
    "download": "download",
    "all": "all",
    "status": "status",
}


def _dispatch(argv: list) -> bool:
    if len(argv) > 1 and argv[1] in _ACTION_MAP:
        argv[1] = _ACTION_MAP[argv[1]]
    return main()


if __name__ == "__main__":
    success = _dispatch(sys.argv)
    sys.exit(0 if success else 1)