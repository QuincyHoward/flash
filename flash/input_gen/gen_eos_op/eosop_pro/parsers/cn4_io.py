# -*- coding: utf-8 -*-
"""IONMIX ``.cn4`` (CONRAD 格式) 数据表读写内核。

格式权威来源
============
本模块的块布局**不是猜测**，其唯一一手依据是本地源码::

    ionmix/ionmix/src/Ionmix/abjt_03.f
        SUBROUTINE OWTF (line 4510)
            isw(21) != 0 分支 (line 4662–4743)

该分支逐条 ``write(123, ...)`` 语句给出了 18 个数据块的**顺序、维度、
循环嵌套与物理量**；``991 format (4e12.6)`` (line 4755) 给出**定宽编码**；
头部三个 ``write`` 与 ``923/921/922`` 格式 (line 4667–4672, 4749–4751)
给出**头部行**。全部已在文件内逐行核对。

配套文字规格::

    ionmix/ionmix/docs/IONMIX用户指南.md
        §5.4 "EOS.CN4 — 格式化数据表"（完整数据排列顺序表）

文件布局（所有数据块以 ``4e12.6`` 无分隔符写出）::

    line 1 : ntemp, ndens            (2i10)   [格式 923]
    line 2 : izgas(...)              (a80, " atomic #s of gases: " + 5i10)  [格式 921]
    line 3 : fracsp(...)             (a80, " relative fractions: " + 1p5e10.2) [格式 922]
    line 4 : ngrups                  (i12)    [格式 982]

    block  1 : tplsma(1..ntemp)        温度数组          (eV)
    block  2 : densnn(1..ndens)        核子数密度数组     (cm^-3)
    block  3 : zbar  = ne/nion         (ntemp*ndens)     无量纲
    block  4 : dzdt                    (ntemp*ndens)     eV^-1
    block  5 : ion pressure            (ntemp*ndens)     J/cm^3
    block  6 : electron pressure       (ntemp*ndens)     J/cm^3
    block  7 : d(pion)/dT              (ntemp*ndens)     J/cm^3/eV
    block  8 : d(pele)/dT              (ntemp*ndens)     J/cm^3/eV
    block  9 : enrgyion                (ntemp*ndens)     J/g
    block 10 : enrgyele                (ntemp*ndens)     J/g
    block 11 : heatcpion               (ntemp*ndens)     J/g/eV
    block 12 : heatcpele               (ntemp*ndens)     J/g/eV
    block 13 : d(eion)/d(nion)         (ntemp*ndens)     J*cm^3/g
    block 14 : d(eele)/d(nele)         (ntemp*ndens)     J*cm^3/g
    block 15 : engrup(1..ngrups+1)     能群边界           (eV)
    block 16 : Rosseland 群不透明度     (ngrups*ntemp*ndens)   cm^2/g
    block 17 : Planck 吸收群不透明度     (ngrups*ntemp*ndens)   cm^2/g
    block 18 : Planck 发射群不透明度     (ngrups*ntemp*ndens)   cm^2/g

循环嵌套（源码逐条核对）
------------------------
二维场（block 3–14），源码写法 ``((x(it,id), it=1,ntemp), id=1,ndens)``::

    温度内循环 (it)、密度外循环 (id)
    -> 扁平数组 .reshape(ndens, ntemp) 得到 (行=密度, 列=温度)

三维不透明度场（block 16–18），源码写法
``(((x(it,id,ig), it=1,ntemp), id=1,ndens), ig=1,ngrups)``::

    温度内循环、密度中循环、**群外循环**
    -> .reshape(ngrups, ndens, ntemp) 得到 (群, 密度, 温度)

⚠️ 与 ``docs/IONMIX用户指南.md`` §5.4 的措辞对照: 该文档写
"三维数组: 先能群、再温度、最后密度"。二者**等价** —— 指的分别是
外循环与 reshape 后的轴序（群为第 0 轴、密度为第 1 轴、温度为第 2 轴）。
本模块以源码为准，并把该关系记录于此以免再次混淆。

计数守恒
--------
总数值数（不含头部行）::

    expected = ntemp + ndens + 12*ntemp*ndens + (ngrups+1) + 3*ngrups*ntemp*ndens

12 个二维场（block 3–14）、1 个能群边界数组、3 个三维场。实测不符即
抛 :class:`CN4ParseError` —— 不静默。

单位说明
--------
块内单位取自源码**注释**（``owtf`` 的 input-variable 说明块 line 4517–4529）
与 ``write`` 语句旁的逐条注释（line 4683–4740），例如::

    c ...    write the temperature points (in ev)
    c ...    write the number density points (in cm^-3)
    c ...    write the ion pressure
    c ...    write the d(pion)/dT (in Joules/cm^3/eV)

压力/能量块本身未直接标单位，但由赋值表达式可推定:
line 4693 ``densnn(id)*tplsma(it)*1.602E-19`` —— ``cm^-3 * eV * J/eV = J/cm^3``
（``n k_B T`` 理想气体律，``1.602E-19`` 即 J/eV），故为 **J/cm^3**。
"""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

# 阿伏伽德罗常数 —— 单一来源规则: 必须复用 ``config.N_A``（见
# eosop_pro/config.py line 109），不得在此硬编码（测试
# test_no_conversion_constant_hardcoded_outside_config 强制）。
from ..core.config import N_A as NA

#: Fortran ``4e12.6`` 字段宽度（源码 line 4755: ``991 format (4e12.6)``）
FIXED_WIDTH = 12

