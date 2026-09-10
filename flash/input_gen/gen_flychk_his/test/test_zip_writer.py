"""test_zip_writer.py — 自包含 zip 写出器、格式契约与 writer/清单。

**无任何外部 FLYCHK 包依赖**：本文件只使用 `zip_writer` 的纯函数与
`writer.FlychkHistoryWriter`。

格式对拍（与外部 FLYCHK 小包逐字节比较）为**可选**动作，见
`cross_check_external.py`，默认不参与测试。
"""

import json
import zipfile
from pathlib import Path

import pytest

from flash.input_gen.gen_flychk_his import regions as rg
from flash.input_gen.gen_flychk_his.builder import HistoryTable
from flash.input_gen.gen_flychk_his.config import FlychkHisConfig
from flash.input_gen.gen_flychk_his.extract import extract_region
from flash.input_gen.gen_flychk_his.sources import synthetic_ch_ti_slab
from flash.input_gen.gen_flychk_his.writer import FlychkHistoryWriter
from flash.input_gen.gen_flychk_his.zip_writer import (FORMAT_CONTRACT_ID,
                                                       WRITER_ID,
                                                       HistoryZipWriter,
                                                       ZipWriterError,
                                                       data_filename_for,
                                                       render_data,
                                                       render_runfile,
                                                       validate_columns,
                                                       write_history_zip)


def table(columns=("time", "size", "te", "ti", "tr", "rho"),
          n=3, element="Ti", z=22):
    rows = []
    for i in range(n):
        row = []
        for c in columns:
            if c == "time":
                row.append(1e-12 * (i + 1))
            elif c == "size":
                row.append(2.0e-4)
            elif c == "te":
                row.append(800.0 + 10.0 * i)
            elif c in ("ti", "tr"):
                row.append(600.0 + 10.0 * i)
            elif c == "rho":
                row.append(0.25)
            elif c in ("ne", "ni"):
                row.append(1.0e22)
        rows.append(row)
    return HistoryTable(columns=list(columns), rows=rows,
                        meta={"element": element, "z": z, "time_unit": "s"})


# ══════════════════════════════════════════════════════════
# 自包含性
# ══════════════════════════════════════════════════════════
class TestSelfContained:
    def test_only_stdlib_imports(self):
        """zip_writer.py 只允许导入标准库与包内模块。"""
        src = Path(__file__).resolve().parents[1] / "zip_writer.py"
        text = src.read_text(encoding="utf-8")
        assert "import flychk" not in text
        assert "FLYCHK_SIM_ROOT" not in text
        for mod in ("zipfile", "pathlib", "dataclasses", "typing"):
            assert mod in text

    def test_no_backend_module(self):
        pkg = Path(__file__).resolve().parents[1]
        assert not (pkg / "backend.py").exists()
        assert not (pkg / "test" / "test_backend_writer.py").exists()

    def test_no_external_reference_in_package_source(self):
        """发布包源码中不得出现外部 FLYCHK 包的导入/路径搜索。"""
        pkg = Path(__file__).resolve().parents[1]
        forbidden = ("flychk.input_gen", "flychk_root", "FLYCHK_SIM_ROOT",
                     "candidate_flychk_roots", "resolve_flychk_generator",
                     "compare_backends", "allow_fallback", "import flychk")
        hits = []
        for py in sorted(pkg.glob("*.py")):          # 仅发布包顶层模块
            txt = py.read_text(encoding="utf-8")
            hits += [f"{py.name}: {f}" for f in forbidden if f in txt]
        assert not hits, hits


