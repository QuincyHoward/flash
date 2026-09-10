"""test_units.py — 单位换算与元素常量表。"""

import numpy as np
import pytest

from flash.input_gen.gen_flychk_his import units


class TestUnitConversion:
    def test_kelvin_to_ev_exact(self):
        # k_B = 8.617333262e-5 eV/K -> 1 eV = 11604.5181... K
        assert units.K_PER_EV == pytest.approx(1.0 / units.KB_EV, rel=1e-15)
        assert units.K_PER_EV == pytest.approx(11604.5181, rel=1e-7)
        assert float(units.temp_to_ev([units.K_PER_EV], "K")[0]) == pytest.approx(1.0, rel=1e-12)
        # 典型量级: 1000 eV ≈ 1.16e7 K
        assert float(units.temp_to_ev([1.16045e7], "K")[0]) == pytest.approx(1000.0, rel=1e-4)

    def test_kev_and_ev(self):
        assert float(units.temp_to_ev(1.0, "eV")) == 1.0
        assert float(units.temp_to_ev(1.0, "keV")) == 1000.0

    def test_ev_to_kelvin_roundtrip(self):
        ev = np.array([1.0, 100.0, 1200.0])
        k = units.ev_to_temp(ev, "K")
        assert np.allclose(units.temp_to_ev(k, "K"), ev, rtol=1e-12)

    def test_length(self):
        assert float(units.to_cm(1.0, "um")) == pytest.approx(1e-4)
        assert float(units.to_cm(1.0, "mm")) == pytest.approx(0.1)
        assert float(units.to_cm(1.0, "cm")) == pytest.approx(1.0)
        assert float(units.to_cm(1.0, "m")) == pytest.approx(100.0)

    def test_time(self):
        assert float(units.to_s(1.0, "ps")) == pytest.approx(1e-12)
        assert float(units.to_s(1.0, "ns")) == pytest.approx(1e-9)
        assert float(units.to_s(1.0, "fs")) == pytest.approx(1e-15)

    def test_density(self):
        assert float(units.to_dens_cgs(1000.0, "kg/m^3")) == pytest.approx(1.0)
        assert float(units.to_dens_cgs(1.0, "g/cm^3")) == pytest.approx(1.0)

    def test_number_density(self):
        assert float(units.to_numdens_cgs(1e6, "m^-3")) == pytest.approx(1.0)
        assert float(units.to_numdens_cgs(1.0, "cm^-3")) == pytest.approx(1.0)

    def test_unit_string_normalization(self):
        # 空白/大小写无关
        assert float(units.to_cm(1.0, " UM ")) == pytest.approx(1e-4)
        assert float(units.temp_to_ev(1.0, "eV")) == 1.0

    @pytest.mark.parametrize("bad", ["foo", "kg", "Kelvin2"])
    def test_unknown_unit_raises(self, bad):
        with pytest.raises(ValueError):
            units.to_cm(1.0, bad)

    def test_unknown_temp_unit_raises(self):
        with pytest.raises(ValueError):
            units.ev_to_temp(1.0, "Ry")


class TestElementTable:
    def test_z_lookup_case_insensitive(self):
        assert units.element_z("Ti") == 22
        assert units.element_z("ti") == 22
        assert units.element_z("c") == 6

    def test_atomic_weight(self):
        assert units.element_a("Ti") == pytest.approx(47.867)
        assert units.element_a("C") == pytest.approx(12.011)

    def test_unknown_element_raises(self):
        with pytest.raises(ValueError):
            units.element_z("Xx")

    def test_window_records(self):
        # 谱窗取自本仓库既有产物命名 (grid_b0_Ti_Z22_out_[4655,4810].zip 等)
        assert units.element_window("Ti", "he") == (4655.0, 4810.0)
        assert units.element_window("Ti", "ly") == (4921.0, 5032.0)
        assert units.element_window("V", "he") == (5110.0, 5240.0)
        assert units.element_window("Au") is None

    def test_element_table_snapshot(self):
        t = units.element_table()
        assert t["Ti"]["z"] == 22
        assert "window" in t["Ti"]
        assert t["H"]["z"] == 1


class TestDensityDerivation:
    def test_nele_from_rho(self):
        rho, zeff, aion = 0.25, 6.0, 12.011
        expected = rho * (zeff / aion) * units.N_A
        got = float(units.nele_from_rho(rho, zeff, aion))
        assert got == pytest.approx(expected, rel=1e-12)
        assert got == pytest.approx(7.52e22, rel=0.01)

    def test_nion_from_rho(self):
        rho, aion = 0.25, 12.011
        assert float(units.nion_from_rho(rho, aion)) == pytest.approx(
            rho / aion * units.N_A, rel=1e-12)

    def test_zero_atomic_weight_raises(self):
        with pytest.raises(ValueError):
            units.nele_from_rho(1.0, 6.0, 0.0)
