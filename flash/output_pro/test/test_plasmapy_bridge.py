"""
test_plasmapy_bridge.py — 方案 A (PlasmaPy 适配层) 测试

测试策略:
  1. 单位桥: 用 gen_test_data 的合成 FLASH 文件验证 CGS→SI 换算
     (tele K / dens g/cm³→kg/m³ / nele 1/cm³→1/m³);
  2. 物理量交叉验证: 用受控物理工况的 duck-type 容器 (合成数据处于强耦合
     非物理区, 不适合直接验证) 对比
       - PlasmaPy vs 手写解析公式 (Debye length, Saha)
       - PlasmaPy vs 项目手写派生变量 (Theta_e)
       - PlasmaPy vs 项目基准常数 (临界密度 9.05e21 cm⁻³ @ 0.351 μm)
       - κ_e^SH 的 T^(5/2) 标度检验
  3. 降级路径: HAS_PLASMAPY=False 时物理量函数抛 RuntimeError(带安装指引)。

运行: pytest test/test_plasmapy_bridge.py -v -s
"""
import numpy as np
import pytest

from flash.output_pro import plasmapy_bridge as pb
from flash.output_pro.hdf5pro.flash_hdf5 import (
    electron_degeneracy_parameter,
    ion_coupling_parameter,
)

if pb.HAS_PLASMAPY:
    import astropy.units as u_  # 仅 plasmapy 存在时测试使用
else:  # pragma: no cover
    u_ = None


# ------------------------------------------------------------------
# 受控物理工况 duck-type 容器 (绕开合成数据的强耦合非物理区)
# ------------------------------------------------------------------
class _FakeContainer:
    """最小容器接口: get/unit/config — 与 FlashDataContainer 鸭子类型兼容。"""

    def __init__(self, data: dict, units: dict):
        self._data = {k: np.asarray(v, dtype=float) for k, v in data.items()}
        self.config = {k: {"unit": u_} for k, u_ in units.items()}

    def get(self, varname):
        if varname not in self._data:
            raise KeyError(f"变量 '{varname}' 不存在于 data 或 derived 中")
        return self._data[varname]

    def unit(self, varname):
        return self.config.get(varname, {}).get("unit", "")


# 物理合理工况: 类日冕 + 类固体两态 (⚠ 值按 DATA_CONFIG 单位制存储:
# tele K / nele 1/cm³ / ls_tele cm — 与 to_quantity 的 CGS 桥接约定一致)
_STATE_CORONA = {   # 日冕态: Te=1e7 K (~0.86 keV), ne=1e21 cm⁻³, L_T=0.1 mm
    "tele": 1.0e7, "nele": 1.0e21,
    "ls_tele": 1.0e-2,                    # cm (0.1 mm)
}
_STATE_SOLID = {    # 固体态: Te=1e6 K, ne=1e24 cm⁻³, L_T=10 nm
    "tele": 1.0e6, "nele": 1.0e24,
    "ls_tele": 1.0e-4,                    # cm (10 nm)
}
_UNITS = {"tele": "K", "nele": "1/cm^3", "ls_tele": "cm"}


def _mk_corona(shape=(32,)):
    d = {k: np.full(shape, v) for k, v in _STATE_CORONA.items()}
    return _FakeContainer(d, _UNITS)


def _mk_solid(shape=(32,)):
    d = {k: np.full(shape, v) for k, v in _STATE_SOLID.items()}
    return _FakeContainer(d, _UNITS)


# ==================================================================
# 1) 单位桥 (真实合成 FLASH 数据)
# ==================================================================
def test_to_quantity_units_real_file():
    """CGS→SI: tele K 直通 / dens g/cm³→kg/m³ / nele cm⁻³→m⁻³。"""
    data = _load_real_container()
    Te = pb.to_quantity(data, "tele")
    rho = pb.to_quantity(data, "dens")
    ne = pb.to_quantity(data, "nele")
    assert str(Te.unit) == "K"
    assert abs(rho.value.max() - 2700.0) < 1e-6 * 2700        # 2.7 g/cm³ → 2700 kg/m³
    assert str(ne.unit) == "1 / m3"
    assert abs(ne.value.max() - 8.1299e29) < 1e-3 * 8.1299e29  # 单位测试同源基准值


