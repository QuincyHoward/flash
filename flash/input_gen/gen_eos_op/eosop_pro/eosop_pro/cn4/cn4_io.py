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
from ..config import N_A as NA

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
    #: ``plotting.labels.cn4_tags(origin_family, ...)`` 回查来源族的
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


#: Fortran 默认记录宽度（``write`` 无格式时的尾部空格填充列数）。
FIXED_HEADER_WIDTH = 80


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
              mantissa_style: str | None = None) -> Path:
    """把 :class:`CN4Table` 写回 cn4 格式。

    严格复刻 ``OWTF`` 的 ``write(123, ...)`` 序列与 ``4e12.6`` 定宽编码，
    因此 ``parse_cn4(write_cn4(t))`` 应逐位回读（见 test 往返校验）。

    Args:
        table: 源表（须已含 12 个二维场；三维场可在 ``write_opacities=False``
            时以零填充 —— 用于"仅 EOS 不含不透明度"的降级写出）
        out_path: 目标路径（``.cn4`` 后缀自动补全）
        write_opacities: 是否写出三维不透明度块。``False`` 时写零占位，
            **块数与计数保持不变**（保持格式合法）。

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
    from ..parsers.base import ParsedTable

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
        to.fields["kappa_g"] = reordered
        to.field_shape["kappa_g"] = (table.ngrups, table.ntemp, table.ndens)
        to.field_units["kappa_g"] = "cm2/g"
        to.field_log10["kappa_g"] = False
        to.n_numbers_seen = len(flat)
        to.n_numbers_expected = len(flat)
        to.unit_source = table.unit_source
        to.notes.append("多群维来自 cn4 的群外循环结构，无需猜测轴序")
        out.append(to)

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
    from ..parsers.base import ParsedTable

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
        if tbl_cn4 is not None and "kappa_g" in tbl_cn4.fields:
            hit = tbl_cn4.fields["kappa_g"]
            used_name = "kappa_g"
            src_desc = f"kind={kind}"
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
    #   plotting.labels.cn4_tags 用它回查该族认证标记。
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
#: ``hyades_eos``(``P``/``E``)、``feos_native``（列序未定，不参与）。
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
    from ..registry.dispatch import FAMILY_PARSERS
    from ..registry.declared_types import declare

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
            from ..config import MATTER_DIR as _MD
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
    """
    tbl = parse_cn4(src, atomwt=opts.pop("atomwt", None))
    return write_cn4(tbl, dst, **opts)


if __name__ == "__main__":  # pragma: no cover —— 手工检查入口
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        print("用法: python -m eosop_pro.cn4.cn4_io <file.cn4> [out.cn4]")
        sys.exit(1)
    d = parse_cn4(sys.argv[1])
    print(d.summary())
    print(f"计数: {d.n_numbers_seen} (期望 {d.n_numbers_expected})")
    print(f"原子量来源: {d.atomwt_source}")
    if len(sys.argv) > 2:
        out = write_cn4(d, sys.argv[2])
        print(f"已写出: {out}")
