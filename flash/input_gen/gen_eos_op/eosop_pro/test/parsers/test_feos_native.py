"""A2 —— F4b FEOS 原生表（``*.feos``）解析器测试。

★ 行 0 的 10 个字段已用 ``.301`` 兄弟文件**独立交叉验证**：

* ``mat_B/B.feos``   L0 = [12.06, **123**, **101**, …] ↔ ``B.301`` hdr = [1040050301, 2.34, **123**, **101**]
* ``mat_Al-1.0/Al.feos`` L0 = [12.06, **192**, **69**, …] ↔ ``Al.feos.301`` hdr = [37170301, 2.7, **192**, **69**]

⚠️ 数据块**列序未定**（FEOS PDF §16.2 正文受抽取伪影影响无法可靠还原）→
解析器只解码表头与网格，其余按原样存 ``raw_values``，**不猜列语义**。
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
from eosop_pro.parsers import feos_native as f4b


def _p(rel):
    return f4b.parse(config.MATTER(rel), rel)


def test_header_decoded_and_cross_validated_al():
    """行 0 头部照常解码并与 ``.301`` 交叉验证；但**真实网格比声明少 1**。

    ⚠️ 2026-09 修正：``Al.feos`` 声明 ``NR=192``，实测 rho 网格只有 **191**
    点 + 1 个 ``0.0`` 哨兵（``B.feos`` 同样 123/122 —— 系统性特征）。
    盲信声明值会把哨兵并入网格尾部、把 payload 首值并入 Te 尾部
    （两轴同时非单调）。解析器现按**严格递增前缀**裁到真实长度，
    并在 notes 中记录 ``实际/声明`` 不符。守护测试见
    ``test/eosopdata/families/test_family_extract.py::
    test_feos_native_grids_are_strictly_monotonic``。
    """
    t = _p("mat_Al-1.0/Al.feos")
    expect_eq(t.nr, 191, "rho 网格应为真实长度 191（声明 192，尾部哨兵已裁）")
    expect_eq(t.nt, 69, "NT 应与 Al.feos.301 的 69 一致")
    expect_eq(t.table_id, 3717, "SESAME 号")
    expect(any("一致" in n and "301" in n for n in t.notes),
           f"应记录与兄弟文件的交叉校验，实测 {[n for n in t.notes if '301' in n]}")
    # 头部声明值仍须如实解码（notes 记录行 0 字段）
    expect(any("NR=192" in n for n in t.notes),
           f"行 0 字段 notes 应含声明的 NR=192")
    # 裁剪行为必须在 notes 中留痕
    expect(any("不符" in n and "191" in n for n in t.notes),
           f"应记录网格实际/声明不符，实测 {[n for n in t.notes if '不符' in n]}")


def test_header_decoded_and_cross_validated_b():
    """``B.feos`` 同样存在哨兵：声明 NR=123，真实网格 **122** 点。"""
    t = _p("mat_B/B.feos")
    expect_eq((t.nr, t.nt), (122, 101),
              "B.feos 真实网格 (122,101)；声明 (123,101)，尾部哨兵已裁")
    expect_eq(t.table_id, 104005)


def test_header_has_ten_fields():
    t = _p("mat_Al-1.0/Al.feos")
    expect(any("Z=12.06" in n for n in t.notes), f"notes={t.notes[:3]}")
    expect(any("rho0=2.7" in n for n in t.notes), f"notes={t.notes[:3]}")


def test_column_semantics_declared_pending():
    """数据块列序未定 → 必须显式声明，不得猜测。"""
    t = _p("mat_Al-1.0/Al.feos")
    expect("raw_values" in t.fields, f"未定列序的值应存 raw_values，实测 {list(t.fields)}")
    expect(any("列序未定" in n or "待定" in n for n in t.notes),
           f"应声明列序未定，实测 {t.notes}")
    expect(t.n_numbers_expected is None, "列序未定时不应给出精确计数公式")


def test_grids_located():
    t = _p("mat_Al-1.0/Al.feos")
    expect("rho" in t.axes and "Te" in t.axes, f"axes={list(t.axes)}")
    expect_eq(len(t.axes["rho"]), t.nr)
    expect_eq(len(t.axes["Te"]), t.nt)


def test_sibling_lookup_works():
    p = config.MATTER("mat_Al-1.0/Al.feos")
    sib = f4b.find_sibling_301(p, "mat_Al-1.0/Al.feos")
    expect(sib is not None, "应找到 FEOS/Al.feos.301")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
