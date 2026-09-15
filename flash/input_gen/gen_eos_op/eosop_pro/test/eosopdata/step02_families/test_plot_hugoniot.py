# -*- coding: utf-8 -*-
"""step02 —— ``hugoniot`` 族（F6 雨贡纽曲线 *.hug，1D）批量出图。

统一绘图模块 gridmap；产物落 ``_out/hugoniot/``。

人工核查要点（用户 2026-09-15 规约：逐类型挨个核查）
------------------------------------------------
1. 网格点 —— ``_out/XX_<table_key>/_report.txt`` 的 ``axis`` 行给出
   点数 / 范围 / 单调性 / log-uniform（本族 x 轴为密度 ``Rho``）；
2. 物理量物理意义 —— ``field`` 行的 ``meaning='...'``；
3. 单位 —— ⚠️ F6 hugoniot **逐文件内嵌声明**（解析器 ``unit_source``
   给出来源行）；P 常见 Mbar / GPa 混用，以文件自身声明为准；
4. 认证标记 —— 本族条目有源（逐文件 '# name [unit]' 头声明）+ 未核查
   -> ``tags=uv``；人工核查后改字典 checked 并重生成字典文档。

产出（落 ``step02_families/_out/hugoniot/``）
----------------------------------------
``XX_<table_key>/<field>_curve.png``（每场一条 log-log 曲线，vs Rho）/
``_report.txt``（核查报告）。
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
from _runner import expect, expect_in, main                       # noqa: E402

sys.path.insert(0, os.path.dirname(_d))                        # test/
sys.path.insert(0, os.path.dirname(os.path.dirname(_d)))       # repo root

# ★ 经核实的平均原子量 (amu)：1D 雨贡纽曲线无电离度场，ne-T 不可导 ——
#   保持 None 即可。
ATOMWT = None

from eosopdata.step02_families._family_plot_common import (   # noqa: E402
    FAMILY_PATTERNS, run_family_plots)

FAMILY = "hugoniot"
PATTERNS = FAMILY_PATTERNS[FAMILY]


def test_batch_plots_produced():
    """批量出图至少 1 张，且每个产物文件真实存在、非空。"""
    r = run_family_plots(FAMILY, PATTERNS, atomwt=ATOMWT)
    if r is None:
        return                                  # 样品不在 -> skip（惰性发现）
    expect(r["n_plots"] >= 1,
           f"{FAMILY} 未产出任何图; skipped={r['skipped'][:3]}")
    from pathlib import Path
    for p in r["plots"]:
        fp = Path(p)
        expect(fp.is_file() and fp.stat().st_size > 1000, f"产物无效: {p}")


def test_report_covers_grid_fields_and_check_status():
    """``_report.txt`` 必须含网格行 / 字段核查行（含 tags=uk/uv 认证标记）/ 溯源行。"""
    r = run_family_plots(FAMILY, PATTERNS, atomwt=ATOMWT)
    if r is None:
        return
    expect(r["reports"], f"{FAMILY} 报告未生成")
    txt = open(r["reports"][0], encoding="utf-8").read()
    expect_in("axis ", txt, "报告缺网格（axis）行")
    expect_in("field ", txt, "报告缺字段（field）行")
    expect_in("tags=", txt, "报告缺认证标记（uk|uv）")
    expect_in("uv", txt, "报告缺未核查（uv）标记")
    expect_in("source_relpath", txt, "报告缺溯源行")


def test_source_data_copied():
    """原始数据文件必须复制到 _out/source_data/（核查对照，用户规约）。"""
    r = run_family_plots(FAMILY, PATTERNS, atomwt=ATOMWT)
    if r is None:
        return
    expect(r.get("source_copies"), "缺 source_data 副本清单")
    from pathlib import Path
    for c in r["source_copies"]:
        fp = Path(c)
        expect(fp.is_file() and fp.stat().st_size > 0,
               f"原始数据副本无效: {c}")
        expect(fp.parent.name == "source_data",
               f"副本应落 _out/source_data/: {c}")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
