"""④ 语义反演 —— 把表头整数当**未知量**，用「计数守恒 × 单调 × 包络」求解布局。

立场（这是阶段 B 的核心思想）
-----------------------------
**不做「匹配已知格式清单」，而做「结构反演 + 自洽性验证」。**
已知格式只是**先验**（用来加速与消歧）；最终一律由**数值证据**定案。
因此同一套代码对未知格式同样有效 —— 未知格式退化为「预算是空的、纯靠通用模板反演」。

流程
----
1. 从表头提取数值与「维度候选」``(d1, d2)``（末两个整数、倒数第三个组合等）；
2. 对每个 **(维度候选 × 布局模板)** 解**计数方程**
   ``payload == sum(segments)`` —— 只有**精确整数解**才保留；
3. 校验前两个 segment 作为**网格**是否**严格单调**；
4. 校验网格量级是否落在**物理包络**内；
5. **唯一**存活的候选 → ``ok``；多个 → ``ambiguous``（**列出全部并列候选**）；
   零个 → ``unrecognized``（输出完整反演报告）。

**绝不静默填一个猜测值** —— 这正是 h5 里 NaN 与 0 严格区分的原因。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Sequence

from .. import config
from . import fortran_numbers as fn
from .envelope import DEFAULT_ENVELOPE, Envelope
from .lineprofile import LineProfile, profile_lines
from .columnprofile import ColumnProfile, profile_columns

__all__ = [
    "LayoutTemplate", "LayoutCandidate", "InferenceResult",
    "TEMPLATES", "split_by_template", "infer_layout",
]

#: segment 名（只用于展示与报告）
_S = ("g1", "g2", "a", "b", "c", "d")


@dataclass(frozen=True)
class LayoutTemplate:
    """一个布局模板：给定维度 → 各 segment 长度。

    ``dims_in_payload_offset``：有些格式的 ``NR/NT`` **不在表头**而在 payload
    开头（实测 F3 Hyades：行 2 的 ``... rho0 L`` 之后，payload 前两个数才是 ``NR NT``）。
    这时维度由 payload 自解，而不是从表头候选里挑。
    """

    name: str
    family: str
    segments: Callable[[int, int, int], tuple[int, ...]]
    note: str = ""
    dims_in_payload_offset: int | None = None
    #: 哪两个 segment 是**网格**（用于单调性校验）。
    #: 例如 F3 的 segment 0 是 payload 里的 ``NR NT`` 两个数，网格从 segment 1 开始。
    grid_segments: tuple[int, int] = (0, 1)

    def count(self, d1: int, d2: int, ng: int = 1) -> int:
        return sum(self.segments(d1, d2, ng))


def _t_f2_gray(d1, d2, ng):        # rho, T, V
    return (d1, d2, d1 * d2)


def _t_f2_mg(d1, d2, ng):          # ng 个子表：每子表 rho,T,V
    return (ng * (d1 + d2 + d1 * d2),)


def _t_f1_with_e0(d1, d2, ng):     # rho, de, e0, P, T
    return (d1, d2, d1, d1 * d2, d1 * d2)


def _t_f1_no_e0(d1, d2, ng):       # rho, de, P, T
    return (d1, d2, d1 * d2, d1 * d2)


def _t_hyades_eos(d1, d2, ng):     # nr, nt, P, E（L 已含 2）
    return (2, d1, d2, d1 * d2, d1 * d2)


def _t_mpqeos(d1, d2, ng):         # R, T, P, E, Z
    return (d1, d2, d1 * d2, d1 * d2, d1 * d2)


def _t_grids_only(d1, d2, ng):     # 只有两个网格
    return (d1, d2)


def _t_ledcop_split(d1, d2, ng):   # 同 f2_gray（4 数头 + 3 段）
    return (d1, d2, d1 * d2)


#: 布局模板（顺序 = 先验强度，强先验在前）
TEMPLATES: tuple[LayoutTemplate, ...] = (
    LayoutTemplate("f2_gray", "multi_opacity", _t_f2_gray,
                   "F2 灰度：rho + T + V"),
    LayoutTemplate("f2_multigroup", "multi_opacity", _t_f2_mg,
                   "F2 多群：ng × (rho + T + V)"),
    LayoutTemplate("ledcop_split", "ledcop_zeff", _t_ledcop_split,
                   "LEDCOP 拆分件：同 f2_gray"),
    LayoutTemplate("f1_with_e0", "multi_inverted_eos", _t_f1_with_e0,
                   "F1 反演 EOS（含冷能）：rho + de + e0 + P + T"),
    LayoutTemplate("f1_no_e0", "multi_inverted_eos", _t_f1_no_e0,
                   "F1 反演 EOS（无冷能）：rho + de + P + T"),
    LayoutTemplate("hyades_eos", "hyades_eos", _t_hyades_eos,
                   "F3：NR + NT + P + E（NR/NT 在 payload 开头）",
                   dims_in_payload_offset=0, grid_segments=(1, 2)),
    LayoutTemplate("mpqeos", "mpqeos", _t_mpqeos,
                   "F4：R + T + P + E + Z"),
    LayoutTemplate("grids_only", "generic_curve", _t_grids_only,
                   "仅两个网格（无数据段）"),
)


@dataclass
class LayoutCandidate:
    """一个自洽的布局解。"""

    template: str
    family: str
    d1: int
    d2: int
    ng: int = 1
    payload: int = 0
    score: float = 0.0
    monotonic: bool = False
    in_envelope: bool = False
    exact: bool = True            # 无前导/尾部未声明数值
    lead: int = 0
    tail: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def dims(self) -> tuple[int, int]:
        return (self.d1, self.d2)

    def describe(self) -> str:
        return (f"{self.template}(d1={self.d1},d2={self.d2},ng={self.ng}) "
                f"payload={self.payload} mono={self.monotonic} "
                f"env={self.in_envelope} score={self.score:.2f}")


@dataclass
class InferenceResult:
    """反演结果。"""

    status: str = "unrecognized"      # ok | ambiguous | unrecognized
    best: LayoutCandidate | None = None
    candidates: list[LayoutCandidate] = field(default_factory=list)
    header_nums: list[float] = field(default_factory=list)
    dim_candidates: list[tuple[int, int]] = field(default_factory=list)
    n_payload: int = 0
    profile: LineProfile | None = None
    columns: ColumnProfile | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == "ok" and self.best is not None

    def report(self) -> str:
        """完整反演报告（``unrecognized``/``ambiguous`` 时应输出它）。"""
        L: list[str] = []
        L.append("=== 通用布局反演报告 ===")
        L.append(f"状态: {self.status}")
        if self.profile:
            L.append(f"行剖面: {self.profile.describe()}")
            for n in self.profile.notes:
                L.append(f"  · {n}")
        if self.columns:
            L.append(f"列剖面: {self.columns.describe()}")
            for n in self.columns.conflicts:
                L.append(f"  · {n}")
        L.append(f"表头数值: {[round(x, 6) for x in self.header_nums]}")
        L.append(f"维度候选: {self.dim_candidates}")
        L.append(f"payload 数值个数: {self.n_payload}")
        L.append(f"自洽候选 ({len(self.candidates)}):")
        for c in self.candidates:
            L.append("  - " + c.describe())
            for n in c.notes:
                L.append(f"      · {n}")
        for n in self.notes:
            L.append("  ! " + n)
        return "\n".join(L)


# ── 切分与校验 ─────────────────────────────────────────────────
def split_by_template(values: Sequence[float], tmpl: LayoutTemplate,
                      d1: int, d2: int, ng: int = 1) -> list[tuple[int, ...]] | None:
    """按模板切分数值；长度不符返回 ``None``。"""
    segs = tmpl.segments(d1, d2, ng)
    if sum(segs) != len(values):
        return None
    out: list[tuple[int, ...]] = []
    i = 0
    for s in segs:
        out.append(tuple(range(i, i + s)))
        i += s
    return out


def _strictly_increasing(v: Sequence[float]) -> bool:
    if len(v) < 2:
        return False
    return all(v[i + 1] > v[i] for i in range(len(v) - 1))


def _envelope_ok(seg1: Sequence[float], seg2: Sequence[float], env: Envelope) -> bool:
    """网格量级自洽性校验 —— 这是**粗筛**，不是精确判别。

    ★ 必须同时接受三种**合法**表示，否则会把真实文件全判死（实测逐条踩过）：

    1. **物理量**：``rho ∈ [1e-8, 1e6] g/cm³``、``T ∈ [1e-2, 1e6] eV``
    2. **log10 存储**：F2 族的 rho/T 就是 ``log10`` 值 → 接受 ``[-8, 6]`` / ``[-2, 6]``
    3. **Kelvin 尺度**：F1/F4 的温度是 Kelvin（``≈ eV / 8.617e-5``）→ 上界放宽到 ``1e10``

    并且**忽略 0**（真空密度、零比能偏移都是合法网格端点），允许 **1 个数量级余量**。
    换言之：包络只用来排除**量级错误**（比如把 ``1e30`` 当密度），
    真正的布局判定靠**计数守恒 + 单调性**。
    """
    def _in(vals, lo, hi):
        fin = [x for x in vals
               if x == x and x not in (float("inf"), float("-inf")) and x != 0.0]
        if not fin:
            return False
        return lo <= min(fin) and max(fin) <= hi

    slack = 10.0
    rho_phys = (env.rho_min, env.rho_max * slack)
    te_eV = (env.te_min, env.te_max / config.EV_PER_K / slack)   # 兼顾 Kelvin 尺度
    rho_log = (math.log10(env.rho_min) - 1.0, math.log10(env.rho_max) + 1.0)
    te_log = (math.log10(env.te_min) - 1.0, math.log10(env.te_max) + 1.0)

    def _any(vals) -> bool:
        return any(_in(vals, lo, hi)
                   for lo, hi in (rho_phys, te_eV, rho_log, te_log))

    cands = (1 if _any(seg1) else 0) + (1 if _any(seg2) else 0)
    return cands >= 1


def _dim_candidates(header_nums: Sequence[float]) -> list[tuple[int, int]]:
    """从表头数值提「维度候选」，**按先验强度排序**。

    实测 F1/F2/F3/F4 的表头都把 ``NR``/``NT`` 放在**最后两位**，
    故「末两个整数」优先；其后是「倒数第 3 与最后」（F3 的 ``... rho0 L`` 会插入一项）、
    「倒数第 3 与倒数第 2」，最后才是其余组合。
    """
    ints: list[int] = []
    for x in header_nums:
        if x == x and x == int(x) and 2 <= int(x) <= config.DIM_MAX:
            ints.append(int(x))
    # ★ 必须保留**位置重复值**：``NR == NT`` 的方表（如 ``20 20``）一旦去重就没了
    n = len(ints)
    ordered: list[tuple[int, int]] = []
    if n >= 2:
        ordered.append((ints[-2], ints[-1]))
    if n >= 3:
        ordered.append((ints[-3], ints[-1]))
        ordered.append((ints[-3], ints[-2]))
    for i in range(n):
        for j in range(i + 1, n):
            ordered.append((ints[i], ints[j]))
    out: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for p in ordered:
        if p[0] >= 2 and p[1] >= 2 and p not in seen:
            seen.add(p)
            out.append(p)
    return out


# ── 主入口 ─────────────────────────────────────────────────────
def infer_layout(lines: list[str], *, declared_families: Sequence[str] = (),
                 env: Envelope | None = None,
                 max_dim_candidates: int = 12) -> InferenceResult:
    """对已读入的行做通用布局反演。

    ★ 表头/数据的**分界本身就是未知量**：F1/F2/F4 的表头行是**纯数字**，
    所以「按字母找文本头」的办法找不到它们（实测踩过）。
    因此本函数对 ``k = 1..4`` 个前导行**逐个假设为表头**并分别反演，
    最后在**全部**自洽解里做唯一性判定。
    """
    env = env or DEFAULT_ENVELOPE
    res = InferenceResult()
    res.profile = profile_lines(lines)
    payload_lines_all = [ln for ln, ok in zip(lines, res.profile.payload_flags) if ok]
    res.columns = profile_columns(payload_lines_all)

    if not payload_lines_all:
        res.notes.append("无 payload 行 → 无法反演")
        return res

    nonblank = [ln for ln in lines if ln.strip()]
    # 文本头存在时优先尊重它；否则穷举前导行数
    if res.profile.header_end > 0:
        splits = [res.profile.header_end]
        if res.profile.header_end <= 2:
            splits.append(res.profile.header_end + 1)
    else:
        splits = [1, 2, 3]

    best_pool: list[tuple[LayoutCandidate, int, list[float]]] = []
    all_notes: list[str] = []
    for k in dict.fromkeys(splits):
        if k < 1 or k >= len(nonblank):
            continue
        header_lines = nonblank[:k]
        body_lines = nonblank[k:]
        header_nums: list[float] = []
        for ln in header_lines:
            header_nums.extend(fn.extract_numbers(ln))
        values: list[float] = []
        for ln in body_lines:
            values.extend(fn.extract_numbers(ln))
        dims = _dim_candidates(header_nums)[:max_dim_candidates]
        for tmpl in TEMPLATES:
            # 维度来源：payload 开头（F3）或 表头候选
            if tmpl.dims_in_payload_offset is not None:
                off = tmpl.dims_in_payload_offset
                if len(values) < off + 2:
                    continue
                a, b = values[off], values[off + 1]
                if a != int(a) or b != int(b):
                    continue
                d1, d2 = int(a), int(b)
                if not (2 <= d1 <= config.DIM_MAX and 2 <= d2 <= config.DIM_MAX):
                    continue
                dim_iter: list[tuple[int, int]] = [(d1, d2)]
            else:
                dim_iter = dims
            for (d1, d2) in dim_iter:
              for lead in range(0, 5):
                for tail in range(0, max(0, min(d1, 8)) + 1):
                    avail = len(values) - lead - tail
                    if avail <= 0:
                        continue
                    # 群数由**扣掉前导/尾部之后**的余量反解
                    if tmpl.name == "f2_multigroup":
                        per = d1 + d2 + d1 * d2
                        if not per or avail % per:
                            continue
                        ng_list = [avail // per]
                    else:
                        ng_list = [1]
                    for ng in ng_list:
                        segs = tmpl.segments(d1, d2, ng)
                        need = sum(segs)
                        if need != avail:
                            continue
                        eff = values[lead:lead + need]
                        idx = split_by_template(eff, tmpl, d1, d2, ng)
                        if idx is None:  # pragma: no cover
                            continue
                        gi, gj = tmpl.grid_segments
                        seg1 = [eff[i] for i in idx[gi]] if gi < len(idx) else []
                        seg2 = [eff[i] for i in idx[gj]] if gj < len(idx) else []
                        mono = _strictly_increasing(seg1)
                        env_ok = _envelope_ok(seg1, seg2, env)
                        c = LayoutCandidate(
                            template=tmpl.name, family=tmpl.family,
                            d1=d1, d2=d2, ng=ng, payload=len(values),
                            score=(1.0 if mono else 0.0) + (1.0 if env_ok else 0.0),
                            monotonic=mono, in_envelope=env_ok,
                            exact=(lead == 0 and tail == 0),
                            lead=lead, tail=tail,
                        )
                        c.notes.append(f"前导表头行数 k={k}")
                        if lead:
                            c.notes.append(f"⚠️ 前置 {lead} 个未声明数值（如实记录）")
                        if tail:
                            c.notes.append(f"⚠️ 尾部 {tail} 个未声明数值（补零，如实记录）")
                        if tmpl.dims_in_payload_offset is not None:
                            c.notes.append("维度取自 payload 前两值")
                        if ng > 1:
                            c.notes.append(f"群数由计数方程反解得 ng={ng}")
                        if tmpl.family in declared_families:
                            c.score += 0.5
                            c.notes.append("命中声明族（先验加分）")
                        if not mono:
                            c.notes.append(
                                f"网格 segment[{gi}] 非严格递增 → 不太可能是网格"
                            )
                        if not env_ok:
                            c.notes.append("网格量级落在物理包络之外")
                        best_pool.append((c, k, header_nums))
        all_notes.append(f"k={k}: dims={dims[:4]} values={len(values)}")

    res.notes.extend(all_notes)
    if not best_pool:
        res.notes.append("所有 (分界 × 维度 × 模板) 组合都不满足计数守恒")
        res.status = "unrecognized"
        return res

    # 候选池：先取「单调 + 包络」都成立的；若一个都没有，则保留全部供报告
    good = [c for c, _k, _h in best_pool if c.monotonic and c.in_envelope]
    pool = good or [c for c, _k, _h in best_pool]

    # 去重：同一 (template, d1, d2, ng) 只保留最优的那一个
    uniq: dict[tuple, LayoutCandidate] = {}
    for c in pool:
        key = (c.template, c.d1, c.d2, c.ng)
        prev = uniq.get(key)
        if prev is None:
            uniq[key] = c
            continue
        better = ((c.exact and not prev.exact)
                  or (c.exact == prev.exact and c.score > prev.score))
        if better:
            uniq[key] = c
    pool = sorted(uniq.values(), key=lambda c: (0 if c.exact else 1, -c.score))
    res.candidates = pool

    exact_good = [c for c in pool if c.monotonic and c.in_envelope and c.exact]
    relaxed_good = [c for c in pool if c.monotonic and c.in_envelope]
    usable = exact_good if exact_good else relaxed_good
    if relaxed_good and not exact_good:
        res.notes.append(
            "无「精确计数」解；以下解都带**未声明的前导/尾部数值**（已逐条标注）—— "
            "属放宽判据，需人工确认"
        )
    # 用最终选定的候选回填表头数值（便于报告）
    for c, _k, hn in best_pool:
        if c is (usable[0] if usable else None):
            res.header_nums = hn
            res.dim_candidates = [tuple(c.dims)]
            break

    if len(usable) == 1:
        res.status, res.best = "ok", usable[0]
    elif len(usable) > 1:
        best_fam = [c for c in usable if c.family in declared_families]
        if len(best_fam) == 1:
            res.status, res.best = "ok", best_fam[0]
            res.notes.append(
                f"有 {len(usable)} 个自洽布局，但仅 1 个属于声明族 "
                f"{list(declared_families)} → 据此消歧（先验）"
            )
        else:
            res.status = "ambiguous"
            res.notes.append(
                f"**{len(usable)} 个布局同时自洽**，无法由计数区分 → "
                f"列出全部并列候选交人工定案："
                + " ; ".join(c.describe() for c in usable[:6])
            )
    else:
        res.status = "unrecognized"
        res.notes.append("无「单调 + 包络」双重自洽的布局")
    return res


def infer_file(path, **kw) -> InferenceResult:
    from .textio import iter_lines
    return infer_layout(list(iter_lines(path)), **kw)
