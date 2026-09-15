#!/usr/bin/env python
"""①②③ 抽取 doc/docx/pdf 格式文档为纯文本（存 docs/extracted/）

用法::

    <venv>/Scripts/python.exe scripts/01_extract_docs.py

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
    raise SystemExit(main([["extract-docs"]]))
