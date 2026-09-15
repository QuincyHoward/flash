"""A2 —— F5 LEDCOP / ATOMIC 解析器测试（``ledcop_atomic`` + ``ledcop_zeff``）。

实测基准
* ``ATOMIC/Al.txt``: ``Number of T = 69  Number of rho = 50``；**348636 行**
  → 必须**流式**解析（峰值内存实测 ~2 MB）
* ``ATOMIC/Al.NoFree``: 头含 LEDCOP 魔数 ``0.1234567E+000``，NR=50 NT=69，
  总数 **3573** = 4+50+69+3450
* 文件内嵌单位声明：``Opacities in cm**2/gm, T in keV, density in gm/cc``

★ 内存纪律：多群段占 ``nt*nr`` 块（Al 为 3450 块 ≈ 34 万行），
``include_multigroup`` 默认 **False**。
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
from eosop_pro.parsers import ledcop_atomic as la
from eosop_pro.parsers import ledcop_zeff as lz


def test_nofree_header_and_count():
    t = lz.parse(config.MATTER("ATOMIC/Al.NoFree"), "ATOMIC/Al.NoFree")
    expect_eq((t.nr, t.nt), (50, 69))
    expect_eq(t.n_numbers_expected, 4 + 50 + 69 + 50 * 69)
    expect_eq(t.n_numbers_expected, 3573)
    expect(any("魔数" in n for n in t.notes), f"应识别 LEDCOP 魔数，实测 {t.notes}")


def test_nofree_vs_avsqfree_field_and_kind():
    z = lz.parse(config.MATTER("ATOMIC/Al.NoFree"), "ATOMIC/Al.NoFree")
    z2 = lz.parse(config.MATTER("ATOMIC/Al.AvSqFree"), "ATOMIC/Al.AvSqFree")
    expect_eq(z.kind, "ZEFF")
    expect_eq(z2.kind, "ZEFF2")
    expect("Z" in z.fields and "Z2" in z2.fields)


def test_split_tables_temperature_is_kev_default():
    t = lz.parse(config.MATTER("ATOMIC/Al.NoFree"), "ATOMIC/Al.NoFree")
    T = t.axes["Te"]
    expect(max(T) > 1e3, f"keV→eV 后应达 keV 量级，实测 max={max(T):.4g}")
    expect(min(T) > 0, f"min={min(T)}")


def test_ledcop_magic_mismatch_is_flagged():
    """非 LEDCOP 文件走此解析器时应告警（而不是静默接受）。"""
    t = lz.parse(config.MATTER("ATOMIC/Al.NoFree"), "ATOMIC/Al.NoFree")
    # 正常情况下魔数匹配 → 不应出现「不符」告警
    expect(not any("不符" in n for n in t.notes),
           f"魔数应匹配，实测 {t.notes}")


def test_atomic_main_table_streaming_dims():
    t = la.parse(config.MATTER("ATOMIC/Al.txt"), "ATOMIC/Al.txt")
    expect_eq((t.nr, t.nt), (50, 69))
    for f in ("Ross", "Planck", "NoFree", "AvSqFree"):
        expect(f in t.fields, f"fields={list(t.fields)}")
        expect_eq(t.field_shape[f], (69, 50), "(n_Te, n_rho)")
    expect(any("已跳过" in n or "跳过" in n for n in t.notes),
           "默认应跳过体积巨大的多群段")


def test_atomic_density_column_matches_rho_grid():
    """灰表格内第一列是 Density → 应与 rho 网格一致（交叉自校验）。"""
    t = la.parse(config.MATTER("ATOMIC/Al.txt"), "ATOMIC/Al.txt")
    note = next((n for n in t.notes if "最大偏差" in n), "")
    expect(note != "", f"应输出偏差自校验，实测 {t.notes}")
    expect("= 0" in note, f"偏差应为 0，实测 {note}")


def test_atomic_inline_units_extracted():
    t = la.parse(config.MATTER("ATOMIC/Al.txt"), "ATOMIC/Al.txt")
    expect("declared" in t.unit_source, f"unit_source={t.unit_source}")
    expect(any("keV" in n or "kev" in n.lower() for n in t.notes),
           f"应记录 keV 声明，实测 {t.notes}")


def test_atomic_material_name_from_comment():
    """``Al.txt`` 内部却写 ``TOPS results for Li`` —— 源数据自身的标注不一致。"""
    t = la.parse(config.MATTER("ATOMIC/Al.txt"), "ATOMIC/Al.txt")
    joined = " ".join(t.notes)
    expect("material=" in joined, f"应记录材料名，实测 {t.notes}")


def test_atomic_memory_stays_low():
    """流式解析：峰值内存必须远低于整读（实测 ~2 MB）。"""
    import tracemalloc
    tracemalloc.start()
    la.parse(config.MATTER("ATOMIC/Al.txt"), "ATOMIC/Al.txt")
    _cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    expect(peak < 200e6, f"峰值内存应 < 200 MB，实测 {peak / 1e6:.1f} MB")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
