"""test_sources.py — 数据源加载与单位归一化。"""

import numpy as np
import pytest

from flash.input_gen.gen_flychk_his import load_series, synthetic_ch_ti_slab
from flash.input_gen.gen_flychk_his.config import FlychkHisConfig
from flash.input_gen.gen_flychk_his.sources import SnapshotSeries, widths_from_x
from flash.input_gen.gen_flychk_his.test import make_test_data as mtd
from flash.input_gen.gen_flychk_his import units


class TestSyntheticModels:
    def test_series_basic(self, synth_series):
        assert isinstance(synth_series, SnapshotSeries)
        assert synth_series.n_time == 6
        assert synth_series.meta["synthetic"] is True
        for name in ("dens", "tele", "tion", "trad", "nele", "nion", "matid"):
            assert name in synth_series.variables

    def test_units_are_canonical(self, synth_series):
        s = synth_series[0]
        assert s.get("tele").max() < 1e5          # eV, 不是 K (K 会 > 1e5)
        # 峰值温度随时间按 (t/tmax)^0.25 增长
        peaks = [float(sn.get("tele").max()) for sn in synth_series]
        assert peaks[-1] == pytest.approx(1200.0, rel=0.05)
        assert np.all(np.diff(peaks) > 0)
        # 平台密度 0.25 g/cm^3; 示踪层叠加 5% 增量 -> 上限 0.2625
        assert 0.25 <= float(s.get("dens").max()) <= 0.27
        assert float(s.get("dens").min()) == pytest.approx(1e-6, rel=1e-6)

    def test_x_sorted_and_widths(self, synth_series):
        x = synth_series[0].x
        assert np.all(np.diff(x) > 0)
        w = synth_series[0].cell_widths()
        assert w.size == x.size
        assert np.all(w > 0)
        assert float(w.sum()) == pytest.approx(x[-1] - x[0] + w[0], rel=0.05)

    def test_ablation_front_moves_forward(self, synth_series):
        """示踪层 (matid=2) 应随烧蚀面向 +x 移动。"""
        def front(snapshot):
            m = snapshot.get("matid") == 2.0
            assert m.any(), "示踪层未命中任何单元"
            return float(snapshot.x[m].min())

        x0 = front(synth_series[0])
        xN = front(synth_series[-1])
        assert xN > x0
        # 位移 ≈ v_abl × Δt = 2e5 cm/s × 1.4e-9 s = 2.8e-4 cm
        dt = float(synth_series[-1].time - synth_series[0].time)
        assert (xN - x0) == pytest.approx(2.0e5 * dt, rel=0.15)

    def test_widths_from_x(self):
        x = np.array([0.0, 1.0, 2.0, 5.0])
        w = widths_from_x(x)
        assert w.size == 4
        assert w[0] == pytest.approx(1.0)
        assert w[-1] == pytest.approx(3.0)


