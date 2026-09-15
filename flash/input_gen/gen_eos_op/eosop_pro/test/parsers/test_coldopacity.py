"""A2 —— F6b 冷不透明度（``*.coldopacity``）解析器测试。

实测 ``ColdOpacity/Al.coldopacity``：**两行自描述表头**（列名 / 单位，制表符分隔）::

    Eph	miu
    eV	cm2/g

这是全库最直白的单位声明 —— 解析器必须把两行都抽出来并写进 ``axis_units``。
"""

import sys
import os
# --- path bootstrap (auto) ---
_d = os.path.dirname(os.path.abspath(__file__))
while _d != os.path.dirname(_d) and not os.path.isfile(
        os.path.join(_d, "_runner.py")):
    _d = os.path.dirname(_d)
if _d not in sys.path:
    sys.path.insert(0, _d)
import _runner  # noqa: F401
from _runner import expect, expect_eq, main

from eosop_pro import config
from eosop_pro.parsers import coldopacity as co


def test_two_line_header_parsed():
    names, units, start = co.parse_two_line_header(
        ["Eph\tmiu", "eV\tcm2/g", "", "10\t486606.52638"]
    )
    expect_eq(names, ["Eph", "miu"])
    expect_eq(units, ["eV", "cm2/g"])
    expect_eq(start, 2)


def test_al_coldopacity_units_declared():
    t = co.parse(config.MATTER("ColdOpacity/Al.coldopacity"),
                 "ColdOpacity/Al.coldopacity")
    expect_eq(t.kind, "COLDOPACITY")
    expect("Eph" in t.axes, f"axes={list(t.axes)}")
    expect_eq(t.axis_units["Eph"], "eV", "光子能量单位来自文件内嵌声明")
    expect_eq(t.field_units["miu"], "cm2/g")
    expect("declared:inline" in t.unit_source)


def test_axis_log10_flags_are_false():
    """该族是线性列式数据（不是 log10 网格）。"""
    t = co.parse(config.MATTER("ColdOpacity/Al.coldopacity"),
                 "ColdOpacity/Al.coldopacity")
    expect(t.axis_log10["Eph"] is False, "Eph 非 log10")
    expect(t.field_log10["miu"] is False, "miu 非 log10")


def test_values_positive_and_rows_consistent():
    t = co.parse(config.MATTER("ColdOpacity/Al.coldopacity"),
                 "ColdOpacity/Al.coldopacity")
    mu = t.fields["miu"]
    expect(len(mu) > 10, f"应有足够行，实测 {len(mu)}")
    expect(all(v > 0 for v in mu[:50]), "质量衰减系数应为正")
    expect_eq(t.n_numbers_seen, t.n_numbers_expected, "行宽一致")


def test_all_coldopacity_files():
    import os
    root = config.MATTER_DIR / "ColdOpacity"
    files = sorted(f for f in os.listdir(root) if f.lower().endswith(".coldopacity"))
    expect(len(files) >= 60, f"应有 >=60 个，实测 {len(files)}")
    for f in files[:12]:
        t = co.parse(root / f, f"ColdOpacity/{f}")
        expect(t.field_units.get("miu") == "cm2/g", f"{f} 单位应为 cm2/g")


def test_header_mismatch_raises():
    import eosop_pro.core.errors as errs
    raised = False
    try:
        co.parse_two_line_header(["Eph\tmiu", "eV"])
    except errs.ParseError:
        raised = True
    expect(raised, "列名/单位数量不一致应报错")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
