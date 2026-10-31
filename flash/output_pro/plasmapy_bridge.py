"""
plasmapy_bridge.py — PlasmaPy 适配层（方案 A，松耦合）

把 FlashDataContainer 的 CGS 裸数组桥接为 astropy Quantity（自动 SI 化），
再调用 PlasmaPy 2026.2.0 的 formulary 计算带单位保证的物理量。

设计约定（方案 A 定稿，详见 docs/PlasmaPy在后处理分析的使用方案.html）:
  1. 零侵入: 不改动 hdf5pro/loader/plotter 任何一行; 本模块缺失 plasmapy 时
     优雅降级（HAS_PLASMAPY=False，物理量函数抛 RuntimeError 带安装指引）。
  2. 单位桥: 复用 DATA_CONFIG 的 CGS 单位字符串 → astropy 单位 → .si 化，
     与 FlashDataContainer.to_si() 既有约定一致。
  3. 字段纪律: 只依赖原始守恒量场 (tele/tion/nele/nion/zbar/dens/velx)，
     **禁止读取 fllm / q_fs** —— FL-SH 的 fllm 已被覆写为 λ₃，SNB 保留自由流
     q_fs，语义跨模型不一致（2026-10-30 结论）。
  4. 性能: 本模块为"交互级"单文件计算；批量（10⁵–10⁶ 网格 × 多文件）请走
     PlasmaPy 的 *_lite 无单位接口（见 docs/PlasmaPy在output_pro中的使用指南.md §5）。

用法示例:
    from flash.output_pro.loader import FlashDataLoader
    from flash.output_pro.plasmapy_bridge import (
        to_quantity, coulomb_log_profile, debye_length_profile,
        critical_density_351, knudsen_number_e,
    )

    c = FlashDataLoader("path/to/hdf5_chk_0005").load(compute_derived=True)

    lnL  = coulomb_log_profile(c)          # 逐网格库仑对数 (无量纲数组)
    lD   = debye_length_profile(c)         # 德拜长度 (m, Quantity)
    x_c  = critical_surface(c)             # 临界密度面位置 + n_c 复核
    kn   = knudsen_number_e(c)             # 电子 Knudsen 层数 λ_mfp/L_Te

    # 裸数组桥接（任意 DATA_CONFIG 注册变量）
    Te_si = to_quantity(c, "tele")         # Quantity [K]（自动 CGS→SI）
"""

from __future__ import annotations

import numpy as np

# ------------------------------------------------------------------
# 可选导入: plasmapy 缺席时整包可用, 物理量函数优雅降级
# ------------------------------------------------------------------
try:  # pragma: no cover - 环境相关
    import astropy.units as u
    import plasmapy
    from plasmapy.formulary import (
        Coulomb_logarithm,
        Debye_length,
        mean_free_path,
    )
    from plasmapy.formulary.braginskii import ClassicalTransport
    from plasmapy.formulary.collisions.dimensionless import coupling_parameter
    from plasmapy.formulary.densities import critical_density
    from plasmapy.formulary.ionization import ionization_balance
    from plasmapy.formulary.laser import em_angular_frequency
    from plasmapy.formulary.quantum import quantum_theta

    HAS_PLASMAPY = True
    PLASMAPY_VERSION = plasmapy.__version__
except ImportError:  # pragma: no cover
    HAS_PLASMAPY = False
    PLASMAPY_VERSION = None
    u = None  # type: ignore[assignment]

__all__ = [
    "HAS_PLASMAPY",
    "PLASMAPY_VERSION",
    "coulomb_log_profile",
    "coupling_profile",
    "critical_density_351",
    "critical_surface",
    "debye_length_profile",
    "knudsen_number_e",
    "mean_free_path_profile",
    "quantum_theta_profile",
    "require_plasmapy",
    "saha_zbar",
    "spitzer_kappa_e",
    "to_quantity",
]

_INSTALL_HINT = (
    "plasmapy 未安装。安装方式 (Windows, 需联网):\n"
    "  python flash/output_pro/PlasmaPy/install_editable.py\n"
    "或: <python> -m pip install -e flash/output_pro/PlasmaPy/src/PlasmaPy\n"
    "平台支持: win ✅ / wsl 条件 ✅ (py>=3.12) / hpc ❌ (py3.10, 优雅降级)"
)

# 默认离子种类: 项目基线为 CH/Ti 示踪体系, 用 Ti+3 (z_mean=3) 作 lnΛ 的代表离子;
# 更精确的逐网格 Z̄ 加权见使用指南 §6 (方案 B 路线)。
DEFAULT_ION = "Ti 3+"
DEFAULT_Z_MEAN = 3.0


def require_plasmapy():
    """门控: plasmapy 缺席时抛带安装指引的 RuntimeError。"""
    if not HAS_PLASMAPY:
        raise RuntimeError(_INSTALL_HINT)


