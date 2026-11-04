# -*- coding: utf-8 -*-
"""discovery.py — 约定式场景发现器（**零注册**地基，2026-10-27；2026-11-04 任意移动改造）
════════════════════════════════════════════════════════════════════════════

★ 设计目标（去注册化）

  新增一个场景 = 建目录 + 写物理配置 + 落一份 ``scene.json``，
  **不改** 父包 ``__init__``、不改 ``catalog.CATALOG``、不调
  ``registry.register()``。

★ 为什么是「文件扫描」而不是 ``pkgutil.walk_packages``

  walk 发现场景必须 import 场景包才能拿到 ``scenario`` 实例 ⇒ 会立刻
  触发 h5py/numpy 等重依赖，摧毁 CLI ``list`` 的惰性语义（B0/C4），
  private 分区 import 失败还会产生告警噪声。
  纯文件扫描（``Path.rglob("scene*.json")``）零 import、天然懒加载、
  private 可缺、对裁剪发布包免疫。场景对象本身仍惰性 import
  （module/attr 写在 manifest 里，即原 ``register()`` 三要素）。

★ 2026-11-04 任意移动改造（场景收纳整理 P1）

  1. 扫描范围从三个固定分区（public/flash_demo/private）扩大为
     **scenarios 全树** —— 场景目录在 ``flash/scenarios/`` 内任意层级、
     任意归类（含新建分类目录、跨分区移动）都能被发现；
  2. 新增**排除规则**：运行产物/缓存/备份目录内的 ``scene*.json``
     副本不会误判为场景；
  3. manifest 的 ``module``/``attr_module``/``script`` 与 ``hpc`` 节的
     ``input_rel_dir``/``gen_script`` 支持**三级解析**：

       a. 显式绝对（旧式 ``flash.scenarios.…`` / ``flash/…``）—— 向后
          兼容，原样使用（但场景移动后需同步改写，audit 会标 ERROR）；
       b. 显式相对（以 ``.`` 开头的包路径，如 ``".laserslab1d_local_custom"``；
          以 ``./`` 开头或纯文件名的路径）—— 相对 manifest 所在目录解释，
          **场景随目录移动自动跟随**；
       c. 完全缺省 —— 从 manifest 物理位置自动派生（变体 .py →
          <目录名>.py → 场景包本身）。

     派生失败显式抛 ``ManifestError``，绝不静默。

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
from fnmatch import fnmatch
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

__all__ = [
    "SceneMeta",
    "ManifestError",
    "load_manifest",
    "iter_scene_manifests",
    "POLICY_ALIASES",
    "SCENARIO_BASE",
]

#: manifest 固定文件名
MANIFEST_NAME = "scene.json"

#: 排除目录名（精确匹配）—— 运行产物 / 缓存 / 归档
_EXCLUDE_PARTS = {
    "__pycache__", ".git", "flash_output", "sim_output", "sim_output_plots",
    "logs_archive", "database", "sim_input", "sim_input_si", "results",
}
#: 排除目录名（通配）—— runs_* 产物区 / 备份 / egg-info
_EXCLUDE_GLOBS = ("runs_*", "*_output", "_backup_*", "*.egg-info", "NNNNNN")
#: 排除子树（相对 scenarios 根）—— 框架与共享脚本区不是场景
_EXCLUDE_SUBTREES = ("core", "scripts")

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
    module: str = ""                # engine/main: 场景模块路径（已解析）
    attr: str = ""                  # engine: scenario 实例属性名
    attr_module: str = ""           # 场景对象所在模块（空 = 同 module）。
                                    # ★ ch_center 的 main() 在 laserslab 模块、
                                    #   scenario 实例在包 __init__ ⇒ 两处不同。
    script: str = ""                # script: 脚本相对仓库根路径（已解析）
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

    ★ 本模块住 ``scenarios/core/`` ⇒ 包根在**上一级**。
    """
    return Path(__file__).resolve().parent.parent


# 兼容别名（文档/测试用）
SCENARIO_BASE = scenario_base


def _repo_root_from(base: Path) -> Optional[Path]:
    """从扫描基准向上找仓库根（wheel 安装环境可能不存在 → None）。"""
    for cand in (base, *base.parents):
        if (cand / "pyproject.toml").is_file() and (cand / "start_flash.py").is_file():
            return cand
    return None


