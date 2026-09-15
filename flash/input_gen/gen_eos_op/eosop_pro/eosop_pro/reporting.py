"""报告写出工具（CSV / Markdown）—— 审计证据的统一格式。

所有报告都遵循同一纪律：**头部写明数据来源、生成时刻、样本总数、sha256 汇总**，
让每条结论都可追溯到具体文件与字段。
"""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

from . import config

__all__ = [
    "now_stamp",
    "utc_now",
    "write_csv",
    "write_json",
    "write_md",
    "md_header",
    "md_table",
    "counter_table",
    "shorten",
]


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def now_stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%S", time.localtime())


def shorten(s: Any, n: int = 60) -> str:
    t = str(s)
    return t if len(t) <= n else t[: n - 3] + "..."


def write_csv(path: str | Path, rows: Sequence[dict[str, Any]],
              columns: Sequence[str] | None = None) -> Path:
    """写 CSV（UTF-8 with BOM，便于 Excel 直接打开中文）。

    ``newline=""`` 交给 ``csv`` 模块自己写行尾 —— 它的默认终结符是 ``\\r\\n``，
    符合 RFC 4180，也正是 Excel 期待的形式。**只有 CSV 用 CRLF**，
    其余文本产物一律 LF（见 :func:`write_md` 的说明）。
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if columns is None:
        seen: list[str] = []
        for r in rows:
            for k in r:
                if k not in seen:
                    seen.append(k)
        columns = seen
    with open(p, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(columns), extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _cell(r.get(k)) for k in columns})
    return p


def write_json(path: str | Path, obj: Any) -> Path:
    """写 JSON（UTF-8，**LF**）。

    ★ ``newline="\\n"`` 不能省：Python 的文本模式在 Windows 上会把 ``\\n``
    翻译成 ``\\r\\n``，于是同一份报告在 Windows 与 Linux 上字节不同 ——
    git 会看到"全文件改动"，`.gitattributes` 的 `eol=lf` 也失去意义。
    实测：不加这个参数时 ``docs/extracted/manifest.json`` 带 CRLF。
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str),
                 encoding="utf-8", newline="\n")
    return p


def write_md(path: str | Path, text: str) -> Path:
    """写 Markdown（UTF-8，**LF**）—— 同 :func:`write_json` 的 ``newline`` 理由。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")
    return p


def _cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, tuple, set)):
        return " ;; ".join(str(x) for x in v)
    if isinstance(v, dict):
        return " ;; ".join(f"{k}={v2}" for k, v2 in v.items())
    return str(v)


def md_header(title: str, source: str, total: int,
              extra: Iterable[tuple[str, Any]] = ()) -> str:
    """报告固定头部：标题、数据来源、生成时刻、样本总数。"""
    lines = [
        f"# {title}",
        "",
        f"- 数据来源: `{source}`",
        f"- 生成时刻 (UTC): `{utc_now()}`",
        f"- 样本总数: **{total}**",
        f"- 工具: `{config.TOOL_VERSION}` / schema `{config.SCHEMA_VERSION}`",
    ]
    for k, v in extra:
        lines.append(f"- {k}: {v}")
    lines.append("")
    return "\n".join(lines)


def md_table(rows: Sequence[dict[str, Any]], columns: Sequence[str],
             max_rows: int | None = None, shorten_to: int = 70) -> str:
    """把行序列渲染成 Markdown 表。"""
    out = ["| " + " | ".join(columns) + " |",
           "|" + "|".join("---" for _ in columns) + "|"]
    for r in (rows[:max_rows] if max_rows else rows):
        cells = [_cell(r.get(c)).replace("|", "\\|") for c in columns]
        out.append("| " + " | ".join(shorten(c, shorten_to) for c in cells) + " |")
    if max_rows and len(rows) > max_rows:
        out.append(f"| ... | 共 {len(rows)} 行，仅显示前 {max_rows} 行 |"
                   + " |" * (len(columns) - 2))
    return "\n".join(out) + "\n"


def counter_table(counter: Any, key_name: str = "key",
                  value_name: str = "count", top: int | None = None) -> str:
    """把 ``Counter`` 渲染成 Markdown 表。"""
    items = counter.most_common(top) if hasattr(counter, "most_common") else list(counter)
    rows = [{key_name: k, value_name: v} for k, v in items]
    total = sum(v for _k, v in items) or 1
    for r, (_k, v) in zip(rows, items):
        r["pct"] = f"{100.0 * v / total:.1f}%"
    return md_table(rows, [key_name, value_name, "pct"])
