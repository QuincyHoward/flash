"""F6d —— IONMIX ``.cn4`` / ``.cnr`` 数据表（**完整块解码**）。

★ 重大升级说明（2026-09-14）
----------------------------
本解析器由「简化占位版」升级为**完整块解码版**。旧版只解出组分头 + 候选
单调网格，把其余数值存入 ``raw_values`` 并标注"列语义待定"；新版依据
本地 FORTRAN 源码**逐块解码全部 18 个数据块**，给出每个物理量的名称与单位。

权威格式来源（一手，非猜测）
----------------------------
1. **源码**（最重要）::

       ionmix/ionmix/src/Ionmix/abjt_03.f
           SUBROUTINE OWTF (line 4510)
               isw(21) != 0 分支 (line 4662-4743)  <- 18 个 write(123,...) 语句
               format 991 (4e12.6) (line 4755)     <- 定宽编码
               format 923/921/922/982              <- 4 行头部

2. **文字规格**::

       ionmix/ionmix/docs/IONMIX用户指南.md  §5.4 "EOS.CN4 — 格式化数据表"

3. **参考实现**（已被本模块取代）::

       ionmix/ionmix/eosop_pro/core/cn4_parser.py

⚠️ 旧版 docstring 写"本地 matter++ 内**没有** IONMIX 格式文档"——
该判断**已被推翻**: 上述 ``abjt_03.f`` 与用户指南都在本仓库内，
且已逐行核对。详见 :mod:`eosop_pro.cn4.cn4_io` 的模块 docstring。

文件布局
--------
::

    line 1 : ntemp, ndens            (2i10)
    line 2 : izgas(...)               (a80, " atomic #s of gases: ")
    line 3 : fracsp(...)              (a80, " relative fractions: ")
    line 4 : ngrups                   (i12)

    block  1 : tplsma(ntemp)        温度          eV
    block  2 : densnn(ndens)        核子数密度      cm^-3
    block  3 : zbar = ne/nion       (ntemp*ndens) 无量纲
    block  4 : dzdt                 (ntemp*ndens) 1/eV
    block  5 : ion pressure         (ntemp*ndens) J/cm^3
    block  6 : electron pressure    (ntemp*ndens) J/cm^3
    block  7 : d(pion)/dT           (ntemp*ndens) J/cm^3/eV
    block  8 : d(pele)/dT           (ntemp*ndens) J/cm^3/eV
    block  9 : enrgyion             (ntemp*ndens) J/g
    block 10 : enrgyele             (ntemp*ndens) J/g
    block 11 : heatcpion            (ntemp*ndens) J/g/eV
    block 12 : heatcpele            (ntemp*ndens) J/g/eV
    block 13 : d(eion)/d(nion)      (ntemp*ndens) J*cm^3/g   ⚠️ 源码注 "not sure"
    block 14 : d(eele)/d(nele)      (ntemp*ndens) J*cm^3/g   ⚠️ 源码注 "not sure"
    block 15 : engrup(ngrups+1)     能群边界       eV
    block 16 : Rosseland 群不透明度   (ngrups*ntemp*ndens) cm^2/g
    block 17 : Planck 吸收群不透明度   (ngrups*ntemp*ndens) cm^2/g
    block 18 : Planck 发射群不透明度   (ngrups*ntemp*ndens) cm^2/g

⚠️ **block 13/14 单位诚实标注**: 源码 line 4715/4720 自身注释为 ``(not sure)``，
且写出量经过 ``condd = -6.242e18*avgatw/avgdro`` 的换算，其物理量纲**无法
从源码独立确认**。本解析器把这两个场标记为 ``unit_source="unknown"``，
**不代为断言** —— 见 :data:`eosop_pro.cn4.units.UNCERTAIN_UNITS`。

输出
----
每文件产出 **1 张** ``ParsedTable``（EOS 总表，kind=``cn4_eos``）。不透明度
三块以多群场 ``kappa_rosseland`` / ``kappa_planck_abs`` / ``kappa_planck_ems``
一并挂在同一张表上（形状 ``(ngrups, n_Te, n_x)``），因为 cn4 本就是
**EOS 与不透明度合一**的表——拆开反而丢失 CN4 的原子性。

若需按"一表一族"拆成 4 张（便于跨族转换），请用
:func:`eosop_pro.cn4.cn4_to_parsed_tables`。
"""

from __future__ import annotations

from pathlib import Path

from ..core.errors import ParseError
from .base import ParsedTable

__all__ = ["FAMILY", "parse", "parse_all", "parse_composition", "CN4_SUPPORTED"]

FAMILY = "ionmix"

#: cn4 解析所依赖的模块（延迟导入，避免无 numpy 环境下的 import 失败）
CN4_SUPPORTED = (".cn4", ".cnr")


