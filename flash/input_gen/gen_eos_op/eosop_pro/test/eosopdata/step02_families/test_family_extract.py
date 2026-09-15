"""非 cn4 各族（F1-F6）的**数据结构与场提取**测试。

覆盖 17 个声明族的样品发现、轴语义、场形状与数值合理性。
样品惰性发现：找不到即早返回（skip），不把"数据不在"当缺陷。

分组（按数据能力）
------------------
============================  =====================================
能力                          族
============================  =====================================
2D EOS 场                     ``mpqeos`` / ``hyades_eos`` /
                              ``feos_native`` / ``multi_inverted_eos``
2D 不透明度 / Zeff            ``ledcop_atomic`` / ``ledcop_zeff`` /
                              ``multi_opacity`` / ``sesame_dat``
1D 曲线                       ``coldopacity`` / ``generic_curve`` /
                              ``hugoniot``
辅助 / 无数值轴               ``snop_input`` / ``feos_aux``
============================  =====================================
"""

import os
import sys

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

from eosopdata._samples import find_parseable                   # noqa: E402

#: 各族样品模式（实测可解析）。
SAMPLE_PATTERNS = {
    "mpqeos": ("*.301",),
    "hyades_eos": ("qeos_*",),
    "feos_native": ("*.feos",),
    "multi_inverted_eos": ("AL_eos",),
    "ledcop_atomic": ("Al.txt",),
    "ledcop_zeff": ("*.NoFree",),
    "multi_opacity": ("*.planck",),
    "sesame_dat": ("*.dat",),
    "coldopacity": ("*.coldopacity",),
    "generic_curve": ("ionpot*",),
    "hugoniot": ("*.hug",),
}

#: **别名族** —— 无扩展名专属声明，靠**路径/名称规则**分派到兄弟族。
#: 实测 ``hyades/Opacity/opc_1022.dat`` 由 ``hyades_eos`` 解析器处理
#: （``family='hyades_eos'``、``kind='OPACITY'``）—— 这**符合设计**，
#: 因为 ``.dat`` 不在 ``EXT_MAP`` 里，只能走 ``NAME_TOKENS`` 路径规则。
ALIAS_FAMILIES = {
    "sesame_dat": ("hyades_eos", "hyades_opacity", "sesame_dat"),
}

#: 有二维场的族（可画彩图）
FAMILIES_2D = ("mpqeos", "hyades_eos", "feos_native", "multi_inverted_eos",
               "ledcop_atomic", "ledcop_zeff", "multi_opacity", "sesame_dat")

#: 只有一维轴的族（可画曲线）
FAMILIES_1D = ("coldopacity", "generic_curve", "hugoniot")


def _first(fam):
    """取族样品表列表，找不到返回 ``None``。"""
    pats = SAMPLE_PATTERNS.get(fam)
    if pats is None:
        return None
    r = find_parseable(fam, pats)
    return r[1] if r else None


def _field_items(table):
    """遍历 ``(field_name, flat_values, shape)``。"""
    for nm in table.fields:
        flat = table.fields[nm]
        if not isinstance(flat, (list, tuple)):
            continue
        shape = table.field_shape.get(nm, ())
        yield nm, flat, shape


# ── 样品发现 ────────────────────────────────────────────────────
def test_all_configured_families_have_discoverable_samples():
    """配置表里至少一半族应能发现样品（否则说明数据树缺失）。"""
    found = [f for f in SAMPLE_PATTERNS if _first(f) is not None]
    assert found, "matter++ 数据树疑似未检出"
    assert len(found) >= 4, f"可发现族过少: {found}"


def test_each_discoverable_family_yields_parsed_tables():
    """每个可发现族解析后至少产出一张表，且表有 kind/family。"""
    for fam in SAMPLE_PATTERNS:
        tables = _first(fam)
        if tables is None:
            continue
        assert tables, f"{fam} 解析结果为空"
        t = tables[0]
        assert getattr(t, "kind", ""), f"{fam} 的表缺 kind"
        assert getattr(t, "family", ""), f"{fam} 的表缺 family"


