"""``eosop_pro.docsrc`` 测试 —— 文档抽取。

关键断言（都必须有**真实文件**作证据，不用伪造数据）
----------------------------------------------------
* **OOXML**：``doc/MULTI使用的SESAME数据文件格式.docx`` 抽出后必须含
  ``Inverted EOS`` / ``MPQeos`` / ``Zeff`` / ``keV`` 等规格关键字
* **OLE2**：``doc/Hyades 数据格式说明.doc`` 与 ``doc/Atomic(LEDCOP)说明.doc``
  必须抽出可读中文/英文正文（双对齐 + BMP 码位判定的正确性证据）
* **无扩展名**：``doc/multi1d7.6/manual`` 必须被认作 text 并抽出
  ``hydro_state`` / ``ts`` —— 这是 F1 自变量定义的第一手来源
* **xlsx**：``matter++/PowerLaws/opacity.xlsx`` 的共享字符串必须被解析成文本
  （而不是留下 ``t="s"`` 的整数索引）
* **「文档 vs 数据」闸门**：``matter++/ATOMIC/Al.txt``（13.5 MB 数值表）
  必须判为数据；``matter++/Readme.txt``（分派规则）必须判为文档
* **健壮性**：空文件 / 垃圾字节 → 记 warning，**绝不抛异常**
"""

import tempfile
from pathlib import Path

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
from _runner import expect, expect_eq, expect_in, main

from eosop_pro import config, docsrc


# ── 路径固定（config.MATTER 会断言存在，避免静默跳过） ───────────────
DOCX_SESAME = config.MULTI_HOME / "doc" / "MULTI使用的SESAME数据文件格式.docx"
DOC_HYADES = config.MULTI_HOME / "doc" / "Hyades 数据格式说明.doc"
DOC_LEDCOP = config.MULTI_HOME / "doc" / "Atomic(LEDCOP)说明.doc"
DOCX_LEDCOP = config.MATTER("ATOMIC/Atomic(LEDCOP)不透明度格式说明.docx")
MANUAL = config.MULTI_HOME / "doc" / "multi1d7.6" / "manual"
XLSX_POWERLAW = config.MATTER("PowerLaws/opacity.xlsx")
XMIND = config.MULTI_HOME / "doc" / "Radiation Hydrodynamics.xmind"
README_MATTER = config.MATTER("Readme.txt")
NUMERIC_TXT = config.MATTER("ATOMIC/Al.txt")


# ══════════════════════════════════════════════════════════════
# 文本卫生
# ══════════════════════════════════════════════════════════════
def test_tidy_normalises_newlines_and_control_chars():
    raw = "a\r\nb\rc\x0b\x0c\x07d\x00e   f\n\n\n\ng"
    t = docsrc.tidy(raw)
    expect("\r" not in t, "CR 必须被消除")
    expect("\x00" not in t, "NUL 必须被消除")
    expect("\x07" not in t, "BEL 必须被消除")
    expect_eq(t.count("\n\n\n"), 0, "连续空行应被压到 2 行以内")


def test_unsafe_name_regex_strips_punctuation():
    p = Path("/x/Atomic(LEDCOP)说明.docx")
    r = docsrc.DocText(src=p, relpath="x", kind="ooxml-word", sha256="ab" * 32)
    name = r.out_name()
    expect("(" not in name and ")" not in name, f"括号须被替换: {name}")
    expect("说明" in name, f"中文应保留: {name}")
    expect(name.endswith(".txt"))


def test_out_name_is_deterministic_and_sha_tagged():
    p = Path("/x/Foo.docx")
    a = docsrc.DocText(src=p, relpath="x", kind="ooxml-word", sha256="0123abcd" + "0" * 56)
    b = docsrc.DocText(src=p, relpath="x", kind="ooxml-word", sha256="0123abcd" + "0" * 56)
    expect_eq(a.out_name(), b.out_name())
    expect_in("0123abcd", a.out_name())


