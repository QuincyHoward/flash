"""
FLASH Math Test Custom 01 — 自定义数学测试模型
═══════════════════════════════════════════════════

基于 laserslab1d_local_custom.py 的输入参数结构，使用 Python 解析模型
模拟 FLASH 仿真的物理过程，输出 nele, tele 等物理量时间序列。

这是**纯数学测试**，不调用实际 FLASH 二进制。
为后续对接 laserslab1d_local_custom.py 的真实仿真做准备。

优化参数空间 (匹配 laserslab1d_local_custom 的可变参数):
  L0_um:               仿真域半宽 (μm), 暂固定
  sim_targetHeight_um: 靶半宽 (μm),  优化变量
  sim_rhoTarg:         靶密度 (g/cm^3),  优化变量
  peak_power:          激光峰值功率密度 (W/cm^2), 优化变量
  pulse_duration_ns:   脉冲时长 (ns), 优化变量
  rise_fall_ps:        上升/下降沿 (ps), 优化变量
  wavelength_um:       激光波长 (μm), 优化变量

输出:
  results["nele"]    — 电子数密度 (n_time, nx)
  results["tele"]    — 电子温度 (n_time, nx)
  results["time"]    — 时间坐标
  results["x"]       — 空间坐标

用法:
  from flash.test.flash_mathtest_custom01 import FlashMathTestCustom01
  sim = FlashMathTestCustom01(peak_power=1e14, sim_rhoTarg=1.0, sim_targetHeight_um=30)
  results = sim.run()
  print(results["nele"].shape)  # (nt, nx)
"""

import numpy as np
from pathlib import Path
from typing import Dict, Optional, Tuple

# ── 物理常量 ──────────────────────────────────
KB_EV = 8.617333262145e-5  # eV/K
NA = 6.02214076e23  # Avogadro
C_LIGHT = 2.99792458e10  # cm/s