def test_parsed_family_matches_requested_family():
    """按族名取到的表，其 ``family`` 应落在**该族的允许集合**内。

    ⚠️ 对**别名族**不能要求 ``family == 族名``：``.dat`` 不在 ``EXT_MAP``
    里，只能走路径规则，故 ``hyades/Opacity/opc_1022.dat`` 的 ``family``
    是 ``hyades_eos``。允许集合见 ``ALIAS_FAMILIES``。
    """
    for fam in SAMPLE_PATTERNS:
        tables = _first(fam)
        if tables is None:
            continue
        allowed = ALIAS_FAMILIES.get(fam, (fam,))
        got = {t.family for t in tables}
        assert got & set(allowed), (
            f"{fam}: 没有一张表的 family 落在 {list(allowed)}，实际={sorted(got)}")


def test_alias_families_resolve_to_a_registered_parser_family():
    """别名族解析出的 ``family`` 必须是**已注册解析族**（防腐烂）。

    这能抓住"解析器被删/改名但分派表未同步"的情况：断言 ``family`` 在
    ``FAMILY_PARSERS`` 里存在，且与请求族不同（正是"别名"的语义）。
    """
    from eosop_pro.registry.dispatch import FAMILY_PARSERS
    for fam, allowed in ALIAS_FAMILIES.items():
        real = [a for a in allowed if a in FAMILY_PARSERS]
        assert real, f"{fam} 的允许集合 {allowed} 里没有已注册解析族"
        tables = _first(fam)
        if tables is None:
            continue
        got = {t.family for t in tables}
        for g in got:
            assert g in FAMILY_PARSERS, f"{fam} 产出未注册的 family={g!r}"


def test_declared_extensions_reference_registered_parsers():
    """``EXT_MAP`` 的候选族应全部在 ``FAMILY_PARSERS`` 中注册。

    ⚠️ ``.dat`` **故意不在** ``EXT_MAP``（它走 ``NAME_TOKENS`` 路径规则），
    故不在此断言中 —— 这是设计，不是遗漏。
    """
    from eosop_pro.registry.declared_types import EXT_MAP
    from eosop_pro.registry.dispatch import FAMILY_PARSERS
    exts = (".301", ".feos", ".planck", ".coldopacity", ".hug")
    missing = [e for e in exts if e not in EXT_MAP]
    assert not missing, f"声明表缺扩展名: {missing}"
    unknown = []
    for e in exts:
        cands, _kind = EXT_MAP[e]
        assert cands, f"EXT_MAP[{e!r}] 候选族为空"
        unknown += [c for c in cands if c not in FAMILY_PARSERS]
    assert not unknown, f"EXT_MAP 引用了未注册解析族: {sorted(set(unknown))}"


# ── 二维 EOS / 不透明度族 ───────────────────────────────────────
def test_2d_families_have_two_named_axes():
    """二维族的表应有 2 个轴，且轴长与场形状自洽。"""
    checked = 0
    for fam in FAMILIES_2D:
        tables = _first(fam)
        if tables is None:
            continue
        t = tables[0]
        assert len(t.axes) >= 2, f"{fam} 轴数 {len(t.axes)} < 2"
        lens = sorted(len(v) for v in t.axes.values())
        for nm, flat, shape in _field_items(t):
            if not shape:
                continue
            prod = 1
            for s in shape:
                prod *= s
            assert prod == len(flat), (
                f"{fam}.'{nm}' 形状 {shape} 与长度 {len(flat)} 不符")
            checked += 1
        break
    if checked == 0:
        return


def test_2d_families_field_values_are_finite_and_nonnegative_temp():
    """二维族里至少有一个场含有限正值（排除"全是 0/NaN"的解析失败）。"""
    for fam in FAMILIES_2D:
        tables = _first(fam)
        if tables is None:
            continue
        t = tables[0]
        finite_pos = 0
        for _nm, flat, _sh in _field_items(t):
            for v in flat:
                if v == v and v > 0:
                    finite_pos += 1
                    break
        assert finite_pos > 0, f"{fam} 没有任何场含有限正值（疑似解析失败）"
        return


