#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_test.py — gen_flychk_his 一键端到端测试 (数据 → FLYCHK 输入 zip)
====================================================================

流程 (全部自动, 无需人工干预)::

    1. 生成/校验测试数据 (test/data/, 合成 FLASH HDF5 + npz/csv/json)
    2. 逐数据源 × 逐区域方案生成 FLYCHK history 输入 zip
    3. 每个 zip 回读自检 (与表内容逐字符核对, 自包含)
    4. 写出 out/REPORT.md + out/overview.png (预诊断图)
    5. 控制台打印汇总表; 全部通过返回 0

注: 与外部 FLYCHK 小包的格式对拍是**可选**动作, 见 cross_check_external.py。

用法::

    python flash/input_gen/gen_flychk_his/test/run_test.py
    python flash/input_gen/gen_flychk_his/test/run_test.py --force-data
    python flash/input_gen/gen_flychk_his/test/run_test.py --pytest   # 另跑 pytest 全量
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import traceback
import zipfile
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from flash.input_gen.gen_flychk_his import (FORMAT_CONTRACT_ID,  # noqa: E402
                                            WRITER_ID, FlychkHistoryGenerator,
                                            plot_region_overview)
from flash.input_gen.gen_flychk_his.test import make_test_data as mtd  # noqa: E402

OUT_DIR = _HERE / "out"
REPORT = OUT_DIR / "REPORT.md"

ELEMENT, Z = "Ti", 22

# (名称, 数据源键, 额外加载参数)
SOURCES = [
    ("flash_hdf5", "flash_hdf5_dir", {}),
    ("npz", "npz", {}),
    ("csv", "csv", {}),
    ("json_fields", "json", {}),
    ("json_snapshots", "json_snapshots", {}),
    ("json_units_declared", "json_units", {}),
]

# (名称, 区域描述)
REGIONS = [
    ("whole_target", "whole"),
    ("tracer_layers", ["label:trac=1", "label:trac=2", "label:trac=3"]),
    ("spatial_layers", ["layer:1/4", "layer:2/4", "layer:3/4", "layer:4/4"]),
    ("front_zone", "x:-46..-40um"),
    ("corona_top10", "top:10%@tele"),
    ("mass_half", "mass:0..0.5"),
]


def _line(title: str = "") -> str:
    return f"{'=' * 78}\n{title}" if title else "=" * 78