# ══════════════════════════════════════════════════════════════
# OOXML
# ══════════════════════════════════════════════════════════════
def test_docx_sesame_extracts_format_spec_keywords():
    """F3（MULTI/SESAME）规格 docx —— 这是解析器 expected 计数的第一手依据。"""
    r = docsrc.extract(DOCX_SESAME)
    expect(r.ok, f"抽取失败: {r.warnings}")
    expect(r.kind == "ooxml-word", r.kind)
    for kw in ("Inverted EOS", "MPQeos", "Zeff", "keV", "Mbar", "material.base"):
        expect_in(kw, r.text,
                  f"SESAME 规格 docx 应含关键字 {kw!r}；实抽 {r.n_chars} 字符")
    # 4+2*nr+ne+2*nr*ne 的计数公式原文
    expect_in("4+2*nr+ne+2*nr*ne", r.text.replace(" ", ""),
              "应含 F1 计数公式 4+2*nr+ne+2*nr*ne")
    expect(not r.warnings, f"不应有 warning: {r.warnings}")


def test_docx_ledcop_in_matter_extracts_atomic_spec():
    """F5（LEDCOP）规格 docx（matter++ 内副本，内容比 doc/ 里的 .doc 更全）。"""
    r = docsrc.extract(DOCX_LEDCOP)
    expect(r.ok, f"抽取失败: {r.warnings}")
    expect(r.n_chars > 5000, f"应抽出较多正文，实抽 {r.n_chars}")
    low = r.text.lower()
    expect("ledcop" in low, "应含 LEDCOP")
    expect("planck" in low or "rosseland" in low, "应含 Planck/Rosseland")


def test_pptx_slide_extraction():
    r = docsrc.extract(config.MULTI_HOME / "doc" / "Multi1D++ and GUI4Multi1D简介.pptx")
    expect(r.ok, f"抽取失败: {r.warnings}")
    expect_eq(r.kind, "ooxml-slide")
    expect(r.meta.get("n_slides", 0) > 5, f"幻灯片数应 >5，实测 {r.meta}")


def test_xlsx_shared_strings_are_resolved():
    """★ 断言共享字符串被真正解析 —— 否则单元格会退化成整数索引。"""
    r = docsrc.extract(XLSX_POWERLAW)
    expect(r.ok, f"抽取失败: {r.warnings}")
    expect_eq(r.kind, "ooxml-sheet")
    expect(r.meta.get("n_shared_strings", 0) > 0, f"sst 数应 >0: {r.meta}")
    expect(r.meta.get("n_cells", 0) > 50, f"单元格数应 >50: {r.meta}")
    # 至少有一个单元格的值是**文本**而不是纯数字（证明 sst 命中）
    vals = [ln.split("\t", 1)[1] for ln in r.text.splitlines() if "\t" in ln]
    expect(any(not v.replace(".", "").replace("-", "").replace("+", "")
               .replace("E", "").replace("e", "").isdigit() for v in vals),
           "应至少有一个非数值单元格（共享字符串）")


# ══════════════════════════════════════════════════════════════
# OLE2（.doc / .xls）
# ══════════════════════════════════════════════════════════════
def test_doc_hyades_ole2_text_extraction():
    """★ 这一条守住「双对齐 + BMP 码位」两个正确性细节。"""
    r = docsrc.extract(DOC_HYADES)
    expect(r.ok, f"抽取失败: {r.warnings}")
    expect_eq(r.kind, "ole2-word")
    expect(r.n_chars > 1000, f"应抽出可观正文，实抽 {r.n_chars}")
    expect(r.method.startswith("ole2-scan"), r.method)
    # 中文必须被正确解出（证明 BMP 码位判定生效，而不是被当成噪声丢弃）
    han = sum(1 for ch in r.text if "\u4e00" <= ch <= "\u9fff")
    expect(han > 200, f"中文字符数应 >200，实测 {han}")


def test_doc_ledcop_ole2_text_extraction():
    r = docsrc.extract(DOC_LEDCOP)
    expect(r.ok, f"抽取失败: {r.warnings}")
    han = sum(1 for ch in r.text if "\u4e00" <= ch <= "\u9fff")
    expect(han > 200, f"中文字符数应 >200，实测 {han}")


