"""eosop_pro —— Multi1D++ ``matter++`` EOS/opacity 数据解析与统一网格 HDF5 导出。"""

from __future__ import annotations

__version__ = "0.1.0"

# R0 兜底：让 ``from eosop_pro import config`` 在 config 迁入 core/ 后继续可用。
from .core import config  # noqa: F401,E402

__all__ = ["__version__", "config"]
