"""``eosopdata`` 共享工具：样品发现 / 跳过语义 / cn4 数据定位。

为什么不写死路径
----------------
``matter++`` 全树 1000+ 文件，且部分是 1.5G 的大目录（已 gitignore）。
测试要能在**不同机器/不同检出**上跑，就必须**惰性发现**样品，
发现不到时明确 ``skip``（返回 ``None``）而不是 FAIL —— 否则测试会因为
"数据不在"而红，掩盖真正的代码缺陷。
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Iterator

#: 全树扫描一次后缓存（避免每个测试都 rglob 1000+ 文件）
_SAMPLE_CACHE: dict[str, Path | None] = {}
_MATTER_FILES: list[Path] | None = None


def repo_root() -> Path:
    """``gen_eos_op`` 仓库根（本文件位于 test/eosopdata/_samples.py）。"""
    return Path(__file__).resolve().parents[3]


def matter_dir() -> Path:
    """``matter++`` 数据根目录。"""
    from eosop_pro import config
    return Path(config.MATTER_DIR)


def cn4_root() -> Path:
    """仓库内自带的 ``.cn4`` 数据目录。"""
    return repo_root() / "eos_op_data"


def tmp_dir() -> Path:
    """测试产物的输出目录：**调用者所在文件夹**下的 ``_out/``（自动创建）。

    落位规则（产物跟测试走，便于人工核查）：

    * ``step01_cn4/``    的测试 -> ``step01_cn4/_out/``
    * ``step02_families/`` 的 -> ``step02_families/_out/``
    * ``step03_transcn4/`` 的 -> ``step03_transcn4/_out/``

    历史：2026-09-15 前为集中式 ``test/_tmp/plots`` —— 产物与测试文件夹
    分离，人工核查不便；现为按调用者定位的就近输出。
    """
    import inspect
    frame = inspect.stack()[1]
    caller = Path(frame.filename).resolve().parent
    d = caller / "_out"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _all_matter_files() -> list[Path]:
    """``matter++`` 全树文件（缓存；跳过 gitignore 的大目录）。"""
    global _MATTER_FILES
    if _MATTER_FILES is None:
        root = matter_dir()
        if not root.is_dir():
            _MATTER_FILES = []
        else:
            out: list[Path] = []
            for dirpath, dirnames, filenames in os.walk(root):
                # 大目录/缓存目录直接剪枝，避免扫描 1.5G 子树
                dirnames[:] = [
                    d for d in dirnames
                    if d != "__pycache__" and d != ".git"
                ]
                for fn in filenames:
                    out.append(Path(dirpath) / fn)
            _MATTER_FILES = out
    return _MATTER_FILES


def find_first(patterns: tuple[str, ...],
               *, max_candidates: int = 400) -> Path | None:
    """在 ``matter++`` 全树里找**第一个能通过 ``predicate`` 的**文件。

    纯按名字匹配，不做内容判断（内容判断交给调用方）。
    """
    key = "|".join(patterns)
    if key in _SAMPLE_CACHE:
        return _SAMPLE_CACHE[key]
    import fnmatch
    hit: Path | None = None
    n = 0
    for f in sorted(_all_matter_files()):
        for pat in patterns:
            if fnmatch.fnmatch(f.name, pat):
                hit = f
                break
        if hit is not None:
            break
        n += 1
        if n > max_candidates * 20:
            break
    _SAMPLE_CACHE[key] = hit
    return hit


def find_parseable(family: str, patterns: tuple[str, ...],
                   limit: int = 80) -> tuple[Path, list] | None:
    """找到第一个**能被 ``family`` 解析器成功解析**的文件。

    Returns:
        ``(path, tables)`` 或 ``None``（找不到/全部解析失败 -> 调用方 skip）
    """
    hits = find_parseable_many(family, patterns, max_files=1, limit=limit)
    return hits[0] if hits else None


def find_parseable_many(family: str, patterns: tuple[str, ...],
                        max_files: int = 3,
                        limit: int = 80) -> list[tuple[Path, list]] | None:
    """找**前 ``max_files`` 个**能被 ``family`` 解析器成功解析的文件。

    用户 2026-09-15 规约：step02 逐类型核查需要覆盖**多个**数据文件，
    而不是只看第一个样品（此前 ``find_parseable`` 只返回首个 —— 全树
    29 个 ``.feos`` 只碰了 1 个）。

    Returns:
        ``[(path, tables), ...]``（至少 1 个时）；一个都找不到 ->
        ``None``（调用方 skip，惰性发现语义不变）。
    """
    key = f"parsemany::{family}::{patterns}::{max_files}"
    if key in _SAMPLE_CACHE:
        v = _SAMPLE_CACHE[key]
        return v if v is None or isinstance(v, list) else None

    from eosop_pro.registry.dispatch import FAMILY_PARSERS
    fn = FAMILY_PARSERS.get(family)
    if fn is None:
        _SAMPLE_CACHE[key] = None
        return None

    import fnmatch
    tried = 0
    hits: list[tuple[Path, list]] = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for f in sorted(_all_matter_files()):
            if len(hits) >= max_files:
                break
            if not any(fnmatch.fnmatch(f.name, p) for p in patterns):
                continue
            tried += 1
            if tried > limit:
                break
            try:
                tables = fn(str(f))
            except Exception:                                  # noqa: BLE001
                continue
            if tables:
                hits.append((f, list(tables)))
    _SAMPLE_CACHE[key] = hits or None
    return hits or None


def find_all_matching(patterns: tuple[str, ...]) -> list[Path]:
    """全部按**名字**匹配的 ``matter++`` 文件（不做解析过滤，全量收集用）。

    用户 2026-09-15 第十一轮规约：``source_data/`` 要收全同一类型的
    **全部**文件（含解析失败者 —— 恰恰是它们最需要人工判断）；
    绘图/解析仍走 :func:`find_parseable_many` 的 ``max_files`` 护栏，
    两者解耦。
    """
    import fnmatch
    return [f for f in sorted(_all_matter_files())
            if any(fnmatch.fnmatch(f.name, p) for p in patterns)]


#: cn4 单样品测试（绘图 / 路径 / 提取）的**默认首选样品**（用户指定 2026-09-15）。
#: 存在即直接采用，不参与体积排序；不存在时 :func:`first_cn4` 回退旧逻辑。
PREFERRED_CN4 = "Z06_0.50-Z01_0.50-20260708_0850.cn4"


def first_cn4() -> Path | None:
    """仓库内默认 ``.cn4`` 样品。

    选择顺序：

    1. :data:`PREFERRED_CN4`（用户指定的默认绘图样品，存在即用）；
    2. 回退：``Gen_eos_op_data`` 下的生成数据中体积适中者（~580KB），
       避免超大文件拖慢测试。
    """
    key = "first_cn4"
    if key in _SAMPLE_CACHE:
        return _SAMPLE_CACHE[key]
    root = cn4_root()
    if root.is_dir():
        pref = next(root.rglob(PREFERRED_CN4), None)
        if pref is not None and pref.is_file():
            _SAMPLE_CACHE[key] = pref
            return pref
    cands: list[Path] = sorted(root.rglob("*.cn4")) if root.is_dir() else []
    # 优先选体积适中的（生成数据 ~580KB），避免超大文件拖慢测试
    cands.sort(key=lambda p: (p.stat().st_size if p.exists() else 0))
    pick = None
    for c in cands:
        sz = c.stat().st_size
        if 1000 < sz < 5_000_000:
            pick = c
            break
    if pick is None and cands:
        pick = cands[0]
    _SAMPLE_CACHE[key] = pick
    return pick


def cn4_samples(n: int = 3) -> list[Path]:
    """返回至多 ``n`` 个不同材料的 ``.cn4``（用于跨材料一致性断言）。"""
    root = cn4_root()
    if not root.is_dir():
        return []
    out: list[Path] = []
    seen_dirs: set[Path] = set()
    for c in sorted(root.rglob("*.cn4")):
        d = c.parent
        if d in seen_dirs:
            continue
        seen_dirs.add(d)
        out.append(c)
        if len(out) >= n:
            break
    return out


def iter_matter(pattern: str, limit: int = 20) -> Iterator[Path]:
    """按 glob 模式遍历 ``matter++``（缓存支撑）。"""
    import fnmatch
    n = 0
    for f in sorted(_all_matter_files()):
        if fnmatch.fnmatch(f.name, pattern):
            yield f
            n += 1
            if n >= limit:
                return