def test_to_quantity_unknown_unit_raises():
    c = _FakeContainer({"foo": [1.0]}, {"foo": "bogus/unit"})
    with pytest.raises(ValueError, match="未在 bridge"):
        pb.to_quantity(c, "foo")


# ==================================================================
# 2) 物理量交叉验证 (受控物理工况)
# ==================================================================
def test_coulomb_log_physical_range():
    """物理工况 lnΛ ∈ (1, 30), 且对密度单调。"""
    c = _mk_corona()
    lnL = pb.coulomb_log_profile(c)
    assert np.all(np.isfinite(lnL))
    assert 1.0 < lnL.mean() < 30.0
    # 密度升 100× → lnΛ 降 (弱依赖)
    d2 = {k: np.full(32, v) for k, v in _STATE_CORONA.items()}
    d2["nele"] = d2["nele"] * 100
    lnL2 = pb.coulomb_log_profile(_FakeContainer(d2, _UNITS))
    assert lnL2.mean() < lnL.mean()


def test_debye_length_vs_analytic():
    """λ_D vs 解析式 sqrt(ε0 kB Te / (ne e²)), 相对误差 < 1e-4。"""
    c = _mk_corona()
    lD = pb.debye_length_profile(c)
    eps0 = 8.8541878128e-12
    kB = 1.380649e-23
    e = 1.602176634e-19
    ne_m3 = _STATE_CORONA["nele"] * 1e6  # 存储 1/cm³ → 手算需 1/m³
    lD_manual = np.sqrt(eps0 * kB * _STATE_CORONA["tele"] / (ne_m3 * e**2))
    assert str(lD.unit) == "m"
    assert np.allclose(lD.value, lD_manual, rtol=1e-4)


def test_critical_density_benchmark():
    """n_c(0.351 μm) ≈ 9.05×10²¹ cm⁻³ (项目基准, 0.1% 容差)。"""
    nc = pb.critical_density_351()
    nc_cgs = nc.to_value("1 / cm^3")
    assert abs(nc_cgs - 9.05e21) / 9.05e21 < 1e-3


def test_quantum_theta_vs_handwritten():
    """Θ_e: PlasmaPy quantum_theta vs 手写 electron_degeneracy_parameter。"""
    c = _mk_solid()  # 固体密度下简并效应显著, 数值有区分度
    th_py = pb.quantum_theta_profile(c)
    # 手写实现输入 CGS: nele 1/cm³, tele K (与 _STATE_SOLID 存储值一致)
    th_hand = electron_degeneracy_parameter(
        np.full(32, _STATE_SOLID["nele"]), np.full(32, _STATE_SOLID["tele"]))
    m = np.isfinite(th_py) & np.isfinite(th_hand)
    assert m.all()
    assert np.allclose(th_py[m], th_hand[m], rtol=1e-6)


def test_coupling_parameter_vs_handwritten():
    """Γ_i: PlasmaPy coupling_parameter vs 手写 ion_coupling_parameter (标量)。"""
    gamma_py_func = pb.coupling_profile(("e-", "p+"))
    T_K, n_cm3, zbar = 1.0e6, 1.0e20, 1.0
    g_py = gamma_py_func(T_K, n_cm3 * 1e6)  # → 1/m³
    g_hand = float(ion_coupling_parameter(
        np.array([n_cm3]), np.array([T_K]), np.array([zbar]))[0])
    assert abs(g_py - g_hand) / g_hand < 1e-3


def test_mean_free_path_and_knudsen():
    """λ_mfp 有限正值; K_n = λ_mfp/L_Te 与手算一致 (L_Te cm→m ×1e-2)。"""
    c = _mk_corona()
    lfp = pb.mean_free_path_profile(c)
    assert np.all(np.isfinite(lfp.value)) and np.all(lfp.value > 0)
    kn = pb.knudsen_number_e(c)
    expect = lfp.value / (_STATE_CORONA["ls_tele"] * 1e-2)  # cm → m
    assert np.allclose(kn, expect, rtol=1e-10)


