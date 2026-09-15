"""Phase 1 —— 文本读取与卫生测试（编码链、换行、空行、BOM、无尾换行）。

全部断言基于**实测**属性（下表为 2026-09 实测值）：

============================  ========  ==========  =======  =========  ======
file                          n_lines   encoding    newline  trailing   blanks
============================  ========  ==========  =======  =========  ======
mat_Al-1.0/AL_eos             2495      utf-8       lf       True        0
mat_Gd/Gd100ZEFF              397       utf-8       crlf     True        1
CH/CHSi10_eos.IN              1171      utf-8       mixed    True        0
Readme.txt                    14        gb18030     crlf     **False**   3
ColdOpacity/20170117.case.log 74        utf-8-sig   crlf     **False**   1
mat_Au-1.0/AU_SIMPLE_PLANCK_MG 96       utf-8       lf       True        0
ATOMIC/Al.GrayOpacity_PLANCK  894       utf-8       crlf     True        0
============================  ========  ==========  =======  =========  ======
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
from eosop_pro.core import textio


def _doc(rel: str) -> textio.TextDoc:
    return textio.read_text(config.MATTER(rel))


def test_al_eos_line_count_and_attributes():
    d = _doc("mat_Al-1.0/AL_eos")
    expect_eq(d.n_lines, 2495, "AL_eos 行数")
    expect_eq(d.encoding, "utf-8")
    expect_eq(d.newline_style, "lf")
    expect(d.has_trailing_newline is True, "有尾换行")
    expect_eq(d.blank_line_indices, [], "payload 区不应有空行")


def test_mixed_newline_file_has_no_stray_cr():
    """实测的 3 个混合换行文件之一：CH/CHSi10_eos.IN。

    通用换行切分后，任何行内都不应残留 ``\\r``。
    """
    d = _doc("CH/CHSi10_eos.IN")
    expect_eq(d.newline_style, "mixed", "该文件确为混合换行")
    expect_eq(d.n_lines, 1171)
    stray = [i for i, ln in enumerate(d.lines) if "\r" in ln]
    expect_eq(stray, [], "不应有任何行残留 \\r")


def test_blank_lines_are_recorded_not_dropped():
    """实测：224 个文件含空行。纪律是**计数登记**，不能静默丢弃。

    ``mat_Gd/Gd100ZEFF`` 的空行落在尾部（index 396 / 共 397 行），
    ``Readme.txt`` 则确有空行位于中间 —— 两种都要能定位。
    """
    d = _doc("mat_Gd/Gd100ZEFF")
    expect_eq(d.n_lines, 397)
    expect_eq(len(d.blank_line_indices), 1, "应记录 1 个空行")
    idx = d.blank_line_indices[0]
    expect(idx > 0, f"空行不应落在第 0 行（表头），实测 idx={idx}")
    expect(d.lines[idx].strip() == "", "被记录的那行确实为空")

    r = _doc("Readme.txt")
    interior = [i for i in r.blank_line_indices if 0 < i < r.n_lines - 1]
    expect(len(interior) >= 1, f"Readme.txt 应有**内部**空行，实测 {r.blank_line_indices}")


def test_no_trailing_newline_last_line_still_usable():
    """实测：291 个文件无结尾换行 —— 末行仍必须参与解析。"""
    d = _doc("Readme.txt")
    expect(d.has_trailing_newline is False, "Readme.txt 无结尾换行")
    expect_eq(d.n_lines, 14, "行数应仍为 14（末行不被吞掉）")
    expect(d.lines[-1].strip() != "", "末行不应为空")

    log = _doc("ColdOpacity/20170117.case.log")
    expect(log.has_trailing_newline is False, "该 .log 同样无结尾换行")
    expect_eq(log.n_lines, 74)


def test_bom_is_stripped_from_first_line():
    """实测：26 个文件带 BOM —— line[0] 不应残留 \\ufeff。"""
    d = _doc("ColdOpacity/20170117.case.log")
    expect(d.has_bom is True, "该文件确实带 BOM")
    expect_eq(d.encoding, "utf-8-sig", "有 BOM 时应标 utf-8-sig")
    expect_eq(d.lines[0].count(config.BOM), 0, "首行不应残留 BOM 字符")
    whole = "".join(d.lines)
    expect_eq(whole.count(config.BOM), 0, "全文不应残留 BOM 字符")


def test_readme_gb18030_and_blank_lines():
    d = _doc("Readme.txt")
    expect_eq(d.encoding, "gb18030", "Readme.txt 必须走 gb18030")
    expect_eq(len(d.blank_line_indices), 3, "实测有 3 个空行")
    expect("修改规则" in d.text, "中文应可读")


def test_packed_label_line_is_preserved_verbatim():
    """实测陷阱：``.27100000E+04PLANCK M`` —— id 与标签紧贴，无分隔符。

    这类行必须**原样保留**（供后续 L2 正则 + 标签正则分别处理）。
    """
    d = _doc("mat_Au-1.0/AU_SIMPLE_PLANCK_MG")
    expect_eq(d.n_lines, 96)
    first = d.lines[0]
    expect("PLANCK M" in first, f"行1 含标签 PLANCK M，实测 {first!r}")
    expect(".27100000E+04PLANCK" in first, f"id 与标签紧贴，实测 {first!r}")


def test_grayopacity_label_also_packed_with_magic():
    """LEDCOP 拆分件：`` 0.1234567E+000PLANCK 1`` —— 魔数与标签同样紧贴。"""
    d = _doc("ATOMIC/Al.GrayOpacity_PLANCK")
    expect_eq(d.n_lines, 894)
    first = d.lines[0]
    expect("0.1234567E+000PLANCK" in first, f"魔数与标签紧贴，实测 {first!r}")


def test_iter_lines_matches_read_text():
    """流式读取必须与整读给出一致的行序列（大文件路径的正确性保证）。"""
    rel = "mat_Al-1.0/AL_eos"
    d = _doc(rel)
    streamed = list(textio.iter_lines(config.MATTER(rel)))
    expect_eq(len(streamed), d.n_lines, "流式行数应与整读一致")
    diff = [i for i, (a, b) in enumerate(zip(streamed, d.lines)) if a != b]
    expect_eq(diff[:5], [], "前 5 个不一致的行号应为空")


def test_is_blank_helper():
    expect(textio.is_blank("") is True)
    expect(textio.is_blank("   \t  ") is True)
    expect(textio.is_blank(" 0.0 ") is False)


if __name__ == "__main__":
    raise SystemExit(main(globals()))