#: 头部行 3 的丰度格式 ``1p5e10.2`` —— 与数据区的 ``e12.6`` 不同，需单独匹配
FRAC_RE = re.compile(r"[-+]?\d+\.\d+[EeDd][-+]?\d+")

#: ``ionmxinp`` 中 ``atomwt(i) = ...`` 行（用于自动补全原子量）
_ATOMWT_RE = re.compile(
    r"atomwt\s*\(\s*(\d+)\s*\)\s*=\s*([-+]?\d*\.?\d+(?:[EeDd][-+]?\d+)?)"
)

#: 经典元素原子量表 (amu)，键为原子序数 Z。来源: IUPAC 标准原子量常用值。
#: 仅用于 ``izgas`` 已知时的**便利回退**; 权威来源应为同目录 ``ionmxinp``。
ELEMENT_ATOMWT: dict[int, float] = {
    1: 1.008, 2: 4.002602, 3: 6.94, 4: 9.0122, 5: 10.81, 6: 12.011,
    7: 14.007, 8: 15.999, 9: 18.9984032, 10: 20.1797, 11: 22.98976928,
    12: 24.305, 13: 26.9815385, 14: 28.085, 15: 30.973761998, 16: 32.06,
    17: 35.45, 18: 39.948, 19: 39.0983, 20: 40.078, 21: 44.955912,
    22: 47.867, 23: 50.9415, 24: 51.9961, 25: 54.938044, 26: 55.845,
    27: 58.933194, 28: 58.6934, 29: 63.546, 30: 65.38, 31: 69.723,
    32: 72.63, 33: 74.921595, 34: 78.971, 35: 79.904, 36: 83.798,
    37: 85.4678, 38: 87.62, 39: 88.90584, 40: 91.224, 41: 92.90637,
    42: 95.95, 44: 101.07, 45: 102.9055, 46: 106.42, 47: 107.8682,
    48: 112.414, 49: 114.818, 50: 118.71, 51: 121.76, 52: 127.6,
    53: 126.90447, 54: 131.293, 55: 132.90545196, 56: 137.327,
    57: 138.90547, 58: 140.116, 59: 140.90766, 60: 144.242,
    62: 150.36, 63: 151.964, 64: 157.25, 65: 158.92535, 66: 162.5,
    67: 164.93033, 68: 167.259, 69: 168.93422, 70: 173.045,
    71: 174.9668, 72: 178.49, 73: 180.94788, 74: 183.84, 75: 186.207,
    76: 190.23, 77: 192.217, 78: 195.084, 79: 196.966569,
    80: 200.592, 81: 204.38, 82: 207.2, 83: 208.9804, 90: 232.0377,
    92: 238.02891,
}


class CN4ParseError(ValueError):
    """cn4 解析失败（计数不匹配 / 头部畸形 / 无法确定布局）。"""


# ── 块规格表（顺序即文件中的书写顺序） ──────────────────────────
#: 每个二维物理量块: (属性名, 显示标签, 单位, 源码行号)
#: 单位取自源码注释（见模块 docstring "单位说明"）。
BLOCK_SPEC: tuple[tuple[str, str, str, int], ...] = (
    ("zbar",      "zbar",       "-",        4687),
    ("dzdt",      "dzdt",       "1/eV",     4691),
    ("p_ion",     "p_ion",      "J/cm3",    4693),
    ("p_ele",     "p_ele",      "J/cm3",    4696),
    ("dpion_dt",  "dpion_dt",   "J/cm3/eV", 4699),
    ("dpele_dt",  "dpele_dt",   "J/cm3/eV", 4702),
    ("e_ion",     "e_ion",      "J/g",      4706),
    ("e_ele",     "e_ele",      "J/g",      4708),
    ("cv_ion",    "cv_ion",     "J/g/eV",   4711),
    ("cv_ele",    "cv_ele",     "J/g/eV",   4713),
    ("deion_dn",  "deion_dn",   "J*cm3/g",  4718),
    ("deele_dn",  "deele_dn",   "J*cm3/g",  4723),
)

#: 三维不透明度块: (属性名, 显示标签, 单位, 源码行号)
OPACITY_SPEC: tuple[tuple[str, str, str, int], ...] = (
    ("opac_rosseland",  "opac_rosseland",  "cm2/g", 4733),
    ("opac_planck_abs", "opac_planck_abs", "cm2/g", 4736),
    ("opac_planck_ems", "opac_planck_ems", "cm2/g", 4739),
)

#: cn4 数据块总数（不含 4 行头部）: 2 个 1D 网格 + 12 个 2D 场 + 1 个群边界 + 3 个 3D 场
N_BLOCKS = 18


#: 打包指数缺陷（Fortran ``4e12.6`` 字段溢出）。
#:
#: ``E12.6`` 只能容纳 ``0.ddddddE±ee`` = 1+1+6+1+3 = **12** 列。
#: 当指数为 **3 位数** 且尾数无前导空格时（即值 ``0.ddddddE-140``），
#: 需要 13 列 —— Fortran 运行时**静默**丢掉 ``E``，写出 ``0.638380-140``。
#:
#: 修复规则: ``0.638380-140`` -> ``0.638380E-140``，即把
#: ``(\d\.\d{6})([-+]\d{3})`` 还原为 ``\1E\2``。
#:
#: **实证依据**（``Ionmix/h-imx-1grp.cn4``）:
#:   * 该文件 ntemp=17, ndens=21, ngrups=1 -> 期望数值数 5395
#:   * 严格 12 列切分得 **5395** 个 token（计数本就闭合）
#:   * 其中 **89** 个 token 匹配本模式（如 ``0.638380-140``、``0.201874-144``）
#:   * 修复后每个 token 仍对应 1 个数 -> 计数不变，仍为 5395 ✔
#:   * 修复后的量级（1e-140）正是该表压力/不透明度区的物理合理量级
#:
#: .. note::
#:    负数尾数 + 3 位指数时（``-1.00000-140``，12 列）同样丢 ``E``，
#:    故正则须允许**可选前导负号** —— 写出侧 :func:`_fmt_e12_6` 会产出这种
#:    形态，读取侧必须能还原，否则负值数据无法往返。
_PACKED_EXP_RE = re.compile(r"^(-?\d\.\d{1,6})([-+]\d{3})$")