def _scene_pkg(scene_dir: Path, base: Path) -> Optional[str]:
    """场景目录 → ``flash.scenarios.<相对路径点分>``；不在 base 下则 None。"""
    try:
        rel = scene_dir.resolve().relative_to(base.resolve())
    except ValueError:
        return None
    return ".".join(("flash.scenarios", *rel.parts))


def _norm(explicit: str) -> str:
    return str(explicit).replace("\\", "/").strip()


def _resolve_module(mf: Path, base: Path, explicit: str, kind: str) -> str:
    """module 三级解析（见模块头注释）。

    Raises:
        ManifestError: 显式相对形式不在 base 下 / 缺省派生失败。
    """
    e = _norm(explicit)
    if e:
        if e.startswith("."):
            # 显式相对：".xxx.yyy" → 场景包子模块；"." → 场景包本身
            pkg = _scene_pkg(mf.parent, base)
            if pkg is None:
                raise ManifestError(
                    f"{mf}: module 相对形式 '.…' 需 manifest 位于扫描基准下")
            tail = e.lstrip("./").replace("/", ".").strip(".")
            return f"{pkg}.{tail}" if tail else pkg
        return e.replace("/", ".")           # 旧式绝对（点分/斜杠兼容）
    # ── 缺省派生（零 import，仅文件存在性探测）──
    d = mf.parent
    stem = mf.stem                            # "scene" 或 "scene.XXX"
    variant = stem.split(".", 1)[1] if "." in stem else ""
    if variant and (d / f"{variant}.py").is_file():
        pkg = _scene_pkg(d, base)
        if pkg:
            return f"{pkg}.{variant}"
    if (d / f"{d.name}.py").is_file():
        pkg = _scene_pkg(d, base)
        if pkg:
            return f"{pkg}.{d.name}"
    if kind == "engine":
        pkg = _scene_pkg(d, base)
        if pkg and (d / "__init__.py").is_file():
            return pkg                        # attr 住包 __init__（grad_dens 模式）
    raise ManifestError(
        f"{mf}: kind='{kind}' 缺 module 且无法从目录派生"
        f"（需 scene 变体 .py / <目录名>.py / 包 __init__.py，或补 module 字段）")


def _resolve_attr_module(mf: Path, base: Path, explicit: str, module: str) -> str:
    """attr_module 解析：缺省 = module 本身（registry 的 ``or`` 语义不变）。"""
    e = _norm(explicit)
    if not e:
        return module
    if e.startswith("."):
        pkg = _scene_pkg(mf.parent, base)
        if pkg is None:
            raise ManifestError(
                f"{mf}: attr_module 相对形式 '.…' 需 manifest 位于扫描基准下")
        tail = e.lstrip("./").replace("/", ".").strip(".")
        return f"{pkg}.{tail}" if tail else pkg
    return e.replace("/", ".")


def _resolve_repo_rel(mf: Path, base: Path, value: str, field: str) -> str:
    """script / hpc.input_rel_dir / hpc.gen_script 的仓库根相对路径解析。

    三级：``./x`` 或纯文件名 → 相对 manifest 目录；``../`` 允许指到场景外
    （仍在仓库内）；旧式 ``flash/…`` 原样（向后兼容）。
    """
    e = _norm(value)
    if not e:
        return e
    if e.startswith(("flash/", "flash\\", "~/")) or Path(e).is_absolute():
        return e.replace("\\", "/")
    if "/" not in e or e.startswith("./") or e.startswith("../"):
        p = (mf.parent / e).resolve()
        repo = _repo_root_from(base)
        if repo is not None:
            try:
                return p.relative_to(repo).as_posix()
            except ValueError:
                raise ManifestError(
                    f"{mf}: {field} 相对路径解析后逃逸仓库根: {e}")
        # wheel 模式（无仓库根）：退化为绝对路径（catalog 的 repo_root()
        # 在该模式下本就无法执行 script 型场景，此处仅为诊断信息可用）
        return p.as_posix()
    return e


