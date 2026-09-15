"""A2 —— F1「反演 EOS」解析器测试。

关键结论（实测基准）
* ``AL_eos``: 头 ``37181000 2.7 66 74`` → 全文件 **9978** 个数；布局 ``with_e0``
* ``AU_eos``: 头 ``27001000 19.300003 101 23``
* ``BE_eos``: 头 ``2020 0.0 101 50``
* ``AU_eosd``: **2 个块**串联、布局 ``no_e0``（无冷能数组），每块 4770
* ``BE_eos_i``: 布局 ``with_e0`` + **2 个尾部补零**

★ 最重要的一条：F1 的**自变量是 (rho, de)**，温度 T 是**因变量（场）**，不是坐标轴。
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
from eosop_pro.parsers import multi_inverted_eos as f1


def _p(rel):
    return f1.parse(config.MATTER(rel), rel)


def test_al_eos_baseline():
    t = _p("mat_Al-1.0/AL_eos")
    expect_eq(t.table_id, 37181000)
    expect_eq(t.nr, 66)
    expect_eq(len(t.axes["de"]), 74, "ne")
    expect_eq(t.field_shape["P"], (74, 66), "二维场轴序 (ne, nr) = (n_Te, n_x)")
    expect_eq(t.n_numbers_seen, 9978, "全文件数值个数（含 4 个表头）")
    expect_eq(t.n_numbers_expected, 9978)
    expect("with_e0" in t.layout_rule)


def test_axes_are_rho_and_de_not_temperature():
    """★ F1 的自变量是 (rho, de)；T 是场。若把 T 当坐标轴就误解了格式。"""
    t = _p("mat_Al-1.0/AL_eos")
    expect("rho" in t.axes and "de" in t.axes, f"axes={list(t.axes)}")
    expect("Te" not in t.axes, "F1 不应有 Te 坐标轴（T 是因变量场）")
    expect("T" in t.fields, "T 应作为场存在")
    expect_eq(t.field_shape["T"], (74, 66))
    expect_eq(t.field_units["T"], "eV", "Kelvin 已换算为 eV")


def test_temperature_is_kelvin_converted_to_ev():
    """T 场来自 Kelvin 数组，已乘 EV_PER_K。"""
    t = _p("mat_Al-1.0/AL_eos")
    T = t.fields["T"]
    expect(all(v >= 0 for v in T), "温度不应为负")
    # 冷态附近 T 应接近 0；高温端应远超 1e5 eV（Kelvin 量级）
    expect(max(T) > 1e4, f"max(T)={max(T):.3g} eV 应在 keV~MeV 量级")


def test_e_equals_de_plus_e0():
    """E[i][j] = de[i] + e0[j]（逐字来自 docx 说明）。"""
    t = _p("mat_Al-1.0/AL_eos")
    ne, nr = t.field_shape["E"]
    de, e0, E = t.fields["de_energy"], t.fields["e0_cold"], t.fields["E"]
    for i in (0, ne // 2, ne - 1):
        for j in (0, nr // 2, nr - 1):
            expect(abs(E[i * nr + j] - (de[i] + e0[j])) < 1e-9,
                   f"E[{i},{j}] != de[{i}]+e0[{j}]")


def test_au_eos_and_be_eos_dims():
    au = _p("mat_Au-1.0/AU_eos")
    expect_eq((au.table_id, au.nr, len(au.axes["de"])), (27001000, 101, 23))
    be = _p("mat_Be-1.0/BE_eos")
    expect_eq((be.table_id, be.nr, len(be.axes["de"])), (2020, 101, 50))


def test_au_eosd_is_two_blocks_without_e0():
    """★ ``AU_eosd`` = 2 个同表头块；每块 payload = rho+de+P+T（**无 e0**）。
    块 1 = 101+23+2323+2323 = 4770；两块共 9548 个 payload 数。"""
    tables = f1.parse_all(config.MATTER("mat_Au-1.0/AU_eosd"), "mat_Au-1.0/AU_eosd")
    expect_eq(len(tables), 2, "应拆成 2 个块")
    for t in tables:
        expect("no_e0" in t.layout_rule, f"layout={t.layout_rule}")
        expect_eq((t.nr, len(t.axes["de"])), (101, 23))
        expect("e0_cold" not in t.fields, "no_e0 布局不应有 e0 数组")
        expect(t.n_numbers_seen == 4 + 4770, f"seen={t.n_numbers_seen}")
    expect(tables[0].table_key.endswith("_b1"))
    expect(tables[1].table_key.endswith("_b2"))


def test_be_eos_i_has_documented_tail_padding():
    """``BE_eos_i`` 精确公式差 2 项 → 必须**显式标注** raw_tail，不能静默吸收。"""
    t = _p("mat_Be-1.0/BE_eos_i")
    expect_eq((t.nr, len(t.axes["de"])), (2, 2))
    expect("raw_tail" in t.fields, f"fields={list(t.fields)}")
    expect_eq(len(t.fields["raw_tail"]), 2)
    expect(any("未声明" in n for n in t.notes), f"应有告警 note，实测 {t.notes}")


def test_kind_from_filename_token():
    expect_eq(_p("mat_Be-1.0/BE_eos_e").kind, "EOS_ELECTRON")
    expect_eq(_p("mat_Be-1.0/BE_eos_i").kind, "EOS_ION")
    expect_eq(_p("mat_Al-1.0/AL_eos").kind, "EOS_TOTAL")


def test_layout_detector_rejects_unknown_counts():
    import eosop_pro.core.errors as errs
    raised = False
    try:
        f1.detect_layout(10, 10, 3)
    except errs.ParseError:
        raised = True
    expect(raised, "无法解释的数量必须抛 ParseError")


def test_header_must_have_four_numbers():
    import eosop_pro.core.errors as errs
    raised = False
    try:
        f1.parse_header("1 2 3")
    except errs.ParseError:
        raised = True
    expect(raised)


if __name__ == "__main__":
    raise SystemExit(main(globals()))
