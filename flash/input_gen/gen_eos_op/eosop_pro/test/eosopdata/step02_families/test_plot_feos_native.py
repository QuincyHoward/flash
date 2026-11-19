# -*- coding: utf-8 -*-
"""step02 —— ``feos_native`` 族（F4 FEOS 原生 *.feos）批量出图与**解码块场图契约**。

统一绘图模块 gridmap；产物落 ``_out/feos_native/``。

人工核查要点（用户 2026-09-15 规约：逐类型挨个核查）
------------------------------------------------
1. 网格点 —— ``_out/XX_<table_key>/_report.txt`` 的 ``axis`` 行给出
   点数 / 范围 / 单调性 / log-uniform。
   ⚠️ 本族格式特征（2026-11 定案）：``.feos`` 声明 NR/NT = 真实点数 + 1
   （**前导** ``Qstart=0.0`` 哨兵计入声明值）；解析器确定性切分后修剪 ——
   报告 axis 行的 N 即**修剪后**真实网格数；
2. 物理量物理意义 —— ✅ **16 块 + Qtot + Q 已定案解码**
   （FE-01_TABTOOLS.C::write_FEOS_format，R3 废除）；
3. 单位 —— 原生 cgs + eV（压强 dyn/cm2、能量/自由能 erg/g、熵 erg/g/eV）；
4. 认证标记 —— 全部命名条目 kind=source code（源码锚点）+ 未人工核查
   -> ``tags=uv``。

⚠️ 契约升级（2026-11-15，替代已废除的 raw 序列图契约）
----------------------------------------------------
旧契约因"payload 列序未定（R3）"只能画 raw vs index 序列图。
布局由 C 源码定案后，解析器输出 16 个命名二维块（P,E,S,F|Pe,Ee,Se,Fe|
Pi,Ei,Si,Fi|PTF,ETF,STF,FTF）+ Qtot + Q0..，gridmap 直接画**物理场彩图**
（轴 = 修剪后真实网格 rho × Te）。每族处理前 ``max_files=3`` 个可解析
``.feos`` 文件，故 ``n_plots >= 1``。

本族特有：``.feos`` 候选顺序 ``[feos_native, multi_eos]`` ——
``mat_Al-1.0/AL_eos.feos`` 与 ``AL_eos`` 字节相同（名 FEOS 实 SESAME），
走 F1 回退，与本族无关。已知边界：``mat_Others/SiO2.feos`` 为 3 位指数
粘连变体（``e+001``），解析器拒收（旧版同样拒收，非回归）。

产出（落 ``step02_families/_out/feos_native/``）
----------------------------------------
``XX_<table_key>/<field>_*.png``（解码块物理场彩图）/
``_report.txt``（轴网格 + 字段 uv 认证标注 + 出图清单）/
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

# ★ 16 块已定案解码；ne-T 派生（需 atomwt/zbar 映射）暂不启用 —— 保持 None。
ATOMWT = None

from eosopdata.step02_families._family_plot_common import (   # noqa: E402
    FAMILY_PATTERNS, run_family_plots)

FAMILY = "feos_native"
PATTERNS = FAMILY_PATTERNS[FAMILY]


def test_axes_documented_and_decoded_field_plotted():
    """轴网格照常入报告；解码块字段标记 uv；物理场彩图必须产出。"""
    r = run_family_plots(FAMILY, PATTERNS, atomwt=ATOMWT)
    if r is None:
        return                                  # 样品不在 -> skip（惰性发现）
    expect(r["reports"], f"{FAMILY} 报告未生成")
    txt = open(r["reports"][0], encoding="utf-8").read()
    expect_in("axis 'rho'", txt, "报告缺 rho 轴核查行")
    expect_in("axis 'Te'", txt, "报告缺 Te 轴核查行")
    expect_in("field ", txt, "报告缺字段（field）行")
    expect_in("Pi", txt, "报告应含解码块 Pi（16 块定案解码）")
    expect_in("Qtot", txt, "报告应含 Qtot（平均电离）")
    expect_in("tags=uv", txt, "解码块应为源码认证（非 uk）且未人工核查（uv）")
    # ── 解码块场图契约：布局定案 -> 物理场彩图 ──
    expect(r["n_plots"] >= 1,
           f"feos_native 应至少产出一个解码块场图，实得 {r['n_plots']} 张; "
           f"skipped={r['skipped'][:3]}")
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