def run_case(name, source, region, out_dir, data_kwargs=None):
    """单个 (数据源, 区域) 组合: 生成 + 读取 zip 内容 + 交叉验证。"""
    gen = FlychkHistoryGenerator(
        element=ELEMENT, agg="mass", n_time_max=8, dens_cut=1e-6,
        write_preview=True, output_dir=str(out_dir))
    t0 = time.perf_counter()
    report = gen.generate(source=source, region=region, output_dir=str(out_dir),
                          self_check=True, verbose=False,
                          **(data_kwargs or {}))
    dt = time.perf_counter() - t0

    rows = []
    for r in report.results:
        if r.zip_path and Path(r.zip_path).is_file():
            with zipfile.ZipFile(r.zip_path) as zf:
                data_name = [n for n in zf.namelist() if n != "runfile.txt"][0]
                lines = zf.read(data_name).decode().splitlines()
            header = lines[0].split()
            arr = np.array([[float(v) for v in ln.split()] for ln in lines[1:]])
            te = arr[:, header.index("te")]
            rho = arr[:, header.index("rho")] if "rho" in header else arr[:, header.index("ne")]
            rows.append({
                "region": r.region, "steps": len(lines) - 1,
                "cols": len(header), "te_min": float(te.min()),
                "te_max": float(te.max()), "rho_min": float(rho.min()),
                "rho_max": float(rho.max()),
                "zip": Path(r.zip_path).name, "ok": r.ok,
                "integrity": bool((r.integrity or {}).get("ok")),
                "preview": Path(r.preview_path).name if r.preview_path else "-",
            })
    return {"case": name, "ok": report.ok, "elapsed_s": round(dt, 2),
            "zip_paths": [str(p) for p in report.zip_paths],
            "manifest": str(report.manifest_path) if report.manifest_path else None,
            "rows": rows, "integrity_ok": report.integrity_ok,
            "errors": report.errors}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="gen_flychk_his 端到端测试")
    p.add_argument("--force-data", action="store_true", help="强制重建测试数据")
    p.add_argument("--skip-preview", action="store_true", help="不画概览图")
    p.add_argument("--pytest", action="store_true", help="额外运行 pytest 全量套件")
    args = p.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(_line("gen_flychk_his 端到端测试"))
    print(f"[时间] {time.strftime('%Y-%m-%d %H:%M:%S')}")
    data = mtd.ensure_test_data(force=args.force_data)

    print(f"[写出器] {WRITER_ID} (自包含, 仅标准库)")
    print(f"[格式契约] {FORMAT_CONTRACT_ID} (FLYCHK history 模式)")
    print("[自检] 每个 zip 写出后回读, 与表内容逐字符核对")

    results, failures = [], []
    for sname, skey, extra in SOURCES:
        src = str(data[skey])
        for rname, region in REGIONS:
            case = f"{sname}__{rname}"
            out = OUT_DIR / case
            try:
                res = run_case(case, src, region, out, data_kwargs=extra)
            except Exception as exc:                       # noqa: BLE001
                failures.append((case, f"{type(exc).__name__}: {exc}"))
                print(f"  [FAIL] {case}: {type(exc).__name__}: {exc}")
                traceback.print_exc()
                continue
            results.append(res)
            flag = "OK " if res["ok"] else "ERR"
            integ = "OK" if res["integrity_ok"] else "-"
            print(f"  [{flag}] {case:<34s} {len(res['zip_paths'])} zip, "
                  f"{sum(r['steps'] for r in res['rows'])} 步, "
                  f"{res['elapsed_s']:>5.2f}s, 自检={integ}")
            if not res["ok"]:
                failures.append((case, "; ".join(res["errors"])))

    # ── 概览图 ──
    overview = None
    if not args.skip_preview:
        try:
            from flash.input_gen.gen_flychk_his import build_history_table
            tables = {}
            for name, spec in (("whole", "whole"),
                               ("tracer (trac=2)", "label:trac=2"),
                               ("corona top10%", "top:10%@tele")):
                tables[name] = build_history_table(
                    source=str(data["flash_hdf5_dir"]), element=ELEMENT,
                    region=spec, n_time_max=8, dens_cut=1e-6)
            overview = plot_region_overview(
                tables, OUT_DIR / "overview.png", element=ELEMENT, z=Z)
            print(f"[绘图] {overview}")
        except Exception as exc:                           # noqa: BLE001
            print(f"[绘图] 失败: {type(exc).__name__}: {exc}")

    # ── 报告 ──
    _write_report(results, failures, data, overview)
    print(f"[报告] {REPORT}")

    # ── 可选 pytest ──
    rc_pytest = None
    if args.pytest:
        print(_line("pytest 全量套件"))
        proc = subprocess.run(
            [sys.executable, "-m", "pytest",
             "flash/input_gen/gen_flychk_his/test", "-q"],
            cwd=str(_ROOT))
        rc_pytest = proc.returncode
        print(f"[pytest] exit={rc_pytest}")

    print(_line())
    n_ok = sum(1 for r in results if r["ok"])
    print(f"[汇总] 用例 {len(results)} 通过 {n_ok} 失败 {len(failures)}"
          + (f", pytest exit={rc_pytest}" if rc_pytest is not None else ""))
    for case, msg in failures:
        print(f"  ! {case}: {msg}")
    return 0 if (not failures and (rc_pytest in (None, 0))) else 1


