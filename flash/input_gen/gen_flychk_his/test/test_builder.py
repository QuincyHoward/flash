"""test_builder.py — FLYCHK history 表构建与校验。"""

import re

import numpy as np
import pytest

from flash.input_gen.gen_flychk_his import regions as rg
from flash.input_gen.gen_flychk_his.builder import (BuilderError, HistoryTable,
                                                    build_table, validate_table)
from flash.input_gen.gen_flychk_his.config import FlychkHisConfig
from flash.input_gen.gen_flychk_his.extract import RegionSeries
from flash.input_gen.gen_flychk_his.sources import synthetic_ch_ti_slab


def make_series(times=(1e-12, 2e-12, 3e-12), te=(100.0, 200.0, 300.0),
                rho=(0.1, 0.2, 0.3), name="region", extra=None):
    cols = {"time": np.asarray(times, dtype=float),
            "te": np.asarray(te, dtype=float),
            "rho": np.asarray(rho, dtype=float),
            "size": np.full(len(times), 1.0e-4)}
    if extra:
        cols.update(extra)
    return RegionSeries(spec=rg.whole(name), times=np.asarray(times, dtype=float),
                        values=cols, notes={"agg": "mass"}, cells=np.full(len(times), 10))


class TestBuildTable:
    def test_from_region_series(self, synth_series, default_config):
        from flash.input_gen.gen_flychk_his import extract_region
        rs = extract_region(synth_series, rg.whole(), default_config)
        tb = build_table(rs, default_config)
        assert tb.columns == list(default_config.columns)
        assert tb.n_steps == min(len(rs), default_config.n_time_max)
        assert tb.element == "Ti" and tb.z == 22

    def test_row_format_matches_flychk(self):
        cfg = FlychkHisConfig(element="Ti", columns=["time", "size", "te", "rho"])
        tb = build_table(make_series(), cfg)
        txt = tb.to_text()
        lines = txt.splitlines()
        assert lines[0] == "time size te rho"
        for line in lines[1:]:
            for tok in line.split(" "):
                assert re.fullmatch(r"-?\d\.\d{6}e[+-]\d{2,3}", tok), tok

    def test_clamping_counts_and_values(self):
        cfg = FlychkHisConfig(element="Ti", columns=["time", "te", "rho"],
                              te_floor=50.0, te_ceil=250.0,
                              dens_floor=0.15, dens_ceil=0.25)
        tb = build_table(make_series(te=(10.0, 200.0, 900.0),
                                     rho=(0.01, 0.2, 5.0)), cfg)
        assert tb.column("te").tolist() == [50.0, 200.0, 250.0]
        assert tb.column("rho").tolist() == [0.15, 0.2, 0.25]
        assert tb.meta["clamped"]["te"] == 2
        assert tb.meta["clamped"]["rho"] == 2

    def test_nan_interpolation(self):
        cfg = FlychkHisConfig(element="Ti", columns=["time", "te", "rho"])
        tb = build_table(make_series(te=(100.0, np.nan, 300.0)), cfg)
        assert tb.column("te")[1] == pytest.approx(200.0)
        assert tb.meta["nan_filled"]["te"] == 1

    def test_nan_edge_uses_nearest(self):
        cfg = FlychkHisConfig(element="Ti", columns=["time", "te", "rho"])
        tb = build_table(make_series(te=(np.nan, 200.0, 300.0)), cfg)
        assert tb.column("te")[0] == pytest.approx(200.0)

    def test_all_nan_column_raises(self):
        cfg = FlychkHisConfig(element="Ti", columns=["time", "te", "rho"])
        with pytest.raises(BuilderError):
            build_table(make_series(te=(np.nan, np.nan, np.nan)), cfg)

    def test_drop_nonpositive_time(self):
        cfg = FlychkHisConfig(element="Ti", columns=["time", "te", "rho"])
        tb = build_table(make_series(times=(0.0, 1e-12, 2e-12)), cfg)
        assert tb.n_steps == 2
        assert tb.meta["dropped"]["nonpositive_time"] == 1
        assert tb.column("time").min() > 0

    def test_keep_nonpositive_time_when_disabled(self):
        cfg = FlychkHisConfig(element="Ti", columns=["time", "te", "rho"],
                              drop_nonpositive_time=False)
        tb = build_table(make_series(times=(0.0, 1e-12, 2e-12)), cfg)
        assert tb.n_steps == 3

    def test_time_unit_ps(self):
        cfg = FlychkHisConfig(element="Ti", columns=["time", "te", "rho"],
                              time_unit="ps")
        tb = build_table(make_series(), cfg)
        assert tb.column("time")[0] == pytest.approx(1.0)      # 1e-12 s = 1 ps
        assert tb.meta["time_unit"] == "ps"
        # meta 同时保留秒值以便追溯
        assert tb.meta["time_span_seconds"][0] == pytest.approx(1e-12)

    def test_time_window(self):
        cfg = FlychkHisConfig(element="Ti", columns=["time", "te", "rho"],
                              tmin=1e-12, tmax=2e-12)
        tb = build_table(make_series(), cfg)
        assert tb.n_steps == 2

    def test_time_stride(self):
        cfg = FlychkHisConfig(element="Ti", columns=["time", "te", "rho"],
                              time_stride=2)
        rs = make_series(times=[1e-12, 2e-12, 3e-12, 4e-12],
                         te=[1, 2, 3, 4], rho=[1, 2, 3, 4])
        tb = build_table(rs, cfg)
        assert tb.column("time").tolist() == [1e-12, 3e-12]

    def test_n_time_max_keeps_ends(self):
        times = [float(i) * 1e-12 for i in range(1, 11)]
        cfg = FlychkHisConfig(element="Ti", columns=["time", "te", "rho"],
                              n_time_max=4)
        rs = make_series(times=times, te=list(range(1, 11)), rho=[1.0] * 10)
        tb = build_table(rs, cfg)
        assert tb.n_steps == 4
        assert tb.column("time")[0] == pytest.approx(times[0])
        assert tb.column("time")[-1] == pytest.approx(times[-1])

    def test_time_sorted_and_dedup(self):
        cfg = FlychkHisConfig(element="Ti", columns=["time", "te", "rho"])
        rs = make_series(times=(3e-12, 1e-12, 3e-12), te=(30, 10, 31),
                         rho=(0.3, 0.1, 0.31))
        tb = build_table(rs, cfg)
        t = tb.column("time")
        assert np.all(np.diff(t) > 0)
        assert tb.meta["dropped"]["duplicate_time"] == 1

    def test_density_mode_switch(self):
        cfg = (FlychkHisConfig(element="Ti", columns=["time", "size", "te", "rho"])
               .with_density("ne"))
        assert "ne" in cfg.columns and "rho" not in cfg.columns
        rs = make_series(extra={"ne": np.array([1e20, 2e20, 3e20])})
        tb = build_table(rs, cfg)
        assert "ne" in tb.columns and "rho" not in tb.columns

    def test_missing_column_gives_clear_error(self):
        cfg = FlychkHisConfig(element="Ti")          # 默认含 ti/tr, rs 中没有
        with pytest.raises(BuilderError) as ei:
            build_table(make_series(), cfg)
        assert "缺少列" in str(ei.value)

    def test_empty_region_series_raises(self):
        rs = RegionSeries(spec=rg.whole(), times=np.array([]), values={
            "time": np.array([]), "te": np.array([]), "rho": np.array([]),
            "size": np.array([])})
        with pytest.raises(BuilderError):
            build_table(rs, FlychkHisConfig(element="Ti"))

    def test_no_time_after_filter_raises(self):
        cfg = FlychkHisConfig(element="Ti", columns=["time", "te", "rho"],
                              tmin=1.0)      # 所有点都在 1e-12 s, 全被裁掉
        with pytest.raises(BuilderError):
            build_table(make_series(), cfg)

    def test_csv_and_dict_export(self, synth_series, default_config):
        from flash.input_gen.gen_flychk_his import extract_region
        rs = extract_region(synth_series, rg.whole(), default_config)
        tb = build_table(rs, default_config)
        assert tb.to_csv().splitlines()[0] == ",".join(tb.columns)
        d = tb.as_dict()
        assert set(d) == set(tb.columns)
        assert d["time"].size == tb.n_steps
        assert "步" in tb.summary()


