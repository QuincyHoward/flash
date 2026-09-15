"""文档抽取 —— 把 ``doc`` / ``docx`` / ``pptx`` / ``xlsx`` / ``xls`` / ``pdf``
/ ``xmind`` / 纯文本转成可审计、可引用的纯文本。

为什么需要它
------------
"每种后缀是什么数据、网格点怎么排、单位是什么" 这三个问题的**第一手证据**
都躺在 ``Multi1D++Portable20241128/doc/`` 与 ``matter++/`` 下的说明文件里：

===========================================  ==================================
文件                                          它定义了什么
===========================================  ==================================
``doc/MULTI使用的SESAME数据文件格式.docx``     F3（SESAME / MULTI 表）权威定义
``doc/Hyades 数据格式说明.doc``                F3（Hyades 侧）权威定义
``doc/Atomic(LEDCOP)说明.doc``                 F5（LEDCOP 原子数据）权威定义
``matter++/ATOMIC/Atomic(LEDCOP)...docx``      同上（matter++ 内副本）
``doc/FEOS/*.pdf``                             F4（FEOS / MPQeos）权威定义
``matter++/Readme.txt``                        **默认分派规则**（4x15 SESAME）
``doc/multi1d7.6/manual``                      ``ts`` 状态量 = (rho, e_e, e_i)
``doc/SNOP.MANUAL``                            F2 来源程序的多群约定
===========================================  ==================================

这些都不是纯文本，必须先抽成文本才能进审计、进文档、被引用。
抽取结果统一落盘 ``docs/extracted/``，每份都记录**来源相对路径 + 字节数 +
sha256 + 抽取方式**，做到结论可溯源。

抽取策略（零第三方依赖）
------------------------
==============  ================================================================
容器             做法
==============  ================================================================
``.docx/.pptx``  ``zipfile`` → ``word/document.xml`` / ``ppt/slides/*.xml``，
                 ``</w:p>`` 断段、``<w:tab/>``→TAB、``<w:br/>``→换行，去标签
``.xlsx``        ``zipfile`` → ``xl/sharedStrings.xml`` + ``worksheets/*.xml``
``.xmind``       ``zipfile`` → ``content.json``，递归取 ``topic.title``
``.doc/.xls``    OLE2 二进制：**双对齐**扫描 UTF-16LE / cp1252 可打印游程
``.pdf``         ``zlib`` 解 ``stream`` → ``BT``/``ET`` 段里的 ``Tj`` / ``TJ``
纯文本           直接走 :func:`eosop_pro.core.textio.read_text` 的编码链
==============  ================================================================

★ 三个关键正确性细节
--------------------
1. ``.doc`` 的文本区**不一定 2 字节对齐** —— 必须 0/1 两种对齐都扫，取文本更多
   的一侧；只看一种对齐会丢掉整段正文。
2. ``.doc`` 里的中文是 BMP 码位（``0x4E00-0x9FFF``），Little-Endian 下低字节
   可能非零，所以**不能**用 "奇数字节都是 0" 这种 ASCII-only 假设来判定；
   必须先把每 2 字节合成一个码位再分类。
3. PDF 的 ``Tj`` 字符串受 ``\\(`` ``\\)`` ``\\\\`` 转义影响，且 CID 字体的码位
   **不是** Unicode。抽不出来时如实记 ``warning``，**绝不编造内容** ——
   这正是本项目"证据优先、不许杜撰"纪律在工具层的落点。
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path

from . import config
from .core import textio

__all__ = [
    "DocText",
    "KIND_BY_EXT",
    "DOC_EXTS",
    "extract",
    "extract_all",
    "scan_documents",
    "write_extracted",
    "write_manifest",
]

#: 扩展名 → 容器类型
KIND_BY_EXT: dict[str, str] = {
    ".docx": "ooxml-word",
    ".docm": "ooxml-word",
    ".pptx": "ooxml-slide",
    ".xlsx": "ooxml-sheet",
    ".xlsm": "ooxml-sheet",
    ".xmind": "xmind",
    ".doc": "ole2-word",
    ".xls": "ole2-sheet",
    ".pdf": "pdf",
    ".txt": "text",
    ".md": "text",
    ".ini": "text",
    ".manual": "text",
}

#: 抽取器认得的全部扩展名（小写）
DOC_EXTS: tuple[str, ...] = tuple(sorted(KIND_BY_EXT))

#: 抽取结果文件名里要冲掉的字符
_UNSAFE = re.compile(r"[^0-9A-Za-z._\u4e00-\u9fff-]+")
#: 去重用的连续空白
_WS_RUN = re.compile(r"[ \t]{2,}")
#: 连续空行
_BLANK_RUN = re.compile(r"\n{3,}")


# ══════════════════════════════════════════════════════════════
# 结果容器
# ══════════════════════════════════════════════════════════════
@dataclass
class DocText:
    """一份文档的抽取结果。"""

    src: Path
    relpath: str
    kind: str
    text: str = ""
    method: str = ""
    size_bytes: int = 0
    sha256: str = ""
    warnings: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    @property
    def n_chars(self) -> int:
        return len(self.text)

    @property
    def n_lines(self) -> int:
        return self.text.count("\n") + 1 if self.text else 0

    @property
    def ok(self) -> bool:
        return bool(self.text.strip())

    def out_name(self) -> str:
        """抽取文本的落盘文件名（**保留原名主干**，便于与源文件对照）。"""
        stem = _UNSAFE.sub("_", self.src.stem).strip("_") or "doc"
        return f"{stem}__{self.kind}__{self.sha256[:8]}.txt"

    def head(self, n: int = 400) -> str:
        t = self.text.strip()
        return t if len(t) <= n else t[:n] + " ..."

    def describe(self) -> str:
        flag = "OK " if self.ok else "EMPTY"
        return (f"[{flag}] {self.kind:<11} {self.n_chars:>8} chars "
                f"{self.n_lines:>6} lines  {self.relpath}")

    def to_row(self) -> dict:
        return {
            "relpath": self.relpath,
            "kind": self.kind,
            "method": self.method,
            "size_bytes": self.size_bytes,
            "n_chars": self.n_chars,
            "n_lines": self.n_lines,
            "sha256": self.sha256[:16],
            "out_name": self.out_name() if self.ok else "",
            "warnings": " ;; ".join(self.warnings),
        }


# ══════════════════════════════════════════════════════════════
# 文本卫生
# ══════════════════════════════════════════════════════════════
def tidy(text: str) -> str:
    """统一换行、压缩空白游程、去尾部空行。**不改动可见字符**。"""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = t.replace("\x0b", "\n").replace("\x0c", "\n").replace("\x07", "\t")
    t = "".join(ch if (ch == "\n" or ch == "\t" or ch >= " ") else " " for ch in t)
    t = "\n".join(_WS_RUN.sub("  ", ln).rstrip() for ln in t.split("\n"))
    t = _BLANK_RUN.sub("\n\n", t)
    return t.strip("\n")


# ══════════════════════════════════════════════════════════════
# OOXML（docx / pptx / xlsx）
# ══════════════════════════════════════════════════════════════
_TAG = re.compile(r"<[^>]+>")
_XML_COMMENT = re.compile(r"<!--.*?-->", re.S)


def _xml_text(chunk: str, *, para_tag: str) -> str:
    """把一段 OOXML 片段转成纯文本（段落用 ``para_tag`` 断行）。"""
    s = _XML_COMMENT.sub("", chunk)
    s = re.sub(r"<" + para_tag + r"\b[^>]*>", "\n", s)
    s = re.sub(r"</" + para_tag + r">", "\n", s)
    s = re.sub(r"<(?:w|a):tab\b[^>]*/>", "\t", s)
    s = re.sub(r"<w:br\b[^>]*/>", "\n", s)
    s = re.sub(r"<a:br\b[^>]*/>", "\n", s)
    s = re.sub(r"</(?:w:tr|a:tr)>", "\n", s)
    s = re.sub(r"</(?:w:tc|a:tc)>", "\t", s)
    s = _TAG.sub("", s)
    return html.unescape(s)


def _zip_read(zf: zipfile.ZipFile, name: str) -> str | None:
    try:
        raw = zf.read(name)
    except KeyError:
        return None
    for enc in ("utf-8", "utf-16", "gb18030", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def _extract_ooxml_word(zf: zipfile.ZipFile, r: DocText) -> None:
    parts = sorted(n for n in zf.namelist()
                   if re.fullmatch(r"word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml", n))
    if not parts:
        r.warnings.append("no word/document.xml in package")
        return
    buf = []
    for name in parts:
        xml = _zip_read(zf, name)
        if not xml:
            continue
        buf.append(f"----- [{name}] -----\n" + _xml_text(xml, para_tag="w:p"))
    r.text = tidy("\n".join(buf))
    r.method = f"zipfile+regex({len(parts)} part)"


def _extract_ooxml_slide(zf: zipfile.ZipFile, r: DocText) -> None:
    slides = sorted((n for n in zf.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                    key=lambda s: int(re.search(r"(\d+)", s.rsplit("/", 1)[1]).group(1)))
    buf = []
    for name in slides:
        xml = _zip_read(zf, name)
        if not xml:
            continue
        buf.append(f"----- [{name}] -----\n" + _xml_text(xml, para_tag="a:p"))
    if not slides:
        r.warnings.append("no ppt/slides/slide*.xml in package")
    r.text = tidy("\n".join(buf))
    r.method = f"zipfile+regex({len(slides)} slide)"
    r.meta["n_slides"] = len(slides)


def _extract_ooxml_sheet(zf: zipfile.ZipFile, r: DocText) -> None:
    """xlsx：共享字符串 + 每张表的单元格值（A1 坐标 + 文本）。"""
    shared: list[str] = []
    sx = _zip_read(zf, "xl/sharedStrings.xml")
    if sx:
        for si in re.findall(r"<si>(.*?)</si>", sx, re.S):
            shared.append(html.unescape(_TAG.sub("", si)))
    sheets = sorted(n for n in zf.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
    buf = []
    n_cells = 0
    for name in sheets:
        xml = _zip_read(zf, name)
        if not xml:
            continue
        buf.append(f"----- [{name}] -----")
        for cell in re.finditer(
                r'<c\s+r="([A-Z]+\d+)"([^>]*)>(.*?)</c>', xml, re.S):
            ref, attrs, body = cell.group(1), cell.group(2), cell.group(3)
            vm = re.search(r"<v>(.*?)</v>", body, re.S)
            if not vm:
                continue
            val = html.unescape(vm.group(1))
            if 't="s"' in attrs:
                try:
                    val = shared[int(val)]
                except (ValueError, IndexError):
                    pass
            elif 't="str"' in attrs or 't="inlineStr"' in attrs:
                if not val.strip():
                    val = html.unescape(_TAG.sub("", body))
            buf.append(f"{ref}\t{val}")
            n_cells += 1
    if not sheets:
        r.warnings.append("no xl/worksheets/sheet*.xml in package")
    r.text = tidy("\n".join(buf))
    r.method = f"zipfile+xml({len(sheets)} sheet, {len(shared)} sst)"
    r.meta.update(n_sheets=len(sheets), n_shared_strings=len(shared), n_cells=n_cells)


def _extract_xmind(zf: zipfile.ZipFile, r: DocText) -> None:
    """xmind：新版 ``content.json`` 的 topic 树；老版 ``content.xml`` 的 ``<title>``。"""
    out: list[str] = []

    def walk_topic(t: dict, depth: int) -> None:
        title = (t.get("title") or "").strip()
        if title:
            out.append("  " * depth + "- " + title)
        for key in ("children", "notes"):
            sub = t.get(key)
            if isinstance(sub, dict):
                for lst in sub.values():
                    if isinstance(lst, list):
                        for c in lst:
                            if isinstance(c, dict):
                                walk_topic(c, depth + 1)
            elif isinstance(sub, list):
                for c in sub:
                    if isinstance(c, dict):
                        walk_topic(c, depth + 1)

    cj = _zip_read(zf, "content.json")
    if cj:
        try:
            data = json.loads(cj)
        except json.JSONDecodeError:
            data = None
        if data is not None:
            for sheet in (data if isinstance(data, list) else [data]):
                if isinstance(sheet, dict):
                    rt = sheet.get("rootTopic") or sheet.get("topic")
                    if isinstance(rt, dict):
                        walk_topic(rt, 0)
            r.method = "zipfile+json(content.json)"

    # ★ 老版 xmind 的标题是 ``<title>`` **子元素**，不是 ``title=`` 属性
    if not out:
        xml = _zip_read(zf, "content.xml")
        if xml:
            for tm in re.finditer(r"<(?:topic|sheet|title)[^>]*>\s*(?:<title>)?(.*?)"
                                  r"(?:</title>)?\s*</(?:topic|sheet|title)>",
                                  xml, re.S):
                t = html.unescape(_TAG.sub("", tm.group(1))).strip()
                if t:
                    out.append("- " + t)
            if not out:
                for tm in re.finditer(r"<title>(.*?)</title>", xml, re.S):
                    t = html.unescape(_TAG.sub("", tm.group(1))).strip()
                    if t:
                        out.append("- " + t)
            if out:
                r.method = "zipfile+regex(content.xml/<title>)"
    if not out:
        r.warnings.append("no topic titles found in xmind package")
    r.text = tidy("\n".join(out))


# ══════════════════════════════════════════════════════════════
# OLE2（Word 97 .doc / Excel .xls）
# ══════════════════════════════════════════════════════════════
#: 允许出现的 BMP 码位（ASCII 可打印 + 常见 CJK / 全角 / 标点）
def _is_text_cp(u: int) -> bool:
    if u in (9, 10, 13):
        return True
    if 0x20 <= u <= 0x7E:
        return True
    if 0x00A0 <= u <= 0x024F:      # 拉丁扩展
        return True
    if 0x2010 <= u <= 0x203B:      # 通用标点
        return True
    if 0x3000 <= u <= 0x303F:      # CJK 标点
        return True
    if 0x4E00 <= u <= 0x9FFF:      # CJK 统一表意
        return True
    if 0xFF00 <= u <= 0xFFEF:      # 全角
        return True
    if 0x2103 <= u <= 0x2122:      # ℃ ™ 等
        return True
    if 0x0370 <= u <= 0x03FF:      # 希腊字母（物理文档常见）
        return True
    if 0x0391 <= u <= 0x03C9:
        return True
    return False


def _runs_utf16(data: bytes, *, align: int, min_units: int = 5) -> list[str]:
    """按 2 字节单位扫描 UTF-16LE 文本游程（``align`` 为起始偏移）。"""
    out: list[str] = []
    cur: list[str] = []
    n = len(data) - 1
    i = align
    while i < n:
        u = data[i] | (data[i + 1] << 8)
        if _is_text_cp(u):
            cur.append(chr(u))
            i += 2
            continue
        if len(cur) >= min_units:
            out.append("".join(cur))
        cur = []
        i += 2
    if len(cur) >= min_units:
        out.append("".join(cur))
    return out


#: cp1252 / GB18030 单字节游程（英文 .doc 用 8 位存）
_RUN8 = re.compile(rb"[\x20-\x7e\xa0-\xff]{6,}")


def _runs_cp8(data: bytes) -> list[str]:
    out: list[str] = []
    for m in _RUN8.finditer(data):
        chunk = m.group(0)
        try:
            out.append(chunk.decode("gb18030"))
        except UnicodeDecodeError:
            out.append(chunk.decode("latin-1"))
    return out


def _extract_ole2(data: bytes, r: DocText, *, word: bool) -> None:
    """OLE2 抽取：双对齐 UTF-16LE + cp1252 游程，取文本更多的一侧。"""
    cands: dict[str, list[str]] = {
        "utf16le@0": _runs_utf16(data, align=0),
        "utf16le@1": _runs_utf16(data, align=1),
    }
    best_key, best_txt = "", ""
    for key, runs in cands.items():
        t = tidy("\n".join(runs))
        if len(t) > len(best_txt):
            best_key, best_txt = key, t
    r.method = f"ole2-scan({best_key})"

    # 8 位游程作为补充：只在 UTF-16 结果稀薄（多为纯英文文档）时启用
    if len(best_txt) < 400:
        t8 = tidy("\n".join(_runs_cp8(data)))
        if len(t8) > len(best_txt):
            best_txt, r.method = t8, "ole2-scan(cp8/gb18030)"

    if not best_txt.strip():
        r.warnings.append(
            "no decodable text run found; OLE2 stream may be compressed or "
            "the document may be a stub / embedded object"
        )
    r.text = best_txt
    r.meta["n_align_variants"] = len(cands)
    r.meta["is_word"] = bool(word)


# ══════════════════════════════════════════════════════════════
# PDF
# ══════════════════════════════════════════════════════════════
_PDF_STREAM = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.S)
_PDF_STR = re.compile(rb"\((?:\\.|[^\\()])*\)", re.S)
_PDF_HEX = re.compile(rb"<([0-9A-Fa-f\s]{4,})>", re.S)
_PDF_TITLE = re.compile(rb"/Title\s*\(([^)]{0,300})\)", re.S)


def _pdf_unescape(b: bytes) -> str:
    out: list[str] = []
    i = 0
    while i < len(b):
        c = b[i]
        if c == 0x5C and i + 1 < len(b):          # backslash
            n = b[i + 1]
            simple = {ord("n"): "\n", ord("r"): "\r", ord("t"): "\t",
                      ord("b"): "\b", ord("f"): "\f",
                      ord("("): "(", ord(")"): ")", ord("\\"): "\\"}
            if n in simple:
                out.append(simple[n])
                i += 2
                continue
            if 0x30 <= n <= 0x37:                   # up to 3 octal digits
                j = i + 1
                oct_s = b""
                while j < len(b) and len(oct_s) < 3 and 0x30 <= b[j] <= 0x37:
                    oct_s += b[j:j + 1]
                    j += 1
                out.append(chr(int(oct_s, 8)))
                i = j
                continue
            i += 2
            continue
        out.append(chr(c))
        i += 1
    return "".join(out)


def _decode_pdf_stream(blob: bytes) -> bytes | None:
    try:
        return zlib.decompress(blob)
    except zlib.error:
        pass
    for skip in (1, 2):
        try:
            return zlib.decompress(blob[skip:])
        except zlib.error:
            continue
    return None


def _extract_pdf(data: bytes, r: DocText) -> None:
    """zlib 解流 → 取 ``BT``/``ET`` 里的 ``Tj`` / ``TJ`` 字符串。"""
    tm = _PDF_TITLE.search(data)
    if tm:
        r.meta["pdf_title"] = _pdf_unescape(tm.group(1)).strip()

    n_stream = n_dec = 0
    bits: list[str] = []
    for sm in _PDF_STREAM.finditer(data):
        n_stream += 1
        blob = sm.group(1)
        dec = _decode_pdf_stream(blob)
        if dec is None:
            dec = blob if b"Tj" in blob or b"TJ" in blob else None
        else:
            n_dec += 1
        if dec is None:
            continue
        for seg in re.findall(rb"BT(.*?)ET", dec, re.S):
            for strm in _PDF_STR.finditer(seg):
                s = _pdf_unescape(strm.group(0)[1:-1])
                if s.strip():
                    bits.append(s)
            for hexm in _PDF_HEX.finditer(seg):
                raw = re.sub(rb"\s", b"", hexm.group(1))
                if len(raw) % 2:
                    raw += b"0"
                try:
                    b2 = bytes.fromhex(raw.decode("ascii"))
                except ValueError:
                    continue
                if len(b2) % 2 == 0:
                    try:
                        u = b2.decode("utf-16-be")
                    except UnicodeDecodeError:
                        u = ""
                    if sum(ch.isprintable() for ch in u) > len(u) * 0.8 and u.strip():
                        bits.append(u)
                else:
                    bits.append(b2.decode("latin-1", errors="replace"))

    r.text = tidy("\n".join(bits))
    r.method = f"pdf-zlib({n_dec}/{n_stream} stream decoded)"
    r.meta.update(n_streams=n_stream, n_decoded=n_dec)
    if not r.text.strip():
        r.warnings.append(
            "no extractable text layer (CID/Type0 font or scanned image); "
            "cite by page-level metadata only -- do NOT paraphrase unread content"
        )
    elif len(r.text) < 200:
        r.warnings.append(f"very short text layer ({len(r.text)} chars)")


# ══════════════════════════════════════════════════════════════
# 分发
# ══════════════════════════════════════════════════════════════
def _kind_of(p: Path) -> str:
    """扩展名 → 容器类型；无扩展名时按**文件名白名单**认作纯文本。

    ★ ``doc/multi1d7.6/{README,manual,history,examples}`` 没有扩展名，
    却是最权威的 ``ts`` 状态量定义与输入文件规格来源 —— 只认扩展名会全部漏掉。
    """
    ext = p.suffix.lower()
    if ext:
        return KIND_BY_EXT.get(ext, "unknown")
    return "text" if p.name.lower() in config.DOC_EXTENSIONLESS else "unknown"


def _relpath_of(p: Path) -> str:
    for base in (config.MATTER_DIR, config.MULTI_HOME):
        try:
            return f"{base.name}/{p.resolve().relative_to(base.resolve()).as_posix()}"
        except ValueError:
            continue
    return p.name


# ══════════════════════════════════════════════════════════════
# 「文档 vs 数值数据」判别
# ══════════════════════════════════════════════════════════════
def looks_like_data(path: str | Path, *,
                    sample: int | None = None,
                    ratio: float | None = None) -> tuple[bool, float]:
    """判断一个纯文本文件是**数值数据表**还是**说明文档**。

    ★ 为什么需要它：``matter++/ATOMIC/Al.txt`` 是 13.5 MB、34.8 万行的数值表，
    扩展名与 ``matter++/Readme.txt`` 完全一样。只看扩展名会把数据当文档吞进来，
    抽出的"文档"就是一堆浮点数。这里用**内容**做第二次判别：

    抽取采样行的非空行，统计 :func:`eosop_pro.core.fortran_numbers.is_payload_line`
    为真的比例；超过 ``ratio`` 即判为数据。

    返回 ``(is_data, payload_ratio)``。
    """
    from .core import fortran_numbers as fn

    p = Path(path)
    n_s = sample if sample is not None else config.DOC_NUMERIC_SAMPLE
    r_th = ratio if ratio is not None else config.DOC_NUMERIC_RATIO

    seen = payload = 0
    try:
        for i, line in enumerate(textio.iter_lines(p)):
            if i >= n_s:
                break
            if not line.strip():
                continue
            seen += 1
            if fn.is_payload_line(line):
                payload += 1
    except OSError:
        return False, 0.0
    if seen == 0:
        return False, 0.0
    p_ratio = payload / seen
    return p_ratio >= r_th, p_ratio


def extract(path: str | Path) -> DocText:
    """抽取单份文档。**任何异常都转成 warning，不抛出**（批量抽取要跑完全树）。"""
    p = Path(path)
    kind = _kind_of(p)
    data = p.read_bytes() if p.exists() else b""
    r = DocText(src=p, relpath=_relpath_of(p), kind=kind,
                size_bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest())

    if not data:
        r.warnings.append("empty file or missing")
        return r

    try:
        if kind == "ooxml-word":
            with zipfile.ZipFile(p) as zf:
                _extract_ooxml_word(zf, r)
        elif kind == "ooxml-slide":
            with zipfile.ZipFile(p) as zf:
                _extract_ooxml_slide(zf, r)
        elif kind == "ooxml-sheet":
            with zipfile.ZipFile(p) as zf:
                _extract_ooxml_sheet(zf, r)
        elif kind == "xmind":
            with zipfile.ZipFile(p) as zf:
                _extract_xmind(zf, r)
        elif kind == "ole2-word":
            _extract_ole2(data, r, word=True)
        elif kind == "ole2-sheet":
            _extract_ole2(data, r, word=False)
        elif kind == "pdf":
            _extract_pdf(data, r)
        elif kind == "text":
            doc = textio.read_text(p)
            r.text = tidy("\n".join(doc.lines)) if hasattr(doc, "lines") else tidy(doc.text)
            r.method = f"textio/{doc.encoding}"
            r.meta["encoding"] = doc.encoding
        else:
            r.warnings.append(
                f"unsupported extension {p.suffix.lower()!r} (-> unknown)")
            r.method = "none"
    except (zipfile.BadZipFile, OSError, ValueError, zlib.error) as exc:
        r.warnings.append(f"{type(exc).__name__}: {exc}")
        r.method = r.method or "failed"

    return r


def scan_documents(root: str | Path | None = None, *,
                   exts: tuple[str, ...] = DOC_EXTS,
                   include_extensionless: bool = True,
                   skip_temp: bool = True,
                   max_bytes: int | None = None,
                   txt_max_bytes: int | None = None,
                   numeric_gate: bool = True) -> list[Path]:
    """递归列出可抽取的文档。

    ``root`` 缺省时扫 :data:`eosop_pro.config.DOC_SCAN_ROOTS`
    （``doc/`` + ``matter++/``）—— ★ 刻意不扫整个 ``MULTI_HOME``，否则
    ``matter++/ATOMIC/*.txt``（每个 13.5 MB 数值表）会被按扩展名吞进来。

    四道闸门，全部基于**内容/体积**而不是单纯扩展名：

    1. ``include_extensionless`` —— 认 :data:`config.DOC_EXTENSIONLESS` 里的
       无扩展名文件（``README`` / ``manual`` / ``history`` / ``examples``）
    2. ``max_bytes``    —— 结构化容器（docx/pptx/xlsx/pdf/xmind）体积上限
    3. ``txt_max_bytes``—— 纯文本候选体积上限
    4. ``numeric_gate`` —— 纯文本候选须通过 :func:`looks_like_data` 的"非数据"判定
       （:data:`config.DOC_ALLOWLIST` 里的文件豁免，因为它们是"几乎全数字的规格"）

    ``skip_temp`` 跳过 Office 锁文件 ``~$*``。
    """
    roots = [Path(root)] if root else [Path(r) for r in config.DOC_SCAN_ROOTS]
    mb = max_bytes if max_bytes is not None else config.DOC_MAX_BYTES
    tb = txt_max_bytes if txt_max_bytes is not None else config.DOC_TXT_MAX_BYTES

    out: list[Path] = []
    for base in roots:
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            if skip_temp and p.name.startswith("~$"):
                continue
            ext = p.suffix.lower()
            if ext:
                if ext not in exts:
                    continue
            elif not include_extensionless:
                continue

            kind = _kind_of(p)
            if kind == "unknown":
                continue
            try:
                size = p.stat().st_size
            except OSError:
                continue
            limit = tb if kind == "text" else mb
            if size > limit:
                continue
            if (kind == "text" and numeric_gate
                    and p.name.lower() not in config.DOC_ALLOWLIST):
                is_data, _ = looks_like_data(p)
                if is_data:
                    continue
            out.append(p)
    return out


def extract_all(root: str | Path | None = None, *,
                exts: tuple[str, ...] = DOC_EXTS,
                outdir: str | Path | None = None,
                write: bool = True) -> list[DocText]:
    """抽取 ``root`` 下全部文档；``write=True`` 时落盘 ``docs/extracted/``。"""
    od = Path(outdir) if outdir else config.EXTRACTED_DIR
    od.mkdir(parents=True, exist_ok=True)
    results = [extract(p) for p in scan_documents(root, exts=exts)]
    if write:
        for r in results:
            if r.ok:
                (od / r.out_name()).write_text(r.text, encoding="utf-8", newline="\n")
        write_manifest(results, od)
    return results


def write_manifest(results: list[DocText], outdir: str | Path | None = None) -> Path:
    """写 ``MANIFEST.md``（人读）+ ``manifest.json``（机读）。"""
    from . import reporting

    od = Path(outdir) if outdir else config.EXTRACTED_DIR
    od.mkdir(parents=True, exist_ok=True)
    rows = [r.to_row() for r in results]

    md = [reporting.md_header(
        "文档抽取清单", f"{config.MULTI_HOME}", len(results),
        extra=[("抽取成功", sum(1 for r in results if r.ok)),
               ("无文本层 / 空", sum(1 for r in results if not r.ok))])]
    md.append("## 1. 按容器类型计数\n")
    import collections
    md.append(reporting.counter_table(
        collections.Counter(r.kind for r in results), "kind", "files"))
    md.append("\n## 2. 抽取方式计数\n")
    md.append(reporting.counter_table(
        collections.Counter(r.method for r in results), "method", "files"))
    md.append("\n## 3. 逐文件明细\n")
    md.append(reporting.md_table(
        rows, ["relpath", "kind", "size_bytes", "n_chars", "n_lines",
               "sha256", "out_name", "warnings"],
        shorten_to=70))
    md.append("\n## 4. 告警明细\n")
    warn = [r for r in results if r.warnings]
    md.append(reporting.md_table(
        [{"relpath": r.relpath, "warnings": " ;; ".join(r.warnings)} for r in warn],
        ["relpath", "warnings"], shorten_to=110) if warn else "（无）\n")
    reporting.write_md(od / "MANIFEST.md", "\n".join(md))
    return reporting.write_json(od / "manifest.json", {
        "generated_utc": reporting.utc_now(),
        "root": str(config.MULTI_HOME),
        "n_files": len(results),
        "n_ok": sum(1 for r in results if r.ok),
        "documents": rows,
    })


def main(argv: list[str] | None = None) -> int:
    """``python -m eosop_pro.docsrc [--root DIR] [--list]``。"""
    import argparse

    ap = argparse.ArgumentParser(description="抽取 Multi1D++ 说明文档为纯文本")
    ap.add_argument("--root", default=None, help="默认 Multi1D++Portable20241128")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--list", action="store_true", help="只列文件不抽取")
    args = ap.parse_args(argv)

    if args.list:
        for p in scan_documents(args.root):
            print(f"{p.stat().st_size:>10}  {p.relative_to(args.root or config.MULTI_HOME)}")
        return 0

    res = extract_all(args.root, outdir=args.outdir)
    for r in res:
        print(r.describe())
    ok = sum(1 for r in res if r.ok)
    print("-" * 70)
    print(f"抽取 {ok}/{len(res)} 份成功 -> {args.outdir or config.EXTRACTED_DIR}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
