"""``convert`` 默认目标（cn4）与任意跨族互转测试。

覆盖范围
--------
1. **默认目标**：``DEFAULT_TARGET == "cn4"`` 且已注册 ——
   ``convert(t, out)`` 不带 target 即写合法 ``.cn4``（"默认转 cn4"）
2. **显式指定**：``target="h5"`` / ``target="hyades_eos"`` 等其他目标仍可用
   （"其他类型也可设置"）
3. **门控**：``izgas`` 必需（不猜）；多元素缺 ``fracsp`` 报错；``invert`` 拒收
4. **跨族默认转换**：mpqeos 单温总 EOS -> cn4（1:1 均分投影守恒）
5. **cn4 作为源**：仓库 cn4 -> ParsedTable -> 默认目标再写回（互转闭环）
6. **批量**：``convert_tables`` 同样默认 cn4
7. **全局默认可改**：``set_default_target`` 生效且测试后恢复（防 run_all
   同进程全局状态泄漏）

样品发现策略与 ``eosopdata/_samples.py`` 一致：惰性发现、数据不在即 skip。
"""

import os
import sys
import tempfile
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

from eosopdata._samples import find_parseable, first_cn4      # noqa: E402
from eosop_pro.convert import (                                # noqa: E402
    DEFAULT_TARGET,
    convert,
    convert_tables,
    get_default_target,
    get_target,
    list_targets,
    set_default_target,
)
from eosop_pro.parsers.cn4_io import (                         # noqa: E402
    cn4_to_parsed_tables,
    expected_number_count,
    load_cn4,
)


def _tmp():
    return tempfile.TemporaryDirectory()


def _eos_table(tables):
    """从解析产物里挑 EOS 总表（convert cn4 目标的合法 kind）。"""
    for t in tables:
        if t.kind in ("EOS_TOTAL", "cn4_eos"):
            return t
    return None


# ── 1. 注册表与默认目标 ─────────────────────────────────────────
def test_default_target_is_cn4():
    expect_eq(DEFAULT_TARGET, "cn4", "默认目标应为 cn4")
    expect_eq(get_default_target(), "cn4", "get_default_target 应一致")
    names = {t.name for t in list_targets()}
    expect_in("cn4", names, f"cn4 应已注册，实测 {sorted(names)}")


def test_cn4_target_descriptor():
    t = get_target("cn4")
    expect(t.description, "cn4 目标应有 description")
    expect_eq(t.requires, ("EOS_TOTAL", "cn4_eos"),
              "cn4 目标只接受 EOS 总表 kind")


def test_default_conversion_writes_valid_cn4():
    """跨族默认转换：不带 target 即写合法 .cn4（默认转 cn4）。"""
    sample = find_parseable("mpqeos", ("*.301",))
    if sample is None:
        return
    _src, tables = sample
    tbl = _eos_table(tables)
    if tbl is None:
        return
    with _tmp() as td:
        out = convert(tbl, Path(td) / "def", izgas=[13])   # 无后缀 -> 自动补
        expect(str(out).endswith(".cn4"), f"应自动补后缀: {out}")
        t = load_cn4(out)
        expect(t.ntemp > 0 and t.ndens > 0, "网格为空")
        expect_eq(t.n_numbers_seen,
                  expected_number_count(t.ntemp, t.ndens, t.ngrups),
                  "数值计数守恒")
        # 单温总 EOS 的 1:1 均分投影：p_ion / p_ele 都应有真实数据
        for attr in ("p_ion", "p_ele"):
            blk = t.fields2d.get(attr) or []
            expect(any(x == x for x in blk),
                   f"单温投影后 '{attr}' 不应全 NaN")


def test_default_conversion_from_ionmix_fills_fields():
    """ionmix .cn4（最完整源）经默认目标转换后 12 场应非全 NaN。"""
    sample = find_parseable("ionmix", ("*.cn4",))
    if sample is None:
        return
    _src, tables = sample
    tbl = _eos_table(tables)
    if tbl is None:
        return
    with _tmp() as td:
        out = convert(tbl, Path(td) / "imx.cn4", izgas=[1, 6],
                      fracsp=[0.5, 0.5])
        t = load_cn4(out)
        nan_all = [a for a, blk in t.fields2d.items()
                   if not any(x == x for x in blk)]
        expect(not nan_all, f"ionmix 源 12 场不应有全 NaN，实测 {nan_all}")


# ── 2. 显式指定其他目标 ─────────────────────────────────────────
def test_explicit_other_target_still_works():
    """target='h5' 显式指定仍可用（'其他类型也可设置'）。"""
    sample = find_parseable("mpqeos", ("*.301",))
    if sample is None:
        return
    _src, tables = sample
    tbl = _eos_table(tables)
    if tbl is None:
        return
    with _tmp() as td:
        out = convert(tbl, Path(td) / "def.h5", target="h5")
        expect(str(out).endswith(".h5"), f"h5 目标应出 .h5: {out}")
        import h5py
        with h5py.File(out, "r") as f:
            expect("tables" in f, "h5 产物应有 /tables")


