# -*- coding: utf-8 -*-
"""step02 —— ``feos_native`` 族（F4 FEOS 原生 *.feos）批量出图与 **raw 序列图契约**。

统一绘图模块 gridmap；产物落 ``_out/feos_native/``。

人工核查要点（用户 2026-09-15 规约：逐类型挨个核查）
------------------------------------------------
1. 网格点 —— ``_out/XX_<table_key>/_report.txt`` 的 ``axis`` 行给出
   点数 / 范围 / 单调性 / log-uniform。
   ⚠️ 本族已知格式特征：``.feos`` 头部声明的 NR/NT 比真实网格**多 1**
   （尾部一个 ``0.0`` 哨兵）；解析器 ``feos_native.grid_length()`` 用
   严格递增前缀裁剪 —— 报告 axis 行的 N 即**裁剪后**网格数；
2. 物理量物理意义 —— ⚠️ **payload 当前不可解码**（见下）；
3. 单位 —— 头部声明 ``format:FEOS (cgs + eV)``；
4. 认证标记 —— 全部条目无可指认一级来源（FEOS PDF 抽取伪影在案，
   见字典来源详述）+ 未核查 -> ``tags=uk,uv``。

⚠️ raw 序列图契约（2026-09-15 晚，用户规约"数值可读即可画"确立）
----------------------------------------------------
解析器对全部 29 个 feos 文件都只产出 ``raw_values``
（meaning = "Undecoded payload (PDF extraction artefacts; column
semantics not recoverable)"）—— payload 的**列语义与排布无法从现有
PDF 文档恢复**，因此带物理意义的场彩图仍不可能。

但按用户规约"即使物理量意义及单位未知，也应能读取数值、绘制数值"，
gridmap 对语义映射不可行的字段画 **raw values vs element index**
序列图（``raw_values_raw_vs_index.png``，图上标注 semantics unknown），
不再静默零图。每族处理前 ``max_files=3`` 个可解析 ``.feos`` 文件，
故 ``n_plots >= 1``（每表 1 张 raw 序列图）。

数学佐证（payload 长度 = 声明NR × nTe × 18 个量）：

* Al.feos：192 × 69 × 18 = 238464 ✓
* B/Ba/Bi/Cl/Co/Cr/Dy/F/K/N.feos 等：123 × 101 × 18 = 223614 ✓
* Cerium.feos：123 × 97 × 18 = 214758 ✓

18 个量的身份（P/E/...？）与排布（块优先 / 行优先 / 交错？）仍无文档
依据 —— raw 序列图**只展示数值分布**，绝不给轴赋予物理语义。将来若从
上游文档恢复列语义并升级解析器，本测试需同步改约（补场彩图契约）。

本族特有：``.feos`` 候选顺序 ``[feos_native, multi_inverted_eos]`` ——
``mat_Al-1.0/AL_eos.feos`` 与 ``AL_eos`` 字节相同（名 FEOS 实 SESAME），
走 F1 回退，与本族无关。

产出（落 ``step02_families/_out/feos_native/``）
----------------------------------------
``XX_<table_key>/raw_values_raw_vs_index.png``（raw 序列图）/
``_report.txt``（轴网格 + raw_values uk/uv 认证标注 + 出图清单）/
``source_data/*.feos``（原始数据副本，核查对照用）。
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
from _runner import expect, expect_eq, expect_in, main            # noqa: E402

sys.path.insert(0, os.path.dirname(_d))                        # test/
sys.path.insert(0, os.path.dirname(os.path.dirname(_d)))       # repo root

# ★ payload 未解码、无电离度场，ne-T 不可导 —— 保持 None 即可。
ATOMWT = None

from eosopdata.step02_families._family_plot_common import (   # noqa: E402
    FAMILY_PATTERNS, run_family_plots)

FAMILY = "feos_native"
PATTERNS = FAMILY_PATTERNS[FAMILY]


def test_axes_documented_and_raw_sequence_plotted():
    """轴网格照常入报告；raw_values 标记 uk/uv；raw 序列图必须产出。"""
    r = run_family_plots(FAMILY, PATTERNS, atomwt=ATOMWT)
    if r is None:
        return                                  # 样品不在 -> skip（惰性发现）
    expect(r["reports"], f"{FAMILY} 报告未生成")
    txt = open(r["reports"][0], encoding="utf-8").read()
    expect_in("axis 'rho'", txt, "报告缺 rho 轴核查行")
    expect_in("axis 'Te'", txt, "报告缺 Te 轴核查行")
    expect_in("raw_values", txt, "报告缺 raw_values（未解码 payload）字段行")
    expect_in("tags=uk,uv", txt, "raw_values 应无源（uk）且未核查（uv）")
    expect_in("uv", txt, "raw_values 应未核查（uv）")
    # ── raw 序列图契约：payload 未解码 -> 无物理语义彩图，但数值可画 ──
    expect(r["n_plots"] >= 1,
           f"feos_native 应至少产出 raw 序列图（数值可读即可画），"
           f"实得 {r['n_plots']} 张; skipped={r['skipped'][:3]}")
    expect_in("raw_vs_index", txt, "报告出图清单应含 raw_vs_index 序列图")
    from pathlib import Path
    for p in r["plots"]:
        fp = Path(p)
        expect(fp.is_file() and fp.stat().st_size > 1000, f"产物无效: {p}")


def test_report_covers_grid_fields_and_check_status():
    """``_report.txt`` 必须含网格行 / 字段 tags=uk/uv 认证行 / 溯源行。"""
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
    """原始 .feos 必须复制到 _out/source_data/（核查对照，用户规约）。"""
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