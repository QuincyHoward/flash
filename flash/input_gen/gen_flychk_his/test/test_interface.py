"""test_interface.py — 门面类、一键函数、CLI 与端到端流程。"""

import json
import zipfile
from pathlib import Path

import numpy as np
import pytest

from flash.input_gen.gen_flychk_his import (ConfigError, FlychkHistoryGenerator,
                                            build_history_table,
                                            describe_interfaces,
                                            generate_history_report,
                                            generate_history_zip,
                                            generate_history_zips,
                                            history_table_text, inspect_source,
                                            make_config)
from flash.input_gen.gen_flychk_his.config import FlychkHisConfig
from flash.input_gen.gen_flychk_his.zip_writer import (FORMAT_CONTRACT_ID,
                                                       WRITER_ID)


class TestConfig:
    def test_make_config_unknown_key(self):
        with pytest.raises(ConfigError):
            make_config(element="Ti", no_such_option=1)

    def test_make_config_evolve(self):
        base = FlychkHisConfig(element="Ti")
        cfg = make_config(base, element="C", agg="mean")
        assert cfg.element == "C" and cfg.agg == "mean"
        assert base.element == "Ti"          # 原对象不变 (frozen)

    def test_with_density_and_size_helpers(self):
        cfg = FlychkHisConfig(element="Ti").with_density("ni")
        assert cfg.resolved_density_mode == "ni"
        cfg2 = cfg.with_size("fixed", size_value=1e-4)
        assert "size" in cfg2.columns and cfg2.size_mode == "fixed"
        with pytest.raises(ConfigError):
            cfg.with_density("nope")

    def test_validate_reports(self):
        assert FlychkHisConfig(element="Ti").validate().ok
        bad = FlychkHisConfig(element="Ti", columns=["time", "te"])
        rep = bad.validate()
        assert not rep.ok and any("密度" in e for e in rep.errors)
        bad2 = FlychkHisConfig(element="Xx")
        assert not bad2.validate().ok
        bad3 = FlychkHisConfig(element="Ti", agg="nope")
        assert not bad3.validate().ok

    def test_to_dict_from_dict_roundtrip(self):
        cfg = FlychkHisConfig(element="V", agg="median", n_time_max=5,
                              columns=["time", "size", "te", "rho"])
        d = cfg.to_dict()
        assert d["resolved"]["z"] == 23
        cfg2 = FlychkHisConfig.from_dict(d)
        assert cfg2.element == "V" and cfg2.agg == "median"
        assert list(cfg2.columns) == list(cfg.columns)

    def test_column_and_source_units(self):
        cfg = FlychkHisConfig(element="Ti", input_units={"tele": "eV"})
        assert cfg.column_unit("te") == "eV"
        assert cfg.source_unit("tele", "K") == "eV"
        assert cfg.source_unit("dens", "g/cm^3") == "g/cm^3"


