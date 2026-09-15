# -*- coding: utf-8 -*-
"""字典驱动标签统一出口（用户 2026-09-15 第十二轮裁定）。

定位
----
一切绘图/报告的物理量标签（坐标轴 / colorbar / 曲线 ylabel / 报告行）
**一律经本模块**从控制字典 :mod:`..registry.field_checks` **实时**取
物理意义（``meaning``）、单位（``unit``）与认证标记（``uk, uv`` /
``uv`` / 省略）。用户人工核查后只改 ``field_checks.py`` 对应条目
（翻 ``checked`` / 修 ``meaning`` / ``unit``），**下一次出图自动同步** ——
绘图代码里不允许存在第二份硬编码标签（守护：
``test/eosopdata/step02_families/test_plot_labels.py`` 扫描绘图模块
源码不得再出现硬编码物理量标签）。

标签格式（与 field_checks 模块头规约一致；长/短双轨）
------------------------------------------------------
::

    field_label("mpqeos", "P")     # -> "P (Mbar), uv"（默认短标签）
    field_label("mpqeos", "P", long=True)  # -> "Pressure (file in GPa) (Mbar), uv"
    field_label("ionmix", "T")     # -> "T (eV)"（已核查，标记省略）

* **短/长双轨**（用户 2026-09-15 晚裁定）—— 条目含 ``short``（物理量
  标准简写）与 ``meaning``（完整表述）两个标签；**绘图默认用短标签**
  （避免长标签遮挡图面），报告/人工核查场景用 ``long=True``。两者都
  带 uk/uv 标记。``short`` 为空串（动态注册族）回退 ``meaning``；
* **未登记名**（仅命中 ``"*"`` 兜底或未注册族兜底）回退用字段名本身
  （去掉 coldopacity 式 ``#`` 前缀），绝不冒充字典语义；
* ``unit`` —— :func:`display_unit`：解析器逐文件实测单位（如 hugoniot
  的 ``# name [unit]`` 头）优先，其次字典 ``unit``，两者皆无写
  ``unknown``（不猜测）；
* 标记 —— :func:`tags_of`（= ``tags_label(field_check(...))``），只有
  ``uk``（无来源确认）/ ``uv``（未人工核查）两个，有源且已核查整体
  省略（当前仅 cn4/ionmix 全 18 块）。

查找顺序（:func:`_entry`）
--------------------------
精确字段名 -> 去 ``#`` 前缀（coldopacity 的 ``"#Eph"`` -> ``"Eph"``）->
``Te``/``tele`` -> ``T``（ionmix 的温度轴登记名）-> ``"*"`` 兜底 ->
未注册族兜底（``field_check`` 自带）。

cn4 泛化（第十二轮指令 3；第十三轮 cn4/ 扁平化）
------------------------------------------------
跨族转换出的 :class:`~..parsers.cn4_io.CN4Table` 带 ``origin_family``
（来源族名）。cn4 路径图（:mod:`.cn4_paths`）的标签用
:func:`cn4_tags` 回查**来源族**的认证标记并追加后缀，让"这批数据的
核查状态"在图上持续可见；原生 cn4 数据全部来自 ionmix（18 块
``checked=True``），标记整体省略。cn4 网格绘图（:mod:`.cn4_plots`）
保留 LaTeX 数学排版标签，但其量名与字典的对应关系由
``test_plot_labels`` 一致性测试锁定（键 ⊆ ionmix 登记键 ∪ 代码派生量）。
"""

from __future__ import annotations

__all__ = ["field_label", "display_unit", "tags_of", "widest_tags",
           "cn4_tags", "CN4_SOURCE_FIELD", "FAMILY_ALIASES"]

#: 族名别名：解析/绘图链路使用的族名 -> 控制字典登记名。
#: cn4 体系的 ParsedTable ``family == "cn4"``，字典登记名是 ``ionmix``。
FAMILY_ALIASES: dict[str, str] = {"cn4": "ionmix"}

#: 温度轴别名：其他族登记 ``Te``，ionmix 登记名为 ``T``。
_TE_ALIAS: frozenset[str] = frozenset({"Te", "tele"})

#: 认证标记的"最差程度"排序（widest = 最该被看见的标记）。
_TAGS_RANK: dict[str, int] = {"": 0, "uv": 1, "uk": 2, "uk, uv": 3}

#: cn4 量名 -> 来源族字典里的候选字段名（:func:`cn4_tags` 用）。
#: 只列"物理意义明确等价"的名字（与 cn4_io._FOREIGN_FIELD_ALIASES 同一
#: 保守立场）；无对应概念（cv 分量 / 偏导量 / Us,Up,V 等路径派生量）
#: 为空元组 -> 调用方回退 :func:`widest_tags`（族级最宽标记）。
CN4_SOURCE_FIELD: dict[str, tuple[str, ...]] = {
    "T":       ("Te", "T"),
    "tele":    ("Te", "T"),
    "nion":    ("rho",),
    "rho":     ("rho",),
    "nele":    ("n_e",),
    "P":       ("P",),
    "p_ion":   ("P",),
    "p_ele":   ("P",),
    "E":       ("E",),
    "e_ion":   ("E",),
    "e_ele":   ("E",),
    "zbar":    ("Z", "zbar", "Zeff", "NoFree", "Zbar"),
    "cv_ion":  (),
    "cv_ele":  (),
    "dzdt":    (),
    "dpion_dt": (),
    "dpele_dt": (),
    "deion_dn": (),
    "deele_dn": (),
    "opac_rosseland": ("Ross", "Rosseland", "kappa"),
    "opac_planck_abs": ("Planck", "kappa"),
    "opac_planck_ems": ("Planck", "kappa"),
}

