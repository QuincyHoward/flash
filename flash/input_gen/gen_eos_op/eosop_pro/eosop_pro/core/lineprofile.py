"""② 行结构剖面 —— 从**内容**定位「头部文本区 / payload 数值区」的分界。

三把尺子
--------
1. **行长度直方图**：定宽数据的行宽会聚成极少数几个值（如 60 = 4×15）。
2. **数值覆盖率**：``numeric_coverage`` = 被数值 token 覆盖的非空白字符占比。
   头部文本行低、payload 行 ≈ 1。
3. **字母残留率**：``letter_ratio``（**先剔除数值 token** 再判字母）——
   这是最干净的主判据，因为 payload 行只含 ``E`` 指数，剔除后无字母。

实测教训（决定了实现方式）
--------------------------
* 注释行**也含数字**（``... SESAME #3711 DATED: 22581 11483`` 覆盖率 0.359 而非 0）
  → 覆盖率不能单独用。
* payload 行含指数 ``E`` → naive「含字母」会把**每一行 payload 都判成表头**
  → 必须先剔除数值 token。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from . import fortran_numbers as fn
from . import textio

__all__ = ["LineProfile", "profile_lines", "profile_file"]


@dataclass
class LineProfile:
    """一个文件的行结构画像。"""

    n_lines: int = 0
    n_blank: int = 0
    length_hist: dict[int, int] = field(default_factory=dict)
    modal_length: int | None = None
    coverage_hist: dict[int, int] = field(default_factory=dict)
    #: 每行是否"像 payload"（无字母残留 + 覆盖率 ≥ 阈值）
    payload_flags: list[bool] = field(default_factory=list)
    #: **未施加众数行宽过滤**的原始判定 —— 用于发现 payload 区的中断
    #: （众数过滤会把散落的短行剔掉，反而看不见中断，实测踩过）
    payload_flags_raw: list[bool] = field(default_factory=list)
    header_end: int = 0            # 头部区**之后**的第一行索引 = payload 起点
    n_payload: int = 0
    n_header: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def is_all_numeric(self) -> bool:
        return self.n_header == 0 and self.n_payload > 0

    @property
    def is_free_text_heavy(self) -> bool:
        """头部占比过高 → 可能是锚点状态机型（如 LEDCOP）。"""
        return self.n_lines > 0 and self.n_header / max(1, self.n_lines) > 0.5

    def describe(self) -> str:
        return (f"lines={self.n_lines} blank={self.n_blank} "
                f"modal_len={self.modal_length} header={self.n_header} "
                f"payload={self.n_payload} header_end={self.header_end}")


def profile_lines(lines: list[str], *, coverage_min: float = 0.99,
                  modal_only: bool = True) -> LineProfile:
    """对行列表做剖面。

    ``modal_only=True`` 时，payload 判定额外要求「行宽 == 众数行宽」
    （定宽族特征），可显著降低把散落数字行误判为 payload 的概率。
    """
    p = LineProfile(n_lines=len(lines))
    lengths = Counter()
    covs = Counter()
    flags: list[bool] = []
    for ln in lines:
        if not ln.strip():
            p.n_blank += 1
            flags.append(False)
            continue
        lengths[len(ln)] += 1
        cov = fn.numeric_coverage(ln)
        covs[int(cov * 10)] += 1
        flags.append(fn.is_payload_line(ln, coverage_min=coverage_min))

    p.length_hist = dict(lengths)
    p.coverage_hist = dict(covs)
    p.modal_length = lengths.most_common(1)[0][0] if lengths else None
    p.payload_flags_raw = list(flags)

    if modal_only and p.modal_length is not None:
        for i, ln in enumerate(lines):
            if flags[i] and len(ln) != p.modal_length:
                flags[i] = False

    p.payload_flags = flags
    idx = [i for i, ok in enumerate(flags) if ok]
    if idx:
        p.header_end = idx[0]
        p.n_payload = len(idx)
        p.n_header = p.header_end
        # ★ 中断检测用**原始**判定（不受众数过滤影响）
        raw_idx = [i for i, ok in enumerate(p.payload_flags_raw) if ok]
        gaps = [raw_idx[i + 1] - raw_idx[i] for i in range(len(raw_idx) - 1)]
        if gaps and max(gaps) > 3:
            p.notes.append(
                f"payload 区存在 {sum(1 for g in gaps if g > 3)} 处中断"
                f"（最大间隔 {max(gaps)} 行）→ 可能是拼接多表或注释穿插"
            )
    else:
        p.header_end = len(lines)
        p.n_header = len(lines)
        p.n_payload = 0
        p.notes.append("未找到任何 payload 行（可能为自由文本或非数值文件）")
    return p


def profile_file(path, *, coverage_min: float = 0.99,
                 modal_only: bool = True, max_lines: int | None = None) -> LineProfile:
    """对文件做剖面（用流式读，避免大文件整读）。"""
    lines: list[str] = []
    for i, ln in enumerate(textio.iter_lines(path)):
        if max_lines is not None and i >= max_lines:
            break
        lines.append(ln)
    return profile_lines(lines, coverage_min=coverage_min, modal_only=modal_only)