def load_manifest(path: Path, base: Optional[Path] = None) -> SceneMeta:
    """读取并校验一份 ``scene.json``（含 module/script/hpc 路径解析）。

    Args:
        path: manifest 文件路径。
        base: 扫描基准（缺省 ``scenario_base()``）；测试注入临时树时传入。

    Raises:
        ManifestError: 结构/内容非法（缺必填、kind 字段不匹配、
            policy 符号未知、路径派生失败等）。
    """
    path = Path(path)
    base = Path(base) if base is not None else scenario_base()
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

    # policy 符号合法
    policy = str(raw.get("policy") or "default").strip()
    if policy not in POLICY_ALIASES:
        raise ManifestError(
            f"{path}: policy='{policy}' 未知；允许: {', '.join(POLICY_ALIASES)}")

    aliases = tuple(str(a).strip() for a in raw.get("aliases") or () if str(a).strip())
    default_args = tuple(str(a) for a in raw.get("default_args") or ())

    known_extra = {"hpc", "nproc_default"}
    unknown = {k for k in raw if k not in known_extra and k not in
               {"name", "kind", "description", "aliases", "policy", "module",
                "attr", "attr_module", "script", "sim_name", "basenm",
                "default_args"}}
    if unknown:
        raise ManifestError(f"{path}: 未知字段: {', '.join(sorted(unknown))}")
    extra = {k: v for k, v in raw.items()
             if k not in unknown and k in known_extra}

    # ★ 2026-11-04: module/attr_module/script/hpc 三级解析（显式绝对兼容 /
    #   显式相对随场景移动 / 缺省派生）。派生失败显式报错。
    #   script 型不需要 module，跳过解析。
    module = (_resolve_module(path, base, str(raw.get("module") or ""), kind)
              if kind in ("main", "engine") else "")
    attr_module = (_resolve_attr_module(
        path, base, str(raw.get("attr_module") or ""), module)
        if module else "")
    script = _resolve_repo_rel(path, base, str(raw.get("script") or ""), "script")

    # kind 与字段匹配（解析后的最终值必须非空）
    for req in _KIND_REQUIRED[kind]:
        final = {"module": module, "attr": str(raw.get("attr") or ""),
                 "script": script}[req]
        if not final.strip():
            raise ManifestError(f"{path}: kind='{kind}' 需要字段 '{req}'")

    # hpc 节的路径字段同样解析（input_rel_dir / gen_script）
    hpc = extra.get("hpc")
    if isinstance(hpc, dict):
        hpc = dict(hpc)
        for hf in ("input_rel_dir", "gen_script"):
            if hf in hpc:
                hpc[hf] = _resolve_repo_rel(path, base, str(hpc[hf]), f"hpc.{hf}")
        extra["hpc"] = hpc

    return SceneMeta(
        name=name, kind=kind,
        description=str(raw.get("description") or ""),
        aliases=aliases, policy=policy,
        module=module, attr=str(raw.get("attr") or ""),
        attr_module=attr_module,
        script=script,
        sim_name=str(raw.get("sim_name") or ""),
        basenm=str(raw.get("basenm") or ""),
        default_args=default_args,
        source=str(path), extra=extra,
    )


def _is_excluded(rel_parts: Tuple[str, ...]) -> bool:
    """manifest 相对路径是否落在排除目录内（产物/缓存/框架子树）。"""
    for part in rel_parts:
        if part in _EXCLUDE_SUBTREES:
            return True
        if part in _EXCLUDE_PARTS:
            return True
        if any(fnmatch(part, pat) for pat in _EXCLUDE_GLOBS):
            return True
    return False


def iter_scene_manifests(bases: Tuple[Path, ...] = ()) -> Iterator[SceneMeta]:
    """扫描 scenarios 全树，产出全部合法 ``SceneMeta``。

    ★ 2026-11-04：扫描范围 = scenarios 包**全树**（不再限定
      public/flash_demo/private 三个分区）—— 场景目录任意移动/归类均可发现；
      排除产物/缓存/备份目录与 core/scripts 框架子树。

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
        for mf in sorted(base.rglob("scene*.json")):
            if not mf.is_file():
                continue
            try:
                rel = mf.parent.resolve().relative_to(base.resolve()).parts
            except ValueError:
                continue
            if _is_excluded(rel):
                continue
            meta = load_manifest(mf, base=base)
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

    # 稳定顺序：按 name（目录顺序无业务含义）
    metas.sort(key=lambda m: m.name)
    yield from metas