def parse_composition(head: list[str]) -> dict:
    """从头部抽组分（Z 列表 + 分数）与维度。保留旧 API 以兼容既有调用。

    自动识别 ``.cn4``（``982 i12`` 独占行）与 ``.cnr``（``981 4e12.6,i12``）
    两种头部布局 —— 判据是第 4 行能否被 ``int()`` 解析。
    """
    from ..cn4.cn4_io import parse_header
    from ..cn4.cnr_io import parse_cnr_header

    try:
        h = parse_header(head)
        fmt = "cn4"
    except Exception:  # noqa: BLE001 —— 回退 cnr 变体
        h = parse_cnr_header(head)
        fmt = "cnr"
    return {
        "z": list(h["izgas"]),
        "fractions": list(h["fracsp"]),
        "nr": h["ndens"],
        "nt": h["ntemp"],
        "ngrups": h["ngrups"],
        "format": fmt,
    }


def _build_table(rel: str, doc_lines: list[str]) -> ParsedTable:
    """调用完整 cn4 内核解析，并适配为单张 ParsedTable。"""
    from ..cn4.cn4_io import (
        BLOCK_SPEC,
        OPACITY_SPEC,
        parse_header,
        _iter_fixed_width,
        expected_number_count,
    )

    h = parse_header(doc_lines)
    ntemp, ndens, ngrups = h["ntemp"], h["ndens"], h["ngrups"]

    values = _iter_fixed_width("\n".join(doc_lines[4:]))
    expected = expected_number_count(ntemp, ndens, ngrups)
    if len(values) != expected:
        raise ParseError(
            f"ionmix/cn4: 数值个数不守恒 实测={len(values)} 期望={expected} "
            f"(ntemp={ntemp}, ndens={ndens}, ngrups={ngrups})",
            path=rel,
        )

    pos = 0
    n2d, n3d = ntemp * ndens, ngrups * ntemp * ndens

    def take(n: int) -> list[float]:
        nonlocal pos
        blk = values[pos:pos + n]
        pos += n
        return blk

    temperature = take(ntemp)
    density = take(ndens)
    fields: dict[str, list[float]] = {}
    units: dict[str, str] = {}
    for attr, _label, unit, _src in BLOCK_SPEC:
        fields[attr] = take(n2d)
        units[attr] = unit
    group_bounds = take(ngrups + 1)
    for attr, _label, unit, _src in OPACITY_SPEC:
        fields[attr] = take(n3d)
        units[attr] = unit

    if pos != len(values):  # pragma: no cover
        raise ParseError(
            f"ionmix/cn4: 解析后仍有 {len(values) - pos} 个数值未消费", path=rel
        )

    # ── 构造 ParsedTable ──
    t = ParsedTable(
        table_key=f"IONMIX_{Path(rel).stem}",
        kind="cn4_eos",
        family=FAMILY,
        source_relpath=rel,
        header_raw=doc_lines[0].strip() + " | " + doc_lines[1].strip(),
        n_groups=ngrups,
        group_bounds=list(group_bounds),
        layout_rule=(
            "F6/IONMIX-cn4 (abjt_03.f SUBROUTINE OWTF, isw(21)!=0): "
            "4 行头 + tplsma + densnn + 12*2D + engrup + 3*3D; "
            "2D 为 (ndens,ntemp) density-major -> 转置为 (n_Te,n_x)"
        ),
    )
    # 轴: cn4 的密度自变量是 n_ion（不是 rho）
    t.axes["nion"] = list(density)
    t.axis_units["nion"] = "cm-3"
    t.axis_log10["nion"] = True
    t.axes["Te"] = list(temperature)
    t.axis_units["Te"] = "eV"
    t.axis_log10["Te"] = True

    # 12 个二维场: (ndens,ntemp) -> (n_Te, n_x) 转置
    for attr, _label, unit, _src in BLOCK_SPEC:
        flat = fields[attr]
        t.fields[attr] = [flat[i * ntemp + j]
                          for j in range(ntemp) for i in range(ndens)]
        t.field_shape[attr] = (ntemp, ndens)
        t.field_units[attr] = unit
        t.field_log10[attr] = False

    # 三维不透明度: (ngrups,ndens,ntemp) -> (ngrups, n_Te, n_x)
    for attr, _label, unit, _src in OPACITY_SPEC:
        flat = fields[attr]
        reordered: list[float] = []
        for g in range(ngrups):
            base = g * n2d
            for j in range(ntemp):
                for i in range(ndens):
                    reordered.append(flat[base + i * ntemp + j])
        name = {
            "opac_rosseland": "kappa_rosseland",
            "opac_planck_abs": "kappa_planck_abs",
            "opac_planck_ems": "kappa_planck_ems",
        }[attr]
        t.fields[name] = reordered
        t.field_shape[name] = (ngrups, ntemp, ndens) if ngrups else (ntemp, ndens)
        t.field_units[name] = unit
        t.field_log10[name] = False

    t.n_numbers_seen = len(values)
    t.n_numbers_expected = expected
    t.unit_source = (
        "abjt_03.f SUBROUTINE OWTF (isw(21)!=0 分支, line 4662-4743) "
        "+ docs/IONMIX用户指南.md §5.4"
    )
    t.notes.append(f"组分 Z={h['izgas']} 分数={h['fracsp']}")
    t.notes.append(
        f"维度 ntemp={ntemp}, ndens={ndens}, ngrups={ngrups}; "
        f"计数守恒 {len(values)}/{expected} OK"
    )
    t.notes.append(
        "轴 nion (cm^-3) 为 cn4 固有自变量；rho 需经 <A> 换算，"
        "未提供 atomwt 时不给 rho（不猜）"
    )
    t.notes.append(
        "⚠️ 场 deion_dn / deele_dn 的单位源码自身注为 '(not sure)' "
        "-> unit_source 标 unknown，见 eosop_pro.cn4.units.UNCERTAIN_UNITS"
    )
    t.notes.append(
        "提示: 不透明度三块已并入本表（cn4 为 EOS+opacity 合一表）；"
        "如需按族拆分请用 eosop_pro.cn4.cn4_to_parsed_tables"
    )
    return t