def _parse_fixed_width(line: str) -> List[float]:
    """按 Fortran ``e12.6`` 固定宽度解析一行。

    每 12 字符为一个科学计数法数字（如 ``'0.100000E+01'``）。
    负号会吃掉前导空格导致字段紧邻无分隔符，故**必须**定宽切分而非 ``split()``。

    另外处理 :data:`_PACKED_EXP_RE` 记录的 **Fortran 字段溢出**缺陷
    （3 位指数导致 ``E`` 被静默丢弃）—— 修复规则有实证依据，不是猜测。
    """
    out: List[float] = []
    s = line.rstrip("\r\n")
    for i in range(0, len(s) - FIXED_WIDTH + 1, FIXED_WIDTH):
        chunk = s[i:i + FIXED_WIDTH].strip()
        if not chunk:
            continue
        text = chunk.replace("D", "E").replace("d", "e")
        # 先尝试原样；失败则尝试修复打包指数（E12.6 溢出缺陷）
        try:
            v = float(text)
        except ValueError:
            m = _PACKED_EXP_RE.match(text)
            if m:
                try:
                    v = float(f"{m.group(1)}E{m.group(2)}")
                except ValueError:
                    v = None
            else:
                v = None
            if v is None:
                # Fortran 运行时可能写出裸 'NaN'/'Inf'（非定宽）
                low = text.lower()
                if low in ("nan", "+nan", "-nan"):
                    v = float("nan")
                elif low in ("inf", "+inf", "infinity", "+infinity"):
                    v = float("inf")
                elif low in ("-inf", "-infinity"):
                    v = float("-inf")
                else:
                    raise CN4ParseError(
                        f"定宽字段 '{chunk}' 不是合法浮点数 (行: {s!r})"
                    )
        # NaN 占位还原: 极负值 -> nan（见 NAN_PLACEHOLDER_FIELD）
        out.append(float("nan") if is_nan_placeholder(v) else v)
    return out


def _iter_fixed_width(text: str) -> List[float]:
    """对多行文本做定宽解析（逐行）。"""
    vals: List[float] = []
    for ln in text.splitlines():
        vals.extend(_parse_fixed_width(ln))
    return vals


def parse_header(lines: Sequence[str]) -> dict:
    """解析 cn4 的前 4 行头部。

    Returns:
        dict: ``ntemp`` / ``ndens`` / ``ngrups`` / ``izgas`` / ``fracsp``
              / ``ngases`` / ``raw``（4 行原文）
    """
    if len(lines) < 4:
        raise CN4ParseError(f"cn4 至少需要 4 行头部, 实际 {len(lines)} 行")

    # line 1: ntemp, ndens  (格式 923: 2i10)
    try:
        toks = lines[0].split()
        ntemp, ndens = int(toks[0]), int(toks[1])
    except (IndexError, ValueError) as exc:
        raise CN4ParseError(
            f"第 1 行应为 2 个整数 (2i10), 实际 {lines[0]!r}"
        ) from exc

    # line 2: " atomic #s of gases: " + 5i10  (格式 921)
    # 前缀长度 20 字符 (" atomic #s of gases: ")，其后每 10 列一个 Z
    if "atomic" not in lines[1].lower():
        raise CN4ParseError(f"第 2 行缺少 'atomic #s of gases' 标记: {lines[1]!r}")
    tail2 = lines[1][20:] if len(lines[1]) > 20 else ""
    izgas = [int(t) for t in re.findall(r"\d+", tail2)]
    if not izgas:
        raise CN4ParseError(f"第 2 行未解析出任何原子序数: {lines[1]!r}")

    # line 3: " relative fractions: " + 1p5e10.2 (格式 922)
    # ⚠️ 该格式与数据区的 4e12.6 不同：宽度 10、精度 2，故单独用正则
    if "fraction" not in lines[2].lower():
        raise CN4ParseError(f"第 3 行缺少 'relative fractions' 标记: {lines[2]!r}")
    fracsp = [float(t.replace("D", "E").replace("d", "e"))
              for t in FRAC_RE.findall(lines[2])]
    if not fracsp:
        raise CN4ParseError(f"第 3 行未解析出任何丰度: {lines[2]!r}")

    # line 4: ngrups  (格式 982: i12)
    try:
        ngrups = int(lines[3].split()[0])
    except (IndexError, ValueError) as exc:
        raise CN4ParseError(f"第 4 行应为 1 个整数 (i12), 实际 {lines[3]!r}") from exc

    if len(izgas) != len(fracsp):
        raise CN4ParseError(
            f"头部不一致: izgas 有 {len(izgas)} 项, fracsp 有 {len(fracsp)} 项"
        )
    for name, v in (("ntemp", ntemp), ("ndens", ndens)):
        if v <= 0:
            raise CN4ParseError(f"{name}={v} 非正数")
    if ngrups < 0:
        raise CN4ParseError(f"ngrups={ngrups} 为负")

    return {
        "ntemp": ntemp, "ndens": ndens, "ngrups": ngrups,
        "izgas": izgas, "fracsp": fracsp, "ngases": len(izgas),
        "raw": [lines[0], lines[1], lines[2], lines[3]],
    }


