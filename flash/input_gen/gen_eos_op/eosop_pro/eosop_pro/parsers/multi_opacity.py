"""F2 —— MULTI 不透明度 / Zeff / NLTE / EPS 解析器（4×15 定宽）★最大族。

★ 关键结构（实测确认，推翻"单一扁平表"的假设）
----------------------------------------------
**多群文件是 ``ng`` 个独立子表的串联，每个子表自带完整表头**：
::

    [子表头1] [能群边界线] [rho 网格] [T 网格] [值]
    [子表头2] [能群边界线] [rho 网格] [T 网格] [值]
    ...

行数算术精确验证（这是最硬的证据）::

    AU_op03p             20 子表 × (1 头 + 1 边界 + 110 payload) = 2240 行 ✓
    Thermos/Al_Planck.dat 25 子表 × (1 + 1 + 127)                = 3225 行 ✓
    AU_SIMPLE_PLANCK_MG   24 子表 × (1 + 1 + 2)                  =   96 行 ✓

且子表头之间是**逐群变化的光子能量区间**（``1.0 10.0`` → ``10.0 50.0`` → ``50.0 75.0`` …），
所以所谓"行 2 的光子能量标记"实为该群的 ``(E_lo, E_hi)``。

``opbe`` 更复杂：它是**不同 KIND 的表**的串联（``opbe.inhalt`` 声明 4 个表号
``NPLA/NROSS/NEPS/NZ``）→ 由 :func:`parse_all` 拆成多张表。

行 1 的 ``<f2>`` 是**类型枚举**（**不是** Zbar！），或一段文本标签：

===========  =========================================================
``f2`` 值     含义（实测于 547 个 F2-like 文件）
===========  =========================================================
0            EOS / 理想气体类
1            出现 34 次，含义待定（风险 R2）
4            Rosseland 类
6            **ZEFF**（119 次）
7            Planck 类
其它         实为 ``rho0`` 密度（2.7 / 19.3 / 3.51 / 1.823 / 2.985 / 9.78…）
0.1234567    LEDCOP 魔数
===========  =========================================================

标签：``PLANCK M``(102)、``ROSSLAN M``(101)、``PLANCK``(16)、``ROSSLAN``(14)、
``PS M``(10)、``EPS M``、``PLANCK 1``。
⚠️ 是 **``ROSSLAN``**（非 ``ROSSELAND``）；匹配用宽松 ``ROS+LAN?D?``。
⚠️ 多群子表头常见 **id/魔数与标签紧贴**：``.27100000E+04PLANCK M``、
``0.1234567E+000PLANCK 1``。

单位
----
rho / T / 值 **均为 log10**（``matlab/outputMULTIOpacity.m`` 逐行佐证）。
T 在多数族是 **eV**；但 ZEFF 表存在 **eV / keV 两套**
（``Thermos/Readme.txt`` 声明 ``*_Z.dat``=eV、``*_Zeff.dat``=keV）→ 由 ``unit_hint`` 传入。
"""

from __future__ import annotations

import re
from pathlib import Path

from ..core import fortran_numbers as fn
from ..core.errors import ParseError
from ..core.textio import read_text
from ..registry.database_index import SESAME_DIGIT_KIND, sesame_digit_of
from .base import ParsedTable

__all__ = ["FAMILY", "parse", "parse_all", "parse_header", "take_numbers",
           "LABEL_RE", "KIND_BY_LABEL", "KIND_BY_F2", "VALUE_FIELD_BY_KIND"]

FAMILY = "multi_opacity"

#: 标签匹配（宽松）。⚠️ 三种拼写都要吃下：``ROSSELAND``(16 次)、``ROSSLAN``(101 次)、
#: 以及不带 M 的 ``PLANCK``/``ROSSLAN``。注意 ``ROS+LAN?D?`` 这类旧写法
#: **匹配不到 ``ROSSELAND``**（``S+`` 后直接要 ``LAN``，但中间有个 ``E``）—— 实测踩过。
LABEL_RE = re.compile(
    r"(?P<name>PLANCK|ROS{1,2}E?L?A?N?D?|PS|EPS)\b\s*(?P<grp>M|\d+)?", re.I
)

#: 标签 → KIND
KIND_BY_LABEL = {
    "PLANCK": "PLANCK", "ROSSELAND": "ROSSELAND", "PS": "PLANCK", "EPS": "EMISSIVITY",
}


def norm_label(name: str) -> str:
    """把任意 ROS* 拼写归一为 ``ROSSELAND``；其余取大写。"""
    u = name.upper()
    if u.startswith("ROS"):
        return "ROSSELAND"
    return u

