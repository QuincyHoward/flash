"""eosop_pro 配置 —— 唯一常量来源。

本模块是全项目**唯一**允许出现路径、阈值、网格参数、压缩参数与跳过规则的地方。
其他模块一律 ``from .. import config`` / ``from eosop_pro import config`` 取值，
不得自行硬编码。

可用 ``MULTI_EOSOP_*`` 环境变量覆盖任意项（见 :func:`_env`）。

目录事实（实测）
----------------
::

    W  = E:\\PhySimX\\PhySimX\\simulation\\Multi\\MultixD      ← git 仓库根
    W\\MultixD\\src\\Multi1D++Portable20241128\\matter++      ← 源数据（2211 文件 / 1567 MB）
    W\\MultixD\\eosop_pro                                   ← 本项目目录
    W\\MultixD\\eosop_pro\\eosop_pro\\config.py            ← 本文件
"""

from __future__ import annotations

import os
from pathlib import Path


def _env(name: str, default: str) -> str:
    return os.environ.get(f"MULTI_EOSOP_{name}", default)


# ── 层级推导 ──────────────────────────────────────────────────
PACKAGE_ROOT = Path(__file__).resolve().parent            # .../eosop_pro/eosop_pro
PROJECT_ROOT = PACKAGE_ROOT.parent                        # .../eosop_pro
MULTIXD_INNER = PROJECT_ROOT.parent                       # .../MultixD
WORKSPACE_ROOT = MULTIXD_INNER.parent                     # .../MultixD (仓库根)

# ── 源数据位置 ────────────────────────────────────────────────
MULTI_HOME = Path(
    _env("MULTI_HOME", str(MULTIXD_INNER / "src" / "Multi1D++Portable20241128"))
)
MATTER_DIR = Path(_env("MATTER_DIR", str(MULTI_HOME / "matter++")))
MATLAB_DIR = MULTI_HOME / "matlab"
DOC_DIR = MULTI_HOME / "doc"
TABELLE_DIR = MULTI_HOME / "tabelle"

# ── 产物位置 ──────────────────────────────────────────────────
OUTPUTS_DIR = Path(_env("OUTPUTS_DIR", str(PROJECT_ROOT / "outputs")))
H5_DIR = OUTPUTS_DIR / "h5"
H5_UNINDEXED_DIR = H5_DIR / "_unindexed"
REPORTS_DIR = OUTPUTS_DIR / "reports"
PLOTS_DIR = OUTPUTS_DIR / "plots"
LOGS_DIR = OUTPUTS_DIR / "logs"
INFERENCE_DIR = REPORTS_DIR / "inference_reports"

DOCS_DIR = PROJECT_ROOT / "docs"
EXTRACTED_DIR = DOCS_DIR / "extracted"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
TEST_DIR = PROJECT_ROOT / "test"

# ── 文档抽取（docsrc） ────────────────────────────────────────
#: 默认扫描根。★ 刻意**不**用整个 MULTI_HOME：``matter++/ATOMIC/Al.txt``
#: 是 13.5 MB 的数值表，按扩展名会被误当文档吞进来。
DOC_SCAN_ROOTS = (DOC_DIR, MATTER_DIR)
#: 结构化容器（docx/pptx/xlsx/pdf/xmind）体积上限；超限几乎必是数据
DOC_MAX_BYTES = int(_env("DOC_MAX_BYTES", "12000000"))
#: 纯文本候选体积上限（Readme/说明一般都 < 100 KB）
DOC_TXT_MAX_BYTES = int(_env("DOC_TXT_MAX_BYTES", "262144"))
#: 「文档 vs 数值数据」判定：采样行数 与 payload 行占比阈值
DOC_NUMERIC_SAMPLE = int(_env("DOC_NUMERIC_SAMPLE", "400"))
DOC_NUMERIC_RATIO = float(_env("DOC_NUMERIC_RATIO", "0.5"))
#: 无扩展名但确系说明文件的名单（``doc/multi1d7.6/{README,manual,history,examples}``）
DOC_EXTENSIONLESS = frozenset({
    "readme", "manual", "history", "examples", "modinfo", "install",
    "license", "changes", "changelog", "notes", "info", "release",
})
#: 内容几乎是纯数字、但**确实是规格说明**的文件（数值闸门的白名单）
DOC_ALLOWLIST = frozenset({
    "structure_of_ascii_data_files.txt",
})

# ── 已知注册表文件（材料注册表三源） ──────────────────────────
MATERIAL_BASE = MATTER_DIR / "material.base"
MATERIAL_USER = MATTER_DIR / "material.user"
DATABASE_INDEX = MATTER_DIR / "DatabaseIndex.xml"
MATTER_README = MATTER_DIR / "Readme.txt"
EOS_LIST = MATTER_DIR / "hyades" / "EOS.list"
OPACITY_LIST = MATTER_DIR / "hyades" / "Opacity.list"
THERMOS_README = MATTER_DIR / "Thermos" / "Readme.txt"

# ── 编码链（按顺序试解，latin-1 永不失败） ───────────────────
# 实测：matter++/Readme.txt 是 GB18030 中文；12 个文件非 UTF-8；26 个带 BOM。
ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "latin-1")

# ── 文本卫生 ──────────────────────────────────────────────────
BOM = "\ufeff"
NUL_BYTE = b"\x00"

# ── 物理包络（单位反演与自洽性校验；全部可配置并在报告中打印） ──
RHO_MIN_G_CM3 = float(_env("RHO_MIN", "1e-8"))
RHO_MAX_G_CM3 = float(_env("RHO_MAX", "1e6"))
TE_MIN_EV = float(_env("TE_MIN", "1e-2"))
TE_MAX_EV = float(_env("TE_MAX", "1e6"))
P_MIN_MBAR = float(_env("P_MIN", "1e-12"))
P_MAX_MBAR = float(_env("P_MAX", "1e12"))

