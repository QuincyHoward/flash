"""
relations — 文件内在关联检查规则子包
════════════════════════════════════

导入本包即完成所有内置规则的注册（写进 _core.REGISTRY）。

扩展自定义关联：新增一个规则模块（或用 @relation_rule 装饰新函数），
然后在本文件末尾 import 它即可自动纳入 run_all()。无需改动主脚本逻辑。
"""

from __future__ import annotations

from ._core import (REGISTRY, RelationContext, RelationResult, relation_rule)

# 导入规则模块以触发 @relation_rule 注册
from . import rules_reference       # noqa: F401  A类 规则 1-3
from . import rules_parameter       # noqa: F401  B类 规则 4-6
from . import rules_dimension       # noqa: F401  C类 规则 7-11
from . import rules_script          # noqa: F401  D类 规则 12-14

__all__ = ["REGISTRY", "RelationContext", "RelationResult", "relation_rule"]
