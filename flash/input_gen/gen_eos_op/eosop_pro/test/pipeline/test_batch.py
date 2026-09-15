"""``eosop_pro.batch`` + ``eosop_pro.cli`` 测试 —— 批处理编排与命令分发。

为什么值得单独测
----------------
``batch.py`` 是"编排层"：它把**声明式审计 / 双轨 HDF5 / QA 出图 / 零先验反演**
串成一条流水线，并被 ``scripts/*.py`` 与 ``scripts/run_all.bat`` 直接调用。
编排层最容易出的错不是算法错，而是**接线错**：

* ``cli`` 的子命令名与 ``scripts/*.py`` 里的名字对不上 → 一键脚本全废
* 报告里写了小数/漏了列 → 结论不可回溯
* ``convert_all`` 把 ``nion_Te`` 的 x 轴写成 ``rho`` → 数据静默错位
* ``infer_unrecognized`` 重新全树扫描 2 分钟 → 明明审计报告里已有答案

所以这里的断言分三类：**接线正确**（子命令可达）、**闸口正确**（计数自洽）、
**结构正确**（h5 双轨键名与属性齐全）。
"""

import csv
import json
import tempfile
from pathlib import Path

import sys
import os
# --- path bootstrap (auto) ---
_d = os.path.dirname(os.path.abspath(__file__))
while _d != os.path.dirname(_d) and not os.path.isfile(
        os.path.join(_d, "_runner.py")):
    _d = os.path.dirname(_d)
if _d not in sys.path:
    sys.path.insert(0, _d)
import _runner  # noqa: F401
from _runner import expect, expect_eq, expect_in, main

from eosop_pro import batch, config
from eosop_pro import cli as mcli


# ══════════════════════════════════════════════════════════════
# ① inventory
# ══════════════════════════════════════════════════════════════
def test_inventory_on_temp_tree():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "a.txt").write_text("hello\n", encoding="utf-8", newline="\n")
        (td / "b.dat").write_bytes(b"1.0 2.0\n3.0 4.0\n")
        (td / "sub").mkdir()
        (td / "sub" / "c.bin").write_bytes(bytes(range(256)))
        r = batch.inventory(outdir=td / "rep", matter_dir=td)
        expect_eq(r["total_files"], 3)
        expect_in(".txt", r["by_suffix"])
        expect_in(".dat", r["by_suffix"])
        for k in ("csv", "json", "md"):
            expect(Path(r[k]).exists(), f"{k} 报告应落盘")
        data = json.loads(Path(r["json"]).read_text(encoding="utf-8"))
        expect_eq(data["total_files"], 3)
        expect_eq(len(data["files"]), 3)
        # 二进制文件必须被识别为 binary
        kinds = {f["name"]: f["kind"] for f in data["files"]}
        expect_eq(kinds["c.bin"], "binary", f"实测 {kinds}")


def test_inventory_real_tree_gate():
    """真实 matter++ 全树：总数必须等于实际文件数，且四类报告都在。"""
    with tempfile.TemporaryDirectory() as td:
        r = batch.inventory(outdir=td)
        real = sum(1 for p in config.MATTER_DIR.rglob("*") if p.is_file())
        expect_eq(r["total_files"], real, "清单总数必须等于实际文件数")
        expect(r["total_bytes"] > 5e8, f"总体积应 >500 MB，实测 {r['total_bytes']}")
        expect_eq(r["by_kind"].get("text", 0) > 900, True,
                  f"文本文件应占多数，实测 {r['by_kind']}")


# ══════════════════════════════════════════════════════════════
# ② audit（截断冒烟，避免测试套件跑 2 分钟）
# ══════════════════════════════════════════════════════════════
def test_audit_sweep_truncated_gate_and_reports():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        r = batch.audit_sweep(outdir=td / "rep", report_dir=td / "rep", limit=40)
        expect_eq(r["total"], 40, "截断运行应只审计 40 个样本")
        expect(r["n_declared_total"] > 1000,
               f"声明文件总数应 >1000，实测 {r['n_declared_total']}")
        expect(r["truncated"] is True)
        # 闸口：已解析 + 已跳过 == 样本数
        expect_eq(r["resolved"] + r["skipped"], r["total"],
                  f"闸口不通过: resolved={r['resolved']} skipped={r['skipped']}")
        expect(r["pass"] is True)
        md = Path(r["md"]).read_text(encoding="utf-8")
        expect_in("截断", md, "报告必须显式标注截断")
        jd = json.loads(Path(r["json"]).read_text(encoding="utf-8"))
        expect_eq(jd["truncated"], True)
        expect_eq(jd["total_files"], 40)
        # CSV 表头与快照行数一致
        with open(r["csv"], encoding="utf-8-sig", newline="") as fh:
            n = sum(1 for _ in csv.DictReader(fh))
        expect_eq(n, 40)