class TestValidateTable:
    def test_valid_table(self, synth_series, default_config):
        from flash.input_gen.gen_flychk_his import extract_region
        rs = extract_region(synth_series, rg.whole(), default_config)
        rep = validate_table(build_table(rs, default_config), default_config)
        assert rep.ok, rep.errors

    def test_missing_density_column_is_error(self):
        tb = HistoryTable(columns=["time", "te"],
                          rows=[[1e-12, 100.0]], meta={})
        rep = validate_table(tb, FlychkHisConfig(element="Ti"))
        assert not rep.ok
        assert any("密度列" in e for e in rep.errors)

    def test_multiple_density_columns_is_error(self):
        tb = HistoryTable(columns=["time", "te", "rho", "ne"],
                          rows=[[1e-12, 100.0, 0.1, 1e20]], meta={})
        rep = validate_table(tb, FlychkHisConfig(element="Ti"))
        assert not rep.ok

    def test_non_monotonic_time_is_error(self):
        tb = HistoryTable(columns=["time", "te", "rho"],
                          rows=[[2e-12, 100.0, 0.1], [1e-12, 100.0, 0.1]], meta={})
        rep = validate_table(tb, FlychkHisConfig(element="Ti"))
        assert not rep.ok
        assert any("递增" in e for e in rep.errors)

    def test_nonpositive_time_is_error(self):
        tb = HistoryTable(columns=["time", "te", "rho"],
                          rows=[[0.0, 100.0, 0.1]], meta={})
        rep = validate_table(tb, FlychkHisConfig(element="Ti"))
        assert not rep.ok

    def test_ragged_rows_is_error(self):
        tb = HistoryTable(columns=["time", "te", "rho"],
                          rows=[[1e-12, 100.0]], meta={})
        rep = validate_table(tb, FlychkHisConfig(element="Ti"))
        assert not rep.ok

    def test_many_steps_warns(self):
        rows = [[float(i) * 1e-12, 100.0, 0.1] for i in range(1, 80)]
        tb = HistoryTable(columns=["time", "te", "rho"], rows=rows, meta={})
        rep = validate_table(tb, FlychkHisConfig(element="Ti"))
        assert rep.ok and any("时间步数" in w for w in rep.warnings)

    def test_strict_promotes_warnings(self):
        rows = [[float(i) * 1e-12, 100.0, 0.1] for i in range(1, 80)]
        tb = HistoryTable(columns=["time", "te", "rho"], rows=rows, meta={})
        rep = validate_table(tb, FlychkHisConfig(element="Ti", strict=True))
        assert not rep.ok

    def test_missing_size_warns(self):
        tb = HistoryTable(columns=["time", "te", "rho"],
                          rows=[[1e-12, 100.0, 0.1]], meta={})
        rep = validate_table(tb, FlychkHisConfig(element="Ti"))
        assert any("opacity" in w for w in rep.warnings)