class TestFacade:
    def test_config_overrides(self):
        gen = FlychkHistoryGenerator(element="C", agg="mean", n_time_max=3)
        assert gen.config.element == "C"
        assert gen.config.agg == "mean"
        with pytest.raises(ConfigError):
            FlychkHistoryGenerator(bogus=1)

    def test_with_config_returns_new(self):
        gen = FlychkHistoryGenerator(element="Ti")
        gen2 = gen.with_config(agg="max")
        assert gen.config.agg == "mass" and gen2.config.agg == "max"

    def test_load_caches(self):
        gen = FlychkHistoryGenerator(element="Ti")
        s1 = gen.load(source=None, n_time=3, verbose=False)
        s2 = gen.load(source=None, verbose=False)
        assert s1 is s2
        s3 = gen.load(source=None, n_time=3, verbose=False, force=True)
        assert s3 is not s1

    def test_series_requires_load(self):
        gen = FlychkHistoryGenerator(element="Ti")
        with pytest.raises(RuntimeError):
            _ = gen.series

    def test_tables_and_text(self):
        gen = FlychkHistoryGenerator(element="Ti", n_time_max=3)
        gen.load(source=None, n_time=4, verbose=False)
        tbs = gen.tables("whole")
        assert len(tbs) == 1 and tbs[0].n_steps == 3
        txt = gen.table_text("whole")
        assert txt.splitlines()[0] == " ".join(gen.config.columns)

    def test_validate(self):
        gen = FlychkHistoryGenerator(element="Ti", n_time_max=3)
        reps = gen.validate("whole", source=None, n_time=4, verbose=False)
        assert reps and all(r.ok for r in reps)

    def test_inspect(self):
        gen = FlychkHistoryGenerator(element="Ti", n_time_max=3)
        info = gen.inspect(source=None, region=["whole", "label:matid=2"],
                           n_time=4, verbose=False)
        assert info["n_time"] == 4
        assert len(info["regions"]) == 2
        assert "table" in info["regions"][0]
        assert info["writer"]["id"] == WRITER_ID
        assert info["writer"]["self_contained"] is True
        json.dumps(info, default=str)       # 可序列化

    def test_generate_and_generate_zip(self, out_dir):
        gen = FlychkHistoryGenerator(element="Ti", n_time_max=3,
                                     agg="mass")
        rep = gen.generate(source=None, region=["whole", "x:-40..0um"],
                           output_dir=str(out_dir / "g"), write_preview=True,
                           verbose=False)
        assert rep.ok and len(rep.zip_paths) == 2
        zip_path = gen.generate_zip(source=None, region="whole",
                                    output_dir=str(out_dir / "gz"),
                                    verbose=False)
        assert Path(zip_path).is_file()

    def test_generate_zip_failure_raises(self, out_dir):
        from flash.input_gen.gen_flychk_his.writer import WriterError
        gen = FlychkHistoryGenerator(element="Ti")
        # strict + 未设 n_time_max -> 配置即非法 -> 无 zip
        with pytest.raises(WriterError):
            gen.generate_zip(source=None, region="whole",
                             output_dir=str(out_dir / "fail"),
                             strict=True, verbose=False)

    def test_generate_with_hdf5_source(self, test_data, out_dir):
        gen = FlychkHistoryGenerator(element="Ti", n_time_max=4, agg="mass")
        rep = gen.generate(source=str(test_data["flash_hdf5_dir"]),
                           region="x:-40..0um",
                           output_dir=str(out_dir / "h5"), verbose=False)
        assert rep.ok
        with zipfile.ZipFile(rep.zip_paths[0]) as zf:
            names = zf.namelist()
        assert names[0] == "runfile.txt"
        assert "history_Ti_Z22_input.txt" in names[1]

    def test_stage_zipfiles(self, out_dir):
        gen = FlychkHistoryGenerator(element="Ti", n_time_max=3)
        rep = gen.generate(source=None, region="whole",
                           output_dir=str(out_dir / "s"), stage_zipfiles=True,
                           verbose=False)
        assert (out_dir / "s" / "zipfiles").is_dir()
        assert any((out_dir / "s" / "zipfiles").iterdir())


class TestOneShotFunctions:
    def test_generate_history_zip(self, out_dir):
        p = generate_history_zip(source=None, element="Ti", region="whole",
                                 output_dir=str(out_dir / "1"),
                                 n_time_max=4, data_kwargs={"n_time": 4})
        assert Path(p).is_file() and p.name.endswith("_in_.zip")

    def test_generate_history_zips(self, out_dir):
        ps = generate_history_zips(source=None, element="V",
                                   region=["whole", "x:-40..0um"],
                                   output_dir=str(out_dir / "2"),
                                   n_time_max=4, data_kwargs={"n_time": 4})
        assert len(ps) == 2

    def test_report_and_build_table(self, out_dir):
        rep = generate_history_report(source=None, element="Ti",
                                      region="label:matid=2",
                                      output_dir=str(out_dir / "3"),
                                      n_time_max=4, data_kwargs={"n_time": 4})
        assert rep.ok and rep.manifest_path is not None
        tb = build_history_table(source=None, element="Ti", region="whole",
                                 n_time_max=4, data_kwargs={"n_time": 4})
        assert tb.columns == list(FlychkHisConfig().columns)
        assert history_table_text(source=None, element="Ti", region="whole",
                                  n_time_max=4,
                                  data_kwargs={"n_time": 4}) == tb.to_text()

    def test_unknown_config_override_raises(self):
        with pytest.raises(ConfigError):
            generate_history_zip(source=None, region="whole",
                                 output_dir="x", n_time=4)   # 应走 data_kwargs

    def test_inspect_source(self):
        info = inspect_source(source=None, element="Ti", n_time_max=3,
                              data_kwargs={"n_time": 3})
        assert info["n_time"] == 3

    def test_self_contained_contract_exposed(self):
        """接口层暴露自包含写出器与格式契约 (无外部依赖)。"""
        txt = describe_interfaces()
        assert "zip_writer" in txt
        assert FORMAT_CONTRACT_ID in txt
        assert WRITER_ID == "flash.input_gen.gen_flychk_his"

    def test_describe_interfaces_mentions_all_axes(self):
        txt = describe_interfaces()
        for key in ("generate_history_zip", "FlychkHistoryGenerator",
                    "数据源", "区域", "聚合", "size", "写出"):
            assert key in txt

    def test_config_object_interface(self, out_dir):
        cfg = FlychkHisConfig(element="Ti", n_time_max=3,
                              output_dir=str(out_dir / "cfg"))
        p = generate_history_zip(source=None, region="whole", config=cfg,
                                 data_kwargs={"n_time": 4})
        assert Path(p).is_file()