#: ``f2`` 枚举 → KIND（0 与 1 语义未定，留 None）
KIND_BY_F2 = {4.0: "ROSSELAND", 6.0: "ZEFF", 7.0: "PLANCK"}

#: KIND → payload 值字段名
VALUE_FIELD_BY_KIND = {
    "PLANCK": "kappa", "ROSSELAND": "kappa", "MUGROUP": "kappa_g",
    "ZEFF": "Z", "ZEFF2": "Z2", "EMISSIVITY": "eps", "NONLTE": "nonlte",
}

_UNIT_SCALE = {"ev": 1.0, "kev": 1e3, "mev": 1e6}


# ── 表头 / 行分类 ───────────────────────────────────────────────
def parse_header(line: str) -> dict:
    """解析一个子表头行。"""
    line = line.replace("\ufeff", "")
    nums = fn.extract_numbers(line)
    residue = fn.non_numeric_residue(line)
    m = LABEL_RE.search(residue)
    label = None
    ng_label = None
    if m:
        label = norm_label(m.group("name"))
        ng_label = m.group("grp")

    if len(nums) < 3:
        raise ParseError(f"F2 header needs >=3 numbers, got {len(nums)}",
                         header_raw=line)
    return {
        "table_id": int(round(nums[0])),
        "f2": None if label else (nums[1] if len(nums) >= 4 else None),
        "label": label,
        "ng_label": ng_label,
        "nr": int(round(nums[-2])),
        "nt": int(round(nums[-1])),
        "packed": bool(re.search(r"[0-9][A-Za-z]", line)),
        "raw": line,
        "n_header_nums": len(nums),
    }


def is_marker_line(line: str) -> bool:
    """该行是否恰为 2 个数字（= 该群的 ``(E_lo, E_hi)`` 边界）。"""
    if fn.has_letters(line):
        return False
    return len(fn.extract_numbers(line)) == 2


def take_numbers(lines: list[str], start: int, need: int) -> tuple[list[float], int]:
    """从 ``lines[start:]`` 精确取走 ``need`` 个数值（空行跳过）。

    若某行会使总数**超过** ``need``，说明数值跨越了子表边界 → 报错而非静默截断。
    """
    vals: list[float] = []
    pos = start
    n = len(lines)
    while len(vals) < need and pos < n:
        line = lines[pos]
        if line.strip():
            here = fn.extract_numbers(line)
            if len(vals) + len(here) > need:
                raise ParseError(
                    f"payload overshoot: have {len(vals)}, need {need}, "
                    f"line {pos} adds {len(here)} -> values span a block boundary",
                    header_raw=line,
                )
            vals.extend(here)
        pos += 1
    if len(vals) != need:
        raise ParseError(f"payload short: got {len(vals)} need {need}")
    return vals, pos


# ── KIND 判定 ───────────────────────────────────────────────────
def kind_of(header: dict, relpath: str) -> tuple[str | None, str]:
    if header["label"]:
        k = KIND_BY_LABEL.get(header["label"])
        if k:
            return k, f"label {header['label']!r}"
    if header["f2"] is not None and header["f2"] in KIND_BY_F2:
        return KIND_BY_F2[header["f2"]], f"f2 enum {header['f2']}"
    base = Path(relpath).name.lower()
    for rx, k in (
        (r"avsqfree", "ZEFF2"),
        (r"op0?3z|zeff|_z\.dat$|_z$|nofree", "ZEFF"),
        (r"op0?3p|planck|_mopp", "PLANCK"),
        (r"op0?3r|ros+lan|_mopr|workop", "ROSSELAND"),
        (r"op0?3e|_?eps\b", "EMISSIVITY"),
        (r"nlte", "NONLTE"),
    ):
        if re.search(rx, base):
            return k, f"name token {rx}"
    tid = str(header["table_id"])
    d = sesame_digit_of(tid)
    if d and d in SESAME_DIGIT_KIND:
        return SESAME_DIGIT_KIND[d], f"sesame digit {d}"
    return None, "unknown"