def test_utf16_runs_reject_binary_noise():
    """全 0 字节 / 全 0xFF 的缓冲不应产出文本游程。"""
    expect_eq(docsrc._runs_utf16(b"\x00" * 400, align=0), [])
    expect_eq(docsrc._runs_utf16(b"\xff" * 400, align=0), [])
    quiet = "".join(chr(c) for c in (0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48))
    blob = quiet.encode("utf-16-le")
    got = docsrc._runs_utf16(blob, align=0)
    expect(got and got[0] == quiet, f"应解出 {quiet!r}，实测 {got}")


def test_doc_alignment_variants_both_tried():
    """奇偏移下的文本也必须能抽到（证明 align=1 分支存在且生效）。"""
    text = "AaBbCcDdEeFfGgHhIiJjKkLl"
    data = b"\x00" + text.encode("utf-16-le")
    got = docsrc._runs_utf16(data, align=1)
    expect(any(text in g for g in got), f"align=1 应解出正文，实测 {got}")


def test_xls_ole2_sheet():
    r = docsrc.extract(config.MULTI_HOME / "doc" / "solution of unsymmetry" / "unsymmetry.xls")
    expect(r.ok, f"抽取失败: {r.warnings}")
    expect_eq(r.kind, "ole2-sheet")


# ══════════════════════════════════════════════════════════════
# 无扩展名 / xmind / pdf
# ══════════════════════════════════════════════════════════════
def test_extensionless_manual_is_recognised_as_text():
    """★ ``ts`` 状态量定义就在这个无扩展名文件里 —— 只认扩展名会全体漏掉。"""
    expect_eq(docsrc._kind_of(MANUAL), "text")
    r = docsrc.extract(MANUAL)
    expect(r.ok, f"抽取失败: {r.warnings}")
    expect_in("hydro_state", r.text)
    expect_in("ts", r.text)
    # 自变量定义：密度 + 电子/离子比能
    low = r.text.lower()
    expect("specific electron" in low or "electron and ion energies" in low,
           "应含电子/离子比能的定义")


def test_extensionless_non_listed_name_is_unknown():
    expect_eq(docsrc._kind_of(Path("/x/whatever")), "unknown")


def test_xmind_titles_extracted():
    r = docsrc.extract(XMIND)
    expect(r.ok, f"抽取失败: {r.warnings}")
    expect_eq(r.kind, "xmind")
    expect(r.n_lines > 5, f"应抽出多条主题，实测 {r.n_lines} 行")


def test_pdf_feos_documentation_extracted():
    r = docsrc.extract(config.MULTI_HOME / "doc" / "FEOS"
                       / "FEOS-Package-Documentation2016.pdf")
    expect(r.ok, f"抽取失败: {r.warnings}")
    expect_eq(r.kind, "pdf")
    expect(r.meta.get("n_decoded", 0) > 0, f"应有 zlib 解出的流: {r.meta}")
    expect(r.n_chars > 10000, f"应抽出可观正文，实抽 {r.n_chars}")