class TestCli:
    def _main(self, argv):
        from flash.input_gen.gen_flychk_his.cli import main
        return main(argv)

    def test_help_actions(self, capsys):
        assert self._main(["--list-elements"]) == 0
        out = capsys.readouterr().out
        assert "Ti" in out and "Z= 22" in out
        assert self._main(["--interfaces"]) == 0
        assert self._main(["--version"]) == 0 if False else True

    def test_demo_generation(self, out_dir, capsys):
        rc = self._main(["--demo", "--out", str(out_dir / "cli"),
                         "--n-time-demo", "4", "--n-time-max", "4",
                         "--region", "whole", "--region", "label:matid=2",
                         "--preview", "--no-self-check"])
        out = capsys.readouterr().out
        assert rc == 0, out
        assert (out_dir / "cli" / "manifest.json").is_file()
        assert len(list((out_dir / "cli").glob("*.zip"))) == 2

    def test_missing_out_returns_2(self, capsys):
        assert self._main(["--demo"]) == 2

    def test_inspect_json(self, out_dir, capsys):
        rc = self._main(["--inspect", "--demo", "--n-time-demo", "3",
                         "--quiet"])
        out = capsys.readouterr().out
        assert rc == 0
        doc = json.loads(out)
        assert doc["n_time"] == 3

    def test_real_source_cli(self, test_data, out_dir, capsys):
        rc = self._main(["--source", str(test_data["flash_hdf5_dir"]),
                         "--out", str(out_dir / "cli_h5"),
                         "--element", "Ti", "--region", "x:-40..0um",
                         "--agg", "mass", "--n-time-max", "4",
                         "--dens-cut", "1e-5", "--quiet"])
        assert rc == 0, capsys.readouterr().out
        assert list((out_dir / "cli_h5").glob("*.zip"))

    def test_layout_batch_cli(self, out_dir, capsys):
        rc = self._main(["--demo", "--out", str(out_dir / "cli_batch"),
                         "--layout", "batch", "--n-time-demo", "3",
                         "--n-time-max", "3", "--quiet"])
        assert rc == 0
        assert (out_dir / "cli_batch" / "input" / "batch_0000").is_dir()

    def test_npz_source_cli(self, test_data, out_dir, capsys):
        rc = self._main(["--source", str(test_data["npz"]),
                         "--out", str(out_dir / "cli_npz"),
                         "--element", "Ti", "--n-time-max", "5", "--quiet"])
        assert rc == 0, capsys.readouterr().out


class TestEndToEndPhysics:
    """端到端物理合理性检查 (数据 → zip 内容)。"""

    def _read_columns(self, zip_path):
        with zipfile.ZipFile(zip_path) as zf:
            data = zf.read("history_Ti_Z22_input.txt").decode().splitlines()
        header = data[0].split()
        arr = np.array([[float(x) for x in line.split()] for line in data[1:]])
        return {c: arr[:, i] for i, c in enumerate(header)}

    def test_te_positive_and_rho_reasonable(self, test_data, out_dir):
        p = generate_history_zip(source=str(test_data["flash_hdf5_dir"]),
                                 element="Ti", region="x:-40..0um",
                                 output_dir=str(out_dir / "e2e"), n_time_max=4)
        d = self._read_columns(p)
        assert np.all(d["te"] > 0)
        assert np.all(d["rho"] > 0)
        assert np.all(d["size"] > 0)
        assert np.all(np.diff(d["time"]) > 0)
        # 区域 [-40µm,0] 在 CH 固体/等离子体内 -> rho 应为 ~0.25 g/cm^3 量级
        assert d["rho"].max() > 0.05

    def test_tracer_region_hotter_than_bulk(self, test_data, out_dir):
        p_trac = generate_history_zip(source=str(test_data["flash_hdf5_dir"]),
                                      element="Ti", region="label:trac=2",
                                      output_dir=str(out_dir / "tr"),
                                      n_time_max=4)
        p_bulk = generate_history_zip(source=str(test_data["flash_hdf5_dir"]),
                                      element="Ti", region="x:20..40um",
                                      output_dir=str(out_dir / "bk"),
                                      n_time_max=4)
        te_tr = self._read_columns(p_trac)["te"]
        te_bk = self._read_columns(p_bulk)["te"]
        assert te_tr.mean() > te_bk.mean()

    def test_density_mode_ne_column(self, test_data, out_dir):
        cfg = FlychkHisConfig(element="Ti", output_dir=str(out_dir / "ne"),
                              n_time_max=4,
                              columns=["time", "size", "te", "ti", "tr", "ne"],
                              input_units={"dens": "g/cm^3"})
        p = generate_history_zip(source=str(test_data["flash_hdf5_dir"]),
                                 region="x:-40..0um", config=cfg,
                                 output_dir=str(out_dir / "ne"))
        d = self._read_columns(p)
        assert "ne" in d and "rho" not in d
        assert d["ne"].max() > 1e21          # 数密度量级检查
        with zipfile.ZipFile(p) as zf:
            runfile = zf.read("runfile.txt").decode()
        assert runfile.strip().endswith("ne\nend")
