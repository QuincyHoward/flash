"""A5 —— HDF5 双轨模式 + 跨格式转换接口测试。

覆盖 ``writer.h5_schema`` / ``writer.h5_writer`` / ``writer.provenance`` /
``convert``（写出器逆变换）。

关键断言
* 双轨齐全：``native/`` 逐字保留 + ``unified/<gid>/`` 两套
* **往返一致性**：``native`` 数值与源 ``ParsedTable`` 逐点相同（float64 精确）
* ``nion_Te`` 轨的 x 轴确实是 n_ion（≠ rho），且源 x 也做了同样变换
* 逆变换（F2/F3/F1）**再解析回来**必须与原始表一致 —— 这是转换接口的硬指标
"""

import tempfile
from pathlib import Path

import sys
import os
# --- path bootstrap (auto) ---
_d = os.path.dirname(os.path.abspath(__file__))
while _d != os.path.dirname(_d) and not os.path.isfile(
        os.path.join(_d, "_runner.py")):
    _d = os.path.dirname(_d)
if _d not in sys.path:
    sys.path.insert(0, _d)
import _runner  # noqa: F401
from _runner import expect, expect_almost, expect_eq, main

import numpy as np

from eosop_pro import config
from eosop_pro.convert import (convert, get_target, list_targets,
                                 write_h5_single)
from eosop_pro.grid.unified_grid import build_all_grids
from eosop_pro.parsers import hyades_eos as f3
from eosop_pro.parsers import multi_inverted_eos as f1
from eosop_pro.parsers import multi_opacity as f2
from eosop_pro.writer import h5_schema as S
from eosop_pro.writer.h5_writer import write_material_h5


def _tmp():
    return tempfile.TemporaryDirectory()


# ── 转换接口本身 ───────────────────────────────────────────────
def test_targets_registered():
    names = {t.name for t in list_targets()}
    for n in ("cn4", "multi_opacity", "hyades_eos", "multi_inverted_eos",
              "h5"):
        expect(n in names, f"应注册目标 {n}，实测 {names}")
    for t in list_targets():
        expect(t.description, f"{t.name} 应有 description")


def test_can_write_guard_reports_missing_fields():
    t = f2.parse(config.MATTER("mat_Al-1.0/AL_SIMPLE_ROSSELAND"), "x")
    ok, why = get_target("hyades_eos").can_write(t)
    expect(not ok, "Rossland 灰度表缺 P/E → 不应允许写 Hyades")
    expect("缺少场" in why, f"应说明缺什么，实测 {why}")
    ok2, _ = get_target("multi_opacity").can_write(t)
    expect(ok2, "F2 → F2 应允许")


# ── 往返一致性（逆变换的硬指标）────────────────────────────────
def test_roundtrip_multi_opacity():
    src = f2.parse(config.MATTER("mat_Al-1.0/1041_ROSS"), "mat_Al-1.0/1041_ROSS")
    with _tmp() as td:
        out = Path(td) / "rt.op"
        convert(src, out, target="multi_opacity")
        back = f2.parse(out, out.name)
        expect_eq((back.nr, back.nt, back.n_groups), (src.nr, src.nt, src.n_groups))
        a = np.asarray(src.fields["kappa"], dtype=float)
        b = np.asarray(back.fields["kappa"], dtype=float)
        # 源是 log10 存储 → 往返误差应在 1e-6 相对量级内
        expect(np.nanmax(np.abs(a - b)) < 1e-5,
               f"kappa 往返最大偏差 {np.nanmax(np.abs(a - b)):.3e}")