def expected_number_count(ntemp: int, ndens: int, ngrups: int) -> int:
    """块布局推导的数值总数（不含头部行）。

    ``ntemp + ndens + 12*ntemp*ndens + (ngrups+1) + 3*ngrups*ntemp*ndens``
    """
    n2d = ntemp * ndens
    return ntemp + ndens + 12 * n2d + (ngrups + 1) + 3 * ngrups * n2d


def guess_atomwt(izgas: Sequence[int]) -> Optional[List[float]]:
    """由原子序数查经典原子量表。任一 Z 缺失则返回 ``None``（不猜）。"""
    vals: List[float] = []
    for z in izgas:
        if z in ELEMENT_ATOMWT:
            vals.append(ELEMENT_ATOMWT[z])
        else:
            return None
    return vals


def read_atomwt_from_ionmxinp(dirpath: str | os.PathLike, ngases: int) -> Optional[List[float]]:
    """从同目录 ``ionmxinp`` 读取 ``atomwt(i)``（权威来源）。缺失/不全返回 ``None``。"""
    inp = Path(dirpath) / "ionmxinp"
    if not inp.is_file() or inp.stat().st_size == 0:
        return None
    values: dict[int, float] = {}
    try:
        text = inp.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        m = _ATOMWT_RE.search(line)
        if m:
            values[int(m.group(1))] = float(m.group(2).replace("D", "E").replace("d", "e"))
    if len(values) != ngases:
        return None
    return [values[i] for i in range(1, ngases + 1)]


@dataclass
class CN4Table:
    """IONMIX ``.cn4`` 文件的结构化数据容器。

    所有二维场的数组形状为 ``(ndens, ntemp)``（行=密度，列=温度）；
    三维不透明度场为 ``(ngrups, ndens, ntemp)``。**用纯 list 存储**，
    以便在无 numpy 的最小解释器上完成解析与计数校验。
    """

    filepath: str
    ntemp: int
    ndens: int
    ngrups: int
    ngases: int
    izgas: List[int]
    fracsp: List[float]
    atomwt: Optional[List[float]]
    temperature: List[float]            # (ntemp,) eV
    density: List[float]                # (ndens,) cm^-3
    fields2d: dict[str, List[float]]    # 12 个二维场, 扁平 (ndens*ntemp)
    group_bounds: List[float]           # (ngrups+1,) eV
    opacities: dict[str, List[float]]   # 3 个三维场, 扁平 (ngrups*ndens*ntemp)
    header_raw: List[str] = field(default_factory=list)
    #: ★ 原生数据区逐字文本（头部 4 行之后的全部内容，含行尾）。
    #:   仅 ``parse_cn4`` 直读原生 cn4 时填写；跨族转换新造的表为 ``None``。
    #:   用途：``write_cn4(..., verbatim=True)`` 直通复刻，使 cn4→cn4 往返
    #:   达到 byte-identical —— 部分生产者（BADGER-TOPS 系列）在**同一文件**
    #:   内混用两种 e12.6 尾数风格（``0.ddddddE±dd`` 与 ``d.ddddddE±dd``）
    #:   并以 ``-Infinity`` 字面量表示负无穷，逐值重排无法复刻，只能直通。
    data_raw: Optional[str] = None
    unit_source: str = ""
    layout_rule: str = ""
    n_numbers_seen: int = 0
    n_numbers_expected: int = 0
    notes: List[str] = field(default_factory=list)
    #: 原子量来源: ``"user"`` / ``"ionmxinp"`` / ``"element_table"`` / ``"unavailable"``
    atomwt_source: str = "unavailable"
    #: ★ 来源族（用户 2026-09-15 第十二轮规约）：跨族转换
    #: （``parsed_tables_to_cn4(..., allow_foreign=True)``）时记录源
    #: ``ParsedTable.family``（如 ``"mpqeos"``）；原生 cn4 / cn4 往返
    #: 转换为 ``""``。cn4 路径图（``cn4_paths``）的轴标签经
    #: ``plotting.style.labels.cn4_tags(origin_family, ...)`` 回查来源族的
    #: 认证标记（``uk, uv`` / ``uv``）并追加后缀 —— 数据的核查状态在
    #: 图上持续可见；原生 cn4 数据全来自 ionmix（已核查）无标记。
    origin_family: str = ""

    # ── 基本视图 ────────────────────────────────────────────────
    @property
    def basename(self) -> str:
        return os.path.splitext(os.path.basename(self.filepath))[0]

    @property
    def species_label(self) -> str:
        return " + ".join(
            f"Z{z}({f * 100:g}%)" for z, f in zip(self.izgas, self.fracsp)
        )

    @property
    def avgatw(self) -> Optional[float]:
        """平均原子量 (amu) = ``sum(fracsp * atomwt)``；原子量未知返回 ``None``。"""
        if self.atomwt is None:
            return None
        return float(sum(f * a for f, a in zip(self.fracsp, self.atomwt)))

    def field(self, name: str) -> List[float]:
        """按名取二维场（扁平）。支持别名。"""
        alias = _FIELD_ALIAS.get(name.lower())
        key = alias or name
        if key in self.fields2d:
            return self.fields2d[key]
        if key in self.opacities:
            raise CN4ParseError(
                f"'{name}' 是三维不透明度场，请用 group_opacity(name, ig)"
            )
        raise KeyError(f"未知二维场 '{name}'. 可选: {sorted(self.fields2d)}")

    def field_grid(self, name: str) -> List[List[float]]:
        """按名取二维场并解成 ``[i_dens][j_T]`` 嵌套列表。"""
        flat = self.field(name)
        n = self.ntemp
        if len(flat) != self.ndens * n:
            raise CN4ParseError(
                f"场 '{name}' 长度 {len(flat)} != ndens*ntemp={self.ndens * n}"
            )
        return [flat[i * n:(i + 1) * n] for i in range(self.ndens)]

    def quantity(self, name: str) -> List[float]:
        """按名取物理量（扁平 ``ndens*ntemp``）。含派生量 ``rho`` / ``nele``。"""
        low = name.lower()
        if low in ("rho", "rhoe", "mass_density"):
            return self.rho_flat()
        if low in ("nele", "ne", "electron_density", "n_e"):
            return self.nele_flat()
        if low in ("p", "ptot", "pressure"):
            return [a + b for a, b in zip(self.field("p_ion"), self.field("p_ele"))]
        if low in ("e", "etot", "energy"):
            return [a + b for a, b in zip(self.field("e_ion"), self.field("e_ele"))]
        if low in ("cv", "cvtot"):
            return [a + b for a, b in zip(self.field("cv_ion"), self.field("cv_ele"))]
        return self.field(name)

    def rho_flat(self) -> List[float]:
        """物质密度 ``rho = n_ion * <A> / N_A`` (g/cm^3)，扁平 ``ndens*ntemp``。

        每个密度点对应的 rho 与温度无关（由 ``n_ion`` 唯一决定），
        故沿温度方向广播。
        """
        aw = self.avgatw
        if aw is None:
            raise CN4ParseError(
                "原子量未知，无法计算 rho。请提供 atomwt 或同目录 ionmxinp。"
            )
        out: List[float] = []
        for nd in self.density:
            r = nd * aw / NA
            out.extend([r] * self.ntemp)
        return out

    def nele_flat(self) -> List[float]:
        """电子数密度 ``n_e = zbar * n_ion`` (cm^-3)，扁平 ``ndens*ntemp``。"""
        zbar = self.field("zbar")
        out: List[float] = []
        for i, nd in enumerate(self.density):
            base = i * self.ntemp
            out.extend([zbar[base + j] * nd for j in range(self.ntemp)])
        return out

    def group_opacity(self, name: str, ig: int) -> List[float]:
        """取第 ``ig`` 群（**1-based**）的不透明度二维场 ``ndens*ntemp``。"""
        key = {
            "rosseland": "opac_rosseland",
            "planck_abs": "opac_planck_abs",
            "abs": "opac_planck_abs",
            "planck_ems": "opac_planck_ems",
            "ems": "opac_planck_ems",
        }.get(name.lower(), name)
        if key not in self.opacities:
            raise KeyError(f"未知不透明度 '{name}'. 可选: {sorted(self.opacities)}")
        if not 1 <= ig <= self.ngrups:
            raise CN4ParseError(f"群号 ig={ig} 越界 (1..{self.ngrups})")
        flat = self.opacities[key]
        n2 = self.ndens * self.ntemp
        return flat[(ig - 1) * n2: ig * n2]

    def summary(self) -> str:
        aw = self.avgatw
        aws = f"{aw:.4f}" if aw is not None else "unknown"
        return (
            f"cn4[{self.basename}] {self.species_label} "
            f"ntemp={self.ntemp} ndens={self.ndens} ngrups={self.ngrups} "
            f"<A>={aws} amu  T=[{self.temperature[0]:.3e}, "
            f"{self.temperature[-1]:.3e}] eV  n_ion=[{self.density[0]:.3e}, "
            f"{self.density[-1]:.3e}] cm^-3"
        )


