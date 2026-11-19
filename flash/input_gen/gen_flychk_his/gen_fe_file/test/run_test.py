"""run_test.py — gen_fe_file 端到端用例 (S1~S6)。

用法::

    python flash/input_gen/gen_flychk_his/gen_fe_file/test/run_test.py
    python flash/input_gen/gen_flychk_his/gen_fe_file/test/run_test.py --pytest  # 联跑 pytest

全部通过返回 0, 产物写 out/REPORT.md。
"""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

import pytest

_TEST_DIR = Path(__file__).resolve().parent
_ROOT = _TEST_DIR.parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from flash.input_gen.gen_flychk_his.builder import HistoryTable  # noqa: E402
from flash.input_gen.gen_flychk_his.config import ConfigError  # noqa: E402
from flash.input_gen.gen_flychk_his.gen_fe_file import (  # noqa: E402
    FeExplicitSeries, FeFileError, FeModel,
    build_fe_file, fe_filename_for, write_history_zip_with_fe,
)
from flash.input_gen.gen_flychk_his.zip_writer import (  # noqa: E402
    HistoryZipWriter, ZipWriterError,
)

OUT_DIR = _TEST_DIR / "out"


def _make_table() -> HistoryTable:
    return HistoryTable(
        columns=["time", "te", "rho"],
        rows=[[1e-12, 500.0, 1e-3], [2e-12, 800.0, 8e-4]],
        meta={"element": "Ti", "z": 22},
    )


def _reset_out() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR, ignore_errors=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)


# ── 场景 ────────────────────────────────────────────────────
def s1_maxwell_small_grid(results: dict) -> None:
    """S1: maxwell 小网格完整 zip, 解压核对成员/runfile/fe 逐字符。"""
    fe = build_fe_file(
        FeModel(te_beam=1000.0, beam_density=1e11, times=[0.0, 1e-9]),
        energies=[500.0, 1000.0, 2000.0, 5000.0],
        comment="S1 maxwell beam Te=1keV",
    )
    table = _make_table()
    fe_name = fe_filename_for(table.element, table.z)
    zp = OUT_DIR / "s1" / "history_Ti_Z22_fe.zip"
    write_history_zip_with_fe(table, fe, str(zp))
    with zipfile.ZipFile(zp) as zf:
        members = zf.namelist()
        runfile = zf.read("runfile.txt").decode("utf-8")
        fe_text = zf.read(fe_name).decode("utf-8")
    assert members == ["runfile.txt", "history_Ti_Z22_input.txt", fe_name]
    assert f"fe file {fe_name}" in runfile.splitlines()
    assert fe_text == fe.to_text()
    res = HistoryZipWriter().verify_zip(table, str(zp), fe_text=fe.to_text(),
                                        fe_filename=fe_name)
    assert res["ok"], res
    results["S1"] = f"OK  成员={members} fe 行已核对 逐字符一致 verify ok"


def s2_explicit_series(results: dict) -> None:
    """S2: 显式数组模式 3 时间步, 回读与输入逐字符一致。"""
    energies = [1000.0, 2000.0, 4000.0]
    records = [
        (0.0, 1e11, [1e-8, 5e-4, 1e-8]),
        (1e-9, 5e10, [5e-9, 2.5e-4, 5e-9]),
        (2e-9, 1e10, [1e-9, 5e-5, 1e-9]),
    ]
    fe = build_fe_file(FeExplicitSeries(energies=energies, records=records))
    table = _make_table()
    fe_name = fe_filename_for(table.element, table.z)
    zp = OUT_DIR / "s2" / "history_Ti_Z22_fe.zip"
    HistoryZipWriter().write(table, str(zp), fe_text=fe.to_text(),
                             fe_filename=fe_name)
    with zipfile.ZipFile(zp) as zf:
        fe_text = zf.read(fe_name).decode("utf-8")
    assert fe_text == fe.to_text()
    assert fe.n_steps == 3 and fe.n_energies == 3
    results["S2"] = "OK  显式 3 时间步 zip 回读逐字符一致"


def s3_500_points_pressure(results: dict) -> None:
    """S3: 500 点压力测试 — 行宽 <=120 + verify 通过。"""
    energies = [10.0 + 20.0 * i for i in range(500)]
    fe = build_fe_file(
        FeModel(te_beam=1000.0, beam_density=1e11, times=[0.0]),
        energies=energies,
    )
    for ln in fe.to_text().splitlines():
        assert len(ln) <= 120
    table = _make_table()
    fe_name = fe_filename_for(table.element, table.z)
    zp = OUT_DIR / "s3" / "history_Ti_Z22_fe_500pts.zip"
    HistoryZipWriter().write(table, str(zp), fe_text=fe.to_text(),
                             fe_filename=fe_name)
    res = HistoryZipWriter().verify_zip(table, str(zp), fe_text=fe.to_text(),
                                        fe_filename=fe_name)
    assert res["ok"], res
    results["S3"] = "OK  500 点全部行宽<=120 verify ok"


def s4_time_series_density(results: dict) -> None:
    """S4: 密度时间序列 — 每步 fe 缩放比 == 密度比。"""
    fe = build_fe_file(
        FeModel(te_beam=1000.0, beam_density=1e11,
                times=[0.0, 1e-9, 2e-9],
                densities=[1e11, 5e10, 1e10]),
        energies=[500.0, 1000.0, 2000.0, 5000.0],
    )
    f0 = fe.records[0][2]
    for k, dens in enumerate([1e11, 5e10, 1e10]):
        for i in range(len(f0)):
            ratio = fe.records[k][2][i] / f0[i] if f0[i] else 0.0
            assert abs(ratio - dens / 1e11) < 1e-9
    results["S4"] = "OK  3 时间步 fe 整体缩放比 == 密度比"