# ── 主解析 ──────────────────────────────────────────────────────
def parse_all(path: str | Path, relpath: str = "", *,
              unit_hint: str | None = None,
              ng_hint: int | None = None) -> list[ParsedTable]:
    """解析文件，返回**全部**表（``opbe`` 这类多 KIND 串联会拆成多张）。"""
    doc = read_text(path)
    rel = relpath or doc.path.name
    lines = doc.lines
    pos = 0
    n = len(lines)

    # 连续同 (label, kind, id, nr, nt) 的子表归为一张多群表
    order: list[tuple] = []
    buckets: dict[tuple, list[dict]] = {}
    padding: list[float] = []

    # ★ 性能：绝不能在每个子表迭代里重扫剩余行（那是 O(n²) —— 实测
    #   ``ATOMIC/Al.MultiGroupOpacity_PLANCK`` 会因此从 0.1s 涨到 23s）。
    #   改为**一次性**统计总数值数，再增量维护 consumed，padding 判定只用差值。
    total_nums = sum(len(fn.extract_numbers(ln)) for ln in lines)
    consumed_nums = 0

    while pos < n:
        if not lines[pos].strip():
            pos += 1
            continue
        # 文件末尾可能残留少量补零（该族有凑满每行 4 字段的习惯）→ 显式记为 padding
        if total_nums - consumed_nums <= 4 and not any(
            fn.has_letters(ln) for ln in lines[pos:]
        ):
            tail_vals = fn.extract_numbers("\n".join(lines[pos:]))
            padding.extend(tail_vals)
            consumed_nums += len(tail_vals)
            break
        hdr = parse_header(lines[pos])
        pos += 1
        if not (2 <= hdr["nr"] <= 50000 and 2 <= hdr["nt"] <= 50000):
            raise ParseError(f"F2 implausible dims nr={hdr['nr']} nt={hdr['nt']}",
                             path=rel, header_raw=hdr["raw"])
        markers: list[float] = []
        if pos < n and is_marker_line(lines[pos]):
            markers = fn.extract_numbers(lines[pos])
            pos += 1

        need = hdr["nr"] + hdr["nt"] + hdr["nr"] * hdr["nt"]
        vals, pos = take_numbers(lines, pos, need)
        consumed_nums += hdr["n_header_nums"] + len(markers) + len(vals)
        kind, why = kind_of(hdr, rel)
        key = (kind, hdr["label"], hdr["table_id"], hdr["nr"], hdr["nt"], why)
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append({
            "header": hdr, "markers": markers, "values": vals,
            "n_header_nums": hdr["n_header_nums"] + len(markers),
        })

    tables: list[ParsedTable] = []
    for key in order:
        kind, label, table_id, nr, nt, why = key
        subs = buckets[key]
        ng = len(subs)
        if kind in ("PLANCK", "ROSSELAND"):
            eff_kind = "MUGROUP" if ng > 1 else kind
        elif kind is None:
            # KIND 未知但确有多个子表 → 至少可断言其为多群表
            eff_kind = "MUGROUP" if ng > 1 else "PLANCK"
        else:
            eff_kind = kind
        tables.append(_build_table(
            eff_kind, label, table_id, nr, nt, ng, subs, rel, why,
            unit_hint=unit_hint, ng_hint=ng_hint,
        ))
    if padding and tables:
        last = tables[-1]
        last.fields["raw_tail"] = padding
        last.field_shape["raw_tail"] = (len(padding),)
        # 补零也要计入 expected，否则会被误报成 count_mismatch
        last.n_numbers_seen += len(padding)
        last.n_numbers_expected = (last.n_numbers_expected or 0) + len(padding)
        last.notes.append(
            f"⚠️ 文件末尾有 {len(padding)} 个补零（该族凑满每行 4 字段的填充），"
            f"已按原样保存为 raw_tail"
        )
    if not tables:
        raise ParseError("F2: no tables found", path=rel)
    return tables


def parse(path: str | Path, relpath: str = "", *,
          unit_hint: str | None = None,
          ng_hint: int | None = None) -> ParsedTable:
    """解析并返回**第一张**表（多表文件请用 :func:`parse_all`）。"""
    tables = parse_all(path, relpath, unit_hint=unit_hint, ng_hint=ng_hint)
    if len(tables) > 1:
        tables[0].notes.append(
            f"⚠️ 本文件含 {len(tables)} 张表（不同 KIND 串联）—— "
            f"parse() 只返回第一张，其余为 "
            f"{[t.table_key for t in tables[1:]]}"
        )
    return tables[0]