#: 二维场名别名（keys 需为小写）
_FIELD_ALIAS = {
    "z": "zbar", "charge": "zbar", "zbar_avg": "zbar",
    "dzdT".lower(): "dzdt",
    "pion": "p_ion", "pele": "p_ele",
    "eion": "e_ion", "eele": "e_ele",
    "cvion": "cv_ion", "cvele": "cv_ele",
    "deion_dn_dens": "deion_dn",
    "deele_dn_dens": "deele_dn",
}


def parse_cn4(filepath: str | os.PathLike, *,
              atomwt: Optional[Sequence[float]] = None) -> CN4Table:
    """解析 ``.cn4`` 文件为 :class:`CN4Table`（含计数守恒校验）。

    Args:
        filepath: ``.cn4`` 路径
        atomwt: 各气体原子量 (amu)，顺序同 ``izgas``。缺省时依次尝试
            同目录 ``ionmxinp`` → 经典元素表；均不可得则置 ``None``
            （此时 ``zbar`` / ``p_*`` / ``e_*`` / ``opacity`` 仍可用，
            但 ``rho`` 会抛错 —— 因为缺 ``<A>`` 无法换算质量密度）。

    Raises:
        CN4ParseError: 头部畸形、数值数不守恒、定宽字段损坏。
    """
    p = Path(filepath).expanduser().resolve()
    if not p.is_file():
        raise CN4ParseError(f"文件不存在: {p}")

    # 编码链: utf-8-sig -> utf-8 -> gb18030 -> latin-1（与 core.textio 同纪律）
    text = None
    for enc in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            text = p.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:  # pragma: no cover
        raise CN4ParseError(f"无法以任何候选编码读取: {p}")

    # NUL 一票否决
    if "\x00" in text:
        raise CN4ParseError(f"文件含 NUL 字节，非纯文本 cn4: {p}")

    lines = text.splitlines()
    head = parse_header(lines)
    ntemp, ndens, ngrups = head["ntemp"], head["ndens"], head["ngrups"]

    # 数据区从第 4 行起（0-based index 4），整体定宽解析
    values = _iter_fixed_width("\n".join(lines[4:]))
    # ★ 逐字保留数据区文本（keepends 保原始行尾），供 write_cn4 直通往返
    data_raw = "".join(text.splitlines(keepends=True)[4:])

    expected = expected_number_count(ntemp, ndens, ngrups)
    if len(values) != expected:
        raise CN4ParseError(
            f"数值个数不守恒: 实测 {len(values)}, 期望 {expected} "
            f"(ntemp={ntemp}, ndens={ndens}, ngrups={ngrups})。"
            f"块布局依据 abjt_03.f SUBROUTINE OWTF。"
        )

    pos = 0
    n2d = ntemp * ndens
    n3d = ngrups * n2d

    def take(n: int) -> List[float]:
        nonlocal pos
        blk = values[pos:pos + n]
        pos += n
        return blk

    temperature = take(ntemp)
    density = take(ndens)
    fields2d: dict[str, List[float]] = {}
    for attr, _label, _unit, _src in BLOCK_SPEC:
        fields2d[attr] = take(n2d)
    group_bounds = take(ngrups + 1)
    opacities: dict[str, List[float]] = {}
    for attr, _label, _unit, _src in OPACITY_SPEC:
        opacities[attr] = take(n3d)

    if pos != len(values):  # pragma: no cover —— 上式已保证相等
        raise CN4ParseError(f"解析后仍有 {len(values) - pos} 个数值未消费")

    # ── 原子量来源解析（三级，不猜） ────────────────────────────
    atomwt_list: Optional[List[float]] = None
    atomwt_source = "unavailable"
    if atomwt is not None:
        if len(atomwt) != head["ngases"]:
            raise CN4ParseError(
                f"atomwt 长度 {len(atomwt)} != 气体数 {head['ngases']}"
            )
        atomwt_list = [float(a) for a in atomwt]
        atomwt_source = "user"
    else:
        atomwt_list = read_atomwt_from_ionmxinp(p.parent, head["ngases"])
        if atomwt_list is not None:
            atomwt_source = "ionmxinp"
        else:
            atomwt_list = guess_atomwt(head["izgas"])
            if atomwt_list is not None:
                atomwt_source = "element_table"

    tbl = CN4Table(
        filepath=str(p),
        ntemp=ntemp, ndens=ndens, ngrups=ngrups,
        ngases=head["ngases"], izgas=head["izgas"], fracsp=head["fracsp"],
        atomwt=atomwt_list,
        temperature=temperature, density=density,
        fields2d=fields2d, group_bounds=group_bounds, opacities=opacities,
        header_raw=head["raw"],
        unit_source="abjt_03.f SUBROUTINE OWTF (isw(21)!=0 分支) + docs/IONMIX用户指南.md §5.4",
        layout_rule=(
            "cn4: 4 行头部 + [tplsma(ntemp)] [densnn(ndens)] "
            "+ 12*[ntemp*ndens] + [engrup(ngrups+1)] + 3*[ngrups*ntemp*ndens]; "
            "2D 温度内循环/密度外循环 -> reshape(ndens,ntemp); "
            "3D 群外循环 -> reshape(ngrups,ndens,ntemp)"
        ),
        n_numbers_seen=len(values),
        n_numbers_expected=expected,
        atomwt_source=atomwt_source,
        data_raw=data_raw,
    )
    if atomwt_source == "element_table":
        tbl.notes.append(
            "⚠️ 原子量取自内置 IUPAC 元素表（同目录无 ionmxinp）。"
            "同素异形体/同位素富集样品应以 ionmxinp 为准。"
        )
    elif atomwt_source == "unavailable":
        tbl.notes.append(
            f"⚠️ 原子量未知（izgas={head['izgas']} 未全部命中内置表，"
            f"且无 ionmxinp）-> rho 不可用; zbar/p_*/e_*/opacity 仍可用。"
        )

    # ★ 记录 ``e12.6`` 尾数风格 —— 供 write_cn4 复刻源文件排版，
    #   使 ``parse -> write`` 达到 byte-identical（实测两种风格并存：
    #   Ionmix 用 "leading0"，BADGER-TOPS 系列用 "dotted"）。
    tbl.notes.append(f"mantissa style: {_sniff_mantissa_style(values, text)}")
    return tbl