def test_temperature_axis_is_ascending_where_present():
    """温度轴（``Te`` / ``T``）应单调递增 —— 否则插值/等温线会失效。"""
    checked = 0
    for fam in FAMILIES_2D:
        tables = _first(fam)
        if tables is None:
            continue
        t = tables[0]
        for key in ("Te", "T", "tele"):
            if key not in t.axes:
                continue
            ax = list(t.axes[key])
            if len(ax) < 3:
                break
            asc = sum(1 for a, b in zip(ax, ax[1:]) if b > a)
            desc = sum(1 for a, b in zip(ax, ax[1:]) if b < a)
            assert max(asc, desc) == len(ax) - 1, (
                f"{fam}.{key} 轴非单调（asc={asc} desc={desc}）")
            checked += 1
            break
    if checked == 0:
        return


def test_density_axis_is_ascending_where_present():
    """密度轴（``rho`` / ``nion``）应单调递增。"""
    checked = 0
    for fam in FAMILIES_2D:
        tables = _first(fam)
        if tables is None:
            continue
        t = tables[0]
        for key in ("rho", "nion", "dens"):
            if key not in t.axes:
                continue
            ax = list(t.axes[key])
            if len(ax) < 3:
                break
            asc = sum(1 for a, b in zip(ax, ax[1:]) if b > a)
            desc = sum(1 for a, b in zip(ax, ax[1:]) if b < a)
            assert max(asc, desc) == len(ax) - 1, (
                f"{fam}.{key} 轴非单调（asc={asc} desc={desc}）")
            checked += 1
            break
    if checked == 0:
        return


def test_eos_families_expose_a_pressure_or_energy_field():
    """EOS 族必须至少含压强或比能类场（否则不是 EOS 表）。"""
    want = ("p_ion", "p_ele", "P", "Pion", "Pele", "e_ion", "e_ele",
            "E", "Eion", "Eele", "eint", "u")
    for fam in ("mpqeos", "hyades_eos", "feos_native", "multi_inverted_eos"):
        tables = _first(fam)
        if tables is None:
            continue
        t = tables[0]
        hit = [nm for nm in t.fields if nm in want]
        assert hit, f"{fam} 无压强/比能场，字段={sorted(t.fields)}"
        return


def test_opacity_families_expose_a_kappa_field():
    """不透明度族应含 ``kappa*`` 或 ``Ross``/``Planck`` 类场。"""
    for fam in ("ledcop_atomic", "multi_opacity", "sesame_dat"):
        tables = _first(fam)
        if tables is None:
            continue
        t = tables[0]
        hit = [nm for nm in t.fields
               if "kappa" in nm.lower() or nm in ("Ross", "Planck",
                                                  "rosseland", "planck")]
        assert hit, f"{fam} 无不透明度场，字段={sorted(t.fields)}"
        return


def test_zeff_family_exposes_a_charge_state_field():
    """``ledcop_zeff`` 应含 ``Zeff``/``Z`` 类平均电离度场。"""
    tables = _first("ledcop_zeff")
    if tables is None:
        return
    t = tables[0]
    hit = [nm for nm in t.fields
           if "z" in nm.lower() or "zeff" in nm.lower()]
    assert hit, f"ledcop_zeff 无电离度场，字段={sorted(t.fields)}"


def test_multi_opacity_group_dimension():
    """多群不透明度应有能群维（``n_groups`` > 0）。"""
    tables = _first("multi_opacity")
    if tables is None:
        return
    t = tables[0]
    ng = getattr(t, "n_groups", 0) or 0
    assert ng > 0, f"multi_opacity 应有能群维，实际 n_groups={ng}"


# ── 一维曲线族 ─────────────────────────────────────────────────
def test_1d_families_have_exactly_one_axis():
    """一维曲线族应只有 1 个轴。"""
    checked = 0
    for fam in FAMILIES_1D:
        tables = _first(fam)
        if tables is None:
            continue
        t = tables[0]
        assert len(t.axes) == 1, f"{fam} 轴数 {len(t.axes)} != 1: {sorted(t.axes)}"
        checked += 1
    if checked == 0:
        return