class TestDictSource:
    @staticmethod
    def _ev_cfg(**kw):
        """声明温度已是 eV 的配置 (默认策略是 FLASH 原生 K)。"""
        return FlychkHisConfig(element="Ti",
                               input_units={"tele": "eV", "tion": "eV",
                                            "trad": "eV"}, **kw)

    def test_kelvin_to_ev(self):
        doc = {"time": [1e-12], "x": [-1e-4, 0.0, 1e-4],
               "tele": [units.K_PER_EV * 100.0] * 3,
               "dens": [0.1] * 3}
        s = load_series(doc, verbose=False)
        assert float(s[0].get("tele")[0]) == pytest.approx(100.0, rel=1e-9)

    def test_eV_declared_passthrough(self):
        doc = {"time": [1e-12], "x": [-1e-4, 0.0, 1e-4],
               "tele": [900.0] * 3, "dens": [0.1] * 3}
        s = load_series(doc, config=self._ev_cfg(), verbose=False)
        assert float(s[0].get("tele")[0]) == pytest.approx(900.0, rel=1e-12)

    def test_alias_mapping(self):
        doc = {"time": [1e-12], "x": [0.0, 1.0], "te": [10.0, 20.0],
               "rho": [0.5, 0.6]}
        s = load_series(doc, config=self._ev_cfg(), verbose=False)
        assert "tele" in s[0].fields and "dens" in s[0].fields
        assert float(s[0].get("tele")[1]) == pytest.approx(20.0)
        assert float(s[0].get("dens")[1]) == pytest.approx(0.6)

    def test_scalar_field_broadcast(self):
        doc = {"time": [1e-12], "x": [0.0, 1.0, 2.0], "tele": 100.0}
        s = load_series(doc, config=self._ev_cfg(), verbose=False)
        assert s[0].get("tele").size == 3
        assert np.allclose(s[0].get("tele"), 100.0)

    def test_nele_nion_derived_from_ye_sumy(self):
        doc = {"time": [1e-12], "x": [0.0], "dens": 0.25,
               "ye": 3.5 / 13.011, "sumy": 1.0 / 13.011}
        s = load_series(doc, verbose=False)
        snap = s[0]
        assert float(snap.get("nele")[0]) == pytest.approx(
            0.25 * (3.5 / 13.011) * units.N_A, rel=1e-12)
        assert float(snap.get("nion")[0]) == pytest.approx(
            0.25 * (1.0 / 13.011) * units.N_A, rel=1e-12)
        derived = " ".join(snap.meta["derived"])
        assert "ye" in derived and "sumy" in derived

    def test_nele_estimated_without_ye(self):
        cfg = FlychkHisConfig(element="C", atomic_weight=12.011, zeff=6.0)
        doc = {"time": [1e-12], "x": [0.0], "dens": 0.25}
        s = load_series(doc, config=cfg, verbose=False)
        assert float(s[0].get("nele")[0]) == pytest.approx(
            0.25 * (6.0 / 12.011) * units.N_A, rel=1e-12)

    def test_unsorted_time_is_sorted(self):
        doc = {"time": [3e-9, 1e-9, 2e-9], "x": [0.0, 1.0],
               "tele": [[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]]}
        s = load_series(doc, config=self._ev_cfg(), verbose=False)
        assert list(s.times) == [1e-9, 2e-9, 3e-9]
        assert float(s[0].get("tele")[0]) == pytest.approx(2.0)

    def test_duplicate_x_removed(self):
        doc = {"time": [1e-12], "x": [0.0, 1.0, 1.0, 2.0],
               "tele": [1.0, 2.0, 9.0, 3.0]}
        s = load_series(doc, config=self._ev_cfg(), verbose=False)
        assert s[0].x.size == 3
        assert s[0].meta["n_duplicate_x_removed"] == 1

    def test_snapshots_list_source(self):
        doc = {"snapshots": [
            {"time": 1e-12, "x": [0.0, 1.0], "tele": [10.0, 20.0], "dens": [0.1, 0.2]},
            {"time": 2e-12, "x": [0.0, 1.0], "tele": [30.0, 40.0], "dens": [0.3, 0.4]},
        ]}
        s = load_series(doc, config=self._ev_cfg(), verbose=False)
        assert s.n_time == 2
        assert float(s[1].get("tele")[1]) == pytest.approx(40.0)

    def test_input_units_override(self):
        cfg = FlychkHisConfig(element="Ti",
                              input_units={"tele": "eV", "dens": "kg/m^3"})
        doc = {"time": [1e-12], "x": [0.0], "tele": [500.0], "dens": [250.0]}
        s = load_series(doc, config=cfg, verbose=False)
        assert float(s[0].get("tele")[0]) == pytest.approx(500.0)      # eV 原样
        assert float(s[0].get("dens")[0]) == pytest.approx(0.25)       # kg/m^3 -> g/cm^3

    def test_input_units_alias_key(self):
        """input_units 可用别名键 (rho 而非 dens)。"""
        cfg = FlychkHisConfig(element="Ti", input_units={"rho": "kg/m^3"})
        doc = {"time": [1e-12], "x": [0.0], "dens": [250.0]}
        s = load_series(doc, config=cfg, verbose=False)
        assert float(s[0].get("dens")[0]) == pytest.approx(0.25)


