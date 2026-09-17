"""字典驱动标签统一出口（``plotting/labels.py``）的守护测试。

第十二轮裁定（用户 2026-09-15）的三个落点都在这里锁定：

1. **同步变更**：人工核查只改 ``field_checks.py``（翻 ``checked`` /
   修 ``meaning`` / ``unit``），绘图标签**下一次出图自动同步** ——
   本文件用一次性注册的演示族翻 ``checked`` 前后对比标签实证；
2. **无硬编码旁路**：``gridmap`` / ``qa_plots`` 源码不得再出现硬编码
   物理量标签（旧的 ``"Electron temperature T$_e$ (eV)"`` 等）；
3. **cn4 泛化接字典**：``CN4Table.origin_family`` 记录来源族；
   ``cn4_tags`` 按来源族回查认证标记；``cn4_plots`` 的 LaTeX 量名与
   字典登记键的一致性由本文件锁定。

样品相关测试懒加载：找不到数据即早返回，不把"数据不在"当缺陷。
"""

import inspect
import os
import sys
from dataclasses import fields as dataclass_fields

# --- path bootstrap (auto) ---
_d = os.path.dirname(os.path.abspath(__file__))
while _d != os.path.dirname(_d) and not os.path.isfile(
        os.path.join(_d, "_runner.py")):
    _d = os.path.dirname(_d)
if _d not in sys.path:
    sys.path.insert(0, _d)
import _runner                                                    # noqa: F401
from _runner import expect, expect_eq, main                      # noqa: E402

sys.path.insert(0, os.path.dirname(_d))                        # test/
sys.path.insert(0, os.path.dirname(os.path.dirname(_d)))       # repo root

from eosopdata._samples import find_parseable                     # noqa: E402

from eosop_pro.plotting.labels import (                           # noqa: E402
    CN4_SOURCE_FIELD, cn4_tags, display_unit, field_label, widest_tags)

#: 演示族名（测试内注册、退出前还原 FIELD_CHECKS，绝不污染字典）。
DEMO = "labels_sync_demo"


def _register_demo(checked_baz: bool) -> None:
    """注册/覆盖演示族：foo 无源未核查 / bar 有源未核查 / baz 可翻核查。"""
    from eosop_pro.registry.field_checks import (FieldCheck, KIND_DOC,
                                                 KIND_NONE, register_family)
    register_family(DEMO, {
        "foo": FieldCheck("Demo quantity foo", "RU", False, KIND_NONE,
                          "no recognizable source - demo entry"),
        "bar": FieldCheck("Demo quantity bar", "RB", False, KIND_DOC,
                          "demo primary document"),
        "baz": FieldCheck("Demo quantity baz", "RC", checked_baz, KIND_DOC,
                          "demo primary document"),
        "*": FieldCheck("Unregistered field", "unknown", False, KIND_NONE,
                        "demo fallback"),
    }, overwrite=True)


class _DemoFamily:
    """上下文管理：注册演示族 -> 运行 -> **原样还原** FIELD_CHECKS。

    ``run_all`` 同进程顺序执行所有模块；``test_field_checks.py`` 守护
    字典白名单与 Markdown 逐字同步 —— 演示族必须在测试结束后消失，
    且无论本文件先跑还是后跑都不得污染字典。
    """

    def __enter__(self):
        from eosop_pro.registry import field_checks as fcmod
        self._fcmod = fcmod
        self._saved = dict(fcmod.FIELD_CHECKS)
        _register_demo(checked_baz=False)
        return self

    def __exit__(self, *exc):
        self._fcmod.FIELD_CHECKS.clear()
        self._fcmod.FIELD_CHECKS.update(self._saved)
        return False


# ── 指令 2：同步变更实证 ────────────────────────────────────────
def test_label_syncs_with_dictionary_checked_flip():
    """翻 ``checked`` 后标签**立即**变化（改字典 -> 下次出图自动同步）。"""
    with _DemoFamily():
        before = field_label(DEMO, "baz")
        expect(before.endswith(", uv"),
               f"有源未核查应带 uv 标记: {before!r}")
        _register_demo(checked_baz=True)          # 用户人工核查后的唯一动作
        after = field_label(DEMO, "baz")
        expect(", uv" not in after,
               f"已核查条目标记应整体省略: {after!r}")
        expect(before.replace(", uv", "") == after,
               f"除标记外标签主体应不变: {before!r} -> {after!r}")
        # meaning/unit 同理：改字典即改标签
        from eosop_pro.registry.field_checks import (FieldCheck, KIND_DOC,
                                                     register_family)
        register_family(DEMO, {
            "foo": FieldCheck("Demo quantity foo", "RU", False, "none", "d"),
            "bar": FieldCheck("Demo quantity bar", "RB", False, KIND_DOC, "d"),
            "baz": FieldCheck("Renamed demo quantity", "RC", True,
                              KIND_DOC, "d"),
            "*": FieldCheck("Unregistered field", "unknown", False,
                            "none", "d"),
        }, overwrite=True)
        expect(field_label(DEMO, "baz").startswith("Renamed demo quantity"),
               "meaning 改动应实时反映到标签")