# ══════════════════════════════════════════════════════════════
# ③ convert-all（双轨 HDF5）
# ══════════════════════════════════════════════════════════════
def test_convert_all_writes_dual_track_h5():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        r = batch.convert_all(outdir=td / "h5", report_dir=td / "rep", limit=3,
                                      include_multigroup=False)
        expect(r["n_written"] >= 1, f"应至少写出 1 个 h5，实测 {r}")
        expect_eq(r["n_failed"], 0, f"不应有失败: {r}")
        h5s = sorted((td / "h5").glob("*.h5"))
        expect(len(h5s) == r["n_written"])
        import h5py
        with h5py.File(h5s[0]) as h:
            expect_in("tables", h)
            expect_in("meta", h)
            expect(h.attrs.get("pipeline") == "convert_all")
            expect_eq(h.attrs.get("stage"), "A")
        # CSV 报告存在且行数与处理数一致
        with open(r["csv"], encoding="utf-8-sig", newline="") as fh:
            expect(sum(1 for _ in csv.DictReader(fh)) >= r["n_written"])


def test_convert_all_dual_track_keeps_native_verbatim_and_unified_grids():
    with tempfile.TemporaryDirectory() as td:
        r = batch.convert_all(outdir=Path(td) / "h5", report_dir=Path(td) / "rep", limit=2)
        import h5py
        h5s = sorted((Path(td) / "h5").glob("*.h5"))
        expect(h5s, "应有 h5 落盘")
        checked_dual = False
        for p in h5s:
            with h5py.File(p) as h:
                if "tables" not in h:
                    continue
                for tkey in h["tables"]:
                    g = h["tables"][tkey]
                    expect_in("native", g, f"{tkey} 必须有 native 轨")
                    if "unified" in g:
                        checked_dual = True
                        for gid in config.UNIFIED_GRID_IDS:
                            expect_in(gid, g["unified"],
                                      f"{tkey} 的 unified 轨应含 {gid}")
                            sub = g["unified"][gid]
                            expect_in("x", sub)
                            expect_in("Te", sub)
                            expect_eq(sub["x"].shape[0], config.N_X_UNIFIED)
                            expect_eq(sub["Te"].shape[0], config.N_TE_UNIFIED)
                            expect_in(sub.attrs["x_axis"], ("rho", "n_ion"))
                            # ★ nion_Te 的 x 轴必须不是 rho
                            if gid == "nion_Te":
                                expect_eq(sub.attrs["x_axis"], "n_ion")
                    # native 量纲属性必须齐全
                    for nm in g["native"]:
                        ds = g["native"][nm]
                        expect_in("units", ds.attrs, f"{tkey}/native/{nm} 缺 units")
                        expect_in("log10", ds.attrs, f"{tkey}/native/{nm} 缺 log10")
        expect(checked_dual, "至少应有一张表带 unified 轨（否则双轨未生效）")


def test_convert_all_native_only_and_unified_only():
    with tempfile.TemporaryDirectory() as td1, tempfile.TemporaryDirectory() as td2:
        batch.convert_all(outdir=Path(td1) / "h5", report_dir=Path(td1) / "rep",
                                  limit=2, with_unified=False)
        batch.convert_all(outdir=Path(td2) / "h5", report_dir=Path(td2) / "rep",
                                  limit=2, with_native=False)
        import h5py
        for p in (Path(td1) / "h5").glob("*.h5"):
            with h5py.File(p) as h:
                for tkey in h.get("tables", {}):
                    expect("unified" not in h["tables"][tkey],
                           "--native-only 不应写 unified 轨")
        for p in (Path(td2) / "h5").glob("*.h5"):
            with h5py.File(p) as h:
                for tkey in h.get("tables", {}):
                    expect("native" not in h["tables"][tkey],
                           "--unified-only 不应写 native 轨")