def test_roundtrip_hyades_eos():
    src = f3.parse(config.MATTER("hyades/sesame/eos_41.dat"), "eos_41.dat")
    with _tmp() as td:
        out = Path(td) / "rt.dat"
        convert(src, out, target="hyades_eos",
                zbar=13.0, abar=26.982, rho0=2.7568)
        back = f3.parse(out, out.name)
        expect_eq((back.nr, back.nt), (src.nr, src.nt))
        expect_eq(back.n_numbers_expected >= src.nr + src.nt + 2, True)
        a = np.asarray(src.fields["P"], dtype=float)
        b = np.asarray(back.fields["P"], dtype=float)
        rel = np.nanmax(np.abs(a - b) / np.maximum(np.abs(a), 1e-300))
        expect(rel < 1e-6, f"P 往返相对偏差 {rel:.3e}")


def test_roundtrip_multi_inverted_eos():
    src = f1.parse(config.MATTER("mat_Al-1.0/AL_eos"), "AL_eos")
    with _tmp() as td:
        out = Path(td) / "rt_eos"
        convert(src, out, target="multi_inverted_eos")
        back = f1.parse(out, out.name)
        # F1 的自变量是 (rho, de)，没有 Te 轴 → 用 de 长度比较
        expect_eq((back.nr, len(back.axes["de"])), (src.nr, len(src.axes["de"])))
        a = np.asarray(src.fields["P"], dtype=float)
        b = np.asarray(back.fields["P"], dtype=float)
        rel = np.nanmax(np.abs(a - b) / np.maximum(np.abs(a), 1e-300))
        expect(rel < 1e-6, f"P 往返相对偏差 {rel:.3e}")
        # T 以 Kelvin 写出再读回 eV → 应一致
        at = np.asarray(src.fields["T"], dtype=float)
        bt = np.asarray(back.fields["T"], dtype=float)
        expect(np.nanmax(np.abs(at - bt)) < 1e-3 * max(1.0, float(np.nanmax(at))),
               "T 往返（K↔eV）应一致")


# ── HDF5 双轨 ──────────────────────────────────────────────────
def _sample_tables():
    return [
        f2.parse(config.MATTER("mat_Al-1.0/1041_ROSS"), "mat_Al-1.0/1041_ROSS"),
        f2.parse(config.MATTER("mat_Al-1.0/1041_PLANCK"), "mat_Al-1.0/1041_PLANCK"),
        f1.parse(config.MATTER("mat_Al-1.0/AL_eos"), "mat_Al-1.0/AL_eos"),
    ]


def test_dual_track_structure_and_native_fidelity():
    tables = _sample_tables()
    grids = build_all_grids(tables, A=26.982, n_x=24, n_Te=20)
    with _tmp() as td:
        p = write_material_h5(Path(td) / "Al.h5",
                              material={"material_name": "Aluminium", "material_id": 1041,
                                        "formula": "Al", "Z": 13, "A": 26.982},
                              tables=tables, grids=grids, A=26.982,
                              sources=[{"table_key": "x", "kind": "PLANCK"}],
                              units=[{"quantity": "T", "unit": "eV", "source": "inline"}],
                              warnings=["demo warning"])
        import h5py
        with h5py.File(p, "r") as f:
            expect(str(f.attrs["schema_version"]) == config.SCHEMA_VERSION)
            expect(str(f.attrs["nan_semantics"]) == "out_of_range")
            expect(S.META in f, "应有 /meta")
            for k in ("sources", "units", "warnings", "unified_grids"):
                expect(k in f[S.META], f"/meta 缺 {k}")
            expect(S.TABLES in f, "应有 /tables")
            for tb in tables:
                g = f[f"{S.TABLES}/{tb.table_key}"]
                for a in S.REQUIRED_TABLE_ATTRS:
                    expect(a in g.attrs, f"{tb.table_key} 缺属性 {a}")
                expect(S.NATIVE in g, f"{tb.table_key} 缺 native")
                # native 逐点一致
                for fld in tb.fields:
                    if fld not in g[S.NATIVE]:
                        continue
                    src = np.asarray(tb.fields[fld], dtype=float).reshape(
                        tuple(tb.field_shape[fld]))
                    got = np.asarray(g[f"{S.NATIVE}/{fld}"][()], dtype=float)
                    expect(got.shape == src.shape,
                           f"{tb.table_key}/{fld} shape {got.shape} != {src.shape}")
                    expect(np.array_equal(got, src),
                           f"{tb.table_key}/{fld} native 应逐点一致")


