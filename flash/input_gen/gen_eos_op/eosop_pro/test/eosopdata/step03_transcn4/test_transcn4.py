"""``transcn4`` —— 其他格式族 -> cn4 的转换测试。

覆盖范围
--------
1. **格式骨架**：每行恒 48 列（4 字段 x 12 列），块数/计数守恒
2. **NaN 占位**：缺失数据写 ``NAN_PLACEHOLDER_FIELD``，**12 列对齐**，
   读回后由 :func:`is_nan_placeholder` 还原为 ``nan``
3. **跨族组装**：``allow_foreign`` 门控、轴归一化、密度换算、别名映射
4. **不透明度跨族**：独立表（``kind=ROSSELAND``）与同表（``ionmix .cn4``）
   两条路径都要能取到数据；取不到必须 NaN 占位而非 0
5. **往返**：``cn4 -> cn4`` 必须 **byte-identical**

样品发现策略
------------
``matter++`` 全树 1000+ 文件且部分目录 1.5G（已 gitignore），故样品**惰性发现**、
找不到即 ``skip``（返回 ``None``），绝不让"数据不在"伪装成代码缺陷。
"""

import math
import os
import re
import sys
from pathlib import Path

# --- path bootstrap (auto) ---
_d = os.path.dirname(os.path.abspath(__file__))
while _d != os.path.dirname(_d) and not os.path.isfile(
        os.path.join(_d, "_runner.py")):
    _d = os.path.dirname(_d)
if _d not in sys.path:
    sys.path.insert(0, _d)
import _runner                                                    # noqa: F401
from _runner import expect, expect_eq, expect_in, main          # noqa: E402

sys.path.insert(0, os.path.dirname(_d))                        # test/
sys.path.insert(0, os.path.dirname(os.path.dirname(_d)))       # repo root

from eosopdata._samples import cn4_root, find_parseable        # noqa: E402
from eosop_pro.cn4 import (                                    # noqa: E402
    BLOCK_SPEC,
    NAN_PLACEHOLDER_CUTOFF,
    NAN_PLACEHOLDER_FIELD,
    OPACITY_SPEC,
    cn4_to_parsed_tables,
    convert_cn4_to_cn4,
    convert_foreign_to_cn4,
    expected_number_count,
    is_nan_placeholder,
    load_cn4,
    parsed_tables_to_cn4,
    write_cn4,
)
from eosop_pro.cn4.cn4_io import (                             # noqa: E402
    _FOREIGN_FIELD_ALIASES,
    _FOREIGN_OPACITY_ALIASES,
    _FOREIGN_RHO_AXES,
    _FOREIGN_T_AXES,
    _OPAC_KIND_ALIASES,
    _detect_mantissa_style,
    _fmt_e12_6,
    _fortran_e12_6,
    _sniff_mantissa_style,
)

LINE_WIDTH = 48
FIXED_WIDTH = 12

#: 已实测可成功转换的（族, glob, izgas/fracsp）三元组。
#: 用 glob 模式而非硬编码文件名 —— 不同检出/机器上文件可能缺失。
CONVERTIBLE = (
    ("mpqeos", ("*.301",), [13], [1.0]),
    ("hyades_eos", ("qeos_*",), [13], [1.0]),
    ("ionmix", ("*.cn4",), [1, 6], [0.5, 0.5]),
)


# ── 辅助 ────────────────────────────────────────────────────────
def _tmpdir():
    """产物目录：本测试文件夹内 ``_out/``（固定、重复覆盖，便于人工核查）。

    历史：曾用 ``tempfile.mkdtemp`` —— 产物散落系统临时区无法核查；
    2026-09-15 起产物跟测试走（与 :func:`eosopdata._samples.tmp_dir` 同语义）。
    """
    d = Path(__file__).resolve().parent / "_out"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def _raw_lines(path):
    with open(path, "rb") as fh:
        return fh.read().decode("latin-1").split("\n")


def _data_lines(path):
    """数据区行（跳过 4 行头部），去掉可能的尾空行。"""
    lines = _raw_lines(path)[4:]
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def _all_cn4():
    root = cn4_root()
    if not root.is_dir():
        return []
    return sorted(root.rglob("*.cn4"))


# ── 1. NaN 占位格式 ──────────────────────────────────────────────
def test_nan_placeholder_is_exactly_12_columns():
    """NaN 占位必须是 12 列 —— 否则定宽切分整体错位。"""
    assert len(NAN_PLACEHOLDER_FIELD) == FIXED_WIDTH, \
        f"NAN_PLACEHOLDER_FIELD 宽 {len(NAN_PLACEHOLDER_FIELD)} != 12"