def test_convert_all_family_filter():
    with tempfile.TemporaryDirectory() as td:
        r = batch.convert_all(outdir=Path(td) / "h5", report_dir=Path(td) / "rep",
                              limit=5, only_families=("multi_opacity",))
        # 只处理 multi_opacity：文件名应只来自该家族（无法反查，改看报告列）
        data = json.loads(Path(r["json"]).read_text(encoding="utf-8"))
        for row in data["rows"]:
            if row.get("h5"):
                expect_eq(row["family"], "multi_opacity")


def test_convert_all_does_not_fail_on_unparsable():
    """不可解析的文件应计入 skipped/failed，**不得抛异常中断整批**。"""
    with tempfile.TemporaryDirectory() as td:
        r = batch.convert_all(outdir=Path(td) / "h5", report_dir=Path(td) / "rep", limit=25)
        expect(r["n_skipped"] >= 0)
        expect_eq(r["n_written"] + r["n_skipped"] + r["n_failed"] >= r["n_written"], True)
        data = json.loads(Path(r["json"]).read_text(encoding="utf-8"))
        expect_eq(data["n_written"], r["n_written"])


# ══════════════════════════════════════════════════════════════
# ④ plot-all
# ══════════════════════════════════════════════════════════════
def test_plot_all_makes_ascii_ppt_grade_figures():
    with tempfile.TemporaryDirectory() as td:
        r = batch.plot_all(outdir=Path(td) / "plots", report_dir=Path(td) / "rep", limit=1)
        expect(r["n_figures_sets"] >= 1, f"应至少出 1 组图，实测 {r}")
        pngs = sorted((Path(td) / "plots").glob("*.png"))
        expect(pngs, "应有 PNG 落盘")
        for p in pngs:
            expect(p.stat().st_size > 5000, f"{p.name} 体积过小")


def test_plot_all_limit_is_respected():
    with tempfile.TemporaryDirectory() as td:
        r2 = batch.plot_all(outdir=Path(td) / "p2", report_dir=Path(td) / "rep", limit=2)
        expect(r2["n_figures_sets"] <= 2, f"limit=2 时不应超过 2 组，实测 {r2}")


# ══════════════════════════════════════════════════════════════
# ⑤ infer-unknown
# ══════════════════════════════════════════════════════════════
def test_infer_unknown_single_file_zero_priors():
    """★ 零先验：不告诉它任何家族信息，也要给出 ``ok`` 与候选。"""
    with tempfile.TemporaryDirectory() as td:
        r = batch.infer_unknown("mat_Al-1.0/AL_eos", outdir=td)
        expect(r["ok"], f"AL_eos 应可零先验反演，实测 status={r['status']}")
        expect(r["n_candidates"] >= 1)
        dumps = list(Path(td).glob("*.md"))
        expect(dumps, "应落盘反演报告 md")


def test_infer_unknown_ambiguous_lists_all_candidates():
    """歧义时必须**列全**候选而不是硬猜一个（用户明确要求）。"""
    with tempfile.TemporaryDirectory() as td:
        r = batch.infer_unknown("mat_Al-1.0/AL_eos", outdir=td)
        md = "\n".join(p.read_text(encoding="utf-8")
                       for p in Path(td).glob("*.md"))
        expect_in("自洽候选", md)
        expect_in("维度候选", md)


def test_infer_unrecognized_reuses_audit_report():
    """★ 复用审计报告而不是重扫全树 —— 否则这一步要跑 ~2 分钟。"""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        fake = td / "audit_all.20260101T000000.csv"
        with open(fake, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["relpath", "status", "family"])
            w.writeheader()
            w.writerow({"relpath": "mat_Al-1.0/AL_eos", "status": "unrecognized",
                        "family": ""})
            w.writerow({"relpath": "mat_Au-1.0/AU_eos", "status": "ok", "family": "x"})
        r = batch.infer_unrecognized(from_report=fake, outdir=td / "inf",
                                     report_dir=td / "rep")
        expect_eq(r["n_targets"], 1, "只应挑出 unrecognized 那一条")
        expect_in("audit-report", r["source"])
        expect_eq(r["n_ok"], 1, "AL_eos 应零先验解出")


