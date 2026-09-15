"""字节层分类 —— 决定一个文件能否走文本解析路径，以及用哪一段编码。

实测背景（matter++ 1164 个文本类文件）
--------------------------------------
* **26** 个带 UTF-8 BOM（全部是 ``.log/.txt/.md/.xml``，数据表 0 个）
* **12** 个非 UTF-8，其中 ``matter++/Readme.txt`` 是 **GB18030 中文**
  （``utf-8`` 解码直接抛 ``UnicodeDecodeError``，``gb18030`` 成功）
* **1** 个含 NUL 字节（``XrayMassCoef/.../Thumbs.db``）
* 换行风格：CRLF 997 / LF 154 / 混合 3

因此编码链必须包含 gb18030，且 NUL 检测要能一票否决文本路径。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .. import config
from .errors import BinarySuspect

__all__ = [
    "ByteClass", "SAMPLE_BYTES", "UTF8_BOM",
    "classify_bytes", "classify_file", "encoding_chain", "read_head",
]

SAMPLE_BYTES = 256 * 1024  # 256 KiB 足以判定；避免为 1.5 GB 目录做全量扫描
UTF8_BOM = b"\xef\xbb\xbf"

_TEXT_KINDS = ("text", "binary", "mixed")


@dataclass
class ByteClass:
    """一个文件的字节层画像。"""

    kind: str                       # text | binary | mixed
    encoding: str | None            # 命中的编码链段
    has_bom: bool = False
    has_nul: bool = False
    nul_ratio: float = 0.0
    printable_ratio: float = 0.0
    non_ascii_ratio: float = 0.0
    newline: str = "none"           # crlf | lf | cr | mixed | none
    size_bytes: int = 0
    sampled_bytes: int = 0
    reasons: list[str] = field(default_factory=list)

    @property
    def is_text(self) -> bool:
        return self.kind == "text"

    def describe(self) -> str:
        return (
            f"kind={self.kind} encoding={self.encoding} bom={self.has_bom} "
            f"nul={self.has_nul} printable={self.printable_ratio:.3f} "
            f"non_ascii={self.non_ascii_ratio:.4f} newline={self.newline}"
        )


def _newline_style(data: bytes) -> str:
    ncrlf = data.count(b"\r\n")
    nlf = data.count(b"\n") - ncrlf
    ncr = data.count(b"\r") - ncrlf
    present = [name for name, n in (("crlf", ncrlf), ("lf", nlf), ("cr", ncr)) if n]
    if not present:
        return "none"
    if len(present) == 1:
        return present[0]
    return "mixed"


def encoding_chain(data: bytes) -> tuple[str, ...]:
    """按「有无 BOM」选择编码链顺序，使报告里的 ``encoding`` 标签更准确。

    * 有 BOM → 先试 ``utf-8-sig``（否则标签会显示成 ``utf-8`` 而 BOM 被当正文）
    * 无 BOM → 先试 ``utf-8``（避免把无 BOM 的纯 UTF-8/ASCII 标成 ``utf-8-sig``）

    实测：26 个带 BOM 的文件全是 ``.log/.txt/.md/.xml``，数据表 0 个；
    而 ``matter++/Readme.txt`` 必须落到 ``gb18030``。
    """
    if data.startswith(UTF8_BOM):
        return ("utf-8-sig", "utf-8", "gb18030", "latin-1")
    return ("utf-8", "gb18030", "latin-1")


def _decode_chain(data: bytes) -> tuple[str | None, str | None]:
    """按 :func:`encoding_chain` 顺序试解，返回 ``(text, encoding)``。"""
    for enc in encoding_chain(data):
        try:
            return data.decode(enc), enc
        except (UnicodeDecodeError, LookupError):
            continue
    return None, None


def classify_bytes(data: bytes, *, size_bytes: int | None = None) -> ByteClass:
    """对一段字节（通常为文件头部样本）做分类。"""
    reasons: list[str] = []
    has_bom = data.startswith(UTF8_BOM)
    if has_bom:
        reasons.append("UTF-8 BOM present")

    nul_count = data.count(config.NUL_BYTE)
    has_nul = nul_count > 0
    nul_ratio = nul_count / len(data) if data else 0.0
    if has_nul:
        reasons.append(f"NUL bytes present ({nul_count})")

    non_ascii = sum(1 for b in data if b > 0x7F)
    non_ascii_ratio = non_ascii / len(data) if data else 0.0

    text, encoding = _decode_chain(data)
    if text is None:
        printable_ratio = 0.0
        reasons.append("no encoding in chain could decode sample")
    else:
        printable = sum(1 for ch in text if ch.isprintable() or ch.isspace())
        printable_ratio = printable / len(text) if text else 0.0

    if has_nul:
        kind = "binary"
    elif text is not None and printable_ratio >= 0.90:
        kind = "text"
    elif text is not None:
        kind = "mixed"
        reasons.append(f"low printable ratio ({printable_ratio:.3f})")
    else:
        kind = "binary"

    return ByteClass(
        kind=kind,
        encoding=encoding,
        has_bom=has_bom,
        has_nul=has_nul,
        nul_ratio=nul_ratio,
        printable_ratio=printable_ratio,
        non_ascii_ratio=non_ascii_ratio,
        newline=_newline_style(data),
        size_bytes=size_bytes if size_bytes is not None else len(data),
        sampled_bytes=len(data),
        reasons=reasons,
    )


def read_head(path: str | Path, n: int = SAMPLE_BYTES) -> bytes:
    with open(path, "rb") as fh:
        return fh.read(n)


def classify_file(path: str | Path, *, strict: bool = False) -> ByteClass:
    """对文件做字节层分类（只读头部样本）。

    ``strict=True`` 时若判为二进制则抛 :class:`BinarySuspect`。
    """
    p = Path(path)
    data = read_head(p)
    try:
        size = p.stat().st_size
    except OSError:
        size = len(data)
    bc = classify_bytes(data, size_bytes=size)
    if strict and bc.kind != "text":
        raise BinarySuspect(f"binary/suspect file: {p} :: {bc.describe()}")
    return bc