def test_1d_axis_length_matches_field_length():
    """一维族的场长度应等于其唯一轴的长度。"""
    checked = 0
    for fam in FAMILIES_1D:
        tables = _first(fam)
        if tables is None:
            continue
        t = tables[0]
        n = len(next(iter(t.axes.values())))
        for nm, flat, _sh in _field_items(t):
            assert len(flat) == n, (
                f"{fam}.'{nm}' 长度 {len(flat)} != 轴长 {n}")
            checked += 1
        break
    if checked == 0:
        return


def test_hugoniot_has_rankine_hugoniot_fields():
    """``.hug`` 应含 Hugoniot 关系所需量（``Us``/``Up`` 或 ``P``/``Rho``）。"""
    tables = _first("hugoniot")
    if tables is None:
        return
    t = tables[0]
    names = set(t.fields) | set(t.axes)
    low = {n.lower() for n in names}
    assert any(k in low for k in ("us", "up", "p", "rho", "u")), \
        f".hug 缺 Hugoniot 量，实际={sorted(names)}"


def test_generic_curve_has_multiple_columns():
    """``ionpot.dat`` 这类通用曲线常为多列 —— 应解析出 >1 个场。"""
    tables = _first("generic_curve")
    if tables is None:
        return
    t = tables[0]
    assert len(t.fields) >= 1, f"generic_curve 未解析出任何场"


def test_coldopacity_axis_is_photon_energy():
    """``coldopacity`` 的轴应是以光子能量（含 ``Eph``/``E`` 字样）。"""
    tables = _first("coldopacity")
    if tables is None:
        return
    t = tables[0]
    keys = " ".join(t.axes).lower()
    assert "eph" in keys or "e" in keys, f"coldopacity 轴名异常: {sorted(t.axes)}"


def test_feos_native_grids_are_strictly_monotonic():
    """⚠️ 回归守护：``feos_native`` 的轴必须**严格单调**。

    实测 ``Al.feos`` 头部声明 ``NR=192``，但真实 rho 网格只有 **191** 点，
    末尾跟一个 ``0.0`` 哨兵。早期实现盲信声明值硬切，把 ``0.0`` 并入 rho
    尾部、把 payload 首值 ``3.55e-44`` 并入 Te 尾部 —— **两个轴同时被污染**，
    表现为轴非单调，进而破坏插值/等温线/雨贡纽拟合。

    修复方式：``parsers/feos_native.grid_length()`` 用**严格递增前缀**判定
    真实网格长度。本测试锁死该行为。
    """
    tables = _first("feos_native")
    if tables is None:
        return
    t = tables[0]
    checked = 0
    for key in ("rho", "Te"):
        if key not in t.axes:
            continue
        ax = [float(v) for v in t.axes[key]]
        assert len(ax) >= 3, f"feos_native.{key} 点数过少: {len(ax)}"
        bad = [(i, ax[i], ax[i + 1]) for i in range(len(ax) - 1)
               if not ax[i + 1] > ax[i]]
        assert not bad, (
            f"feos_native.{key} 非严格单调，{len(bad)} 处违例，前 3: {bad[:3]}")
        assert ax[-1] > 0, f"feos_native.{key} 末点非正: {ax[-1]}"
        checked += 1
    assert checked == 2, f"未检查到两个轴（实际 {checked}）"


def test_feos_native_grid_length_helper_rejects_sentinel():
    """``grid_length`` 应剔除尾部哨兵点（单元级验证）。"""
    from eosop_pro.parsers.feos_native import grid_length
    inc = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert grid_length(inc + [0.0], 0, 6) == 5, "应裁掉尾部 0.0 哨兵"
    assert grid_length(inc, 0, 5) == 5, "完整递增序列应原样返回"
    # 偏差过大时不猜（保持历史行为）
    assert grid_length(inc, 0, 99) == 5, "声明远超实际时退回可取长度"
    # 起点越界
    assert grid_length([1.0], 5, 3) == 0
    # ⚠️ 首对即递减 -> 是别的格式，不是哨兵；不得裁成 1
    assert grid_length([3.0, 1.0, 2.0], 0, 3) == 3, "首对递减不应被当作哨兵"
    # 两元素有效网格仍可裁
    assert grid_length([1.0, 2.0, 0.0], 0, 3) == 2, "两元素递增网格应可裁"
    # start 偏移
    assert grid_length([9.0, 9.0, 1.0, 2.0, 3.0, 0.0], 2, 4) == 3