def test_unified_tracks_and_nion_x_axis():
    tables = [f2.parse(config.MATTER("mat_Al-1.0/1041_ROSS"), "mat_Al-1.0/1041_ROSS")]
    A = 26.982
    grids = build_all_grids(tables, A=A, n_x=16, n_Te=12)
    with _tmp() as td:
        p = write_material_h5(Path(td) / "Al.h5", material={"material_name": "Al"},
                              tables=tables, grids=grids, A=A)
        import h5py
        with h5py.File(p, "r") as f:
            base = f"{S.TABLES}/{tables[0].table_key}/{S.UNIFIED}"
            for gid in ("rho_Te", "nion_Te"):
                expect(gid in f[base], f"缺统一轨 {gid}")
            rho_x = np.asarray(f[f"{base}/rho_Te/x"][()], dtype=float)
            nion_x = np.asarray(f[f"{base}/nion_Te/x"][()], dtype=float)
            expect(not np.allclose(rho_x, nion_x), "两套 x 轴必须不同")
            ratio = nion_x / rho_x
            expect(abs(ratio[0] / ratio[-1] - 1.0) < 1e-12,
                   "n_ion / rho 应为常数 N_A/A（纯换算）")
            expect_almost(ratio[0], config.N_A / A, 1e-3)
            ds = f[f"{base}/rho_Te/kappa"]
            expect(str(ds.attrs["units"]) == "cm2/g")
            expect(str(ds.attrs["interp_method"]) == config.INTERP_METHOD)
            expect("out_of_range_count" in ds.attrs)
            expect_almost(float(ds.attrs["coverage"]), 1.0, 1e-9,
                          "目标点在源范围内 → 覆盖率应为 1")


def test_inverted_eos_uses_inversion_track():
    """F1（de 基）表应经反演落盘，并把方法记进属性。"""
    tb = f1.parse(config.MATTER("mat_Al-1.0/AL_eos"), "AL_eos")
    grids = build_all_grids([tb], A=26.982, n_x=16, n_Te=12)
    with _tmp() as td:
        p = write_material_h5(Path(td) / "Al.h5", material={"material_name": "Al"},
                              tables=[tb], grids=grids, A=26.982)
        import h5py
        with h5py.File(p, "r") as f:
            sub = f[f"{S.TABLES}/{tb.table_key}/{S.UNIFIED}/rho_Te"]
            expect("invert" in str(sub.attrs["interp_method"]),
                   f"应标注反演，实测 {sub.attrs['interp_method']}")
            expect("P" in sub, "反演应产出 P")
            expect("T" in sub, "反演应产出 T")


def test_single_table_h5_target():
    tb = f2.parse(config.MATTER("mat_Al-1.0/1041_ROSS"), "x")
    with _tmp() as td:
        p = convert(tb, Path(td) / "one", target="h5")
        expect(Path(p).exists(), f"应写出 h5: {p}")
        expect(str(p).endswith(".h5"), f"应自动补 .h5 后缀，实测 {p}")


def test_chunking_and_compression_on_2d():
    tb = f2.parse(config.MATTER("mat_Al-1.0/1041_ROSS"), "x")
    grids = build_all_grids([tb], A=26.982, n_x=64, n_Te=64)
    with _tmp() as td:
        p = write_material_h5(Path(td) / "a.h5", material={"material_name": "Al"},
                              tables=[tb], grids=grids)
        import h5py
        with h5py.File(p, "r") as f:
            ds = f[f"{S.TABLES}/{tb.table_key}/{S.NATIVE}/kappa"]
            expect(ds.chunks is not None, "2D 数据集应分块")
            expect(ds.compression is not None, "2D 数据集应压缩")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
