"""test_fe_model.py — 解析模型数学正确性。"""

from __future__ import annotations

import math

import pytest

from flash.input_gen.gen_flychk_his.config import ConfigError
from flash.input_gen.gen_flychk_his.gen_fe_file import (
    FeModel, build_fe_file, maxwell_fe,
)
from flash.input_gen.gen_flychk_his.gen_fe_file.fe_file import _trapz_sqrt_e_fe


# ── maxwell_fe 解析值 ────────────────────────────────────────
class TestMaxwellFE:
    def test_analytic_values(self):
        """Te=100 eV 手算精确值。"""
        base = 2.0 / math.sqrt(math.pi) / 100.0 ** 1.5  # fe(0)
        assert maxwell_fe(0.0, 100.0) == pytest.approx(base)
        assert maxwell_fe(50.0, 100.0) == pytest.approx(base * math.exp(-0.5))
        assert maxwell_fe(100.0, 100.0) == pytest.approx(base * math.exp(-1.0))

    def test_monotone_decreasing_positive(self):
        energies = [10.0 * i + 1.0 for i in range(200)]
        fe = [maxwell_fe(e, 100.0) for e in energies]
        assert all(v > 0 for v in fe)
        assert all(fe[i + 1] < fe[i] for i in range(len(fe) - 1))

    def test_negative_te_raises(self):
        with pytest.raises(Exception):
            maxwell_fe(10.0, -1.0)


# ── build_fe_file: FeModel ──────────────────────────────────
FINE_GRID = [1e-3 + i * 2.5 for i in range(400)]  # ~0~1000 eV, 400 点 (<=500 上限)


class TestBuildModel:
    def test_fine_grid_integral_matches_density(self):
        """细网格 (400 点, 0~10*Te) 梯形积分 ≈ n_beam (rtol 5e-3)。"""
        n_beam = 1e11
        fe = build_fe_file(
            FeModel(te_beam=100.0, beam_density=n_beam, times=[0.0]),
            energies=FINE_GRID,
        )
        assert fe.n_steps == 1 and fe.n_energies == len(FINE_GRID)
        integral = _trapz_sqrt_e_fe(fe.energies, fe.records[0][2])
        assert integral == pytest.approx(n_beam, rel=5e-3)

    def test_densities_scale_fe(self):
        """densities 逐时间点缩放: fe 比 == 密度比。"""
        fe = build_fe_file(
            FeModel(te_beam=100.0, beam_density=1e11,
                    times=[0.0, 1e-9, 2e-9],
                    densities=[1e11, 5e10, 1e10]),
            energies=FINE_GRID,
        )
        f0 = fe.records[0][2]
        for k, dens in enumerate([1e11, 5e10, 1e10]):
            ratio = fe.records[k][2][100] / f0[100]
            assert ratio == pytest.approx(dens / 1e11, rel=1e-9)

    def test_empty_times_single_step_t0(self):
        fe = build_fe_file(
            FeModel(te_beam=100.0, beam_density=1e11), energies=FINE_GRID)
        assert fe.n_steps == 1
        assert fe.records[0][0] == 0.0

    def test_negative_te_error(self):
        with pytest.raises(ConfigError):
            build_fe_file(
                FeModel(te_beam=-5.0, beam_density=1e11), energies=FINE_GRID)

    def test_unknown_model_error(self):
        with pytest.raises(ConfigError):
            build_fe_file(
                FeModel(te_beam=100.0, beam_density=1e11, model="kappa"),
                energies=FINE_GRID)

    def test_zero_density_warning_not_error(self):
        """束密度=0 是合法物理 (束关闭): warning 但 ok。"""
        fe = build_fe_file(
            FeModel(te_beam=100.0, beam_density=0.0, times=[0.0, 1e-9],
                    densities=[0.0, 1e11]),
            energies=FINE_GRID,
        )
        assert fe.report.ok and fe.report.warnings

    def test_negative_density_error(self):
        """负束密度在模型模式下产生负 fe -> error。"""
        with pytest.raises(ConfigError):
            build_fe_file(
                FeModel(te_beam=100.0, beam_density=-1e11), energies=FINE_GRID)

    def test_drift_maxwell(self):
        """漂移麦克斯韦: E<=E0 处 fe=0, 积分归一到 n_beam。"""
        e0 = 2000.0
        grid = [100.0 + i * 50.0 for i in range(200)]  # 100~10050 eV
        fe = build_fe_file(
            FeModel(te_beam=500.0, beam_density=1e11, model="drift_maxwell",
                    drift_energy=e0),
            energies=grid,
        )
        vals = fe.records[0][2]
        below = [v for e, v in zip(grid, vals) if e <= e0]
        assert all(v == 0.0 for v in below)
        integral = _trapz_sqrt_e_fe(grid, vals)
        assert integral == pytest.approx(1e11, rel=1e-9)

    def test_mono_beam(self):
        """单能束: 峰在 E0, 积分归一到 n_beam。"""
        grid = [1000.0 + i * 10.0 for i in range(200)]
        fe = build_fe_file(
            FeModel(te_beam=100.0, beam_density=1e11, model="mono",
                    mono_energy=2000.0, mono_width=50.0),
            energies=grid,
        )
        vals = fe.records[0][2]
        peak = grid[vals.index(max(vals))]
        assert peak == pytest.approx(2000.0, abs=15.0)
        integral = _trapz_sqrt_e_fe(grid, vals)
        assert integral == pytest.approx(1e11, rel=1e-9)


class TestNormalizeToDensity:
    def test_coarse_grid_exact_after_normalize(self):
        """粗网格 + normalize_to_density=True -> 网格积分精确 = n_beam。"""
        n_beam = 1e11
        coarse = [10.0, 50.0, 100.0, 300.0, 1000.0]  # 粗网格
        fe_raw = build_fe_file(
            FeModel(te_beam=100.0, beam_density=n_beam, times=[0.0]),
            energies=coarse,
        )
        raw_integral = _trapz_sqrt_e_fe(coarse, fe_raw.records[0][2])
        assert raw_integral != pytest.approx(n_beam, rel=1e-6)  # 粗网格有偏差

        fe_norm = build_fe_file(
            FeModel(te_beam=100.0, beam_density=n_beam, times=[0.0],
                    normalize_to_density=True),
            energies=coarse,
        )
        norm_integral = _trapz_sqrt_e_fe(coarse, fe_norm.records[0][2])
        assert norm_integral == pytest.approx(n_beam, rel=1e-12)
        assert fe_norm.meta["normalize_to_density"] is True

    def test_coarse_grid_warning_without_normalize(self):
        """粗网格不归一 -> 归一偏差 warning。"""
        fe = build_fe_file(
            FeModel(te_beam=100.0, beam_density=1e11, times=[0.0]),
            energies=[10.0, 50.0, 100.0, 300.0, 1000.0],
        )
        assert any("归一偏差" in w for w in fe.report.warnings)