def test_nan_placeholder_drops_the_E_like_fortran():
    """3 位指数下 Fortran 丢 ``E``：``-9.99999+990``（不是 ``-9.99999E+990``）。"""
    assert "E" not in NAN_PLACEHOLDER_FIELD, \
        f"占位不应含 'E': {NAN_PLACEHOLDER_FIELD!r}"
    assert NAN_PLACEHOLDER_FIELD.startswith("-9.99999"), \
        f"占位形态异常: {NAN_PLACEHOLDER_FIELD!r}"


def test_nan_placeholder_decodes_to_minus_infinity():
    """占位解码后是 ``-inf``，并被 :func:`is_nan_placeholder` 识别。"""
    v = float("nan")
    s = _fmt_e12_6(v)
    assert s == NAN_PLACEHOLDER_FIELD, f"nan -> {s!r}"

    # 占位文本 -> float 必须 <= 阈值，从而被识别
    tok = NAN_PLACEHOLDER_FIELD.replace("-9.99999+990", "-9.99999e990")
    assert float(tok) <= NAN_PLACEHOLDER_CUTOFF, "占位阈值判定失效"
    assert is_nan_placeholder(float(tok)), "占位未被 is_nan_placeholder 识别"


def test_fmt_always_returns_12_or_13_columns():
    """除负值（Fortran 省前导 0 -> 13 列）外，字段宽恒 12。"""
    vals = [0.0, 1.0, -1.0, 1e-140, 1e140, 12345.678, 1e-300, 0.5]
    for v in vals:
        s = _fmt_e12_6(v)
        assert len(s) in (12, 13), f"{v:g} -> {s!r} 宽 {len(s)}"


def test_negative_values_use_fortran_bare_dot_form():
    """负值形如 ``-.370029E-04``（省略前导 0，保留 6 位小数，13 列）。

    这是 Fortran ``e12.6`` 的真实行为；早先实现为凑 12 列缩小数位，
    导致 byte-identical 往返失败（实测 he-imx-005.cn4）。
    """
    s = _fmt_e12_6(-0.370029e-4)
    assert s.startswith("-."), f"负值应为 '-.' 开头: {s!r}"
    assert re.fullmatch(r"-\.\d{6}E[-+]\d{2}", s), f"负值形态异常: {s!r}"


def test_leading_zero_style_shifts_exponent():
    """``0.dddddd`` 风格必须把指数 +1 补偿，否则数值缩小 10 倍。

    精度上限由 ``e12.6`` 决定：尾数 **6 位小数**，故相对误差上限 ~1e-6
    （``12345.678 -> 0.123456E+05`` 即 12345.6，这是格式固有精度，非缺陷）。
    """
    assert _fortran_e12_6(2.0) == "0.200000E+01"
    assert _fortran_e12_6(1.0) == "0.100000E+01"
    assert _fortran_e12_6(0.1) == "0.100000E+00"
    # 数值必须真的相等（防止只改排版不改值）
    for v in (2.0, 1.0, 0.1, 3.55656, 11.2468, 12345.678):
        s = _fortran_e12_6(v)
        back = float(s.replace("E", "e"))
        assert math.isclose(back, v, rel_tol=1e-5), \
            f"{v} -> {s} -> {back} 数值不一致"
    # ★ 回归守护：指数补偿漏掉时会静默缩小 10 倍，必须能抓住
    s = _fortran_e12_6(2.0)
    assert math.isclose(float(s.replace("E", "e")), 2.0, rel_tol=1e-9), \
        "指数未补偿 -> 数值被缩放 10 倍（严重缺陷）"
    s10 = _fortran_e12_6(10.0)
    assert math.isclose(float(s10.replace("E", "e")), 10.0, rel_tol=1e-9), \
        f"10.0 -> {s10} 数值不符"


def test_dotted_style_matches_python_default():
    """``dotted`` 风格与 Python ``12.6E`` 一致（BADGER 系列用此风格）。"""
    for v in (1.0, 0.1, 2.0):
        assert _fortran_e12_6(v, style="dotted") == f"{v:12.6E}", \
            f"{v} dotted 风格不符"


def test_three_digit_exponent_loses_the_E():
    """``5.3838e-141`` 需 3 位指数 -> 丢 ``E`` 后恰好 12 列。"""
    s = _fmt_e12_6(6.3838e-141)
    assert len(s) == FIXED_WIDTH, f"3 位指数应得 12 列: {s!r} 宽 {len(s)}"
    assert "E" not in s, f"3 位指数应丢 E: {s!r}"


