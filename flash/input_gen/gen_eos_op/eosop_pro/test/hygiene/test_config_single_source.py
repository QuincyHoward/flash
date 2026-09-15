"""``config`` 单一常量来源测试 —— **禁止硬编码**。

为什么必须有一个测试守住它
--------------------------
用户的项目纪律明写：

> **偏好统一配置管理与接口优先方案，禁止硬编码与跨模块调用**

"禁止硬编码"如果只写在文档里，两周后就会有人（包括我自己）在某个解析器里
写一个 `1e-2` 当 GPa→Mbar 的换算。这种错误**不会让任何测试失败** ——
两个 `1e-2` 恰好相等，结果完全正常，直到有人改了一处没改另一处。

所以这里用**源码级**检查把它变成会失败的测试：

1. 用 ``ast`` 解析 ``eosop_pro/`` 下每个模块；
2. 收集所有 ``ast.Constant`` 里的 **float 字面量**；
3. 与 ``config.py`` 里的换算常量逐一比对（相对容差 1e-9）；
4. 命中即失败，并指出文件、行号、常量名。

★ 用 ``ast`` 而不是正则，是因为 ``ast`` **天然跳过 docstring 与注释**
（它们是 ``str`` 常量，不是 ``float``）。所以文档里写 "``≈ eV / 8.617e-5``"
这种说明文字不会误报 —— 这很重要，否则为了过测试就不能在注释里解释物理。
"""

import ast
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

from eosop_pro import config

#: 必须单一来源的换算常量（名称 → 值），分两档
#:
#: ★ 为什么要分档：``1e-2`` 这种"整数幂次"的值在别处**合法存在**
#: （实测：``qa_plots.plot_eos_isobars(densities=(0.01, 0.1, ...))`` 里的
#: 0.01 是"要画哪几条等密度线"，与 GPa→Mbar 毫无关系）。
#: 只按值匹配会产生假阳性，进而让人把检查关掉 —— 那还不如没有检查。
#:
#: 分档规则：
#: * **distinctive**：有效数字多位、不可能巧合（`8.617333262e-5`、`6.02214076e23`、
#:   `1.66053906660e-24`）→ **值匹配即失败**
#: * **round**：整数幂次，可能巧合（`1e-2`、`1e-3`、`1e9`、`1e12`）
#:   → **值匹配 且 同行出现单位词** 才失败
DISTINCTIVE = {
    "EV_PER_K": config.EV_PER_K,
    "N_A": config.N_A,
    "AMU_G": config.AMU_G,
}

ROUND = {
    "MBAR_PER_GPA": config.MBAR_PER_GPA,
    "MBAR_CM3_G_PER_MJ_KG": config.MBAR_CM3_G_PER_MJ_KG,
    "ERG_G_PER_MBAR_CM3_G": config.ERG_G_PER_MBAR_CM3_G,
    "DYN_CM2_PER_MBAR": config.DYN_CM2_PER_MBAR,
    "KEV_PER_EV": config.KEV_PER_EV,
}

#: 出现这些词，说明那一行在做**单位换算**（而不是在设参数）
UNIT_TOKENS = ("GPa", "MJ", "Mbar", "mbar", "dyne", "erg", "keV", "eV",
               "Kelvin", "cm2/g", "cm3/g", "amu", "N_A")

#: 允许出现这些字面量的文件（config.py 自身）
ALLOW = {
    "config.py",
}


def _iter_modules(root: Path):
    for p in sorted(root.rglob("*.py")):
        if p.name in ALLOW:
            continue
        yield p