#: 原生 cn4 来源（无标记可加：数据全来自 ionmix，已核查）。
_CN4_NATIVE: frozenset[str] = frozenset({"", "ionmix", "cn4"})


def _entries(family: str):
    """族名（经别名归一）-> ``(登记名, entries | None)``。"""
    from ..registry.field_checks import FIELD_CHECKS
    fam = FAMILY_ALIASES.get(family, family)
    return fam, FIELD_CHECKS.get(fam)


def _entry(family: str, name: str):
    """查 ``(family, name)`` 的字典条目。

    Returns:
        ``(FieldCheck, 登记族名, 命中键 | None)``；``命中键 is None``
        表示只命中 ``"*"`` 兜底或未注册族兜底（标签回退用字段名本身）。
    """
    from ..registry.field_checks import field_check
    fam, entries = _entries(family)
    if entries is not None:
        for key in (name, str(name).lstrip("#")):
            if key in entries:
                return entries[key], fam, key
        if name in _TE_ALIAS and "T" in entries:
            return entries["T"], fam, "T"
        if "*" in entries:
            return entries["*"], fam, None
    return field_check(family, name), fam, None


def display_unit(family: str, name: str, parser_unit: str | None = None) -> str:
    """单位显示串：**解析器逐文件实测单位优先**（如 hugoniot 逐文件头
    声明），其次字典 ``unit``，两者皆无写 ``unknown``（不猜测）。"""
    if parser_unit:
        return str(parser_unit)
    fc, _fam, _key = _entry(family, name)
    return fc.unit or "unknown"


def tags_of(family: str, name: str) -> str:
    """``(family, name)`` 的认证标记（``"uk, uv"`` / ``"uv"`` / ``""``）。"""
    from ..registry.field_checks import tags_label
    fc, _fam, _key = _entry(family, name)
    return tags_label(fc)


def field_label(family: str, name: str, *,
                parser_unit: str | None = None,
                long: bool = False) -> str:
    """★ 物理量标签统一出口：``"Label (unit)"`` + 认证标记后缀。

    * **长/短双轨**（用户 2026-09-15 晚裁定）：默认用字典登记的
      **短标签** ``short``（空串回退 ``meaning``）；``long=True`` 用长
      标签 ``meaning``（报告/人工核查场景）。两者都带认证标记；
    * 标签取字典登记值；未登记名（兜底命中）回退字段名本身
      （去 ``#`` 前缀）—— 绝不把兜底语义冒充成登记语义；
    * ``unit`` 走 :func:`display_unit`（实测优先 -> 字典 -> unknown）；
    * 标记非空时追加 ``", <tags>"``（有源且已核查则整体省略）。

    用户人工核查后只改 ``field_checks.py``，下一次出图自动同步 ——
    本函数没有任何缓存或第二份标签表。
    """
    fc, _fam, key = _entry(family, name)
    if key is not None:
        base = fc.meaning if long else (getattr(fc, "short", "") or fc.meaning)
    else:
        base = str(name).lstrip("#")
    unit = display_unit(family, name, parser_unit)
    core = f"{base} ({unit})"
    tags = tags_of(family, name)
    return f"{core}, {tags}" if tags else core


def widest_tags(family: str) -> str:
    """族内**最宽**认证标记（含 ``"*"`` 兜底条目）—— 最该被看见的标记。

    未注册族返回 ``"uk, uv"``（与 ``field_check`` 的未注册兜底一致，
    绝不让未登记数据冒充已核查）。
    """
    from ..registry.field_checks import FIELD_CHECKS, tags_label
    fam, entries = _entries(family)
    if not entries:
        return "uk, uv"
    best, rank = "", -1
    for fc in entries.values():
        t = tags_label(fc)
        r = _TAGS_RANK.get(t, 0)
        if r > rank:
            best, rank = t, r
    return best


def cn4_tags(origin_family: str, cn4_field: str) -> str:
    """跨族转换 cn4 表的标签标记后缀来源（用户 2026-09-15 第十二轮规约）。

    * ``origin_family`` 为空 / ``ionmix`` / ``cn4`` -> ``""``（原生 cn4
      数据全部来自 ionmix 的 18 个 ``checked=True`` 条目，标记省略）；
    * 其他来源族 -> 按 :data:`CN4_SOURCE_FIELD` 候选名查该族字典条目的
      标记，取**最宽**者；无候选命中（Us/Up/V/cv 等无对应概念）回退
      :func:`widest_tags`；
    * 来源族本身未注册字典 -> ``"uk, uv"``（保守，绝不冒充已核查）。
    """
    from ..registry.field_checks import FIELD_CHECKS, tags_label
    fam = str(origin_family or "")
    if fam in _CN4_NATIVE:
        return ""
    entries = FIELD_CHECKS.get(fam)
    if not entries:
        return "uk, uv"
    hits = [tags_label(entries[nm])
            for nm in CN4_SOURCE_FIELD.get(cn4_field, ())
            if nm in entries]
    if hits:
        return max(hits, key=lambda t: _TAGS_RANK.get(t, 0))
    return widest_tags(fam)