def test_spitzer_kappa_t25_scaling():
    """κ_e^SH ∝ T_e^(5/2)/lnΛ: 同密度双温态, 期望比值含 lnΛ 修正 (2% 容差)。

    lnΛ 修正项用与 spitzer_kappa_e 内部完全一致的调用
    (species ("e-","p+"), GMS-6, 显式 coulomb_log_ei 路径)。
    """
    from plasmapy.formulary import Coulomb_logarithm
    T1, T2, ne_cm3 = 1.0e6, 1.0e7, 1.0e20  # 同密度, 10× 升温
    def _mk(T):
        return _FakeContainer(
            {"tele": np.array([T]), "nele": np.array([ne_cm3]), "ls_tele": np.array([1e-2])},
            {"tele": "K", "nele": "1/cm^3", "ls_tele": "cm"})
    k1 = pb.spitzer_kappa_e(_mk(T1))
    k2 = pb.spitzer_kappa_e(_mk(T2))
    assert str(k1.unit) == "W / (K m)"
    assert np.isfinite(k1.value[0]) and np.isfinite(k2.value[0])
    lnL1 = float(Coulomb_logarithm(T1 * u_.K, ne_cm3 * 1e6 * u_.m**-3,
                                   ("e-", "p+"), z_mean=3.0, method="GMS-6"))
    lnL2 = float(Coulomb_logarithm(T2 * u_.K, ne_cm3 * 1e6 * u_.m**-3,
                                   ("e-", "p+"), z_mean=3.0, method="GMS-6"))
    expect = (T2 / T1) ** 2.5 * (lnL1 / lnL2)   # κ ∝ T^{5/2} / lnΛ (平行 SH 极限)
    ratio = k2.value[0] / k1.value[0]
    assert abs(ratio - expect) / expect < 0.02


def test_saha_zbar_finite_physical_state():
    """Z̄_Saha 在电离区 (Te=1e5 K, ne=1e20 cm⁻³) 为有限正值。"""
    c = _FakeContainer(
        {"tele": np.full(8, 1.0e5), "nele": np.full(8, 1.0e20)},  # K, 1/cm³
        {"tele": "K", "nele": "1/cm^3"},
    )
    zb = pb.saha_zbar(c)
    assert np.all(np.isfinite(zb.value))
    assert np.all(zb.value > 0.1)


def test_critical_surface_locates_interface():
    """临界密度面: 构造 nele 从 1e22 线性降到 1e18 cm⁻³ 的剖面, x_c 应落在
    n_e ≈ 9.05e21 cm⁻³ 附近 (1D, 均匀网格)。"""
    n = 200
    x_cm = np.linspace(0.0, 1.0, n)
    ne_cm3 = np.linspace(1.0e22, 1.0e18, n)
    c = _FakeContainer(
        {"tele": np.full(n, 1.0e7), "nele": ne_cm3,  # K, 1/cm³ (CGS 存储)
         "x": x_cm, "ls_tele": np.full(n, 1e-2)},
        {"tele": "K", "nele": "1/cm^3", "x": "cm", "ls_tele": "cm"},
    )
    x_c, nc = pb.critical_surface(c)
    # n_e 降到 n_c 的位置: x = (1e22 - 9.05e21)/(1e22-1e18) ≈ 0.0905
    x_expect = (1e22 - nc.to_value("1 / cm^3")) / (1e22 - 1e18)
    assert abs(x_c - x_expect) < 2.0 / (n - 1)  # 一个网格间距内


# ==================================================================
# 3) 降级路径 (无 plasmapy 环境)
# ==================================================================
def test_graceful_degradation(monkeypatch):
    """HAS_PLASMAPY=False 时物理量函数抛 RuntimeError 且消息含安装指引。"""
    monkeypatch.setattr(pb, "HAS_PLASMAPY", False)
    c = _mk_corona(shape=(4,))
    with pytest.raises(RuntimeError, match="install_editable"):
        pb.coulomb_log_profile(c)
    with pytest.raises(RuntimeError, match="install_editable"):
        pb.debye_length_profile(c)
    with pytest.raises(RuntimeError, match="install_editable"):
        pb.to_quantity(c, "tele")


# ==================================================================
# 辅助
# ==================================================================
def _load_real_container():
    """加载 gen_test_data 合成 1D 文件 (conftest 已在收集期生成)。"""
    from flash.output_pro.loader import FlashDataLoader

    glob_pattern = None
    from pathlib import Path
    here = Path(__file__).resolve().parent
    inputfiles = here.parent / "inputfiles"
    files = sorted((inputfiles / "hdf5files_1d").glob("lasslab_hdf5_*"))
    if not files:
        pytest.skip("合成测试数据未生成 (gen_test_data)")
    return FlashDataLoader(str(files[0])).load(compute_derived=True)