# ------------------------------------------------------------------
# CGS → astropy 单位映射 (与 DATA_CONFIG unit 字符串一一对应)
# ------------------------------------------------------------------
_CGS2U = {
    "g/cm^3": None,  # 构造时惰性填充 (u 未导入时跳过)
}
if HAS_PLASMAPY:
    _CGS2U = {
        "g/cm^3": u.g / u.cm**3,
        "K": u.K,
        "dyne/cm^2": u.dyne / u.cm**2,
        "cm/s": u.cm / u.s,
        "1/cm^3": u.cm**-3,
        "erg/cm^3": u.erg / u.cm**3,
        "cm": u.cm,
        "erg": u.erg,
        "cm^2/s": u.cm**2 / u.s,
    }


def to_quantity(container, varname: str):
    """FlashDataContainer 裸数组 → astropy Quantity (自动 CGS→SI)。

    复用 DATA_CONFIG 的 unit 字符串; 未注册单位时抛 ValueError。
    返回 SI 基准 Quantity（.si），消除 CGS/SI 歧义。
    """
    require_unit_bridge()
    arr = container.get(varname)
    unit_str = container.unit(varname)
    if not unit_str:
        raise ValueError(
            f"变量 {varname!r} 在 DATA_CONFIG 中未登记单位, 无法桥接 "
            f"(可用: {[k for k in _CGS2U if k in (container.config.get(varname, {}) or {})]} )"
        )
    if unit_str not in _CGS2U:
        raise ValueError(f"单位 {unit_str!r} 未在 bridge _CGS2U 映射中注册, 请在 plasmapy_bridge.py 补充")
    return (np.asarray(arr, dtype=float) * _CGS2U[unit_str]).si


def require_unit_bridge():
    """单位桥依赖 astropy（随 plasmapy 一起安装）; 缺席时报安装指引。"""
    if not HAS_PLASMAPY:
        raise RuntimeError(_INSTALL_HINT)


# ------------------------------------------------------------------
# 高层物理量函数（输入: FlashDataContainer; 输出: SI Quantity 或裸数组）
# ------------------------------------------------------------------


def _si(container, varname):
    """内部快捷: 变量 → SI Quantity（必要变量缺失时报可读错误）。"""
    try:
        return to_quantity(container, varname)
    except KeyError:
        raise KeyError(f"容器中缺少变量 {varname!r} — 请 load(compute_derived=True) 以生成派生量") from None


def coulomb_log_profile(
    container, ion: str = DEFAULT_ION, z_mean: float = DEFAULT_Z_MEAN, method: str = "GMS-6"
) -> np.ndarray:
    """逐网格库仑对数 lnΛ(x)。FL-SH/SNB 非局域判定的核心输入。

    返回无量纲裸数组 (与 DATA_CONFIG 派生变量约定一致)。
    """
    require_plasmapy()
    Te = _si(container, "tele")
    ne = _si(container, "nele")
    lnL = Coulomb_logarithm(Te, ne, ("e-", ion), z_mean=z_mean, method=method)
    return np.asarray(lnL, dtype=float)


def debye_length_profile(container):
    """逐网格电子德拜长度 λ_D(T_e, n_e)。返回 SI Quantity [m]。"""
    require_plasmapy()
    return Debye_length(_si(container, "tele"), _si(container, "nele"))


def critical_density_351(wavelength_um: float = 0.351):
    """三倍频 (0.351 μm) 激光临界密度。返回 SI Quantity [1/m³]。

    项目基准: n_c ≈ 9.05×10²¹ cm⁻³ (0.351 μm)。
    """
    require_plasmapy()
    lam = wavelength_um * u.um
    return critical_density(em_angular_frequency(lam))


def critical_surface(container, wavelength_um: float = 0.351):
    """临界密度面 x_c: n_e(x) = n_c(λ) 等值面位置。

    返回 (x_value_in_container_units, n_c Quantity)。
    1D 场直接取最近网格点; 多维场取 n_e 最接近 n_c 的扁平单元。
    """
    require_plasmapy()
    ne_si = _si(container, "nele")
    nc = critical_density_351(wavelength_um)
    diff = np.abs(np.asarray(ne_si.value) - nc.si.value)
    idx = int(np.nanargmin(diff))
    # x 坐标: 优先容器已登记的坐标变量 (保持容器原单位, 通常 cm)
    for xname in ("x", "xc", "x_face"):
        try:
            x = container.get(xname)
            return float(np.asarray(x).ravel()[idx]) if np.ndim(x) else float(x), nc
        except Exception:  # noqa: BLE001, S112 — 非物理工况静默降级为扁平索引
            continue
    return float(idx), nc  # 无坐标时返回扁平索引


def mean_free_path_profile(container, ion: str = DEFAULT_ION):
    """电子平均自由程 λ_mfp(T_e, n_e)。返回 SI Quantity [m]。"""
    require_plasmapy()
    Te = _si(container, "tele")
    ne = _si(container, "nele")
    return mean_free_path(Te, ne, ("e-", ion))


