"""Phase 1 —— 字节层分类测试。

实测基准（matter++ 全树扫描）
* 26 个文件带 UTF-8 BOM（全部是 .log/.txt/.md/.xml，**数据表 0 个**）
* 12 个文件非 UTF-8，其中 matter++/Readme.txt 是 **GB18030 中文**
* 1 个文件含 NUL（XrayMassCoef/.../Thumbs.db）
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
from eosop_pro.core import byteclass as bcl
from eosop_pro.core.errors import BinarySuspect


def test_readme_txt_is_gb18030_not_utf8():
    """matter++/Readme.txt 是 GB18030 中文；utf-8 解码必然失败。

    这是编码链必须包含 gb18030 的**唯一实证理由**。
    """
    raw = config.MATTER_README.read_bytes()
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        pass
    else:
        raise AssertionError("前提不成立：Readme.txt 竟然能被 utf-8 解码")
    bc = bcl.classify_file(config.MATTER_README)
    expect_eq(bc.kind, "text", "Readme.txt 应判为文本")
    expect_eq(bc.encoding, "gb18030", "命中编码应为 gb18030")
    expect(bc.is_text, "is_text 应为 True")


def test_readme_txt_chinese_is_readable_after_gb18030():
    from eosop_pro.core import textio

    doc = textio.read_text(config.MATTER_README)
    expect_eq(doc.encoding, "gb18030")
    expect(
        "material.base的修改规则" in doc.text,
        "首个正文行应为可读中文（证明编码链生效）",
    )
    expect("如果文件名和路径中有" in doc.text, "格式路由规则原文应可读")


def test_thumbs_db_is_binary_with_nul():
    """含 NUL 字节 → 一票否决文本路径。"""
    import os

    target = None
    for root, _dirs, files in os.walk(config.MATTER_DIR / "XrayMassCoef"):
        for f in files:
            if f.lower() == "thumbs.db":
                target = os.path.join(root, f)
    expect(target is not None, "应能找到 Thumbs.db")
    bc = bcl.classify_file(target)
    expect_eq(bc.kind, "binary", "Thumbs.db 应判为二进制")
    expect(bc.has_nul, "应检出 NUL 字节")
    thrown = False
    try:
        bcl.classify_file(target, strict=True)
    except BinarySuspect:
        thrown = True
    expect(thrown, "strict=True 时应对二进制文件抛 BinarySuspect")


def test_multi_family_files_are_lf_only():
    """实测：MULTI 家族（mat_*）文件是 **LF-only**；且无 BOM 时应标 utf-8。

    全树统计：LF-only 197 个 / CRLF-only 997 个，且换行风格与家族相关 ——
    ``mat_*``（MULTI/SESAME 导出）为 LF，而 ``hyades/*`` 为 CRLF。
    """
    bc = bcl.classify_file(config.MATTER("mat_Al-1.0/AL_eos"))
    expect_eq(bc.kind, "text")
    expect_eq(bc.newline, "lf", f"AL_eos 为 LF，实测 {bc.newline}")
    expect_eq(bc.has_nul, False)
    expect(bc.printable_ratio == 1.0, f"printable={bc.printable_ratio}")
    expect_eq(bc.encoding, "utf-8", "无 BOM 的纯 ASCII 应标 utf-8（而非 utf-8-sig）")


def test_hyades_family_files_are_crlf():
    """对照：``hyades/*`` 是 CRLF —— 换行风格与家族相关，可作辅助诊断信号。"""
    for rel in ("hyades/sesame/eos_41.dat", "hyades/qeos/qeos_52.dat"):
        bc = bcl.classify_file(config.MATTER(rel))
        expect_eq(bc.newline, "crlf", f"{rel} 应为 CRLF，实测 {bc.newline}")


def test_classify_bytes_detects_bom():
    bc = bcl.classify_bytes(b"\xef\xbb\xbfhello 123\n")
    expect(bc.has_bom, "应检出 UTF-8 BOM")
    expect_eq(bc.encoding, "utf-8-sig", "编码链首段应命中 utf-8-sig")


def test_classify_bytes_nul_wins_over_text():
    """即使大部分是可打印文本，只要含 NUL 就判二进制。"""
    bc = bcl.classify_bytes(b"hello world\x00more text\n")
    expect_eq(bc.kind, "binary", "NUL 出现即判二进制")
    expect(bc.nul_ratio > 0, f"nul_ratio={bc.nul_ratio}")


def test_mixed_newline_detected():
    """实测存在 3 个混合换行文件（CH/CHSi10_eos.IN 等）。"""
    bc = bcl.classify_file(config.MATTER("CH/CHSi10_eos.IN"))
    expect_eq(bc.newline, "mixed", f"应判为 mixed，实测 {bc.newline}")


def test_newline_style_helper():
    expect_eq(bcl._newline_style(b"a\r\nb\r\n"), "crlf")
    expect_eq(bcl._newline_style(b"a\nb\n"), "lf")
    expect_eq(bcl._newline_style(b"a\rb\r"), "cr")
    expect_eq(bcl._newline_style(b"a\r\nb\n"), "mixed")
    expect_eq(bcl._newline_style(b"abc"), "none")


def test_describe_is_informative():
    bc = bcl.classify_file(config.MATTER("mat_Al-1.0/AL_eos"))
    d = bc.describe()
    for token in ("kind=text", "encoding=", "newline=lf"):
        expect(token in d, f"describe() 应含 {token}，实测 {d}")


def test_encoding_chain_order_depends_on_bom():
    """有 BOM → 先 utf-8-sig；无 BOM → 先 utf-8（否则标签会误导）。"""
    with_bom = bcl.encoding_chain(b"\xef\xbb\xbfhello")
    expect_eq(with_bom[0], "utf-8-sig")
    without = bcl.encoding_chain(b"hello")
    expect_eq(without[0], "utf-8", "无 BOM 时应先试 utf-8")
    expect("gb18030" in without, "gb18030 必须在链中（Readme.txt 依赖它）")
    expect_eq(without[-1], "latin-1", "latin-1 收尾保证永不失败")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