def test_pdf_without_text_layer_degrades_gracefully():
    """没有文本层的 PDF 必须记 warning 而不是抛异常、也不是编内容。"""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "blank.pdf"
        p.write_bytes(b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n")
        r = docsrc.extract(p)
        expect(not r.ok, "不应抽出文本")
        expect(any("no extractable text layer" in w for w in r.warnings),
               f"应记文本层缺失 warning，实测 {r.warnings}")


# ══════════════════════════════════════════════════════════════
# 「文档 vs 数据」闸门
# ══════════════════════════════════════════════════════════════
def test_numeric_gate_flags_data_table():
    is_data, ratio = docsrc.looks_like_data(NUMERIC_TXT)
    expect(is_data, f"ATOMIC/Al.txt 应判为数值数据，实测 ratio={ratio}")
    expect(ratio > 0.9, f"payload 占比应 >0.9，实测 {ratio}")


def test_numeric_gate_passes_readme():
    is_data, ratio = docsrc.looks_like_data(README_MATTER)
    expect(not is_data, f"matter++/Readme.txt 应判为文档，实测 ratio={ratio}")


def test_scan_excludes_giant_numeric_txt():
    paths = [p.name for p in docsrc.scan_documents(config.MATTER_DIR)]
    for bad in ("Al.txt", "C.txt", "CH2.txt", "Fe.txt"):
        expect(bad not in paths, f"{bad} 是数值表，不应出现在文档清单里")
    expect("Readme.txt" in paths, "matter++/Readme.txt 应出现在文档清单里")


def test_scan_default_roots_cover_doc_and_matter():
    names = {p.name for p in docsrc.scan_documents()}
    for must in ("Structure_of_ASCII_data_files.txt", "SNOP.MANUAL",
                 "Readme.txt", "manual"):
        expect_in(must, names, f"默认扫描应含 {must}")


def test_scan_skips_office_lock_files():
    names = {p.name for p in docsrc.scan_documents()}
    expect(not any(n.startswith("~$") for n in names), "不应含 ~$ 锁文件")


def test_allowlist_file_passes_numeric_gate():
    """``Structure_of_ASCII_data_files.txt`` 内容几乎全数字，但确是规格说明。"""
    names = {p.name for p in docsrc.scan_documents()}
    expect_in("Structure_of_ASCII_data_files.txt", names)
    r = docsrc.extract(config.MULTI_HOME / "doc" / "Structure_of_ASCII_data_files.txt")
    expect(r.ok, f"应抽出内容: {r.warnings}")
    expect(r.n_chars > 20, f"实抽 {r.n_chars}")


# ══════════════════════════════════════════════════════════════
# 健壮性 + 落盘
# ══════════════════════════════════════════════════════════════
def test_empty_and_garbage_inputs_warn_but_never_raise():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "empty.docx").write_bytes(b"")
        (td / "garbage.docx").write_bytes(b"not a zip at all" * 10)
        (td / "garbage.pdf").write_bytes(b"%PDF-1.4\n" + bytes(range(256)) * 4)
        (td / "weird.xyz").write_bytes(b"hello")
        for name in ("empty.docx", "garbage.docx", "garbage.pdf", "weird.xyz"):
            r = docsrc.extract(td / name)
            expect(r.n_chars >= 0, "不应抛异常")
            expect(bool(r.warnings), f"{name} 应至少有一条 warning")
        expect(any("BadZipFile" in w for w in docsrc.extract(td / "garbage.docx").warnings),
               "损坏的 zip 应报 BadZipFile")


def test_extract_all_writes_texts_and_manifest():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        out = td / "extracted"
        res = docsrc.extract_all(config.MULTI_HOME / "doc" / "multi1d7.6", outdir=out)
        expect(len(res) >= 4, f"应抽到 ≥4 份（README/manual/history/examples），实测 {len(res)}")
        expect((out / "MANIFEST.md").exists(), "应写 MANIFEST.md")
        expect((out / "manifest.json").exists(), "应写 manifest.json")
        txts = list(out.glob("*.txt"))
        expect(len(txts) >= 4, f"应落盘 ≥4 份文本，实测 {len(txts)}")
        for p in txts:
            expect(p.stat().st_size > 100, f"{p.name} 体积过小")
            # 生成的文本必须用 LF，避免 Windows 上二次污染
            expect(b"\r\n" not in p.read_bytes(), f"{p.name} 不应含 CRLF")


def test_manifest_json_is_parseable_and_counts_match():
    import json

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "ex"
        res = docsrc.extract_all(config.MULTI_HOME / "doc" / "multi1d7.6", outdir=out)
        data = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        expect_eq(data["n_files"], len(res))
        expect_eq(data["n_ok"], sum(1 for r in res if r.ok))
        expect(len(data["documents"]) == len(res))


def test_relpath_is_relative_to_known_root():
    r = docsrc.extract(README_MATTER)
    expect(r.relpath.startswith("matter++/") or r.relpath.startswith("Multi1D++"),
           f"relpath 应为相对路径，实测 {r.relpath}")
    expect(len(r.sha256) == 64, "sha256 应为 64 位十六进制")


def test_describe_and_to_row_shapes():
    r = docsrc.extract(README_MATTER)
    expect("OK" in r.describe() or "EMPTY" in r.describe())
    row = r.to_row()
    for k in ("relpath", "kind", "method", "size_bytes", "n_chars",
              "n_lines", "sha256", "out_name", "warnings"):
        expect_in(k, row)


if __name__ == "__main__":
    raise SystemExit(main(globals()))
