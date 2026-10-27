# -*- coding: utf-8 -*-
"""discovery.py — 约定式场景发现器（**零注册**地基，2026-10-27）
════════════════════════════════════════════════════════════════════════════

★ 设计目标（去注册化）

  新增一个场景 = 建目录 + 写物理配置 + 落一份 ``scene.json``，
  **不改** 父包 ``__init__``、不改 ``catalog.CATALOG``、不调
  ``registry.register()``。

★ 为什么是「文件扫描」而不是 ``pkgutil.walk_packages``

  walk 发现场景必须 import 场景包才能拿到 ``scenario`` 实例 ⇒ 会立刻
  触发 h5py/numpy 等重依赖，摧毁 CLI ``list`` 的惰性语义（B0/C4），
  private 分区 import 失败还会产生告警噪声。
  纯文件扫描（``Path.glob("*/scene.json")``）零 import、天然懒加载、
  private 可缺、对裁剪发布包免疫。场景对象本身仍惰性 import
  （module/attr 写在 manifest 里，即原 ``register()`` 三要素）。

★ manifest 放置与基准目录

  只扫 ``flash/scenarios/{public,flash_demo,private}`` 一级场景目录；
  基准目录取 ``Path(__file__).parent``（**不是** ``repo_root()``）——
  wheel 安装环境下仓库根可能不存在，但 ``flash/scenarios`` 包一定在。
  ``private`` 缺失静默跳过（克隆/发布环境允许缺）。

★ policy 用符号引用

  manifest 里写 ``"policy": "public_scene"|"snb"|"default"``，
  本模块映射到 ``flash.scenarios.core.policies`` 的策略常量
  （策略对象仍住场景层 ⇒ R-LAYER-03 合规）。

用法::

    from flash.scenarios.core.discovery import iter_scene_manifests

    for meta in iter_scene_manifests():
        print(meta.name, meta.kind, meta.module)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Tuple

__all__ = [
    "SceneMeta",
    "ManifestError",
    "load_manifest",
    "iter_scene_manifests",
    "POLICY_ALIASES",
    "SCENARIO_BASE",
]

#: 场景分区（private 可缺）
_PARTITIONS = ("public", "flash_demo", "private")
_OPTIONAL_PARTITIONS = ("private",)

#: manifest 固定文件名
MANIFEST_NAME = "scene.json"

#: policy 符号 → 策略常量（场景层唯一归属，延迟 import 防环）
POLICY_ALIASES = {
    "default": "DEFAULT_POLICY",
    "public_scene": "PUBLIC_SCENE_POLICY",
    "snb": "SNB_POLICY",
}

#: 合法 runner kind 与其必填字段
_KIND_REQUIRED = {
    "engine": ("module", "attr"),
    "main": ("module",),
    "script": ("script",),
}

#: registry 需要声明式场景对象 ⇒ main 型可选带 ``attr``（如 ch_center
#: 同时维护一个 SimulationScenario 供引擎/MCP 使用）。


class ManifestError(ValueError):
    """scene.json 结构/内容非法。"""


@dataclass(frozen=True)
class SceneMeta:
    """一个场景的声明式元数据（来自 ``scene.json``）。"""

    name: str
    kind: str                       # engine | main | script
    description: str = ""
    aliases: Tuple[str, ...] = ()
    policy: str = "default"         # 符号引用（POLICY_ALIASES 的键）
    module: str = ""                # engine/main: 场景模块路径
    attr: str = ""                  # engine: scenario 实例属性名
    attr_module: str = ""           # 场景对象所在模块（空 = 同 module）。
                                    # ★ ch_center 的 main() 在 laserslab 模块、
                                    #   scenario 实例在包 __init__ ⇒ 两处不同。
    script: str = ""                # script: 脚本相对仓库根路径
    sim_name: str = ""
    basenm: str = ""
    default_args: Tuple[str, ...] = ()
    source: str = ""                # manifest 文件绝对路径（诊断用）
    extra: Dict = field(default_factory=dict)   # hpc / nproc_default 等预留节

    def policy_object(self):
        """解析 policy 符号 → 策略常量（延迟 import 防环）。"""
        from flash.flash_run.execution import DEFAULT_POLICY
        from flash.scenarios.core.policies import PUBLIC_SCENE_POLICY, SNB_POLICY
        return {
            "default": DEFAULT_POLICY,
            "public_scene": PUBLIC_SCENE_POLICY,
            "snb": SNB_POLICY,
        }[self.policy]


def scenario_base() -> Path:
    """scenarios 包目录（发现基准）。

    ★ 本模块住 ``scenarios/core/`` ⇒ 分区（public/…）在**上一级**。
    """
    return Path(__file__).resolve().parent.parent


# 兼容别名（文档/测试用）
SCENARIO_BASE = scenario_base


def load_manifest(path: Path) -> SceneMeta:
    """读取并校验一份 ``scene.json``。

    Raises:
        ManifestError: 结构/内容非法（缺必填、kind 字段不匹配、
            policy 符号未知等）。
    """
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ManifestError(f"{path}: JSON 解析失败: {e}") from e
    if not isinstance(raw, dict):
        raise ManifestError(f"{path}: 顶层必须是对象")

    # 必填字段
    for key in ("name", "kind"):
        if not str(raw.get(key) or "").strip():
            raise ManifestError(f"{path}: 缺必填字段 '{key}'")
    name, kind = str(raw["name"]).strip(), str(raw["kind"]).strip()

    if kind not in _KIND_REQUIRED:
        raise ManifestError(
            f"{path}: kind='{kind}' 非法；允许: {', '.join(_KIND_REQUIRED)}")

    # kind 与字段匹配
    for req in _KIND_REQUIRED[kind]:
        if not str(raw.get(req) or "").strip():
            raise ManifestError(f"{path}: kind='{kind}' 需要字段 '{req}'")

    # policy 符号合法
    policy = str(raw.get("policy") or "default").strip()
    if policy not in POLICY_ALIASES:
        raise ManifestError(
            f"{path}: policy='{policy}' 未知；允许: {', '.join(POLICY_ALIASES)}")

    aliases = tuple(str(a).strip() for a in raw.get("aliases") or () if str(a).strip())
    default_args = tuple(str(a) for a in raw.get("default_args") or ())

    known_extra = {"hpc", "nproc_default"}
    extra = {k: v for k, v in raw.items()
             if k not in {"name", "kind", "description", "aliases", "policy",
                          "module", "attr", "attr_module", "script", "sim_name",
                          "basenm", "default_args"} and k in known_extra}
    unknown = {k for k in raw if k not in known_extra and k not in
               {"name", "kind", "description", "aliases", "policy", "module",
                "attr", "attr_module", "script", "sim_name", "basenm",
                "default_args"}}
    if unknown:
        raise ManifestError(f"{path}: 未知字段: {', '.join(sorted(unknown))}")

    return SceneMeta(
        name=name, kind=kind,
        description=str(raw.get("description") or ""),
        aliases=aliases, policy=policy,
        module=str(raw.get("module") or ""), attr=str(raw.get("attr") or ""),
        attr_module=str(raw.get("attr_module") or ""),
        script=str(raw.get("script") or ""),
        sim_name=str(raw.get("sim_name") or ""),
        basenm=str(raw.get("basenm") or ""),
        default_args=default_args,
        source=str(path), extra=extra,
    )


def iter_scene_manifests(bases: Tuple[Path, ...] = ()) -> Iterator[SceneMeta]:
    """扫描场景分区，产出全部合法 ``SceneMeta``。

    ★ 校验失败（非法 manifest）**不吞** —— 静默跳过会把"场景消失"变成
      谜题；重复 name/alias 同样显式报错。

    Args:
        bases: 覆盖扫描基准（测试注入用）；默认 ``scenario_base()``。
    """
    base_dirs = tuple(bases) if bases else (scenario_base(),)
    seen_names: Dict[str, str] = {}
    seen_aliases: Dict[str, str] = {}

    metas: List[SceneMeta] = []
    for base in base_dirs:
        for part in _PARTITIONS:
            part_dir = base / part
            if not part_dir.is_dir():
                if part not in _OPTIONAL_PARTITIONS:
                    # 随发布包分区的缺失是打包缺陷，但发现器不做 import，
                    # 交给 warm_registry/cli 的既有报错路径 —— 这里跳过即可。
                    continue
                continue
            # ★ 场景目录深度不一（ch_center 在 2 级、sandwich 3 级、
            #   SNB 4 级）⇒ 必须递归扫，不能只看一层。
            # ★ 一目录多场景（2026-10-27）：triplet 族（VTi/TiTi/CHTi…）
            #   同目录含 3 个变体 ⇒ 支持 ``scene.<名>.json`` 命名。
            for mf in sorted(part_dir.rglob("scene*.json")):
                meta = load_manifest(mf)
                # name/alias 全局唯一
                for key in (meta.name, *meta.aliases):
                    table, what = ((seen_names, "场景名") if key == meta.name
                                   else (seen_aliases, "别名"))
                    if key in seen_names or key in seen_aliases:
                        prev = seen_names.get(key) or seen_aliases.get(key)
                        raise ManifestError(
                            f"{mf}: {what} '{key}' 与 {prev} 重复")
                    if key == meta.name:
                        seen_names[key] = str(mf)
                    else:
                        seen_aliases[key] = str(mf)
                metas.append(meta)

    # 稳定顺序：按 name（分区顺序无业务含义，private 先于 public 纯属字母序）
    metas.sort(key=lambda m: m.name)
    yield from metas
