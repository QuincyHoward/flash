# -*- coding: utf-8 -*-
"""cn4 写侧内核 —— ParsedTable/CN4Table → ``.cn4`` 文件的全部写出逻辑。

⚠️ 职责边界（2026-11-15 解耦迁移）：**写/转**逻辑全部在此；
读取（``parse_cn4``/``load_cn4``/``CN4Table``/``cn4_to_parsed_tables``）
仍在 :mod:`eosop_pro.parsers.cn4_io`。本模块可 import parsers（convert → parsers
合法方向），parsers **不得**反向 import 本模块。

迁移内容（自 parsers/cn4_io.py，逐字保留）::

    FIXED_HEADER_WIDTH / _detect_mantissa_style / _pad80 / _fortran_e12_6 /
    _exp_fortran / _fmt_e12_6 / _write_block / write_cn4 /
    parsed_tables_to_cn4 / _all_nan / _FOREIGN_T_AXES / _FOREIGN_RHO_AXES /
    _pick_axis / _resolve_foreign_grid / convert_foreign_to_cn4 / convert_cn4_to_cn4

格式权威来源与 18 块布局说明见 parsers/cn4_io.py 模块 docstring（单一事实源）。
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from ..core.config import N_A as NA
from ..parsers.cn4_io import (BLOCK_SPEC, CN4ParseError, CN4Table,
                              FIXED_WIDTH, NAN_PLACEHOLDER_FIELD,
                              OPACITY_SPEC, expected_number_count,
                              guess_atomwt, parse_cn4)

#: Fortran 默认记录宽度（``write`` 无格式时的尾部空格填充列数）。
FIXED_HEADER_WIDTH = 80


def _detect_mantissa_style(table: CN4Table) -> str:
    """推断源表的 ``e12.6`` 尾数风格：``"leading0"`` 或 ``"dotted"``。

    依据（按可靠性排序）：

    1. ``table.header_raw`` 里若记录了源文件的原始数据行样本 —— 最直接。
       实际项目中 ``header_raw`` 只存头部，故通常走 (2)。
    2. ``table.notes`` 中若由解析器写入了风格标记（含 ``mantissa`` 字样）。
    3. 兜底：``"leading0"`` —— Ionmix / OWTF 是本项目 cn4 的主生产者
       （实测 6/10 文件为该风格；BADGER 系列 4/10 为 ``dotted``）。

    调用方若明确知道风格，应直接传 ``mantissa_style=``，不要依赖本推断。
    """
    for n in (table.notes or ()):
        low = str(n).lower()
        if "mantissa" in low:
            if "dotted" in low:
                return "dotted"
            if "leading0" in low or "leading-zero" in low:
                return "leading0"
    return "leading0"


def _pad80(s: str) -> str:
    """把头部行补齐/截断到 :data:`FIXED_HEADER_WIDTH` 列。

    实测源 cn4 头部前 3 行恰为 80 字节（尾部空格填充），复刻之以保证
    byte-identical 往返；超长行按 Fortran 行为**截断**。
    """
    if len(s) >= FIXED_HEADER_WIDTH:
        return s[:FIXED_HEADER_WIDTH]
    return s.ljust(FIXED_HEADER_WIDTH)


def _fortran_e12_6(v: float, dec: int = 6,
                   style: str = "leading0") -> str:
    """把 ``v`` 写成 Fortran ``e12.6`` 的**字面形态**。

    实测本项目的 cn4 生产者存在**两种**尾数风格（数值等价，仅排版不同）：

    ==============  ==================  ==========================
    风格            ``style``           形如
    ==============  ==================  ==========================
    前导零          ``"leading0"``      ``0.100000E+00``  (12 列)
    点号            ``"dotted"``        ``1.000000E-01``  (12 列)
    ==============  ==================  ==========================

    * Ionmix / OWTF 产物（``he-imx-*.cn4``、``polystyrene-imx-*.cn4``、
      ``Z02_*.cn4`` …）用 **前导零** 风格。
    * BADGER-TOPS 系列（``CH/He/Ti/V-BADGER-TOPS*.cn4``）用 **点号** 风格。

    二者都是合法 Fortran 输出（取决于编译器/编辑描述符写法），
    Python 的 ``f"{v:12.6E}"`` 与 **点号** 风格一致。为保证
    byte-identical 往返，调用方需按源文件风格选择。
    """
    if style == "dotted":
        s = f"{v:12.{dec}E}"
        return s                    # Python 默认即 d.ddddddE±ee

    # ``:.{dec}E`` -> ``d.ddddddE±ee``（精度与前导零由 dec 决定）
    mant, _, exp = f"{v:.{dec}E}".partition("E")
    if not exp:
        return f"{v:.{dec}E}"
    neg = mant.startswith("-")
    m = mant.lstrip("-")
    intpart, _, frac = m.partition(".")

    # ★ 归一化为 Fortran 的 ``0.dddddd`` 时，尾数**右移一位**（d.dddd -> 0.ddddd），
    #   因此指数必须 **+1** 补偿，否则数值会被静默放小 10 倍。
    #       2.000000E+00 -> 0.200000E+01   （不是 E+00！）
    exp_i = int(exp[1:]) * (1 if exp[0] == "+" else -1)
    if intpart != "0":
        exp_i += 1

    # 尾数总位数 = 1 个前导 0 + dec 位小数；整数部分并入后重新截取 dec 位。
    digits = (intpart + frac)[:dec]
    if len(digits) < dec:
        digits = digits.ljust(dec, "0")

    # ★ 负值：Fortran 实测写法是 ``-.370029E-04``（**省略前导 0**，保留 dec 位
    #   小数），因此字段宽 13 列而非 12 列。这是 Fortran ``e12.6`` 的真实行为，
    #   读取侧靠定宽切分 + 正则容忍。**不要**为了凑 12 列而缩小数位 ——
    #   那会破坏 byte-identical 往返（实测 he-imx-005.cn4 等多份文件受影响）。
    if neg:
        return f"-." + digits + f"E{_exp_fortran(exp_i)}"
    return "0." + digits + f"E{_exp_fortran(exp_i)}"


def _exp_fortran(exp_i: int) -> str:
    """Fortran 指数字段：恒 2 位（``+01`` / ``-01``），3 位则原样。"""
    sign = "+" if exp_i >= 0 else "-"
    a = abs(exp_i)
    return f"{sign}{a:02d}" if a <= 99 else f"{sign}{a}"


def _fmt_e12_6(v: float, style: str = "leading0") -> str:
    """Fortran ``e12.6`` 单字段: **恒 12 列**、6 位小数。

    合法输出形如 ``0.100000E+01``（12 列）。三类边界必须显式处理，
    否则会破坏定宽切分并导致后续字段**静默错位**（实测缺陷）::

        -0.5      ->  '-5.000000E-01'   13 列  (负号吃掉前导空格)
        1e-140    ->  '1.000000E-140'   13 列  (3 位指数)
        nan       ->  '         NAN'    12 列但非法

    修复规则（三种，均有实证）:

    1. **负号使字段变 13 列** → 缩短尾数小数位，保证总宽 12。
       Fortran ``e12.6`` 遇负号确实会写出 13 列（本项目的解析器因此
       专门做定宽切分），但**写出方**必须保证对齐，否则一次错位污染整行。
    2. **3 位指数** → 复刻 Fortran 运行时的行为：**丢弃 ``E``**，
       得 ``0.638380-140``（正好 12 列）。这正是
       :data:`_PACKED_EXP_RE` 在读取侧要修复的形态，写出侧必须一致。
    3. **NaN / ±Inf** → 写 :data:`NAN_PLACEHOLDER`（``-1.000000E+99``），
       12 列对齐，读回后由 :func:`is_nan_placeholder` 还原。
    """
    # ── 3: NaN / Inf -> 占位（字面 12 列，见 NAN_PLACEHOLDER_FIELD） ──
    if v != v or v in (float("inf"), float("-inf")):
        return NAN_PLACEHOLDER_FIELD

    # ── 常规路径 ──
    # ★ 必须归一化尾数为 Fortran 的 ``0.ddddddE±ee`` 形态（前导 0），
    #   而不是 Python ``f"{v:12.6E}"`` 的 ``d.ddddddE±ee``。
    #   两者数值相同、宽度同为 12 列，但**逐字节比较**会不一致：
    #       源文件: 0.200000E+01       Python: 2.000000E+00
    #   本项目的往返校验要求 byte-identical，故必须复刻 Fortran 写法。
    s = _fortran_e12_6(v, style=style)

    # ── 2: 3 位指数 -> 复刻 Fortran 丢 ``E`` ──
    #    实测 ``0.638380-140``（正好 12 列）；负值形如 ``-.63838-140``（12 列）。
    m = re.fullmatch(r"(-?0?\.\d{6})E([-+]\d{3})", s)
    if m:
        mant, ex = m.group(1), m.group(2)
        if mant.startswith("-."):
            # ``-.638380-140`` = 13 列 -> Fortran 会缩 1 位小数 -> ``-.63838-140``
            mant = "-." + mant[2:][:5]
        packed = f"{mant}{ex}"
        if len(packed) == FIXED_WIDTH:
            return packed
        return packed[:FIXED_WIDTH].rjust(FIXED_WIDTH)

    # ── 正/负常规（12 或 13 列）──
    # ★ 负值实测为 **13 列**（``-.370029E-04``，省略前导 0），这是 Fortran
    #   ``e12.6`` 的真实行为；读取侧靠定宽切分 + 正则容忍。**不要**为了凑
    #   12 列而缩小数位 —— 会破坏 byte-identical 往返（实测多份文件中招）。
    return s


def _write_block(fh, flat: Iterable[float], what: str, *, per_line: int = 4,
                 style: str = "leading0") -> int:
    """按 ``4e12.6`` 写出一个块（每行 4 个值）。返回写出的数值个数。"""
    n = 0
    buf: List[str] = []
    for v in flat:
        buf.append(_fmt_e12_6(v, style))
        n += 1
        if len(buf) == per_line:
            fh.write("".join(buf) + "\n")
            buf = []
    if buf:
        fh.write("".join(buf) + "\n")
    return n


def write_cn4(table: CN4Table, out_path: str | os.PathLike, *,
              write_opacities: bool = True,
              mantissa_style: str | None = None,
              verbatim: bool = False) -> Path:
    """把 :class:`CN4Table` 写回 cn4 格式。

    严格复刻 ``OWTF`` 的 ``write(123, ...)`` 序列与 ``4e12.6`` 定宽编码，
    因此 ``parse_cn4(write_cn4(t))`` 应逐位回读（见 test 往返校验）。

    Args:
        table: 源表（须已含 12 个二维场；三维场可在 ``write_opacities=False``
            时以零填充 —— 用于"仅 EOS 不含不透明度"的降级写出）
        out_path: 目标路径（``.cn4`` 后缀自动补全）
        write_opacities: 是否写出三维不透明度块。``False`` 时写零占位，
            **块数与计数保持不变**（保持格式合法）。
        verbatim: ★ 原生直通模式。当源表带有逐字数据区文本
            （``table.data_raw``，仅 ``parse_cn4`` 直读原生 cn4 时存在）时，
            头部按现有逻辑复刻、数据区**逐字节原样回写**，从而实现
            cn4→cn4 往返 byte-identical（含同一文件内混用两种尾数风格、
            ``-Infinity`` 字面量等逐值重排无法复刻的情形）。与
            ``write_opacities=False`` 或显式 ``mantissa_style`` 互斥。

    Returns:
        实际写出的 ``Path``
    """
    out = Path(out_path)
    if out.suffix.lower() != ".cn4":
        out = out.with_suffix(".cn4")
    out.parent.mkdir(parents=True, exist_ok=True)

    ntemp, ndens, ngrups = table.ntemp, table.ndens, table.ngrups
    n2d, n3d = ntemp * ndens, ngrups * ntemp * ndens
    z3 = [0.0] * n3d

    # ★ 尾数风格：默认自动探测（源表若带 ``notes``/``layout_rule`` 线索或
    #   已有原生数组则沿用），否则用 Ionmix 的 "leading0"。
    style = mantissa_style or _detect_mantissa_style(table)
    if style not in ("leading0", "dotted"):
        raise CN4ParseError(f"未知的尾数风格 {style!r}（应 'leading0' 或 'dotted'）")

    with out.open("w", encoding="latin-1", newline="\n") as fh:
        # ── 头部（格式 923 / 921 / 922 / 982） ──
        # ★ 若源表带有**原始头部文本**（``parse_cn4`` 会保留），直接逐行复用，
        #   以保证 byte-identical 往返。不同生产者对前 3 行的尾部填充不一致：
        #       Ionmix/OWTF 产物 -> 补齐到 80 列
        #       CH-BADGER-TOPS-Final.cn4 -> 无填充（20/31/31 列）
        #   强行统一任一风格都会让另一风格往返失败，故"原样保留"才是正解。
        #   仅当头部缺失（如跨族转换新造的表）时才按 Fortran 风格生成。
        hdr = [h for h in (table.header_raw or []) if h is not None]
        if len(hdr) >= 3:
            for line in hdr[:3]:
                fh.write(line + "\n")
            # 第 4 行是 ngrups（i12）；源头部可能带旧值，以表字段为准
            fh.write(f"{ngrups:12d}" + "\n")
        else:
            fh.write(_pad80(f"{ntemp:10d}{ndens:10d}") + "\n")        # 923: 2i10
            zs = "".join(f"{z:10d}" for z in table.izgas)
            fh.write(_pad80(f" atomic #s of gases: {zs}") + "\n")     # 921
            fs = "".join(f"{f:10.2E}" for f in table.fracsp)
            fh.write(_pad80(f" relative fractions: {fs}") + "\n")     # 922
            fh.write(f"{ngrups:12d}" + "\n")                          # 982: i12

        # ── ★ verbatim 直通：数据区逐字节回写（头部已按上逻辑复刻） ──
        if verbatim:
            if table.data_raw is None:
                raise CN4ParseError(
                    "verbatim=True 需要源表带 data_raw（仅 parse_cn4 直读"
                    "原生 cn4 时保留；跨族转换新造的表请走常规路径）"
                )
            if not write_opacities or mantissa_style is not None:
                raise CN4ParseError(
                    "verbatim=True 与 write_opacities=False / mantissa_style "
                    "互斥（直通即源文本，无重排自由度）"
                )
            fh.write(table.data_raw)
            return out

        # ── block 1, 2 ──
        _write_block(fh, table.temperature, "tplsma", style=style)
        _write_block(fh, table.density, "densnn", style=style)

        # ── block 3..14（顺序见 BLOCK_SPEC，与 OWTF 完全一致） ──
        for attr, _label, _unit, _src in BLOCK_SPEC:
            blk = table.fields2d.get(attr)
            if blk is None:
                raise CN4ParseError(f"缺失二维场 '{attr}'，无法写出完整 cn4")
            if len(blk) != n2d:
                raise CN4ParseError(
                    f"场 '{attr}' 长度 {len(blk)} != ndens*ntemp={n2d}"
                )
            _write_block(fh, blk, attr, style=style)

        # ── block 15 ──
        _write_block(fh, table.group_bounds, "engrup", style=style)

        # ── block 16..18 ──
        for attr, _label, _unit, _src in OPACITY_SPEC:
            if write_opacities:
                blk = table.opacities.get(attr)
                if blk is None:
                    blk = z3
                elif len(blk) != n3d:
                    raise CN4ParseError(
                        f"不透明度 '{attr}' 长度 {len(blk)} != {n3d}"
                    )
            else:
                blk = z3
            _write_block(fh, blk, attr, style=style)

    return out


def parsed_tables_to_cn4(tables: Sequence, *,
                         atomwt: Optional[Sequence[float]] = None,
                         izgas: Optional[Sequence[int]] = None,
                         fracsp: Optional[Sequence[float]] = None,
                         allow_foreign: bool = False) -> CN4Table:
    """把 ``ParsedTable`` 列表**反向**组装回 :class:`CN4Table`。

    两种用法
    --------
    1. **cn4 往返**（默认，``allow_foreign=False``）

       要求 ``tables`` 含一张 ``family == "cn4"`` 的 EOS 总表；不透明度表
       可选（缺失时三维块以 :data:`NAN_PLACEHOLDER_FIELD` 填充，保持格式合法
       且可被 :func:`is_nan_placeholder` 识别为"缺数据"）。

    2. **跨族转换**（``allow_foreign=True``）

       接受**任意**族的 ``ParsedTable``（F1–F6），把它当作"物料源"组装成
       cn4。这是"其他文件类型 -> cn4"的入口。此时：

       * EOS 总表：取任一 ``kind == "EOS_TOTAL"`` 的表（不限族）
       * 二维场：按 :data:`BLOCK_SPEC` 逐项求值；**源表没有的场写 NaN 占位**
         （不写 0 —— 0 是合法物理值，会被误读为真实数据）
       * 不透明度：按 ``ROSSELAND`` / ``PLANCK`` / ``EMISSIVITY`` 匹配；
         **缺失的整块写 NaN 占位**
       * 能群边界：取自任一不透明度表的 ``group_bounds``；缺失则置 NaN

       ⚠️ **单位不换算**：跨族单位差异很大（LEDCOP 用 keV、F1/F4 用 Mbar、
       ionmix 用 J/cm3）。本函数**不做**单位猜测，只在 ``notes`` 里记录来源
       族的单位体系，由调用方决定是否换算。若强行猜单位，错误会静默传播。

    Args:
        tables: ``ParsedTable`` 序列
        atomwt: 原子量列表（可选，缺省走 ``guess_atomwt``）
        izgas: 原子序数列表（**cn4 头部必需**）
        fracsp: 丰度列表（**cn4 头部必需**）
        allow_foreign: 是否允许非 cn4 族作为数据源

    Raises:
        CN4ParseError: 缺 EOS 总表 / 缺 izgas/fracsp / 长度不一致
    """
    from .base import ParsedTable

    #: 等价于"EOS 总表"的 kind 名。
    #: ``cn4_eos`` 是 ionmix 解析器对 ``.cn4`` 的命名（该族把 EOS 与
    #: 三块不透明度**合并在同一张表**里，见 ``parsers/ionmix.py``）。
    _EOS_KINDS = ("EOS_TOTAL", "cn4_eos")
    _OPAC_KINDS = ("ROSSELAND", "PLANCK", "EMISSIVITY")

    eos = None
    opacs: dict[str, ParsedTable] = {}
    foreign_families: set[str] = set()
    for t in tables:
        if not isinstance(t, ParsedTable):
            continue
        allowed = (t.family == "cn4" or allow_foreign)
        if not allowed:
            continue
        if t.kind in _EOS_KINDS:
            if eos is None or t.family == "cn4":
                eos = t
            foreign_families.add(t.family)
        elif t.kind in _OPAC_KINDS:
            opacs.setdefault(t.kind, t)
            foreign_families.add(t.family)
        # ★ 兜底：某些族把不透明度画在 kind=EOS_TOTAL 的表里而不另开表。
        #   只要表里**确实存在**已知的不透明度字段名，就登记为不透明度源，
        #   否则 cn4 -> cn4 往返时这三块会被误判为"缺失 -> NaN 占位"。
        if t.kind in _EOS_KINDS:
            for k in _OPAC_KINDS:
                if any(nm in t.fields
                       for nm in _FOREIGN_OPACITY_ALIASES.get(k, ())):
                    opacs.setdefault(k, t)
    if eos is None:
        hint = ("（已开启 allow_foreign，但仍未找到任何 EOS 总表；"
                f"接受的 kind = {list(_EOS_KINDS)}）"
                if allow_foreign else
                "（若源数据非 cn4 族，请加 allow_foreign=True）")
        raise CN4ParseError(f"parsed_tables_to_cn4: 未找到可用的 EOS_TOTAL 表{hint}")

    if izgas is None or fracsp is None:
        raise CN4ParseError(
            "parsed_tables_to_cn4 需要显式 izgas 与 fracsp（cn4 头部必需）"
        )
    if len(izgas) != len(fracsp):
        raise CN4ParseError(
            f"izgas({len(izgas)}) 与 fracsp({len(fracsp)}) 长度不一致"
        )

    is_foreign = bool(foreign_families - {"cn4"})
    notes: List[str] = []

    # ── 网格：cn4 走原生轴名；跨族走"轴归一化 + 质量密度换算" ──
    aw_for_grid = None
    if atomwt is not None and len(atomwt) == len(izgas):
        aw_for_grid = float(sum(f * a for f, a in zip(fracsp, atomwt)))
    elif guess_atomwt(izgas) is not None:
        aw_for_grid = float(sum(f * a for f, a in
                                zip(fracsp, guess_atomwt(izgas))))

    if is_foreign:
        Te, nion, grid_info = _resolve_foreign_grid(eos, aw_for_grid)
        notes.append(grid_info)
        if aw_for_grid is not None:
            notes.append(f"平均原子量 <A> = {aw_for_grid:.6g} amu（用于密度换算）")
    else:
        Te = list(eos.axes["Te"])
        nion = list(eos.axes["nion"])
    ntemp, ndens = len(Te), len(nion)

    # 反查真值: 默认取该 cn4 的主网格
    ngrups = 0
    group_bounds: List[float] = []
    for t in opacs.values():
        if t.n_groups:
            ngrups = int(t.n_groups)
            group_bounds = list(t.group_bounds or [])
            break

    def _to_density_major(flat: Sequence[float], shape) -> List[float]:
        """(n_Te, n_x) 或 (ng, n_Te, n_x) -> cn4 的 density-major 扁平序。"""
        if len(shape) == 2:
            n_T, n_x = shape
            return [flat[j * n_x + i] for i in range(n_x) for j in range(n_T)]
        if len(shape) == 3:
            ng, n_T, n_x = shape
            out: List[float] = []
            n2 = n_T * n_x
            for g in range(ng):
                base = g * n2
                out.extend(flat[base + j * n_x + i]
                           for i in range(n_x) for j in range(n_T))
            return out
        raise CN4ParseError(f"不支持的场形状 {shape}")

    n2d = ntemp * ndens
    nan_block = [float("nan")] * n2d

    def _find_field(table: ParsedTable, names: Sequence[str]):
        """在给定表里按候选名找一个可用场；返回 ``(flat, shape)`` 或 ``None``。"""
        for nm in names:
            if nm in table.fields:
                return table.fields[nm], _guess_shape(table, nm)
        return None

    def _guess_shape(table: ParsedTable, nm: str):
        """推断字段形状：优先 ``field_shape``，否则由**实际轴长**推导。

        注意不能用固定的 ``("Te", "nion")`` —— 跨族表的密度轴叫 ``rho``，
        固定名会得到长度 0，从而把可用字段误判为"形状不匹配 -> NaN 占位"。
        """
        sh = table.field_shape.get(nm)
        if sh:
            return sh
        lens = [len(v) for v in getattr(table, "axes", {}).values()
                if isinstance(v, (list, tuple))]
        return tuple(lens) if lens else ()

    def _find_field_named(table: ParsedTable, names: Sequence[str]):
        """同 :func:`_find_field`，但额外返回**实际命中的字段名**（审计用）。"""
        for nm in names:
            if nm in table.fields:
                return nm, (table.fields[nm], _guess_shape(table, nm))
        return None, None

    fields2d: dict[str, List[float]] = {}
    foreign_slots_used: List[str] = []
    #: ★ 单温总 EOS（mpqeos / hyades / …）只有**总压强/总比能**，
    #: 而 cn4 要求 ``p_ion``/``p_ele`` 分列。若把总量只塞给 ion 槽，
    #: 则 ele 槽变 NaN，导致读取侧 ``P = p_ion + p_ele`` == NaN ——
    #: **自相矛盾**（表里有 P 但合成 P 是 NaN），下游绘图/雨贡纽全崩。
    #: 故此处记录"由总量均分而来"的槽位，稍后做等分投影，保证
    #: ``p_ion + p_ele == P`` 与 ``e_ion + e_ele == E`` 恒成立。
    total_split: dict[str, tuple[str, List[float]]] = {}
    for attr, label, _unit, _src in BLOCK_SPEC:
        hit = None
        used_name = None
        # ① 优先：源表里就叫 cn4 的原生标签（cn4 往返路径）
        if label in eos.fields:
            hit = (eos.fields[label], eos.field_shape.get(label, (ntemp, ndens)))
            used_name = label
        # ② 其次：按别名表找等价物理量（跨族路径）
        if hit is None:
            cands = _FOREIGN_FIELD_ALIASES.get(attr, ())
            for tbl2 in (eos, *opacs.values()):
                nm, h2 = _find_field_named(tbl2, cands)
                if h2 is not None:
                    hit = h2
                    used_name = nm
                    break
        if hit is None:
            # ★ 缺失 -> NaN 占位（不是 0；0 会被当成真实物理数据）
            fields2d[attr] = list(nan_block)
            notes.append(f"字段 '{attr}' 在源数据中不存在 -> NaN 占位")
        else:
            flat, shape = hit
            if not (len(shape) == 2 and shape == (ntemp, ndens)):
                # 形状不匹配 -> 无法安全重排，占位并记录
                fields2d[attr] = list(nan_block)
                notes.append(
                    f"字段 '{attr}' 形状 {shape} != ({ntemp}, {ndens}) -> NaN 占位")
            else:
                fields2d[attr] = _to_density_major(flat, shape)
                if used_name != label:
                    foreign_slots_used.append(f"{attr}<-'{used_name}'")
                    if attr in _TOTAL_PLACED_IN_ION_SLOT:
                        # ★ 记下"这是总量"，待 ele 槽处理时等分
                        total_split[attr] = (
                            used_name, list(fields2d[attr]))

    # ★ 单温 -> 双温投影：把总量均分给 ion / ele 两槽。
    #    仅在**对偶槽位仍是 NaN 占位**（即源数据确实没有分项）时执行，
    #    绝不覆盖源表真实提供的分项。
    for ion_attr, ele_attr in _TOTAL_SPLIT_PAIRS:
        if ion_attr not in total_split:
            continue
        src_name, ion_vals = total_split[ion_attr]
        ele_cur = fields2d.get(ele_attr)
        if ele_cur is None or not _all_nan(ele_cur):
            continue                      # 有真实分项 -> 不覆盖
        half = [v / 2.0 if fin else v for v, fin in
                ((v, v == v) for v in ion_vals)]
        fields2d[ion_attr] = list(half)
        fields2d[ele_attr] = list(half)
        notes.append(
            f"单温总 EOS：'{src_name}' 是**总量**，已按 1:1 均分到 "
            f"'{ion_attr}'/''{ele_attr}'（保证 {ion_attr}+{ele_attr} 守恒）；"
            f"这是单温->双温的保守投影，非真实分项"
        )

    opacities: dict[str, List[float]] = {}
    n3d = ngrups * ntemp * ndens
    nan3d = [float("nan")] * n3d
    for attr in ("opac_rosseland", "opac_planck_abs", "opac_planck_ems"):
        kind = {"opac_rosseland": "ROSSELAND", "opac_planck_abs": "PLANCK",
                "opac_planck_ems": "EMISSIVITY"}[attr]
        # ── ① cn4 原生标签优先（cn4 -> cn4 往返路径） ──
        hit = None
        used_name = None
        src_desc = ""
        tbl_cn4 = opacs.get(kind)
        if tbl_cn4 is not None:
            # 新命名（字典登记名）优先，兼容旧 kappa_g
            for cand in (attr, "kappa_g"):
                if cand in tbl_cn4.fields:
                    hit = tbl_cn4.fields[cand]
                    used_name = cand
                    src_desc = f"kind={kind}"
                    break
        # ── ② 跨族：先在 "同 kind" 的表里按别名找，再放开到任意 kind ──
        if hit is None:
            # ⚠️ ``_FOREIGN_OPACITY_ALIASES`` 的键是**kind**（ROSSELAND/...），
            #    不是 cn4 的属性名（opac_rosseland/...）。用 attr 查会永远得到
            #    空元组，从而静默退化成"缺失 -> NaN 占位"。
            cands = _FOREIGN_OPACITY_ALIASES.get(kind, ())
            for k_try in _OPAC_KIND_ALIASES.get(kind, (kind,)):
                t = opacs.get(k_try)
                if t is None:
                    continue
                nm, h2 = _find_field_named(t, cands)
                if h2 is not None:
                    hit, used_name = h2[0], nm
                    src_desc = f"kind={k_try}"
                    break
            # 同表兜底：不透明度可能与 EOS 同表（ionmix .cn4）
            if hit is None:
                nm, h2 = _find_field_named(eos, cands)
                if h2 is not None:
                    hit, used_name = h2[0], nm
                    src_desc = f"kind={eos.kind}(同表)"
        if hit is not None:
            # 形状必须与目标网格自洽，否则 _to_density_major 会静默错位
            t_src = None
            for k_try in _OPAC_KIND_ALIASES.get(kind, (kind,)):
                t = opacs.get(k_try)
                if t is not None and used_name in t.fields:
                    t_src = t
                    break
            if t_src is None and used_name in eos.fields:
                # 不透明度与 EOS 同表（如 ionmix .cn4）
                t_src = eos
            shape = (t_src.field_shape.get(used_name, (ngrups, ntemp, ndens))
                     if t_src is not None else (ngrups, ntemp, ndens))
            ok_shape = (len(shape) == 3 and shape[1] == ntemp
                        and shape[2] == ndens)
            if not ok_shape:
                notes.append(
                    f"不透明度块 '{attr}' 形状 {shape} 与网格 "
                    f"(ng={ngrups}, nT={ntemp}, nx={ndens}) 不符 -> NaN 占位")
                hit = None
            else:
                flat = _to_density_major(hit, shape)
                if len(flat) != n3d:
                    notes.append(f"不透明度块 '{attr}' 长度不符 -> NaN 占位")
                    hit = None
                else:
                    opacities[attr] = flat
                    if used_name != "kappa_g":
                        foreign_slots_used.append(f"{attr}<-'{used_name}'")
                    if ngrups == 0:
                        notes.append(
                            f"不透明度块 '{attr}' 取自 {src_desc} 的 "
                            f"'{used_name}'，但源无辐射能群 (ngrups=0)"
                            " -> 该块在 cn4 中不可寻址（保留占位）")
        if hit is None:
            # ★ 缺失 -> NaN 占位（原实现写 0.0，会把"没有数据"伪装成"不透明=0"）
            opacities[attr] = list(nan3d) if ngrups else []
            if not any(f"不透明度块 '{attr}'" in n for n in notes):
                notes.append(f"不透明度块 '{attr}' 缺失 -> NaN 占位")

    # ★ 能群边界长度必须恒为 ``ngrups + 1``（含 ngrups=0 的退化情形——
    #   纯 EOS 源没有辐射群，但 cn4 布局仍要求 1 个 engrup 数值）。
    #    否则写出侧会少 1 个数，读回时"数值个数不守恒"。
    if len(group_bounds) != ngrups + 1:
        notes.append(
            f"能群边界长度 {len(group_bounds)} != ngrups+1={ngrups + 1} "
            "-> 用 NaN 补齐/截断")
        group_bounds = (list(group_bounds) + [float("nan")] * (ngrups + 1)
                        )[:ngrups + 1]

    if is_foreign:
        notes.append(
            "跨族转换 (" + ", ".join(sorted(foreign_families - {"cn4"})) + ")："
            "**物理量数值保持源族原始单位**（未做 P/E/cv 的单位换算，"
            "各族单位体系差异大，需调用方按需换算）；"
            f"源族单位来源 = {eos.unit_source or 'unknown'}")

    # ★ 来源族（第十二轮）：取首个非 cn4 来源族名；绘图标签经
    #   plotting.style.labels.cn4_tags 用它回查该族认证标记。
    foreign_named = sorted(foreign_families - {"cn4"})
    origin_family = foreign_named[0] if foreign_named else ""

    return CN4Table(
        filepath=str(eos.source_relpath),
        ntemp=ntemp, ndens=ndens, ngrups=ngrups, ngases=len(izgas),
        izgas=list(izgas), fracsp=list(fracsp),
        atomwt=list(atomwt) if atomwt is not None else guess_atomwt(izgas),
        temperature=Te, density=nion,
        fields2d=fields2d, group_bounds=group_bounds, opacities=opacities,
        header_raw=list(eos.header_raw.split(" | ")) if eos.header_raw else [],
        unit_source=eos.unit_source,
        layout_rule=("parsed_tables_to_cn4: 由 ParsedTable 组装的 cn4"
                     + ("（跨族）" if foreign_families - {"cn4"} else "")),
        n_numbers_seen=0,
        n_numbers_expected=expected_number_count(ntemp, ndens, ngrups),
        atomwt_source="user" if atomwt is not None else (
            "element_table" if guess_atomwt(izgas) is not None else "unavailable"
        ),
        origin_family=origin_family,
        notes=notes,
    )


#: 跨族转换时，各族物理量名 -> cn4 二维场的候选等价名。
#:
#: 命名约定实测
#: ------------
#: * F6 cn4 原生：``zbar`` / ``p_ion`` / ``p_ele`` / ``e_ion`` / ``e_ele`` …
#: * F3 hyades：``P`` (dyne/cm2) / ``E`` (erg/g) —— **总量**，无离子/电子之分
#: * F4 mpqeos：``P`` (Mbar) / ``E`` (Mbar*cm3/g) / ``Z`` —— 同上 + 电离度
#: * F5 ledcop：``Ross`` / ``Planck``（不透明度），电离度在单独文件中
#:
#: ★ **保守**：只列"物理意义明确等价"的名字。含义存疑的一律不列，
#: 宁可写 NaN 占位让人看见"这里没有数据"，也不要错配一个数值。
#:
#: ⚠️ **总量语义**：``P`` / ``E`` 是"总压强/总比能"（离子+电子之和）。
#: cn4 把二者分开存。这里把总量放进 **离子分量槽**（``p_ion`` / ``e_ion``）,
#: 并在 ``notes`` 里标注 —— 因为 cn4 没有"总量槽"，而离子槽语义更接近
#: "物质主体分量"。调用方若需要分项，须自行从源族取电子分量。
_FOREIGN_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "zbar":     ("zbar", "Z", "z", "zeff", "Zbar", "zbar_avg"),
    "dzdt":     ("dzdt",),
    "p_ion":    ("p_ion", "P_ion", "pion", "P_i", "P"),
    "p_ele":    ("p_ele", "P_ele", "pele", "P_e"),
    "dpion_dt": ("dpion_dt", "dP_dT"),
    "dpele_dt": ("dpele_dt",),
    "e_ion":    ("e_ion", "E_ion", "eion", "E_i", "E"),
    "e_ele":    ("e_ele", "E_ele", "eele", "E_e"),
    "cv_ion":   ("cv_ion", "Cv_ion", "cvion", "Cv"),
    "cv_ele":   ("cv_ele", "Cv_ele", "cvele"),
    "deion_dn": ("deion_dn", "dP_drho"),
    "deele_dn": ("deele_dn",),
}

#: 跨族的不透明度字段候选名（``kind -> 候选字段名``）。
#:
#: * F6 cn4 / F5 ionmix：``kappa_g`` / ``kappa_rosseland`` 等
#: * F5 ledcop：``Ross`` (Rosseland) / ``Planck`` (Planck 吸收)
#:   —— ledcop 主表同时含两列，族内 ``kind`` 只声明其一，
#:   故这里允许跨 ``kind`` 取名（见 ``_OPAC_KIND_ALIASES``）。
_FOREIGN_OPACITY_ALIASES: dict[str, tuple[str, ...]] = {
    "ROSSELAND": ("kappa_g", "kappa_rosseland", "kappa_r", "Ross", "rosseland",
                  "opac_rosseland", "k_ross"),
    "PLANCK":    ("kappa_g", "kappa_planck", "kappa_planck_abs", "Planck",
                  "planck", "opac_planck_abs", "k_planck"),
    "EMISSIVITY": ("kappa_g", "kappa_planck_ems", "kappa_emissivity",
                   "opac_planck_ems", "k_ems"),
}

#: ``kind`` -> 可接受的 ``kind`` 别名（用于跨族时"一张表含多列"的情形）。
_OPAC_KIND_ALIASES: dict[str, tuple[str, ...]] = {
    "ROSSELAND": ("ROSSELAND",),
    "PLANCK": ("PLANCK", "EMISSIVITY"),
    "EMISSIVITY": ("EMISSIVITY", "PLANCK"),
}

#: 这些 cn4 槽位填入的是**源族的"总量"**而非分项，需在 notes 里标注。
_TOTAL_PLACED_IN_ION_SLOT: tuple[str, ...] = ("p_ion", "e_ion", "cv_ion")

#: 单温总 EOS -> 双温 cn4 的**均分对**：``(ion 槽, ele 槽)``。
#:
#: 适用族（实测只有总量）：``mpqeos``(.301, 字段 ``P``/``E``)、
#: ``hyades_eos``(``P``/``E``)。``feos_native`` 的 16 块已定案解码
#: （FE-01_TABTOOLS.C::write_FEOS_format，见 parsers/feos_native.py），
#: 自带 Pi/Pe/Ei/Ee 分项、无需均分 —— 原生 .feos → cn4 走
#: ``feos/feos_run/feos_to_cn4.py``（含 zbar=Qtot/Xtot 归一与不透明度零填充）。
#: 均分理由：cn4 是**双温**模型，要求 ``p_ion`` 与 ``p_ele`` 分列；
#: 单温源只给总压。若把总量只塞 ion 槽，则读取侧 ``P = p_ion + p_ele``
#: 得到 NaN，与"表里明明有 P"自相矛盾。等分保证守恒且不抛异常。
#: ⚠️ 这是**保守投影**（真实电子/离子分配随 T、ρ 变化），必须在 notes
#: 明确标注，避免下游误当真实分项。
_TOTAL_SPLIT_PAIRS: tuple[tuple[str, str], ...] = (
    ("p_ion", "p_ele"),
    ("e_ion", "e_ele"),
    ("cv_ion", "cv_ele"),
)


def _all_nan(values) -> bool:
    """``values`` 是否**全部**为 NaN（空序列视为 True）。"""
    for v in values:
        if v == v:                        # 非 NaN
            return False
    return True

#: 温度轴的候选名（按优先级）。**只列真正的温度**（eV）。
#:
#: ⚠️ 刻意**不含** F1 的 ``de`` —— 那是 ``Mbar*cm3/g``（比内能），
#: 不是温度。若误当温度轴，整张表会静默错位。
_FOREIGN_T_AXES: tuple[str, ...] = ("Te", "T", "tele", "T_e", "Tion", "Ti")

#: 密度轴的候选名（按优先级）与其**单位**。
#:
#: 值 = ``(单位字符串, 是否为质量密度 g/cm^3)``。
#: 质量密度需经 ``n = rho * N_A / <A>`` 换成 cn4 要求的数密度 (cm^-3)。
_FOREIGN_RHO_AXES: tuple[tuple[str, str, bool], ...] = (
    ("nion", "cm^-3", False),
    ("ni",   "cm^-3", False),
    ("n_i",  "cm^-3", False),
    ("rho",  "g/cm3", True),
    ("rhoe", "g/cm3", True),
    ("dens", "g/cm3", True),
    ("x",    "g/cm3", True),
)


def _pick_axis(table, names: Sequence[str]):
    """在 ``table.axes`` 里按候选名取第一个存在的轴；返回 ``(name, values)``。"""
    for nm in names:
        if nm in table.axes and len(table.axes[nm]):
            return nm, list(table.axes[nm])
    return None, None


def _resolve_foreign_grid(eos, avg_atomwt: Optional[float]):
    """把任意族的 (温度轴, 密度轴) 归一化成 cn4 要求的 ``(Te_eV, n_ion_cm-3)``。

    Returns:
        ``(Te, n_ion, info)``；``info`` 是给 ``notes`` 用的人读说明。
        无法确定轴时抛 :class:`CN4ParseError`（**不猜**）。

    换算依据
    --------
    质量密度 -> 数密度: ``n_ion = rho * N_A / <A>``
    （``<A>`` 单位 amu；由 ``config`` 的 ``N_A`` 与调用方给的 ``atomwt`` 决定）。
    """
    t_name, Te = _pick_axis(eos, _FOREIGN_T_AXES)
    if t_name is None:
        raise CN4ParseError(
            f"跨族转换: 在 '{eos.family}' 表里找不到温度轴 "
            f"（候选 {list(_FOREIGN_T_AXES)}；实际轴 = {sorted(eos.axes)}）")

    r_name = r_kind = None
    rho = None
    for nm, unit, is_mass in _FOREIGN_RHO_AXES:
        if nm in eos.axes and len(eos.axes[nm]):
            r_name, r_kind, rho = nm, (unit, is_mass), list(eos.axes[nm])
            break
    if r_name is None:
        raise CN4ParseError(
            f"跨族转换: 在 '{eos.family}' 表里找不到密度轴 "
            f"（候选 {[c[0] for c in _FOREIGN_RHO_AXES]}；"
            f"实际轴 = {sorted(eos.axes)}）")

    unit, is_mass = r_kind
    info = f"轴归一化: T <- '{t_name}' ({eos.axis_units.get(t_name, 'eV')}), " \
           f"n_ion <- '{r_name}' ({unit})"
    if is_mass:
        if avg_atomwt is None:
            raise CN4ParseError(
                f"跨族转换: 密度轴 '{r_name}' 是质量密度 ({unit})，"
                "换算成数密度需要平均原子量 <A>，但无法确定"
                "（请显式传 atomwt= 或 izgas= 以便查表）")
        n_ion = [r * NA / avg_atomwt for r in rho]
        info += f"；已换算 质量密度->数密度 (乘 N_A/<A>={NA / avg_atomwt:.6g})"
    else:
        n_ion = rho

    return list(Te), n_ion, info


def convert_foreign_to_cn4(src: str | os.PathLike, dst: str | os.PathLike, *,
                           family: Optional[str] = None,
                           izgas: Sequence[int],
                           fracsp: Sequence[float],
                           atomwt: Optional[Sequence[float]] = None,
                           **opts) -> Path:
    """**其他格式族 -> cn4** 的转换入口（用户级便利函数）。

    缺失的数据用 :data:`NAN_PLACEHOLDER_FIELD` 占位，12 列对齐，
    读回后由 :func:`is_nan_placeholder` 还原为 ``nan``。

    Args:
        src: 源文件（任意受支持族）
        dst: 输出 ``.cn4`` 路径
        family: 强制指定族名（``None`` = 走声明表自动识别）
        izgas / fracsp: cn4 头部必需的组成信息（**不猜**）
        atomwt: 原子量（可选）

    Returns:
        写出的 ``.cn4`` 路径
    """
    from ..registry.identify.dispatch import FAMILY_PARSERS
    from ..registry.schema.declared_types import declare

    srcp = Path(src)
    tables = None
    tried: List[str] = []
    if family:
        fams: List[str] = [family]
    else:
        # ★ 必须传**完整路径**而非 ``.name``：``declare`` 的路径规则
        #   （如 "路径含 ATOMIC -> ledcop" / "路径含 Ionmix -> ionmix"）
        #   依赖目录名。只传 basename 会绕过所有路径规则，退化到 Readme.txt
        #   的默认候选（SESAME），从而把 LEDCOP 等族表误判为 SESAME。
        #   相对 ``matter++`` 根时传相对路径最好；非 matter++ 路径传绝对路径，
        #   路径规则里的 ``/atomic/`` 等子串仍能命中。
        try:
            from ..core.config import MATTER_DIR as _MD
            _rel = os.path.relpath(str(srcp), str(_MD)).replace("\\", "/")
            if _rel.startswith(".."):
                _rel = str(srcp).replace("\\", "/")
        except Exception:                                  # noqa: BLE001
            _rel = str(srcp).replace("\\", "/")
        dt = declare(_rel)
        fams = list(getattr(dt, "families", ()) or ())
        if not fams or fams == ["skip"]:
            # 声明表未命中 -> 退化为"逐个解析器试"
            fams = sorted(FAMILY_PARSERS)

    # 解析器只做"能否读出表"的判断，**不判断是否含 EOS 总表**。
    # 声明表给的族序可能全都不含 EOS（如 Al.txt 声明为 sesame_dat，
    # 实际是 LEDCOP 不透明度）；因此解析成功后仍要试组装，
    # 组装失败就换下一个候选族 —— 否则会因为"第一个能解析的族恰好没有
    # EOS 总表"而过早放弃，漏掉真正可用的族。
    asm_errors: List[str] = []
    tbl = None
    for fam in fams:
        fn = FAMILY_PARSERS.get(fam)
        if fn is None:
            continue
        tried.append(fam)
        try:
            got = fn(str(srcp))
        except Exception:                                  # noqa: BLE001
            continue
        if not got:
            continue
        try:
            tbl = parsed_tables_to_cn4(list(got), izgas=izgas, fracsp=fracsp,
                                       atomwt=atomwt, allow_foreign=True)
        except CN4ParseError as exc:
            asm_errors.append(f"{fam}: {exc}")
            continue
        break

    if tbl is None:
        # 声明表给的候选族全试完仍未成功 -> 退化为"逐个解析器试"
        declared = set(fams)
        for fam in sorted(FAMILY_PARSERS):
            if fam in declared:
                continue
            fn = FAMILY_PARSERS[fam]
            tried.append(fam)
            try:
                got = fn(str(srcp))
            except Exception:                              # noqa: BLE001
                continue
            if not got:
                continue
            try:
                tbl = parsed_tables_to_cn4(list(got), izgas=izgas,
                                           fracsp=fracsp, atomwt=atomwt,
                                           allow_foreign=True)
            except CN4ParseError as exc:
                asm_errors.append(f"{fam}: {exc}")
                continue
            break

    if tbl is None:
        detail = ""
        if asm_errors:
            detail = "；组装失败原因: " + " | ".join(asm_errors[:4])
        raise CN4ParseError(
            f"convert_foreign_to_cn4: 无法把 {srcp.name} 转为 cn4"
            f"（尝试过: {tried or '无可用族'}）{detail}")

    return write_cn4(tbl, dst, **opts)


def convert_cn4_to_cn4(src: str | os.PathLike, dst: str | os.PathLike, **opts) -> Path:
    """cn4 → cn4 往返（等价于"规范化重写"）。

    这是**后续把其他 eosop 数据转为 cn4** 的入口模板::

        load_cn4(A) -> CN4Table -> write_cn4(-> B)
        read(A) -> ParsedTable -> parsed_tables_to_cn4 -> write_cn4(-> B)

    两条路径都可用；前者保留 cn4 原生数组，后者便于跨族统一。

    ★ 默认 ``verbatim=True``：源文件是原生 cn4 时，数据区逐字节直通
    （仅头部按表字段复刻），往返 byte-identical —— 含 BADGER 系列
    混用尾数风格 / ``-Infinity`` 字面量等情形。调用方显式传
    ``mantissa_style=`` 或 ``write_opacities=False`` 时自动退回逐值重排。
    """
    tbl = parse_cn4(src, atomwt=opts.pop("atomwt", None))
    opts.setdefault("verbatim", True)
    return write_cn4(tbl, dst, **opts)