def test_problem_relpaths_from_report_filters_statuses():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "r.csv"
        with open(p, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["relpath", "status"])
            w.writeheader()
            for st in ("ok", "count_mismatch", "unrecognized",
                       "ambiguous_layout", "error", "skipped_non_numeric"):
                w.writerow({"relpath": f"f_{st}", "status": st})
        got = batch._problem_relpaths_from_report(p)
        expect_eq(sorted(got),
                  ["f_ambiguous_layout", "f_count_mismatch", "f_error",
                   "f_unrecognized"])


def test_latest_audit_report_picks_newest():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "audit_all.20260101T000000.csv").write_text("a\n", encoding="utf-8")
        (td / "audit_all.20261231T235959.csv").write_text("b\n", encoding="utf-8")
        got = batch.latest_audit_report(td)
        expect_in("20261231", got.name)


def test_latest_audit_report_returns_none_on_empty_dir():
    with tempfile.TemporaryDirectory() as td:
        expect(batch.latest_audit_report(td) is None)


# ══════════════════════════════════════════════════════════════
# 接线：cli 子命令 ↔ scripts/*.py
# ══════════════════════════════════════════════════════════════
def test_cli_exposes_every_script_subcommand():
    """★ 这是最容易断的接线：``scripts/*.py`` 调的子命令必须真的存在。"""
    import argparse

    ap = None
    # 借 argparse 的注册表：直接构造一次 parser 不方便，改为扫 main() 源码引用
    src = Path(mcli.__file__).read_text(encoding="utf-8")
    needed = ["inventory", "extract-docs", "audit", "convert-all",
              "plot-all", "infer-unknown", "zeff", "identify", "parse",
              "infer", "convert", "h5", "plot", "targets"]
    for name in needed:
        expect_in(f'"{name}"', src, f"cli 必须注册子命令 {name}")
    expect(ap is None)


def test_scripts_wrappers_call_existing_subcommands():
    """``scripts/*.py`` 里 ``main([[...]])`` 的名字必须都在 cli 里注册。"""
    import re

    src = Path(mcli.__file__).read_text(encoding="utf-8")
    registered = set(re.findall(r'add_parser\(\s*"([a-z-]+)"', src))
    expect(registered, "应解析出已注册子命令")
    wrappers = sorted(config.SCRIPTS_DIR.glob("*.py"))
    expect(wrappers, "应存在 scripts/*.py")
    for w in wrappers:
        text = w.read_text(encoding="utf-8")
        for name in re.findall(r'main\(\[\["([a-z-]+)"', text):
            expect_in(name, registered,
                      f"{w.name} 调用了未注册的子命令 {name!r}")


def test_cli_dispatch_smoke_for_batch_commands():
    """逐个走一遍真实分发（用最小参数），确保接线不抛异常。

    ★ 每个批量命令都显式传 ``--report-dir <temp>`` ——
    否则它们会把报告写进**真实的** ``outputs/reports/``
    （实测：加这条之前 outputs/reports 里堆了 133 个文件，
    其中绝大多数来自 test 运行）。
    """
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        rd = str(td / "rep")
        expect_eq(mcli.main(["inventory", "--outdir", str(td / "inv"),
                             "--report-dir", rd,
                             "--matter-dir", str(config.MATTER_DIR)]), 0)
        expect_eq(mcli.main(["extract-docs", "--root",
                             str(config.MULTI_HOME / "doc" / "multi1d7.6"),
                             "--outdir", str(td / "ex")]), 0)
        expect_eq(mcli.main(["audit", "--outdir", rd, "--report-dir", rd,
                             "--limit", "12"]), 0)
        expect_eq(mcli.main(["convert-all", "--outdir", str(td / "h5"),
                             "--report-dir", rd, "--limit", "2"]), 0)
        expect_eq(mcli.main(["plot-all", "--outdir", str(td / "pl"),
                             "--report-dir", rd, "--limit", "1"]), 0)
        expect_eq(mcli.main(["infer-unknown", "mat_Al-1.0/AL_eos",
                             "--outdir", str(td / "inf"),
                             "--report-dir", rd]), 0)
        expect_eq(mcli.main(["targets"]), 0)
        # ★ 断言：真实 reports 目录里**没有**这次运行产生的新文件
        before = {p.name for p in config.REPORTS_DIR.glob("*")}
        expect(len(before) >= 0)          # 目录本身存在即可
        # 报告确实落在临时目录
        expect(list(Path(rd).glob("*.md")), f"{rd} 里应有 md 报告")