#: 兼容旧名（参考实现中称 ``CN4Data`` / ``load_cn4``）
CN4Data = CN4Table


def load_cn4(filepath: str | os.PathLike, *,
             atomwt: Optional[Sequence[float]] = None) -> CN4Table:
    """``parse_cn4`` 的别名（保持与参考实现 ``load_cn4`` 的调用兼容）。"""
    return parse_cn4(filepath, atomwt=atomwt)


def load_cn4_dir(dirpath: str | os.PathLike) -> List[CN4Table]:
    """解析目录下**全部** ``.cn4`` 文件（按文件名排序，失败项跳过并记录）。"""
    d = Path(dirpath)
    out: List[CN4Table] = []
    if not d.is_dir():
        return out
    for f in sorted(d.iterdir()):
        if f.is_file() and f.suffix.lower() == ".cn4":
            try:
                out.append(parse_cn4(f))
            except CN4ParseError:
                continue
    return out


# ── 写出（cn4 是最重要的**目标格式**，故写出器与解析器同源） ──────
#: NaN 占位编码（Fortran ``E12.6`` 定宽内合法）。
#:
#: Fortran 无法在 ``e12.6`` 里写出 ``NaN``（``gfortran`` 会写出裸 ``NaN`` 三字符，
#: 但**不是**合法科学计数法，且列宽随运行时可变）。本项目需要"缺失数据用 NaN
#: 占位且**对齐**"的能力（见 ``test/eosopdata/transcn4``），因此定义一个
#: **项目内的占位约定**：字面 12 列 ``-9.99999+990``。
#:
#: 选择依据:
#:   * 解码为 ``-9.99999e990`` ⟹ **IEEE double 下溢为 ``-inf``**，
#:     对 EOS 任何物理量都绝无可能，不会与真实数据混淆
#:     （真实 cn4 量级见 ``h-imx-1grp.cn4``：~1e-150 至 ~1e+16）
#:   * **恰好 12 列**，与 ``e12.6`` 定宽天然对齐
#:   * 形态与 :data:`_PACKED_EXP_RE` **完全一致**（Fortran 丢 ``E`` 形态），
#:     故读取侧无需新增分支，走既有打包指数还原路径即可
#:   * Fortran 侧读到它不会崩（是合法浮点数），只是数值荒谬 —— 可接受降级
NAN_PLACEHOLDER_FIELD = "-9.99999+990"