def _build_table(kind: str, label: str | None, table_id: int, nr: int, nt: int,
                 ng: int, subs: list[dict], rel: str, why: str, *,
                 unit_hint: str | None, ng_hint: int | None) -> ParsedTable:
    per = nr * nt
    unit = (unit_hint or "eV")
    scale = _UNIT_SCALE.get(unit.lower(), 1.0)
    kelvin = unit.lower() in ("k", "kelvin")

    # ``f2_or_label``：有标签用标签，否则用**数值类型枚举**（不可丢 —— 见 §f2 说明）
    h0 = subs[0]["header"]
    f2v = h0.get("f2")
    f2_or_label = label if label else (f"{f2v:g}" if f2v is not None else None)

    table = ParsedTable(
        table_key=f"{kind}_{table_id}",
        kind=kind,
        family=FAMILY,
        source_relpath=rel,
        table_id=table_id,
        sesame_digit=sesame_digit_of(table_id),
        f2_or_label=f2_or_label,
        header_raw=subs[0]["header"]["raw"],
        n_groups=ng,
        layout_rule="F2: ng 个独立子表串联；每子表 1 头(+1 边界) + nr + nt + nr*nt",
    )
    # 计数守恒：每个子表「头(+边界) + nr + nt + nr*nt」逐子表精确累加
    n_hdr_total = sum(s["n_header_nums"] for s in subs)
    table.n_numbers_seen = sum(s["n_header_nums"] + len(s["values"]) for s in subs)
    table.n_numbers_expected = n_hdr_total + ng * (nr + nt + per)
    if table.n_numbers_seen != table.n_numbers_expected:
        from ..core.errors import CountMismatch
        raise CountMismatch(table.n_numbers_seen, table.n_numbers_expected,
                            path=rel, header_raw=subs[0]["header"]["raw"])

    # 网格取自第一个子表（各子表网格一致，下面会校验）
    first = subs[0]["values"]
    log_rho = first[:nr]
    log_T = first[nr:nr + nt]
    for si, s in enumerate(subs[1:], start=1):
        v = s["values"]
        if v[:nr] != log_rho:
            table.notes.append(f"⚠️ 子表 {si} 的 rho 网格与子表 0 不一致")
            break
        if v[nr:nr + nt] != log_T:
            table.notes.append(f"⚠️ 子表 {si} 的 T 网格与子表 0 不一致")
            break

    T_phys = [(10.0 ** x) * scale for x in log_T]
    if kelvin:
        from .. import config
        T_phys = [t * config.EV_PER_K for t in T_phys]

    table.axes["rho"] = [10.0 ** x for x in log_rho]
    table.axis_units["rho"] = "g/cm3"
    table.axis_log10["rho"] = True
    table.axes["Te"] = T_phys
    table.axis_units["Te"] = "eV"
    table.axis_log10["Te"] = True

    field = VALUE_FIELD_BY_KIND.get(kind, "kappa")
    flat: list[float] = []
    for s in subs:
        flat.extend(s["values"][nr + nt:])
    table.fields[field] = flat
    if ng == 1:
        table.field_shape[field] = (nt, nr)
    else:
        table.field_shape[field] = (ng, nt, nr)
        table.notes.append(
            "多群数组按 **group-major** 存储 (ng, nt, nr)；"
            "子表串联结构天然给出群维，无需按 rho-major 猜测"
        )
    table.field_units[field] = "cm2/g" if field.startswith("kappa") else "1"
    table.field_log10[field] = field.startswith("kappa")

    # 能群边界：各子表的 (E_lo, E_hi)
    if ng > 1:
        pairs = [s["markers"] for s in subs if len(s["markers"]) == 2]
        if len(pairs) == ng:
            table.group_bounds = [pairs[0][0]] + [p[1] for p in pairs]
            table.notes.append(
                f"groups: {ng} 群，边界 {table.group_bounds[0]:g} … "
                f"{table.group_bounds[-1]:g} eV"
            )
        else:
            table.notes.append(f"⚠️ 仅 {len(pairs)}/{ng} 个子表带能群边界线")
    elif subs[0]["markers"]:
        table.group_bounds = list(subs[0]["markers"])

    table.unit_source = f"declared:{unit}" if unit_hint else "default:eV"
    if kind in ("ZEFF", "ZEFF2") and not unit_hint:
        table.unit_source = "default:eV (⚠️ ZEFF 表存在 eV/keV 两套，应由注释声明)"
    table.notes.append(f"kind decided by {why}")
    if subs[0]["header"]["packed"]:
        table.notes.append("子表头存在 id/魔数与标签紧贴（已按 L2 提取）")
    if ng_hint is not None and ng_hint != ng:
        table.notes.append(
            f"⚠️ 群数不一致：伴随注释声明 NG={ng_hint}，文件实为 {ng} 个子表"
        )
    return table