def test_convert_tables_default_and_explicit():
    """批量接口同样默认 cn4；显式 target 时跳过语义正常。"""
    sample = find_parseable("mpqeos", ("*.301",))
    if sample is None:
        return
    _src, tables = sample
    tbl = _eos_table(tables)
    if tbl is None:
        return
    with _tmp() as td:
        written, skipped = convert_tables([tbl], td, izgas=[13])  # 默认 cn4
        expect_eq(len(written), 1, f"默认批量应写出 1 份，{written}")
        expect(str(written[0]).endswith(".cn4"),
               f"默认批量应出 .cn4: {written[0]}")
        # 指定 h5：mpqeos 表可写 h5
        written2, _sk2 = convert_tables([tbl], td, target="h5")
        expect_eq(len(written2), 1, "显式 h5 批量应写出 1 份")
    # 不透明度表不是 EOS 总表 -> cn4 目标应跳过而非崩溃
    sample2 = find_parseable("multi_opacity", ("*_ROSS*",))
    if sample2 is not None:
        ross = sample2[1][0]
        with _tmp() as td2:
            _w, sk = convert_tables([ross], td2, on_skip="collect")
            expect(len(sk) == 1 and not _w,
                   f"kind 不符应跳过: w={_w} sk={sk}")


# ── 3. 门控：izgas / fracsp / invert ────────────────────────────
def _mpqeos_or_none():
    sample = find_parseable("mpqeos", ("*.301",))
    if sample is None:
        return None
    return _eos_table(sample[1])


def test_missing_izgas_raises_with_hint():
    tbl = _mpqeos_or_none()
    if tbl is None:
        return
    try:
        convert(tbl, Path(tempfile.mkdtemp()) / "x.cn4")
    except Exception as exc:                                 # noqa: BLE001
        expect("izgas" in str(exc), f"报错应提示 izgas: {exc}")
        return
    raise AssertionError("缺 izgas 时应报错（cn4 头部必需，不猜）")


def test_multielement_requires_fracsp():
    tbl = _mpqeos_or_none()
    if tbl is None:
        return
    try:
        convert(tbl, Path(tempfile.mkdtemp()) / "x.cn4", izgas=[1, 6])
    except Exception as exc:                                 # noqa: BLE001
        expect("fracsp" in str(exc), f"报错应提示 fracsp: {exc}")
        return
    raise AssertionError("多元素缺 fracsp 时应报错")


def test_invert_is_rejected_for_cn4():
    tbl = _mpqeos_or_none()
    if tbl is None:
        return
    try:
        convert(tbl, Path(tempfile.mkdtemp()) / "x.cn4", izgas=[13],
                invert=True)
    except ValueError as exc:
        expect("invert" in str(exc), f"报错应提及 invert: {exc}")
        return
    raise AssertionError("cn4 目标应拒收 invert")


# ── 4. cn4 作为源参与互转（闭环） ────────────────────────────────
def test_cn4_source_roundtrip_via_default_target():
    """仓库 cn4 -> ParsedTable -> 默认目标再写回：读回合法且计数守恒。"""
    c = first_cn4()
    if c is None:
        return
    tabs = cn4_to_parsed_tables(load_cn4(str(c)))
    eos = _eos_table(tabs)
    if eos is None:
        return
    izgas = [int(z) for z in load_cn4(str(c)).izgas]
    fracsp = [1.0 / len(izgas)] * len(izgas)
    with _tmp() as td:
        out = convert(eos, Path(td) / "rt.cn4", izgas=izgas, fracsp=fracsp)
        t = load_cn4(out)
        expect_eq(t.n_numbers_seen,
                  expected_number_count(t.ntemp, t.ndens, t.ngrups),
                  "cn4 源再写回应计数守恒")
        expect_eq(list(t.izgas), izgas, "izgas 应原样保留")


# ── 5. 全局默认可改（测试后恢复，防同进程泄漏） ──────────────────
def test_set_default_target_switches_and_restores():
    tbl = _mpqeos_or_none()
    if tbl is None:
        return
    old = set_default_target("h5")
    try:
        expect_eq(get_default_target(), "h5", "默认应已切到 h5")
        with _tmp() as td:
            out = convert(tbl, Path(td) / "sw.h5")
            expect(str(out).endswith(".h5"),
                   f"切默认后 convert 应出 h5: {out}")
    finally:
        set_default_target(old)
    expect_eq(get_default_target(), old, "默认应已恢复")
    # 未知目标名应被拒
    try:
        set_default_target("no_such_target")
    except KeyError as exc:
        expect("no_such_target" in str(exc), f"应报未知目标: {exc}")
    else:
        raise AssertionError("未知目标名应被拒")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
