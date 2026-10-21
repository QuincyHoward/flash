"""公开分享的典型示例场景包。

本包收录可对外分发的示例（不依赖私有分区的数据/表），按物理专题分组：

  center_evolution/      中心演化 —— ch_center (CH 靶 1D 激光)
  sandwich/              薄层三明治 —— thin_layer_sandwich / grad_dens_sandwich
  collision_compression/ 对撞压缩 (占位, 场景在 private 分区)
  plasma_preparation/    等离子体制备 (占位, 待补充)

★ 每个子包内部自行负责注册（见各子包 __init__.py），本文件只做容错导入：
  某个专题在裁剪过的发布包里缺失时不应拖垮其余示例。
"""

from __future__ import annotations

import warnings

for _sub in ("center_evolution", "collision_compression",
             "plasma_preparation", "sandwich"):
    try:
        __import__(f"flash.scenarios.public.{_sub}")
    except ImportError as _e:  # pragma: no cover
        warnings.warn(f"公开示例包 public.{_sub} 加载失败: {_e}", stacklevel=2)