def s5_invalid_inputs_rejected(results: dict) -> None:
    """S5: 非法输入 (501 点/降序网格/负 fe/重复时间) 拒绝且不写 zip。"""
    table = _make_table()
    out_s5 = OUT_DIR / "s5"
    cases = {
        "501点": FeExplicitSeries(
            energies=[10.0 + i for i in range(501)],
            records=[(0.0, 1e11, [1e-8] * 501)]),
        "降序网格": FeExplicitSeries(
            energies=[1000.0, 500.0, 100.0],
            records=[(0.0, 1e11, [1e-8, 1e-6, 1e-8])]),
        "负fe": FeExplicitSeries(
            energies=[100.0, 500.0, 1000.0],
            records=[(0.0, 1e11, [1e-8, -1e-6, 1e-8])]),
        "重复时间": FeExplicitSeries(
            energies=[100.0, 500.0, 1000.0],
            records=[(1e-9, 1e11, [1e-8, 1e-6, 1e-8]),
                     (1e-9, 1e11, [1e-8, 1e-6, 1e-8])]),
    }
    for name, spec in cases.items():
        with pytest.raises((ConfigError, FeFileError)):
            build_fe_file(spec)
    # fe_text/fe_filename 不成对
    with pytest.raises(ZipWriterError):
        HistoryZipWriter().write(table, str(out_s5 / "bad_pair.zip"),
                                 fe_text="x", fe_filename=None)
    # 确认没有写出任何 zip
    zips = list(out_s5.glob("*.zip")) if out_s5.exists() else []
    assert not zips, f"非法输入不应写出 zip: {zips}"
    results["S5"] = f"OK  {len(cases)} 种非法输入拒绝 + 不成对参数拒绝 + 零 zip 产物"


def s6_roundtrip_and_tamper(results: dict) -> None:
    """S6: 回读自检全 checks 通过; 篡改 fe 成员后 verify 失败。"""
    fe = build_fe_file(
        FeModel(te_beam=1000.0, beam_density=1e11, times=[0.0, 1e-9]),
        energies=[500.0, 1000.0, 2000.0, 5000.0],
    )
    table = _make_table()
    fe_name = fe_filename_for(table.element, table.z)
    zp = OUT_DIR / "s6" / "history_Ti_Z22_fe.zip"
    HistoryZipWriter().write(table, str(zp), fe_text=fe.to_text(),
                             fe_filename=fe_name)
    res = HistoryZipWriter().verify_zip(table, str(zp), fe_text=fe.to_text(),
                                        fe_filename=fe_name)
    assert res["ok"] and all(
        v for k, v in res["checks"].items() if isinstance(v, bool))
    # 篡改
    import zipfile as zf_mod
    tampered = fe.to_text().replace("5.000000e+03", "4.000000e+03")
    assert tampered != fe.to_text()
    with zf_mod.ZipFile(zp) as zin, \
            zf_mod.ZipFile(str(zp) + ".tmp", "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == fe_name:
                data = tampered.encode("utf-8")
            zout.writestr(item, data)
    shutil.move(str(zp) + ".tmp", str(zp))
    res2 = HistoryZipWriter().verify_zip(table, str(zp), fe_text=fe.to_text(),
                                         fe_filename=fe_name)
    assert not res2["ok"], "篡改后的 zip 不应通过校验"
    results["S6"] = "OK  回读全 checks 通过 + 篡改检测生效"


SCENARIOS = [s1_maxwell_small_grid, s2_explicit_series,
             s3_500_points_pressure, s4_time_series_density,
             s5_invalid_inputs_rejected, s6_roundtrip_and_tamper]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="gen_fe_file 端到端测试")
    parser.add_argument("--pytest", action="store_true",
                        help="联跑 pytest 全量测试")
    args = parser.parse_args(argv)

    _reset_out()
    results: dict = {}
    failed = []
    for fn in SCENARIOS:
        try:
            fn(results)
            print(f"[PASS] {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed.append(fn.__name__)
            results[fn.__name__] = f"FAIL: {exc}"
            print(f"[FAIL] {fn.__name__}: {exc}")

    report_lines = [
        "# gen_fe_file 端到端测试报告",
        "",
        f"用例总数: {len(SCENARIOS)}, 通过: {len(SCENARIOS) - len(failed)}, "
        f"失败: {len(failed)}",
        "",
        "| 场景 | 结果 |",
        "|---|---|",
    ]
    for fn in SCENARIOS:
        report_lines.append(f"| {fn.__name__} | {results.get(fn.__name__, '-')} |")
    report = "\n".join(report_lines) + "\n"
    (OUT_DIR / "REPORT.md").write_text(report, encoding="utf-8", newline="\n")
    print(f"\n报告: {OUT_DIR / 'REPORT.md'}")

    if args.pytest:
        import subprocess
        rc = subprocess.call([
            sys.executable, "-m", "pytest",
            str(_TEST_DIR), "-q",
        ])
        if rc != 0:
            failed.append("pytest")

    if failed:
        print(f"失败用例: {failed}")
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
