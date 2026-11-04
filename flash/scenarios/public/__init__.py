"""公开分享的典型示例场景包。

本包收录可对外分发的示例（不依赖私有分区的数据/表），按物理专题分组：

  center_evolution/      中心演化 —— ch_center (CH 靶 1D 激光)
  sandwich/              薄层三明治 —— thin_layer_sandwich / grad_dens_sandwich

★ 2026-11-04 任意移动改造：不再硬编码子包清单（清单本身就是位置绑定，
  且占位名会产生告警噪声）—— 改为枚举本目录下实际存在的子包；
  某个专题在裁剪过的发布包里缺失时不应拖垮其余示例。

★ 每个子包内部自行负责注册（见各子包 __init__.py），本文件只做容错导入。
"""

from __future__ import annotations

import warnings
from pathlib import Path

_HERE = Path(__file__).resolve().parent

for _child in sorted(p for p in _HERE.iterdir() if p.is_dir()):
    if _child.name.startswith(("_", ".")) or _child.name == "__pycache__":
        continue
    _sub = _child.name
    try:
        __import__(f"flash.scenarios.public.{_sub}")
    except ImportError as _e:  # pragma: no cover
        warnings.warn(f"公开示例包 public.{_sub} 加载失败: {_e}", stacklevel=2)