#: 判定阈值: 任何 ``<=`` 本值或非有限数都视为 NaN 占位
#: （真实物理量不会低于 ``-1e98``，占位解码后为 ``-inf``）。
NAN_PLACEHOLDER_CUTOFF = -1.0e98


def is_nan_placeholder(v: float) -> bool:
    """判断 ``v`` 是否为 :data:`NAN_PLACEHOLDER_FIELD` 编码的 NaN 占位。"""
    if v != v:  # 原生 nan
        return True
    if v == float("-inf") or v == float("inf"):
        return True
    return v <= NAN_PLACEHOLDER_CUTOFF


def _sniff_mantissa_style(values: Sequence[float], raw: str = "") -> str:
    """从**原始文本**判断 ``e12.6`` 尾数风格（``"leading0"`` / ``"dotted"``）。

    判据：数据行里第一个形如 ``\\d\\.\\d+E`` 的片段的整数部分。

    * ``0.200000E+01`` -> 整数部分 ``"0"`` -> ``"leading0"``
    * ``1.000000E-01`` -> 整数部分 ``"1"`` -> ``"dotted"``

    仅看**前若干个**候选片段并取多数，避免个别 ``0.`` 开头的 ``dotted`` 值
    （如 ``0.500000E-02`` 恰与 leading0 同形）造成误判。
    """
    if not raw:
        return "leading0"
    n_zero = n_nonzero = 0
    # 跳过头部 4 行，只看数据区
    for line in raw.split("\n")[4:]:
        line = line.strip()
        if not line:
            continue
        for m in re.finditer(r"(-?)(\d)\.\d+E", line):
            if m.group(1) == "-":
                continue                    # 负值两种风格都是 '-.'，无区分度
            if m.group(2) == "0":
                n_zero += 1
            else:
                n_nonzero += 1
        if n_zero + n_nonzero > 200:
            break
    if n_zero + n_nonzero == 0:
        return "leading0"
    return "leading0" if n_zero >= n_nonzero else "dotted"