def _build_table_cnr(rel: str, path: str | Path) -> ParsedTable:
    """解析 legacy ``.cnr``（late-1986 CONRAD），并适配为单张 ParsedTable。

    ``.cnr`` 与 ``.cn4`` 是 ``abjt_03.f`` ``OWTF`` 的**两个互斥输出分支**:

    * ``isw(21) != 0``  → unit 123 → ``.cn4``（18 块，含完整 EOS）
    * ``isw(8) = 1/12/13`` → unit 8  → ``.cnr``（7 块，**无** EOS 二维场）

    故本函数只输出 ``.cnr`` 实际拥有的量: 组分、``zbar``、``enrgy``、
    能群边界、以及三块群/2-T 不透明度。**不伪造**缺失的 EOS 场。
    """
    from ..cn4.cnr_io import parse_cnr

    c = parse_cnr(path)

    t = ParsedTable(
        table_key=f"IONMIX_{Path(rel).stem}",
        kind="cnr_legacy",
        family=FAMILY,
        source_relpath=rel,
        header_raw=c.header_lines[0].strip() + " | " + c.header_lines[1].strip(),
        n_groups=c.ngrups,
        group_bounds=list(c.blocks.get("engrup", [])),
        layout_rule=(
            "F6/IONMIX-cnr (abjt_03.f SUBROUTINE OWTF, isw(8)=1/12/13, "
            "late-1986 CONRAD): 4 行头 + zbar + enrgy + op2tr + op2tp + "
            "engrup + orgp + opgpe; 头部第 4 行为 981 (4e12.6,i12)"
        ),
    )

    n2d = c.n2d
    # 轴: .cnr 头部的 4 个网格参数无法直接给出网格点（只有步长/起点），
    # 网格点须由 dlgden/dlgtmp 与 rho0/T0 递推 —— 此处不做递推（避免猜），
    # 仅把参数记录在 notes，轴留空由上层决定。
    t.axes["nion_index"] = list(range(c.ndens))
    t.axis_units["nion_index"] = "-"
    t.axes["Te_index"] = list(range(c.ntemp))
    t.axis_units["Te_index"] = "-"

    # 二维场（density-major -> 转置为 (n_Te, n_x)）
    for attr in ("zbar", "enrgy"):
        flat = c.blocks.get(attr, [])
        if len(flat) != n2d:
            continue
        if c.blocks.get(attr):
            t.fields[attr] = [flat[i * c.ntemp + j]
                              for j in range(c.ntemp) for i in range(c.ndens)]
            t.field_shape[attr] = (c.ntemp, c.ndens)
            t.field_units[attr] = "-" if attr == "zbar" else "J/g"
            t.field_log10[attr] = False

    # 三维群不透明度（(ngrups, ndens, ntemp) -> (ngrups, n_Te, n_x)）
    for src_name, dst_name, unit in (
        ("orgp", "kappa_rosseland", "cm2/g"),
        ("opgpe", "kappa_planck_ems", "cm2/g"),
        ("op2tr", "kappa_2t_rosseland", "cm2/g"),
        ("op2tp", "kappa_2t_planck", "cm2/g"),
    ):
        flat = c.blocks.get(src_name, [])
        if not flat:
            continue
        if src_name.startswith("op2t"):
            # 2-T 表: 形状 (ntrad*ndens*ntemp) —— ntrad 为辐射温度点数
            t.fields[dst_name] = list(flat)
            t.field_shape[dst_name] = (c.ntrad, c.ntemp, c.ndens)
            t.field_units[dst_name] = unit
            t.field_log10[dst_name] = False
            continue
        reordered: list[float] = []
        for g in range(c.ngrups):
            base = g * n2d
            for j in range(c.ntemp):
                for i in range(c.ndens):
                    reordered.append(flat[base + i * c.ntemp + j])
        t.fields[dst_name] = reordered
        t.field_shape[dst_name] = (c.ngrups, c.ntemp, c.ndens)
        t.field_units[dst_name] = unit
        t.field_log10[dst_name] = False

    t.n_numbers_seen = len(c.raw_tail_values)
    t.n_numbers_expected = len(c.raw_tail_values)
    t.unit_source = (
        "abjt_03.f SUBROUTINE OWTF (isw(8)=1/12/13 分支, line 4598-4621); "
        "IONMIX 用户指南未文档化 .cnr —— 单位取自源码注释"
    )
    t.notes.append(f"组分 Z={c.izgas} 分数={c.fracsp}")
    t.notes.append(
        f"格式 cnr (late-1986 CONRAD); 维度 ntemp={c.ntemp}, ndens={c.ndens}, "
        f"ngrups={c.ngrups}, ntrad="
        f"{c.ntrad if c.ntrad is not None else 'unknown'}"
    )
    t.notes.append(
        "头部 981 行网格参数 dlgden=%s rho0_log=%s dlgtmp=%s t0_log=%s "
        "(物理含义 inferred, 指南未文档化)" % (c.dlgden, c.rho0_log, c.dlgtmp, c.t0_log)
    )
    if c.unknown_blocks:
        t.notes.append(
            f"⚠️ 无法唯一切分的块 -> {list(c.unknown_blocks)} (标 unknown, 不猜)"
        )
    t.notes.append(
        "⚠️ .cnr **不含** .cn4 的 12 个 EOS 二维场（压力/比热/离子电子分量）"
        "-> 不可用于 EOS 路径分析，也不可直接转 .cn4"
    )
    t.notes.extend(c.notes)
    return t


