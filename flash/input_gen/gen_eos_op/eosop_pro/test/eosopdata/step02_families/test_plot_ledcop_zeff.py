# -*- coding: utf-8 -*-
"""step02 —— ``ledcop_zeff`` 族（F5 LEDCOP 平均电离度 *.NoFree）批量出图。

统一绘图模块 gridmap；产物落 ``_out/ledcop_zeff/``。

人工核查要点（用户 2026-09-15 规约：逐类型挨个核查）
------------------------------------------------
1. 网格点 —— ``_out/XX_<table_key>/_report.txt`` 的 ``axis`` 行给出
   点数 / 范围 / 单调性 / log-uniform；
2. 物理量物理意义 —— ``field`` 行的 ``meaning='...'``；
3. 单位 —— ⚠️ F5 LEDCOP：温度轴 **keV**；``NoFree`` 是**无自由电子比例**
   的 Zbar 等价量（``CHARGE_FIELD_CANDIDATES`` 显式收录）；
4. 认证标记 —— rho/Te 有源（一级文档 docx Zeff 节：log 坐标 + keV）
   + 未核查 -> ``tags=uv``；NoFree/AvSqFree 值段待核 -> ``tags=uk,uv``。

本族特有：``NoFree`` 命中电离度场候选 —— 填入下方 ``ATOMWT`` 后自动追加
``<field>_ne-T.png`` 彩图（n_e = rho * N_A * Zbar / A）。

产出（落 ``step02_families/_out/ledcop_zeff/``）
----------------------------------------
``XX_<table_key>/<field>_<y>-<x>.png``（原生平面彩图）/
``<field>_ne-T.png``（仅当填了 ATOMWT）/ ``<field>_vs_*.png``（截断曲线）/
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

# ★ 经核实的平均原子量 (amu)：填入实数后自动启用 ne-T 彩图；
#   None = 文件未声明 A，按"不猜"纪律跳过 ne-T（_report.txt 写明原因）。
#   已知样品为 Al 的 NoFree 表（仅注释，未核实前不启用）：Al 26.9815385。
ATOMWT = None

from eosopdata.step02_families._family_plot_common import (   # noqa: E402
    FAMILY_PATTERNS, run_family_plots)

FAMILY = "ledcop_zeff"
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