class FlashMathTestCustom01:
    """自定义 FLASH 数学测试 (基于 laserslab1d_local_custom 参数结构)。

    对称域仿真: 靶居中 ([-target_half, target_half])，
    两侧真空。两束激光相向入射。

    Parameters
    ----------
    L0_um : float
        仿真域半宽 (μm), 默认 100
    sim_targetHeight_um : float
        靶半宽 (μm), 默认 30
    sim_rhoTarg : float
        靶初始密度 (g/cm^3), 默认 1.0
    peak_power : float
        激光峰值功率密度 (W/cm^2), 默认 5e14
    pulse_duration_ns : float
        平顶脉冲时长 (ns), 默认 1.0
    rise_fall_ps : float
        上升/下降沿时间 (ps), 默认 40
    wavelength_um : float
        激光波长 (μm), 默认 0.351
    nx : int
        空间网格数, 默认 400
    n_time_steps : int
        时间步数, 默认 200
    """

    def __init__(
        self,
        L0_um: float = 100.0,
        sim_targetHeight_um: float = 30.0,
        sim_rhoTarg: float = 1.0,
        peak_power: float = 5e14,
        pulse_duration_ns: float = 1.0,
        rise_fall_ps: float = 40.0,
        wavelength_um: float = 0.351,
        nx: int = 400,
        n_time_steps: int = 200,
    ):
        self.L0_um = L0_um
        self.sim_targetHeight_um = sim_targetHeight_um
        self.sim_rhoTarg = sim_rhoTarg
        self.peak_power = peak_power
        self.pulse_duration_ns = pulse_duration_ns
        self.rise_fall_ps = rise_fall_ps
        self.wavelength_um = wavelength_um
        self.nx = nx
        self.n_time_steps = n_time_steps

        # 靶材料参数 (polystyrene-imx-008.cn4 近似)
        self.ms_targA = 6.5
        self.ms_targZ = 3.5

        # 派生量
        L0_cm = L0_um * 1e-4
        target_half_cm = sim_targetHeight_um * 1e-4

        # 空间网格 (对称域)
        self.x = np.linspace(-L0_cm, L0_cm, nx)

        # 靶区域 mask
        self.target_mask = np.abs(self.x) <= target_half_cm

        # 真空区域 mask
        self.vacuum_mask = ~self.target_mask

        # 时间网格
        pulse_total_ns = pulse_duration_ns + 2 * rise_fall_ps * 1e-3
        tmax = pulse_total_ns * 1e-9 * 1.2  # 120% 脉冲总长
        self.t = np.linspace(0, tmax, n_time_steps)

        self.results: Dict[str, np.ndarray] = {}

    def run(self) -> Dict[str, np.ndarray]:
        """运行自定义数学测试。

        Returns
        -------
        dict
            keys: dens, tele, tion, trad, nele, time, x
        """
        nx = self.nx
        nt = self.n_time_steps
        x = self.x
        t = self.t
        mask = self.target_mask
        rho0 = self.sim_rhoTarg
        A = self.ms_targA
        Z = self.ms_targZ

        # ── 1. 激光脉冲形状 (梯形脉冲) ──
        rise_s = self.rise_fall_ps * 1e-12
        pulse_s = self.pulse_duration_ns * 1e-9

        times = np.array([0.0, rise_s, pulse_s + rise_s, pulse_s + 2 * rise_s, t[-1]])
        powers = np.array([0.0, self.peak_power, self.peak_power, 0.0, 0.0])

        laser_power = np.interp(t, times, powers, left=0.0, right=0.0)

        # ── 2. 激光吸收 (考虑波长依赖临界密度) ──
        # 临界密度 nc ∝ 1/λ^2
        nc_ratio = (0.351 / max(self.wavelength_um, 0.01)) ** 2

        # 吸收效率: 短波长穿透更深
        absorption = 1.0 - np.exp(-nc_ratio)
        absorbed_power = laser_power * absorption

        # ── 3. 温度演化 (1D 热传导) ──
        tele = np.full((nt, nx), 300.0)  # K (初始室温)
        trad = np.full((nt, nx), 300.0)
        tion = np.full((nt, nx), 300.0)

        # 热传导系数 (cm^2/s)
        D_therm = 1.0

        for i in range(nt):
            if i > 0:
                tele[i] = tele[i - 1].copy()

            # 靶表面加热 (激光沉积在靶两侧)
            if np.any(mask):
                # 找到靶边界
                idx_target = np.where(mask)[0]
                left_edge = idx_target[0]
                right_edge = idx_target[-1]

                # 激光从两侧入射，沉积在靶表面
                heating = absorbed_power[i] / 1.0e14 * 5.0e4  # K

                # 指数衰减进入靶
                skin_depth = 0.1 * (self.wavelength_um / 0.351)  # 趋肤深度 (域分数)
                n_skin = max(1, int(skin_depth * len(idx_target)))

                for edge in [left_edge, right_edge]:
                    if mask[edge]:
                        # 向靶内衰减
                        for j in range(min(n_skin, len(idx_target) // 2)):
                            idx = edge + j if edge == left_edge else edge - j
                            if 0 <= idx < nx:
                                decay = np.exp(-j / n_skin)
                                tele[i, idx] += heating * decay

            # 热传导 (扩散)
            if i > 0:
                d2T = np.zeros(nx)
                d2T[1:-1] = (tele[i - 1, 2:] - 2 * tele[i - 1, 1:-1] + tele[i - 1, :-2]) / ((x[1] - x[0]) ** 2)

                dt = t[1] - t[0] if len(t) > 1 else 1e-12
                tele[i, 1:-1] += D_therm * d2T[1:-1] * dt * 1e-3

            # 温度上限/下限
            tele[i] = np.clip(tele[i], 300.0, 1.0e7)

            # 离子温度
            tion[i] = tele[i] * 0.8

            # 辐射温度
            trad[i] = tele[i] * 0.6

        # ── 4. 密度演化 (激光烧蚀) ──
        dens = np.full((nt, nx), 1e-6, dtype=float)  # 真空
        dens[:, mask] = rho0

        for i in range(1, nt):
            # 靶表面烧蚀: 加热区域密度降低
            pressure = (tele[i] / 1.0e4) ** 1.5
            dens[i, mask] = rho0 / (1.0 + 0.05 * pressure[mask])
            dens[i, mask] = np.clip(dens[i, mask], rho0 * 0.01, rho0 * 2.0)

        # ── 5. 电离度 (Zbar) ──
        tele_eV = tele / 11605.0  # K -> eV
        I_eV = 6.0 * (Z**2) / (A ** (1 / 3))  # 近似电离能

        zbar = Z * (1.0 - np.exp(-tele_eV / max(I_eV, 1.0)))
        zbar = np.clip(zbar, 0.0, Z)

        # ── 6. 电子数密度 nele = rho * Zbar * NA / A ──
        nele = dens * zbar * NA / A

        # ── 整理结果 ──
        self.results = {
            "dens": dens,  # (nt, nx) 质量密度
            "tele": tele,  # (nt, nx) 电子温度
            "tion": tion,  # (nt, nx) 离子温度
            "trad": trad,  # (nt, nx) 辐射温度
            "zbar": zbar,  # (nt, nx) 平均电离度
            "nele": nele,  # (nt, nx) 电子数密度
            "laser_power": laser_power,  # (nt,) 激光功率
            "time": t,  # (nt,)
            "x": x,  # (nx,)
        }

        return self.results

    def compute_objective(
        self,
        target_center_cm: float = 0.0,
        spatial_half_width_cm: float = 5e-4,
        time_window_s: float = 300e-12,
    ) -> float:
        """计算 nele*tele 时空平均目标函数值。

        匹配用户真实优化目标:
        "在靶材中心范围 +/- 5 um 内, 300ps 窗口内,
         nele*tele 的时间积分平均最大化"

        Parameters
        ----------
        target_center_cm : float
            靶中心位置 (cm), 对称域为 0.0
        spatial_half_width_cm : float
            空间窗口半宽 (cm), 默认 5e-4 (5 um)
        time_window_s : float
            时间窗口 (s), 默认 300e-12 (300 ps)

        Returns
        -------
        float
            nele*tele 时间平均 (negated for GA minimization)
        """
        if not self.results:
            self.run()

        nele = self.results["nele"]
        tele = self.results["tele"]
        t = self.results["time"]
        x = self.results["x"]

        # 空间窗口
        x_mask = (x >= target_center_cm - spatial_half_width_cm) & (x <= target_center_cm + spatial_half_width_cm)
        if not np.any(x_mask):
            return 1e30

        # 时间窗口
        t_mask = t <= time_window_s
        if not np.any(t_mask):
            return 1e30

        # nele * tele
        product = nele * tele

        # 空间平均
        spatial_avg = np.mean(product[:, x_mask], axis=1)

        # 时间积分
        t_valid = t[t_mask]
        s_valid = spatial_avg[t_mask]

        if len(t_valid) < 2:
            return 1e30

        time_integral = np.trapezoid(s_valid, t_valid)
        time_avg = time_integral / (t_valid[-1] - t_valid[0])

        # 返回负值 (GA 默认最小化)
        return -float(time_avg)

    def get_summary(self) -> Dict:
        """获取运行摘要。"""
        if not self.results:
            return {"error": "No results. Run first."}
        return {
            "peak_tele_K": float(np.max(self.results["tele"])),
            "peak_tele_eV": float(np.max(self.results["tele"]) / 11605.0),
            "peak_nele": float(np.max(self.results["nele"])),
            "avg_final_dens": float(np.mean(self.results["dens"][-1, :])),
            "L0_um": self.L0_um,
            "target_um": self.sim_targetHeight_um,
            "rho0": self.sim_rhoTarg,
            "peak_power": self.peak_power,
        }


# ── 简化目标函数包装器 (用于遗传算法) ──


def make_flash_custom_objective(
    param_names: Optional[list] = None,
    default_params: Optional[Dict] = None,
) -> callable:
    """创建用于 GA 优化的 FLASH custom 目标函数。

    返回的 callable 自动跟踪调用次数 (上限 500 次)。

    Returns
    -------
    (objective_fn, sim_instance)
    """
    _call_count = [0]
    MAX_CALLS = 500

    # 默认参数
    params = {
        "L0_um": 100.0,
        "sim_targetHeight_um": 30.0,
        "sim_rhoTarg": 1.0,
        "peak_power": 5e14,
        "pulse_duration_ns": 1.0,
        "rise_fall_ps": 40.0,
        "wavelength_um": 0.351,
    }
    if default_params:
        params.update(default_params)

    def objective(ga_params: Dict[str, float]) -> float:
        nonlocal _call_count
        _call_count[0] += 1

        if _call_count[0] > MAX_CALLS:
            raise RuntimeError(f"FLASH Custom Math Test: call limit ({MAX_CALLS}) exceeded")

        # 合并参数
        sim_params = dict(params)
        for k, v in ga_params.items():
            sim_params[k] = v

        # 提取参数
        sim = FlashMathTestCustom01(
            L0_um=sim_params.get("L0_um", 100.0),
            sim_targetHeight_um=sim_params.get("sim_targetHeight_um", 30.0),
            sim_rhoTarg=sim_params.get("sim_rhoTarg", 1.0),
            peak_power=sim_params.get("peak_power", 5e14),
            pulse_duration_ns=sim_params.get("pulse_duration_ns", 1.0),
            rise_fall_ps=sim_params.get("rise_fall_ps", 40.0),
            wavelength_um=sim_params.get("wavelength_um", 0.351),
        )

        try:
            return sim.compute_objective(
                target_center_cm=0.0,
                spatial_half_width_cm=5e-4,
                time_window_s=300e-12,
            )
        except Exception as exc:
            return 1e30  # 失败 → 坏分数

    # 附加信息
    objective.call_count = _call_count  # 可查询调用次数
    objective.reset = lambda: _call_count.__setitem__(0, 0)

    return objective, FlashMathTestCustom01()


# ── 自测 ──
if __name__ == "__main__":
    print("FLASH Math Test Custom 01 — 自测")
    print("=" * 50)

    sim = FlashMathTestCustom01(
        peak_power=1e14,
        sim_rhoTarg=1.0,
        sim_targetHeight_um=30,
    )
    results = sim.run()

    print(f"  输出形状:")
    for key in ["nele", "tele", "dens", "time", "x"]:
        if key in results:
            arr = results[key]
            print(f"    {key}: {arr.shape}")

    obj = sim.compute_objective()
    print(f"\n  目标函数值 (nele*tele 时间平均): {-obj:.6e}")

    summary = sim.get_summary()
    print(f"\n  摘要:")
    for k, v in summary.items():
        print(f"    {k}: {v}")

    print("\n  自测完成 ✓")
