"""test_regions.py — 区域选择策略与字符串 DSL。"""

import numpy as np
import pytest

from flash.input_gen.gen_flychk_his import regions as rg
from flash.input_gen.gen_flychk_his.sources import synthetic_ch_ti_slab


@pytest.fixture()
def snap():
    return synthetic_ch_ti_slab(n_time=2, nx=400)[-1]


class TestDslParsing:
    @pytest.mark.parametrize("spec,kind", [
        ("whole", "whole"),
        ("all", "whole"),
        ("*", "whole"),
        ("x:-40..0um", "x_range"),
        ("x:[-40,0]um", "x_range"),
        ("rho:0.1..10", "dens_range"),
        ("dens:0.1:1.0", "dens_range"),
        ("mass:0..0.5", "mass_range"),
        ("label:trac=2", "label"),
        ("label:trac=1,2", "label"),
        ("label:dens>=0.1", "label"),
        ("label:dens<=1e-3", "label"),
        ("layer:1/4", "layer"),
        ("top:10%", "top_fraction"),
        ("top:0.1@tele", "top_fraction"),
        ("index:0:60", "index_slice"),
    ])
    def test_kinds(self, spec, kind):
        assert rg.parse_region(spec).kind == kind

    def test_x_range_values_in_cm(self):
        r = rg.parse_region("x:-40..0um")
        assert r.params["lo"] == pytest.approx(-40e-4)
        assert r.params["hi"] == pytest.approx(0.0)

    def test_x_range_cm_default(self):
        r = rg.parse_region("x:-0.01..0.0")
        assert r.params["lo"] == pytest.approx(-0.01)

    def test_label_values(self):
        r = rg.parse_region("label:trac=1,2")
        assert r.params["field"] == "trac"
        assert r.params["values"] == [1.0, 2.0]

    def test_label_threshold(self):
        assert rg.parse_region("label:dens>=0.1").params["above"] == 0.1
        assert rg.parse_region("label:dens<=0.1").params["below"] == 0.1

    def test_layer_one_based(self):
        r = rg.parse_region("layer:1/4")
        assert r.params["index"] == 0 and r.params["n_layers"] == 4

    def test_top_percent(self):
        assert rg.parse_region("top:10%").params["frac"] == pytest.approx(0.1)

    @pytest.mark.parametrize("bad", ["bogus:1", "x:", "layer:0/4", "label:trac",
                                     "mass:0.5..0.1", "top:150%", "z:1"])
    def test_invalid_specs(self, bad):
        with pytest.raises(rg.RegionError):
            rg.parse_region(bad)

    def test_other_forms(self):
        assert rg.parse_region((0.0, 1.0)).kind == "x_range"
        assert rg.parse_region({"x": (-0.01, 0.0)}).kind == "x_range"
        assert rg.parse_region({"dens": (0.1, 1.0)}).kind == "dens_range"
        assert rg.parse_region({"mass": (0.0, 0.5)}).kind == "mass_range"
        spec = rg.RegionSpec(name="a", kind="whole")
        assert rg.parse_region(spec) is spec
        assert rg.parse_region(lambda s: np.ones(s.x.size, bool)).kind == "custom"
        with pytest.raises(rg.RegionError):
            rg.parse_region({"kind": "nope"})

    def test_resolve_regions_forms(self):
        assert len(rg.resolve_regions(None)) == 1
        assert len(rg.resolve_regions("whole")) == 1
        assert len(rg.resolve_regions(["whole", "x:0..1cm", "layer:1/2"])) == 3
        assert len(rg.resolve_regions((0.0, 1.0))) == 1
        with pytest.raises(rg.RegionError):
            rg.resolve_regions([])


class TestFactoryFunctions:
    def test_whole_and_x_range(self):
        assert rg.whole().kind == "whole"
        r = rg.x_range(-40, 0, unit="um")
        assert r.params["hi"] == 0.0
        with pytest.raises(rg.RegionError):
            rg.x_range(1.0, 0.0)

    def test_mass_range_validation(self):
        with pytest.raises(rg.RegionError):
            rg.mass_range(0.6, 0.5)

    def test_label_requires_criterion(self):
        with pytest.raises(rg.RegionError):
            rg.label("trac")

    def test_top_fraction_validation(self):
        with pytest.raises(rg.RegionError):
            rg.top_fraction(1.5).mask(synthetic_ch_ti_slab(n_time=1, nx=50)[0])

    def test_custom_requires_callable(self):
        with pytest.raises(rg.RegionError):
            rg.custom("not_callable")

    def test_serialization_roundtrip(self):
        r = rg.x_range(-40, 0, unit="um", name="tracer_side")
        d = r.to_dict()
        r2 = rg.RegionSpec.from_dict(d)
        assert r2.kind == r.kind and r2.name == r.name
        assert r2.params["lo"] == pytest.approx(r.params["lo"])


