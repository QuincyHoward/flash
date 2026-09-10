"""
gen_flychk_his.zip_writer — FLYCHK history 输入 zip 写出器 (自包含)
==================================================================

**本模块完全自包含（仅依赖 Python 标准库）**，不导入、不搜索、不依赖任何
外部 FLYCHK Python 包 —— 便于 flash-sim 独立分发使用。

它只负责一件事: 把 `builder.HistoryTable` 写成 NIST FLYCHK 网站 history 模式
可上传的 zip。写出的内容是 **FLYCHK 官方 history 输入格式**（格式契约见下），
即"格式与 FLYCHK 兼容"，而不是"代码依赖某个 FLYCHK 实现"。

格式契约 ``FORMAT_CONTRACT_ID = "flychk-history-v1"``
----------------------------------------------------

zip 成员（顺序固定）:

1. ``runfile.txt`` — 控制文件::

       z {z}
       initial ss
       evolve ss
       history
       opacity file                     # 仅当含 size 列
       ti file                          # 仅当含 ti 列
       tr file                          # 仅当含 tr 列
       history {datafile} rho|ne|ni     # 密度列三选一
       end

2. ``history_{element}_Z{z}_input.txt`` — 数据文件::

       time size te ti tr rho           # 首行列名, 空格分隔
       1.000000e-12 2.000000e-04 ...    # 数据行, %.6e

约束（与 FLYCHK 网站接受范围一致，违反时抛 `ZipWriterError`）:

- 必须含 ``time`` 与 ``te``；
- ``rho`` / ``ne`` / ``ni`` 最多出现一种（runfile 只给出一个密度基准）；
- 每行列数必须等于列数。
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .builder import HistoryTable

# 格式契约标识（写入 manifest, 便于下游核对）
FORMAT_CONTRACT_ID = "flychk-history-v1"
WRITER_ID = "flash.input_gen.gen_flychk_his"

BASE_COLUMNS = ("time", "size", "te", "ti", "tr")
DENSITY_COLUMNS = ("rho", "ne", "ni")


class ZipWriterError(RuntimeError):
    """写出 FLYCHK history 输入 zip 失败。"""


# ══════════════════════════════════════════════════════════
# 文本渲染 (纯函数, 便于单测/人工核对)
# ══════════════════════════════════════════════════════════
def render_runfile(element: str, z: int, columns: Sequence[str],
                   data_filename: str) -> str:
    """渲染 ``runfile.txt`` 内容。"""
    cols = set(columns)
    lines = [f"z {int(z)}", "initial ss", "evolve ss", "history"]
    if "size" in cols:
        lines.append("opacity file")
    if "ti" in cols:
        lines.append("ti file")
    if "tr" in cols:
        lines.append("tr file")
    for mode in ("rho", "ne", "ni"):
        if mode in cols:
            lines.append(f"history {data_filename} {mode}")
            break
    lines.append("end")
    return "\n".join(lines) + "\n"


def render_data(columns: Sequence[str], rows: Sequence[Sequence[float]]) -> str:
    """渲染 FLYCHK 数据文件内容（首行列名 + ``%.6e`` 数据行）。"""
    lines = [" ".join(columns)]
    for row in rows:
        lines.append(" ".join(f"{v:.6e}" for v in row))
    return "\n".join(lines) + "\n"


def validate_columns(columns: Sequence[str], rows: Sequence[Sequence[float]],
                     element: str = "", z: int = 0) -> None:
    """校验列组合与行长（FLYCHK 输入约束）。"""
    cols = list(columns)
    if not cols:
        raise ZipWriterError("columns 不能为空")
    col_set = set(cols)
    missing = [c for c in ("time", "te") if c not in col_set]
    if missing:
        raise ZipWriterError(f"columns 必须包含 {missing}（FLYCHK history 必需）")
    present_density = [c for c in DENSITY_COLUMNS if c in col_set]
    if len(present_density) > 1:
        raise ZipWriterError(
            f"rho/ne/ni 只能出现一种，当前包含：{present_density}"
            "（FLYCHK runfile 只接受单一密度基准）"
        )
    if not present_density:
        raise ZipWriterError(
            "columns 必须包含 rho/ne/ni 之一：FLYCHK runfile 通过"
            " 'history <datafile> <mode>' 关联数据文件，缺密度列时数据文件不会被读取"
        )
    n = len(cols)
    for i, row in enumerate(rows):
        if len(row) != n:
            raise ZipWriterError(
                f"第 {i} 行长度 ({len(row)}) 与列数 ({n}) 不一致"
            )


def data_filename_for(element: str, z: int) -> str:
    """FLYCHK history 数据文件名。"""
    return f"history_{element}_Z{int(z)}_input.txt"


# ══════════════════════════════════════════════════════════
# 写出器
# ══════════════════════════════════════════════════════════
@dataclass
class HistoryZipWriter:
    """FLYCHK history 输入 zip 写出器（自包含, 无外部依赖）。

    用法::

        w = HistoryZipWriter()
        w.write(table, "out/history_whole_Ti_Z22_in_.zip")
    """

    compress: bool = True

    # ── 主接口 ──────────────────────────────────────────────
    def write(self, table: HistoryTable, output_path: str) -> Path:
        """由 `HistoryTable` 写出 zip (element/z 取自 table.meta)。"""
        return self.generate_history_zip(
            element=table.element, z=table.z,
            columns=list(table.columns),
            data_rows=[list(r) for r in table.rows],
            output_path=str(output_path),
        )

    def generate_history_zip(self, element: str = "Ti", z: int = 22,
                             columns: Optional[List[str]] = None,
                             data_rows: Optional[List[List[float]]] = None,
                             output_path: Optional[str] = None) -> Path:
        """写出 FLYCHK history 输入 zip，返回路径。"""
        cols = list(columns or ["time", "size", "te", "ti", "tr", "rho"])
        rows = [[float(v) for v in r] for r in
                (data_rows or [[1e-12, 1e-4, 500.0, 480.0, 450.0, 1e-3]])]
        validate_columns(cols, rows, element=element, z=z)

        data_name = data_filename_for(element, z)
        runfile = render_runfile(element, z, cols, data_name)
        data = render_data(cols, rows)

        out = Path(output_path) if output_path else \
            Path(f"history_{element}_Z{int(z)}_in_.zip")
        out.parent.mkdir(parents=True, exist_ok=True)
        mode = zipfile.ZIP_DEFLATED if self.compress else zipfile.ZIP_STORED
        with zipfile.ZipFile(str(out), "w", mode) as zf:
            zf.writestr("runfile.txt", runfile)
            zf.writestr(data_name, data)
        return out

    # ── 自校验 ──────────────────────────────────────────────
    @staticmethod
    def expected_members(element: str, z: int) -> List[str]:
        return ["runfile.txt", data_filename_for(element, z)]

    def verify_zip(self, table: HistoryTable, zip_path: str) -> Dict[str, Any]:
        """读取刚写出的 zip 并与表内容逐字符核对（自包含完整性检查）。

        Returns:
            {"ok": bool, "members": [...], "checks": {...}, "detail": ...}
        """
        expected_members = self.expected_members(table.element, table.z)
        res: Dict[str, Any] = {"ok": False, "members": [], "checks": {}}
        path = Path(zip_path)
        if not path.is_file():
            res["detail"] = f"zip 不存在: {path}"
            return res
        with zipfile.ZipFile(str(path)) as zf:
            members = zf.namelist()
            res["members"] = members
            res["checks"]["member_order"] = members == expected_members
            if not res["checks"]["member_order"]:
                res["detail"] = f"成员顺序不符: {members} != {expected_members}"
                return res
            runfile = zf.read("runfile.txt").decode("utf-8")
            data = zf.read(expected_members[1]).decode("utf-8")
        res["checks"]["runfile_content"] = runfile == render_runfile(
            table.element, table.z, table.columns, expected_members[1])
        res["checks"]["data_matches_table"] = data == table.to_text()
        res["checks"]["format_contract"] = FORMAT_CONTRACT_ID
        res["checks"]["n_steps"] = table.n_steps
        res["ok"] = all(bool(v) for k, v in res["checks"].items()
                        if isinstance(v, bool))
        if not res["ok"]:
            res["detail"] = "zip 内容与表不一致: " + ", ".join(
                k for k, v in res["checks"].items() if v is False)
        return res


def write_history_zip(table: HistoryTable, output_path: str) -> Path:
    """便捷函数: 写出单个 FLYCHK history 输入 zip。"""
    return HistoryZipWriter().write(table, output_path)


def verify_history_zip(table: HistoryTable, zip_path: str) -> Dict[str, Any]:
    """便捷函数: 校验已写出的 zip 与表内容一致。"""
    return HistoryZipWriter().verify_zip(table, zip_path)


__all__ = [
    "HistoryZipWriter", "ZipWriterError", "write_history_zip",
    "verify_history_zip", "render_runfile", "render_data",
    "validate_columns", "data_filename_for",
    "FORMAT_CONTRACT_ID", "WRITER_ID",
]