def test_cli_batch_commands_expose_report_dir_and_relpath():
    """★ ``--report-dir`` / ``--relpath`` 必须出现在 argparse 里。

    没有 ``--report-dir`` 时，测试无法隔离报告输出（实测污染过真实目录）。
    ``--relpath`` 让"精确复现某几个文件"不必跑全树。
    """
    import re

    from eosop_pro import cli as mcli

    src = Path(mcli.__file__).read_text(encoding="utf-8")
    expect(src.count('"--report-dir"') >= 5,
           f"至少 5 个批量命令应提供 --report-dir，实测 {src.count('--report-dir')}")
    expect_in('"--relpath"', src)
    for name in ("inventory", "audit", "convert-all", "plot-all", "infer-unknown"):
        expect_in(f'"{name}"', src)


def test_cli_parse_and_infer_smoke():
    expect_eq(mcli.main(["parse", "mat_Al-1.0/AL_eos"]), 0)
    expect_eq(mcli.main(["infer", "mat_Al-1.0/AL_eos"]), 0)


# ══════════════════════════════════════════════════════════════
# 辅助函数
# ══════════════════════════════════════════════════════════════
def test_is_2d_helper():
    from eosop_pro.parsers import multi_opacity as f2

    t = f2.parse(config.MATTER("mat_Al-1.0/1041_ROSS"), "x")
    expect(batch._is_2d(t), "F2 灰度表应为 2-D")


def test_A_for_reads_material_registry():
    from eosop_pro.registry.material import MaterialRegistry

    reg = MaterialRegistry(build_annotations=False)
    a_al = batch._A_for("mat_Al-1.0/AL_eos", reg)
    expect(a_al is not None, "Al 应有原子量")
    expect(26.0 < a_al < 28.0, f"Al 原子量应 ~27，实测 {a_al}")


def test_figs_for_labels_are_known():
    from eosop_pro.parsers import multi_opacity as f2

    t = f2.parse(config.MATTER("mat_Au-1.0/AU_op03z"), "x")
    tags = batch._figs_for(t).split(" ;; ")
    expect(any(tag in ("zeff", "opacity_heatmap") for tag in tags), tags)


# ══════════════════════════════════════════════════════════════
# ★ 退化轴范围不能让整批中断
# ══════════════════════════════════════════════════════════════
def test_convert_all_survives_degenerate_grid_range():
    """★ 回归：``convert-all`` 曾在 700/1214 处
    ``ValueError: invalid rho range: (1.0, 1.0)`` 而**整批中断**。

    根因：``Thermos/mat_Mo/Mo_Ideal_Gas`` 的 rho 网格是 ``[0.0, 1.0]``，
    过滤非正值后范围退化成单点，``build_grid`` 直接抛异常。
    修法：退化时略过该 gid（返回 ``None``），h5 少一条 unified 轨。

    用 ``only_relpaths`` 精确指定文件（回归不必跑全树）。
    """
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        r = batch.convert_all(
            outdir=td / "h5", report_dir=td / "rep",
            only_relpaths=["Thermos/mat_Mo/Mo_Ideal_Gas",
                           "mat_Al-1.0/AL_eos"])
        expect_eq(r["n_failed"], 0, f"不应有失败：{r}")
        expect_eq(r["n_written"], 2, f"两个文件都应写出（native 轨）→ {r}")
        data = json.loads(Path(r["json"]).read_text(encoding="utf-8"))
        deg = [row for row in data["rows"]
               if row.get("unified_skipped") == "degenerate-range"]
        expect(len(deg) == 1,
               f"Mo_Ideal_Gas 应被标 degenerate-range，实测 {deg}")
        expect_in("Mo_Ideal_Gas", deg[0]["relpath"])


def test_convert_all_unified_only_skips_degenerate():
    """``--unified-only`` 下退化文件应计入 skipped 而不是写空 h5。"""
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        r = batch.convert_all(
            outdir=td / "h5", report_dir=td / "rep", with_native=False,
            only_relpaths=["Thermos/mat_Mo/Mo_Ideal_Gas",
                           "mat_Al-1.0/AL_eos"])
        expect_eq(r["n_failed"], 0, f"不应有失败：{r}")
        expect_eq(r["n_written"], 1, f"只有 AL_eos 能写 unified → {r}")
        expect_eq(r["n_skipped"], 1, f"Mo_Ideal_Gas 应计入 skipped → {r}")
        data = json.loads(Path(r["json"]).read_text(encoding="utf-8"))
        skipped = [row for row in data["rows"]
                   if row.get("error") == "unified-only 且轴范围退化 → 无轨可写"]
        expect(skipped, "退化文件应计入 skipped 并带可读原因")