class TestSizeStrategies:
    def _extract(self, mode, **kw):
        from flash.input_gen.gen_flychk_his import extract_region
        cfg = FlychkHisConfig(element="Ti", size_mode=mode, **kw)
        s = synthetic_ch_ti_slab(n_time=2, nx=400)
        return extract_region(s, rg.parse_region("x:-40..0um"), cfg)

    def test_extent_equals_region_thickness(self):
        rs = self._extract("extent")
        size = rs.column("size")
        assert np.all(size > 0)
        # 区域 [-40µm, 0] 厚度 ≈ 40 µm (含半个边界单元)
        assert np.all(np.abs(size - 40e-4) < 3e-4)

    def test_fixed(self):
        rs = self._extract("fixed", size_value=5.0e-4)
        assert np.allclose(rs.column("size"), 5.0e-4)

    def test_scale_length_bounded_by_extent(self):
        rs = self._extract("scale_length_ne")
        size = rs.column("size")
        assert np.all(size > 0)
        # size_cap_extent=True -> 不超过区域厚度 (含半边界单元, 略大于 40 µm)
        assert np.all(size <= 40.5e-4)

    def test_size_scale_applied(self):
        a = self._extract("extent", size_scale=1.0).column("size")
        b = self._extract("extent", size_scale=2.0).column("size")
        assert np.allclose(b, 2.0 * a)


