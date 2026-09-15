# -*- coding: utf-8 -*-
"""eosop 家族**大型控制字典** —— 变量物理意义 / 单位 / 来源 / 核查状态
的唯一权威登记（用户 2026-09-15 规约：一切绘图与分析操作都须经本字典）。

标记规约（2026-09-15 第二次裁定：**标记只有 ``uk`` / ``uv`` 两个**）
----------------------------------------------------------------
每个变量（字段/轴）由两个独立属性描述，显示时折叠为 0~2 个标记：

* 来源确认 —— 是否有可指认的一级出处给出物理意义与单位。
  **无可指认来源 -> 显示 ``uk``**；有来源（``kind`` != ``none`` 且
  ``source`` 给出一级出处）-> **不显示**。
* 人工核查 —— 是否经过人工逐条核查。**未核查 -> 显示 ``uv``**；
  已核查 -> **不显示**。

即三种状态：``uk, uv``（完全无源且未核查）/ ``uv``（有源未核查）/
无标记（有源且已人工核查 —— **当前只有 cn4 全 18 块**）。用户将挨个
人工核查，手动把 ``checked`` 翻为 ``True`` 后该条目标记即消失。

统一出口 :func:`tags_label` 返回折叠后的标记串（``"uk, uv"`` / ``"uv"``
/ ``""``）；报告行写 ``tags=uk,uv``（完全核查后该键整体省略）；图上
colorbar / x/y 轴一律 ``Name (unit, <tags>)`` 形式（无标记则只写
``Name (unit)``）。

来源规约（2026-09-15 补充裁定：**source 必须对应最基础的文档**）
----------------------------------------------------------------
``source`` 是**长文本**溯源详述，只能引用四类一级出处：

1. **文件内明文声明**（``in-file declaration``）—— 数据文件自带的头行
   注释（ledcop_atomic 头行 3、coldopacity 两行头、hugoniot
   ``'# name [unit]'`` 头）；
2. **一级说明文档**（``primary document``）—— ``doc/`` 下随数据分发的
   权威手册（``MULTI使用的SESAME数据文件格式.docx``、
   ``Hyades 数据格式说明.doc``、``SNOP.MANUAL``、FEOS/MPQeos PDF），
   引用时给出 ``docs/extracted/`` 抽取文本路径 + **原文摘录**；
3. **源码行号**（``source code``）—— 数据写出器/解析器源码锚点
   （``abjt_03.f``、``eosop_pro/parsers/*.py``）；
4. **代码内派生公式**（``code-derived``）—— 派生轴的公式与常数锚点。

⚠️ ``docs/20_格式规格与物理量单位手册.md`` 是**中间产物**（由上述一级
出处整理而来），**不得**作为 ``source`` 引用 —— 引用一律下探到一级
出处。确实无一级出处的条目，``source`` 如实写明检索结果与不采信理由
（如 PDF 抽取伪影、.doc 抽取乱码不可引用），``kind="none"`` ->
显示 ``uk``。

字段结构（2026-09-15 补充裁定：结构化字段，各字段含义一目了然）
----------------------------------------------------------------
* ``meaning`` —— 物理意义（英文，出图/报告用，保证 ASCII）；
* ``unit``    —— 单位（``"unknown"`` = 未判定，**不猜测**）；
* ``kind``    —— 来源类型分类：``in-file declaration``（文件内声明）/
  ``primary document``（一级说明文档）/ ``source code``（源码行号）/
  ``code-derived``（派生公式）/ ``parser-measured``（解析器实测，
  预留给 :func:`register_family` 的实测类来源）/ ``none``
  （无可指认来源 -> ``uk``）；
* ``source``  —— 来源详述（长文本：一级出处原文摘录 / 脚本与行号 /
  文件内声明原文；无源条目如实说明检索结果）—— **允许并鼓励长文本**；
* ``checked`` —— 是否已人工核查（``False`` -> ``uv``；``True`` 且有源
  -> 标记省略）。

``doc`` 不再是存储字段，而是由 ``kind`` 派生的只读属性
（``kind != "none"`` 即视为有源 -> 不显示 ``uk``）—— 单一事实来源，
杜绝 kind/doc 两处手改失同步。

现状盘点（白名单）
------------------
* ``ionmix``（cn4）：全 18 块 ``source code``（abjt_03.f OWTF 逐块
  write 注释 + IONMIX 用户指南 §5.4 双佐证）+ ``checked=True``；
* ``multi_inverted_eos`` / ``mpqeos``（rho,Te,P,E）/ ``multi_opacity``
  （rho,Te,kappa）/ ``hyades_*``/``sesame_dat``（rho,Te,P,E,kappa）/
  ``ledcop_zeff``（rho,Te,NoFree,AvSqFree）/ ``snop_input``
  （T1,T2,X1,X2,FG）：``primary document``（一级手册原文佐证；
  ledcop_zeff 值段另有 LANL TOPS FAQ 逐字定义，2026-09-15 联网核查）；
* ``ledcop_atomic``（rho,Te,Ross,Planck）/ ``coldopacity``（全部）/
  ``hugoniot``（全部）：``in-file declaration``；
* ``derived_axes.n_e``：``code-derived``；其余条目 ``none`` -> ``uk``。
* ``unknown`` 严格保留为 ``"unknown"``，不猜测（诚实纪律）。

**未来未知格式**：经 :func:`register_family` 注册进本字典后即被
绘图/报告链路（``plotting/gridmap.py``）自动采用 —— 新格式必须走
本字典运作，不得绕过。

用法
----
::

    from eosop_pro.registry.field_checks import (
        field_check, FIELD_CHECKS, tags_label)

    tags_label(field_check("mpqeos", "Z"))        # -> "uk, uv"（无源未核查）
    tags_label(field_check("mpqeos", "P"))        # -> "uv"（一级文档佐证）
    tags_label(field_check("ionmix", "p_ion"))    # -> ""（cn4 已人工核查，省略）

动态列族（``coldopacity`` / ``generic_curve`` 等，列名逐文件声明）用
``"*"`` 兜底条目兜住未登记列名。

字典 Markdown 全文再生成：``python -m eosop_pro.registry.field_checks``
（写入 ``docs/eosop变量控制字典.md``；测试守护其与字典逐字同步）。
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["FieldCheck", "FIELD_CHECKS", "field_check", "checked_families",
           "family_check_stats", "doc_label", "verify_label", "tags_label",
           "register_family", "dump_markdown",
           "DOC_DOCUMENTED", "DOC_UNKNOWN", "VERIFY_OK", "VERIFY_UV",
           "KIND_IN_FILE", "KIND_DOC", "KIND_CODE", "KIND_MEASURED",
           "KIND_DERIVED", "KIND_NONE"]

#: 第一重认证取值：有可指认的一级出处。
DOC_DOCUMENTED = "doc"
#: 第一重认证取值：无可指认来源（用户 2026-09-15 规约标记）。
DOC_UNKNOWN = "uk"
#: 第二重认证取值：已人工核查。
VERIFY_OK = "ok"
#: 第二重认证取值：未人工核查（用户 2026-09-15 规约标记）。
VERIFY_UV = "uv"

# ----------------------------------------------------------------
# 来源类型（kind）受控词表 —— 每类的判定标准见模块 docstring「来源规约」
# ----------------------------------------------------------------
#: 文件内明文声明：数据文件自带头行注释逐字给出名称/单位。
KIND_IN_FILE = "in-file declaration"
#: 一级说明文档：doc/ 下随数据分发的权威手册（引用须带抽取文本路径）。
KIND_DOC = "primary document"
#: 源码行号：数据写出器/解析器源码的可指认锚点。
KIND_CODE = "source code"
#: 解析器实测：对样品文件的计数守恒/交叉校验等实测证据（预留词表）。
KIND_MEASURED = "parser-measured"
#: 代码内派生公式：公式与常数均可指认（如 n_e = rho*N_A*Zbar/A）。
KIND_DERIVED = "code-derived"
#: 无可指认来源 -> ``uk``。
KIND_NONE = "none"

_KNOWN_KINDS = frozenset({KIND_IN_FILE, KIND_DOC, KIND_CODE,
                          KIND_MEASURED, KIND_DERIVED, KIND_NONE})

_CN4_SOURCE = "abjt_03.f OWTF (line 4662-4743) + IONMIX user guide S5.4"

# 一级说明文档（抽取文本由 eosop_pro/docsrc.py 生成并记录 sha256）
_SRC_MULTI_SESAME = ("doc/MULTI使用的SESAME数据文件格式.docx（一级说明文档；抽取"
                     "文本 docs/extracted/MULTI使用的SESAME数据文件格式__ooxml-"
                     "word__3e289d7f.txt）")
_SRC_HYADES = ("doc/Hyades 数据格式说明.doc（一级说明文档；抽取文本 "
               "docs/extracted/Hyades_数据格式说明__ole2-word__ca1491e7.txt）")
_SRC_SNOP_MANUAL = ("doc/SNOP.MANUAL（SNOP 程序手册；抽取文本 "
                    "docs/extracted/SNOP__text__79a5123d.txt）")


@dataclass(frozen=True)
class FieldCheck:
    """单个字段的核查条目（各字段含义见模块 docstring「字段结构」）。

    Attributes:
        meaning: 物理意义（英文，出图/报告用，保证 ASCII）。
        unit: 单位字符串；未判定为 ``"unknown"``（不猜测）。
        checked: 第二重认证 —— 是否完成人工核查（未核查显示 ``uv``）。
        kind: 来源类型（受控词表 KIND_*；``"none"`` -> 显示 ``uk``）。
        source: 来源详述（长文本，一级出处原文摘录 / 脚本行号 / 文件内
            声明原文；无源条目如实写明检索结果与不采信理由）。
    """

    meaning: str
    unit: str
    checked: bool
    kind: str = KIND_NONE
    source: str = ""

    @property
    def doc(self) -> str:
        """兼容属性：有源（``kind != none``）-> ``"doc"``，否则 ``"uk"``。

        由 ``kind`` 单一事实来源派生，避免与 kind 手改失同步。
        """
        return DOC_DOCUMENTED if self.kind != KIND_NONE else DOC_UNKNOWN


def doc_label(fc: FieldCheck) -> str:
    """第一重认证的显示标记：``"doc"``（有可指认来源）或 ``"uk"``（无源）。"""
    return DOC_DOCUMENTED if fc.doc == DOC_DOCUMENTED else DOC_UNKNOWN


def verify_label(fc: FieldCheck) -> str:
    """人工核查状态的内部标记：``"ok"``（已核查）或 ``"uv"``（未验证）。

    ⚠️ 显示层请用 :func:`tags_label`（2026-09-15 规约：已核查标记省略）。
    """
    return VERIFY_OK if fc.checked else VERIFY_UV


def tags_label(fc: FieldCheck) -> str:
    """★ 标记统一出口（用户 2026-09-15 第二次裁定：标记只有 uk/uv 两个）。

    折叠规则（``uk`` = 无来源确认、``uv`` = 未人工核查）：

    * 无来源 + 未核查 -> ``"uk, uv"``
    * 有来源 + 未核查 -> ``"uv"``
    * 有来源 + 已核查 -> ``""``（**标记整体省略**，当前仅 cn4）
    * 无来源 + 已核查 -> ``"uk"``（诚实边界：核查过但来源不可指认，
      不冒充全通过 —— 正常流程不应出现，出现即字典登记有缺陷）
    """
    tokens: list[str] = []
    if fc.doc != DOC_DOCUMENTED:
        tokens.append(DOC_UNKNOWN)
    if not fc.checked:
        tokens.append(VERIFY_UV)
    return ", ".join(tokens)


def register_family(name: str, entries: dict[str, FieldCheck], *,
                    overwrite: bool = False) -> None:
    """把一个（可能未来才出现的未知）eosop 格式族注册进控制字典。

    注册后该族立即被 ``plotting/gridmap`` 的报告/绘图链路采用 ——
    新格式必须经本字典运作（用户 2026-09-15 规约），不得绕过。

    Args:
        name: 族注册名（与 ``ParsedTable.family`` / dispatch 族名一致）。
        entries: ``field -> FieldCheck`` 条目；建议含 ``"*"`` 兜底条目，
            未登记列名走兜底（查询永不崩溃，也绝不冒充已核查）。
            ``kind`` 请使用模块级 ``KIND_*`` 受控词表；``source`` 为长文本
            一级出处详述（文件内声明原文 / 文档+抽取路径 / 源码行号）。
        overwrite: 已存在同名族时是否覆盖；默认拒绝（防误覆盖手工
            核查成果）。
    """
    if not overwrite and name in FIELD_CHECKS:
        raise ValueError(
            f"family {name!r} already registered; pass overwrite=True to replace")
    FIELD_CHECKS[name] = dict(entries)


def dump_markdown(title: str = "eosop 变量控制字典") -> str:
    """把控制字典渲染为 Markdown 全文（人工挨个核查的对照底稿）。

    内容：字段说明图例 + 每族每变量的物理意义 / 单位 / 来源类型 /
    标记 / 来源详述（长文本）。再生成：
    ``python -m eosop_pro.registry.field_checks``；测试守护该文档与字典
    **逐字同步**（字典改动后文档必须重生成）。
    """
    n_fam = len(FIELD_CHECKS)
    n_ent = sum(len(v) for v in FIELD_CHECKS.values())
    lines: list[str] = [
        f"# {title}",
        "",
        "> 由 `registry/field_checks.py::dump_markdown()` 自动生成 ——",
        "> **勿手改本文件**；人工核查后请直接改 `field_checks.py` 中对应",
        "> 条目的 `checked=True`（或补 `source`），再重跑上述命令同步本文档。",
        "> 标记规约（2026-09-15）：只有 `uk`（无来源确认）/ `uv`（未人工",
        "> 核查）两个标记；两者都通过则**省略**（当前仅 cn4）。",
        "> 来源规约（2026-09-15）：`source` 只引用一级出处（文件内声明 /",
        "> 一级说明文档 / 源码行号 / 派生公式），并尽量原文摘录；",
        "> `docs/20` 手册属中间产物，**不得**作为来源引用。",
        "",
        "## 字段说明（每列含义）",
        "",
        "| 字段 | 含义 |",
        "|---|---|",
        ("| 变量 | 解析器/绘图链路使用的字段名或轴名；`*` = 未登记列名的"
         "兜底条目 |"),
        ("| 物理意义 | 英文表述（出图/报告用，保证 ASCII），括注坐标制与"
         "已知陷阱 |"),
        ("| 单位 | 推荐记法；`unknown` = 未判定，**不猜测** |"),
        ("| 来源类型 | `in-file declaration` 文件内声明 / `primary document` "
         "一级说明文档 / `source code` 源码行号 / `code-derived` 派生公式 / "
         "`none` 无可指认来源 |"),
        ("| 标记 | `uk, uv` 无源未核查 / `uv` 有源未核查 / "
         "`（已核查，省略）` 有源已核查 |"),
        ("| 来源详述 | 一级出处原文摘录 + 脚本/行号锚点；无源条目如实写明"
         "检索结果与不采信理由 |"),
        "",
        f"登记族数：{n_fam}；变量条目总数：{n_ent}",
        "",
    ]
    for fam in sorted(FIELD_CHECKS):
        entries = FIELD_CHECKS[fam]
        lines.append(f"## {fam}")
        lines.append("")
        lines.append("| 变量 | 物理意义 | 单位 | 来源类型 | 标记 | "
                     "来源详述（一级出处 / 脚本 / 文件内声明） |")
        lines.append("|---|---|---|---|---|---|")
        for fld, fc in entries.items():
            tags = tags_label(fc) or "（已核查，省略）"
            src = fc.source.replace("|", "\\|")
            lines.append(
                f"| `{fld}` | {fc.meaning} | {fc.unit} | {fc.kind} | {tags} "
                f"| {src} |")
        lines.append("")
    return "\n".join(lines)


# ================================================================
# F6 ionmix —— cn4 18 块（★ 唯一 checked=True 的族）
# 来源类型 = source code（abjt_03.f 写出器源码行号 + IONMIX 指南双佐证）
# ================================================================

_IONMIX_C4: dict[str, FieldCheck] = {
    # -- 轴 --
    "T":       FieldCheck("Temperature axis (tplsma)", "eV", True, KIND_CODE,
                          "abjt_03.f:4684 '(in ev)' + guide S5.4"),
    "nion":    FieldCheck("Ion (nucleon) number density axis (densnn)",
                          "cm^-3", True, KIND_CODE,
                          "abjt_03.f:4686 + guide S5.1 mass-density formula"),
    # -- 12 个二维 EOS 场 --
    "zbar":    FieldCheck("Average charge state ne/nion", "-", True, KIND_CODE,
                          _CN4_SOURCE + " :4687"),
    "dzdt":    FieldCheck("d(zbar)/dT", "1/eV", True, KIND_CODE,
                          _CN4_SOURCE + " :4691 (L4 derivation)"),
    "p_ion":   FieldCheck("Ion pressure", "J/cm3", True, KIND_CODE,
                          _CN4_SOURCE + " :4693 (L4) + guide :920"),
    "p_ele":   FieldCheck("Electron pressure", "J/cm3", True, KIND_CODE,
                          _CN4_SOURCE + " :4696 (L4) + guide :921"),
    "dpion_dt": FieldCheck("d(p_ion)/dT", "J/cm3/eV", True, KIND_CODE,
                           _CN4_SOURCE + " :4699 + guide :922"),
    "dpele_dt": FieldCheck("d(p_ele)/dT", "J/cm3/eV", True, KIND_CODE,
                           _CN4_SOURCE + " :4702 + guide :923"),
    "e_ion":   FieldCheck("Ion specific internal energy", "J/g", True,
                          KIND_CODE, _CN4_SOURCE + " :4706 + guide :924"),
    "e_ele":   FieldCheck("Electron specific internal energy", "J/g", True,
                          KIND_CODE, _CN4_SOURCE + " :4708 + guide :925"),
    "cv_ion":  FieldCheck("Ion specific heat", "J/g/eV", True, KIND_CODE,
                          _CN4_SOURCE + " :4711 + guide :926"),
    "cv_ele":  FieldCheck("Electron specific heat", "J/g/eV", True, KIND_CODE,
                          _CN4_SOURCE + " :4713 + guide :927"),
    "deion_dn": FieldCheck(
        "d(e_ion)/d(n_ion)", "J*cm3/g", True, KIND_CODE,
        _CN4_SOURCE + " :4717-4719; source self-notes 'not sure' - "
        "unit provisional per guide :928 (uncertainty registered in cn4.units)"),
    "deele_dn": FieldCheck(
        "d(e_ele)/d(n_ele)", "J*cm3/g", True, KIND_CODE,
        _CN4_SOURCE + " :4722-4725; source self-notes 'not sure' - "
        "unit provisional per guide :929 (uncertainty registered in cn4.units)"),
    # -- 群结构 + 3 个三维不透明度场 --
    "engrup":  FieldCheck("Photon group boundaries", "eV", True, KIND_CODE,
                          _CN4_SOURCE + " :4729 '(in ev)'"),
    "opac_rosseland": FieldCheck("Rosseland group opacity", "cm2/g", True,
                                 KIND_CODE,
                                 _CN4_SOURCE + " :4525/:4733 + guide :931"),
    "opac_planck_abs": FieldCheck("Planck absorption group opacity", "cm2/g",
                                  True, KIND_CODE,
                                  _CN4_SOURCE + " :4526/:4736 + guide :932"),
    "opac_planck_ems": FieldCheck("Planck emission group opacity", "cm2/g",
                                  True, KIND_CODE,
                                  _CN4_SOURCE + " :4739 + guide :933"),
}


# ================================================================
# F1 multi_inverted_eos —— 一级文档 doc/MULTI使用的SESAME数据文件格式.docx
# 「参数单位制」节逐字声明全部单位（2026-09-15 从 docs/20 下探到一级出处）
# ================================================================

_MULTI_INVERTED_EOS: dict[str, FieldCheck] = {
    "rho":   FieldCheck(
        "Mass density axis (linear)", "g/cm3", False, KIND_DOC,
        _SRC_MULTI_SESAME + "：'r[nr]  密度(g/cc)'；同文明文'因变量和自变量都"
        "没有使用对数坐标系，而是使用线性坐标系'；解析器 parsers/"
        "multi_inverted_eos.py:234-236 同值实现。"),
    "de":    FieldCheck(
        "Specific internal energy axis (above cold curve)", "Mbar*cm3/g",
        False, KIND_DOC,
        _SRC_MULTI_SESAME + "：'de[ne]  能量(能量列表，与冷能量的差距, "
        "单位Mbar*cm3/g)'；解析器 parsers/multi_inverted_eos.py:238-240。"),
    "P":     FieldCheck(
        "Pressure P(rho, de+e0)", "Mbar", False, KIND_DOC,
        _SRC_MULTI_SESAME + "：'P[ne*nr]  压力 P[(0~nr-1)+nr*i]为密度为"
        "r[0~nr-1]，能量de[i]+e0[0~ nr-1]时的压力，单位为Mbar'；解析器 "
        "parsers/multi_inverted_eos.py:242-245。"),
    "E":     FieldCheck(
        "Specific internal energy (de + e0_cold)", "Mbar*cm3/g", False,
        KIND_DOC,
        _SRC_MULTI_SESAME + "：de 为'与冷能量的差距'，总比能 = de + e0；"
        "解析器 parsers/multi_inverted_eos.py:249-259 合成（无 e0 布局以 "
        "de 为基准并显式注记）。"),
    "e0_cold": FieldCheck(
        "Cold curve specific energy (1-D over rho)", "Mbar*cm3/g", False,
        KIND_DOC,
        _SRC_MULTI_SESAME + "：'e0[nr]  冷能量(密度对应的冷能量列表，"
        "单位Mbar*cm3/g)'；解析器 parsers/multi_inverted_eos.py:247-252。"),
    "de_energy": FieldCheck(
        "Energy-axis spacing (same array as axis de)", "Mbar*cm3/g", False,
        KIND_DOC,
        "能量轴 de 另注册为一维场以便出图；单位继承 de 的 " +
        _SRC_MULTI_SESAME + " 声明；解析器 parsers/multi_inverted_eos.py:"
        "266-268。"),
    "T":     FieldCheck(
        "Temperature field T(rho, de+e0) (file in Kelvin, parser converts)",
        "eV", False, KIND_DOC,
        _SRC_MULTI_SESAME + "：'T[ne*nr] 密度为r[0~nr-1]，能量de[i]+e0[0~ "
        "nr-1]时的温度（Kelvin）'；解析器 parsers/multi_inverted_eos.py:"
        "261-264 乘 config.EV_PER_K 转 eV（常数单一来源）。"),
    "*":     FieldCheck(
        "Unregistered field", "unknown", False, KIND_NONE,
        "MULTI SESAME docx 的 F1 布局只定义 r/de/e0/P/T 五段（计数公式 "
        "'参数个数为4+2*nr+ne+2*nr*ne'），解析器 with_e0/no_e0 布局之外"
        "不承认其它列 —— 未登记名一律兜底，不猜。"),
}


# ================================================================
# F2 multi_opacity —— rho/Te/kappa 有一级文档逐字单位；Z（NZ 段）语义待核
# ================================================================

_MULTI_OPACITY: dict[str, FieldCheck] = {
    "rho":   FieldCheck(
        "Mass density axis (log10)", "g/cm3", False, KIND_DOC,
        _SRC_MULTI_SESAME + "：'剩下的数据依次为 r[nr]: log(密度g/cc)'，且"
        "'不透明度为logloglog全部采用对数存储数据'（log10 坐标）；解析器 "
        "parsers/multi_opacity.py 模块头'单位'节（另引 bundled 脚本 "
        "matlab/outputMULTIOpacity.m 逐行佐证）。"),
    "Te":    FieldCheck(
        "Electron temperature axis (log10; eV/keV dual trap)", "eV", False,
        KIND_DOC,
        _SRC_MULTI_SESAME + "：'t[nt] log(温度eV)'；⚠️ ZEFF 族例外为 keV —— "
        "同 docx Zeff 节'温度单位是keV'并明文以 X_Z.dat(eV) / X_Zeff.dat"
        "(keV) 区分文件名，由解析器 unit_hint 传入（multi_opacity.py 模块头"
        "'单位'节）。"),
    "kappa": FieldCheck(
        "Opacity (per-group subtables, log10)", "cm2/g", False, KIND_DOC,
        _SRC_MULTI_SESAME + "：'z[nr*nt]表格数据（log坐标,cm2/g）'；多群子表"
        "头自带逐群 (E_lo, E_hi)，标签 PLANCK/ROSSLAN/EPS 分别对应 Planck "
        "平均/Rosseland 平均/NLTE 因子（docx 数据类型表）；解析器 parsers/"
        "multi_opacity.py（LABEL_RE / KIND_BY_LABEL）。"),
    "Z":     FieldCheck(
        "Mean ionisation (NZ kind)", "-", False, KIND_NONE,
        "NZ kind 值段（opbe.inhalt 表号 NZ；f2 枚举实测 547 个 F2-like 文件，"
        "见 multi_opacity.py 模块头）。⚠️ 不冒充有源：一级文档中 'Z' 指不透明"
        "度表格角值（docx：'其中Z的单位为cm2/g'），并非平均电离度 —— NZ 段"
        "语义未获任何一级来源确认，待人工核查定案。"),
    "*":     FieldCheck(
        "Unregistered field", "unknown", False, KIND_NONE,
        "未登记列名兜底；不猜，人工核查后补条目。"),
}


# ================================================================
# F3 hyades_eos / hyades_opacity / sesame_dat（共用一套条目）
# 一级文档 doc/Hyades 数据格式说明.doc 逐字给出四量单位与不透明度布局
# ================================================================

_HYADES: dict[str, FieldCheck] = {
    "rho":   FieldCheck(
        "Mass density axis", "g/cm3", False, KIND_DOC,
        _SRC_HYADES + "：'密度 g/cm3; 温度 keV; 压强 dyne/cm2;比内能 erg/g'"
        "（逐字）；解析器 parsers/hyades_eos.py 模块头同文摘录（36-38 行）。"),
    "Te":    FieldCheck(
        "Electron temperature axis (file in keV)", "eV", False, KIND_DOC,
        _SRC_HYADES + "：'温度 keV'（文件原生 keV，解析器换算为 eV 后登记）。"),
    "P":     FieldCheck(
        "Pressure (CGS native)", "dyne/cm2", False, KIND_DOC,
        _SRC_HYADES + "：'压强 dyne/cm2'（CGS 原生单位，解析器原样保留）。"),
    "E":     FieldCheck(
        "Specific internal energy (CGS native)", "erg/g", False, KIND_DOC,
        _SRC_HYADES + "：'比内能 erg/g'（CGS 原生单位）。"),
    "kappa": FieldCheck(
        "Opacity (opc_* = [Rosseland, Planck])", "cm2/g", False, KIND_DOC,
        _SRC_HYADES + "：'不透明度参数使用同样的格式，压强处为平均Rosseland值，"
        "比内能处为平均Planck值，单位cm2/g'；且'本来应该存储Planck平均不透明度"
        "的位置用0代替'（Rosseland-only 判序依据，解析器 hyades_eos.py 模块头 "
        "32-34 行自动判序实现）。"),
    "raw_tail": FieldCheck(
        "Trailing residual values", "unknown", False, KIND_NONE,
        "尾部残余值：L = 2 + NR + NT + 2*NR*NT 之外的余数，解析器 hyades_eos.py "
        "按原样保存为 raw_tail 并记 unit=unknown —— 任何一级来源都未定义其含义，"
        "不猜。"),
    "*":     FieldCheck(
        "Unregistered field", "unknown", False, KIND_NONE,
        "Hyades docx 未定义其它列名；未登记名兜底，不猜。"),
}


# ================================================================
# F4a mpqeos —— rho/Te/P/E 有一级文档单位与换算式；Z 段语义待核（R3）
# ================================================================

_MPQEOS: dict[str, FieldCheck] = {
    "rho":   FieldCheck(
        "Mass density axis", "g/cm3", False, KIND_DOC,
        _SRC_MULTI_SESAME + "（MPQeos/SESAME 节）：'SESAME数据库的单位：…密度"
        "（g/cc）'，数据布局 'Id(1111)  Density(g/cc)  NR  NT'；解析器 "
        "parsers/mpqeos.py:107-109。"),
    "Te":    FieldCheck(
        "Electron temperature axis (file in Kelvin)", "eV", False, KIND_DOC,
        _SRC_MULTI_SESAME + "（MPQeos/SESAME 节）：'温度(Kelvin)'、布局 "
        "'T[1-NT](K)'，且'Multi1D++程序将自动识别文件后缀301/304/305并对单位"
        "制进行转化'；解析器 parsers/mpqeos.py:110-111 乘 config.EV_PER_K "
        "转 eV。"),
    "P":     FieldCheck(
        "Pressure (file in GPa)", "Mbar", False, KIND_DOC,
        _SRC_MULTI_SESAME + "（MPQeos/SESAME 节）：'压强（GPa）' + 换算式 "
        "'1GPa= 1e9Pa= 1e10 dyne/cm2=1e10erg/cm3=1e12 erg/cm2=1e-2Mbar'；"
        "解析器 parsers/mpqeos.py:115-117（config.MBAR_PER_GPA）。"),
    "E":     FieldCheck(
        "Specific internal energy (file in MJ/kg)", "Mbar*cm3/g", False,
        KIND_DOC,
        _SRC_MULTI_SESAME + "（MPQeos/SESAME 节）：'能量（MJ/kg）' + 换算式 "
        "'1MJ/kg= 1e3J/g= 1e10 erg/g= 1e12 erg*cm/g=1e-2Mbar*cm3/g'；解析器 "
        "parsers/mpqeos.py:120-122（config.MBAR_CM3_G_PER_MJ_KG）。"),
    "Z":     FieldCheck(
        "Average ionisation (5th payload segment)", "-", False, KIND_NONE,
        "docx 布局第 5 段 'Z[1-NRxNT]'，但同一 docx 自述'压强、能量甚至Z等有"
        "负值，原因正在查找'；解析器 parsers/mpqeos.py:142-152 实测负值并显式"
        "告警（风险 R3：段语义待核）。⚠️ 与'平均电离度'语义相矛盾的证据在案，"
        "不冒充有源 —— 待人工核查。"),
    "*":     FieldCheck(
        "Unregistered field", "unknown", False, KIND_NONE,
        "MPQeos 布局只有 R/T/P/E/Z 五段；未登记名兜底，不猜。"),
}


# ================================================================
# F4b feos_native —— PDF 抽取伪影，无可指认一级来源（诚实保持 uk）
# ================================================================

_FEOS_NATIVE: dict[str, FieldCheck] = {
    "rho":   FieldCheck(
        "Mass density axis", "g/cm3", False, KIND_NONE,
        "网格经 .301 兄弟文件交叉校验逐值一致（parsers/feos_native.py 模块头"
        "'交叉校验证据'：Al/B 两例 NR/NT 双验证）；但 .feos 自身的单位声明"
        "无法从一级文档可靠还原 —— FEOS-Package-Documentation2016.pdf §16.2 "
        "正文受 PDF 抽取连字伪影影响（解析器模块头'诚实声明（风险 R3）'）→ "
        "无可指认来源，待人工对照 PDF 原件核查。"),
    "Te":    FieldCheck(
        "Electron temperature axis", "eV", False, KIND_NONE,
        "网格由单调递增前缀裁剪定位（parsers/feos_native.py::grid_length，"
        "头部声明 NR/NT 实测可能多 1 个 0.0 哨兵）；行 0 十字段含 T_ref[eV]，"
        "但网格单位的文档级声明不可得（同 rho：PDF 抽取伪影）→ 待人工核查。"),
    "raw_values": FieldCheck(
        "Undecoded payload (PDF extraction artefacts; column semantics "
        "not recoverable)", "unknown", False, KIND_NONE,
        "未解码载荷：解析器只完全解码行 0 十字段（有 .301 交叉验证）并定位 "
        "rho/T 网格，其余数值按原样存 raw_values、绝不猜列语义（feos_native.py "
        "模块头'诚实声明（风险 R3）'）—— 设计上无来源可用。"),
    "*":     FieldCheck(
        "Unregistered field", "unknown", False, KIND_NONE,
        "未登记名兜底，不猜。"),
}

_FEOS_TABDATA: dict[str, FieldCheck] = {
    "*":     FieldCheck(
        "All columns (colN naming; no local column-name doc)", "unknown",
        False, KIND_NONE,
        "colN 占位列名：本地无任何一级列名文档（仅有中间产物草稿提及，"
        "不作依据）—— 语义待人工核查，不猜。"),
}

_FEOS_AUX: dict[str, FieldCheck] = {
    "*":     FieldCheck(
        "raw_values (auxiliary parameter file)", "unknown", False, KIND_NONE,
        "辅助参数文件的未解码载荷：无可指认的一级来源（中间产物草稿不作"
        "依据）—— 待人工核查。"),
}


# ================================================================
# F5a ledcop_atomic —— 文件内明文声明（头行 3）；说明 .doc 抽取乱码不可引用
# ================================================================

_LEDCOP_DECL = ("文件头第 3 行明文声明（实测 Al.txt）：'Opacities in cm**2/gm, "
                "T in keV, density in gm/cc'")

_LEDCOP_ATOMIC: dict[str, FieldCheck] = {
    "rho":   FieldCheck("Mass density axis", "g/cm3", False, KIND_IN_FILE,
                        _LEDCOP_DECL + " —— density（gm/cc）项。"),
    "Te":    FieldCheck("Electron temperature axis (file declares keV inline)",
                        "eV", False, KIND_IN_FILE,
                        _LEDCOP_DECL + " —— T 项（文件原生 keV，解析器换算 eV）。"),
    "Ross":  FieldCheck("Rosseland opacity", "cm2/g", False, KIND_IN_FILE,
                        _LEDCOP_DECL + " —— Opacities 项。"),
    "Planck": FieldCheck("Planck opacity", "cm2/g", False, KIND_IN_FILE,
                         _LEDCOP_DECL + " —— Opacities 项。"),
    "No. Free": FieldCheck(
        "Free-electron count (dimensionless, normalization unchecked)", "-",
        False, KIND_NONE,
        "列名来自解析器对数据列的切分命名；文件内无该列的单位/语义声明；"
        "Atomic(LEDCOP)说明.doc 抽取为乱码（ole2 双对齐失败）不可引用 → "
        "无可指认来源，待人工核查。"),
    "Av Sq Free": FieldCheck(
        "Mean-square free-electron count", "-", False, KIND_NONE,
        "同 'No. Free'：文件内无声明、说明 .doc 抽取乱码不可引用 → 待人工核查。"),
    "*":     FieldCheck("Unregistered field", "unknown", False, KIND_NONE,
                        "未登记列名兜底，不猜。"),
}


# ================================================================
# F5b ledcop_zeff —— rho/Te 有一级文档（docx Zeff 节）；NoFree/AvSqFree
# 有 LANL TOPS FAQ 逐字定义（2026-09-15 联网核查）
# ================================================================

_LEDCOP_ZEFF: dict[str, FieldCheck] = {
    "rho":   FieldCheck(
        "Mass density axis (log10 values)", "g/cm3", False, KIND_DOC,
        _SRC_MULTI_SESAME + "（Zeff 节）：'温度和密度采用对数坐标系…密度单位"
        "是g/cm3'；解析器 parsers/ledcop_zeff.py 模块头（log10 rho 布局）。"),
    "Te":    FieldCheck(
        "Electron temperature axis (log10 values, keV)", "keV", False,
        KIND_DOC,
        _SRC_MULTI_SESAME + "（Zeff 节）：'温度单位是keV'，并明文与不透明度族"
        "区分（'与不透明度不同，不透明度温度单位为eV'）、文件名约定 "
        "X_Zeff.dat(keV) vs X_Z.dat(eV)；解析器 parsers/ledcop_zeff.py 模块头。"),
    "NoFree": FieldCheck(
        "Free-electron number (Zbar equivalent)", "-", False, KIND_DOC,
        "LANL TOPS FAQ（https://aphysics2.lanl.gov/static/opacdocs/"
        "opac-faq.html）Q1 逐字定义：'the free electron number is the "
        "average number of free electrons per ion'（每离子平均自由电子数；"
        "逐离子态布居加权，混合物按数分数加权平均）。LEDCOP 为 TOPS 官方"
        "文件格式之一（opac-help.html：'The LEDCOP files are older cross "
        "section files'），NoFree 列名即 TOPS 输出约定；最佳引用 "
        "Magee et al. 1995（LANL T-1）。*.NoFree 值段解析器 _field_for "
        "登记为 Z/ZEFF；文件内无单位声明（.doc 抽取乱码不可引用）→ 无量纲。"),
    "AvSqFree": FieldCheck(
        "Mean-square free-electron number (Z^2 equivalent)", "-", False,
        KIND_DOC,
        "LANL TOPS FAQ（https://aphysics2.lanl.gov/static/opacdocs/"
        "opac-faq.html）Q7 逐字定义：'This is the average of the square of "
        "the number of free electrons over the ion stages of an element' "
        "（自由电子数平方对离子态的平均）→ <Z^2>，与 NoFree=<Z> 配套"
        "（差值即离子态方差）。同 NoFree：LEDCOP/TOPS 同源（LANL T-1，"
        "最佳引用 Magee et al. 1995），无量纲；解析器 _field_for 登记 "
        "Z2/ZEFF2。"),
    "*":     FieldCheck("Unregistered field", "unknown", False, KIND_NONE,
                        "未登记列名兜底，不猜。"),
}


# ================================================================
# coldopacity —— 逐文件两行头声明（in-file declaration）
# ================================================================

_COLD_DECL = ("逐文件两行头明文声明列名与单位（实测 Ac.coldopacity："
              "'#Eph<TAB>miu' + '#eV<TAB>cm2/g'）；解析器 parsers/coldopacity.py "
              "读取该头逐列登记")

_COLDOPACITY: dict[str, FieldCheck] = {
    "Eph":   FieldCheck("Photon energy axis (typical; per-file declared)",
                        "eV", False, KIND_IN_FILE,
                        _COLD_DECL + "；本条 unit 为典型值，以逐文件头为准。"),
    "miu":   FieldCheck("Opacity column (typical; per-file declared)",
                        "cm2/g", False, KIND_IN_FILE,
                        _COLD_DECL + "；本条 unit 为典型值，以逐文件头为准。"),
    "*":     FieldCheck("Per-file column (see in-file name/unit header lines)",
                        "unknown", False, KIND_IN_FILE,
                        _COLD_DECL + "；兜底列名/单位由逐文件头实时登记（查询"
                        "兜底不猜）。"),
}


# ================================================================
# hugoniot —— 逐文件 '# name [unit]' 注释头声明（in-file declaration）
# ================================================================

_HUGO_DECL = ("逐文件首行 '# name [unit]' 注释头逐列声明（两种写法：裸 '[unit]' "
              "与 '[scale unit]' 缩放因子剥离，见 parsers/hugoniot.py）。⚠️ 单位"
              "逐文件可变（实测 Al.feos.hug 声明 P 为 dyne/cm^2）—— 字典 unit "
              "仅为典型值，绘图以解析器逐文件提取（table.field_units）为准")

_HUGONIOT: dict[str, FieldCheck] = {
    "Rho":   FieldCheck("Mass density (per-file declared)", "g/cm3", False,
                        KIND_IN_FILE, _HUGO_DECL),
    "T":     FieldCheck("Temperature (per-file declared)", "eV", False,
                        KIND_IN_FILE, _HUGO_DECL),
    "P":     FieldCheck("Pressure (per-file declared)", "Mbar", False,
                        KIND_IN_FILE, _HUGO_DECL),
    "E":     FieldCheck("Specific internal energy (per-file declared)",
                        "erg/g", False, KIND_IN_FILE, _HUGO_DECL),
    "Us":    FieldCheck("Shock velocity (per-file declared)", "km/s", False,
                        KIND_IN_FILE, _HUGO_DECL),
    "Up":    FieldCheck("Particle velocity (per-file declared)", "km/s",
                        False, KIND_IN_FILE, _HUGO_DECL),
    "*":     FieldCheck("Per-file column (see '# [...] [unit]' comment header)",
                        "unknown", False, KIND_IN_FILE,
                        _HUGO_DECL + "；兜底列由逐文件头实时登记。"),
}


# ================================================================
# F6f snop_input —— 一级手册 doc/SNOP.MANUAL 逐字给出参数含义与单位
# （X1/X2 原文为光子能量边界 —— 修正此前中间产物手册的 'Density bound' 笔误）
# ================================================================

_SNOP_UNITS_NOTE = "解析器 parsers/snop_input.py:33-38 PARAM_UNITS 逐字摘录。"

_SNOP_INPUT: dict[str, FieldCheck] = {
    "T1":    FieldCheck("Temperature bound 1 (lowest)", "keV", False, KIND_DOC,
                        _SRC_SNOP_MANUAL + "：'T1  Lowest temperature (in keV)'；"
                        + _SNOP_UNITS_NOTE),
    "T2":    FieldCheck("Temperature bound 2 (highest)", "keV", False, KIND_DOC,
                        _SRC_SNOP_MANUAL + "：'T2  Highest temperature (in keV)'；"
                        + _SNOP_UNITS_NOTE),
    "X1":    FieldCheck("Photon energy bound 1 (lowest)", "keV", False,
                        KIND_DOC,
                        _SRC_SNOP_MANUAL + "：'X1  Lowest photon energy (in "
                        "keV)'；★ 修正：此前登记为 'Density bound'，系中间产物"
                        "手册笔误 —— SNOP.MANUAL 原文为光子能量边界；"
                        + _SNOP_UNITS_NOTE),
    "X2":    FieldCheck("Photon energy bound 2 (highest)", "keV", False,
                        KIND_DOC,
                        _SRC_SNOP_MANUAL + "：'X2  Highest photon energy (in "
                        "keV)'；修正说明同 X1；" + _SNOP_UNITS_NOTE),
    "FG":    FieldCheck("Photon group boundaries (user-supplied if IGROUP=0)",
                        "eV", False, KIND_DOC,
                        _SRC_SNOP_MANUAL + "：'FG(NG+1)Group boundaries (in eV) "
                        "given by user if IGROUP = 0'；" + _SNOP_UNITS_NOTE),
    "*":     FieldCheck(
        "Unregistered field", "unknown", False, KIND_NONE,
        "SNOP.MANUAL 定义的其余 namelist 参数未逐一登记；未登记名兜底，不猜。"),
}


# ================================================================
# generic_curve —— 兜底族（设计上无来源）
# ================================================================

_GENERIC_CURVE: dict[str, FieldCheck] = {
    "*":     FieldCheck(
        "Fallback family - column semantics not documented, never guessed",
        "unknown", False, KIND_NONE,
        "兜底族设计立场：列语义不文档化、绝不猜测（parsers/generic_curve.py）"
        "—— 无来源可用，人工核查前保持 uk, uv。"),
}


# ================================================================
# 派生轴（绘图代码内计算，非文件字段）
# ================================================================

#: gridmap ne-T 彩图的派生 y 轴：``n_e = rho * N_A * Zbar / A``
#: （公式在 ``plotting/gridmap.py::_derive_ne``，常数取 ``config.N_A``
#: 单一来源）。公式与常数均可指认 -> ``code-derived``（显示 ``uv``）；
#: 未人工核查。
_DERIVED_AXES: dict[str, FieldCheck] = {
    "n_e":   FieldCheck(
        "Electron number density (derived: n_e = rho*N_A*Zbar/A)", "cm^-3",
        False, KIND_DERIVED,
        "代码内派生公式：plotting/gridmap.py::_derive_ne，常数 N_A 取 "
        "config.py 单一来源（公式与常数均可指认，单位由量纲确定）—— 待人工核查。"),
}


#: ★ 核查字典：family -> field -> FieldCheck。
#: cn4（注册族名 ``ionmix``）是唯一 ``checked=True`` 的族；
#: kind 白名单现状见模块 docstring「现状盘点」；其余条目 ``kind="none"``
#: （含 ``"*"`` 兜底）。
FIELD_CHECKS: dict[str, dict[str, FieldCheck]] = {
    "ionmix": _IONMIX_C4,
    "multi_inverted_eos": _MULTI_INVERTED_EOS,
    "multi_opacity": _MULTI_OPACITY,
    "hyades_eos": _HYADES,
    "hyades_opacity": _HYADES,
    "sesame_dat": _HYADES,
    "mpqeos": _MPQEOS,
    "feos_native": _FEOS_NATIVE,
    "feos_tabdata": _FEOS_TABDATA,
    "feos_aux": _FEOS_AUX,
    "ledcop_atomic": _LEDCOP_ATOMIC,
    "ledcop_zeff": _LEDCOP_ZEFF,
    "coldopacity": _COLDOPACITY,
    "hugoniot": _HUGONIOT,
    "snop_input": _SNOP_INPUT,
    "generic_curve": _GENERIC_CURVE,
    "derived_axes": _DERIVED_AXES,
}

#: 未注册族的兜底条目（绝不让查询崩溃，但也绝不让未核查数据冒充已核查）。
_UNREGISTERED_FAMILY = FieldCheck(
    "Field of unregistered family (no check dictionary entry)", "unknown",
    False, KIND_NONE,
    "field_checks：该族未注册进控制字典（register_family 登记后方可被 "
    "gridmap 链路采用）—— 查询兜底，绝不冒充已核查。")


def field_check(family: str, field: str) -> FieldCheck:
    """查询 ``(family, field)`` 的核查条目。

    查找顺序：精确字段名 -> ``"*"`` 兜底 -> 未注册族兜底。
    返回值只读（:class:`FieldCheck` 为 frozen dataclass）。
    """
    fam = FIELD_CHECKS.get(family)
    if fam is None:
        return _UNREGISTERED_FAMILY
    return fam.get(field, fam.get("*", _UNREGISTERED_FAMILY))


def checked_families() -> tuple[str, ...]:
    """当前已完成核查（存在 checked=True 条目）的族名列表。"""
    out = []
    for fam, entries in FIELD_CHECKS.items():
        if any(fc.checked for fc in entries.values()):
            out.append(fam)
    return tuple(sorted(out))


def family_check_stats(family: str) -> dict[str, int]:
    """族内核查统计：``{"total", "checked", "unchecked"}``（不含 "*" 兜底）。"""
    entries = FIELD_CHECKS.get(family, {})
    named = {k: v for k, v in entries.items() if k != "*"}
    n_checked = sum(1 for fc in named.values() if fc.checked)
    return {"total": len(named), "checked": n_checked,
            "unchecked": len(named) - n_checked}


#: 字典 Markdown 文档的落盘位置（仓库内 docs/）。
DICT_DOC_RELPATH = "docs/eosop变量控制字典.md"


if __name__ == "__main__":                       # python -m eosop_pro.registry.field_checks
    from pathlib import Path as _Path

    _out = _Path(__file__).resolve().parents[2] / DICT_DOC_RELPATH
    _out.parent.mkdir(parents=True, exist_ok=True)
    # 字典文档是生成物，统一 LF（Windows 默认会翻译 CRLF，铁律见 MEMORY）
    _out.write_text(dump_markdown(), encoding="utf-8", newline="\n")
    print(f"control dictionary written: {_out}")