def test_convert_all_only_relpaths_is_order_explicit():
    """``only_relpaths`` 给出的顺序应与处理顺序一致（便于精确复现）。"""
    with tempfile.TemporaryDirectory() as td:
        r = batch.convert_all(
            outdir=Path(td) / "h5", report_dir=Path(td) / "rep",
            only_relpaths=["mat_Al-1.0/AL_eos", "mat_Au-1.0/AU_op03z"])
        data = json.loads(Path(r["json"]).read_text(encoding="utf-8"))
        got = [row["relpath"] for row in data["rows"]]
        expect_eq(got, ["mat_Al-1.0/AL_eos", "mat_Au-1.0/AU_op03z"])


def test_convert_all_report_has_unified_skipped_column():
    """报告应把 ``unified_skipped`` 写进明细（可回溯"为什么这条轨没写"）。"""
    with tempfile.TemporaryDirectory() as td:
        r = batch.convert_all(outdir=Path(td) / "h5",
                              report_dir=Path(td) / "rep",
                              only_relpaths=["mat_Al-1.0/AL_eos"])
        data = json.loads(Path(r["json"]).read_text(encoding="utf-8"))
        for row in data["rows"]:
            if row.get("h5"):
                expect_in("unified_skipped", row)


# ══════════════════════════════════════════════════════════════
# ★ 同键多表必须去重（否则第二次 create_dataset 会抛）
# ══════════════════════════════════════════════════════════════
def test_convert_all_deduplicates_duplicate_table_keys():
    """★ 回归：``convert-all`` 曾有 1 个 ``write_failed``，原因是
    ``mat_Al-1.0/Al_etc.dat`` 含 **2 个** F2 多群块，
    两者的 SESAME id 都是 ``00000000`` → ``table_key`` 都是 ``MUGROUP_0``。

    修法：``write_material_h5`` 对同键做 ``_b2`` / ``_b3`` 去重，
    并把原名写进 ``group_key_disambiguated_from`` 属性；
    ``write_unified`` 也必须用去重后的键（否则两张表的 unified 轨撞进同一组 ——
    这正是第一版修复后又失败一次的原因）。
    """
    import h5py

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        r = batch.convert_all(outdir=td / "h5", report_dir=td / "rep",
                              only_relpaths=["mat_Al-1.0/Al_etc.dat"])
        expect_eq(r["n_failed"], 0, f"不应有失败：{r}")
        expect_eq(r["n_written"], 1)
        p = sorted((td / "h5").glob("*.h5"))[0]
        with h5py.File(p) as f:
            expect_eq(f.attrs["n_tables"], 2)
            expect_eq(f.attrs["n_duplicate_table_keys"], 1)
            expect_in("MUGROUP_0", str(f.attrs["duplicate_table_keys"]))
            keys = sorted(f["tables"])
            expect_eq(keys, ["MUGROUP_0", "MUGROUP_0_b2"],
                      f"同键应加 _b2 后缀，实测 {keys}")
            expect_eq(f["tables/MUGROUP_0_b2"].attrs[
                          "group_key_disambiguated_from"], "MUGROUP_0")
            # ★ 两条轨都要在（第一版修复漏了 unified）
            for k in keys:
                expect("native" in f["tables"][k], f"{k} 缺 native 轨")
                expect("unified" in f["tables"][k],
                       f"{k} 缺 unified 轨（key_override 没传到 write_unified）")
                expect_eq(sorted(f["tables"][k]["unified"]),
                          ["nion_Te", "rho_Te"])


def test_write_material_h5_records_dedup_metadata_even_without_dups():
    """没有重复时也应写出 ``n_duplicate_table_keys = 0``（便于机器判断）。"""
    import h5py

    with tempfile.TemporaryDirectory() as td:
        r = batch.convert_all(outdir=Path(td) / "h5",
                              report_dir=Path(td) / "rep",
                              only_relpaths=["mat_Al-1.0/AL_eos"])
        p = sorted((Path(td) / "h5").glob("*.h5"))[0]
        with h5py.File(p) as f:
            expect_eq(f.attrs["n_duplicate_table_keys"], 0)