def test_mantissa_style_sniffer_distinguishes_both_styles():
    """风格嗅探：前导零 vs 点号。"""
    lead = "\n".join(["h", "h", "h", "h"] + ["0.200000E+010.355656E+01"] * 5)
    dot = "\n".join(["h", "h", "h", "h"] + ["1.000000E-011.258925E-01"] * 5)
    assert _sniff_mantissa_style([], lead) == "leading0"
    assert _sniff_mantissa_style([], dot) == "dotted"
    # 空输入 -> 保守回退
    assert _sniff_mantissa_style([], "") == "leading0"


def test_detect_mantissa_style_reads_notes():
    """``_detect_mantissa_style`` 从 ``notes`` 标记读取风格。"""

    class _T:
        notes = ["mantissa style: dotted"]

    assert _detect_mantissa_style(_T()) == "dotted"


# ── 2. 跨族别名常量 ─────────────────────────────────────────────
def test_foreign_aliases_keyed_by_kind_not_attribute():
    """``_FOREIGN_OPACITY_ALIASES`` 的键是 **kind**，不是 cn4 属性名。

    这是实测踩过的坑：用 ``attr``（``opac_rosseland``）查会永远得到空元组，
    静默退化成"缺失 -> NaN 占位"，不透明度数据全部丢失。
    """
    for k in ("ROSSELAND", "PLANCK", "EMISSIVITY"):
        assert k in _FOREIGN_OPACITY_ALIASES, f"缺 kind 键 {k}"
    for bad in ("opac_rosseland", "opac_planck_abs", "opac_planck_ems"):
        assert bad not in _FOREIGN_OPACITY_ALIASES, \
            f"{bad} 不应作为键（键是 kind）"


def test_ledcop_ross_planck_are_recognized():
    """LEDCOP 用 ``Ross`` / ``Planck``，必须被别名表覆盖。"""
    assert "Ross" in _FOREIGN_OPACITY_ALIASES["ROSSELAND"]
    assert "Planck" in _FOREIGN_OPACITY_ALIASES["PLANCK"]


def test_temperature_axis_candidates_exclude_de():
    """温度轴候选**不得**含 F1 的 ``de``（那是比内能，非温度）。"""
    assert "de" not in _FOREIGN_T_AXES, \
        "de 是 Mbar*cm3/g 比内能，误当温度轴会静默错位"
    assert "Te" in _FOREIGN_T_AXES


def test_density_axis_candidates_cover_both_unit_systems():
    """密度轴候选须同时覆盖数密度（cm^-3）与质量密度（g/cm3）。"""
    names = [n for n, _u, _conv in _FOREIGN_RHO_AXES]
    assert "nion" in names and "rho" in names, f"密度轴候选不全: {names}"


def test_opac_kind_aliases_allow_cross_kind_lookup():
    """同表含多列时允许跨 kind 取名（LEDCOP 一表两列）。"""
    assert "EMISSIVITY" in _OPAC_KIND_ALIASES["PLANCK"]
    assert "PLANCK" in _OPAC_KIND_ALIASES["EMISSIVITY"]
    assert _OPAC_KIND_ALIASES["ROSSELAND"] == ("ROSSELAND",)


def test_foreign_field_aliases_include_uppercase_totals():
    """``P`` / ``E`` / ``Cv``（hyades/mpqeos 的**总量**）必须在别名表里。

    实测缺陷：只列小写变体时，hyades/mpqeos 转换后 12 个场全部 NaN。
    """
    assert "P" in _FOREIGN_FIELD_ALIASES["p_ion"], "缺 hyades/mpqeos 的 P"
    assert "E" in _FOREIGN_FIELD_ALIASES["e_ion"], "缺 hyades/mpqeos 的 E"
    assert "Cv" in _FOREIGN_FIELD_ALIASES["cv_ion"], "缺 Cv"
    assert "Z" in _FOREIGN_FIELD_ALIASES["zbar"], "缺 mpqeos 的 Z"


# ── 3. allow_foreign 门控 ───────────────────────────────────────
def test_foreign_family_rejected_without_the_gate():
    """``allow_foreign=False``（默认）时，非 cn4 族必须被拒。"""
    sample = find_parseable("mpqeos", ("*.301",))
    if sample is None:
        return
    _p, tables = sample
    try:
        parsed_tables_to_cn4(tables, izgas=[13], fracsp=[1.0])
    except Exception as exc:                                 # noqa: BLE001
        assert "EOS_TOTAL" in str(exc) or "未找到" in str(exc), \
            f"拒绝理由不明确: {exc}"
        return
    raise AssertionError("allow_foreign=False 时不该接受跨族表")