def test_label_syncs_through_gridmap_axis_label():
    """``gridmap`` 的轴标签同样实时同步（经 _axis_label_of）。"""
    with _DemoFamily():
        from eosop_pro.plotting.gridmap import _axis_label_of

        class _T:                      # 最小 duck-table（只用到两属性）
            family = DEMO
            axis_units = {"foo": ""}

        lab = _axis_label_of(_T(), "foo")
        expect(lab.endswith(", uk, uv"),
               f"无源未核查轴应带 uk, uv: {lab!r}")
        _register_demo(checked_baz=False)     # 把 foo 翻成有源：kind=doc
        from eosop_pro.registry.field_checks import (FieldCheck, KIND_DOC,
                                                     register_family)
        register_family(DEMO, {
            "foo": FieldCheck("Demo quantity foo", "RU", False, KIND_DOC, "d"),
            "bar": FieldCheck("Demo quantity bar", "RB", False, KIND_DOC, "d"),
            "baz": FieldCheck("Demo quantity baz", "RC", False, KIND_DOC, "d"),
            "*": FieldCheck("Unregistered field", "unknown", False,
                            "none", "d"),
        }, overwrite=True)
        lab2 = _axis_label_of(_T(), "foo")
        expect(lab2.endswith(", uv") and not lab2.endswith(", uk, uv"),
               f"补来源后 uk 应消失: {lab!r} -> {lab2!r}")


# ── 标签构造规则 ───────────────────────────────────────────────
def test_unregistered_field_falls_back_to_name():
    """未登记名（仅命中 ``"*"`` 兜底）回退字段名本身，不冒充字典语义。"""
    with _DemoFamily():
        lab = field_label(DEMO, "weird_col")
        expect(lab.startswith("weird_col ("),
               f"未登记名应以字段名为基: {lab!r}")
        expect(lab.endswith(", uk, uv"),
               f"兜底条目应带 uk, uv: {lab!r}")
        expect("Unregistered field" not in lab,
               "兜底语义串不得出现在标签里")


def test_display_unit_priority():
    """单位：解析器实测优先 -> 字典 -> unknown（不猜测）。"""
    with _DemoFamily():
        expect_eq(display_unit(DEMO, "foo", "keV"), "keV",
                  "实测单位应优先于字典")
        expect_eq(display_unit(DEMO, "foo", ""), "RU",
                  "无实测时应取字典单位")
        expect_eq(display_unit(DEMO, "nope", ""), "unknown",
                  "两者皆无应写 unknown")
        expect_eq(display_unit(DEMO, "nope", None), "unknown",
                  "None 实测同空串")


def test_hash_prefix_and_te_alias_lookup():
    """coldopacity 式 ``#`` 前缀名与 ionmix 式 ``T`` 轴名都能命中字典。

    第十三轮双轨：默认**短标签**（``E_ph`` / ``T``）；``long=True``
    取长标签 meaning（含已知陷阱注记）。
    """
    lab = field_label("coldopacity", "#Eph")
    expect(lab.startswith("E_ph ("),
           f"#Eph 应命中 Eph 条目（短标签默认）: {lab!r}")
    expect("Photon energy axis" in field_label(
               "coldopacity", "#Eph", long=True),
           f"#Eph long=True 应取长标签: {lab!r}")
    lab2 = field_label("ionmix", "Te")
    expect(lab2 == "T (eV)",
           f"ionmix 的 Te 应别名到 T 条目（短标签默认）: {lab2!r}")
    expect(field_label("ionmix", "Te", long=True).startswith(
               "Temperature axis"),
           "ionmix 的 Te long=True 应取长标签")
    expect(lab2 == field_label("ionmix", "T"),
           "Te 与 T 的 ionmix 标签应一致（均为已核查，无标记）")
    expect(", uv" not in lab2, f"cn4/ionmix 已核查，标记应省略: {lab2!r}")


def test_family_alias_cn4_maps_to_ionmix():
    """族名别名：ParsedTable 的 ``family == "cn4"`` -> 字典 ``ionmix``。"""
    lab = field_label("cn4", "Te")
    expect(lab == "T (eV)",
           f"cn4 应经别名命中 ionmix（短标签 T）: {lab!r}")
    expect(field_label("cn4", "Te", long=True).startswith(
               "Temperature axis"),
           "cn4 别名 long=True 应取 ionmix 长标签")
    expect_eq(cn4_tags("cn4", "T"), "", "cn4 别名应视为原生（无标记）")