# ══════════════════════════════════════════════════════════
# 格式契约
# ══════════════════════════════════════════════════════════
class TestFormatContract:
    def _members(self, tmp, columns, element="Ti", z=22):
        tb = table(columns, element=element, z=z)
        p = Path(tmp) / "x.zip"
        HistoryZipWriter().write(tb, str(p))
        with zipfile.ZipFile(p) as zf:
            return {n: zf.read(n).decode("utf-8") for n in zf.namelist()}

    def test_full_runfile(self, out_dir):
        m = self._members(out_dir, ["time", "size", "te", "ti", "tr", "rho"])
        assert m["runfile.txt"] == (
            "z 22\ninitial ss\nevolve ss\nhistory\nopacity file\nti file\n"
            "tr file\nhistory history_Ti_Z22_input.txt rho\nend\n"
        )
        assert m["history_Ti_Z22_input.txt"].splitlines()[0] == \
            "time size te ti tr rho"

    @pytest.mark.parametrize("columns,dens_line", [
        (["time", "te", "rho"], "history history_Ti_Z22_input.txt rho"),
        (["time", "te", "ne"], "history history_Ti_Z22_input.txt ne"),
        (["time", "te", "ni"], "history history_Ti_Z22_input.txt ni"),
    ])
    def test_density_basis_lines(self, out_dir, columns, dens_line):
        m = self._members(out_dir, columns)
        assert dens_line in m["runfile.txt"]
        assert "opacity file" not in m["runfile.txt"]

    def test_size_triggers_opacity_file(self, out_dir):
        m = self._members(out_dir, ["time", "size", "te", "rho"])
        assert "opacity file" in m["runfile.txt"]
        assert "ti file" not in m["runfile.txt"]

    def test_member_order_and_names(self, out_dir):
        tb = table()
        p = Path(out_dir) / "o.zip"
        HistoryZipWriter().write(tb, str(p))
        with zipfile.ZipFile(p) as zf:
            assert zf.namelist() == ["runfile.txt", "history_Ti_Z22_input.txt"]

    def test_data_text_matches_table_text(self, out_dir):
        tb = table()
        p = Path(out_dir) / "d.zip"
        HistoryZipWriter().write(tb, str(p))
        with zipfile.ZipFile(p) as zf:
            assert zf.read("history_Ti_Z22_input.txt").decode() == tb.to_text()

    def test_render_helpers_are_pure(self):
        cols = ["time", "te", "rho"]
        assert render_runfile("C", 6, cols, "f.txt").startswith("z 6\n")
        assert render_data(cols, [[1e-12, 10.0, 0.1]]).splitlines()[1] == \
            "1.000000e-12 1.000000e+01 1.000000e-01"
        assert data_filename_for("V", 23) == "history_V_Z23_input.txt"
        assert FORMAT_CONTRACT_ID == "flychk-history-v1"
        assert WRITER_ID == "flash.input_gen.gen_flychk_his"

    def test_validate_columns_errors(self):
        with pytest.raises(ZipWriterError):
            validate_columns(["te", "rho"], [[1.0, 1.0]])       # 缺 time
        with pytest.raises(ZipWriterError):
            validate_columns(["time", "te"], [[1.0, 1.0]])      # 缺密度列
        with pytest.raises(ZipWriterError):
            validate_columns(["time", "te", "rho", "ne"],
                             [[1.0, 1.0, 1.0, 1.0]])            # 多个密度列
        with pytest.raises(ZipWriterError):
            validate_columns(["time", "te", "rho"], [[1.0, 1.0]])  # 行长不符
        with pytest.raises(ZipWriterError):
            validate_columns([], [])

    def test_generate_history_zip_defaults(self, out_dir):
        p = HistoryZipWriter().generate_history_zip(
            element="Ti", z=22, output_path=str(Path(out_dir) / "def.zip"))
        with zipfile.ZipFile(p) as zf:
            assert zf.namelist() == ["runfile.txt", "history_Ti_Z22_input.txt"]

    def test_write_history_zip_convenience(self, out_dir):
        p = write_history_zip(table(), str(Path(out_dir) / "c.zip"))
        assert Path(p).is_file()