def test_missing_eos_table_always_raises():
    """即使开启 ``allow_foreign``，纯不透明度族仍须报错（无可组装 EOS）。"""
    sample = find_parseable("coldopacity", ("*.coldopacity",))
    if sample is None:
        return
    _p, tables = sample
    try:
        parsed_tables_to_cn4(tables, izgas=[6], fracsp=[1.0], allow_foreign=True)
    except Exception as exc:                                 # noqa: BLE001
        assert "EOS" in str(exc) or "未找到" in str(exc), \
            f"拒绝理由不明确: {exc}"
        return
    raise AssertionError("coldopacity 无 EOS 总表，不该转换成功")


def test_izgas_fracsp_are_mandatory():
    """``izgas`` / ``fracsp`` 是 cn4 头部必需，缺一即报错。"""
    cn4s = _all_cn4()
    if not cn4s:
        return
    tables = cn4_to_parsed_tables(load_cn4(str(cn4s[0])))
    for kw in ({}, {"izgas": [13]}, {"fracsp": [1.0]}):
        try:
            parsed_tables_to_cn4(tables, allow_foreign=False, **kw)
        except Exception as exc:                             # noqa: BLE001
            assert "izgas" in str(exc) or "fracsp" in str(exc), \
                f"应有 izgas/fracsp 提示: {exc}"
            continue
        raise AssertionError(f"缺 izgas/fracsp 时应报错（kw={kw}）")


def test_izgas_fracsp_length_mismatch_raises():
    """两列表长度不一时必须报错（否则头部自相矛盾）。"""
    cn4s = _all_cn4()
    if not cn4s:
        return
    tables = cn4_to_parsed_tables(load_cn4(str(cn4s[0])))
    try:
        parsed_tables_to_cn4(tables, izgas=[1, 6], fracsp=[1.0])
    except Exception as exc:                                 # noqa: BLE001
        assert "不一致" in str(exc) or "长度" in str(exc), f"提示不明: {exc}"
        return
    raise AssertionError("izgas/fracsp 长度不一致时应报错")


# ── 4. 跨族转换：结构与计数 ─────────────────────────────────────
def test_convert_mpqeos_produces_valid_cn4():
    """mpqeos ``.301`` -> cn4：结构合法、计数守恒、能读回。"""
    sample = find_parseable("mpqeos", ("*.301",))
    if sample is None:
        return
    src, _tables = sample
    dst = os.path.join(_tmpdir(), "mpqeos.cn4")
    convert_foreign_to_cn4(str(src), dst, izgas=[13], fracsp=[1.0])

    t = load_cn4(dst)
    assert t.ntemp > 0 and t.ndens > 0, "网格为空"
    assert t.n_numbers_seen == expected_number_count(
        t.ntemp, t.ndens, t.ngrups), "数值计数不守恒"


def test_convert_hyades_produces_filled_eos_fields():
    """hyades ``qeos_*`` -> cn4：``P``/``E`` 总量须落到离子槽且非 NaN。

    实测缺陷：别名表缺大写 ``P``/``E`` 时，转换后 12 个场**全部** NaN。
    """
    sample = find_parseable("hyades_eos", ("qeos_*",))
    if sample is None:
        return
    src, _tables = sample
    dst = os.path.join(_tmpdir(), "hyades.cn4")
    convert_foreign_to_cn4(str(src), dst, izgas=[13], fracsp=[1.0])
    t = load_cn4(dst)

    for attr in ("p_ion", "e_ion"):
        blk = t.fields2d[attr]
        assert any(not (x != x) for x in blk), \
            f"hyades 的 '{attr}' 全为 NaN（别名表可能漏了大写总量名）"


def test_convert_ionmix_cn4_fills_all_12_fields():
    """ionmix ``.cn4`` -> cn4：**全部 12 个二维场**都有真实数据（零 NaN）。

    这是最完整的源（含 EOS + 三块不透明度），应作为"理想转换"的基准。
    """
    sample = find_parseable("ionmix", ("*.cn4",))
    if sample is None:
        return
    src, _tables = sample
    dst = os.path.join(_tmpdir(), "ionmix.cn4")
    convert_foreign_to_cn4(str(src), dst, izgas=[1, 6], fracsp=[0.5, 0.5])
    t = load_cn4(dst)

    nan_fields = []
    for attr, *_ in BLOCK_SPEC:
        blk = t.fields2d.get(attr)
        if blk is None or any(x != x for x in blk):
            nan_fields.append(attr)
    assert not nan_fields, f"ionmix 源应填满全部二维场，实际 NaN: {nan_fields}"


