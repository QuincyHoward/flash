"""中心演化系列 — ch_center (CH 靶中心演化)

ch_center 依赖私有场景 thin_layer_sandwich 提供的 `interpolator` 模块
(见 .gitignore PRIVATE 分区, 不随包分发)。因此此处采用与
collision_compression/__init__.py 相同的容错导入策略:
本地工作区存在时正常注册; 克隆/发布环境缺失时优雅跳过,
保证公共包可独立导入。
"""
from __future__ import annotations

import warnings

try:
    from . import ch_center  # noqa: F401

    _ch_center_ok = True
except ImportError as e:  # pragma: no cover - 依赖私有场景时才触发
    warnings.warn(
        f"场景 'ch_center' 未加载 (依赖私有 interpolator, 不随包分发): {e}",
        stacklevel=2,
    )
    _ch_center_ok = False