def parse_all(path: str | Path, relpath: str = "", *,
              unit_hint_T: str | None = None,
              atomwt: list[float] | None = None) -> list[ParsedTable]:
    """解析 IONMIX 表为 1 张 ``ParsedTable``。

    按扩展名分派:

    * ``.cn4`` → 完整 18 块解码，kind=``cn4_eos``（EOS + 三块不透明度合一）
    * ``.cnr`` → legacy 7 块解码，kind=``cnr_legacy``（仅组分/zbar/enrgy/群不透明度）

    Args:
        path: cn4 / cnr 文件路径
        relpath: 相对路径（用于溯源显示）
        unit_hint_T: 忽略 —— cn4 的 T 单位由源码确定为 **eV**，
            **不接受**外部覆盖（若传入非 eV 值会被记为 note）。
        atomwt: 可选原子量列表，顺序同 ``izgas``；仅影响 ``rho`` 派生场
            （当前 ``_build_table`` 未算 rho，故此处保留签名兼容）。
    """
    from ..cn4.cn4_io import parse_header
    from ..core.textio import read_text

    rel = relpath or Path(str(path)).name

    if str(path).lower().endswith(".cnr"):
        return [_build_table_cnr(rel, path)]

    doc = read_text(path)
    rel = relpath or doc.path.name
    lines = doc.lines
    if len(lines) < 5:
        raise ParseError(f"ionmix/cn4: 行数过少 ({len(lines)})", path=rel)

    try:
        head = parse_header(lines)
    except Exception as exc:  # noqa: BLE001
        raise ParseError(f"ionmix/cn4: 头部解析失败: {exc}", path=rel) from exc

    # 合理性闸门：阻止把非 cn4 文本误判为 cn4
    if not (1 <= head["ntemp"] <= 100000 and 1 <= head["ndens"] <= 100000):
        raise ParseError(
            f"ionmix/cn4: 维度不合理 ntemp={head['ntemp']} ndens={head['ndens']}"
            f"（可能不是 cn4 文件）",
            path=rel,
        )

    t = _build_table(rel, lines)
    if head["ngrups"] == 0:
        t.notes.append("⚠️ ngrups=0（无群不透明度），三维块为空")
    if unit_hint_T and unit_hint_T.lower() not in ("ev",):
        t.notes.append(
            f"⚠️ 外部声明 T 单位 '{unit_hint_T}' 被忽略 —— cn4 的 T 单位由 "
            f"abjt_03.f 确定为 eV（block 1 注释 `(in ev)`）"
        )
    return [t]


def parse(path: str | Path, relpath: str = "", *,
          unit_hint_T: str | None = None,
          atomwt: list[float] | None = None) -> ParsedTable:
    return parse_all(path, relpath, unit_hint_T=unit_hint_T, atomwt=atomwt)[0]
