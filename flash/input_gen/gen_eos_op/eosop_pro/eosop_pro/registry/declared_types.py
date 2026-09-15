"""阶段 A 的**声明式类型表** —— 零内容推断。

类型来源（按优先级）
--------------------
1. **扩展名**（``.301/.304/.305/.cn4/.cnr/.coldopacity/.feos/.sesame/.ini/.snop/.hug`` …）
2. **路径规则**（``matter++/Readme.txt`` 原文：含 ``hyades`` → Hyades；含 ``.feos`` → FEOS；
   含 ``.301/.304/.305`` → MPQeos；否则默认 SESAME 4×15）
3. **文件名 token 约定**（``_eos_e``/``_eos_i``/``_ieos``/``_mopp``/``_mopr``/``ZEFF``/
   ``PLANCK``/``ROSS``/``EPS``/``op03p``/``op03r``/``op03e``/``op03z``/``eos_<n>``/
   ``opc_<n>``/``qeos_<n>``/``_MULTI`` …）
4. **外部注册表**（``material.base`` 的 ``EOS/PLANCK/ROSSELAND/ZEFF`` 行 → 直接给出 KIND）
5. **伴随注释文件**（``.info`` 的 ``IME=304``/``IMI=305`` 等）

实测支撑：150 个无扩展名文件中 **95 个**可由注册表定案、**约 50 个**可由文件名 token 定案，
**仅约 5 个**是真硬骨头（交阶段 B）。

⚠️ 关于 ``.feos``
-----------------
``mat_Al-1.0/AL_eos.feos`` 与 ``AL_eos`` **字节相同**（名为 FEOS、实为 SESAME）。
阶段 A 按 ``Readme.txt`` 声明取候选顺序 ``[feos_native, multi_inverted_eos]``，
依次尝试；失败回退**记录在案**。这仍属"按声明候选尝试"，
真正的**内容识别**（行剖面/列剖面/计数反演/包络）留待阶段 B。
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .. import config
from .annotation_store import AnnotationStore
from .database_index import kind_from_sesame_id
from .material import MaterialRegistry

__all__ = [
    "FAMILIES",
    "KINDS",
    "EXT_MAP",
    "DeclaredType",
    "declare",
    "scan_declared",
    "default_registry",
]

# ── 家族（解析器）名 ────────────────────────────────────────────
FAMILIES = (
    "multi_inverted_eos",   # F1 反演 EOS（4×15）
    "multi_opacity",        # F2 灰度 / 多群不透明度、Zeff、EPS（4×15）
    "hyades_eos",           # F3 Hyades EOS（5×15，含 L 公式）
    "hyades_opacity",       # F3' SESAME 不透明度（同一 L 公式）
    "sesame_dat",           # SESAME 301 表（Hyades 布局）
    "mpqeos",               # F4 .301/.304/.305（4×16 或 4×15，逐文件推断）
    "feos_native",          # F4 原生 .feos（10 数表头）
    "feos_tabdata",         # F4 ShowEOS 导出的 TSV
    "feos_aux",             # .PAR/.cst/.mexport/.critical.dat/.isobaric.dat
    "ledcop_atomic",        # F5 ATOMIC/*.txt 主表（锚点状态机）
    "ledcop_zeff",          # F5 *.NoFree / *.AvSqFree（4 数头 + LEDCOP 魔数）
    "ionmix",               # .cn4/.cnr
    "coldopacity",          # 自描述两行表头
    "hugoniot",             # .hug
    "snop_input",           # SNOP 输入脚本
    "generic_curve",        # 一维曲线（ionpot / powerlaws / xray 等）
    "skip",                 # 明确的非数值文件
)

# ── KIND（写 h5 的 ``/tables/<KIND>_<id>``） ────────────────────
KINDS = (
    "EOS_TOTAL", "EOS_ELECTRON", "EOS_ION", "PLANCK", "ROSSELAND",
    "EMISSIVITY", "ZEFF", "ZEFF2", "NONLTE", "COLDOPACITY", "MUGROUP",
    "HUGONIOT", "CURVE", "AUX",
)

#: 扩展名 → (家族候选, KIND)
EXT_MAP: dict[str, tuple[tuple[str, ...], str | None]] = {
    ".301": (("mpqeos",), "EOS_TOTAL"),
    ".304": (("mpqeos",), "EOS_ELECTRON"),
    ".305": (("mpqeos",), "EOS_ION"),
    ".cn4": (("ionmix",), "AUX"),
    ".cnr": (("ionmix",), "AUX"),
    ".coldopacity": (("coldopacity",), "COLDOPACITY"),
    ".hug": (("hugoniot",), "HUGONIOT"),
    # ★ ``.sesame``（实测 6 个文件）：L0 = [MID/magic, rho0, nr, ne]，4×15 定宽。
    #   上游文档里这个布局正是 **F1 Inverted EOS**（见 SESAME 规格 docx
    #   "EOS数据" 一节）。实测 4 个文件的计数**精确**吻合
    #   ``4 + 2*nr + ne + 2*nr*ne``：
    #       SiO2/eos_22.sesame  [0,1,36,1792] → 130892 == 32723 行 × 4
    #       SiO2/eos_24.sesame  [0,1,73,2474] → 363828 == 90957 行 × 4
    #       SiO2/eos_21.sesame  [0,1,43,1765] → 153645 == 38411 行 × 4 + 1
    #       Ta2O5/PowerLaw...SESAME [0.12,1,3,19] → 143 == 36 行(3/4 列混排)
    #   所以**把真正有解析器的族放第一位**；``sesame_dat`` 只作语义标记保留。
    ".sesame": (("multi_inverted_eos", "sesame_dat", "hyades_eos",
                 "generic_curve"), None),
    # ★ ``.inv`` = INVerted（MULTI 术语）。实测 mat_CPC/{AU,BE}.INV：
    #   L0 = ' 1.00003010e+07 0.00000000e+00 1.23000000e+02 1.00000000e+02'
    #   → [SESAME id, 0.0, nr=123, ne=100]，6238 行 × 4 = 24952
    #   F1/with_e0(123,100) = 24950 + 2 尾部 ✓（其余布局都差得远）
    ".inv": (("multi_inverted_eos", "feos_aux"), "EOS_TOTAL"),
    ".ini": (("generic_curve",), "AUX"),
    ".snop": (("snop_input",), "AUX"),
    ".mexport": (("feos_aux",), "AUX"),
    ".cst": (("feos_aux",), "AUX"),
    ".par": (("feos_aux",), "AUX"),
    ".feos": (("feos_native", "multi_inverted_eos"), None),
    ".planck": (("multi_opacity",), "PLANCK"),
    ".ross": (("multi_opacity",), "ROSSELAND"),
    ".zeff": (("multi_opacity",), "ZEFF"),
    ".eps": (("multi_opacity",), "EMISSIVITY"),
    ".avsqfree": (("ledcop_zeff",), "ZEFF2"),
    ".nofree": (("ledcop_zeff",), "ZEFF"),
    ".multigroupopacity_planck": (("multi_opacity",), "PLANCK"),
    ".multigroupopacity_rosseland": (("multi_opacity",), "ROSSELAND"),
    ".grayopacity_planck": (("multi_opacity",), "PLANCK"),
    ".grayopacity_rosseland": (("multi_opacity",), "ROSSELAND"),
}

#: ★ **比路径规则更具体**的扩展名 —— 必须先于 ``hyades`` 路径规则判定。
#:
#: 为什么需要这一层（实测反例）：
#:
#:     hyades/sesame/eos_32.hug        ← Hugoniot 表，**不是** Hyades EOS
#:     hyades/qeos/qeos_392.dat.par    ← FEOS 参数文件，**不是** Hyades EOS
#:
#: 这两个文件都在 ``hyades/`` 目录下，但它们是**别的格式**。
#: 而 ``.feos`` 是 FEOS 工具**追加在原文件名后**的通用标记：
#:
#:     hyades/sesame/eos_41.dat.feos   ← 内容其实是标准 Hyades 布局
#:
#: 所以必须区分两档：
#:   * ``EXT_SPECIFIC``（本集合）—— 语义唯一、不可能有歧义的扩展名 → **优先**
#:   * 其余 ``EXT_MAP`` 项（如 ``.feos`` / ``.301``）—— 通用标记 → **让位给 hyades**，
#:     但仍追加到候选列表尾部作为回退
EXT_SPECIFIC = frozenset({
    ".inv",          # MULTI Inverted EOS（**不是** FEOS 导出）
    ".hug",          # Hugoniot
    ".cn4", ".cnr",  # IONMIX
    ".coldopacity",  # 冷不透明度（自描述两行表头）
    ".snop",         # SNOP 输入
    ".par", ".cst", ".mexport",   # FEOS 参数/导出
    ".avsqfree", ".nofree",        # LEDCOP 拆分件
    ".planck", ".ross", ".zeff", ".eps",   # MULTI 不透明度单群
    ".multigroupopacity_planck", ".multigroupopacity_rosseland",
    ".grayopacity_planck", ".grayopacity_rosseland",
})

#: 明确跳过的扩展名（非数值：文档 / 图片 / 脚本 / 电子表格 / 运行产物 / 说明）
_SKIP_EXT = frozenset({
    ".docx", ".doc", ".pdf", ".xls", ".xlsx", ".pptx", ".ppt",
    ".js", ".gif", ".png", ".jpg", ".jpeg", ".opj", ".xmind", ".db",
    ".html", ".htm", ".url",
    # 注册表 / 配置文件（不是 EOS/op 表，已由 registry 单独解析）
    ".xml", ".base", ".list", ".lck", ".ini.lock",
    # 说明文件（已由 AnnotationStore 作为伴随注释收录）
    ".info", ".inhalt", ".readme",
    # 运行产物 / 辅助导出 / 备份
    ".log", ".case", ".bak", ".ist", ".isc", ".ist4gnuplot", ".isc4gnuplot",
    ".cst", ".mexport",          # FEOS 辅助（由 feos_aux 按需处理，不作为栅格表）
})

#: 明确跳过的文件名（元数据 / 说明 / 校验）
_SKIP_NAMES = frozenset({
    "readme", "readme.txt", "modinfo", "filelist", "lock",
    "material.list", "material.base", "material.user", "checksum",
    "thumbs.db", "desktop.ini", "albedo.xml", "databaseindex.xml",
    "atomicweighttable.txt", "bulkmodulus.xlsx", "nofs",
    "opbe.inhalt", "snop.inhalt",
})

#: 文件名里含空格且像"说明句"的（实测：``Ta2O5_1G_MULTI from unknown source``、
#: ``No EOS data, but Opacity in OpacityThermos.txt``）→ 是笔记不是数据
_SKIP_NAME_HINTS = ("from unknown source", "no eos data", "coupling and electron")

#: 文件名 token → KIND（顺序敏感：先匹配更专门的）
NAME_TOKENS: tuple[tuple[re.Pattern[str], str | None], ...] = (
    (re.compile(r"_eos_e\b|_EOS_e\b|eos_?e\b|_ieeos", re.I), "EOS_ELECTRON"),
    (re.compile(r"_eos_i\b|_EOS_i\b|_ieos|_imi", re.I), "EOS_ION"),
    (re.compile(r"op0?3z\b|ZEFF|Zeff", re.I), "ZEFF"),
    (re.compile(r"AvSqFree", re.I), "ZEFF2"),
    (re.compile(r"op0?3p\b|PLANCK|Planck|_mopp|MOPP", re.I), "PLANCK"),
    (re.compile(r"op0?3r\b|ROSSELAND|ROSSLAN|Rosseland|_mopr|MOPR|WorkOp", re.I), "ROSSELAND"),
    (re.compile(r"op0?3e\b|_?EPS\b|EMISSIVITY", re.I), "EMISSIVITY"),
    (re.compile(r"\d+_(PLANCK|ROS+LAN?D?)\b", re.I), None),   # 由上面的 token 定
    (re.compile(r"NONLTE|NLTE", re.I), "NONLTE"),
    (re.compile(r"IDEAL_GAS|_EOS\b|_eos\b|_Z\b|_hug\b", re.I), "EOS_TOTAL"),
)

#: 文件名 token → 家族（当扩展名不足时）
NAME_FAMILY_TOKENS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^eos_\d+", re.I), "hyades_eos"),
    (re.compile(r"^qeos_\d+", re.I), "hyades_eos"),
    (re.compile(r"^opc_\d+", re.I), "hyades_opacity"),
    (re.compile(r"\.data\.txt$", re.I), "feos_tabdata"),
    # ★ 原先这里有 ``|\.INV$`` → 把 ``mat_CPC/AU.INV`` 误判成 feos_aux。
    #   实测该文件是 MULTI **Inverted** EOS（F1 布局，计数吻合）。
    #   ``.inv`` 已改由 EXT_MAP 处理（见上），此处只留真正的 FEOS 导出后缀。
    (re.compile(r"\.critical\.dat$|\.isobaric\.dat$", re.I), "feos_aux"),
    (re.compile(r"^\d+_\d{4}_|coldopac|coldopacity", re.I), "coldopacity"),
    # ★ F2 家族的名字特征（ZEFF / Planck / Rossland / EPS / WorkOp / NLTE / mopp / mopr）
    # 实测必需：``AL_ZEFF_multifs-1.2.dat``、``C.ZEFF``、``AU_SIMPLE_PLANCK_MG`` 等
    # 都靠这些 token 才能脱离 F1 的默认候选。
    (re.compile(r"zeff|op0?3[zpre]|planck|ros+lan|_mopp|_mopr|_?eps\b|workop|nlte",
                re.I), "multi_opacity"),
    (re.compile(r"ionpot|powerlaw|xraymass|reflectivity|crystal", re.I), "generic_curve"),
    (re.compile(r"_MULTI$|_MULTI\d*$", re.I), "multi_opacity"),
)

_DIGITS = re.compile(r"^(\d{4,})")


@dataclass
class DeclaredType:
    """一个文件的**声明式**类型判定结果。"""

    relpath: str
    families: list[str] = field(default_factory=list)   # 候选族，按声明顺序
    kind: str | None = None
    source: str = ""                  # extension | path | name_token | registry | companion | default
    evidence: str = ""
    mid: int | None = None
    material: str | None = None
    sesame_id: int | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def family(self) -> str | None:
        return self.families[0] if self.families else None

    @property
    def is_skipped(self) -> bool:
        return self.family == "skip"

    @property
    def is_unresolved(self) -> bool:
        return not self.families

    def describe(self) -> str:
        return (f"{self.relpath}: families={self.families} kind={self.kind} "
                f"src={self.source} ({self.evidence})")


# ── 单文件判定 ──────────────────────────────────────────────────
def _ext_of(fname: str) -> str:
    """扩展名（小写），**剥掉尾部下划线与空白**。

    ★ 实测：``Ta2O5/PowerLawTa2O5_EOS.SESAME_`` 尾部的 ``_`` 是 Windows
    文件复制冲突留下的后缀。若不剥，``.sesame`` 规则失配（``.sesame_`` 不在
    ``EXT_MAP`` 里），文件名 token ``powerlaw`` 就会抢到 ``generic_curve`` ——
    而该文件的内容是 **F1 反演 EOS**（计数 143 == ``4+2*3+19+2*3*19``，
    精确吻合）。
    """
    return os.path.splitext(fname)[1].lower().rstrip("_ \t")


def _is_compound_ext(fname: str) -> str | None:
    """识别 ``*.multiGroupOpacity_PLANCK`` 这类"复合扩展名"。"""
    low = fname.lower()
    for ext in EXT_MAP:
        if ext.count(".") > 1 and low.endswith(ext):
            return ext
    return None


def declare(relpath: str | Path, *, registry: MaterialRegistry | None = None,
            store: AnnotationStore | None = None) -> DeclaredType:
    """判定一个 ``matter++`` 相对路径的声明式类型。"""
    rel = str(relpath).replace("\\", "/").lstrip("/")
    fname = rel.split("/")[-1]
    low = fname.lower()
    ext = _ext_of(fname)
    dt = DeclaredType(relpath=rel)

    # 0) 跳过规则 -------------------------------------------------
    # ``#`` 前缀是**说明文件**（如 ``ATOMIC/#LEDCOP``、``### Generated by SNOP``），
    # 不是数据；它们已由 AnnotationStore 作为伴随注释收录。
    low_hint = low.lower()
    if (ext in _SKIP_EXT or low in _SKIP_NAMES or fname.startswith(("~$", "#"))
            or any(h in low_hint for h in _SKIP_NAME_HINTS)):
        dt.families = ["skip"]
        dt.source = "skip_rule"
        if fname.startswith("#"):
            dt.evidence = "companion note file (# prefix)"
        elif any(h in low_hint for h in _SKIP_NAME_HINTS):
            dt.evidence = "filename looks like a free-text note"
        else:
            dt.evidence = f"ext={ext or '(none)'} name={fname}"
        return dt

    # 1) 复合扩展名 -----------------------------------------------
    ext_fams: list[str] = []
    cext = _is_compound_ext(fname)
    if cext:
        fams, kind = EXT_MAP[cext]
        ext_fams = list(fams)
        dt.kind = kind
        dt.evidence = f"compound ext {cext}"

    # 2) 简单扩展名 -----------------------------------------------
    ext_specific = False
    if not ext_fams and ext in EXT_MAP:
        fams, kind = EXT_MAP[ext]
        ext_fams = list(fams)
        ext_specific = ext in EXT_SPECIFIC
        dt.kind = kind
        dt.evidence = f"ext {ext}"

    # 3) ★ Readme.txt 的**有序**链：hyades > .feos > .301/.304/.305 > default ──
    #    上游原文把「文件名和路径中有 hyades」列为**第一条**规则，而不是"扩展名
    #    优先于路径"。实测反例（这是踩过的坑）：
    #
    #        hyades/sesame/eos_41.dat.feos     ← 真实内容是 Hyades 5×15 布局
    #        hyades/qeos/qeos_392.dat.feos     （首行是 'Silicon LLNL QEOS…'，
    #                                            第 2 行是 id/zbar/abar/rho0/L）
    #
    #    若让 `.feos` 先命中，则声明 = ['feos_native']，两个候选都失败 →
    #    last_resort 退化成 generic_curve，**Hyades 布局信息全丢**
    #    （L 公式、Zbar/Abar、P/E 语义都没了）。
    #
    #    但 hyades 优先**不能无限上纲** —— 实测第二个反例：
    #
    #        hyades/sesame/eos_32.hug        ← Hugoniot 表（．hug 语义唯一）
    #        hyades/qeos/qeos_392.dat.par    ← FEOS 参数文件（．par 语义唯一）
    #
    #    所以先判 ``EXT_SPECIFIC``（语义唯一的具体扩展名），再判 hyades 路径。
    plow = rel.lower()
    if ext_specific:
        dt.families = ext_fams
        dt.source = "extension"
        dt.evidence = f"ext {ext} (specific, 优先于路径规则)"
        dt.notes.append(
            f"扩展名 {ext} 属 EXT_SPECIFIC，即使路径含 'hyades' 也优先")
    elif "hyades" in plow:
        if "/opacity/" in plow or low.startswith("opc_"):
            fams = ["hyades_opacity", "hyades_eos"]
        else:
            fams = ["hyades_eos", "sesame_dat", "hyades_opacity"]
        merged = fams + [f for f in ext_fams if f not in fams]
        dt.notes.append(
            f"Readme.txt rule #1: path contains 'hyades' → {fams}"
            + (f"（扩展名候选 {ext_fams} 已降级为回退）" if ext_fams else ""))
        dt.families = merged
        dt.source = "path"
        dt.evidence = "path contains 'hyades'"
    elif ext_fams:
        dt.families = ext_fams
        dt.source = "extension"
        dt.evidence = dt.evidence or f"ext {ext}"

    # 3b) 其它路径规则 --------------------------------------------
    if not dt.families:
        if "thermos" in plow:
            # ★ Thermos 目录里不只有 Z̄/不透明度，还有**理想气体 EOS**：
            #     Thermos/mat_Mo/Mo_Ideal_Gas   L0 = [0.1234567, 10.22, 2, 2]
            #     Thermos/mat_U/U_IdealGas_EOS  L0 = [0.1234567, 19.1,  2, 2]
            #   两个第 2 字段正好是 Mo / U 的**实测固体密度**（10.22 / 19.1），
            #   计数 18 == F1/with_e0(2,2)，与 doc 里 AU_IDEAL_GAS 的布局逐一对应
            #   → 它们是 F1 理想气体表，不是不透明度。
            dt.families = ["multi_opacity", "multi_inverted_eos", "generic_curve"]
            dt.source = "path"
            dt.evidence = "path contains 'Thermos'"
        elif "atomics" in plow or "atomic" in plow:
            dt.families = ["ledcop_atomic", "ledcop_zeff", "multi_opacity"]
            dt.source = "path"
            dt.evidence = "path contains 'ATOMIC'"
        elif "ionmix" in plow:
            dt.families = ["ionmix"]
            dt.source = "path"
            dt.evidence = "path contains 'Ionmix'"
        elif "coldopacity" in plow:
            dt.families = ["coldopacity"]
            dt.source = "path"
            dt.evidence = "path contains 'ColdOpacity'"

    # 4) 文件名 token（家族） -------------------------------------
    if not dt.families:
        for rx, fam in NAME_FAMILY_TOKENS:
            if rx.search(fname):
                dt.families = [fam]
                dt.source = "name_token"
                dt.evidence = f"name matches {rx.pattern}"
                break

    # 5) 默认候选（Readme.txt：「其他按照默认的 SESAME 数据库格式」） ──
    if not dt.families:
        dt.families = ["multi_inverted_eos", "multi_opacity", "sesame_dat"]
        dt.source = "default"
        dt.evidence = "Readme.txt default (SESAME 4x15)"

    # 6) KIND（token 优先于扩展名；注册表可覆盖） ------------------
    if dt.kind is None:
        for rx, kind in NAME_TOKENS:
            if kind and rx.search(fname):
                dt.kind = kind
                dt.notes.append(f"kind from name token {rx.pattern} -> {kind}")
                break

    # 7) 注册表：直接给出 KIND + 材料 ------------------------------
    if registry is not None:
        refs = registry.base.refs_for_file(rel)
        if refs:
            keys = [r.key for r in refs]
            dt.notes.append(f"material.base refs: {','.join(keys)}")
            primary = None
            for k in keys:
                if k.upper() in ("EOS", "EOS_TOTAL"):
                    primary = "EOS_TOTAL"
                    break
            if primary is None:
                primary = refs[0].kind
            dt.kind = primary if primary else dt.kind
            dt.source = dt.source or "registry"
            dt.evidence += " | in material.base"
        owners = registry.for_file(rel)
        if owners:
            dt.mid = owners[0].mid
            dt.material = owners[0].label

    # 8) 伴随注释文件：IME/IMI 等声明 ----------------------------
    if store is not None:
        anns = store.for_file(rel)
        for a in anns:
            if a.dims.get("IME") and dt.kind == "EOS_ELECTRON":
                dt.notes.append(f"companion declared IME={a.dims['IME']}")
            if a.dims.get("IMI") and dt.kind == "EOS_ION":
                dt.notes.append(f"companion declared IMI={a.dims['IMI']}")

    # 9) SESAME 表号 → KIND（交叉校验，不覆盖已有判定） ------------
    m = _DIGITS.match(fname)
    if m:
        dt.sesame_id = int(m.group(1))
        sk = kind_from_sesame_id(dt.sesame_id)
        if sk:
            dt.notes.append(f"sesame digit -> {sk}")
            if dt.kind is None:
                dt.kind = sk

    return dt


# ── 共享注册表（避免重复构建） ──────────────────────────────────
_REGISTRY_CACHE: MaterialRegistry | None = None
_STORE_CACHE: AnnotationStore | None = None


def default_registry() -> tuple[MaterialRegistry, AnnotationStore]:
    """构建（或复用）默认的注册表与注释索引。

    注册表与注释索引都要遍历全树，构建一次后缓存复用。
    """
    global _REGISTRY_CACHE, _STORE_CACHE
    if _STORE_CACHE is None:
        _STORE_CACHE = AnnotationStore().build()
    if _REGISTRY_CACHE is None:
        # 注释索引已单独缓存，MaterialRegistry 不必重复构建
        _REGISTRY_CACHE = MaterialRegistry(build_annotations=False)
    return _REGISTRY_CACHE, _STORE_CACHE


# ── 全量扫描 ────────────────────────────────────────────────────
def iter_source_files(matter_dir: str | Path | None = None):
    """遍历 ``matter++`` 下全部文件，返回相对路径（POSIX 风格）。"""
    root = Path(matter_dir or config.MATTER_DIR)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fname in sorted(filenames):
            abs_p = os.path.join(dirpath, fname)
            yield os.path.relpath(abs_p, root).replace("\\", "/")


def scan_declared(matter_dir: str | Path | None = None, *,
                  registry: MaterialRegistry | None = None,
                  store: AnnotationStore | None = None) -> list[DeclaredType]:
    """对全树做声明式类型扫描。"""
    if registry is None or store is None:
        reg, sto = default_registry()
        registry = registry or reg
        store = store or sto
    return [declare(rel, registry=registry, store=store)
            for rel in iter_source_files(matter_dir)]
