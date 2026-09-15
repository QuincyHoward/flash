"""伴随注释文件发现与配对 —— 阶段 A 的**声明式**证据来源。

实测配对实例
------------
========================================  ==========================================
伴随文件                                   它声明了什么（并关联到哪些数据文件）
========================================  ==========================================
``mat_Au-1.0/AU_info``                     群数 NG=20 + 单位 keV + ``Z/P/R/E`` 表号映射
``SNOP/opbe.inhalt``                       NG=40 + 4 个表号（**拆分 opbe 的钥匙**）
``mat_Be-1.0/BE_eos.info``                 ``_e``/``_i`` → IME=304 / IMI=305
``mat_Be-1.0/Be20keV.info``                ``Be20keV.PLANCK`` / ``.ROSS`` 两个伴随文件
``mat_CELIA/C.ZEFF.readme``                单位变更史（eV → keV）与等价文件
``ATOMIC/#LEDCOP``                         ``Al.txt`` → Atomic 网站生成（GB18030）
``Thermos/Readme.txt``                     目录级：``*_Z.dat``=eV、``*_Zeff.dat``=keV
``mat_Ge/Readme.txt``                      ``T in eV, rho in g/cc, k in cm2/g``
========================================  ==========================================

三类配对规则
------------
1. **同名/前缀**：``<stem>.info|.inhalt|.readme`` 或数据名以 ``<stem>`` 开头
   （涵盖 ``BE_eos.info`` ↔ ``BE_eos_e``、``Mix20keV.info`` ↔ ``Mix20keV.PLANCK``）
2. **目录级**：``README`` / ``Readme.txt`` / ``MODINFO`` 作用于本目录（及按需子目录）全部数据
3. **``#`` 前缀**：``#LEDCOP`` 这类是**说明文件而非数据**，其内容含「文件名 → 来源」映射
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .. import config
from ..core import textio
from ..core.annotations import Annotation, extract_annotations

__all__ = ["COMPANION_SUFFIXES", "COMPANION_FILENAMES", "COMPANION_PREFIXES",
           "AnnotationStore"]

COMPANION_SUFFIXES = (".info", ".inhalt", ".readme")
#: ★ 下划线变体：MULTI 惯例里同时存在 ``AU_info``（下划线）与 ``BE_eos.info``（点）。
#: 实测踩过：只认 ``.info`` 会漏掉 ``mat_Au-1.0/AU_info``（含权威的 Z/P/R/E 表号映射）。
COMPANION_SUFFIXES_UNDERSCORE = ("_info", "_inhalt", "_readme")
COMPANION_FILENAMES = ("readme", "readme.txt", "modinfo")
COMPANION_PREFIXES = ("#",)

_ALL_SUFFIXES = COMPANION_SUFFIXES + COMPANION_SUFFIXES_UNDERSCORE


def _is_companion(fname: str) -> bool:
    low = fname.lower()
    if low in COMPANION_FILENAMES:
        return True
    if any(low.endswith(s) for s in _ALL_SUFFIXES):
        return True
    return any(fname.startswith(p) for p in COMPANION_PREFIXES)


def _stem_for(fname: str) -> str:
    """伴随文件名去掉 ``.info/.inhalt/.readme``（含下划线变体）后的主干。

    ``BE_eos.info`` → ``BE_eos``（配 ``BE_eos_e`` / ``BE_eos_i``）
    ``AU_info``     → ``AU``    （配 ``AU_eos`` / ``AU_op03p`` / …）
    ``Mix20keV.info`` → ``Mix20keV``（配 ``Mix20keV.PLANCK`` / ``.ROSS`` / ``.EPS``）
    """
    low = fname.lower()
    for s in _ALL_SUFFIXES:
        if low.endswith(s):
            return fname[: -len(s)]
    return fname


@dataclass
class _DirEntry:
    rel_dir: str
    annotations: list[Annotation] = field(default_factory=list)
    #: 子目录递归生效（如 ``matter++/Readme.txt`` 对全树）
    recursive: bool = False


class AnnotationStore:
    """扫描 ``matter++`` 下的伴随注释文件，并提供「数据文件 → 注释」查询。"""

    def __init__(self, matter_dir: str | Path | None = None) -> None:
        self.matter_dir = Path(matter_dir or config.MATTER_DIR)
        self._built = False
        #: rel_dir → 目录级注释（README/MODINFO/Readme.txt）
        self._dir_entries: dict[str, _DirEntry] = {}
        #: (rel_dir, stem) → 文件名级注释
        self._stem_entries: dict[tuple[str, str], list[Annotation]] = {}
        #: 全部伴随文件（relpath）与解析结果
        self.companions: dict[str, Annotation] = {}
        self.skipped: list[str] = []

    # ── 构建索引 ────────────────────────────────────────────────
    def build(self, *, force: bool = False) -> "AnnotationStore":
        if self._built and not force:
            return self
        self._dir_entries.clear()
        self._stem_entries.clear()
        self.companions.clear()
        self.skipped.clear()

        for root, dirs, files in os.walk(self.matter_dir):
            dirs.sort()
            rel_dir = os.path.relpath(root, self.matter_dir).replace("\\", "/")
            if rel_dir == ".":
                rel_dir = ""
            for fname in sorted(files):
                if not _is_companion(fname):
                    continue
                rel = f"{rel_dir}/{fname}" if rel_dir else fname
                abs_p = os.path.join(root, fname)
                try:
                    doc = textio.read_text(abs_p)
                    ann = extract_annotations(doc, kind="companion", source=rel)
                except Exception as exc:  # noqa: BLE001
                    self.skipped.append(f"{rel}: {type(exc).__name__}: {exc}")
                    continue
                self.companions[rel] = ann

                low = fname.lower()
                if low in COMPANION_FILENAMES or low.startswith("#"):
                    # 目录级：README/MODINFO/#xxx 作用于**本目录及其子树**
                    # （例：Thermos/Readme.txt 描述 Thermos/mat_*/ 下的 *_Z*.dat）
                    entry = self._dir_entries.setdefault(
                        rel_dir, _DirEntry(rel_dir=rel_dir)
                    )
                    entry.annotations.append(ann)
                    entry.recursive = True
                else:
                    stem = _stem_for(fname)
                    self._stem_entries.setdefault((rel_dir, stem), []).append(ann)

        self._built = True
        return self

    # ── 查询 ────────────────────────────────────────────────────
    def for_file(self, relpath: str | Path) -> list[Annotation]:
        """返回作用于某个数据文件的全部伴随注释（文件名级 + 目录级）。"""
        self.build()
        rel = str(relpath).replace("\\", "/").lstrip("/")
        rel_dir, fname = os.path.split(rel)
        out: list[Annotation] = []

        # 1) 文件名级：精确 stem 或「数据名以 stem 开头」
        for (d, stem), anns in self._stem_entries.items():
            if d != rel_dir:
                continue
            if fname == stem or fname.startswith(stem):
                out.extend(anns)

        # 2) 目录级：本级 + 祖先级（祖先级仅当 recursive，即顶层 Readme.txt）
        parts = rel_dir.split("/") if rel_dir else []
        for i in range(len(parts) + 1):
            d = "/".join(parts[:i]) if i else ""
            entry = self._dir_entries.get(d)
            if entry is None:
                continue
            if i == len(parts) or entry.recursive:
                out.extend(entry.annotations)
        return out

    def for_directory(self, rel_dir: str) -> list[Annotation]:
        """某目录下的全部伴随注释（含本级与祖先级）。"""
        self.build()
        rel_dir = rel_dir.replace("\\", "/").strip("/")
        out: list[Annotation] = []
        parts = rel_dir.split("/") if rel_dir else []
        for i in range(len(parts) + 1):
            d = "/".join(parts[:i]) if i else ""
            entry = self._dir_entries.get(d)
            if entry and (i == len(parts) or entry.recursive):
                out.extend(entry.annotations)
        for (d, _stem), anns in self._stem_entries.items():
            if d == rel_dir:
                out.extend(anns)
        return out

    def merged_units(self, relpath: str | Path) -> dict[str, str]:
        """把作用于该文件的注释里的单位声明合并（后者不覆盖前者）。"""
        merged: dict[str, str] = {}
        for ann in self.for_file(relpath):
            for k, v in ann.units.items():
                merged.setdefault(k, v)
        return merged

    def merged_file_unit_hints(self, relpath: str | Path) -> dict[str, str]:
        """合并作用于该文件的「文件名模式 → 单位」提示。"""
        merged: dict[str, str] = {}
        for ann in self.for_file(relpath):
            for k, v in ann.file_unit_hints.items():
                merged.setdefault(k, v)
        return merged

    def unit_hint_for(self, relpath: str | Path, *, axis: str = "T") -> str | None:
        """按数据文件名匹配「文件名模式 → 单位」声明，返回该轴的单位。

        实测关键用途：``Thermos/Readme.txt`` 声明
        ``*_Z.dat 文件温度单位为eV`` / ``*_Zeff.dat 文件温度单位为keV``，
        据此把 ``Al_Zeff.dat``(keV) 与 ``Al_Z.dat``(eV) 这一对
        「表头与行数完全相同」的文件区分开 —— 靠**声明**而不是猜测。

        匹配规则：取**最长**命中模式，避免 ``_Z.dat`` 误配 ``_Zeff.dat``。
        """
        hints = self.merged_file_unit_hints(relpath)
        if not hints:
            return None
        fname = os.path.basename(str(relpath).replace("\\", "/"))
        best_pat = ""
        best_unit: str | None = None
        for pat, unit in hints.items():
            if fname.endswith(pat) and len(pat) > len(best_pat):
                best_pat, best_unit = pat, unit
        if axis == "T":
            return best_unit
        return None

    def table_id_kinds(self) -> dict[int, str]:
        """从全部伴随即注中收集「表号 → 类型字符/名称」映射。

        实测权威来源：``mat_Au-1.0/AU_info`` 的 ``Z:27002003; P:27003003; ...``
        以及 ``mat_Others/Mix20keV.info`` 的 ``IP=20143000`` / ``IR=20144000``。
        """
        self.build()
        kinds: dict[int, str] = {}
        letter_meaning = {
            "Z": "ZEFF", "P": "PLANCK", "R": "ROSSELAND", "E": "EMISSIVITY",
            "IP": "PLANCK", "IR": "ROSSELAND", "IEPS": "EMISSIVITY",
            "NPLA": "PLANCK", "NROSS": "ROSSELAND", "NEPS": "EMISSIVITY", "NZ": "ZEFF",
        }
        for ann in self.companions.values():
            for key, num in ann.table_ids.items():
                kinds.setdefault(num, letter_meaning.get(key, key))
        return kinds

    # ── 报告 ────────────────────────────────────────────────────
    def summary(self) -> dict[str, int]:
        self.build()
        n_dir = sum(len(e.annotations) for e in self._dir_entries.values())
        n_stem = sum(len(v) for v in self._stem_entries.values())
        return {
            "companion_files": len(self.companions),
            "dir_level": n_dir,
            "stem_level": n_stem,
            "skipped": len(self.skipped),
            "with_units": sum(1 for a in self.companions.values() if a.units),
            "with_table_ids": sum(1 for a in self.companions.values() if a.table_ids),
            "with_dims": sum(1 for a in self.companions.values() if a.dims),
        }
