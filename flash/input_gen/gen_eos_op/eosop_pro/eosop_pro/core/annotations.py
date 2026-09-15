"""注释 / 文字说明证据通道 —— 把「注释」从"要跳过的噪声"升级为"一等证据"。

实测覆盖率（matter++，1164 个文本类文件）
-----------------------------------------
* **707 个（61%）** 的前 12 行含成词文本 → 注释承载
* **105 个** 在表头**显式声明单位**
* 来源标记：SESAME 160、FEOS 53、QEOS 17、TOPS/Atomic 13、SNOP 8、Hyades 5

为什么它重要
------------
纯数字**无法**区分 ``Al_Zeff.dat``（keV）与 ``Al_Z.dat``（eV）——
两者表头与行数完全相同（均 128 行），logT 差恰为 log10(1000)=3.0。
注释通道把这两个问题从「猜」变成「**声明**」：

* 伴随文件 ``Thermos/Readme.txt`` 明写 ``*_Z.dat`` 用 eV、``*_Zeff.dat`` 用 keV
* 文件内嵌：``ATOMIC/*.txt`` 的 ``T in keV``、``.coldopacity`` 的两行表头
* ``AU_info`` / ``opbe.inhalt`` 给出群上限与单位

两阶段中的角色
--------------
* **阶段 A**：解析器读**自己格式规范内**的表头/注释（按声明类型解析）；并读**伴随**注释文件。
* **阶段 B**：把注释当作**推断证据** —— 从注释反推类型/单位。
同一份注释，用途方向不同。
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from . import anchors as an
from . import fortran_numbers as fn
from .textio import TextDoc

__all__ = [
    "PROVENANCE_KEYWORDS",
    "GroupScheme",
    "Annotation",
    "canon_unit",
    "extract_annotations",
    "extract_from_text",
]

#: 生成器 / 来源关键词 → 规范名
PROVENANCE_KEYWORDS: tuple[tuple[str, str], ...] = (
    (r"split_EOS_table", "split_EOS_table"),
    (r"\bSNOP\b", "SNOP"),
    (r"\bMPQEOS\b|\bMPQeos\b", "MPQeos"),
    (r"\bFEOS\b", "FEOS"),
    (r"\bQEOS\b|\bLLNL-QEOS\b", "QEOS"),
    (r"\bHYADES\b|\bHyades\b", "Hyades"),
    (r"LANL\s+SESAME|\bSESAME\b", "SESAME"),
    (r"\bTOPS\b|\bLEDCOP\b|Atomic\S*网站", "LEDCOP/Atomic"),
    (r"\bThermos\b", "Thermos"),
    (r"\bIONMIX\b|\bIonmix\b", "Ionmix"),
    (r"lililing|李丽玲", "lililing"),
    (r"Calculated\s+by\s+(\S+)", "author"),
)

#: ``T in keV`` / ``Te in eV`` 这类直白声明
_UNIT_INLINE = re.compile(
    r"\bT(?:e|emperature)?\s*in\s+(keV|MeV|eV|Kelvin|K)\b", re.I
)
_RHO_INLINE = re.compile(r"\bdensity\s+in\s+(\S+)|\brho\s+in\s+(\S+)", re.I)
_OP_INLINE = re.compile(r"\b(?:opacit\w*)\s+in\s+(\S+)", re.I)
_PRESSURE_INLINE = re.compile(r"\b(?:pressure)\s+in\s+(\S+)", re.I)
_ENERGY_INLINE = re.compile(r"\b(?:energy)\s+in\s+(\S+)", re.I)

#: 单位**变更史**（``mat_CELIA/C.ZEFF.readme``）：
#: "Orginal C.ZEFF with Te in eV. Changed to keV."
#: 这类文字**不能**简单取第一个单位 —— 必须区分「曾经」与「现在」。
_UNIT_WAS = re.compile(r"Orginal\s+.*?with\s+Te\s+in\s+(keV|eV)", re.I)
_UNIT_NOW = re.compile(r"Changed\s+to\s+(keV|eV)", re.I)

#: 「文件名模式 → 单位」声明（``Thermos/Readme.txt``）：
#: ``*_Z.dat 文件温度单位为eV`` / ``*_Zeff.dat 文件温度单位为keV``
#: 这是解决 ``Al_Zeff.dat``(keV) 与 ``Al_Z.dat``(eV) 表头完全同构问题的**声明**。
_FILE_PAT = re.compile(r"(\*?[\w.]*?(?:_Zeff|_Z|_Z\.dat)\.dat)")
#: 注意：**不能用 ``\b``** —— 单位 token 前一个字符常是中文（「为」），
#: 而 Python 的 ``\b`` 基于 Unicode ``\w``，会把汉字当词字符，
#: 导致 ``为keV`` 之间不存在词边界、``\bkeV`` 匹配失败（实测踩过）。
_UNIT_TOKEN = re.compile(r"(?<![A-Za-z])(keV|MeV|eV|Kelvin)(?![A-Za-z])")

#: 单位规范名（统一大小写与写法，便于比对与写 h5）
_UNIT_CANON: dict[str, str] = {
    "ev": "eV", "kev": "keV", "mev": "MeV", "k": "K", "kelvin": "Kelvin",
    "gpa": "GPa", "mbar": "Mbar", "mj/kg": "MJ/kg", "erg/g": "erg/g",
    "gm/cc": "g/cm3", "g/cc": "g/cm3", "gm/cm3": "g/cm3", "gm/cm**3": "g/cm3",
    "cm**2/gm": "cm2/g", "cm2/g": "cm2/g", "cm^2/g": "cm2/g",
    "dyn/cm2": "dyne/cm2", "dyne/cm2": "dyne/cm2",
}


def canon_unit(u: str) -> str:
    """单位规范化（大小写与写法统一）。未知单位原样返回。"""
    s = (u or "").strip()
    return _UNIT_CANON.get(s.lower(), s)


@dataclass
class GroupScheme:
    """群划分方案（SNOP 的 ``GRUPPENEINTEILUNG``）。"""

    scheme_id: int | None = None
    ng: int | None = None
    bounds_eV: list[float] = field(default_factory=list)
    range_text: str = ""

    def summary(self) -> str:
        rng = f" range={self.range_text}" if self.range_text else ""
        return f"scheme={self.scheme_id} NG={self.ng}{rng} n_bounds={len(self.bounds_eV)}"


@dataclass
class Annotation:
    """一个文件（数据文件自身，或其伴随注释文件）抽出的全部注释证据。"""

    source: str = ""
    kind: str = "companion"          # companion | inline
    material_name: str | None = None
    material_z: float | None = None
    material_a: float | None = None
    composition: str | None = None
    provenance: list[str] = field(default_factory=list)
    dims: dict[str, int] = field(default_factory=dict)
    units: dict[str, str] = field(default_factory=dict)
    table_ids: dict[str, int] = field(default_factory=dict)
    #: 文件名模式 → 单位（如 ``_Zeff.dat`` → ``keV``）
    file_unit_hints: dict[str, str] = field(default_factory=dict)
    group_scheme: GroupScheme | None = None
    powerlaw: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not any([
            self.material_name, self.composition, self.provenance, self.dims,
            self.units, self.table_ids, self.file_unit_hints,
            self.group_scheme, self.powerlaw,
        ])

    def to_row(self) -> dict[str, Any]:
        d = asdict(self)
        d["provenance"] = ",".join(self.provenance)
        d["dims"] = ",".join(f"{k}={v}" for k, v in self.dims.items())
        d["units"] = ",".join(f"{k}={v}" for k, v in self.units.items())
        d["table_ids"] = ",".join(f"{k}={v}" for k, v in sorted(self.table_ids.items()))
        d["file_unit_hints"] = ",".join(
            f"{k}={v}" for k, v in sorted(self.file_unit_hints.items())
        )
        d["group_scheme"] = self.group_scheme.summary() if self.group_scheme else ""
        d["powerlaw"] = ",".join(f"{k}={v}" for k, v in self.powerlaw.items())
        d["notes"] = " ;; ".join(self.notes)
        return d


# ── 内部抽取步骤 ────────────────────────────────────────────────

def _dims_from_anchors(text: str, ann: Annotation) -> None:
    for anchor, key in (
        ("ledcop_n_t", "NT"), ("ledcop_n_rho", "NR"), ("ledcop_n_mat", "NMAT"),
        ("info_ime", "IME"), ("info_imi", "IMI"),
        ("ledcop_t_grid_hdr", "T_GRID_PTS"), ("ledcop_rho_grid_hdr", "RHO_GRID_PTS"),
    ):
        m = an.find(text, anchor)
        if m:
            try:
                ann.dims[key] = int(m.group(1))
            except (TypeError, ValueError):
                continue
    # SNOP 参数文件形式的 `NT = 20` / `NG = 40`
    for m in an.find_all(text, "snop_kv"):
        key, val = m.group(1), m.group(2)
        if key.upper() in ("NT", "NR", "NG", "NP", "NE", "NPLA", "NROSS", "NEPS", "NZ"):
            try:
                if key.upper() in ("NPLA", "NROSS", "NEPS", "NZ"):
                    ann.table_ids.setdefault(key.upper(), int(float(val)))
                else:
                    ann.dims[key.upper()] = int(float(val))
            except ValueError:
                continue


def _units_from_text(text: str, ann: Annotation) -> None:
    m = an.find(text, "ledcop_units")
    if m:
        ann.units.setdefault("T", m.group(1))
        ann.units.setdefault("rho", m.group(2))
        ann.units.setdefault("kappa", "cm**2/gm")
        ann.notes.append("units declared inline (LEDCOP family header)")

    m = an.find(text, "powerlaw_units")
    if m:
        ann.units.setdefault("T", m.group(1))
        ann.units.setdefault("rho", m.group(2))
        ann.units.setdefault("kappa", m.group(3))
        ann.notes.append("units declared inline (power-law readme)")

    for rx, key in ((_UNIT_INLINE, "T"), (_RHO_INLINE, "rho"),
                    (_OP_INLINE, "kappa"), (_PRESSURE_INLINE, "P"),
                    (_ENERGY_INLINE, "E")):
        mm = rx.search(text)
        if mm:
            val = next((g for g in mm.groups() if g), None)
            if val:
                ann.units.setdefault(key, val.strip())

    # 群上限声明（Mix20keV/Be20keV/DT20keV.info: "extended to 20 keV (30 groups)"）
    m = an.find(text, "info_n_groups_keV")
    if m:
        ann.units.setdefault("group_bound", "keV")
        try:
            ann.dims.setdefault("NG", int(m.group(2)))
        except ValueError:
            pass
    # 德语群声明（AU_info: "20 GRUPPEN ZWISCHEN 0 UND 5 KEV"）
    m = an.find(text, "snop_groups_de")
    if m:
        ann.units.setdefault("group_bound", m.group(4).lower())
        try:
            ann.dims.setdefault("NG", int(m.group(1)))
        except ValueError:
            pass


def _table_ids_from_text(text: str, ann: Annotation) -> None:
    for m in an.find_all(text, "snop_table_id"):
        letter, num = m.group(1), m.group(2)
        try:
            ann.table_ids[letter] = int(num)
        except ValueError:
            continue
    for anchor, key in (("info_ip", "IP"), ("info_ir", "IR"), ("info_eps", "IEPS")):
        m = an.find(text, anchor)
        if m:
            try:
                ann.table_ids.setdefault(key, int(m.group(1)))
            except ValueError:
                pass


def _group_scheme_from_lines(lines: list[str], ann: Annotation) -> None:
    for i, ln in enumerate(lines):
        m = an.match_line(ln, "snop_group_scheme") or an.find(ln, "snop_group_scheme")
        if not m:
            continue
        scheme = GroupScheme()
        try:
            scheme.scheme_id = int(m.group(1))
            scheme.ng = int(m.group(2))
        except ValueError:
            pass
        scheme.range_text = m.group(3).strip()
        # 其后若干行的数值即群边界（每行若干个数）
        bounds: list[float] = []
        for follow in lines[i + 1: i + 1 + 60]:
            if not follow.strip():
                continue
            if fn.has_letters(follow):
                break
            bounds.extend(fn.extract_numbers(follow))
            if scheme.ng and len(bounds) >= scheme.ng + 1:
                break
        # NG 个群需要 NG+1 个边界；行尾可能多读进若干值，按 NG 截断
        if scheme.ng and len(bounds) > scheme.ng + 1:
            bounds = bounds[: scheme.ng + 1]
        scheme.bounds_eV = bounds
        ann.group_scheme = scheme
        ann.notes.append(f"group scheme: {scheme.summary()}")
        return


def _material_from_text(text: str, ann: Annotation) -> None:
    m = re.search(r"NLTE\s+TABELLE\s+FUER\s+(\w+)", text)
    if m:
        ann.material_name = ann.material_name or m.group(1).title()

    m = an.find(text, "info_files_line")
    if m:
        files = m.group(1)
        ann.notes.append(f"companion files: {files.strip()}")
        if ann.material_name is None and m.group(2):
            cand = m.group(2).strip()
            if re.fullmatch(r"[A-Z][a-z]+(?: [A-Z][a-z]+)*", cand):
                ann.material_name = cand

    if "GOLD" in text and ann.material_name is None:
        ann.material_name = "GOLD"

    v = an.find(text, "info_atomic_mass")
    if v:
        try:
            ann.material_a = float(v.group(1))
        except ValueError:
            pass

    comp = an.find(text, "info_mass_comp")
    if comp:
        ann.composition = comp.group(1).strip()
        ann.notes.append("mass composition declared")
    else:
        comp = an.find(text, "info_atom_comp")
        if comp:
            ann.composition = comp.group(1).strip()
            ann.notes.append("atom composition declared")


def _powerlaw_from_text(text: str, ann: Annotation) -> None:
    if an.find(text, "powerlaw_eq") is None:
        return
    for m in an.find_all(text, "powerlaw_coeff_abc"):
        try:
            ann.powerlaw[m.group(1)] = float(m.group(2))
        except ValueError:
            continue
    if ann.powerlaw:
        ann.notes.append(f"power-law coefficients: {ann.powerlaw}")
    # c: 1.38889e-007 / a: 1.5 / b: -1.2  （mat_Au/Au_Rosseland_*.readme 形式）
    for m in re.finditer(r"^\s*([abc])\s*:\s*([-\d.eE+]+)\s*$", text, re.M):
        try:
            ann.powerlaw.setdefault(m.group(1), float(m.group(2)))
        except ValueError:
            continue


def _provenance_from_text(text: str, ann: Annotation) -> None:
    for pattern, name in PROVENANCE_KEYWORDS:
        m = re.search(pattern, text)
        if not m:
            continue
        if name == "author":
            ann.notes.append(f"author: {m.group(1)}")
            continue
        if name not in ann.provenance:
            ann.provenance.append(name)


# ── 内联 TSV 表头（自描述表）──────────────────────────────────
# 实测：ColdOpacity/*.coldopacity（67 个）前两行就是「列名 / 单位」：
#     Eph\tmiu
#     eV\tcm2/g
# 这是最直白的单位**声明**，必须抽出来。
_TSV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_TSV_UNIT = re.compile(r"[\w/*^.]+")
_UNIT_LIKE = re.compile(
    r"(?:^|[\W])(eV|keV|MeV|K|g|cc|cm|cm2|gm|Mbar|GPa|erg|dyne|J|MJ)(?:$|[\W])",
    re.I,
)


def _tsv_header_from_lines(lines: list[str], ann: Annotation) -> None:
    for i in range(min(4, len(lines) - 1)):
        names = re.split(r"[\t ]+", lines[i].strip())
        units = re.split(r"[\t ]+", lines[i + 1].strip())
        if len(names) < 2 or len(names) != len(units):
            continue
        if not all(_TSV_NAME.fullmatch(t) for t in names):
            continue
        if not all(_TSV_UNIT.fullmatch(t) for t in units):
            continue
        joined = " ".join(units)
        if not _UNIT_LIKE.search(joined):
            continue
        for n, u in zip(names, units):
            ann.units.setdefault(n, u)
        ann.notes.append(f"inline TSV header: names={names} units={units}")
        return


def _version_from_text(text: str, ann: Annotation) -> None:
    for m in re.finditer(r"(SNOP|MPQEOS|mpqeos|snop)[-\s]*version\s*\[?([\w.\-]+)\]?", text):
        ann.notes.append(f"version {m.group(1)}={m.group(2)}")
    m = re.search(r"version\s*\[([\w.\-]+)\]", text)
    if m:
        ann.notes.append(f"version={m.group(1)}")


def _unit_history_from_text(text: str, ann: Annotation) -> None:
    """处理**单位变更史**（``mat_CELIA/C.ZEFF.readme``）。

    原文：``Orginal C.ZEFF with Te in eV. Changed to keV.``
    → 若简单取第一个单位会得到 ``eV``（**错的**，现行是 keV）。
    正确做法：取 ``Changed to`` 的单位作为现行值，并把历史记入 notes。

    注意：本步骤**必须在** :func:`_units_from_text` **之前**执行 —— 否则
    ``Te in eV`` 会先被通用规则写成 ``T=eV`` 并锁死（``setdefault`` 不覆盖）。
    这里用**直接赋值**以确保「现行单位」胜出。
    """
    was = _UNIT_WAS.search(text)
    now = _UNIT_NOW.search(text)
    if now:
        ann.units["T"] = canon_unit(now.group(1))
        if was:
            ann.notes.append(
                f"unit history: was {was.group(1)} -> now {now.group(1)} "
                f"(现行取 Changed to 的值)"
            )
        else:
            ann.notes.append(f"unit changed to {now.group(1)}")


def _file_unit_hints_from_text(text: str, ann: Annotation) -> None:
    """抽取「文件名模式 → 单位」声明（``Thermos/Readme.txt``）。

    原文（GB18030）::

        *_Z.dat 文件温度单位为eV
        *_Zeff.dat 文件温度单位为keV
    """
    for m in _FILE_PAT.finditer(text):
        pat = m.group(1).lstrip("*")
        window = text[m.end(): m.end() + 40]
        u = _UNIT_TOKEN.search(window)
        if not u:
            continue
        ann.file_unit_hints.setdefault(pat, canon_unit(u.group(1)))
    if ann.file_unit_hints:
        ann.notes.append(f"file-name unit hints: {ann.file_unit_hints}")


def _canonicalize_units(ann: Annotation) -> None:
    """把全部单位规范化（大小写/写法统一），最后一步执行。"""
    for k, v in list(ann.units.items()):
        ann.units[k] = canon_unit(v)
    for k, v in list(ann.file_unit_hints.items()):
        ann.file_unit_hints[k] = canon_unit(v)


def _provenance_from_table_ids(ann: Annotation) -> None:
    """由 ``Z/P/R/E`` 表号映射反推 SNOP 来源。

    ``AU_info`` 这类文件本身不写 "SNOP"，但它的 ``MATERIALNUMMERN`` 段
    （``Z:27002003; P:27003003; R:27004003; E:27005003``）是 SNOP 输出的标准签名。
    """
    letters = set(ann.table_ids) & {"Z", "P", "R", "E", "NPLA", "NROSS", "NEPS", "NZ"}
    if len(letters) >= 2 and "SNOP" not in ann.provenance:
        ann.provenance.append("SNOP")
        ann.notes.append(f"provenance inferred from table-id letters {sorted(letters)}")


# ── 公开 API ───────────────────────────────────────────────────
def extract_annotations(doc: TextDoc, *, kind: str = "companion",
                        source: str = "") -> Annotation:
    """从 :class:`TextDoc` 抽取注释证据（**绝不抛异常**，异常降级为 note）。"""
    return extract_from_text(doc.text, source=source or str(doc.path), kind=kind,
                             lines=doc.lines)


def extract_from_text(text: str, *, source: str = "", kind: str = "companion",
                      lines: list[str] | None = None) -> Annotation:
    """从原始文本抽取注释证据。"""
    ann = Annotation(source=source, kind=kind)
    ls = lines if lines is not None else text.splitlines()
    for step in (
        lambda: _material_from_text(text, ann),
        lambda: _dims_from_anchors(text, ann),
        # 单位历史必须先于通用单位规则，否则 eV/keV 会被旧值锁死
        lambda: _unit_history_from_text(text, ann),
        lambda: _file_unit_hints_from_text(text, ann),
        lambda: _units_from_text(text, ann),
        lambda: _table_ids_from_text(text, ann),
        lambda: _provenance_from_table_ids(ann),
        lambda: _group_scheme_from_lines(ls, ann),
        lambda: _tsv_header_from_lines(ls, ann),
        lambda: _powerlaw_from_text(text, ann),
        lambda: _provenance_from_text(text, ann),
        lambda: _version_from_text(text, ann),
        lambda: _canonicalize_units(ann),
    ):
        try:
            step()
        except Exception as exc:  # noqa: BLE001 —— 抽取失败不得中断主流程
            ann.notes.append(f"extract step failed: {type(exc).__name__}: {exc}")
    return ann
