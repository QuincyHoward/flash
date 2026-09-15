# -*- coding: utf-8 -*-
"""eosop_pro.guess —— 任意 eosop 数据的"盲读"猜测层（用户 2026-09-15 第十一轮令）。

定位
----
回答两类问题（对**任何**丢进来的 eosop 文本数据文件）：

* **3.1 意义块划分猜测**：这份文件的数值 payload 是几个块？每块是
  多少 ``m×n``？（行宽统计 + 因数分解 + 单调列识别 + 常值/零长跑 +
  数量级跳变 + :mod:`eosop_pro.core.inference` 模板反演，多证据合议）
* **3.2 物理意义/单位猜测**：把文件的块指纹（量级跨度/整值率/单调性/
  符号分布）与**已解析已知族**（cn4/ionmix、hyades、mpqeos 等
  :class:`ParsedTable <eosop_pro.tables.ParsedTable>`）的字段指纹对比，
  给出"疑似某族某字段"的候选（单位取自
  :mod:`eosop_pro.registry.field_checks` 的登记）。

★ 边界（**猜测绝不污染事实**）：本模块的一切输出都是**假设**
（hypothesis / guess），与人工核查的事实字典
:mod:`eosop_pro.registry.field_checks` 严格分离 —— 猜测结果只进
屏幕/报告，**绝不写回**控制字典；报告措辞一律 "guess"（英文 CLI 输出
保持 ASCII，Windows 控制台 GBK 下不乱码）。

底层复用（不重复造轮子）：行结构判定用
:func:`eosop_pro.core.lineprofile.profile_lines`（payload 三把尺子），
布局模板反演用 :func:`eosop_pro.core.inference.infer_file`
（f2_gray/f2_mg/f1_*/hyades/mpqeos/grids_only/ledcop 八模板 +
计数守恒/单调性/包络校验），编码鲁棒读取用
:func:`eosop_pro.core.textio.iter_lines`。
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .core import textio
from .core.inference import (TEMPLATES, infer_file, split_by_template)
from .core.lineprofile import LineProfile, profile_lines

__all__ = [
    "GuessReport", "SegmentGuess", "analyze_file", "read_payload_values",
    "factor_pairs", "value_fingerprint", "family_field_fingerprints",
    "match_fingerprints", "render_report", "main",
]


# ── 数值 token 解析（含 Fortran E12.6 丢 E 自愈） ─────────────────────
#: ``1.234567-101`` → ``1.234567E-101``（三位指数溢出静默丢 E，ionmix 实证 89 处）
_FORT_E = re.compile(r"(\d\.\d{6})([-+]\d{3})(?![\dEe])")


def _parse_token(tok: str) -> float | None:
    """单个 token → float；不可解析返回 ``None``（**不猜测**）。"""
    t = _FORT_E.sub(r"\1E\2", tok)
    try:
        v = float(t)
    except ValueError:
        return None
    return v


def _line_values(line: str) -> list[float] | None:
    """一行 → 数值列表；**任一** token 不可解析 → ``None``（整行非 payload）。"""
    toks = line.split()
    if not toks:
        return None
    vals: list[float] = []
    for t in toks:
        v = _parse_token(t)
        if v is None:
            return None
        vals.append(v)
    return vals


def read_payload_values(path: str | Path, *, coverage_min: float = 0.99,
                        max_lines: int | None = None
                        ) -> tuple[list[float], list[int], LineProfile]:
    """盲读：返回 ``(扁平数值序列, 每行 token 数, 行剖面)``。

    payload 行由 :func:`profile_lines`（``modal_only=False``，保留中断
    行 —— 中断本身是分块线索）判定；payload 行上**逐 token** 解析，
    任一 token 失败则该行降级为非 payload（诚实计数，不硬猜）。
    """
    lines: list[str] = []
    for i, ln in enumerate(textio.iter_lines(path)):
        if max_lines is not None and i >= max_lines:
            break
        lines.append(ln)
    prof = profile_lines(lines, coverage_min=coverage_min, modal_only=False)
    values: list[float] = []
    widths: list[int] = []
    for ok, ln in zip(prof.payload_flags, lines):
        if not ok:
            continue
        vals = _line_values(ln)
        if vals is None:                      # 剖面误判 -> 降级
            continue
        values.extend(vals)
        widths.append(len(vals))
    return values, widths, prof


# ── 统计基元 ─────────────────────────────────────────────────────────
def factor_pairs(n: int) -> list[tuple[int, int]]:
    """``n`` 的全部因数对 ``(a, b)``（``a <= b``，按 ``|a-b|`` 升序 = 最"方"优先）。"""
    out: list[tuple[int, int]] = []
    a = 1
    while a * a <= n:
        if n % a == 0:
            out.append((a, n // a))
        a += 1
    out.sort(key=lambda p: abs(p[0] - p[1]))
    return out


def value_fingerprint(vals) -> dict:
    """数值序列指纹（猜测对比的最小充分统计量，全 ASCII 键）。"""
    import numpy as np
    v = np.asarray(vals, dtype=float).ravel()
    fin = v[np.isfinite(v)]
    pos = fin[fin > 0]
    fp: dict = {"n": int(v.size)}
    fp["zero_frac"] = round(float((fin == 0).mean()), 4) if fin.size else 0.0
    fp["neg_frac"] = round(float((fin < 0).mean()), 4) if fin.size else 0.0
    fp["int_like_frac"] = (
        round(float(np.mean(np.abs(fin - np.round(fin)) < 1e-9)), 4)
        if fin.size else 0.0)
    if pos.size >= 2:
        lg = np.log10(pos)
        fp["log10_median"] = round(float(np.median(lg)), 3)
        fp["log10_span"] = round(float(lg.max() - lg.min()), 3)
        dif = np.diff(v[np.isfinite(v)])
        fp["mono_frac"] = (
            1.0 if dif.size == 0 else
            round(float(max((dif > 0).mean(), (dif < 0).mean())), 4))
    else:
        fp["log10_median"] = None
        fp["log10_span"] = None
        fp["mono_frac"] = None
    return fp


def _runs(vals, pred, min_len: int) -> list[tuple[int, int]]:
    """满足 ``pred`` 的极长连续段（返回 ``(start, end)`` 左闭右开）。"""
    out: list[tuple[int, int]] = []
    i, n = 0, len(vals)
    while i < n:
        if pred(vals[i]):
            j = i
            while j < n and pred(vals[j]):
                j += 1
            if j - i >= min_len:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


def _equal_runs(vals, min_len: int) -> list[tuple[int, int]]:
    """连续相等段（start 含首元素，左闭右开；任意重复值，不限首值）。"""
    out: list[tuple[int, int]] = []
    i, n = 0, len(vals)
    while i < n:
        j = i + 1
        while j < n and vals[j] == vals[j - 1]:
            j += 1
        if j - i >= min_len:
            out.append((i, j))
        i = j
    return out


def _decade_jumps(vals, threshold: float = 2.5, cap: int = 40
                  ) -> list[tuple[int, float, float]]:
    """相邻正值的 |Δlog10| ≥ threshold 处（潜在**块边界**）。"""
    out: list[tuple[int, float, float]] = []
    prev_i: int | None = None
    prev_v = 0.0
    for i, v in enumerate(vals):
        if not (math.isfinite(v) and v > 0):
            continue
        if prev_i is not None and i == prev_i + 1:
            dl = abs(math.log10(v) - math.log10(prev_v))
            if dl >= threshold:
                out.append((i, prev_v, v))
                if len(out) >= cap:
                    break
        prev_i, prev_v = i, v
    return out


def _col_profiles(rows: list[list[float]], width: int) -> list[dict]:
    """一致宽度矩阵的逐列画像（轴列识别用）。"""
    out: list[dict] = []
    for j in range(width):
        col = [r[j] for r in rows if len(r) == width]
        n = len(col)
        inc = all(col[i + 1] > col[i] for i in range(n - 1)) if n >= 2 else False
        dec = all(col[i + 1] < col[i] for i in range(n - 1)) if n >= 2 else False
        uniq = len(set(col))
        fp = value_fingerprint(col)
        out.append({
            "index": j, "n": n, "mono": "increasing" if inc else
            ("decreasing" if dec else "no"),
            "n_unique": uniq,
            "unique_frac": round(uniq / n, 3) if n else 0.0,
            "fingerprint": fp,
        })
    return out


@dataclass
class SegmentGuess:
    """一个意义块/段的猜测。"""

    index: int
    start: int
    end: int
    kind: str                 # axis_like | data_block | zero_run | constant_run
    length: int
    detail: str = ""

    def describe(self) -> str:
        return (f"seg[{self.index}] [{self.start}:{self.end}) "
                f"len={self.length} kind={self.kind} {self.detail}")


@dataclass
class GuessReport:
    """analyze_file 的完整猜测报告。"""

    path: str = ""
    n_lines: int = 0
    n_header: int = 0
    n_payload: int = 0
    row_widths: dict[int, int] = field(default_factory=dict)
    width_mode: int | None = None
    rows_consistent: bool = False
    total_values: int = 0
    factor_pairs: list[tuple[int, int]] = field(default_factory=list)
    shape_candidates: list[tuple[int, int]] = field(default_factory=list)
    log10_span: float | None = None
    int_like_frac: float = 0.0
    zero_frac: float = 0.0
    negative_frac: float = 0.0
    axis_like_cols: list[int] = field(default_factory=list)
    zero_runs: list[tuple[int, int]] = field(default_factory=list)
    constant_runs: list[tuple[int, int]] = field(default_factory=list)
    decade_jumps: list[tuple[int, float, float]] = field(default_factory=list)
    inference_status: str = "n/a"
    layout_candidates: list[str] = field(default_factory=list)
    template_segments: list[SegmentGuess] = field(default_factory=list)
    segments: list[SegmentGuess] = field(default_factory=list)
    matches: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def analyze_file(path: str | Path, *, compare_family: str | None = None,
                 max_bytes: int = 64_000_000) -> GuessReport:
    """对任意 eosop 文本数据做完整盲读猜测。

    Args:
        compare_family: 可选已知族键（如 ``"ionmix"``）—— 用该族已解析
            表的字段指纹与本文件段指纹对比，产出 :attr:`matches`。
        max_bytes: 超过则拒绝（防误丢超大二进制；诚实报错）。
    """
    p = Path(path)
    rep = GuessReport(path=str(p))
    if not p.is_file():
        rep.notes.append("file not found")
        return rep
    if p.stat().st_size > max_bytes:
        rep.notes.append(f"file too large ({p.stat().st_size} > {max_bytes} bytes)")
        return rep

    values, widths, prof = read_payload_values(p)
    rep.n_lines = prof.n_lines
    rep.n_header = prof.n_header
    rep.n_payload = len(widths)
    rep.row_widths = dict(Counter(widths))
    rep.width_mode = (Counter(widths).most_common(1)[0][0]
                      if widths else None)
    rep.rows_consistent = bool(widths) and len(set(widths)) == 1
    rep.total_values = len(values)
    rep.factor_pairs = factor_pairs(len(values)) if values else []
    if values:
        fp = value_fingerprint(values)
        rep.log10_span = fp["log10_span"]
        rep.int_like_frac = fp["int_like_frac"]
        rep.zero_frac = fp["zero_frac"]
        rep.negative_frac = fp["neg_frac"]
    if rep.rows_consistent and widths:
        # 一致宽度 -> 重排行优先矩阵，逐列画像找"轴样"列（单调且唯一率高）
        w = rep.width_mode or 0
        rows: list[list[float]] = []
        it = iter(values)
        for _ in range(len(widths)):
            rows.append([next(it) for _ in range(w)])
        cols = _col_profiles(rows, w)
        rep.axis_like_cols = [
            c["index"] for c in cols
            if c["mono"] != "no" and c["unique_frac"] > 0.9]
        # 形状候选：行优先 (n_rows, w) 与转置 (w, n_rows)
        rep.shape_candidates = [(len(widths), w), (w, len(widths))]

    rep.zero_runs = _runs(values, lambda v: v == 0.0, min_len=5)
    rep.constant_runs = _equal_runs(values, min_len=8) if values else []
    rep.decade_jumps = _decade_jumps(values)

    # -- 模板反演（core 层，多证据合议） --
    inf = infer_file(p)
    rep.inference_status = inf.status
    for c in inf.candidates[:8]:
        rep.layout_candidates.append(c.describe())
    if inf.ok and values and inf.best is not None:
        tmpl = next((t for t in TEMPLATES
                     if t.name == inf.best.template), None)
        if tmpl is None:
            rep.notes.append(
                f"template {inf.best.template!r} not found in TEMPLATES")
        else:
            segs = split_by_template(values, tmpl, inf.best.d1,
                                     inf.best.d2, inf.best.ng)
            if segs is None:
                rep.notes.append("best template length mismatch (internal)")
            else:
                for k, (a, b) in enumerate(segs):
                    sl = values[a:b]
                    mono = value_fingerprint(sl)["mono_frac"]
                    kind = ("axis_like"
                            if mono is not None and mono > 0.99 and len(sl) >= 4
                            else "data_block")
                    rep.template_segments.append(SegmentGuess(
                        index=k, start=a, end=b, kind=kind, length=b - a,
                        detail=f"template={inf.best.template}"))

    # -- 无模板时的朴素分段（跳变/长跑切） --
    cuts = {0, len(values)}
    for a, _b in rep.zero_runs:
        cuts.add(a)
        cuts.add(_b)
    for i, _a, _v in rep.decade_jumps:
        cuts.add(i)
    if len(values) and len(cuts) > 2:
        ordered = sorted(cuts)
        for k in range(len(ordered) - 1):
            a, b = ordered[k], ordered[k + 1]
            if b - a < 3:
                continue
            sl = values[a:b]
            zr = all(v == 0.0 for v in sl)
            kind = "zero_run" if zr else "data_block"
            rep.segments.append(SegmentGuess(
                index=k, start=a, end=b, kind=kind, length=b - a))

    if compare_family:
        rep.matches = _compare_with_family(rep, values, compare_family)
    return rep


def _compare_with_family(rep: GuessReport, values: list[float],
                         family: str) -> list[dict]:
    """与已知族字段指纹对比（3.2 猜意义/单位的朴素合议）。"""
    from .registry.dispatch import FAMILY_PARSERS
    from .registry.field_checks import field_check

    fn_parser = FAMILY_PARSERS.get(family)
    if fn_parser is None:
        rep.notes.append(f"unknown family for compare: {family}")
        return []
    # 用本文件所在族解析（同族样例最可比）；失败则诚实返回空
    try:
        tables = fn_parser(str(rep.path))
    except Exception as exc:                              # noqa: BLE001
        rep.notes.append(f"family parse failed: {exc}")
        return []
    if not tables:
        return []
    seg_fps = [value_fingerprint(values[a:b])
               for a, b in _seg_bounds(rep, values)]
    field_fps: list[dict] = []
    for tbl in tables:
        for name, flat in tbl.fields.items():
            if not isinstance(flat, (list, tuple)) or len(flat) < 4:
                continue
            fc = field_check(getattr(tbl, "family", family), name)
            field_fps.append({
                "field": f"{tbl.table_key}.{name}",
                "unit": fc.unit or "unknown",
                "meaning": fc.meaning,
                "fp": value_fingerprint(flat),
            })
    return match_fingerprints(seg_fps, field_fps)


def _seg_bounds(rep: GuessReport, values: list[float]) -> list[tuple[int, int]]:
    """报告里可用的段边界（模板段优先，朴素段兜底，整段兜底）。"""
    if rep.template_segments:
        return [(s.start, s.end) for s in rep.template_segments]
    if rep.segments:
        return [(s.start, s.end) for s in rep.segments]
    return [(0, len(values))]


def match_fingerprints(seg_fps: list[dict], field_fps: list[dict],
                       *, top_k: int = 6, tol_median: float = 0.7,
                       tol_span: float = 1.5) -> list[dict]:
    """段指纹 × 字段指纹 → "疑似"候选（量级/跨度/整值率三证据合议）。

    单位换算容忍（第十一轮实战教训）：解析器常把文件原始 CGS 值换算成
    SI —— 盲读段与登记字段会差**一个 10 的整数次幂**因子。此时命中并
    在结果里给出 ``guess_scale``（GUESS ONLY 的换算因子候选）；scale≠1
    的命中加 +1 惩罚分，保证真实同量级匹配永远优先。
    """
    out: list[dict] = []
    for si, sf in enumerate(seg_fps):
        if sf.get("log10_median") is None:
            continue
        scored: list[tuple[float, dict, float]] = []
        for ff in field_fps:
            fp = ff["fp"]
            if fp.get("log10_median") is None:
                continue
            dm_abs = abs(sf["log10_median"] - fp["log10_median"])
            k = round(dm_abs)
            frac = abs(dm_abs - k)
            if frac < 0.15:                    # 整数 decade 偏移 -> 换算命中
                sign = 1 if sf["log10_median"] >= fp["log10_median"] else -1
                dm, scale = frac, 10.0 ** (sign * k)
            else:
                dm, scale = dm_abs, 1.0
            ds = abs((sf["log10_span"] or 0) - (fp["log10_span"] or 0))
            di = abs(sf["int_like_frac"] - fp["int_like_frac"])
            score = dm + 0.5 * ds + 0.5 * di
            if scale != 1.0:
                score += 1.0                   # 换算命中惩罚：真实匹配优先
            if dm <= tol_median and ds <= tol_span:
                scored.append((score, ff, scale))
        scored.sort(key=lambda t: t[0])
        for score, ff, scale in scored[:top_k]:
            out.append({
                "segment": si,
                "guess_field": ff["field"],
                "guess_meaning": ff["meaning"],
                "guess_unit": ff["unit"],
                "guess_scale": scale,
                "score": round(score, 3),
                "note": "GUESS ONLY (not verified)",
            })
    return out


def family_field_fingerprints(family: str, tables: list) -> list[dict]:
    """已知族已解析表的字段指纹清单（供外部批量对比/报告复用）。"""
    from .registry.field_checks import field_check
    out: list[dict] = []
    for tbl in tables:
        for name, flat in tbl.fields.items():
            if not isinstance(flat, (list, tuple)) or len(flat) < 4:
                continue
            fc = field_check(getattr(tbl, "family", family), name)
            out.append({
                "field": f"{tbl.table_key}.{name}",
                "unit": fc.unit or "unknown",
                "meaning": fc.meaning,
                "fp": value_fingerprint(flat),
            })
    return out


def render_report(rep: GuessReport) -> str:
    """ASCII 纯文本报告（CLI 输出 / 落盘均安全，Windows GBK 不乱码）。"""
    L: list[str] = []
    L.append("=== eosop guess report (GUESS ONLY, not verified) ===")
    L.append(f"file: {rep.path}")
    L.append(f"lines={rep.n_lines} header={rep.n_header} "
             f"payload_rows={rep.n_payload} values={rep.total_values}")
    L.append(f"row widths hist: {rep.row_widths}")
    L.append(f"width mode: {rep.width_mode} consistent={rep.rows_consistent}")
    L.append(f"factor pairs of total: {rep.factor_pairs[:12]}")
    if rep.shape_candidates:
        L.append(f"shape candidates (row-major, transposed): "
                 f"{rep.shape_candidates}")
    if rep.log10_span is not None:
        L.append(f"log10 span={rep.log10_span} int_like={rep.int_like_frac} "
                 f"zero_frac={rep.zero_frac} neg_frac={rep.negative_frac}")
    if rep.axis_like_cols:
        L.append(f"axis-like columns (monotonic, unique>90%): "
                 f"{rep.axis_like_cols}")
    if rep.zero_runs:
        L.append(f"zero runs: {rep.zero_runs[:10]}")
    if rep.constant_runs:
        L.append(f"constant runs: {rep.constant_runs[:10]}")
    if rep.decade_jumps:
        L.append(f"decade jumps (idx, before, after): "
                 f"{[(i, f'{a:.3g}', f'{b:.3g}') for i, a, b in rep.decade_jumps[:10]]}")
    L.append(f"template inference: status={rep.inference_status}")
    for c in rep.layout_candidates:
        L.append(f"  candidate: {c}")
    for s in rep.template_segments:
        L.append("  " + s.describe())
    for s in rep.segments:
        L.append("  naive " + s.describe())
    if rep.matches:
        L.append("-- guesses by fingerprint match vs known family --")
        for m in rep.matches:
            sc = (f"x{m['guess_scale']:.0e}"
                  if m.get("guess_scale", 1.0) != 1.0 else "")
            L.append(f"  seg{m['segment']} -> {m['guess_field']} "
                     f"unit={m['guess_unit']} {sc} "
                     f"score={m['score']} ({m['note']})")
    for n in rep.notes:
        L.append(f"  ! {n}")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    """CLI：``python -m eosop_pro.guess <file> [--compare-family F]``。"""
    import argparse
    ap = argparse.ArgumentParser(
        prog="python -m eosop_pro.guess",
        description="blind-read and guess any eosop data file "
                    "(GUESS ONLY, never written back to field_checks)")
    ap.add_argument("file", help="path to the data file")
    ap.add_argument("--compare-family", default=None,
                    help="known family key to fingerprint-match against "
                         "(e.g. ionmix)")
    args = ap.parse_args(argv)
    rep = analyze_file(args.file, compare_family=args.compare_family)
    print(render_report(rep))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
