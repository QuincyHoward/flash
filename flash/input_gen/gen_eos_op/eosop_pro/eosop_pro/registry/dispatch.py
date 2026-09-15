"""阶段 A 分派器 —— 按**声明式**候选族依次尝试解析，全程留痕。

要点
----
* 候选族来自 :mod:`declared_types`（扩展名 / 路径 / 命名 token / 注册表 / 伴随注释）。
* 按候选顺序依次尝试；**成功即停**，并把「第几个候选成功」记进 ``dispatch_rule``。
* ``.feos`` 的第一候选 ``feos_native`` 会因为计数守恒失败而回退到
  ``multi_inverted_eos``（``mat_Al-1.0/AL_eos.feos`` 与 ``AL_eos`` 字节相同，
  是"名实不符"的经典案例）—— 回退**不是猜测**，而是"按声明候选顺序尝试"，
  且完整记录在案。
* 每个文件产出一条 :class:`ParseSnapshot`；mismatch/异常**不静默**。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .. import config
from ..core import textio
from ..core.byteclass import classify_file
from ..core.hashing import sha256_file
from ..core.snapshot import ParseSnapshot, Stopwatch, utc_mtime
from ..parsers import (
    coldopacity as p_coldopacity,
    feos_aux as p_feos_aux,
    feos_native as p_feos_native,
    feos_tabdata as p_feos_tabdata,
    generic_curve as p_generic_curve,
    hugoniot as p_hugoniot,
    hyades_eos as p_hyades,
    ionmix as p_ionmix,
    ledcop_atomic as p_ledcop_atomic,
    ledcop_zeff as p_ledcop_zeff,
    mpqeos as p_mpqeos,
    multi_inverted_eos as p_f1,
    multi_opacity as p_f2,
    snop_input as p_snop_input,
)
from . import declared_types as dt_mod
from .annotation_store import AnnotationStore
from .declared_types import DeclaredType
from .material import MaterialRegistry

__all__ = ["FAMILY_PARSERS", "parse_declared", "ParseOutcome"]

#: 声明族 → 解析器的 ``parse_all``
FAMILY_PARSERS: dict[str, Callable[..., list]] = {
    # F1
    "multi_inverted_eos": p_f1.parse_all,
    # F2
    "multi_opacity": p_f2.parse_all,
    # F3（Hyades 布局；opacity 与 sesame_dat 共用同一解析器）
    "hyades_eos": p_hyades.parse_all,
    "hyades_opacity": p_hyades.parse_all,
    "sesame_dat": p_hyades.parse_all,
    # F4
    "mpqeos": p_mpqeos.parse_all,
    "feos_native": p_feos_native.parse_all,
    "feos_tabdata": p_feos_tabdata.parse_all,
    "feos_aux": p_feos_aux.parse_all,
    # F5
    "ledcop_atomic": p_ledcop_atomic.parse_all,
    "ledcop_zeff": p_ledcop_zeff.parse_all,
    # F6
    "ionmix": p_ionmix.parse_all,
    "coldopacity": p_coldopacity.parse_all,
    "hugoniot": p_hugoniot.parse_all,
    "snop_input": p_snop_input.parse_all,
    "generic_curve": p_generic_curve.parse_all,
}


class ParseOutcome:
    """一次解析尝试的结果（表 + 快照）。"""

    def __init__(self, tables: list, snapshot: ParseSnapshot) -> None:
        self.tables = tables
        self.snapshot = snapshot

    @property
    def ok(self) -> bool:
        return bool(self.tables) and self.snapshot.is_ok


def _unit_hint_for(rel: str, store: AnnotationStore | None) -> str | None:
    """T 轴单位的**声明**来源：文件名模式提示 > 伴随文件单位表。"""
    if store is None:
        return None
    hint = store.unit_hint_for(rel)
    if hint:
        return hint
    units = store.merged_units(rel)
    return units.get("T") or units.get("group_bound")


def _ng_hint_for(rel: str, store: AnnotationStore | None) -> int | None:
    if store is None:
        return None
    for ann in store.for_file(rel):
        ng = ann.dims.get("NG")
        if ng:
            return ng
    return None


def parse_declared(relpath: str, declared: DeclaredType, *,
                   registry: MaterialRegistry | None = None,
                   store: AnnotationStore | None = None,
                   include_multigroup: bool = False) -> ParseOutcome:
    """按声明候选族依次尝试解析 ``relpath``。"""
    abs_path = config.MATTER_DIR / relpath
    sw = Stopwatch()

    snap = ParseSnapshot(
        relpath=relpath,
        abs_path=str(abs_path),
        declared_type=declared.family,
        dispatch_rule=declared.source,
        size_bytes=abs_path.stat().st_size if abs_path.exists() else 0,
        mtime_utc=utc_mtime(abs_path),
    )

    if declared.is_skipped:
        snap.status = "skipped_non_numeric"
        snap.skipped_reason = declared.evidence
        snap.elapsed_ms = sw.ms
        return ParseOutcome([], snap)

    if declared.is_unresolved:
        snap.status = "unrecognized"
        snap.note("no declared family candidates")
        snap.elapsed_ms = sw.ms
        return ParseOutcome([], snap)

    # 字节层判定（含 NUL 一票否决 / 非文本一票转跳过）
    try:
        bc = classify_file(abs_path)
        snap.encoding_used = bc.encoding or ""
        snap.newline_style = bc.newline
        if bc.kind != "text":
            # 二进制/混合 → 登记为**跳过**（附字节层证据），而不是"错误"。
            # 例：``Thumbs.db``、``*.xlsx``、含重音字符的长标题文件。
            snap.status = "skipped_non_numeric"
            snap.skipped_reason = f"byteclass: {bc.describe()}"
            snap.note(f"byteclass: {bc.describe()}")
            snap.elapsed_ms = sw.ms
            return ParseOutcome([], snap)
    except OSError as exc:
        snap.status = "error"
        snap.note(f"byteclass failed: {type(exc).__name__}: {exc}")
        snap.elapsed_ms = sw.ms
        return ParseOutcome([], snap)

    snap.sha256 = sha256_file(abs_path)
    unit_hint = _unit_hint_for(relpath, store)
    ng_hint = _ng_hint_for(relpath, store)

    tried: list[str] = []
    for idx, fam in enumerate(declared.families):
        parser = FAMILY_PARSERS.get(fam)
        if parser is None:
            tried.append(f"{fam}(no parser)")
            continue
        tried.append(fam)
        kwargs: dict[str, Any] = {}
        if fam == "multi_opacity":
            # F2 的签名用 `unit_hint`（不是 `unit_hint_T`）
            kwargs["unit_hint"] = unit_hint
            kwargs["ng_hint"] = ng_hint
        elif fam == "ledcop_atomic":
            kwargs["include_multigroup"] = include_multigroup
            kwargs["unit_hint_T"] = unit_hint
        elif fam in ("ledcop_zeff", "hyades_eos", "hyades_opacity", "sesame_dat",
                     "mpqeos", "feos_native", "feos_tabdata", "feos_aux",
                     "ionmix", "coldopacity", "hugoniot", "snop_input",
                     "generic_curve"):
            kwargs["unit_hint_T"] = unit_hint
        try:
            tables = parser(abs_path, relpath, **kwargs)
        except Exception as exc:  # noqa: BLE001 —— 必须记录而非中断
            snap.note(f"candidate[{idx}] {fam} -> {type(exc).__name__}: {exc}")
            continue

        if not tables:
            snap.note(f"candidate[{idx}] {fam} -> empty result")
            continue

        first = tables[0]
        snap.family = fam
        snap.dispatch_rule = (
            f"declared:{declared.source}"
            + (f"->fallback@{idx}:{fam}" if idx else f"->first:{fam}")
        )
        snap.nr = first.nr
        snap.nt = first.nt
        snap.n_numbers_actual = first.n_numbers_seen
        snap.n_numbers_expected = first.n_numbers_expected
        snap.n_groups = first.n_groups
        snap.header_raw = first.header_raw
        snap.layout_rule = first.layout_rule
        snap.unit_source = first.unit_source
        snap.field_width = _width_from(first)
        snap.n_fields_per_line = None
        snap.notes = list(first.notes[:12])
        if len(tables) > 1:
            snap.note(f"文件含 {len(tables)} 张表: {[t.table_key for t in tables]}")
        snap.status = "ok" if first.n_numbers_expected is not None else "ok_unverified"
        snap.finalize()
        snap.elapsed_ms = sw.ms
        return ParseOutcome(tables, snap)

    snap.status = "error"
    snap.dispatch_rule = f"declared:{declared.source}->all-candidates-failed"
    snap.note("tried: " + ", ".join(tried))

    # ── 最后手段：通用列式兜底 ──────────────────────────────────
    # 明确标注为 last-resort（不是声明类型）。非数值文件已由 skip 规则与字节层
    # 过滤掉，所以这里对**所有剩余文本文件**尝试都安全。
    if not relpath.startswith("~"):
        try:
            tables = p_generic_curve.parse_all(abs_path, relpath, unit_hint_T=unit_hint)
        except ValueError as exc:
            snap.status = "skipped_non_numeric"
            snap.skipped_reason = f"no numeric rows ({exc})"
            snap.dispatch_rule += "->last-resort:generic_curve(no-numeric)"
            snap.elapsed_ms = sw.ms
            return ParseOutcome([], snap)
        except Exception as exc:  # noqa: BLE001
            snap.note(f"last-resort generic_curve -> {type(exc).__name__}: {exc}")
        else:
            first = tables[0]
            snap.family = "generic_curve"
            snap.dispatch_rule += "->last-resort:generic_curve"
            snap.nr = first.nr
            snap.nt = first.nt
            snap.n_numbers_actual = first.n_numbers_seen
            snap.n_numbers_expected = first.n_numbers_expected
            snap.header_raw = first.header_raw
            snap.layout_rule = first.layout_rule
            snap.unit_source = first.unit_source
            snap.notes = list(first.notes[:12])
            snap.status = "ok_unverified"
            snap.elapsed_ms = sw.ms
            return ParseOutcome(tables, snap)

    snap.elapsed_ms = sw.ms
    return ParseOutcome([], snap)


def _width_from(table) -> int | None:
    """从 ``layout_rule`` 文本里取回字段宽（F4/MPQeos 会写 ``W=nn``）。"""
    import re
    m = re.search(r"W=(\d+)", table.layout_rule or "")
    return int(m.group(1)) if m else None