def test_widest_tags_ranking():
    """widest_tags：未注册族 uk,uv；ionmix 无标记；按最差程度取宽。"""
    expect_eq(widest_tags("ionmix"), "", "ionmix 全部已核查")
    expect_eq(widest_tags("generic_curve"), "uk, uv", "兜底族无源未核查")
    expect_eq(widest_tags("definitely_not_registered__"), "uk, uv",
              "未注册族保守取 uk, uv")
    with _DemoFamily():
        expect_eq(widest_tags(DEMO), "uk, uv",
                  "foo 无源未核查 -> 族内最宽 uk, uv")


# ── 指令 3：cn4 泛化接字典 ─────────────────────────────────────
def test_cn4_tags_by_origin_family():
    """cn4_tags：原生无标记；来源族按候选回查；无映射回退族级最宽。"""
    expect_eq(cn4_tags("", "P"), "", "原生 cn4 无标记")
    expect_eq(cn4_tags("ionmix", "P"), "", "ionmix 来源无标记")
    expect_eq(cn4_tags("mpqeos", "P"), "uv", "mpqeos P 有源未核查")
    expect_eq(cn4_tags("mpqeos", "p_ion"), "uv", "p_ion 候选映射到 P")
    expect_eq(cn4_tags("mpqeos", "zbar"), "uk, uv",
              "mpqeos Z 无源未核查 -> uk, uv")
    expect_eq(cn4_tags("mpqeos", "Us"), "uk, uv",
              "Us 无候选映射 -> 回退族级最宽（mpqeos 的 Z 为 uk,uv）")
    expect_eq(cn4_tags("no_such_family__", "P"), "uk, uv",
              "未注册来源族保守 uk, uv")
    expect_eq(cn4_tags("ledcop_zeff", "zbar"), "uv",
              "ledcop_zeff NoFree（TOPS FAQ 有源）-> uv")


def test_cn4_source_field_candidates_are_registered():
    """每个非空候选元组至少有一个名字已登记进字典（防映射失效）。"""
    from eosop_pro.registry.field_checks import FIELD_CHECKS
    known = {k for entries in FIELD_CHECKS.values() for k in entries
             if k != "*"}
    for field, cands in CN4_SOURCE_FIELD.items():
        if not cands:
            continue
        hit = [c for c in cands if c in known]
        expect(hit, f"cn4 量 {field!r} 的候选 {cands} 无一登记进字典")


def test_cn4_table_has_origin_family_field():
    """``CN4Table`` 必须带 ``origin_family`` 字段（默认空 = 原生 cn4）。"""
    from eosop_pro.parsers.cn4_io import CN4Table
    names = {f.name for f in dataclass_fields(CN4Table)}
    expect("origin_family" in names, "CN4Table 缺 origin_family 字段")
    f = next(f for f in dataclass_fields(CN4Table)
             if f.name == "origin_family")
    expect_eq(f.default, "", "origin_family 默认应为空串（原生 cn4）")


def test_cn4_plot_quantity_names_are_dictionary_backed():
    """cn4_plots 的量名 ⊆ ionmix 登记键 ∪ cn4 代码派生量（一致性锁定）。

    LaTeX 排版标签保留（第十二轮裁定），但量名集合不得偏离字典 ——
    字典登记键改名/删除而 cn4_plots 未同步时，本测试 FAIL。
    """
    from eosop_pro.plotting.cn4_plots import (AXES, OPACITY_NAMES,
                                         _QUANTITY_META,
                                         SUPPORTED_QUANTITIES)
    from eosop_pro.registry.field_checks import FIELD_CHECKS
    ionmix = set(FIELD_CHECKS["ionmix"])
    derived = {"rho", "nele"}     # cn4 派生量（rho=nion<A>/N_A、nele=zbar*nion）
    alias = {"tele"}              # IONMIX 单温假设下 T 的轴别名（labels._TE_ALIAS）
    extra = {"transmission", "cs",
             "gamma_ion", "gamma_ele", "cs_thermal_fraction"}
    # r16 扩展：cn4 特有派生诊断量（无源族概念）——
    # gamma_ion/gamma_ele = 1+P/(rho*e) 单点恒等式（cn4_thermo），
    # cs_thermal_fraction = 热熵项占 c_s^2 比值（cn4_thermo 两项分解）
    legal = ionmix | derived | alias | extra
    for nm in AXES:
        expect(nm in legal, f"AXES 键 {nm!r} 不在字典 ionmix 集内")
    for nm in _QUANTITY_META:
        expect(nm in legal,
               f"_QUANTITY_META 键 {nm!r} 不在字典 ionmix 集内")
    for nm in SUPPORTED_QUANTITIES:
        expect(nm in legal,
               f"SUPPORTED_QUANTITIES 含未知量 {nm!r}")
    for label, attr in OPACITY_NAMES.values():  # 值 = (显示标签, CN4Table 属性名)
        expect(attr in ionmix,
               f"OPACITY_NAMES 属性 {attr!r}（标签 {label!r}）不在字典内")