# ══════════════════════════════════════════════════════════
# 自检 (回读比对)
# ══════════════════════════════════════════════════════════
class TestZipIntegritySelfCheck:
    def test_verify_ok(self, out_dir):
        tb = table()
        w = HistoryZipWriter()
        p = w.write(tb, str(Path(out_dir) / "i.zip"))
        res = w.verify_zip(tb, str(p))
        assert res["ok"] is True
        assert res["members"] == w.expected_members("Ti", 22)
        assert res["checks"]["data_matches_table"] is True
        assert res["checks"]["runfile_content"] is True
        assert res["checks"]["format_contract"] == FORMAT_CONTRACT_ID

    def test_verify_detects_corruption(self, out_dir):
        tb = table()
        w = HistoryZipWriter()
        p = w.write(tb, str(Path(out_dir) / "bad.zip"))
        # 篡改 zip 内数据文件
        other = table(columns=tb.columns, n=3)
        other.rows[0][1] = 9.99e-4
        res = w.verify_zip(other, str(p))
        assert res["ok"] is False
        assert res["checks"]["data_matches_table"] is False
        assert "不一致" in res.get("detail", "")

    def test_verify_missing_file(self, out_dir):
        res = HistoryZipWriter().verify_zip(table(), str(Path(out_dir) / "no.zip"))
        assert res["ok"] is False and "不存在" in res["detail"]

    def test_report_flags_integrity(self, out_dir):
        s = synthetic_ch_ti_slab(n_time=3, nx=200)
        cfg = FlychkHisConfig(element="Ti", n_time_max=3)
        rs = [extract_region(s, rg.whole(), cfg)]
        rep = FlychkHistoryWriter(cfg).write(rs, str(Path(out_dir) / "rep"),
                                             self_check=True)
        assert rep.ok and rep.integrity_ok is True
        assert rep.results[0].integrity["checks"]["member_order"] is True

    def test_self_check_can_be_disabled(self, out_dir):
        s = synthetic_ch_ti_slab(n_time=3, nx=200)
        cfg = FlychkHisConfig(element="Ti", n_time_max=3)
        rs = [extract_region(s, rg.whole(), cfg)]
        rep = FlychkHistoryWriter(cfg).write(rs, str(Path(out_dir) / "off"),
                                             self_check=False)
        assert rep.integrity_ok is None
        assert rep.ok


