"""A2 —— F6g 通用列式曲线兜底解析器测试。

用于 ``ionpot.dat`` / ``PowerLaws`` / ``XrayMassCoef`` / ``Crystal`` 等无专门解析器的列式表。
策略：**保守** —— 众数列宽 + 第 0 列作 x 轴 + 其余命名 ``colN``，单位一律 ``unknown``，
**绝不因文件名猜测物理量**。
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
from eosop_pro.parsers import generic_curve as gc


def test_comment_line_detection():
    for s in ("# comment", "% comment", "REM note", "c note", "", "   "):
        expect(gc.is_comment_line(s) is True, f"{s!r} 应判为注释")
    expect(gc.is_comment_line("1.0 2.0") is False)
    expect(gc.is_comment_line("2.7e-06 1.2e3") is False)


def test_ionpot_parses_with_wide_columns():
    t = gc.parse(config.MATTER("hyades/ionpot.dat"), "hyades/ionpot.dat")
    expect(t.n_numbers_seen > 0, "应有数据")
    expect("x" in t.axes, f"axes={list(t.axes)}")
    expect_eq(t.axis_units["x"], "unknown", "兜底解析不猜单位")
    expect(t.field_units[list(t.fields)[0]] == "unknown")


def test_modal_column_count_used():
    t = gc.parse(config.MATTER("hyades/ionpot.dat"), "hyades/ionpot.dat")
    expect(any("列宽直方图" in n for n in t.notes), f"应报告列宽直方图，实测 {t.notes}")
    expect_eq(t.n_numbers_seen, t.n_numbers_expected, "众数列宽下不应有偏差")


def test_no_physical_naming_guessed():
    t = gc.parse(config.MATTER("hyades/ionpot.dat"), "hyades/ionpot.dat")
    expect(any("不猜测" in n or "需文档" in n for n in t.notes),
           f"必须声明不猜物理语义，实测 {t.notes}")
    for name in t.fields:
        expect(name.startswith("col"), f"字段名应为 colN，实测 {name}")


def test_empty_file_raises():
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "empty.dat"
        p.write_text("# only a comment\n", encoding="utf-8")
        raised = False
        try:
            gc.parse(p, "empty.dat")
        except ValueError:
            raised = True
        expect(raised, "无数值行应抛 ValueError")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