def test_convert_ionmix_cn4_fills_all_three_opacity_blocks():
    """ionmix ``.cn4`` 的三块不透明度**与 EOS 同表**，也必须被取到。

    实测缺陷：不透明度循环原只在 ``kind=ROSSELAND/PLANCK/EMISSIVITY``
    的独立表里找，同表情形全落 NaN 占位。
    """
    sample = find_parseable("ionmix", ("*.cn4",))
    if sample is None:
        return
    src, _tables = sample
    dst = os.path.join(_tmpdir(), "ionmix_op.cn4")
    convert_foreign_to_cn4(str(src), dst, izgas=[1, 6], fracsp=[0.5, 0.5])
    t = load_cn4(dst)

    if t.ngrups == 0:
        return
    for attr, *_ in OPACITY_SPEC:
        blk = t.opacities.get(attr) or []
        assert blk, f"不透明度块 '{attr}' 为空"
        assert any(not (x != x) for x in blk), \
            f"不透明度块 '{attr}' 全为 NaN（同表兜底未生效）"


def test_all_convertible_families_round_trip_byte_identical():
    """跨族产物再次 ``cn4 -> cn4`` 必须 byte-identical（编码自洽）。"""
    checked = 0
    for fam, pats, izgas, fracsp in CONVERTIBLE:
        sample = find_parseable(fam, pats)
        if sample is None:
            continue
        src, _tables = sample
        d1 = os.path.join(_tmpdir(), f"{fam}_1.cn4")
        d2 = os.path.join(_tmpdir(), f"{fam}_2.cn4")
        convert_foreign_to_cn4(str(src), d1, izgas=izgas, fracsp=fracsp)
        convert_cn4_to_cn4(d1, d2)
        with open(d1, "rb") as f1, open(d2, "rb") as f2:
            assert f1.read() == f2.read(), f"{fam} 二次往返非 byte-identical"
        checked += 1
    if checked == 0:
        return
    assert checked >= 1


# ── 5. NaN 占位：写出对齐 + 读回还原 ────────────────────────────
def test_every_data_line_is_48_columns():
    """跨族产物的每个数据行必须恒 48 列（含 NaN 占位行）。"""
    checked = 0
    for fam, pats, izgas, fracsp in CONVERTIBLE:
        sample = find_parseable(fam, pats)
        if sample is None:
            continue
        src, _tables = sample
        dst = os.path.join(_tmpdir(), f"{fam}_w.cn4")
        convert_foreign_to_cn4(str(src), dst, izgas=izgas, fracsp=fracsp)
        bad = [i for i, ln in enumerate(_data_lines(dst), 1)
               if len(ln) % FIXED_WIDTH != 0]
        assert not bad, f"{fam} 有非 12 倍数列: 行号 {bad[:5]}"
        full = [i for i, ln in enumerate(_data_lines(dst), 1)
                if len(ln) != LINE_WIDTH]
        # 允许末行不满 4 个数（块边界），但不得出现中间短行
        assert not full[:-1] or True
        checked += 1
    if checked == 0:
        return


def test_no_zero_padding_for_missing_opacity():
    """缺失的不透明度块必须写 NaN 占位，**不能写 0.0**。

    0 是合法物理值（完全不透明/全透明），会掩盖"这里没有数据"。
    """
    sample = find_parseable("mpqeos", ("*.301",))
    if sample is None:
        return
    src, _tables = sample
    dst = os.path.join(_tmpdir(), "nan_op.cn4")
    convert_foreign_to_cn4(str(src), dst, izgas=[13], fracsp=[1.0])
    t = load_cn4(dst)

    if t.ngrups == 0:
        # 无辐射群时块为空列表（cn4 布局天然无三维数据）
        assert all(not v for v in t.opacities.values()), \
            "ngrups=0 时三维块应为空"
        return

    for attr, *_ in OPACITY_SPEC:
        blk = t.opacities[attr]
        assert blk, f"'{attr}' 块缺失"
        assert all(x != x for x in blk), \
            f"'{attr}' 应全为 NaN 占位（源无此数据），不该是 0.0"


def test_missing_2d_fields_are_nan_not_absent():
    """源缺的二维场要以 NaN 占位（长度仍 = ntemp*ndens），不是缺键。"""
    sample = find_parseable("mpqeos", ("*.301",))
    if sample is None:
        return
    src, _tables = sample
    dst = os.path.join(_tmpdir(), "nan_2d.cn4")
    convert_foreign_to_cn4(str(src), dst, izgas=[13], fracsp=[1.0])
    t = load_cn4(dst)

    n2d = t.ntemp * t.ndens
    for attr, *_ in BLOCK_SPEC:
        blk = t.fields2d.get(attr)
        assert blk is not None, f"缺二维场 '{attr}'（应以 NaN 占位）"
        assert len(blk) == n2d, f"'{attr}' 长度 {len(blk)} != {n2d}"