class TestCallableAndAux:
    def test_callable_source(self):
        x = np.linspace(-1e-4, 1e-4, 11)
        cfg = FlychkHisConfig(element="Ti", input_units={"tele": "eV"})

        def f(t):
            return {"x": x, "tele": np.full_like(x, 100.0 * t / 1e-12),
                    "dens": np.full_like(x, 0.1)}

        s = load_series(f, config=cfg, times=[1e-12, 2e-12], verbose=False)
        assert s.n_time == 2
        assert float(s[1].get("tele")[0]) == pytest.approx(200.0)

    def test_callable_without_times_raises(self):
        with pytest.raises(ValueError):
            load_series(lambda t: {"x": [0.0]}, verbose=False)

    def test_path_list_source(self, test_data):
        files = test_data["flash_files"][:3]
        s = load_series(list(files), config=FlychkHisConfig(element="Ti"),
                        verbose=False)
        assert s.n_time == 3

    def test_unsupported_type_raises(self):
        with pytest.raises(TypeError):
            load_series(12345, verbose=False)

    def test_missing_path_raises(self):
        with pytest.raises(FileNotFoundError):
            load_series("no/such/dir/flash_output", verbose=False)


class TestFileSources:
    def test_npz_source(self, test_data):
        s = load_series(str(test_data["npz"]), config=FlychkHisConfig(element="Ti"),
                        verbose=False)
        assert s.n_time == mtd.SERIES_TIMES.size
        x_ref, fields_ref = mtd.profiles(mtd.TMAX)
        # npz 中温度是 FLASH 原生 K -> 归一化后应为 eV
        assert float(s[-1].get("tele")[0]) == pytest.approx(
            fields_ref["tele"][0] / mtd.K_PER_EV, rel=1e-9)
        assert float(s[-1].get("dens")[0]) == pytest.approx(fields_ref["dens"][0],
                                                           rel=1e-9)

    def test_csv_source(self, test_data):
        s = load_series(str(test_data["csv"]), config=FlychkHisConfig(element="Ti"),
                        verbose=False)
        assert s.n_time == mtd.SERIES_TIMES.size
        assert s[0].x.size == mtd.NX
        assert "trac" in s.variables
        _, f_ref = mtd.profiles(mtd.TMAX)
        assert float(s[-1].get("tele")[0]) == pytest.approx(
            f_ref["tele"][0] / mtd.K_PER_EV, rel=1e-6)

    def test_json_fields_source(self, test_data):
        s = load_series(str(test_data["json"]), config=FlychkHisConfig(element="Ti"),
                        verbose=False)
        assert s.n_time == mtd.SERIES_TIMES.size
        assert "tele" in s.variables
        _, f_ref = mtd.profiles(mtd.TMAX)
        assert float(s[-1].get("tele")[0]) == pytest.approx(
            f_ref["tele"][0] / mtd.K_PER_EV, rel=1e-6)

    def test_json_snapshots_source(self, test_data):
        s = load_series(str(test_data["json_snapshots"]),
                        config=FlychkHisConfig(element="Ti"), verbose=False)
        assert s.n_time == mtd.SERIES_TIMES.size

    def test_json_self_declared_units(self, test_data):
        """hist_units.json 通过 units 键自声明 eV / kg·m^-3。"""
        s = load_series(str(test_data["json_units"]),
                        config=FlychkHisConfig(element="Ti"), verbose=False)
        _, f_ref = mtd.profiles(mtd.TMAX)
        assert float(s[-1].get("dens")[0]) == pytest.approx(f_ref["dens"][0], rel=1e-9)
        assert float(s[-1].get("tele")[0]) == pytest.approx(
            f_ref["tele"][0] / mtd.K_PER_EV, rel=1e-9)
        assert s.meta["declared_units"]["rho"] == "kg/m^3"

    def test_json_units_explicit_override_wins(self, test_data):
        cfg = FlychkHisConfig(element="Ti",
                             input_units={"tele": "eV", "rho": "kg/m^3"})
        s = load_series(str(test_data["json_units"]), config=cfg, verbose=False)
        _, f_ref = mtd.profiles(mtd.TMAX)
        assert float(s[-1].get("dens")[0]) == pytest.approx(f_ref["dens"][0], rel=1e-9)