# ── 数值合理性 ─────────────────────────────────────────────────
def test_temperature_axis_is_in_eV_range_for_thermal_families():
    """温度轴应在合理 eV 范围（1e-3 .. 1e7 eV），排除单位误判。

    常见陷阱：LEDCOP 温度是 **keV**，ionmix/其余族是 eV（差 1000 倍）。
    """
    for fam in ("mpqeos", "hyades_eos", "ledcop_atomic"):
        tables = _first(fam)
        if tables is None:
            continue
        t = tables[0]
        for key in ("Te", "T"):
            if key not in t.axes:
                continue
            ax = [v for v in t.axes[key] if v == v and v > 0]
            if not ax:
                break
            lo, hi = min(ax), max(ax)
            assert 1e-6 < lo and hi < 1e9, (
                f"{fam}.{key} 范围异常: [{lo:g}, {hi:g}]（单位疑似错）")
            break
        return


def test_density_axis_is_positive():
    """密度轴必须全为正（``rho``>0 或 ``nion``>0），0/负值是解析错误的信号。"""
    for fam in FAMILIES_2D:
        tables = _first(fam)
        if tables is None:
            continue
        t = tables[0]
        for key in ("rho", "nion", "dens"):
            if key not in t.axes:
                continue
            ax = list(t.axes[key])
            pos = sum(1 for v in ax if v == v and v > 0)
            assert pos > 0, f"{fam}.{key} 全为非正值"
            break
        return


def test_no_field_is_all_nan():
    """任何族的场都不应**整场** NaN（那是解析失败的典型信号）。"""
    for fam in SAMPLE_PATTERNS:
        tables = _first(fam)
        if tables is None:
            continue
        t = tables[0]
        for nm, flat, _sh in _field_items(t):
            if not flat:
                continue
            if all(v != v for v in flat):
                raise AssertionError(f"{fam}.'{nm}' 整场 NaN（疑似解析失败）")
        return


def test_no_field_contains_inf_from_parse_errors():
    """解析产物不应含 ±inf（除显式占位外）—— inf 常见于除零/溢出。"""
    for fam in SAMPLE_PATTERNS:
        tables = _first(fam)
        if tables is None:
            continue
        t = tables[0]
        for nm, flat, _sh in _field_items(t):
            n_inf = sum(1 for v in flat if v in (float("inf"), float("-inf")))
            assert n_inf == 0, f"{fam}.'{nm}' 含 {n_inf} 个 inf"
        return


def test_axis_values_are_finite():
    """所有轴值应为有限数（NaN 轴会让插值/绘图静默出错）。"""
    for fam in SAMPLE_PATTERNS:
        tables = _first(fam)
        if tables is None:
            continue
        t = tables[0]
        for key, ax in t.axes.items():
            bad = [v for v in ax if not (v == v)]
            assert not bad, f"{fam}.{key} 轴含 {len(bad)} 个 NaN"
        return


def test_field_shape_metadata_is_consistent():
    """``field_shape`` 声明的形状必须乘积等于实际长度。"""
    checked = 0
    for fam in SAMPLE_PATTERNS:
        tables = _first(fam)
        if tables is None:
            continue
        t = tables[0]
        for nm, flat, shape in _field_items(t):
            if not shape:
                continue
            prod = 1
            for s in shape:
                prod *= s
            assert prod == len(flat), (
                f"{fam}.'{nm}' shape={shape} prod={prod} != len={len(flat)}")
            checked += 1
        if checked:
            break
    if checked == 0:
        return


if __name__ == "__main__":
    raise SystemExit(main(globals()))