# ── 硬编码旁路守护 ─────────────────────────────────────────────
def test_plotting_modules_have_no_hardcoded_labels():
    """绘图模块源码不得再出现硬编码物理量标签（旧缺陷的回归守护）。"""
    import eosop_pro.plotting.gridmap as gridmap
    import eosop_pro.plotting.qa_plots as qa_plots
    src_g = inspect.getsource(gridmap)
    src_q = inspect.getsource(qa_plots)
    for bad in ("Electron temperature Te", "log10 rho (g/cm",
                "(mean ionisation)"):
        expect(bad not in src_g, f"gridmap 仍硬编码 {bad!r}")
        expect(bad not in src_q, f"qa_plots 仍硬编码 {bad!r}")
    expect("Electron temperature T$_e$" not in src_q,
           "qa_plots 仍硬编码 LaTeX 温度标签")
    expect("Temperature T" not in src_g.replace("Temperature T)", ""),
           "gridmap 仍硬编码 Te/T/tele 标签映射")


def test_all_dictionary_labels_are_ascii():
    """全字典（family, field）的标签必须 ASCII（可安全上图）。"""
    from eosop_pro.registry.field_checks import FIELD_CHECKS
    for fam, entries in FIELD_CHECKS.items():
        for fld in entries:
            lab = field_label(fam, fld)
            expect(lab.isascii(), f"非 ASCII 标签: {fam}.{fld} -> {lab!r}")


# ── 端到端：qa_plots / gridmap 实图标签带标记（懒样品） ─────────
def _mpqeos_first():
    r = find_parseable("mpqeos", ("*.301",))
    return r[1][0] if r else None


def test_qa_plots_isobar_labels_carry_tags():
    """实图断言：mpqeos 等压线图的 x/y 轴标签带 ``uv`` 标记（指令 1 修复）。"""
    from eosop_pro.plotting.qa_plots import _plt, plot_eos_isobars
    t = _mpqeos_first()
    if t is None or "P" not in t.fields:
        return
    fig = plot_eos_isobars(t, "P")
    ax = fig.axes[0]
    expect("uv" in ax.get_xlabel(),
           f"等压线 xlabel 缺认证标记: {ax.get_xlabel()!r}")
    expect("uv" in ax.get_ylabel(),
           f"等压线 ylabel 缺认证标记: {ax.get_ylabel()!r}")
    _plt().close(fig)


def test_gridmap_axis_label_of_real_table_carries_tags():
    """实表断言：``_axis_label_of`` 对真实解析表输出带 ``uv`` 的短标签。

    第十三轮双轨：mpqeos.Te 登记短标签就是 ``Te`` -> 默认
    ``"Te (eV), uv"``；``long=True`` 取完整 meaning（含陷阱注记）。
    """
    from eosop_pro.plotting.gridmap import _axis_label_of
    t = _mpqeos_first()
    if t is None:
        return
    lab = _axis_label_of(t, "Te")
    expect(lab.endswith(", uv"), f"mpqeos Te 轴标签应带 uv: {lab!r}")
    expect(lab == "Te (eV), uv",
           f"mpqeos Te 轴标签默认应为短标签: {lab!r}")
    lab_long = _axis_label_of(t, "Te", long=True)
    expect(lab_long.startswith("Electron temperature axis"),
           f"mpqeos Te 轴标签 long=True 应取字典长标签: {lab_long!r}")


def test_short_label_dual_track_default_short():
    """短标签双轨（用户 2026-09-15 晚裁定）：绘图默认短标签；全字典
    每个登记条目都必须有非空 ASCII 短标签（缺失即字典登记缺陷）。
    字段名本身即标准简写的（p_ion/cv_ion 等），短标签与字段名一致。"""
    from eosop_pro.registry.field_checks import FIELD_CHECKS
    lab = field_label("mpqeos", "P", parser_unit="Mbar")
    expect_eq(lab, "P (Mbar), uv",
              f"默认应取短标签: {lab!r}")
    lab_long = field_label("mpqeos", "P", parser_unit="Mbar", long=True)
    expect(lab_long.startswith("Pressure (file in GPa)"),
           f"long=True 应取长标签 meaning: {lab_long!r}")
    for fam, entries in FIELD_CHECKS.items():
        for fld, fc in entries.items():
            expect(bool(fc.short), f"{fam}.{fld} 缺短标签（short 为空）")
            expect(all(ord(c) < 128 for c in fc.short),
                   f"{fam}.{fld} 短标签含非 ASCII: {fc.short!r}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