class TestUnitSanityGuard:
    def test_warns_when_ev_values_declared_as_kelvin(self):
        doc = {"time": [1e-12], "x": [0.0, 1.0], "tele": [800.0, 900.0],
               "dens": [0.1, 0.2]}          # 明显是 eV, 但默认按 K 解释
        s = load_series(doc, verbose=False)
        assert "unit_warnings" in s[0].meta
        assert "eV" in s[0].meta["unit_warnings"][0]

    def test_no_warning_for_real_kelvin(self):
        doc = {"time": [1e-12], "x": [0.0], "tele": [1.0e6], "dens": [0.1]}
        s = load_series(doc, verbose=False)
        assert "unit_warnings" not in s[0].meta

    def test_warns_when_kelvin_declared_as_ev(self):
        cfg = FlychkHisConfig(element="Ti", input_units={"tele": "eV"})
        doc = {"time": [1e-12], "x": [0.0], "tele": [1.0e7], "dens": [0.1]}
        s = load_series(doc, config=cfg, verbose=False)
        assert "unit_warnings" in s[0].meta


class TestFlashHdf5Source:
    def test_directory_load(self, h5_series):
        assert h5_series.n_time == mtd.SERIES_TIMES.size
        assert h5_series.meta["kind"] == "flash_hdf5"
        assert h5_series.meta["extraction_mode"] == "h5py"
        assert h5_series.variables  # 非空

    def test_temperature_converted_k_to_ev(self, h5_series):
        x_ref, f_ref = mtd.profiles(mtd.TMAX)
        tele = h5_series[-1].get("tele")
        assert tele.size == x_ref.size
        # FLASH 中以 K 存储 -> 必须换算为 eV
        assert float(np.max(np.abs(tele - f_ref["tele"] / mtd.K_PER_EV))) \
            == pytest.approx(0.0, abs=1e-6)

    def test_density_values(self, h5_series):
        snap = h5_series[-1]
        dens = snap.get("dens")
        # 平台 0.25 g/cm^3 (示踪层 +5%), 本底 1e-6 g/cm^3
        assert 0.25 <= float(dens.max()) <= 0.27
        assert float(dens.min()) == pytest.approx(1e-6, rel=1e-6)
        # 未扰动固体 (40 µm < x < 49 µm, 仍在初始 CH 平板内) 应等于平台密度
        solid = dens[(snap.x > 40e-4) & (snap.x < 49e-4)]
        assert solid.size > 10
        assert np.allclose(solid, 0.25, atol=1e-9)
        # 平板外侧 (x > 60 µm) 为本底气体
        outer = dens[snap.x > 60e-4]
        assert np.allclose(outer, 1e-6, rtol=1e-6)
        # 高密度区应占相当比例的单元
        assert int((dens > 0.2).sum()) > 0.3 * dens.size

    def test_x_sorted_and_times(self, h5_series):
        assert np.all(np.diff(h5_series[-1].x) > 0)
        assert np.allclose(h5_series.times, mtd.SERIES_TIMES, rtol=1e-12)

    def test_derived_nele_present(self, h5_series):
        assert "nele" in h5_series[-1].fields
        assert float(h5_series[-1].get("nele").max()) > 1e22

    def test_single_file_source(self, test_data):
        s = load_series(str(test_data["flash_files"][0]),
                        config=FlychkHisConfig(element="Ti"), verbose=False)
        assert s.n_time == 1

    def test_yt_mode_optional(self, test_data):
        """extraction_mode='yt' 为可选路径 (无 yt 时跳过)。"""
        pytest.importorskip("yt")
        s = load_series(str(test_data["flash_files"][0]),
                        config=FlychkHisConfig(element="Ti"),
                        extraction_mode="yt", verbose=False)
        assert s.n_time == 1
        assert s[-1].x.size > 0