# ══════════════════════════════════════════════════════════
# 写出器编排
# ══════════════════════════════════════════════════════════
class TestWriter:
    def _rseries(self, agg="mass"):
        cfg = FlychkHisConfig(element="Ti", agg=agg, n_time_max=4)
        s = synthetic_ch_ti_slab(n_time=6, nx=300)
        return [extract_region(s, rg.parse_region("x:-40..0um"), cfg),
                extract_region(s, rg.parse_region("label:matid=2"), cfg)], cfg

    def test_flat_layout(self, out_dir):
        rs, cfg = self._rseries()
        rep = FlychkHistoryWriter(cfg).write(rs, str(Path(out_dir) / "flat"),
                                             layout="flat",
                                             source_meta={"kind": "synthetic"})
        assert rep.ok
        assert len(rep.zip_paths) == 2
        for p in rep.zip_paths:
            assert Path(p).is_file()
        assert rep.manifest_path is not None and Path(rep.manifest_path).is_file()

    def test_batch_layout(self, out_dir):
        rs, cfg = self._rseries()
        rep = FlychkHistoryWriter(cfg).write(rs, str(Path(out_dir) / "batch"),
                                             layout="batch")
        assert rep.ok
        assert (Path(out_dir) / "batch" / "input" / "batch_0000").is_dir()
        assert (Path(out_dir) / "batch" / "input" / "batch_0001").is_dir()

    def test_unknown_layout_raises(self, out_dir):
        from flash.input_gen.gen_flychk_his.writer import WriterError
        rs, cfg = self._rseries()
        with pytest.raises(WriterError):
            FlychkHistoryWriter(cfg).write(rs, str(Path(out_dir) / "x"),
                                           layout="weird")

    def test_manifest_content(self, out_dir):
        rs, cfg = self._rseries()
        rep = FlychkHistoryWriter(cfg).write(rs, str(Path(out_dir) / "man"),
                                             source_meta={"kind": "synthetic"})
        doc = json.loads(Path(rep.manifest_path).read_text(encoding="utf-8"))
        assert doc["generator"] == WRITER_ID
        assert doc["writer"]["id"] == WRITER_ID
        assert doc["writer"]["format_contract"] == FORMAT_CONTRACT_ID
        assert doc["writer"]["self_contained"] is True
        assert doc["zip_integrity_ok"] is True
        assert doc["n_regions"] == 2
        r0 = doc["regions"][0]
        assert r0["n_steps"] == 4
        assert r0["columns"] == list(cfg.columns)
        assert r0["table_meta"]["element"] == "Ti"
        assert r0["validation"]["ok"] is True
        assert r0["zip_integrity"]["ok"] is True
        assert Path(r0["zip_path"]).is_file()

    def test_manifest_has_no_external_backend_key(self, out_dir):
        """旧版的 backend 段必须消失（解耦验证）。"""
        rs, cfg = self._rseries()
        rep = FlychkHistoryWriter(cfg).write(rs, str(Path(out_dir) / "nob"))
        doc = json.loads(Path(rep.manifest_path).read_text(encoding="utf-8"))
        assert "backend" not in doc
        assert "cross_check" not in doc

    def test_zip_payload_matches_table_file(self, out_dir):
        rs, cfg = self._rseries()
        rep = FlychkHistoryWriter(cfg).write(rs, str(Path(out_dir) / "cmp"))
        r0 = rep.results[0]
        with zipfile.ZipFile(r0.zip_path) as zf:
            data = zf.read([n for n in zf.namelist() if n != "runfile.txt"][0]).decode()
        assert data == Path(r0.table_path).read_text(encoding="utf-8")

    def test_table_file_and_preview(self, out_dir):
        cfg = FlychkHisConfig(element="Ti", agg="mass", n_time_max=3,
                              write_preview=True)
        s = synthetic_ch_ti_slab(n_time=4, nx=200)
        rs = [extract_region(s, rg.whole(), cfg)]
        rep = FlychkHistoryWriter(cfg).write(rs, str(Path(out_dir) / "prev"))
        assert rep.results[0].table_path is not None
        assert rep.results[0].preview_path is not None
        assert Path(rep.results[0].preview_path).stat().st_size > 1000

    def test_skip_zip_on_validation_error(self, out_dir):
        # 无 size 列 + strict 使 warning 升级 -> 不写 zip, 报告标 ERR
        cfg = FlychkHisConfig(element="Ti", columns=["time", "te", "rho"],
                              agg="mass", strict=True)
        s = synthetic_ch_ti_slab(n_time=2, nx=100)
        rs = [extract_region(s, rg.whole(), cfg)]
        rep = FlychkHistoryWriter(cfg).write(rs, str(Path(out_dir) / "strict"))
        assert not rep.ok
        assert rep.zip_paths == []
        assert rep.errors

    def test_stage_zipfiles(self, out_dir):
        rs, cfg = self._rseries()
        rep = FlychkHistoryWriter(cfg).write(rs, str(Path(out_dir) / "stage"))
        copied = FlychkHistoryWriter.stage_zipfiles(rep)
        assert len(copied) == 2
        assert all(p.is_file() for p in copied)

    def test_missing_output_dir_raises(self):
        from flash.input_gen.gen_flychk_his import FlychkHistoryGenerator
        from flash.input_gen.gen_flychk_his.writer import WriterError
        gen = FlychkHistoryGenerator(element="Ti")
        with pytest.raises(WriterError):
            gen.generate(source=None, region="whole", output_dir=None)

    def test_zip_name_template(self, out_dir):
        cfg = FlychkHisConfig(element="C",
                              zip_name_template="his_{label}_{element}{z}.zip")
        s = synthetic_ch_ti_slab(n_time=2, nx=100)
        rs = [extract_region(s, rg.whole(), cfg)]
        rep = FlychkHistoryWriter(cfg).write(rs, str(Path(out_dir) / "tpl"))
        assert Path(rep.zip_paths[0]).name == "his_whole_C6.zip"
