"""L3 锚点库 —— 表头 / 注释/ 自由文本的**唯一**合法解析方式。

纪律：锚点匹配结果**绝不进入数值数组**。它们只用于：
材料身份、生成器来源、维度、单位、表号→类型映射、群方案、幂律系数。

实测陷阱
--------
``ALUMINUM  LANL SESAME #3711 DATED: 22581 11483`` 里的 ``3711 / 22581 / 11483``
若走 L2 正则会被当成数据 —— 这就是必须分区的根本原因。
"""

from __future__ import annotations

import re
from typing import Iterable

__all__ = ["ANCHORS", "find", "find_all", "match_line", "search_lines"]


def _c(pattern: str, flags: int = 0) -> re.Pattern[str]:
    return re.compile(pattern, flags)


ANCHORS: dict[str, re.Pattern[str]] = {
    # ── LEDCOP / ATOMIC ────────────────────────────────────────────
    "ledcop_n_t": _c(r"Number\s+of\s+T\s*=\s*(\d+)"),
    "ledcop_n_rho": _c(r"Number\s+of\s+rho\s*=\s*(\d+)"),
    "ledcop_n_mat": _c(r"Number\s+of\s+materials\s*=\s*(\d+)"),
    # 单位声明整族（13 个 ATOMIC/*.txt 都有）
    "ledcop_units": _c(
        r"Opacities\s+in\s+cm\*\*2/gm,\s*T\s+in\s+(\w+),\s*density\s+in\s+(\S+)"
    ),
    "ledcop_source": _c(r"(TOPS|Ledcop|LEDCOP)\s+results\s+for\s+(\S+)\s+on\s+(.+)"),
    "ledcop_comp_header": _c(
        r"No\.\s+Fraction\s+Mass\s+Fraction\s+At\.\s*No\.\s+Chem\.\s*Sym\.\s+Mat\s+ID\."
    ),
    "ledcop_t_grid_hdr": _c(r"Temperature\s+grid\s+used\s+the\s+following\s+(\d+)\s+points"),
    "ledcop_rho_grid_hdr": _c(r"Density\s+grid\s+used\s+the\s+following\s+(\d+)\s+points"),
    "ledcop_block_T": _c(
        r"Density\s+Ross\s+opa\s+Planck\s+opa\s+No\.\s+Free\s+Av\s+Sq\s+Free\s+T\s*=\s*"
        r"([-\d.]+E[-+]?\d+)",
        re.I,
    ),
    "ledcop_mg_block": _c(
        r"Energy\s+Ross\s+mg\s+Planck\s+mg\s+for\s+T,\s*density\s*=\s*"
        r"([-\d.]+E[-+]?\d+)\s+([-\d.]+E[-+]?\d+)",
        re.I,
    ),
    # ── Hyades / SESAME 注释行 ────────────────────────────────────
    "sesame_comment": _c(r"LANL\s+SESAME"),
    "qeos_comment": _c(r"\b(QEOS|LLNL-QEOS)\b"),
    "dated": _c(r"DATED:"),
    # ALUMINUM  LANL SESAME #3711 DATED: ...        → ("3711", None)
    # POLY      LANL SESAME #17171 DATED: ...       → ("17171", None)
    # GOLD      LANL SESAME 2700-304 DATED: ...     → ("2700", "304")
    "sesame_number": _c(r"LANL\s+SESAME\s+#?(\d+)(?:-(\d+))?"),
    # ── SNOP 伴随文件（.inhalt / _info） ──────────────────────────
    "snop_input_hdr": _c(r"EINGANGSPARAMETER"),
    "snop_matnummern": _c(r"MATERIALNUMMERN"),
    # Z:27002003; P:27003003; R:27004003  → 表号→类型字符映射
    "snop_table_id": _c(r"\b([ZPRE])\s*:\s*(\d{6,})\b"),
    "snop_kv": _c(r"^\s*([A-Z]{1,8})\s*=\s*([-+]?[\d.]+(?:E[-+]?\d+)?)", re.M),
    "snop_groups_de": _c(r"(\d+)\s+GRUPPEN\s+ZWISCHEN\s+([\d.]+)\s+UND\s+([\d.]+)\s+(\w+)"),
    "snop_group_scheme": _c(
        r"GRUPPENEINTEILUNG\s+(\d+)\s*:\s*NG\s*=\s*(\d+)\s*\(([^)]*)\)"
    ),
    # ── 伴随 .info 文件（MULTI 发行版模板） ───────────────────────
    "info_files_line": _c(r"^\s*files?\s+(.+?)\s+\((.+)\)\s*$", re.M),
    "info_ime": _c(r"IME\s*=\s*(\d+)"),
    "info_imi": _c(r"IMI\s*=\s*(\d+)"),
    "info_ip": _c(r"Planck[-\s]*(?:multigroup)?\s*(?:opacity\s*table)?\s*\(IP\s*=\s*(\d+)\)"),
    "info_ir": _c(r"Rosseland[-\s]*(?:multigroup)?\s*(?:opacity\s*table)?\s*\(IR\s*=\s*(\d+)\)"),
    "info_eps": _c(r"emissivity\s*table\s*\(IR\s*=\s*(\d+)\)", re.I),
    "info_n_groups_keV": _c(r"extended\s+to\s+([\d.]+)\s*keV\s*\((\d+)\s*groups\)", re.I),
    "info_standard_groups": _c(r"Standard\s+settings", re.I),
    "info_mass_comp": _c(r"Mass\s+composition:\s*(.+)"),
    "info_atom_comp": _c(r"Atom\s+composition:\s*(.+)"),
    "info_generated_by": _c(r"generated\s+by\s+(.+)"),
    "info_split_code": _c(r"split_EOS_table"),
    "info_atomic_mass": _c(r"Atomic\s+mass\s+([\d.]+)"),
    # ── 幂律说明（Thermos / Ge / Au Rosseland） ───────────────────
    "powerlaw_eq": _c(r"k\s*=\s*e\^?a\s*\*\s*T\^?b\s*\*\s*rho\^?c", re.I),
    "powerlaw_units": _c(r"T\s+in\s+(\w+),\s*rho\s+in\s+(\S+?),\s*k\s+in\s+(\S+)"),
    "powerlaw_valid": _c(r"Valid\s+range:\s*temperatures\s+from\s+(.+?)\s+to\s+(.+)"),
    "powerlaw_coeff_abc": _c(r"^\s*([abc])\s*:\s*([-\d.eE+]+)", re.M),
    # ── material.base ────────────────────────────────────────────
    "material_block": _c(r"^\s*MATERIAL\s+(\S+)", re.M),
    "material_kv": _c(r"^\s*([A-Za-z]+)\s+(\S+)", re.M),
    # ── 其他 ─────────────────────────────────────────────────────
    "ledcop_note_cn": _c(r"Atomic\S*网站生成的文件"),
    "coldopacity_note": _c(r"^#?\s*(Eph|miu)\b"),
    "units_eV_keV": _c(r"\b(in\s+(?:eV|keV)|in\s+Kelvin|keV|MeV|GPa|Mbar|MJ/kg|erg/g|cm\*\*2/gm|gm/cc)\b", re.I),
}


def find(text: str, name: str) -> re.Match[str] | None:
    """在 ``text`` 中找第一个锚点 ``name``。"""
    rx = ANCHORS[name]
    return rx.search(text)


def find_all(text: str, name: str) -> list[re.Match[str]]:
    return list(ANCHORS[name].finditer(text))


def match_line(line: str, name: str) -> re.Match[str] | None:
    return ANCHORS[name].match(line)


def search_lines(lines: Iterable[str], name: str) -> tuple[int, re.Match[str]] | None:
    """返回 ``(行号, match)``，找不到返回 ``None``。"""
    rx = ANCHORS[name]
    for i, ln in enumerate(lines):
        m = rx.search(ln)
        if m:
            return i, m
    return None
