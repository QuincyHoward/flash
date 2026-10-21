"""Sandwich 场景家族 (workspace 收录版)

收录 collision_compression 的两个子场景 (自包含副本):
  - grad_dens_sandwich   — HE-CH-Si-CH-HE 渐变密度 CH
  - thin_layer_sandwich  — Si/CH/He 薄层三层靶 (sim_input_si)

★ 2026-10-21: 本文件原先**不导入子包**，导致两个场景的 `register()`
  从未执行，`list_scenarios()` 里看不到它们（只有 ch_center 出现）。
  现改为与 center_evolution/ 相同的容错导入：某个子场景在裁剪包中缺失
  时只告警，不拖垮另一个。
"""

from __future__ import annotations

import warnings

for _sub in ("grad_dens_sandwich", "thin_layer_sandwich"):
    try:
        __import__(f"flash.scenarios.public.sandwich.{_sub}")
    except ImportError as _e:  # pragma: no cover
        warnings.warn(f"场景 sandwich.{_sub} 未加载: {_e}", stacklevel=2)
