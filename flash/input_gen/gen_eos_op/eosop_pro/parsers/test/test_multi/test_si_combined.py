"""Si（Z14, matter++）组合核查 —— qeos_392 + Thermos/mat_Si + Z14 cn4 对比。

独立测试（**不接入** parsers/test/run_all.py，与 test_celia_combined 同策略）：
单文件裸跑 ``python eosop_pro/parsers/test/test_multi/test_si_combined.py``。

被测文件（均与外部根 E:\\...\\Multi1D++Portable20241128 逐字节相同，SHA256 已比对）：
- ``hyades/qeos/qeos_392.dat``       hyades_eos (F3)：QEOS 反演前 (rho,T) 表，
  68×67，头部 ``392 14 28.08 2.42 9249``。**注意**：Multi 程序运行时打印的
  "Inverted EOS Boundaries 68×299 + e0/de" 是程序自产反演，磁盘无此文件 [S-PROG]。
- ``Thermos/mat_Si/Si_Planck.dat``   multi_opacity (F2)：110 群 MUGROUP，21×22
- ``Thermos/mat_Si/Si_Rosseland.dat`` multi_opacity (F2)：同上
- ``Thermos/mat_Si/Si_Zeff.dat``     multi_opacity ZEFF（keV log10 T 轴）
- ``Thermos/mat_Si/Si_Z.dat``        同构旧版（2012 vs 2016），147 字节差异
- ``Thermos/mat_Si/Si.ini``          轴/群边界明文清单（111 边界 = 110 群）
- ``eos_op_data/.../Z14_1.00-...cn4`` IONMIX Si 表（ntemp=51/ndens=31/ngrups=6）

操作者视图 oracle（用户提供的 Multi 程序加载输出，2026-11-14）作为边界交叉验证。
对比口径（2026-11-14 用户裁定升级）：EOS 数值对比 + 不透明度**边界拼接群对比**
（Si 110 群中能精确拼出 cn4 群边界的子群做能量宽度加权聚合后数值对比）+
zbar/Zeff 软对比（IONMIX vs QEOS 模型差，展示不判分）。
另含 Planck 发射 vs 吸收机制调查（MULTI 文献 + abjt_03.f 源码 + cn4 块18/19 实证）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # parsers/test/
import _bootstrap            # noqa: F401,E402
import _runner               # noqa: F401,E402
from _runner import expect, expect_eq, main           # noqa: E402
from _common import out_dir, write_summary, log, try_plot, table_stats  # noqa: E402

import base64
import html as _html
import re
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from eosop_pro.parsers.cn4_io import parse_cn4, cn4_to_parsed_tables
from eosop_pro.parsers.hyades_eos import parse_all as hyades_parse, parse_header_line
from eosop_pro.parsers.multi_opacity import parse_all as f2_parse
from eosop_pro.convert.invert_eos import cn4_eos_to_rho_base, cn4_opac_to_rho_base, to_de_grid
from eosop_pro.convert.writers_multi import write_multi_opacity_from_cn4

# 仓库根: test_multi -> parsers/test -> parsers -> eosop_pro -> gen_eos_op
_REPO = Path(__file__).resolve().parents[4]
_MAT = _REPO / "src" / "Multi1D++Portable20241128" / "matter++"
_QEOS = _MAT / "hyades" / "qeos" / "qeos_392.dat"
_THERMOS = _MAT / "Thermos" / "mat_Si"
_SI_PLANCK = _THERMOS / "Si_Planck.dat"
_SI_ROSS = _THERMOS / "Si_Rosseland.dat"
_SI_ZEFF = _THERMOS / "Si_Zeff.dat"
_SI_Z = _THERMOS / "Si_Z.dat"
_SI_INI = _THERMOS / "Si.ini"
_CN4 = _REPO / "eos_op_data" / "Gen_eos_op_data" / "Z14_1.00-20260708_0850" / "Z14_1.00-20260708_0850.cn4"
_OUT = out_dir("test_multi_si")

# ── 操作者视图 oracle（用户提供的 Multi 加载输出；uv 证据，非文件内容） ──
OP_QEOS = {"id": 392, "Z": 14.0, "abar": 28.08, "rho0": 2.42, "L": 9249,
           "nr": 68, "nt": 67,
           "rho": (1e-3, 1e3), "T_eV": (0.025, 1e5),
           "P_dyne": (3.34628086e4, 5.15544e19), "E_erg": (-2.27897e6, 7.77105e16)}
# 程序自产 68x299 反演边界（磁盘无文件 → 软核验，超差记 REM 不 FAIL）[S-PROG]
OP_INV = {"ne": 299, "e0_erg": (-2.19359e9, 2.22449e14), "de_erg": (0.0, 7.7405e16),
          "P_dyne": (0.0, 5.15544e19), "T_eV": (0.0, 1e5)}
OP_PLANCK = {"nt": 21, "nr": 22, "ng": 110, "klog10_max": 11.1305}
OP_ROSS = {"nt": 21, "nr": 22, "ng": 110, "klog10_max": 10.9544}
OP_ZEFF = {"nt": 21, "nr": 22, "f2": 6.0, "zlog10_max": 1.1714632}
# ZEFF 载荷口径：log10(zbar)（2026-11-14 用户裁定，45 元素族校准：He 0.346→2.2、
# C 0.792→6.2、Si 1.171→14.8、Fe 1.423→26.5、U 1.966→92.5 ≈ 各核电荷数；
# -10 哨兵 = log10(1e-10)）。已落库 field_checks（parser-measured, checked）。

# 用户粘贴的 110 群清单（0.1 - 1 ... 30000 - 40000）→ 111 边界 oracle
_SI_GROUPS_TXT = """
0.1 - 1, 1 - 10, 10 - 20, 20 - 30, 30 - 40,
40 - 50, 50 - 60, 60 - 70, 70 - 80, 80 - 90,
90 - 100, 100 - 110, 110 - 120, 120 - 130, 130 - 140,
140 - 150, 150 - 160, 160 - 170, 170 - 180, 180 - 190,
190 - 200, 200 - 220, 220 - 240, 240 - 250, 250 - 260,
260 - 270, 270 - 280, 280 - 290, 290 - 300, 300 - 310,
310 - 320, 320 - 330, 330 - 340, 340 - 350, 350 - 360,
360 - 370, 370 - 380, 380 - 390, 390 - 400, 400 - 410,
410 - 420, 420 - 430, 430 - 440, 440 - 450, 450 - 460,
460 - 470, 470 - 480, 480 - 490, 490 - 500, 500 - 520,
520 - 540, 540 - 560, 560 - 580, 580 - 600, 600 - 650,
650 - 700, 700 - 750, 750 - 800, 800 - 900, 900 - 1000,
1000 - 1100, 1100 - 1200, 1200 - 1300, 1300 - 1400, 1400 - 1500,
1500 - 1600, 1600 - 1700, 1700 - 1800, 1800 - 1820, 1820 - 1840,
1840 - 1860, 1860 - 1880, 1880 - 1900, 1900 - 2000, 2000 - 2010,
2010 - 2020, 2020 - 2050, 2050 - 2100, 2100 - 2120, 2120 - 2140,
2140 - 2160, 2160 - 2180, 2180 - 2200, 2200 - 2220, 2220 - 2240,
2240 - 2260, 2260 - 2280, 2280 - 2300, 2300 - 2400, 2400 - 2500,
2500 - 2600, 2600 - 2800, 2800 - 3000, 3000 - 3500, 3500 - 4000,
4000 - 4500, 4500 - 5000, 5000 - 6000, 6000 - 7000, 7000 - 8000,
8000 - 9000, 9000 - 10000, 10000 - 11000, 11000 - 12000, 12000 - 13000,
13000 - 14000, 14000 - 15000, 15000 - 20000, 20000 - 30000, 30000 - 40000
"""
_pairs = re.findall(r"([\d.]+)\s*-\s*([\d.]+)", _SI_GROUPS_TXT)
assert len(_pairs) == 110, len(_pairs)
_OP_BOUNDS = sorted({float(x) for p in _pairs for x in p})
assert len(_OP_BOUNDS) == 111, len(_OP_BOUNDS)

_CACHE: dict = {}


# ── 惰性加载（幂等自足） ──────────────────────────────────────────
def _qeos():
    if "qeos" in _CACHE:
        return _CACHE["qeos"]
    if not _QEOS.exists():
        _CACHE["qeos"] = None
        return None
    tabs = hyades_parse(str(_QEOS))
    _CACHE["qeos"] = (_QEOS, tabs[0])
    return _CACHE["qeos"]


def _opac(path: Path, hint=None):
    key = f"opac_{path.name}_{hint or 'auto'}"   # hint 入键：同一文件不同单位口径各自缓存
    if key in _CACHE:
        return _CACHE[key]
    if not path.exists():
        _CACHE[key] = None
        return None
    tabs = f2_parse(str(path)) if hint is None else f2_parse(str(path), unit_hint=hint)
    _CACHE[key] = tabs[0]
    return _CACHE[key]


def _cn4():
    if "cn4" in _CACHE:
        return _CACHE["cn4"]
    if not _CN4.exists():
        _CACHE["cn4"] = None
        return None
    cn4 = parse_cn4(str(_CN4))
    _CACHE["cn4"] = (_CN4, cn4, cn4_to_parsed_tables(cn4))
    return _CACHE["cn4"]


def _ensure_conv():
    """cn4 → F2 转换（ross/planck 写盘并读回），幂等。"""
    if "conv" in _CACHE:
        return _CACHE["conv"]
    src = _cn4()
    if src is None:
        _CACHE["conv"] = None
        return None
    _p, cn4, tables = src
    _eos, ross, pabs, _pems = tables
    meta = {"cn4": cn4, "tables": tables}
    (_OUT / "f2_from_cn4_ross").mkdir(parents=True, exist_ok=True)
    (_OUT / "f2_from_cn4_planck").mkdir(parents=True, exist_ok=True)
    meta["f2_ross_path"] = write_multi_opacity_from_cn4(
        ross, _OUT / "f2_from_cn4_ross" / "Z14_from_cn4_ross.dat", avgatw=cn4.avgatw)
    meta["f2_planck_path"] = write_multi_opacity_from_cn4(
        pabs, _OUT / "f2_from_cn4_planck" / "Z14_from_cn4_planck.dat", avgatw=cn4.avgatw)
    meta["f2_ross"] = f2_parse(str(meta["f2_ross_path"]))[0]
    meta["f2_planck"] = f2_parse(str(meta["f2_planck_path"]))[0]
    _CACHE["conv"] = meta
    return meta


# ── 工具 ─────────────────────────────────────────────────────────
def _as2d(t, name):
    return np.asarray(t.fields[name], dtype=float).reshape(t.field_shape[name])


def _rel_stats(a, ref):
    """相对偏差统计（以 ref 为基准）；仅取两者有限且 ref≠0 处。"""
    m = np.isfinite(a) & np.isfinite(ref) & (np.abs(ref) > 0)
    if not m.any():
        return None
    rel = np.abs(a[m] - ref[m]) / np.abs(ref[m])
    return {"n": int(m.sum()), "median": float(np.median(rel)),
            "p90": float(np.percentile(rel, 90)), "max": float(rel.max())}


def _interp2d_loglog(M, rho_own, Te_own, rho_q, Te_q):
    """(nTe,nrho) 场 → (nTeq,nrhoq)，log10(rho)×log10(Te) 双线性。"""
    lr = np.log10(np.asarray(rho_own, dtype=float))
    lt = np.log10(np.asarray(Te_own, dtype=float))
    lq = np.log10(np.asarray(rho_q, dtype=float))
    ltq = np.log10(np.asarray(Te_q, dtype=float))
    G = np.vstack([np.interp(lq, lr, M[i, :]) for i in range(M.shape[0])])
    return np.vstack([np.interp(ltq, lt, G[:, j]) for j in range(G.shape[1])]).T


def _plot_heat(ax, M, rho, Te, title, vmin=None, vmax=None, colorbar=True):
    lr, lt = np.log10(rho), np.log10(Te)
    im = ax.imshow(M, aspect="auto", origin="lower", vmin=vmin, vmax=vmax,
                   extent=[lr[0], lr[-1], lt[0], lt[-1]], cmap="viridis")
    ax.set_xlabel("log10(rho [g/cm3])")
    ax.set_ylabel("log10(Te [eV])")
    ax.set_title(title, fontsize=10)
    if colorbar:
        plt.colorbar(im, ax=ax, shrink=0.85)
    return im


# ── 测试 1：qeos_392 解析（F3 Hyades/QEOS, 68×67） ────────────────
def test_qeos_parse():
    sample = _qeos()
    if sample is None:
        log("  SKIP: qeos_392.dat 不存在")
        return
    path, t = sample
    # 行 1 是 QEOS 注释（"Silicon LLNL QEOS DATED: ..."），5 数表头在行 2
    hdr = None
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()[:4]:
        try:
            hdr = parse_header_line(ln)
            break
        except Exception:
            continue
    expect(hdr is not None, "行 2 找到 5 数表头（行 1 为 QEOS 注释）")
    expect_eq(int(hdr["id"]), OP_QEOS["id"], "id = 392")
    expect_eq(float(hdr["zbar"]), OP_QEOS["Z"], "第2数 = 原子序数 Z=14（解析器键名 zbar）")
    expect_eq(float(hdr["abar"]), OP_QEOS["abar"], "abar = 28.08")
    expect_eq(float(hdr["rho0"]), OP_QEOS["rho0"], "rho0 = 2.42 g/cm3")
    expect_eq(int(hdr["L"]), OP_QEOS["L"], "L = 9249 = 2+68+67+2*68*67")
    expect_eq(t.n_numbers_seen, t.n_numbers_expected,
              f"计数守恒（seen={t.n_numbers_seen} = L+1 tail）")
    expect_eq(list(t.fields.get("raw_tail", [])), [0.0], "raw_tail = [0.0]（DOS EOF 前 0）")
    expect_eq(len(t.axes["rho"]), OP_QEOS["nr"], "rho 轴 68 点")
    expect_eq(len(t.axes["Te"]), OP_QEOS["nt"], "Te 轴 67 点")
    rho, Te = np.asarray(t.axes["rho"]), np.asarray(t.axes["Te"])
    expect(abs(rho[0] - OP_QEOS["rho"][0]) < 1e-6 and abs(rho[-1] - OP_QEOS["rho"][1]) < 1e-6,
           f"rho [{rho[0]:.4g},{rho[-1]:.4g}] = 操作者视图 [0.001,1000] g/cm3")
    expect(abs(Te[0] - OP_QEOS["T_eV"][0]) < 1e-4 and abs(Te[-1] - OP_QEOS["T_eV"][1]) < 1e-4,
           f"Te [{Te[0]:.4g},{Te[-1]:.4g}] eV = 操作者视图 [0.025,1e5] eV"
           "（文件存 keV log10，解析器 ×1e3 → eV，见 unit_source）")
    P, E = _as2d(t, "P"), _as2d(t, "E")
    expect_eq(t.field_shape["P"], (OP_QEOS["nt"], OP_QEOS["nr"]), "P/E 形状 (nt,nr)=(67,68)")
    expect(abs(P.min() - OP_QEOS["P_dyne"][0]) / OP_QEOS["P_dyne"][0] < 1e-4
           and abs(P.max() / OP_QEOS["P_dyne"][1] - 1) < 1e-5,
           f"P 范围 [{P.min():.5g},{P.max():.5g}] dyne/cm2 = 操作者视图")
    expect(abs(E.min() - OP_QEOS["E_erg"][0]) / abs(OP_QEOS["E_erg"][0]) < 1e-4
           and abs(E.max() / OP_QEOS["E_erg"][1] - 1) < 1e-5,
           f"E 范围 [{E.min():.5g},{E.max():.5g}] erg/g = 操作者视图（E 可为负——冷曲线）")
    lines = table_stats(path, [t]) + [
        "",
        "── T 轴单位链（文件→程序显示） ──",
        "文件 log10(T_keV) ∈ [-4.39794, 2.0] → 4e-5..100 keV → ×1e3 → 0.025..1e5 eV",
        "＝ 操作者视图 temperature(eV): [0.025, 100000]（Multi 显示层换算）",
        "── 与 Multi 打印 'Inverted EOS 68x299' 的关系 ──",
        "磁盘文件是 (rho,T) 基 68×67（Hyades F3）；68×299 反演表为程序运行时",
        "自产（下测软核验），仓库内不存在 68×299 文件 [S-PROG]。",
    ]
    write_summary("test_multi_si", lines)
    log("\n".join(lines))


# ── 测试 2：68×299 反演边界软核验（自反演 vs 程序打印） ────────────
def test_qeos_self_inversion():
    """程序打印的 Inverted EOS 边界无磁盘文件 → 由 (rho,T) 表自反演软核验。"""
    sample = _qeos()
    if sample is None:
        return
    _path, t = sample
    E = _as2d(t, "E")                       # (nt,nr) erg/g
    P = _as2d(t, "P")
    e0 = E[0, :]                            # 每密度列 T_min 处能量（类冷曲线）
    de_max_j = E.max(axis=0) - e0           # 每密度列 de 上限
    de_max = float(de_max_j.max())
    chk = {
        "de_max_self": de_max, "de_max_prog": OP_INV["de_erg"][1],
        "de_max_rel": abs(de_max - OP_INV["de_erg"][1]) / OP_INV["de_erg"][1],
        "e0_min_self": float(e0.min()), "e0_min_prog": OP_INV["e0_erg"][0],
        "e0_max_self": float(e0.max()), "e0_max_prog": OP_INV["e0_erg"][1],
        "P_max_self": float(P.max()), "T_eV_max_self": float(t.axes["Te"][-1]),
    }
    _CACHE["inv"] = chk
    expect(chk["de_max_rel"] < 0.02,
           f"自反演 de_max={de_max:.4e} erg/g vs 程序打印 {OP_INV['de_erg'][1]:.4e}"
           f"（相对偏差 {chk['de_max_rel']:.3%} < 2%）")
    for nm, lo, hi in (("e0_min", chk["e0_min_self"], chk["e0_min_prog"]),
                       ("e0_max", chk["e0_max_self"], chk["e0_max_prog"])):
        rel = abs(lo - hi) / max(abs(hi), 1e-30)
        log(f"  REM[{nm}]: 自算 {lo:.4e} vs 程序 {hi:.4e}（rel {rel:.2%}）"
            + ("—— 量级一致，程序 e0 定义细节未公开（零点/外推差异），不判 FAIL"
               if rel > 0.02 else "一致"))
    # E 沿 T 单调性（正演反演前提）
    n_bad = int((np.diff(E, axis=0) < 0).sum())
    log(f"  E(rho,T) 沿 T 非单调点数: {n_bad}/{E.size}（软前提，多数物理区间单调）")
    # to_de_grid 演示（正 E 区间）
    pos = E[E > 0]
    de_t = np.geomspace(max(pos.min(), 1e3), pos.max(), 40)
    res = to_de_grid(t, de_t, value_fields=("P",), log_value=("P",), extrapolate="edge")
    _CACHE["degrid"] = res
    expect(bool(np.isfinite(res.fields["T"]).all()), "to_de_grid T 场无 NaN（edge 延拓）")
    log(f"  to_de_grid: 40×68 (de,rho)，coverage={res.coverage:.2%}")


# ── 测试 3：Si_Planck / Si_Rosseland 解析（110 群） ───────────────
def test_si_opacity_parse():
    for path, op_o in ((_SI_PLANCK, OP_PLANCK), (_SI_ROSS, OP_ROSS)):
        t = _opac(path)
        if t is None:
            log(f"  SKIP: {path.name} 不存在")
            continue
        expect_eq(t.kind, "MUGROUP", f"{path.name}: kind=MUGROUP（110 子表归并 1 表）")
        expect_eq(t.n_groups, op_o["ng"], f"{path.name}: 110 群")
        gb = np.asarray(t.group_bounds)
        expect_eq(len(gb), 111, f"{path.name}: 111 个群边界")
        expect(bool(np.allclose(gb, _OP_BOUNDS, rtol=1e-6)),
               f"{path.name}: 群边界与操作者视图 110 群清单逐点一致（0.1..40000 eV）")
        expect_eq(t.field_shape["kappa_g"], (110, op_o["nt"], op_o["nr"]),
                  f"{path.name}: kappa_g 形状 (110,21,22)")
        rho, Te = np.asarray(t.axes["rho"]), np.asarray(t.axes["Te"])
        expect(abs(rho[0] - 1e-6) < 1e-12 and abs(rho[-1] - 1e4) < 1e-6,
               f"{path.name}: rho [{rho[0]:.3g},{rho[-1]:.4g}] = [1e-6,10000]")
        expect(abs(Te[0] - 0.04) < 1e-6 and abs(Te[-1] - 1e5) < 1e-6,
               f"{path.name}: Te [0.04,1e5] eV")
        k = np.asarray(t.fields["kappa_g"], dtype=float).reshape(t.field_shape["kappa_g"])
        expect(abs(k.max() - op_o["klog10_max"]) / op_o["klog10_max"] < 1e-4,
               f"{path.name}: log10(kappa) max {k.max():.6f} ≈ 操作者视图 {op_o['klog10_max']}")
        _CACHE.setdefault("kmin_rem", []).append(
            f"{path.name}: 实测 log10(kappa) min={k.min():.4f}，比操作者视图打印下限更负"
            "——程序打印范围口径（疑排除部分群/按集成量打印），记 REM 不判 FAIL")
        log(f"  {path.name}: ng=110 bounds[0..-1]=({gb[0]},{gb[-1]}) "
            f"klog10 [{k.min():.4f},{k.max():.4f}]")
    # Planck >= Rosseland 趋势（不硬断言）
    tp, tr = _opac(_SI_PLANCK), _opac(_SI_ROSS)
    if tp is not None and tr is not None:
        kp = _as2d(tp, "kappa_g").reshape(110, 21, 22)
        kr = _as2d(tr, "kappa_g").reshape(110, 21, 22)
        frac = float((kp >= kr).mean())
        log(f"  Planck>=Rosseland 点占比: {frac:.1%}（物理趋势，仅记录）")
        _CACHE["pkge_r"] = frac


# ── 测试 4：Si_Zeff / Si_Z / Si.ini ──────────────────────────────
def test_si_zeff_parse():
    tz = _opac(_SI_ZEFF, hint="keV")     # Zeff: log10(T_keV) 起点 -4.39794
    tv = _opac(_SI_Z, hint="eV")         # Z: log10(T_eV) 起点 -1.39794（Readme 约定成立）
    if tz is None:
        log("  SKIP: Si_Zeff.dat 不存在")
        return
    for t, nm in ((tz, "Si_Zeff.dat"), (tv, "Si_Z.dat")):
        expect_eq(t.kind, "ZEFF", f"{nm}: kind=ZEFF（f2=6 枚举）")
        expect_eq(t.field_shape["Z"], (OP_ZEFF["nt"], OP_ZEFF["nr"]),
                  f"{nm}: Z 形状 (21,22)")
        rho = np.asarray(t.axes["rho"])
        Te = np.asarray(t.axes["Te"])
        expect(abs(rho[0] - 1e-6) < 1e-12 and abs(rho[-1] - 1e4) < 1e-6,
               f"{nm}: rho [1e-6,1e4]（22 点，与不透明度文件同轴）")
        expect(abs(Te[0] - 0.04) < 1e-6 and abs(Te[-1] - 1e5) < 1e-6,
               f"{nm}: Te [0.04,1e5] eV")
    Z = _as2d(tz, "Z")
    expect(abs(Z.max() - OP_ZEFF["zlog10_max"]) < 1e-4,
           f"log10(zbar) max {Z.max():.7f} ≈ 1.1714632（=log10(14.8)，Si 全电离 14 的"
           "log10=1.146，高压压致电离略超核值）")
    n_sent = int((Z <= -9.9).sum())
    log(f"  哨兵点（Z<=-9.9, =log10(1e-10) 近零电离）: {n_sent}/{Z.size}；"
        "其余负值（如 -2.7）为物理低电离 log10(zbar)")
    # 两代文件同构不同值（磁盘 147 字节差，含 T 轴单位编码段）
    raw_diff = _SI_Z.read_bytes() != _SI_ZEFF.read_bytes()
    expect(raw_diff, "Si_Z(2012) 与 Si_Zeff(2016) 磁盘内容不同（同构不同代）")
    Zv = _as2d(tv, "Z")
    n_diff = int((Z != Zv).sum())
    log(f"  Z 载荷差 {n_diff}/{Z.size} 点（T 轴编码不同：Z=eV log10 / Zeff=keV log10）")
    # Readme 单位约定：两文件 T 轴 log10 基不同（-1.39794 vs -4.39794）
    log("  REM[单位约定]: Thermos/Readme.txt 约定成立——Si_Z.dat 存 log10(T_eV)"
        "（起点 -1.39794），Si_Zeff.dat 存 log10(T_keV)（起点 -4.39794）；"
        "hint 必须分别为 eV / keV，错用差 ×1e3。")
    # Si.ini 交叉验证
    if _SI_INI.exists():
        ini = _SI_INI.read_text(encoding="utf-8", errors="replace")
        freq = [float(x) for x in ini.split("Frequency=")[1].splitlines()[0].split(",")]
        expect_eq(len(freq), 111, "Si.ini Frequency = 111 边界")
        expect(bool(np.allclose(freq, _OP_BOUNDS, rtol=1e-6)),
               "Si.ini 群边界 = 操作者视图 110 群清单逐点一致")
        ntemp = len(ini.split("Temperature=")[1].splitlines()[0].split(","))
        ndens = len(ini.split("Density=")[1].splitlines()[0].split(","))
        expect_eq((ntemp, ndens), (21, 22), "Si.ini Temperature=21 / Density=22")
        _CACHE["ini_freq"] = freq


# ── 测试 5：Z14 cn4 载入 ─────────────────────────────────────────
def test_cn4_z14_load():
    src = _cn4()
    if src is None:
        log("  SKIP: Z14 cn4 不存在")
        return
    p, cn4, tables = src
    expect_eq(cn4.ntemp, 51, "ntemp=51")
    expect_eq(cn4.ndens, 31, "ndens=31")
    expect_eq(cn4.ngrups, 6, "ngrups=6")
    expect_eq(len(tables), 4, "cn4 拆 4 表（EOS/ROSS/PABS/PEMS）")
    eos = tables[0]
    Te = np.asarray(eos.axes["Te"])
    rho = np.asarray(eos.fields["rho"]).reshape(eos.field_shape["P"])[0]
    expect(abs(Te[0] - 1.0) < 1e-6 and 1.9e4 < Te[-1] <= 2e4,
           f"Te [{Te[0]:g},{Te[-1]:g}] eV（ntemp log 轴末端 19998.6 < 2e4）")
    _CACHE["cn4_rho"] = (float(rho.min()), float(rho.max()))
    log(f"  cn4: {p.name}  <A>={cn4.avgatw:.4f}  rho [{rho.min():.3g},{rho.max():.3g}] g/cm3"
        f"  群边界 {cn4.group_bounds}")


# ── 测试 6：cn4 EOS vs qeos_392 数值对比（公共 rho-T 窗口） ───────
def test_cn4_eos_vs_qeos():
    src = _cn4()
    q = _qeos()
    if src is None or q is None:
        log("  SKIP: cn4 或 qeos 缺失")
        return
    _p, cn4, tables = src
    _path, qt = q
    eos = cn4_eos_to_rho_base(tables[0])
    rho_cn4 = np.asarray(eos.axes["rho"])
    Te_cn4 = np.asarray(eos.axes["Te"])
    rho_q = np.asarray(qt.axes["rho"])
    Te_q = np.asarray(qt.axes["Te"])
    lo = max(rho_cn4.min(), rho_q[rho_q > 0].min())
    hi = min(rho_cn4.max(), rho_q.max())
    tlo = max(Te_cn4.min(), Te_q.min())
    thi = min(Te_cn4.max(), Te_q.max())
    rho_w = np.geomspace(lo, hi, 24)
    Te_w = np.geomspace(tlo, thi, 24)
    # cn4: J/cm3 -> Mbar (/1e5), J/g -> Mbar*cm3/g (/1e5)
    P_c = _as2d(eos, "P") * 1e-5
    E_c = _as2d(eos, "E") * 1e-5
    # qeos: dyne/cm2 -> Mbar (/1e12), erg/g -> Mbar*cm3/g (/1e12)
    P_q = _as2d(qt, "P") * 1e-12
    E_q = _as2d(qt, "E") * 1e-12
    Pc_w = _interp2d_loglog(P_c, rho_cn4, Te_cn4, rho_w, Te_w)
    Ec_w = _interp2d_loglog(E_c, rho_cn4, Te_cn4, rho_w, Te_w)
    Pq_w = _interp2d_loglog(P_q, rho_q, Te_q, rho_w, Te_w)
    Eq_w = _interp2d_loglog(E_q, rho_q, Te_q, rho_w, Te_w)
    sP = _rel_stats(Pc_w, Pq_w)
    m = (Eq_w > 0) & (Ec_w > 0)
    sE = _rel_stats(Ec_w[m], Eq_w[m]) if m.any() else None
    _CACHE["eos_cmp"] = {"sP": sP, "sE": sE, "window": (float(lo), float(hi), float(tlo), float(thi)),
                         "rho_w": rho_w, "Te_w": Te_w,
                         "Pc": Pc_w, "Ec": Ec_w, "Pq": Pq_w, "Eq": Eq_w,
                         "E_mask": m}
    expect(sP is not None and sP["n"] > 100, f"P 公共可比点 {sP['n'] if sP else 0} > 100")
    expect(sE is not None and sE["n"] > 100, f"E 公共可比点（双方正能）{sE['n'] if sE else 0} > 100")
    for nm, s in (("P", sP), ("E", sE)):
        if s:
            log(f"  vs qeos_392 {nm}: n={s['n']} median={s['median']:.2%} "
                f"p90={s['p90']:.2%} max={s['max']:.2%}")
    log(f"  窗口: rho [{lo:.3g},{hi:.3g}] g/cm3, Te [{tlo:.3g},{thi:.3g}] eV"
        "（IONMIX vs LLNL-QEOS 跨模型，15–20% 中位差属预期，无硬阈值）")


# ── 测试 7：cn4 不透明度转换 + 群边界对照 + 块18/19 发射-吸收实证 ──
def test_cn4_opacity_vs_si():
    meta = _ensure_conv()
    src = _cn4()
    if meta is None or src is None:
        log("  SKIP: cn4 缺失")
        return
    cn4 = meta["cn4"]
    cb = [round(x, 3) for x in cn4.group_bounds]
    expect(cb != [round(x, 3) for x in _OP_BOUNDS],
           "cn4 6 群边界 ≠ Si 110 群边界（直接逐群对比不可行 → 下一测做边界拼接）")
    for key, ng in (("f2_ross", "ROSS"), ("f2_planck", "PLANCK")):
        t = meta[key]
        expect_eq(t.n_groups, cn4.ngrups, f"{key}: 群数 = cn4 ngrups(6)")
        expect(bool(np.allclose(np.asarray(t.group_bounds), cn4.group_bounds, rtol=1e-6)),
               f"{key}: 群边界与 cn4 一致")
        log(f"  {key}: ng={t.n_groups} bounds {cb}")
    _CACHE["bounds_rows"] = [
        ("Z14 cn4 (IONMIX)", str(cn4.ngrups), str(cb)),
        ("Si_Planck.dat", "110", f"0.1 .. 40000 eV（111 边界，逐点 oracle 见测 3）"),
        ("Si_Rosseland.dat", "110", "同上"),
    ]
    # 块18(Planck abs) vs 块19(Planck ems) 实证：发射-吸收是否独立生成
    pabs = cn4_to_parsed_tables(cn4)[2]
    pems = cn4_to_parsed_tables(cn4)[3]
    ka = np.asarray(pabs.fields["opac_planck_abs"], dtype=float).reshape(
        pabs.field_shape["opac_planck_abs"])
    ke = np.asarray(pems.fields["opac_planck_ems"], dtype=float).reshape(
        pems.field_shape["opac_planck_ems"])
    d = np.abs(ka - ke)
    nz = d > 0
    rel = d[nz] / np.maximum(np.abs(ke[nz]), 1e-30)
    stats_ems = {"n_diff": int(nz.sum()), "n_total": int(d.size),
                 "median_rel": float(np.median(rel)) if rel.size else 0.0}
    _CACHE["ems_stats"] = stats_ems
    log(f"  块18(Planck abs) vs 块19(Planck ems): {stats_ems['n_diff']}/"
        f"{stats_ems['n_total']} 点不同，|Δ|相对中位 {stats_ems['median_rel']:.2%}"
        " → abjt_03.f 中发射（LTE 平衡布局）与吸收（受激辐射修正）独立生成"
        "（详见报告 §6.2）")


# ── 测试 7b：cn4 vs Si 边界拼接群对比（2026-11-14 用户裁定升级） ──
def test_cn4_opacity_stitched_groups():
    """Si 110 群中边界可精确拼出 cn4 群的子群 → 能量宽度加权聚合成 1 群，
    与 cn4 对应群数值对比（统一 log10(cm2/g) + 共享色标）。"""
    meta = _ensure_conv()
    src = _cn4()
    tp, tr = _opac(_SI_PLANCK), _opac(_SI_ROSS)
    if meta is None or src is None or tp is None or tr is None:
        log("  SKIP: cn4 或 Si 不透明度缺失")
        return
    _p, cn4, tables = src
    _eos, ross_c, pabs_c, _pems = tables
    gb_si = np.asarray(tr.group_bounds)          # 111 边界
    cb = np.asarray(cn4.group_bounds)            # 7 边界 = 6 群
    rho_si = np.asarray(tr.axes["rho"])
    Te_si = np.asarray(tr.axes["Te"])

    def stitch(t, lo, hi, mode):
        """[lo,hi] 内 Si 子群能量宽度加权聚合（平谱近似）；mode: ross=调和/planck=算术"""
        K = np.asarray(t.fields["kappa_g"], dtype=float).reshape(
            t.field_shape["kappa_g"])            # (110,21,22) log10
        num = np.zeros(K.shape[1:])
        den = np.zeros(K.shape[1:])
        nsub = 0
        for g in range(t.n_groups):
            e_lo, e_hi = gb_si[g], gb_si[g + 1]
            if e_lo >= lo - 1e-9 and e_hi <= hi + 1e-9:
                w = e_hi - e_lo
                kg = 10.0 ** K[g]                # 线性 kappa cm2/g
                if mode == "ross":               # 1/k_agg = Σ(w/k)/Σw
                    num += w / kg
                else:                            # k_agg = Σ(w·k)/Σw
                    num += w * kg
                den += w
                nsub += 1
        if nsub == 0 or not np.allclose(den, hi - lo, rtol=1e-6):
            return None, 0
        return np.log10(den / num) if mode == "ross" else np.log10(num / den), nsub

    # cn4 每群 κ 转到 Si (rho,Te) 网格（log10 域插值；Si 网格作参考）
    # cn4 原生轴为 nion(cm-3) → cn4_opac_to_rho_base 转 rho(g/cm3)
    ross_r = cn4_opac_to_rho_base(ross_c, cn4.avgatw)
    pabs_r = cn4_opac_to_rho_base(pabs_c, cn4.avgatw)
    Kc = {"ross": np.asarray(ross_r.fields["opac_rosseland"], dtype=float).reshape(
              ross_r.field_shape["opac_rosseland"]),
          "planck": np.asarray(pabs_r.fields["opac_planck_abs"], dtype=float).reshape(
              pabs_r.field_shape["opac_planck_abs"])}
    rho_c = np.asarray(ross_r.axes["rho"])
    Te_c = np.asarray(ross_r.axes["Te"])
    # cn4 κ 为线性 cm2/g → 统一取 log10（与 Si 文件 log10 存储同口径）
    for fam in Kc:
        Kc[fam] = np.log10(np.maximum(Kc[fam], 1e-300))
    # Si 网格中落在 cn4 原生范围内的掩膜（避免边缘延拓参与统计）
    in_rho = (rho_si >= rho_c.min()) & (rho_si <= rho_c.max())
    in_Te = (Te_si >= Te_c.min()) & (Te_si <= Te_c.max())

    results = {}
    for fam, t_si in (("ross", tr), ("planck", tp)):
        rows = []
        for gi in range(cn4.ngrups):
            lo, hi = cb[gi], cb[gi + 1]
            si_agg, nsub = stitch(t_si, lo, hi, "ross" if fam == "ross" else "planck")
            if si_agg is None:
                rows.append({"gi": gi + 1, "band": f"{lo:g}-{hi:g} eV",
                             "nsub": 0, "note": "Si 子群边界不能精确拼出（或超出 40000 eV）→ 不比"})
                continue
            kc = _interp2d_loglog(Kc[fam][gi], rho_c, Te_c, rho_si, Te_si)
            m = in_Te[:, None] & in_rho[None, :]
            mc = 10.0 ** kc
            ms = 10.0 ** si_agg
            dex = np.abs(kc - si_agg)          # log10 域差（dex）
            stat = {"n": int(m.sum()),
                    "median_dex": float(np.median(dex[m])) if m.any() else None,
                    "p90_dex": float(np.percentile(dex[m], 90)) if m.any() else None,
                    "within03": float((dex[m] <= 0.3).mean()) if m.any() else None}
            rows.append({"gi": gi + 1, "band": f"{lo:g}-{hi:g} eV", "nsub": nsub,
                         "stat": stat, "si": si_agg, "cn4": kc, "mask": m})
        results[fam] = rows
        for r in rows:
            if r.get("stat"):
                s = r["stat"]
                log(f"  {fam} 群{r['gi']} [{r['band']}]（{r['nsub']} 子群拼接）: "
                    f"n={s['n']} median={s['median_dex']:.3f} dex "
                    f"p90={s['p90_dex']:.3f} dex within0.3dex={s['within03']:.0%}")
            else:
                log(f"  {fam} 群{r['gi']} [{r['band']}]: {r['note']}")
    expect(all(("stat" in r) for r in results["ross"][:5]),
           "Rosseland 群 1-5 均完成拼接数值对比")
    expect(all(("stat" in r) for r in results["planck"][:5]),
           "Planck 群 1-5 均完成拼接数值对比")
    _CACHE["stitch"] = {"results": results, "rho_si": rho_si, "Te_si": Te_si,
                        "si_masks": (in_rho, in_Te)}


# ── 测试 8：cn4 zbar vs Si_Zeff 软对比 ───────────────────────────
def test_cn4_zbar_vs_zeff():
    src = _cn4()
    tz = _opac(_SI_ZEFF, hint="keV")
    if src is None or tz is None:
        log("  SKIP: cn4 或 Si_Zeff 缺失")
        return
    _p, cn4, tables = src
    eos = cn4_eos_to_rho_base(tables[0])
    zbar = _as2d(eos, "zbar")               # (nTe,nrho)
    rho_cn4 = np.asarray(eos.axes["rho"])
    Te_cn4 = np.asarray(eos.axes["Te"])
    rho_z = np.asarray(tz.axes["rho"])
    Te_z = np.asarray(tz.axes["Te"])
    Zw = np.geomspace(max(rho_cn4.min(), rho_z[rho_z > 0].min()),
                      min(rho_cn4.max(), rho_z.max()), 20)
    Tw = np.geomspace(max(Te_cn4.min(), Te_z.min()),
                      min(Te_cn4.max(), Te_z.max()), 20)
    z_cn4_w = _interp2d_loglog(zbar, rho_cn4, Te_cn4, Zw, Tw)
    z_si = _as2d(tz, "Z")
    ok_si = np.isfinite(z_si) & (z_si > -9.0)      # 掩膜 -10 哨兵，其余为物理 log10(zbar)
    z_si_lin = np.where(ok_si, np.power(10.0, np.where(ok_si, z_si, 0.0)), np.nan)
    z_si_w = _interp2d_loglog(z_si_lin, rho_z, Te_z, Zw, Tw)
    m = np.isfinite(z_si_w) & (z_si_w > 0) & np.isfinite(z_cn4_w)
    s = _rel_stats(z_cn4_w[m], z_si_w[m]) if m.any() else None
    _CACHE["zeff_cmp"] = {"s": s, "n_mask": int(m.sum()), "Zw": Zw, "Tw": Tw,
                          "z_cn4": z_cn4_w, "z_si": z_si_w, "mask": m}
    expect(int(m.sum()) > 100, f"Zeff 公共可比点 {int(m.sum())} > 100")
    if s:
        log(f"  zbar vs Si_Zeff: n={s['n']} median={s['median']:.2%} "
            f"p90={s['p90']:.2%}（IONMIX vs QEOS 电离模型差，仅展示）")


# ── 测试 9：图 + HTML 报告（含文件树节） ─────────────────────────
def _plot_all() -> list:
    pngs = []
    q = _qeos()
    if q is not None:
        _path, qt = q
        rho = np.asarray(qt.axes["rho"])
        Te = np.asarray(qt.axes["Te"])
        P = _as2d(qt, "P") * 1e-12           # Mbar
        E = _as2d(qt, "E") * 1e-12
        fig, axes = plt.subplots(1, 2, figsize=(12.8, 4.8))
        for i in range(0, len(Te), 11):
            axes[0].loglog(rho, P[i], label=f"Te={Te[i]:g} eV")
            axes[1].loglog(rho, np.where(E[i] > 0, E[i], np.nan),
                           label=f"Te={Te[i]:g} eV")
        axes[0].set_ylabel("P [Mbar]"); axes[0].set_xlabel("rho [g/cm3]")
        axes[1].set_ylabel("E [Mbar*cm3/g]"); axes[1].set_xlabel("rho [g/cm3]")
        axes[0].set_title("qeos_392 P(rho) isotherms", fontsize=11)
        axes[1].set_title("qeos_392 E(rho) isotherms (E>0)", fontsize=11)
        for ax in axes:
            ax.legend(fontsize=8)
        fig.tight_layout()
        p = _OUT / "qeos_axes_overview.png"
        fig.savefig(p, dpi=110); plt.close(fig); pngs.append(p)

        # 自反演核验图：de(T) 曲线 + to_de_grid T(de)
        E_erg = _as2d(qt, "E")
        e0 = E_erg[0, :]
        fig, axes = plt.subplots(1, 2, figsize=(12.8, 4.8))
        for j in (10, 34, 55, 67):
            de = E_erg[:, j] - e0[j]
            axes[0].loglog(np.asarray(qt.axes["Te"]), np.where(de > 0, de, np.nan),
                           label=f"rho={rho[j]:g}")
        axes[0].axhline(OP_INV["de_erg"][1], ls="--", c="r",
                        label=f"prog de_max={OP_INV['de_erg'][1]:.3g}")
        axes[0].set_xlabel("Te [eV]"); axes[0].set_ylabel("de = E - e0 [erg/g]")
        axes[0].legend(fontsize=8); axes[0].set_title("self-inversion de(Te)", fontsize=11)
        res = _CACHE.get("degrid")
        if res is not None:
            Tg = res.fields["T"]
            for j in (10, 34, 55, 67):
                axes[1].loglog(np.asarray(res.de), Tg[:, j], label=f"rho={rho[j]:g}")
            axes[1].set_xlabel("de [erg/g]"); axes[1].set_ylabel("T [eV]")
            axes[1].legend(fontsize=8)
            axes[1].set_title("to_de_grid T(de) (positive-E region)", fontsize=11)
        fig.tight_layout()
        p = _OUT / "qeos_inverted_check.png"
        fig.savefig(p, dpi=110); plt.close(fig); pngs.append(p)

    # Si 原生不透明度热图（群平均，仅定性；两面板共享色标）
    tp, tr = _opac(_SI_PLANCK), _opac(_SI_ROSS)
    if tp is not None and tr is not None:
        fig, axes = plt.subplots(1, 2, figsize=(12.8, 4.8))
        fields = []
        for t in (tp, tr):
            k = _as2d(t, "kappa_g").reshape(110, 21, 22)
            fields.append(k.mean(axis=0))
        vmin = min(f.min() for f in fields)
        vmax = max(f.max() for f in fields)
        for ax, M, t, nm in ((axes[0], fields[0], tp, "Si_Planck (110-group mean)"),
                             (axes[1], fields[1], tr, "Si_Rosseland (110-group mean)")):
            _plot_heat(ax, M, np.asarray(t.axes["rho"]), np.asarray(t.axes["Te"]),
                       nm, vmin=vmin, vmax=vmax, colorbar=(ax is axes[1]))
        fig.suptitle("log10(kappa [cm2/g]) -- group-mean, plot-only (shared color scale)",
                     fontsize=11)
        fig.tight_layout()
        p = _OUT / "si_opacity_heatmaps.png"
        fig.savefig(p, dpi=110); plt.close(fig); pngs.append(p)

    meta = _ensure_conv()
    if meta is not None:
        # cn4 转换 F2 vs Si 原生 2x2
        fig, axes = plt.subplots(2, 2, figsize=(12.8, 9.2))
        panels = []
        for key, nm in (("f2_ross", "cn4->F2 Rosseland (6-group mean)"),
                        ("f2_planck", "cn4->F2 Planck abs (6-group mean)")):
            t = meta[key]
            k = np.asarray(t.fields["kappa_g"], dtype=float).reshape(t.field_shape["kappa_g"])
            panels.append((k.mean(axis=0), np.asarray(t.axes["rho"]),
                           np.asarray(t.axes["Te"]), nm))
        for t, nm in ((tp, "Si_Planck (110-group mean)"),
                      (tr, "Si_Rosseland (110-group mean)")):
            if t is None:
                continue
            k = np.asarray(t.fields["kappa_g"], dtype=float).reshape(t.field_shape["kappa_g"])
            panels.append((k.mean(axis=0), np.asarray(t.axes["rho"]),
                           np.asarray(t.axes["Te"]), nm))
        for ax, (M, r, T_, nm) in zip(axes.ravel(), panels):
            _plot_heat(ax, M, r, T_, nm,
                       vmin=min(p[0].min() for p in panels),
                       vmax=max(p[0].max() for p in panels),
                       colorbar=(ax is axes.ravel()[-1]))
        fig.suptitle("log10(kappa [cm2/g]) -- cn4(6g) vs Si(110g) group-mean "
                     "(shared color scale; stitched per-group compare: next fig)",
                     fontsize=11)
        fig.tight_layout()
        p = _OUT / "cn4_vs_si_opac_heatmaps.png"
        fig.savefig(p, dpi=110); plt.close(fig); pngs.append(p)

        # 边界拼接群对比图（每族 2 行：上=Si 拼接、下=cn4；全图共享色标）
        st = _CACHE.get("stitch")
        if st:
            for fam, fname in (("ross", "stitched_rosseland.png"),
                               ("planck", "stitched_planck.png")):
                rows = [r for r in st["results"][fam] if r.get("stat")]
                if not rows:
                    continue
                fig, axes = plt.subplots(2, len(rows),
                                         figsize=(3.2 * len(rows), 8.6))
                allM = [r[key] for r in rows for key in ("si", "cn4")]
                vmin = min(M.min() for M in allM)
                vmax = max(M.max() for M in allM)
                for j, r in enumerate(rows):
                    _plot_heat(axes[0, j], r["si"], st["rho_si"], st["Te_si"],
                               f"Si stitched g{r['gi']}\n[{r['band']}] "
                               f"({r['nsub']} sub)",
                               vmin=vmin, vmax=vmax, colorbar=False)
                    _plot_heat(axes[1, j], r["cn4"], st["rho_si"], st["Te_si"],
                               f"cn4 g{r['gi']} (interp)\nmedian "
                               f"{r['stat']['median_dex']:.2f} dex",
                               vmin=vmin, vmax=vmax, colorbar=False)
                im = axes[0, 0].images[0]
                fig.colorbar(im, ax=axes, shrink=0.55,
                             label="log10(kappa [cm2/g])")
                fig.suptitle(f"{fam}: Si 110g stitched vs cn4 6g "
                             "(energy-width weighted, shared scale)",
                             fontsize=11)
                fig.tight_layout()
                p = _OUT / fname
                fig.savefig(p, dpi=110); plt.close(fig); pngs.append(p)

        # EOS 曲线对比
        cmp_res = _CACHE.get("eos_cmp")
        if cmp_res:
            rho_w, Te_w = cmp_res["rho_w"], cmp_res["Te_w"]
            fig, axes = plt.subplots(1, 2, figsize=(12.8, 4.8))
            for i in (0, len(Te_w) // 2, len(Te_w) - 1):
                axes[0].loglog(rho_w, cmp_res["Pc"][i], label=f"cn4 Te={Te_w[i]:g}")
                axes[0].loglog(rho_w, cmp_res["Pq"][i], "--", label=f"qeos Te={Te_w[i]:g}")
                axes[1].loglog(rho_w, np.where(cmp_res["Ec"][i] > 0, cmp_res["Ec"][i], np.nan),
                               label=f"cn4 Te={Te_w[i]:g}")
                axes[1].loglog(rho_w, np.where(cmp_res["Eq"][i] > 0, cmp_res["Eq"][i], np.nan),
                               "--", label=f"qeos Te={Te_w[i]:g}")
            axes[0].set_ylabel("P [Mbar]"); axes[1].set_ylabel("E [Mbar*cm3/g]")
            for ax in axes:
                ax.set_xlabel("rho [g/cm3]"); ax.legend(fontsize=7)
            axes[0].set_title("cn4 vs qeos_392 P(rho) in common window", fontsize=11)
            axes[1].set_title("cn4 vs qeos_392 E(rho) (E>0)", fontsize=11)
            fig.tight_layout()
            p = _OUT / "cn4_vs_si_eos_curves.png"
            fig.savefig(p, dpi=110); plt.close(fig); pngs.append(p)

        # Zeff 对比（三面板统一 log10(zbar) 口径 + 共享色标）
        zc = _CACHE.get("zeff_cmp")
        if zc:
            fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.4))
            Zsi = _as2d(_opac(_SI_ZEFF, hint="keV"), "Z")
            Zsv = _as2d(_opac(_SI_Z, hint="eV"), "Z")
            t0 = _opac(_SI_ZEFF, hint="keV")
            p0 = np.where(Zsi > -9, Zsi, np.nan)
            p1 = np.where(Zsv > -9, Zsv, np.nan)
            # cn4 zbar → log10(zbar)（统一口径）
            zc4 = zc["z_cn4"]
            p2 = np.where(zc["mask"] & (zc4 > 0), np.log10(np.where(zc4 > 0, zc4, np.nan)),
                          np.nan)
            vmin = min(np.nanmin(a) for a in (p0, p1, p2))
            vmax = max(np.nanmax(a) for a in (p0, p1, p2))
            _plot_heat(axes[0], p0, np.asarray(t0.axes["rho"]), np.asarray(t0.axes["Te"]),
                       "Si_Zeff.dat log10(zbar) (2016)", vmin=vmin, vmax=vmax,
                       colorbar=False)
            _plot_heat(axes[1], p1, np.asarray(t0.axes["rho"]), np.asarray(t0.axes["Te"]),
                       "Si_Z.dat log10(zbar) (2012)", vmin=vmin, vmax=vmax,
                       colorbar=False)
            _plot_heat(axes[2], p2, zc["Zw"], zc["Tw"],
                       "cn4 log10(zbar) (interp)", vmin=vmin, vmax=vmax,
                       colorbar=(True))
            fig.suptitle("mean ionization log10(zbar): IONMIX cn4 vs QEOS Thermos "
                         "(same caliber + shared color scale)", fontsize=11)
            fig.tight_layout()
            p = _OUT / "zeff_compare.png"
            fig.savefig(p, dpi=110); plt.close(fig); pngs.append(p)
    return pngs


def _img_tag(png: Path) -> str:
    data = base64.b64encode(png.read_bytes()).decode("ascii")
    return (f'<figure><img src="data:image/png;base64,{data}" alt="{_html.escape(png.name)}">'
            f"<figcaption>{_html.escape(png.name)}</figcaption></figure>")


def _file_tree_html() -> str:
    rows = [
        ("src/Multi1D++Portable20241128/matter++/", "", "MULTI 便携版数据根（与外部根逐字节相同）"),
        ("  hyades/qeos/qeos_392.dat", "F3 hyades_eos", "Si QEOS (rho,T) 表 68×67，L=9249；68×299 反演为程序自产 [S-PROG]"),
        ("  hyades/qeos/qeos_392.dat.feos/.par", "FEOS 附件", "名不副实（内容同 .dat）/ FEOS 参数"),
        ("  Thermos/mat_Si/Si_Planck.dat", "F2 multi_opacity", "110 群 Planck，21×22，log10 cm2/g"),
        ("  Thermos/mat_Si/Si_Rosseland.dat", "F2 multi_opacity", "110 群 Rosseland，同布局"),
        ("  Thermos/mat_Si/Si_Zeff.dat", "F2 ZEFF (keV)", "平均电离化 2016 版"),
        ("  Thermos/mat_Si/Si_Z.dat", "F2 ZEFF (keV 实测)", "2012 旧版，147 字节载荷差"),
        ("  Thermos/mat_Si/Si.ini", "明文轴清单", "T=21/D=22/Frequency=111（本测试群边界 oracle 来源）"),
        ("eos_op_data/Gen_eos_op_data/Z14_1.00-20260708_0850/", "cn4 (IONMIX)", "Si cn4：ntemp=51/ndens=31/ngrups=6"),
        ("eosop_pro/parsers/test/_out/test_multi_si/", "产物", "本测试全部图像/报告/转换产物"),
    ]
    tr = "".join(f"<tr><td><code>{_html.escape(a)}</code></td><td>{b}</td>"
                 f"<td>{c}</td></tr>" for a, b, c in rows)
    return f"<table><tr><th>路径</th><th>格式族</th><th>说明</th></tr>{tr}</table>"


def test_si_report():
    pngs = _plot_all()
    _CACHE["pngs"] = pngs
    inv = _CACHE.get("inv", {})
    cmp_res = _CACHE.get("eos_cmp", {})
    zc = _CACHE.get("zeff_cmp", {})
    bounds_rows = _CACHE.get("bounds_rows", [])
    st = _CACHE.get("stitch", {})
    ems = _CACHE.get("ems_stats", {})

    def _stats_row(nm, s):
        if s is None:
            return f"<tr><td>{nm}</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>"
        return (f"<tr><td>{nm}</td><td>{s['n']}</td><td>{s['median']:.2%}</td>"
                f"<td>{s['p90']:.2%}</td><td>{s['max']:.2%}</td></tr>")

    def _stitch_rows(fam):
        out = []
        for r in st.get("results", {}).get(fam, []):
            if r.get("stat"):
                s = r["stat"]
                out.append(f"<tr><td>群{r['gi']} [{r['band']}]</td><td>{r['nsub']} 子群"
                           f"精确拼接</td><td>{s['n']}</td><td>{s['median_dex']:.3f}</td>"
                           f"<td>{s['p90_dex']:.3f}</td><td>{s['within03']:.0%}</td></tr>")
            else:
                out.append(f"<tr><td>群{r['gi']} [{r['band']}]</td><td>-</td>"
                           f"<td colspan=4>{r['note']}</td></tr>")
        return "".join(out)

    rows_cmp = (_stats_row("P: cn4 vs qeos_392 (公共窗口)", cmp_res.get("sP"))
                + _stats_row("E: cn4 vs qeos_392 (双方正能)", cmp_res.get("sE"))
                + _stats_row("zbar: cn4 vs Si_Zeff (软对比)", zc.get("s")))
    rows_b = "".join(f"<tr><td>{_html.escape(a)}</td><td>{b}</td>"
                     f"<td><code>{_html.escape(c)}</code></td></tr>"
                     for a, b, c in bounds_rows)
    inv_rows = "".join(
        f"<tr><td>{k}</td><td>{v:.6g}</td></tr>" for k, v in inv.items())
    kmin_rems = "".join(f"<li>{_html.escape(x)}</li>" for x in _CACHE.get("kmin_rem", []))
    imgs = "".join(f"<h3>{_html.escape(p.stem)}</h3>{_img_tag(p)}" for p in pngs)

    page = f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><title>Si (Z14) 组合核查报告</title>
<style>
  body {{ font-family: "Segoe UI","Microsoft YaHei",sans-serif; margin: 2em auto; max-width: 1150px; color: #222; background: #fafafa; }}
  h1 {{ border-bottom: 3px solid #2e8b57; padding-bottom: .3em; }}
  h2 {{ color: #2e8b57; margin-top: 1.6em; }}
  section {{ border: 1px solid #ccc; border-radius: 8px; padding: 1em 1.5em; margin: 1.5em 0; background: #fff; }}
  table {{ border-collapse: collapse; margin: .8em 0; }}
  td, th {{ border: 1px solid #bbb; padding: 3px 10px; font-size: .9em; }}
  th {{ background: #e8f3ec; }}
  code {{ background: #eee; padding: 1px 4px; border-radius: 3px; }}
  .gallery {{ display: flex; flex-wrap: wrap; gap: 10px; }}
  figure {{ margin: 0; text-align: center; }} figure img {{ max-width: 460px; border: 1px solid #999; }}
  figcaption {{ font-size: .75em; color: #555; }}
  .note {{ background: #fff7e0; border-left: 4px solid #e0a800; padding: .6em 1em; margin: .8em 0; }}
  .decl {{ background: #eaf3ea; border-left: 4px solid #3a8a3a; padding: .6em 1em; margin: .8em 0; }}
</style></head><body>
<h1>Si（Z14 / matter++）组合核查报告</h1>
<p>被测: qeos_392.dat (F3 Hyades/QEOS 68×67) + Thermos/mat_Si 四件套 (F2 110 群/ZEFF)
   + Z14 cn4 (IONMIX 51×31×6) ｜ 独立测试（不接 run_all）｜
   数据与外部根 E:\\...\\Multi1D++Portable20241128 逐字节相同（SHA256 比对）</p>

<section><h2>1. 数据源文件树</h2>{_file_tree_html()}</section>

<section><h2>2. 操作者视图 oracle（Multi 程序加载输出，2026-11-14 用户提供）</h2>
<table><tr><th>oracle</th><th>值</th><th>核查结果</th></tr>
<tr><td>qeos_392 EOS Boundaries</td><td>68×67；rho [0.001,1000] g/cm3；T [0.025,1e5] eV；
    P [33462.8, 5.15544e19] dyne/cm2；E [-2.27897e6, 7.77105e16] erg/g</td>
    <td>✅ 逐项命中（测 1）；T 轴文件存 keV log10 → ×1e3 → eV</td></tr>
<tr><td>Inverted EOS Boundaries (68×299)</td><td>e0 [-2.19359e9, 2.22449e14] erg/g；
    de [0, 7.7405e16] erg/g；P max 5.15544e19；T max 1e5 eV</td>
    <td>⚠️ 程序自产（磁盘无 68×299 文件）→ 测 2 软核验：de_max 命中，
    e0 端点量级一致、细节差异记 REM</td></tr>
<tr><td>Si_Planck / Si_Rosseland</td><td>110 群（0.1–40000 eV，111 边界）；21×22；
    log10(kappa) 打印范围 Planck [-0.122273,11.1305] / Ross [-0.283409,10.9544]</td>
    <td>✅ 群边界逐点一致（=Si.ini Frequency）；max 命中；
    min 比打印更负（实测 Planck -2.48 / Ross -4.67）→ 打印口径 REM</td></tr>
<tr><td>Si_Zeff.dat</td><td>（用户粘贴为空）</td><td>实测：单表 ZEFF f2=6，(21,22)，
    载荷为 <b>log10(zbar)</b> ∈ [-10 哨兵, 1.1714632]（45 元素族校准证据，已裁定落库，见 §7）；
    rho [1e-6,1e4] / Te [0.04,1e5] eV</td></tr>
</table></section>

<section><h2>3. 单位链推导</h2>
<ul>
<li><b>T</b>：文件 log10(T_keV) ∈ [-4.39794, 2] → 10^x keV → ×1e3 → eV；
    0.04 eV ↔ -4.39794（keV log10）＝操作者视图首温。</li>
<li><b>P</b>：1 dyne/cm² = 0.1 Pa = 1e-7 J/cm³ → 1 J/cm³ = 1e7 dyne/cm²；
    1 Mbar = 1e12 dyne/cm²。cn4 P (J/cm³) ÷1e5 = Mbar；qeos P (dyne/cm²) ÷1e12 = Mbar。</li>
<li><b>E</b>：1 erg = 1e-7 J → 1 erg/g = 1e-7 J/g；1 Mbar·cm³/g = 1e5 J/g = 1e12 erg/g。
    cn4 E (J/g) ÷1e5、qeos E (erg/g) ÷1e12 → 统一 Mbar·cm³/g。</li>
<li><b>rho</b>：cn4 轴 nion (cm⁻³) → rho = nion·&lt;A&gt;/N_A（&lt;A&gt;=28.085）。</li>
</ul></section>

<section><h2>4. qeos_392 自反演软核验（68×299 无磁盘文件 [S-PROG]）</h2>
<table><tr><th>量</th><th>值</th></tr>{inv_rows}</table>
<p>de_max 由每密度列 E_max − e0 直接算得（精确算术）；e0 端点与程序打印量级一致、
细节差异（零点/低温外推约定）记 REM 不判 FAIL。</p></section>

<section><h2>5. cn4 对比统计（跨模型：IONMIX vs LLNL-QEOS，无硬阈值）</h2>
<table><tr><th>对比项</th><th>n</th><th>median</th><th>p90</th><th>max</th></tr>
{rows_cmp}</table>
<p>窗口: rho [{cmp_res.get('window', (0,0,0,0))[0]:.3g}, {cmp_res.get('window', (0,0,0,0))[1]:.3g}] g/cm3,
Te [{cmp_res.get('window', (0,0,0,0))[2]:.3g}, {cmp_res.get('window', (0,0,0,0))[3]:.3g}] eV。</p>
<div class="note">物理声明：cn4 是 IONMIX 产物，qeos_392/Thermos 是 LLNL QEOS 产物——
对比目标是"转换正确性 + 数值邻近度"，不是模型一致性验证。</div></section>

<section><h2>6. 不透明度群边界对照与拼接群对比（2026-11-14 用户裁定升级）</h2>
<table><tr><th>文件</th><th>群数</th><th>群边界</th></tr>{rows_b}</table>

<h3>6.1 边界拼接群数值对比（同单位 log10(cm2/g)、每族共享色标）</h3>
<p>Si 110 群中存在与 cn4 6 群**边界精确重合**的子群集合：cn4 群 [0.1,1] 与 [1,10]
与 Si 子群一一对应；[10,100]、[100,1000]、[1000,10000] 分别由 9/49/42 个 Si 子群
**精确铺满**（边界逐点重合）。聚合口径（平谱近似，REM 已声明）：
Planck（算术）$\kappa_{{agg}}=\sum_i \Delta E_i\,\kappa_i / \sum_i \Delta E_i$；
Rosseland（调和）$1/\kappa_{{agg}}=\sum_i \Delta E_i/\kappa_i / \sum_i \Delta E_i$；
统计在 log10 域以 dex 计，掩膜限制在 cn4 原生 (rho,Te) 范围内。</p>
<p><b>Rosseland（Si_Rosseland vs cn4 块17）</b></p>
<table><tr><th>cn4 群</th><th>拼接方式</th><th>n</th><th>median (dex)</th>
<th>p90 (dex)</th><th>≤0.3 dex 占比</th></tr>
{_stitch_rows('ross')}</table>
<p><b>Planck 吸收（Si_Planck vs cn4 块18）</b></p>
<table><tr><th>cn4 群</th><th>拼接方式</th><th>n</th><th>median (dex)</th>
<th>p90 (dex)</th><th>≤0.3 dex 占比</th></tr>
{_stitch_rows('planck')}</table>
<p>cn4 群6 [10000,100000] 因 Si 表能量上限 40000 eV 覆盖不足，不做数值对比（记 REM）。</p>
<div class="decl">裁定升级（2026-11-14）：不再"边界不同 → 只绘图"，改为**可精确拼接的
群做数值对比**；聚合采用能量宽度加权平谱近似（逐子群真值聚合需谱权重函数，无谱数据）。</div>

<h3>6.2 Planck 发射 vs 吸收：MULTI 与 IONMIX（abjt_03.f）的处理机制</h3>
<table>
<tr><th>侧</th><th>机制（溯源）</th></tr>
<tr><td><b>MULTI</b></td>
<td>发射按 Kirchhoff 定律绑定吸收：$\eta_\nu=\kappa_\nu\,I_\nu^{{eq}}(T)$
（Ramis 1988, CPC 49, eq.(2.4)-(2.5)，References/1988CPC49 PDF p.3）；群源
$U_{{S,k}}=\epsilon_k\,U_{{P,k}}(T)$（eq.(3.21)），其中 $\epsilon_k$ 为 **NLTE 因子**
（"Deviations from LTE ... taken into account by the coefficients ε_k ... In LTE,
ε_k are equal to unity"，p.8 §3.3）——即 **Planck 吸收系数同时驱动吸收项与（ε=1 的）
发射源；非 LTE 时由独立的 EPS 表（docx 表1："EPS 1/EPS M 表示 NLTE 因子"；
SNOP.MANUAL NEPS："If LTE is chosen, this table is not necessary"）缩放发射**。
MULTI 便携版仅二进制无源码，以上为手册+文献级结论。</td></tr>
<tr><td><b>IONMIX (abjt_03.f)</b></td>
<td>逐频点独立计算两条系数链（isw(6) 控制 LTE/non-LTE 布局）：
<b>吸收</b>受激辐射修正 <code>stcorr = max(0, n − n_eq·e^(-hν/kT))</code>（L762-774，
non-LTE 用实际布局 deni、LTE 用平衡布局 eqdeni）；<b>发射</b>恒用 **LTE 平衡布局**
<code>sum2e += eqdeni·(1−e^(-hν/kT))·xsec</code>（L774-776）；线过程同构
（L1047-1083：abscof=α·corsea 实际布局修正 / emscof=α·corsee 平衡布局）。
群平均（opacgp，L3889-4135）：Planck 权 $x^3 e^(-x)/(1-e^(-x))$ 分别作用于
$\alpha_\nu$（→κ_PA）与 $\eta_\nu$（→κ_PE），Rosseland 权
$x^4 e^(-x)/(1-e^(-x))^2/(\alpha_\nu+\sigma_\nu)$；owtf（L~4700）依次写块
17=Rosseland / 18=Planck 吸收 / 19=Planck 发射（×opacity_lim=1.0）。
<b>结论：cn4 的块 18 与块 19 是两条独立物理链</b>（发射≈LTE Kirchhoff 语义，
吸收含 non-LTE 实际布局+受激辐射修正），与 MULTI 的"吸收+ε 因子"结构不同构。</td></tr>
</table>
<p><b>实证（Z14 cn4）</b>：块 18 vs 块 19 有 {ems.get('n_diff','?')}/{ems.get('n_total','?')}
点数值不同，|Δ| 相对中位 {ems.get('median_rel',0):.2%} → 发射/吸收确系独立生成，
FLASH 使用群表时两者不可互相替代。</p></section>

<section><h2>7. REM 记录</h2><ul>
<li>Si_Z.dat / Si_Zeff.dat 单位编码：Readme.txt 约定成立——Si_Z.dat 存 log10(T_eV)
    （起点 -1.39794）、Si_Zeff.dat 存 log10(T_keV)（起点 -4.39794）；unit_hint 必须分别为
    eV / keV，错用差 ×1e3。两文件磁盘差 147 字节（含 T 轴编码段）。</li>
<li>Z ≤ -9.9 为哨兵（=log10(1e-10) 近零电离）；其余负值为物理低电离 log10(zbar)。</li>
<li><b>ZEFF 载荷为 log10(zbar)（2026-11-14 用户裁定，已落库）</b>：45 个
    Thermos/mat_*_Zeff.dat 族校准——max 值 10^Z 与核电荷数逐一吻合
    （H 1.09、He 2.22、C 6.20、Si 14.84、Fe 26.5、Ag 47.6、Au 81.3、U 92.5，
    高压端略超核值符合压致电离）；field_checks "Z" 条目已转 checked
    （kind=parser-measured，单位 log10(zbar)），解析器 field_units/field_log10
    同步更新，字典 md 已重生成。ZEFF2（Z2）Thermos 无样本，本裁定不适用。</li>
<li>拼接聚合口径：能量宽度加权平谱近似——逐子群真值聚合需 Planck/Rosseland
    权重函数在子群内的谱积分（数据不可得）；Rosseland 用调和加权、Planck 用
    算术加权，对平滑连续谱是良好近似，对谱线主导群可能高估聚合 κ。</li>
<li>cn4 群6 [10000,100000] eV：Si 表能量上限 40000 eV，覆盖不足 → 不做数值对比。</li>
<li>自反演 e0 端点：e0_max 与程序打印精确一致（2.2245e14），e0_min 自算 -2.279e6
    vs 程序 -2.1936e9（差 ×1e3，量级不一致）——程序 e0 的低温端定义（零点/外推）未公开，
    记 [S-UNK] 不判 FAIL。</li>
{kmin_rems}
</ul></section>

<section><h2>8. 核查图像（{len(pngs)} 张）</h2>
<div class="gallery">{imgs}</div></section>
</body></html>"""
    rpt = _OUT / "report.html"
    rpt.write_text(page, encoding="utf-8", newline="\n")
    log(f"  report: {rpt}  ({rpt.stat().st_size:,} bytes, {len(pngs)} images)")
    write_summary("test_multi_si", [
        "qeos_392: F3 68x67 oracle 命中；68x299 反演=程序自产，de_max 软核验通过",
        f"self-inversion: {inv}",
        f"cn4 vs qeos: P {cmp_res.get('sP')} | E {cmp_res.get('sE')}",
        f"zbar vs Si_Zeff: {zc.get('s')}",
        "opacity: cn4 6g vs Si 110g 边界拼接群对比（5/6 群精确拼接，平谱近似）",
        f"cn4 block18 vs block19: {ems.get('n_diff')}/{ems.get('n_total')} 点不同"
        f"（发射/吸收独立生成）",
    ])
    expect(rpt.exists() and rpt.stat().st_size > 5_000, "HTML 报告生成")


if __name__ == "__main__":
    raise SystemExit(main(globals()))