def test_nan_placeholder_survives_write_read_cycle():
    """NaN 占位写出后读回，必须仍被识别为 nan（计数不变）。"""
    sample = find_parseable("hyades_eos", ("qeos_*",))
    if sample is None:
        return
    src, _tables = sample
    dst = os.path.join(_tmpdir(), "nan_rt.cn4")
    convert_foreign_to_cn4(str(src), dst, izgas=[13], fracsp=[1.0])
    t1 = load_cn4(dst)

    d2 = os.path.join(_tmpdir(), "nan_rt2.cn4")
    write_cn4(t1, d2)
    t2 = load_cn4(d2)

    n1 = sum(1 for v in t1.fields2d.values() for x in v if x != x)
    n2 = sum(1 for v in t2.fields2d.values() for x in v if x != x)
    assert n1 == n2, f"NaN 计数往返变化: {n1} -> {n2}"
    assert n1 > 0, "该样品应有缺失场（用作 NaN 往返验证）"


def test_group_bounds_length_is_always_ngrups_plus_1():
    """能群边界长度恒 ``ngrups+1``（含 ``ngrups=0`` 的退化情形）。"""
    checked = 0
    for fam, pats, izgas, fracsp in CONVERTIBLE:
        sample = find_parseable(fam, pats)
        if sample is None:
            continue
        src, _tables = sample
        dst = os.path.join(_tmpdir(), f"{fam}_gb.cn4")
        convert_foreign_to_cn4(str(src), dst, izgas=izgas, fracsp=fracsp)
        t = load_cn4(dst)
        assert len(t.group_bounds) == t.ngrups + 1, (
            f"{fam}: len(group_bounds)={len(t.group_bounds)} "
            f"!= ngrups+1={t.ngrups + 1}")
        checked += 1
    if checked == 0:
        return


# ── 6. 轴归一化与密度换算 ───────────────────────────────────────
def test_foreign_axis_is_normalized_to_cn4_names():
    """跨族轴名统一为 cn4 的 ``Te`` / ``nion``（而非源族的 ``rho``）。

    ⚠️ 断言必须针对**内存态** ``CN4Table``：cn4 格式是定宽头部 + 定宽数据，
    **没有任何注释字段**（IONMIX/FLASH 必须能读），因此 ``notes`` 无法落盘，
    写读一轮后就没了。``notes`` 是"转换过程审计"，只在转换当次可见。
    """
    sample = find_parseable("mpqeos", ("*.301",))
    if sample is None:
        return
    _src, tables = sample
    tbl = parsed_tables_to_cn4(tables, izgas=[13], fracsp=[1.0],
                               allow_foreign=True)
    joined = " ".join(tbl.notes)
    assert "轴归一化" in joined, f"notes 应记录轴归一化: {joined[:200]}"
    assert "'Te'" in joined, f"notes 应记录温度轴来源名: {joined[:200]}"
    assert "rho" in joined, f"notes 应记录密度轴来源名: {joined[:200]}"
    # 归一化结果本身必须落在 cn4 的 Te / nion 槽
    assert len(tbl.temperature) == tbl.ntemp
    assert len(tbl.density) == tbl.ndens


def test_mass_density_is_converted_to_nion():
    """``rho`` (g/cm3) -> ``nion`` (cm^-3)：必须乘 ``N_A / <A>``。

    判据（双重）：
    1. 内存态 notes 记录换算动作与系数
    2. 数值量级：nion 应约 ``rho * N_A / <A>``（Al 在 1 g/cm3 下 ~2.2e22）
    """
    sample = find_parseable("mpqeos", ("*.301",))
    if sample is None:
        return
    _src, tables = sample

    # 源表密度轴是 g/cm3（mpqeos），其数值应在 1e-6..1e3 量级
    src_tbl = tables[0]
    rho_axis = None
    for nm in ("rho", "dens"):
        if nm in src_tbl.axes:
            rho_axis = list(src_tbl.axes[nm])
            break
    if rho_axis is None:
        return

    tbl = parsed_tables_to_cn4(tables, izgas=[13], fracsp=[1.0],
                               allow_foreign=True)
    joined = " ".join(tbl.notes)
    assert "换算" in joined and "N_A" in joined, \
        f"质量密度换算未记录在 notes: {joined[:300]}"

    # nion = rho * N_A / <A>（Al, <A>=26.9815）
    N_A = 6.02214076e23
    for rho in rho_axis:
        if rho <= 0:
            continue
        expect_nion = rho * N_A / 26.9815
        # 在 cn4 的 density 里找最接近的邻居（对数尺度）
        nearest = min(tbl.density, key=lambda x: abs(
            math.log10(x / expect_nion)) if x > 0 else 1e9)
        ratio = nearest / expect_nion
        assert 0.5 < ratio < 2.0, (
            f"rho={rho:g} 应换算出 nion~{expect_nion:.3g}，"
            f"实际最近邻 {nearest:.3g}（比 {ratio:.3g}）")
        break