class TestAggregations:
    @pytest.mark.parametrize("agg", ["mean", "median", "mass", "volume",
                                     "max", "min", "center", "peak_dens",
                                     "percentile:50"])
    def test_all_aggregations_run(self, agg):
        from flash.input_gen.gen_flychk_his import extract_region
        cfg = FlychkHisConfig(element="Ti", agg=agg)
        s = synthetic_ch_ti_slab(n_time=2, nx=200)
        rs = extract_region(s, rg.parse_region("x:-40..0um"), cfg)
        te = rs.column("te")
        assert te.size == 2 and np.all(np.isfinite(te))

    def test_aggregation_ordering(self):
        from flash.input_gen.gen_flychk_his import extract_region
        s = synthetic_ch_ti_slab(n_time=1, nx=300)
        spec = rg.parse_region("x:-40..0um")
        vals = {}
        for agg in ("min", "mean", "max"):
            rs = extract_region(s, spec, FlychkHisConfig(element="Ti", agg=agg))
            vals[agg] = float(rs.column("te")[0])
        assert vals["min"] <= vals["mean"] <= vals["max"]

    def test_custom_aggregator(self):
        from flash.input_gen.gen_flychk_his import extract_region
        cfg = FlychkHisConfig(element="Ti", agg=lambda v, s, m: float(np.sum(v)))
        s = synthetic_ch_ti_slab(n_time=1, nx=100)
        rs = extract_region(s, rg.whole(), cfg)
        assert float(rs.column("te")[0]) > 0

    def test_unknown_aggregator_raises(self):
        from flash.input_gen.gen_flychk_his.extract import resolve_aggregator, ExtractError
        with pytest.raises(ExtractError):
            resolve_aggregator("bogus")

    def test_region_time_series_ordering(self, synth_series):
        from flash.input_gen.gen_flychk_his import extract_region
        cfg = FlychkHisConfig(element="Ti", agg="mass")
        whole = extract_region(synth_series, rg.whole(), cfg)
        trac = extract_region(synth_series, rg.parse_region("label:matid=2"), cfg)
        # 示踪层位于烧蚀面附近 (高温), 全域质量加权平均包含大量冷物质
        assert float(np.mean(trac.column("te"))) > float(np.mean(whole.column("te")))

    def test_column_fallback_recorded(self):
        from flash.input_gen.gen_flychk_his import extract_region
        s = synthetic_ch_ti_slab(n_time=2, nx=100)
        for snap in s:                       # 制造缺少 tion/trad 的数据
            snap.fields.pop("tion", None)
            snap.fields.pop("trad", None)
        cfg = FlychkHisConfig(element="Ti")
        rs = extract_region(s, rg.whole(), cfg)
        assert rs.notes["column_fallback"]["ti"] == "tele"
        assert rs.notes["column_fallback"]["tr"] == "tele"

    def test_missing_required_column_raises(self):
        from flash.input_gen.gen_flychk_his import extract_region
        from flash.input_gen.gen_flychk_his.extract import ExtractError
        s = synthetic_ch_ti_slab(n_time=1, nx=50)
        s[0].fields.pop("tele", None)
        s[0].fields.pop("dens", None)
        with pytest.raises(ExtractError):
            extract_region(s, rg.whole(), FlychkHisConfig(element="Ti"))
