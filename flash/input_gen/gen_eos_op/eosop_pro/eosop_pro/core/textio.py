"""文本读取 —— 编码链、换行统一、空行统计、流式读取。

实测背景（matter++）
--------------------
* 换行：CRLF 997 / LF 154 / **混合 3**（``CH/CHSi10_eos.IN``、``CH/CHSi1_eos.IN``、
  ``mat_C-1.0/CHSi1_eos.IN``）→ 一律用**通用换行**切分。
* **224** 个文件在 payload 区含内部空行（如 ``mat_Gd/Gd100ZEFF``）→ 解析器必须容忍。
* **291** 个文件无结尾换行 → 末行同样要参与解析，不做特判。
* ``matter++/Readme.txt`` 是 GB18030 → 编码链必须含 gb18030。

纪律
----
* 注释行与空行**永不进入** payload 数值流（由各解析器保证），但必须**计数并登记**。
* 原始行文本（去掉行尾换行符后）完整保留，供 ``header_raw`` 溯源。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from .. import config
from .byteclass import ByteClass, classify_bytes, encoding_chain, read_head

__all__ = ["TextDoc", "read_text", "iter_lines", "strip_bom", "is_blank", "load_lines"]


@dataclass
class TextDoc:
    """一次性读入的文本文件画像。"""

    path: Path
    text: str
    lines: list[str]
    encoding: str
    byteclass: ByteClass
    blank_line_indices: list[int] = field(default_factory=list)
    has_trailing_newline: bool = True

    # 便捷属性 ---------------------------------------------------------
    @property
    def n_lines(self) -> int:
        return len(self.lines)

    @property
    def newline_style(self) -> str:
        return self.byteclass.newline

    @property
    def has_bom(self) -> bool:
        return self.byteclass.has_bom

    def line(self, i: int) -> str:
        return self.lines[i]

    def head(self, n: int) -> list[str]:
        return self.lines[:n]


def strip_bom(s: str) -> str:
    """无条件剥离 BOM（26 个文件带 BOM，全部是文档类；防御性处理）。"""
    return s.lstrip(config.BOM)


def is_blank(line: str) -> bool:
    """空行 / 纯空白行。"""
    return not line.strip()


def read_text(path: str | Path) -> TextDoc:
    """整文件读入并解码（**正确性优先**：编码链作用于完整字节流）。

    适用于中小文件。超大文件（如 ``ATOMIC/Al.txt`` 34.8 万行）请用 :func:`iter_lines`
    以控制内存峰值。
    """
    p = Path(path)
    data = p.read_bytes()
    bc = classify_bytes(data, size_bytes=len(data))

    text: str | None = None
    for enc in encoding_chain(data):
        try:
            text = data.decode(enc)
            bc.encoding = enc
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if text is None:  # pragma: no cover - latin-1 永不失败
        raise UnicodeDecodeError("latin-1", data, 0, 1, "unreachable")

    return _build(p, text, bc)


def load_lines(path: str | Path) -> list[str]:
    """只取行列表（便捷封装）。"""
    return read_text(path).lines


def _build(p: Path, text: str, bc: ByteClass) -> TextDoc:
    has_trailing = text.endswith(("\n", "\r"))
    body = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = body.split("\n")
    if has_trailing and lines and lines[-1] == "":
        lines = lines[:-1]
    lines = [strip_bom(ln) if i == 0 else ln for i, ln in enumerate(lines)]
    blank = [i for i, ln in enumerate(lines) if is_blank(ln)]
    return TextDoc(
        path=p,
        text=text,
        lines=lines,
        encoding=bc.encoding or "latin-1",
        byteclass=bc,
        blank_line_indices=blank,
        has_trailing_newline=has_trailing,
    )


def iter_lines(path: str | Path, *, encoding: str | None = None) -> Iterator[str]:
    """流式逐行读取（通用换行），用于超大文件以压低内存峰值。

    编码由头部样本判定；整文件用 ``errors="replace"`` 解码，避免单个坏字节
    中断整个读取。数值区为纯 ASCII，替换字符只可能出现在文本注释里。
    """
    p = Path(path)
    if encoding is None:
        head = read_head(p)
        encoding = classify_bytes(head).encoding or "latin-1"
    first = True
    with open(p, "r", encoding=encoding, errors="replace", newline=None) as fh:
        for raw in fh:
            ln = raw[:-1] if raw.endswith("\n") else raw
            if first:
                ln = strip_bom(ln)
                first = False
            yield ln