class TestMasks:
    def test_x_range_mask_matches_manual(self, snap):
        spec = rg.parse_region("x:-40..0um")
        m = spec.mask(snap)
        manual = (snap.x >= -40e-4) & (snap.x <= 0.0)
        assert m.sum() == manual.sum()
        assert m.sum() > 0

    def test_dens_range_mask(self, snap):
        spec = rg.dens_range(0.1, 1.0)
        m = spec.mask(snap)
        assert m.sum() > 0
        assert np.all(snap.get("dens")[m] >= 0.1)
        assert np.all(snap.get("dens")[m] <= 1.0)

    def test_dens_cut_applied(self, snap):
        base = rg.whole().mask(snap)
        cut = rg.whole().mask(snap, dens_cut=0.1)
        assert cut.sum() < base.sum()

    def test_label_equality(self, snap):
        m = rg.parse_region("label:matid=2").mask(snap)
        assert m.sum() >= 1
        assert np.all(snap.get("matid")[m] == 2.0)

    def test_label_multi_value(self, snap):
        m = rg.label("matid", values=[1, 3]).mask(snap)
        assert set(np.unique(snap.get("matid")[m])) <= {1.0, 3.0}

    def test_label_threshold(self, snap):
        m = rg.label("dens", above=0.1).mask(snap)
        assert np.all(snap.get("dens")[m] >= 0.1)

    def test_layer_partition_is_exact_cover(self, snap):
        n = 5
        masks = [rg.layer(i, n).mask(snap) for i in range(n)]
        total = sum(int(m.sum()) for m in masks)
        assert total == snap.x.size
        # 互不重叠
        acc = np.zeros(snap.x.size, dtype=int)
        for m in masks:
            acc += m.astype(int)
        assert np.all(acc == 1)

    def test_top_fraction_count(self, snap):
        frac = 0.1
        m = rg.top_fraction(frac, by="dens").mask(snap)
        assert m.sum() == max(1, int(round(frac * snap.x.size)))
        # 选中的应是密度最高的一批
        dens = snap.get("dens")
        assert dens[m].min() >= dens[~m].max() - 1e-12

    def test_index_slice(self, snap):
        m = rg.parse_region("index:0:60").mask(snap)
        assert m.sum() == 60
        m2 = rg.parse_region("index:0:60:2").mask(snap)
        assert m2.sum() == 30

    def test_custom_mask(self, snap):
        m = rg.custom(lambda s: np.arange(s.x.size) % 2 == 0).mask(snap)
        assert m.sum() == (snap.x.size + 1) // 2

    def test_custom_mask_wrong_length_raises(self, snap):
        with pytest.raises(rg.RegionError):
            rg.custom(lambda s: np.ones(3, dtype=bool)).mask(snap)

    def test_mass_range_half(self, snap):
        m = rg.mass_range(0.0, 0.5).mask(snap)
        mass = rg.mass_coordinate(snap)
        assert mass[m].sum() / mass.sum() == pytest.approx(0.5, abs=0.02)

    def test_empty_region_raises_with_diagnostics(self, snap):
        spec = rg.x_range(0.5, 1.0)        # 域外
        with pytest.raises(rg.RegionError) as ei:
            spec.mask(snap)
        msg = str(ei.value)
        assert "为空" in msg and "dens" in msg

    def test_label_missing_field_raises(self, snap):
        with pytest.raises(rg.RegionError):
            rg.label("no_such_field", values=[1]).mask(snap)

    def test_dens_required_variables(self):
        s = synthetic_ch_ti_slab(n_time=1, nx=50)
        s[0].fields.pop("dens", None)
        with pytest.raises(rg.RegionError):
            rg.dens_range(0.1, 1.0).mask(s[0])


class TestPresets:
    def test_layered_regions(self):
        rs = rg.resolve_regions(["layer:1/3", "layer:2/3", "layer:3/3"])
        assert [r.params["index"] for r in rs] == [0, 1, 2]

    def test_layered_regions_helper(self):
        from flash.input_gen.gen_flychk_his import layered_regions
        specs = layered_regions(3, names=["a", "b", "c"])
        assert [s.name for s in specs] == ["a", "b", "c"]
        with pytest.raises(rg.RegionError):
            layered_regions(3, names=["a"])

    def test_tracer_regions_helper(self):
        from flash.input_gen.gen_flychk_his import tracer_regions
        specs = tracer_regions("trac", [1, 2], extra=["whole"])
        assert len(specs) == 3
        assert specs[-1].kind == "whole"