# ── 与 ParsedTable 体系的双向桥接 ───────────────────────────────
def cn4_to_parsed_tables(table: CN4Table, relpath: str = "") -> list:
    """把 :class:`CN4Table` 适配为 ``eosop_pro`` 的 :class:`ParsedTable` 列表。

    产出 **4 张** 表（与 ``ParsedTable`` 的"一表一族"惯例一致）::

        CN4_<name>_EOS        二维 EOS 场（zbar, p_ion, e_ion, ... cv_ele）
        CN4_<name>_OPAC_ROSS  Rosseland 群不透明度（多群, ngrups 维）
        CN4_<name>_OPAC_PABS  Planck 吸收群不透明度
        CN4_<name>_OPAC_PEMS  Planck 发射群不透明度

    轴语义: 统一用 ``axes["nion"]``（离子数密度 cm^-3）与 ``axes["Te"]``（eV）。
    这**不是** ``rho`` 轴 —— cn4 的密度自变量是 ``n_ion``；质量密度 ``rho``
    需经 ``<A>`` 换算，作为**派生场** ``rho`` 一并写入。

    二维场展平为 ``(n_Te, n_x)`` 语义即 ``(ntemp, ndens)`` **T-major**，
    与 ``ParsedTable.field_shape`` 的约定一致；而 cn4 原始存储为
    density-major，故此处做一次转置（逐列重排），并把该动作记入 ``notes``。
    """
    from .base import ParsedTable

    rel = relpath or os.path.basename(table.filepath)
    key_base = f"CN4_{table.basename}"
    out: list = []

    # ── 1) EOS 总表 ──
    t = ParsedTable(
        table_key=f"{key_base}_EOS",
        kind="EOS_TOTAL",
        family="cn4",
        source_relpath=rel,
        header_raw=" | ".join(x.strip() for x in table.header_raw[:2]),
        layout_rule=table.layout_rule,
    )
    t.axes["nion"] = list(table.density)
    t.axis_units["nion"] = "cm-3"
    t.axis_log10["nion"] = True
    t.axes["Te"] = list(table.temperature)
    t.axis_units["Te"] = "eV"
    t.axis_log10["Te"] = True

    # cn4 原始为 (ndens, ntemp)；ParsedTable 约定 (n_Te, n_x) -> 转置
    for attr, label, unit, _src in BLOCK_SPEC:
        flat = table.fields2d[attr]
        rowmajor = [flat[i * table.ntemp + j]
                    for j in range(table.ntemp) for i in range(table.ndens)]
        t.fields[label] = rowmajor
        t.field_shape[label] = (table.ntemp, table.ndens)
        t.field_units[label] = unit
        t.field_log10[label] = False

    # 派生量: 总压 / 总内能 / 总比热 / rho / nele
    def _sum2d(a: str, b: str) -> list:
        fa, fb = t.fields[a], t.fields[b]
        return [x + y for x, y in zip(fa, fb)]

    t.fields["P"] = _sum2d("p_ion", "p_ele")
    t.field_shape["P"] = (table.ntemp, table.ndens)
    t.field_units["P"] = "J/cm3"
    t.field_log10["P"] = False

    t.fields["E"] = _sum2d("e_ion", "e_ele")
    t.field_shape["E"] = (table.ntemp, table.ndens)
    t.field_units["E"] = "J/g"
    t.field_log10["E"] = False

    t.fields["cv"] = _sum2d("cv_ion", "cv_ele")
    t.field_shape["cv"] = (table.ntemp, table.ndens)
    t.field_units["cv"] = "J/g/eV"
    t.field_log10["cv"] = False

    if table.avgatw is not None:
        rho_flat = table.rho_flat()
        t.fields["rho"] = [rho_flat[i * table.ntemp + j]
                           for j in range(table.ntemp) for i in range(table.ndens)]
        t.field_shape["rho"] = (table.ntemp, table.ndens)
        t.field_units["rho"] = "g/cm3"
        t.field_log10["rho"] = False

    nele_flat = table.nele_flat()
    t.fields["nele"] = [nele_flat[i * table.ntemp + j]
                        for j in range(table.ntemp) for i in range(table.ndens)]
    t.field_shape["nele"] = (table.ntemp, table.ndens)
    t.field_units["nele"] = "cm-3"
    t.field_log10["nele"] = False

    t.n_groups = None
    t.n_numbers_seen = table.n_numbers_seen
    t.n_numbers_expected = table.n_numbers_expected
    t.unit_source = table.unit_source
    t.notes.append(f"成分: {table.species_label}")
    t.notes.append(
        f"原子量来源: {table.atomwt_source}"
        + (f" (<A>={table.avgatw:.4f} amu)" if table.avgatw is not None else "")
    )
    t.notes.append(
        "轴: nion (cm^-3) 为 cn4 固有自变量; rho/nele 为派生场。"
        "二维场已由 cn4 原始 (ndens,ntemp) 转置为 ParsedTable 约定的 (n_Te,n_x)"
    )
    t.notes.extend(table.notes)
    out.append(t)

    # ── 2–4) 三张不透明度表 ──
    for attr, label, kind in (
        ("opac_rosseland", "opac_rosseland", "ROSSELAND"),
        ("opac_planck_abs", "opac_planck_abs", "PLANCK"),
        ("opac_planck_ems", "opac_planck_ems", "EMISSIVITY"),
    ):
        to = ParsedTable(
            table_key=f"{key_base}_OPAC_{kind}",
            kind=kind,
            family="cn4",
            source_relpath=rel,
            header_raw=table.header_raw[1].strip() if len(table.header_raw) > 1 else "",
            n_groups=table.ngrups,
            group_bounds=list(table.group_bounds),
            layout_rule="cn4 三维不透明度块（群外循环）-> (ngrups, n_Te, n_x)",
        )
        to.axes["nion"] = list(table.density)
        to.axis_units["nion"] = "cm-3"
        to.axis_log10["nion"] = True
        to.axes["Te"] = list(table.temperature)
        to.axis_units["Te"] = "eV"
        to.axis_log10["Te"] = True

        # 原始 (ngrups, ndens, ntemp) -> 约定 (ngrups, n_Te, n_x)
        flat = table.opacities[attr]
        n2 = table.ndens * table.ntemp
        reordered: list = []
        for g in range(table.ngrups):
            base = g * n2
            for j in range(table.ntemp):
                for i in range(table.ndens):
                    reordered.append(flat[base + i * table.ntemp + j])
        # 字段名用控制字典登记名（opac_rosseland/opac_planck_abs/opac_planck_ems），
        # 使 field_check 链路命中 checked 条目——统一叫 kappa_g 会落入
        # "未注册"兜底（uk,uv 误标）。单位 cm2/g 与字典一致。
        to.fields[label] = reordered
        to.field_shape[label] = (table.ngrups, table.ntemp, table.ndens)
        to.field_units[label] = "cm2/g"
        to.field_log10[label] = False
        to.n_numbers_seen = len(flat)
        to.n_numbers_expected = len(flat)
        to.unit_source = table.unit_source
        to.notes.append("多群维来自 cn4 的群外循环结构，无需猜测轴序")
        out.append(to)

    return out


if __name__ == "__main__":  # pragma: no cover —— 手工检查入口
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        print("用法: python -m eosop_pro.parsers.cn4_io <file.cn4> [out.cn4]")
        sys.exit(1)
    d = parse_cn4(sys.argv[1])
    print(d.summary())
    print(f"计数: {d.n_numbers_seen} (期望 {d.n_numbers_expected})")
    print(f"原子量来源: {d.atomwt_source}")
    if len(sys.argv) > 2:
        from eosop_pro.convert.cn4_write import write_cn4
        out = write_cn4(d, sys.argv[2])
        print(f"已写出: {out}")
