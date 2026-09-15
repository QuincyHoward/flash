# -*- coding: utf-8 -*-
"""step02 各族批量出图的**共享驱动**（每种文件类型一个文件夹一个脚本）。

分工
----
* 本模块只做「找样品 -> 调统一绘图模块 :mod:`eosop_pro.plotting.gridmap`
  -> 汇总报告」三件事；
* 各类型的文件夹（如 ``mpqeos/``）里放**各自独立的**
  ``test_plot_<type>.py``，产物统一落在**根级** ``_out/<type>/``
  （2026-09-15 第十一轮"下移一级"：族文件夹只放代码，产物全部收进
  根目录唯一的 ``_out/``，step02 根目录保持纯净）；
* **原始数据全量收集**（用户 2026-09-15 第十一轮规约）：同一类型
  **全部**名字匹配的文件（含解析失败者 —— 恰恰是它们最需要人工判断）
  原样复制到 ``_out/<type>/source_data/``，人工核查时图表与原始数据
  对照，不需要回 ``matter++`` 全树里翻；重名文件以父目录链改名避让；
* **多样品覆盖**：绘图/解析仍只处理**前 ``max_files``（默认 3）个**
  可解析文件（护栏不变，与全量收集解耦；此前只碰第一个 —— 全树
  29 个 ``.feos`` 只核查过 1 个）；
* 字段的「物理意义 / 单位 / 认证标记（tags=uk,uv | tags=uv | 省略）」
  来自 :mod:`eosop_pro.registry.field_checks`（eosop 家族**大型控制字典**，
  标记只有 ``uk``=无来源确认 / ``uv``=未人工核查 两个，有源且已核查
  则整体省略 —— 当前仅 cn4；来源白名单含文件内声明条目：
  ledcop_atomic rho/Te/Ross/Planck、coldopacity Eph/miu/"*"、
  hugoniot 全部），逐行写进每张表的 ``_report.txt``；图上 colorbar 与
  **x/y 轴**（含 ne-T 派生轴，经 ``derived_axes`` 登记）一律带同规约标记。

ne-T 派生轴的诚实边界
--------------------
n_e = rho * N_A * Zbar / A 需要**平均原子量 A**；除 cn4（ionmix）外，
绝大多数族的文件**不声明 A** —— 此时 ne-T 彩图**跳过并在报告写明原因**，
绝不猜测（数值本身照画 rho-T 平面 + raw 兜底图，见 gridmap）。若人工
核实了某族的 A，把 ``test_plot_<type>.py`` 顶部的 ``ATOMWT`` 从 ``None``
改为实数即可自动启用。
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

# --- path bootstrap（与各测试文件相同的头两行约定） ---
_HERE = Path(__file__).resolve().parent          # step02_families/
_TEST_DIR = _HERE.parent                         # eosopdata/
_REPO_ROOT = _TEST_DIR.parent                    # eosop_pro/
for _p in (str(_TEST_DIR), str(_REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from eosopdata._samples import (  # noqa: E402
    find_all_matching,
    find_parseable_many,
    matter_dir,
)

#: 各族样品模式（与 test_family_extract.py 保持一致；改动需两处同步）。
FAMILY_PATTERNS: dict[str, tuple[str, ...]] = {
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

#: 报告缓存（同进程内每族只跑一次批量出图；多个测试函数共享结果）。
_REPORT_CACHE: dict[tuple[str, str, str, int], dict | None] = {}


def run_family_plots(family: str, patterns: tuple[str, ...], *,
                     atomwt: float | None = None,
                     max_groups: int = 3, max_tables: int = 6,
                     max_files: int = 3) -> dict | None:
    """跑一族的批量出图，返回报告 dict；样品不可发现时返回 ``None``（skip）。

    * 产物落位：``step02_families/_out/<family>/``（第十一轮"下移一级"）；
    * 同一类型**全部**名字匹配文件原样复制到 ``_out/<family>/source_data/``
      （全量收集；重名以父目录链改名避让，解析样品保留原名）；
    * 绘图/解析仍只处理前 ``max_files`` 个可解析文件（护栏不变）。
    """
    key = (family, "|".join(patterns), repr(atomwt), max_files)
    if key in _REPORT_CACHE:
        return _REPORT_CACHE[key]

    found = find_parseable_many(family, patterns, max_files=max_files)
    if not found:
        _REPORT_CACHE[key] = None
        return None

    outdir = _HERE / "_out" / family
    src_dir = outdir / "source_data"
    src_dir.mkdir(parents=True, exist_ok=True)

    # -- 全量收集（用户 2026-09-15 第十一轮）：名字匹配的全部文件 --
    all_matched = find_all_matching(patterns)
    parsed_paths = {p for p, _ in found}
    used: set[str] = set()
    dst_of: dict[Path, str] = {}
    for p in parsed_paths:                    # 解析样品优先占用原名
        dst_of[p] = p.name
        used.add(p.name)
    matter_root = matter_dir()
    for src_path in all_matched:
        if src_path in dst_of:
            continue
        name = src_path.name
        if name in used:                      # 重名 -> 父目录链改名避让
            rel = src_path.relative_to(matter_root)
            name = "__".join(rel.parts[-3:])
            k = 2
            while name in used:
                name = f"{k:02d}__{src_path.name}"
                k += 1
        dst_of[src_path] = name
        used.add(name)
    copied: list[str] = []
    for src_path in all_matched:
        dst = src_dir / dst_of[src_path]
        if not (dst.exists()
                and dst.stat().st_size == src_path.stat().st_size):
            shutil.copyfile(src_path, dst)    # 原样复制（同体积跳过=幂等）
        copied.append(str(dst))

    all_tables: list = []
    for _src_path, tables in found:
        all_tables.extend(tables)

    from eosop_pro.plotting.gridmap import plot_table_all_fields
    report = plot_table_all_fields(
        all_tables, outdir, family=family, atomwt=atomwt,
        max_groups=max_groups, max_tables=max_tables)
    report["source"] = str(found[0][0])
    report["sources"] = [str(p) for p, _ in found]
    report["source_copies"] = copied
    report["n_source_all"] = len(all_matched)
    report["n_source_parsed"] = len(found)
    report["outdir"] = str(outdir)
    _REPORT_CACHE[key] = report
    return report