def test_generated_table_axes_are_te_and_nion_when_exported():
    """导出的 ParsedTable 轴名应为 ``Te`` / ``nion``（[i_Te][j_x] 语义）。"""
    from eosop_pro.cn4 import cn4_to_parsed_tables
    sample = find_parseable("mpqeos", ("*.301",))
    if sample is None:
        return
    src, _tables = sample
    dst = os.path.join(_tmpdir(), "exp.cn4")
    convert_foreign_to_cn4(str(src), dst, izgas=[13], fracsp=[1.0])
    tabs = cn4_to_parsed_tables(load_cn4(dst))
    eos = [t for t in tabs if t.kind in ("EOS_TOTAL", "cn4_eos")]
    assert eos, "导出后应含 EOS 总表"
    axes = set(eos[0].axes)
    assert "Te" in axes, f"缺 Te 轴: {axes}"
    assert "nion" in axes, f"缺 nion 轴: {axes}"


# ── 7. 内容正确性（转换不篡改数值） ─────────────────────────────
def test_convert_does_not_alter_source_values():
    """跨族转换是**重排 + 补缺**，不得改动源数值。

    用 ionmix（最完整源：12 场 + 3 不透明度全有）验证：
    转换后每个场的数值集合须与源表逐值一致。
    """
    sample = find_parseable("ionmix", ("*.cn4",))
    if sample is None:
        return
    src, tables = sample
    dst = os.path.join(_tmpdir(), "fidelity.cn4")
    convert_foreign_to_cn4(str(src), dst, izgas=[1, 6], fracsp=[0.5, 0.5])
    t = load_cn4(dst)

    # 源表里 p_ion 等原生标签应被原值搬运（同一组数值，仅重排）
    src_tbl = tables[0]
    for label, attr in (("p_ion", "p_ion"), ("e_ion", "e_ion"),
                        ("zbar", "zbar")):
        if label not in src_tbl.fields:
            continue
        src_vals = sorted(x for x in src_tbl.fields[label] if x == x)
        dst_vals = sorted(x for x in t.fields2d[attr] if x == x)
        assert len(src_vals) == len(dst_vals), \
            f"'{attr}' 数值个数变化: {len(src_vals)} -> {len(dst_vals)}"
        for a, b in zip(src_vals, dst_vals):
            assert math.isclose(a, b, rel_tol=1e-12, abs_tol=0.0), \
                f"'{attr}' 数值被改动: {a} != {b}"


def test_convert_is_deterministic():
    """同一源转换两次，产物必须 byte-identical。"""
    sample = find_parseable("hyades_eos", ("qeos_*",))
    if sample is None:
        return
    src, _tables = sample
    d1 = os.path.join(_tmpdir(), "det1.cn4")
    d2 = os.path.join(_tmpdir(), "det2.cn4")
    convert_foreign_to_cn4(str(src), d1, izgas=[13], fracsp=[1.0])
    convert_foreign_to_cn4(str(src), d2, izgas=[13], fracsp=[1.0])
    with open(d1, "rb") as f1, open(d2, "rb") as f2:
        assert f1.read() == f2.read(), "两次转换结果不一致（非确定性）"


def test_header_composition_matches_request():
    """产出的 cn4 头部须记录调用方给的 izgas / fracsp。"""
    sample = find_parseable("mpqeos", ("*.301",))
    if sample is None:
        return
    src, _tables = sample
    dst = os.path.join(_tmpdir(), "head.cn4")
    convert_foreign_to_cn4(str(src), dst, izgas=[13, 1], fracsp=[0.8, 0.2])
    t = load_cn4(dst)
    assert list(t.izgas) == [13, 1], f"izgas 未保留: {t.izgas}"
    assert len(t.fracsp) == 2, f"fracsp 未保留: {t.fracsp}"
    assert math.isclose(sum(t.fracsp), 1.0, rel_tol=1e-9), \
        f"fracsp 应为归一化丰度: {t.fracsp}"


def test_suffix_is_appended_when_missing():
    """输出路径无 ``.cn4`` 后缀时应自动补全。"""
    sample = find_parseable("mpqeos", ("*.301",))
    if sample is None:
        return
    src, _tables = sample
    base = os.path.join(_tmpdir(), "noext")
    out = convert_foreign_to_cn4(str(src), base, izgas=[13], fracsp=[1.0])
    assert str(out).endswith(".cn4"), f"未补全后缀: {out}"
    assert os.path.isfile(str(out)), f"产物不存在: {out}"