def knudsen_number_e(container, ion: str = DEFAULT_ION):
    """电子 Knudsen 层数 K_n = λ_mfp / L_Te (>1 ⇒ 非局域/SNB 主导区)。

    L_Te 取现有派生变量 ls_tele (温度标长, cm → m)。
    返回无量纲裸数组。
    """
    require_plasmapy()
    lfp = np.asarray(mean_free_path_profile(container, ion).si.value)
    lT = np.asarray(_si(container, "ls_tele").value)  # ls_tele: cm → .si 后为 m
    with np.errstate(divide="ignore", invalid="ignore"):
        return lfp / np.maximum(lT, 1e-300)


def spitzer_kappa_e(
    container, ion: str = "p+", z_mean: float = DEFAULT_Z_MEAN, model: str = "Braginskii", lnL_method: str = "GMS-6"
):
    """Spitzer/Braginskii 平行电子热导率 κ_e^SH(T_e, n_e)。返回 SI Quantity [W/(m·K)]。

    FL-SH (α=0.08 限流) 对照基准。
    ⚠ 2026.2.0 实测约定:
      - model="Spitzer" 的 SH'53 表只允许 Z ∈ {1, 2, 4, 16, ∞} — Z̄=3 会抛
        PhysicsError (本函数捕获后置 NaN); 需要任意 Z̄ 请用默认 "Braginskii"
        或 "ji-held";
      - ion 必须传 "p+" (输运系数由 Z 单独控制); 传多电荷离子 (如 "Ti 3+")
        会触发内部 Z 推断缺陷 ("3.0 is not an allowed Z value");
      - n_i = n_e/Z̄, Z̄ 由参数 z_mean 给出 (平均电离度, 可取 IONMIX 输出);
      - 库仑对数经 lnL_method (默认 GMS-6) 显式计算后以 coulomb_log_ei 传入 —
        绕开内部 coulomb_log_method="GMS-6" 与 Particle 型 z_mean 的 isnan
        缺陷, 且与 coulomb_log_profile 输出严格一致。
    """
    require_plasmapy()
    Te_q = _si(container, "tele")
    ne_q = _si(container, "nele")
    Te_v = np.atleast_1d(np.asarray(Te_q.value, dtype=float)).ravel()
    ne_v = np.atleast_1d(np.asarray(ne_q.value, dtype=float)).ravel()
    n = max(Te_v.size, ne_v.size)
    Te_v = np.resize(Te_v, n)
    ne_v = np.resize(ne_v, n)

    def _one(t: float, nn: float) -> float:
        try:
            lnL = float(Coulomb_logarithm(t * u.K, nn * u.m**-3, ("e-", ion), z_mean=z_mean, method=lnL_method))
            trans = ClassicalTransport(
                T_e=t * u.K,
                n_e=nn * u.m**-3,
                T_i=t * u.K,
                n_i=nn / z_mean * u.m**-3,
                ion=ion,
                Z=z_mean,
                model=model,
                field_orientation="parallel",
                coulomb_log_ei=lnL,
            )
            return trans.electron_thermal_conductivity.si.value
        except Exception as exc:
            if type(exc).__name__ == "PhysicsError":
                return np.nan
            raise

    if n == 1:
        vals = np.array([_one(float(Te_v[0]), float(ne_v[0]))])
    else:
        vals = np.array([_one(t, nn) for t, nn in zip(Te_v, ne_v)])
    shape = np.shape(Te_q.value) or (n,)
    return (vals * u.W / (u.m * u.K)).reshape(shape)


def saha_zbar(container):
    """Saha 平衡平均电离度 Z̄_bal(n_e, T_e)。返回无量纲 Quantity。

    ⚠ 适用域: 仅作 IONMIX 非平衡 Z̄ 的对照下界; 强耦合 (Γ≳1) 或快速加热区失真。
    """
    require_plasmapy()
    Te = _si(container, "tele")
    ne = _si(container, "nele")
    return ionization_balance(n=ne, T_e=Te)


def quantum_theta_profile(container):
    """电子简并参数 Θ_e = k_B T_e / E_F。返回无量纲裸数组。

    与手写派生变量 Theta_e (electron_degeneracy_parameter) 交叉验证。
    """
    require_plasmapy()
    Te = _si(container, "tele")
    ne = _si(container, "nele")
    return np.asarray(quantum_theta(Te, ne), dtype=float)


def coupling_profile(species_pair=("e-", "p+")):
    """库仑耦合参数 Γ = Z²e²/(a k_B T) 的 PlasmaPy 参考实现（标量接口）。

    注意: PlasmaPy coupling_parameter 为标量/同质网格接口;
    逐网格版本沿用手写派生变量 Gamma_i, 本函数用于常数工况交叉验证。
    """
    require_plasmapy()

    def _gamma(T_K: float, n_m3: float) -> float:
        return float(coupling_parameter(T_K * u.K, n_m3 * u.m**-3, species_pair))

    return _gamma