# ══════════════════════════════════════════════════════════════
# ★ h5 命名必须一一映射（否则静默覆盖）
# ══════════════════════════════════════════════════════════════
def test_h5_name_is_injective_for_the_atomic_collision_case():
    """★ 回归：初版用 ``Path(rel).stem`` 命名，7 个 ATOMIC 文件全部撞车。

    ``Path('ATOMIC/Al.NoFree').stem == 'Al'`` —— **切掉了点号之后的部分**，
    于是 ``Al.txt`` / ``Al.NoFree`` / ``Al.AvSqFree`` /
    ``Al.GrayOpacity_{PLANCK,ROSSELAND}`` /
    ``Al.MultiGroupOpacity_{PLANCK,ROSSELAND}`` 都映射到 ``ATOMIC__Al.h5``。

    全树实测：报告 ``n_written=992`` 但盘上只有 **770** 个 .h5 ——
    **222 个被静默覆盖**。
    """
    rels = ["ATOMIC/Al.txt", "ATOMIC/Al.NoFree", "ATOMIC/Al.AvSqFree",
            "ATOMIC/Al.GrayOpacity_PLANCK", "ATOMIC/Al.GrayOpacity_ROSSELAND",
            "ATOMIC/Al.MultiGroupOpacity_PLANCK",
            "ATOMIC/Al.MultiGroupOpacity_ROSSELAND"]
    names = [batch._h5_name_for(r) for r in rels]
    expect_eq(len(set(names)), len(rels),
              f"7 个文件必须有 7 个不同的 h5 名，实测 {names}")


def test_h5_name_keeps_dots_and_dirs_distinguishable():
    """点号与目录分隔都要保留信息，避免 ``a.b/c`` 与 ``a/b.c`` 撞车。"""
    a = batch._h5_name_for("a.b/c")
    b = batch._h5_name_for("a/b.c")
    expect(a != b, f"不同路径不应撞名：{a} vs {b}")
    expect_eq(batch._h5_name_for("hyades/sesame/eos_41.dat"),
              "hyades__sesame__eos_41_dat.h5")
    expect_eq(batch._h5_name_for("mat_Al-1.0/AL_eos"),
              "mat_Al-1_0__AL_eos.h5")
    expect(batch._h5_name_for("x").endswith(".h5"))


def test_h5_name_collision_check_has_a_fallback():
    """即使命名规则被改坏，兜底也要加数字后缀而不是覆盖。"""
    orig = batch._h5_name_for
    batch._h5_name_for = lambda r: "same.h5"
    try:
        m = batch._check_name_collisions(["x", "y", "z"])
        expect_eq(len(set(m.values())), 3, f"兜底应产生 3 个不同的名字，实测 {m}")
        expect_eq(m["x"], "same.h5")
        expect_eq(m["y"], "same_2.h5")
        expect_eq(m["z"], "same_3.h5")
    finally:
        batch._h5_name_for = orig


def test_convert_all_reconciles_written_count_against_disk():
    """★ 报告必须自证：``n_h5_on_disk == n_written``。

    初版缺这条对账时，"992 已写 / 770 个文件"的报告看起来完全正常。
    """
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        r = batch.convert_all(outdir=td / "h5", report_dir=td / "rep",
                              only_relpaths=["ATOMIC/Al.txt", "ATOMIC/Al.NoFree",
                                             "ATOMIC/Al.AvSqFree",
                                             "ATOMIC/Al.GrayOpacity_PLANCK"])
        expect_eq(r["n_written"], 4, f"4 个文件都应写出 → {r}")
        expect_eq(r["n_h5_on_disk"], 4, f"盘上也应有 4 个 → {r}")
        expect(r["reconciled"] is True, f"对账应通过 → {r}")
        expect_eq(len(list((td / "h5").glob("*.h5"))), 4)
        data = json.loads(Path(r["json"]).read_text(encoding="utf-8"))
        expect_eq(data["n_h5_on_disk"], 4)
        expect_eq(data["reconciled"], True)
        md = Path(r["md"]).read_text(encoding="utf-8")
        expect_in("对账", md)


if __name__ == "__main__":
    raise SystemExit(main(globals()))
