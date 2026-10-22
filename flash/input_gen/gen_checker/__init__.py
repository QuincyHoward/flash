"""
gen_checker — 依赖检查器包
"""
from .checker import DependencyChecker, CheckResult
from .check_relations import RelationChecker, RelationResult, RelationContext, REGISTRY
from .check_scene_sources import check_scene_sources, SceneViolation, FORBIDDEN_TOKENS

__all__ = [
    "DependencyChecker",
    "CheckResult",
    "RelationChecker",
    "RelationResult",
    "RelationContext",
    "REGISTRY",
    "check_scene_sources",
    "SceneViolation",
    "FORBIDDEN_TOKENS",
]