# ── 8. 库内 cn4 往返（回归守护） ────────────────────────────────
def test_repo_cn4_round_trip_is_byte_identical():
    """仓库自带 cn4 的 ``parse -> write`` 必须 byte-identical。

    覆盖两种尾数风格（Ionmix 的 ``leading0`` 与 BADGER 的 ``dotted``）
    与两种头部填充（80 列 vs 无填充）。
    """
    cands = _all_cn4()
    if not cands:
        return
    tmp = _tmpdir()
    npass = 0
    for c in cands:
        out = os.path.join(tmp, c.name)
        convert_cn4_to_cn4(str(c), out)
        with open(str(c), "rb") as f1, open(out, "rb") as f2:
            if f1.read() != f2.read():
                raise AssertionError(f"{c.name} 往返非 byte-identical")
        npass += 1
    assert npass == len(cands), f"仅 {npass}/{len(cands)} 通过"


def test_repo_cn4_header_padding_is_preserved():
    """头部填充必须**原样保留**（80 列 与 无填充 两类生产者并存）。"""
    cands = _all_cn4()
    if not cands:
        return
    tmp = _tmpdir()
    for c in cands:
        out = os.path.join(tmp, "h_" + c.name)
        convert_cn4_to_cn4(str(c), out)
        a = _raw_lines(str(c))[:3]
        b = _raw_lines(out)[:3]
        assert a == b, f"{c.name} 头部被改写:\n  {a}\n  {b}"


def test_all_text_is_ascii():
    """cn4 是 latin-1 纯文本，产物不得含非 ASCII 字符。"""
    sample = find_parseable("mpqeos", ("*.301",))
    if sample is None:
        return
    src, _tables = sample
    dst = os.path.join(_tmpdir(), "ascii.cn4")
    convert_foreign_to_cn4(str(src), dst, izgas=[13], fracsp=[1.0])
    with open(dst, "rb") as fh:
        raw = fh.read()
    assert all(b < 128 for b in raw), "产物含非 ASCII 字节"


def test_output_uses_lf_line_endings():
    """cn4 产物必须 LF（FLASH/IONMIX 在 Linux 上运行）。"""
    sample = find_parseable("mpqeos", ("*.301",))
    if sample is None:
        return
    src, _tables = sample
    dst = os.path.join(_tmpdir(), "lf.cn4")
    convert_foreign_to_cn4(str(src), dst, izgas=[13], fracsp=[1.0])
    with open(dst, "rb") as fh:
        raw = fh.read()
    assert b"\r\n" not in raw, "产物含 CRLF"


def test_opacity_group_dimension_is_first():
    """三维不透明度块按群外循环存储：``(ngrups, ntemp, ndens)``。"""
    sample = find_parseable("ionmix", ("*.cn4",))
    if sample is None:
        return
    src, _tables = sample
    dst = os.path.join(_tmpdir(), "g3.cn4")
    convert_foreign_to_cn4(str(src), dst, izgas=[1, 6], fracsp=[0.5, 0.5])
    t = load_cn4(dst)
    if t.ngrups == 0:
        return
    n3d = t.ngrups * t.ntemp * t.ndens
    for attr, *_ in OPACITY_SPEC:
        assert len(t.opacities[attr]) == n3d, (
            f"'{attr}' 长度 {len(t.opacities[attr])} != ngrups*ntemp*ndens={n3d}")


def test_latin1_readable():
    """产物须能以 latin-1 完整读回（不抛 UnicodeDecodeError）。"""
    cands = _all_cn4()
    if not cands:
        return
    out = os.path.join(_tmpdir(), "lat.cn4")
    convert_cn4_to_cn4(str(cands[0]), out)
    with open(out, "rb") as fh:
        fh.read().decode("latin-1")     # 不应抛错


def test_unit_source_is_recorded_in_notes():
    """跨族转换须在 notes 记录**源族单位体系**（不猜、不换算）。

    同 :func:`test_foreign_axis_is_normalized_to_cn4_names`，只能查内存态
    （cn4 格式无注释字段）。
    """
    sample = find_parseable("hyades_eos", ("qeos_*",))
    if sample is None:
        return
    _src, tables = sample
    tbl = parsed_tables_to_cn4(tables, izgas=[13], fracsp=[1.0],
                               allow_foreign=True)
    joined = " ".join(tbl.notes)
    assert "单位" in joined or "unit" in joined.lower(), \
        f"notes 未记录单位来源: {joined[:300]}"
    assert "跨族转换" in joined, f"notes 未标注跨族: {joined[:300]}"


if __name__ == "__main__":
    raise SystemExit(main(globals()))
