"""对撞压缩物理专题 — collision_compression 场景包

本包包含以下场景 (按分享属性区分):

【公开场景 — 随包分发】
  (暂无; 预留)

【私有场景 — 仅本地使用, 不随包分发】
  thin_layer_sandwich   (Si/Al 三层靶)   — 见 .gitignore PRIVATE 分区
  grad_dens_sandwich    (HE-CH-Si-CH-HE) — 见 .gitignore PRIVATE 分区

私有场景通过 try/except 导入: 本地工作区存在时正常注册;
克隆/发布环境缺失时优雅跳过, 保证公共包可独立导入。
"""
from __future__ import annotations

import importlib
import warnings


def _try_import_private(mod_name: str):
    """尝试导入私有场景模块, 缺失时警告并跳过。"""
    try:
        importlib.import_module(f".{mod_name}", __name__)
        return True
    except ImportError as e:
        warnings.warn(
            f"私有场景 '{mod_name}' 未安装 (仅本地使用, 不随包分发): {e}",
            stacklevel=2,
        )
        return False


# 私有场景: thin_layer_sandwich (Si/Al 三层靶)
_tls_ok = _try_import_private("thin_layer_sandwich")

# 私有场景: grad_dens_sandwich (HE-CH-Si-CH-HE)
_gds_ok = _try_import_private("grad_dens_sandwich")
