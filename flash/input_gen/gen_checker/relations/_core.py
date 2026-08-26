"""
relations._core — 文件内在关联检查框架核心
════════════════════════════════════════════════

提供可扩展的"注册式规则引擎"：
  - RelationResult : 单个关联检查项的结果
  - RelationContext: 跨规则共享的解析缓存（.par / Config / F90 / 脚本）
  - relation_rule  : 装饰器，把规则函数注册进 REGISTRY
  - REGISTRY       : 规则注册表（id -> rule func）

扩展方式见 check_relations.py 头注释与 GEN_CHECKER_GUIDE.md「如何扩展自定义关联」。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

__all__ = [
    "RelationResult",
    "RelationContext",
    "relation_rule",
    "REGISTRY",
]

# 规则 id -> 规则函数（由 relation_rule 装饰器填充）
REGISTRY: Dict[str, Callable[..., "RelationResult"]] = {}


@dataclass
class RelationResult:
    """一条内在关联检查的结果。

    Attributes:
        rule_id:  规则唯一标识（与 REGISTRY key 一致）
        name:     规则的简短中文名
        status:   True=通过 / False=失败 / None=跳过（文件缺失无法检查）
        message:  人可读的结论描述
        details:  附加结构化信息（关键文件名/行号/缺失清单等）
    """
    rule_id: str
    name: str
    status: Optional[bool]
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RelationContext:
    """一次关联检查的共享上下文。

    各规则需要解析同一份 .par / Config / F90 文件，为避免重复解析，把解析结果
    缓存在这里。所有解析方法都有 `_parsed` 缓存，首次调用后复用。

    Attributes:
        sim_dir:  仿真目录（含 7 个关键文件的目录）
        verbose:  是否输出冗长信息
    """
    sim_dir: Path
    verbose: bool = False
    _cache: Dict[str, Any] = field(default_factory=dict)

    # ── 缓存工具 ────────────────────────────────────
    def _cached(self, key: str, loader: Callable[[], Any]) -> Any:
        if key not in self._cache:
            self._cache[key] = loader()
        return self._cache[key]

    def file(self, name: str) -> Optional[Path]:
        """返回目录下第一个匹配 name（支持 glob）的文件，不存在返回 None。"""
        hits = list(self.sim_dir.glob(name))
        return hits[0] if hits else None

    # ── 各文件解析（带缓存）────────────────────────
    def par_path(self) -> Optional[Path]:
        return self._cached("par_path", lambda: self.file("*.par"))

    def par_params(self) -> Dict[str, str]:
        """解析 .par 为 {参数名: 原始值字符串} 字典。"""
        def _load() -> Dict[str, str]:
            p = self.par_path()
            if p is None:
                return {}
            out: Dict[str, str] = {}
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
                if m:
                    out[m.group(1)] = m.group(2).strip()
            return out
        return self._cached("par_params", _load)

    def config_lines(self) -> List[str]:
        def _load() -> List[str]:
            c = self.file("Config")
            if c is None:
                return []
            return c.read_text(encoding="utf-8", errors="replace").splitlines()
        return self._cached("config_lines", _load)

    def config_datafiles(self) -> List[str]:
        """Config 中 DATAFILES 声明的所有文件名。"""
        def _load() -> List[str]:
            return [ln.split()[-1] for ln in self.config_lines()
                    if ln.strip().upper().startswith("DATAFILES") and len(ln.split()) >= 2]
        return self._cached("config_datafiles", _load)

    def config_species(self) -> List[str]:
        """Config 中 SPECIES 声明的所有物种名。"""
        def _load() -> List[str]:
            return [ln.split()[-1] for ln in self.config_lines()
                    if ln.strip().upper().startswith("SPECIES") and len(ln.split()) >= 2]
        return self._cached("config_species", _load)

    def config_parameters(self) -> List[str]:
        """Config 中 PARAMETER 声明的所有参数名。"""
        def _load() -> List[str]:
            names: List[str] = []
            for ln in self.config_lines():
                s = ln.strip().upper()
                if s.startswith("PARAMETER "):
                    parts = ln.split()
                    if len(parts) >= 2:
                        names.append(parts[1])
            return names
        return self._cached("config_parameters", _load)

    def simulation_f90(self) -> Dict[str, str]:
        """Simulation_*.F90 文件内容字典 {文件名: 文本}。"""
        def _load() -> Dict[str, str]:
            out: Dict[str, str] = {}
            for f in self.sim_dir.glob("Simulation_*.F90"):
                out[f.name] = f.read_text(encoding="utf-8", errors="replace")
            return out
        return self._cached("simulation_f90", _load)

    def run_scripts(self) -> Dict[str, str]:
        """目录下 run_flash.sh / submit_flash.sh 等脚本内容 {文件名: 文本}。"""
        def _load() -> Dict[str, str]:
            out: Dict[str, str] = {}
            for pat in ("run_flash.sh", "run_flash.bat", "submit_flash.sh", "submit_flash.slurm"):
                for f in self.sim_dir.glob(pat):
                    out[f.name] = f.read_text(encoding="utf-8", errors="replace")
            return out
        return self._cached("run_scripts", _load)

    def makefile_lines(self) -> List[str]:
        def _load() -> List[str]:
            m = self.file("Makefile")
            if m is None:
                return []
            return m.read_text(encoding="utf-8", errors="replace").splitlines()
        return self._cached("makefile_lines", _load)


def relation_rule(rule_id: str, name: str):
    """把规则函数注册进 REGISTRY 的装饰器。

    Args:
        rule_id: 规则唯一标识
        name:    规则的简短中文名

    用法:
        @relation_rule("par_cn4_exist", ".par 引用的 .cn4 存在于磁盘")
        def rule(ctx: RelationContext) -> RelationResult:
            ...
    """
    def deco(fn: Callable[[RelationContext], RelationResult]):
        def wrapper(ctx: RelationContext) -> RelationResult:
            return fn(ctx)
        wrapper.rule_id = rule_id          # type: ignore[attr-defined]
        wrapper.rule_name = name           # type: ignore[attr-defined]
        REGISTRY[rule_id] = wrapper
        return wrapper
    return deco
