"""``hyades/EOS.list`` 与 ``hyades/Opacity.list`` 解析 —— 注册表第三源。

实测格式（空白分列）
--------------------
``hyades/EOS.list``（**84** 行）::

    11        Deuterium+tritium  1.000       2.515       0.2205
    41        Aluminum    13.00       26.982     2.7568
    44        Aluminum    13.00       26.982     2.7      *  #
    531       Zinc           30.00       65.37       7.139

``hyades/Opacity.list``（**36** 行）::

    1022   Quartz       10.00       20.028
    1032   Polystyrene            3.500        <- 字段可缺失！
    1051 *  Gold       79.00       196.97
    1491   Silver         47.00       107.68

缺字段判定规则
--------------
字段可缺失（``1032`` 只有 1 个数值），所以**不能按列数硬解析**。
规则：``id`` = 首 token；``name`` = 其后第一个非数值 token；
其余数值 token 依序填入 ``[Zbar, Abar, rho0]``。

标志位：``*`` = Preferred（两种温度表亦被偏好）、``#`` = Two-temperature。
不透明度号 ≈ EOS 号 + 1000。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .. import config
from ..core import textio

__all__ = ["ListEntry", "parse_list_file", "parse_eos_list", "parse_opacity_list",
           "RegistryLists"]


@dataclass
class ListEntry:
    """一行 ``EOS.list`` / ``Opacity.list``。"""

    no: int
    name: str
    zbar: float | None = None
    abar: float | None = None
    rho0: float | None = None
    preferred: bool = False
    two_temperature: bool = False
    raw: str = ""
    line_no: int = 0

    def describe(self) -> str:
        flags = ("*" if self.preferred else "") + ("#" if self.two_temperature else "")
        return (f"{self.no} {self.name} Zbar={self.zbar} Abar={self.abar} "
                f"rho0={self.rho0} {flags}")


def _is_num(tok: str) -> bool:
    try:
        float(tok)
        return True
    except ValueError:
        return False


def parse_list_file(path: str | Path) -> list[ListEntry]:
    """解析一个 ``*.list`` 文件（字段可缺失，按语义填充）。"""
    doc = textio.read_text(path)
    out: list[ListEntry] = []
    for i, ln in enumerate(doc.lines):
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        toks = s.split()
        if len(toks) < 2:
            continue
        if not toks[0].lstrip("+-").isdigit():
            continue

        entry = ListEntry(no=int(toks[0]), name="", raw=s, line_no=i)
        nums: list[float] = []
        seen_name = False
        for t in toks[1:]:
            if t == "*":
                entry.preferred = True
                continue
            if t == "#":
                entry.two_temperature = True
                continue
            if _is_num(t):
                nums.append(float(t))
            elif not seen_name:
                entry.name = t
                seen_name = True
            else:
                # 名字里的第二个词（如 "Deuterium+tritium" 不会走到这里；
                # 但保险起见并入名字）
                entry.name = f"{entry.name} {t}"
        # 数值按 [Zbar, Abar, rho0] 左→右填充
        if len(nums) >= 1:
            entry.zbar = nums[0]
        if len(nums) >= 2:
            entry.abar = nums[1]
        if len(nums) >= 3:
            entry.rho0 = nums[2]
        out.append(entry)
    return out


def parse_eos_list(path: str | Path | None = None) -> list[ListEntry]:
    return parse_list_file(path or config.EOS_LIST)


def parse_opacity_list(path: str | Path | None = None) -> list[ListEntry]:
    return parse_list_file(path or config.OPACITY_LIST)


class RegistryLists:
    """``EOS.list`` + ``Opacity.list`` 的合并索引。"""

    def __init__(self, eos_path: str | Path | None = None,
                 op_path: str | Path | None = None) -> None:
        self.eos_entries = parse_eos_list(eos_path)
        self.opacity_entries = parse_opacity_list(op_path)
        self._by_no: dict[int, ListEntry] = {}
        for e in self.eos_entries + self.opacity_entries:
            self._by_no.setdefault(e.no, e)

    def by_no(self, no: int) -> ListEntry | None:
        return self._by_no.get(no)

    def by_name(self, name: str) -> list[ListEntry]:
        low = name.lower()
        return [e for e in self.eos_entries + self.opacity_entries
                if e.name.lower() == low]

    @property
    def preferred(self) -> list[ListEntry]:
        return [e for e in self.eos_entries + self.opacity_entries if e.preferred]

    def summary(self) -> dict[str, int]:
        return {
            "eos_list": len(self.eos_entries),
            "opacity_list": len(self.opacity_entries),
            "preferred": len(self.preferred),
            "two_temperature": sum(
                1 for e in self.eos_entries + self.opacity_entries if e.two_temperature
            ),
        }