def _float_literals(path: Path) -> list[tuple[int, float]]:
    """返回 ``[(lineno, value), ...]``，**不含 docstring / 注释**。

    ★ 必须去重 ``-0.01``：AST 里它同时是
    ``UnaryOp(USub, Constant(0.01))`` —— 直接 ``ast.walk`` 会把
    ``Constant(0.01)`` 与 ``-0.01`` 各收一次（这是第一版踩的坑）。
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    neg_operands: set[int] = set()
    out: list[tuple[int, float]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) \
                and isinstance(node.operand, ast.Constant) \
                and isinstance(node.operand.value, (int, float)):
            neg_operands.add(id(node.operand))
            out.append((node.lineno, -float(node.operand.value)))
    for node in ast.walk(tree):
        if id(node) in neg_operands:
            continue
        if isinstance(node, ast.Constant) \
                and isinstance(node.value, float) \
                and not isinstance(node.value, bool):
            out.append((node.lineno, node.value))
    return out


def _same(a: float, b: float) -> bool:
    return (b != 0 and abs(a - b) <= abs(b) * 1e-9) or (a == 0 and b == 0)


def test_no_conversion_constant_hardcoded_outside_config():
    """★ 核心断言：换算常量不得在 ``config.py`` 之外以字面量出现。

    两档规则见 ``DISTINCTIVE`` / ``ROUND`` 的注释。
    """
    pkg = Path(config.PACKAGE_ROOT)
    hits: list[str] = []
    for mod in _iter_modules(pkg):
        lines = mod.read_text(encoding="utf-8").splitlines()
        for lineno, val in _float_literals(mod):
            src_line = lines[lineno - 1] if 0 < lineno <= len(lines) else ""

            for name, ref in DISTINCTIVE.items():
                if _same(val, ref):
                    hits.append(f"{mod.relative_to(pkg).as_posix()}:{lineno} "
                                f"value={val!r} == config.{name}（distinctive）")

            for name, ref in ROUND.items():
                if _same(val, ref) and any(tok in src_line for tok in UNIT_TOKENS):
                    hits.append(f"{mod.relative_to(pkg).as_posix()}:{lineno} "
                                f"value={val!r} == config.{name}"
                                f"（同行含单位词）\n      {src_line.strip()}")
    expect(not hits,
           "发现硬编码的换算常量（请改用 config.<NAME>）：\n  "
           + "\n  ".join(hits))


def test_distinctive_and_round_disjoint():
    """两档不得重叠，否则分档规则自相矛盾。"""
    for n1, v1 in DISTINCTIVE.items():
        for n2, v2 in ROUND.items():
            expect(not _same(v1, v2),
                   f"{n1} 与 {n2} 值相同，分档失效")


def test_round_tier_does_not_false_positive_on_plot_defaults():
    """★ 回归：``densities=(0.01, 0.1, 1.0, 10.0)`` 这类**参数**不该被误报。"""
    src = (Path(config.PACKAGE_ROOT) / "plotting" / "qa_plots.py") \
        .read_text(encoding="utf-8")
    expect("densities=(0.01" in src or "densities=(" in src,
           "样本前提变了：qa_plots 应含 densities 默认参数")
    # 该行的 0.01 不含单位词 → round 档不应命中
    for ln in src.splitlines():
        if "densities=" in ln:
            expect(not any(tok in ln for tok in UNIT_TOKENS),
                   f"该行意外含单位词，回归前提失效: {ln.strip()}")


def test_ast_scan_skips_docstrings():
    """★ 证明扫描器不会误伤文档里的数值说明（否则注释就没法写物理了）。"""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "m.py"
        p.write_text(
            '"""docstring mentions 1e-2 and 8.617333262e-5 but is a str."""\n'
            "# comment 0.01\n"
            "x: float = 0.01\n"
            "y: float = -0.01\n",
            encoding="utf-8")
        lits = _float_literals(p)
        values = sorted(v for _ln, v in lits)
        expect_eq(values, [-0.01, 0.01],
                  "只应取到代码里的字面量，不含 docstring/注释")


def test_banned_values_are_actually_in_config():
    """白名单里的值必须真的来自 config（防止测试本身被绕过）。"""
    for name, ref in list(DISTINCTIVE.items()) + list(ROUND.items()):
        expect(hasattr(config, name), f"config 缺少 {name}")
        expect_eq(getattr(config, name), ref, f"config.{name} 值不一致")


def test_matter_helper_asserts_existence():
    """``config.MATTER`` 必须断言存在 —— 测试要引用**真实源文件**。"""
    p = config.MATTER("mat_Al-1.0/AL_eos")
    expect(p.exists(), f"应解析出真实路径: {p}")
    try:
        config.MATTER("definitely/not/here.dat")
    except FileNotFoundError as exc:
        expect_in("matter++ source not found", str(exc))
    else:
        raise AssertionError("不存在的路径应抛 FileNotFoundError")


def test_matter_rel_is_posix_style():
    rel = config.matter_rel(config.MATTER("mat_Al-1.0/AL_eos"))
    expect_eq(rel, "mat_Al-1.0/AL_eos")
    expect("\\" not in rel, "相对路径必须用 POSIX 斜杠（跨平台一致）")


def test_config_has_no_project_absolute_path_literals():
    """config.py 里不得出现写死的盘符路径 —— 必须由层级推导或环境变量给。"""
    src = (Path(config.PACKAGE_ROOT) / "config.py").read_text(encoding="utf-8")
    code_lines = [ln for ln in src.splitlines()
                  if not ln.lstrip().startswith("#")]
    code = "\n".join(code_lines)
    for bad in ("E:\\PhySimX", "E:/PhySimX", "C:\\Users"):
        expect(bad not in code,
               f"config.py 不应写死绝对路径 {bad!r}（层级推导/环境变量代替）")


def test_env_override_is_wired():
    """任一 ``MULTI_EOSOP_*`` 环境变量都应能生效（这里验 3 个）。"""
    import importlib
    import os

    keys = {"MULTI_EOSOP_N_X_UNIFIED": ("N_X_UNIFIED", 111),
            "MULTI_EOSOP_EXTRAPOLATION": ("EXTRAPOLATION", "clamp"),
            "MULTI_EOSOP_TE_MIN": ("TE_MIN_EV", 0.5)}
    for env_key, (attr, val) in keys.items():
        old = os.environ.get(env_key)
        os.environ[env_key] = str(val)
        try:
            mod = importlib.reload(importlib.import_module("eosop_pro.config"))
            got = getattr(mod, attr)
            if isinstance(val, float) or isinstance(got, float):
                expect_eq(float(got), float(val), f"{attr} 未被 {env_key} 覆盖")
            else:
                expect_eq(got, val, f"{attr} 未被 {env_key} 覆盖")
        finally:
            if old is None:
                os.environ.pop(env_key, None)
            else:
                os.environ[env_key] = old
    # 还原
    importlib.reload(importlib.import_module("eosop_pro.config"))


def test_output_dirs_helper_is_idempotent():
    config.ensure_output_dirs()
    config.ensure_output_dirs()      # 第二次不应报错
    for d in (config.H5_DIR, config.REPORTS_DIR, config.PLOTS_DIR,
              config.LOGS_DIR, config.INFERENCE_DIR):
        expect(d.is_dir(), f"{d} 应存在")


def test_annotation_and_skip_configs_are_frozensets_for_lookup():
    expect(isinstance(config.SKIP_EXTENSIONS, frozenset))
    expect(isinstance(config.SKIP_FILENAMES, frozenset))
    expect(isinstance(config.ANNOTATION_NAMES, frozenset))
    expect(".docx" in config.SKIP_EXTENSIONS)
    expect("readme" in config.SKIP_FILENAMES)


def test_doc_scan_gates_present():
    """文档抽取的三道闸门阈值必须在 config 里（不得在 docsrc 里写死）。"""
    for name in ("DOC_SCAN_ROOTS", "DOC_MAX_BYTES", "DOC_TXT_MAX_BYTES",
                 "DOC_NUMERIC_SAMPLE", "DOC_NUMERIC_RATIO",
                 "DOC_EXTENSIONLESS", "DOC_ALLOWLIST"):
        expect(hasattr(config, name), f"config 缺少 {name}")
    expect(config.DOC_MAX_BYTES > 0)
    expect(0 < config.DOC_NUMERIC_RATIO <= 1)


def test_unified_grid_ids_declared_once():
    expect_eq(tuple(config.UNIFIED_GRID_IDS), ("rho_Te", "nion_Te"))
    # 后补的 nele_Te 不在本轮范围
    expect("nele_Te" not in config.UNIFIED_GRID_IDS)


if __name__ == "__main__":
    raise SystemExit(main(globals()))
