#!/usr/bin/env python
"""② matter++ 全量文件清单与目录画像

用法::

    <venv>/Scripts/python.exe scripts/02_inventory.py

本文件只是薄包装；真正的实现都在 ``eosop_pro`` 包内（便于单测与复用）。
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eosop_pro.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main([["inventory"]]))