def _write_report(results, failures, data, overview) -> None:
    lines = [
        "# gen_flychk_his 端到端测试报告",
        "",
        f"- 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 元素: {ELEMENT} (Z={Z})",
        f"- zip 写出器: **{WRITER_ID}** (自包含, 仅标准库)",
        f"- 格式契约: `{FORMAT_CONTRACT_ID}` (FLYCHK history 模式)",
        "- 完整性: 每个 zip 写出后回读自检 (与表内容逐字符核对)",
        f"- 合成数据源: `{mtd.DATA_DIR}`",
        f"- 用例: {len(results)} 通过 / {len(results) - len(failures)}"
        + f", 失败 {len(failures)}",
        "",
        "## 1. 测试数据",
        "",
        "| 名称 | 路径 |",
        "|------|------|",
    ]
    for key in ("flash_hdf5_dir", "npz", "csv", "json", "json_snapshots", "json_units"):
        lines.append(f"| {key} | `{data[key]}` |")
    lines.append(f"| flash_files | {len(data['flash_files'])} 个 HDF5 chk 文件 |")

    lines += [
        "",
        "物理剖面 (解析模型, FLASH 原生 cgs/K): CH 平板 `x ∈ [-50, 50] µm`,",
        "烧蚀面 `x_a(t) = -50µm + 2e5·t`, 峰值温度 `Te_pk(t) = 1200 eV·(t/tmax)^0.25`,",
        "1/2/3 µm 处 Ti 示踪层 (`trac` = 1/2/3)。",
        "",
        "## 2. 用例结果",
        "",
        "| 数据源 | 区域方案 | zip 数 | 步数 | 耗时(s) | zip 自检 | 状态 |",
        "|--------|----------|-------:|-----:|--------:|----------|------|",
    ]
    for r in results:
        src, reg = r["case"].split("__", 1)
        lines.append(
            f"| {src} | {reg} | {len(r['zip_paths'])} | "
            f"{sum(x['steps'] for x in r['rows'])} | {r['elapsed_s']} | "
            f"{'OK' if r['integrity_ok'] else '-'} | "
            f"{'OK' if r['ok'] else 'ERR'} |")

    lines += ["", "## 3. 生成内容明细 (物理量范围)", "",
              "| 用例 | 区域 | 步数 | 列数 | Te (eV) | rho (g/cm³) | zip |",
              "|------|------|-----:|-----:|---------|-------------|-----|"]
    for r in results:
        for row in r["rows"]:
            lines.append(
                f"| {r['case']} | {row['region']} | {row['steps']} | {row['cols']} | "
                f"{row['te_min']:.1f} ~ {row['te_max']:.1f} | "
                f"{row['rho_min']:.3e} ~ {row['rho_max']:.3e} | `{row['zip']}` |")

    if overview:
        lines += ["", "## 4. 概览图", "",
                  f"![overview]({Path(overview).name})", ""]

    if failures:
        lines += ["", "## 5. 失败用例", ""]
        for case, msg in failures:
            lines.append(f"- `{case}`: {msg}")

    lines += [
        "",
        "## 6. 复核入口",
        "",
        "- 逐用例 `manifest.json` (源文件 / 区域定义 / 配置 / 校验 / 后端) 位于各用例目录;",
        "- 表文本 `<zip 基名>.txt` 与 zip 内数据文件内容一致 (见 `test_zip_writer.py`);",
        "- 独立性: `python test/verify_decoupled.py` 在封锁外部包导入的敌对环境"
        "下重跑全量测试 (解耦机械化证明);",
        "- 可选对拍: `python test/cross_check_external.py --flychk-root <路径>`"
        " 可与外部 FLYCHK 小包逐字节比对 (非发布包依赖);",
        "- 预诊断图 `<zip 基名>_preview.png` 为提交 FLYCHK 前的先验检查依据。",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8", newline="\n")


if __name__ == "__main__":       # pragma: no cover
    sys.exit(main())