# ── 单位反演兜底阈值（实测两组无重叠） ───────────────────────
LOG_T_EV_IF_GE = float(_env("LOG_T_EV_IF_GE", "4.5"))
LOG_T_KEV_IF_LE = float(_env("LOG_T_KEV_IF_LE", "2.5"))

# ── 物理常量 ──────────────────────────────────────────────────
N_A = 6.02214076e23          # mol^-1
EV_PER_K = 8.617333262e-5    # eV/K
K_PER_EV = 1.0 / EV_PER_K
KEV_PER_EV = 1e-3
MBAR_PER_GPA = 1e-2          # 1 GPa = 1e-2 Mbar
MBAR_CM3_G_PER_MJ_KG = 1e-2  # 1 MJ/kg = 1e-2 Mbar*cm^3/g
ERG_G_PER_MBAR_CM3_G = 1e9   # 1 Mbar*cm^3/g = 1e9 erg/g
DYN_CM2_PER_MBAR = 1e12      # 1 Mbar = 1e12 dyne/cm^2
AMU_G = 1.66053906660e-24    # g

# ── 统一网格 ──────────────────────────────────────────────────
N_X_UNIFIED = int(_env("N_X_UNIFIED", "128"))
N_TE_UNIFIED = int(_env("N_TE_UNIFIED", "128"))
UNIFIED_SPACING = "log10"
UNIFIED_GRID_IDS = ("rho_Te", "nion_Te")   # 本轮两套；(n_ele,Te) 后补
UNIFIED_GRID_FALLBACK = {
    "rho_Te": (RHO_MIN_G_CM3, RHO_MAX_G_CM3),
    "nion_Te": (RHO_MIN_G_CM3, RHO_MAX_G_CM3),   # 初值按 rho 范围，按材料 A 换算
}

# ── 插值 ──────────────────────────────────────────────────────
INTERP_METHOD = "bilinear_log10"
EXTRAPOLATION = _env("EXTRAPOLATION", "nan")           # nan | clamp | linear
MONOTONIC_ATOL = 1e-12
MONOTONIC_POLICY = _env("MONOTONIC_POLICY", "error")   # error | average | keep_last

# ── HDF5 ──────────────────────────────────────────────────────
SCHEMA_VERSION = "1.0"
TOOL_VERSION = "eosop_pro 0.1.0"
H5_COMPRESSION = "gzip"
H5_COMPRESSION_OPTS = 4
H5_SHUFFLE = True
H5_CHUNK_MAX = 64
FLOAT_DTYPE = "f8"
NAN_SEMANTICS = "out_of_range"
AXIS_ORDER = ("Te_eV", "x")

# ── 布局反演尺寸上限 ─────────────────────────────────────────
DIM_MIN = 2
DIM_MAX = 50000

# ── 非数值文件跳过规则（跳过但登记） ─────────────────────────
SKIP_EXTENSIONS = frozenset({
    ".docx", ".doc", ".pdf", ".xls", ".xlsx", ".pptx", ".ppt",
    ".js", ".gif", ".png", ".jpg", ".jpeg", ".opj", ".xmind", ".db",
})
SKIP_FILENAMES = frozenset({
    "readme", "readme.txt", "modinfo", "filelist", "lock",
    "material.list", "checksum", "thumbs.db", "desktop.ini",
})
SKIP_PREFIXES = ("~$",)

# ── 注释 / 伴随文件 ──────────────────────────────────────────
ANNOTATION_SUFFIXES = (".info", ".inhalt", ".readme")
ANNOTATION_NAMES = frozenset({"readme", "readme.txt", "modinfo"})
ANNOTATION_PREFIXES = ("#",)

# ── 绘图样式（PPT / 演讲级，全英文） ─────────────────────────
# ⚠️ 规约：**任何字体大小必须 > 18pt**（用户既定要求）。故所有字号皆 >= 20，
#    其中 legend 曾为 18（等于而非大于），2026-09-14 修正为 20。
#    守护测试：test/eosopdata/families/test_family_plots.py::
#              test_plot_style_constants_meet_ppt_requirements
PLOT_DPI = 450
PLOT_TITLE_FONTSIZE = 26
PLOT_LABEL_FONTSIZE = 22
PLOT_TICK_FONTSIZE = 20
PLOT_LEGEND_FONTSIZE = 20
PLOT_LINEWIDTH = 2.4
PLOT_MARKERSIZE = 8
PLOT_FIGSIZE = (8.0, 6.0)
PLOT_CMAP = "viridis"


def ensure_output_dirs() -> None:
    """确保所有输出目录存在（幂等）。"""
    for d in (H5_DIR, H5_UNINDEXED_DIR, REPORTS_DIR, PLOTS_DIR, LOGS_DIR, INFERENCE_DIR):
        d.mkdir(parents=True, exist_ok=True)


def MATTER(relpath: str) -> Path:
    """把 ``matter++`` 下的相对路径解析为绝对路径，并断言其存在。

    测试与解析器统一用它引用**真实源文件**（不复制数据）。
    """
    p = (MATTER_DIR / relpath.replace("\\", "/")).resolve()
    if not p.exists():
        raise FileNotFoundError(f"matter++ source not found: {relpath} -> {p}")
    return p


def matter_rel(path: str | Path) -> str:
    """把绝对路径转成相对 ``matter++`` 的 POSIX 风格相对路径。"""
    p = Path(path).resolve()
    try:
        return p.relative_to(MATTER_DIR.resolve()).as_posix()
    except ValueError:
        return p.as_posix()
