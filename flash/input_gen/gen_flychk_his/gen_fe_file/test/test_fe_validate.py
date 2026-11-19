"""test_fe_validate.py — 校验清单逐条触发。"""

from __future__ import annotations

import pytest

from flash.input_gen.gen_flychk_his.gen_fe_file import (
    FeExplicitSeries, FeFileError, FeModel, build_fe_file, validate_fe_file,
)

OK_ENERGIES = [100.0, 500.0, 1000.0]
OK_RECORDS = [(0.0, 1e11, [1e-6, 1e-5, 1e-6])]


class TestErrors:
    def test_too_many_energy_points(self):
        energies = [10.0 + i for i in range(501)]
        records = [(0.0, 1e11, [1e-6] * 501)]
        rep = validate_fe_file(energies, records)
        assert not rep.ok and any("500" in e for e in rep.errors)

    def test_descending_grid(self):
        rep = validate_fe_file([1000.0, 500.0, 100.0], OK_RECORDS)
        assert not rep.ok and any("升序" in e for e in rep.errors)

    def test_non_positive_energy(self):
        rep = validate_fe_file([0.0, 500.0, 1000.0], OK_RECORDS)
        assert not rep.ok
        rep = validate_fe_file([-10.0, 500.0, 1000.0], OK_RECORDS)
        assert not rep.ok

    def test_nan_energy(self):
        rep = validate_fe_file([float("nan"), 500.0, 1000.0], OK_RECORDS)
        assert not rep.ok

    def test_negative_fe(self):
        rep = validate_fe_file(
            OK_ENERGIES, [(0.0, 1e11, [1e-6, -1e-5, 1e-6])])
        assert not rep.ok and any("为负" in e for e in rep.errors)

    def test_nan_fe(self):
        rep = validate_fe_file(
            OK_ENERGIES, [(0.0, 1e11, [1e-6, float("nan"), 1e-6])])
        assert not rep.ok

    def test_duplicate_time(self):
        rep = validate_fe_file(OK_ENERGIES, [
            (1e-9, 1e11, [1e-6, 1e-5, 1e-6]),
            (1e-9, 1e11, [1e-6, 1e-5, 1e-6]),
        ])
        assert not rep.ok and any("严格大于" in e for e in rep.errors)

    def test_empty_records(self):
        rep = validate_fe_file(OK_ENERGIES, [])
        assert not rep.ok

    def test_fe_length_mismatch(self):
        rep = validate_fe_file(OK_ENERGIES, [(0.0, 1e11, [1e-6, 1e-5])])
        assert not rep.ok and any("不一致" in e for e in rep.errors)

    def test_build_raises_on_error(self):
        with pytest.raises(Exception):
            build_fe_file(
                FeExplicitSeries(energies=[1000.0, 500.0, 100.0],
                                 records=OK_RECORDS))


class TestWarnings:
    def test_zero_density_warning_ok(self):
        rep = validate_fe_file(
            OK_ENERGIES, [(0.0, 0.0, [0.0, 0.0, 0.0])])
        assert rep.ok and rep.warnings

    def test_norm_deviation_warning(self):
        """粗网格麦克斯韦 (Te=100) 归一偏差 >5% -> warning。"""
        energies = [10.0, 50.0, 100.0, 300.0, 1000.0]
        fe = build_fe_file(
            FeModel(te_beam=100.0, beam_density=1e11, times=[0.0]),
            energies=energies,
        )
        assert any("归一偏差" in w for w in fe.report.warnings)
        assert "norm_deviation_max" in fe.report.info

    def test_fine_grid_no_norm_warning(self):
        energies = [1e-3 + i * 2.5 for i in range(400)]
        fe = build_fe_file(
            FeModel(te_beam=100.0, beam_density=1e11, times=[0.0]),
            energies=energies,
        )
        assert not any("归一偏差" in w for w in fe.report.warnings)


class TestExplicitMode:
    def test_explicit_rejects_duplicate_energies_arg(self):
        spec = FeExplicitSeries(energies=OK_ENERGIES, records=OK_RECORDS)
        with pytest.raises(FeFileError):
            build_fe_file(spec, energies=OK_ENERGIES)

    def test_explicit_requires_energies(self):
        with pytest.raises(FeFileError):
            build_fe_file(FeModel(te_beam=100.0, beam_density=1e11))

    def test_bad_spec_type(self):
        with pytest.raises(FeFileError):
            build_fe_file("not-a-spec", energies=OK_ENERGIES)
