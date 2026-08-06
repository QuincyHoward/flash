"""
FLASH 数学测试函数
═══════════════════

支持 1D (默认) / 2D / 3D 仿真，
多模态输入，输出物理量时间序列到 HDF5。

功能:
  - LaserSlabCa1D: 1D 快速测试 (Ca = Cartesian 笛卡尔坐标系)
  - FlashMathTest: 通用数学测试框架
  - 空壳: input_gen_1d/2d/3d, run_config, data_analysis

命名约定:
  LaserSlab + Ca(Cartesian) + 1D — Ca 表示笛卡尔坐标系，非化学元素钙
  同理: Cy(Cylindrical 柱坐标), Sp(Spherical 球坐标)

用法:
  from flash.math_test import LaserSlabCa1D, FlashMathTest

  tester = LaserSlabCa1D()
  result = tester.run()
  tester.save_hdf5("result.h5")
"""

import numpy as np
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

# ── 维度枚举 ──────────────────────────────────


class SimDimension(Enum):
    D1 = 1
    D2 = 2
    D3 = 3


# ── 脉冲形状 ──────────────────────────────────


class PulseShape(Enum):
    SQUARE = "square"
    TRIANGLE = "triangle"
    GAUSSIAN = "gaussian"
    TRAPEZOID = "trapezoid"


# ── 多模态输入 ────────────────────────────────


@dataclass
class MultimodalInput:
    """多模态仿真输入。"""

    # 激光参数
    wavelength_nm: float = 351.0  # 波长 (nm), 默认 3ω = 351nm
    pulse_shape: PulseShape = PulseShape.GAUSSIAN
    pulse_duration_s: float = 5.0e-9
    peak_power_w_cm2: float = 1.0e13

    # 实验配置
    target_material: str = "CH"  # 靶材料 (Ca = Cartesian 几何, 非钙元素)
    target_z: int = 6  # 靶主要成分核电荷数 (C=6 for CH)
    target_a: float = 12.0  # 靶主要成分原子质量 (C=12 for CH)
    target_density_g_cm3: float = 1.0  # 固体密度 (g/cm³)
    target_thickness_cm: float = 0.01  # 靶厚度 (cm)

    # 目标物理量
    output_vars: List[str] = field(
        default_factory=lambda: ["dens", "tele", "nele", "tion", "trad", "zbar", "shock_front"]
    )

    # 网格
    dimension: SimDimension = SimDimension.D1
    nx: int = 400
    ny: int = 1  # 1D/2D/3D
    nz: int = 1  # 1D/2D/3D
    domain_x_cm: float = 0.1
    domain_y_cm: float = 0.0  # 1D: 0
    domain_z_cm: float = 0.0  # 1D: 0

    # 时间
    t_max_s: float = 1.0e-10
    n_time_steps: int = 100

    # 输出
    output_path: str = "flash_math_test.h5"
    save_hdf5: bool = True


# ── 物理常量 ──────────────────────────────────

KB_EV = 8.617333262145e-5  # Boltzmann constant (eV/K)
C_LIGHT = 2.99792458e10  # Speed of light (cm/s)
H_PLANCK_EV = 4.135667696e-15  # Planck constant (eV·s)
A_U = 1.66053906660e-24  # Atomic mass unit (g)


# ── LaserSlabCa1D 快速测试 ─────────────────


class LaserSlabCa1D:
    """LaserSlab Cartesian 1D 快速测试。

    Ca = Cartesian (笛卡尔坐标系), 不是化学元素钙。
    同理: Cy = Cylindrical (柱坐标), Sp = Spherical (球坐标)。

    使用简化的物理模型模拟激光驱动平板靶的 1D 演化，
    输出 dens, tele, nele, tion, trad, zbar, shock_front 时间序列。
    靶材料通过构造参数独立配置，默认 CH (塑料)。
    """

    def __init__(
        self,
        wavelength_nm: float = 351.0,
        peak_power_w_cm2: float = 1.0e13,
        pulse_duration_s: float = 5.0e-9,
        nx: int = 400,
        x_max_cm: float = 0.1,
        n_time_steps: int = 100,
        output_path: str = "laserslab_ca1d.h5",
        # 靶材料参数 (独立于几何坐标系)
        target_material: str = "CH",
        target_z: int = 6,
        target_a: float = 12.0,
        rho0: float = 1.0,
    ):
        self.wavelength_nm = wavelength_nm
        self.peak_power = peak_power_w_cm2
        self.pulse_duration = pulse_duration_s
        self.nx = nx
        self.x_max = x_max_cm
        self.n_time = n_time_steps
        self.output_path = output_path

        # 靶材料参数 (与几何无关, Ca = Cartesian 几何)
        self.target_material = target_material
        self.Z = target_z
        self.A = target_a
        self.rho0 = rho0  # g/cm³
        self.T0 = 300.0  # K (初始温度)

        # 网格
        self.x = np.linspace(0, self.x_max, self.nx)
        self.dx = self.x_max / (self.nx - 1)

        # 时间
        self.t = np.linspace(0, self.pulse_duration * 2, self.n_time)

        # 结果存储
        self.results: Dict[str, np.ndarray] = {}

    def run(self) -> Dict[str, np.ndarray]:
        """运行 1D 模拟 (解析模型)。

        Returns:
            {物理量名: ndarray (n_time, nx)}
        """
        nx, nt = self.nx, self.n_time
        x = self.x
        t = self.t

        # 1. 激光功率密度时间序列 (高斯脉冲)
        t_norm = (t - self.pulse_duration) / (self.pulse_duration / 2.5)
        laser_power = self.peak_power * np.exp(-0.5 * t_norm**2)
        laser_power[t < 0] = 0.0
        laser_power[t > 2 * self.pulse_duration] = 0.0

        # 2. 吸收深度 (随温度变化的临界密度)
        # 简化: 假设吸收深度与 laser_power^0.5 成正比
        absorb_depth = 1.0e-4 * (laser_power / self.peak_power + 0.01) ** 0.5
        absorb_depth = np.clip(absorb_depth, 1e-6, self.x_max)

        # 3. 温度演化 (热传导简化模型)
        tele = np.zeros((nt, nx))
        trad = np.zeros((nt, nx))

        for i in range(nt):
            # 表面加热
            source_strength = laser_power[i] / 1.0e13 * np.exp(-x / (absorb_depth[i] + 1e-6))
            tele[i, :] = self.T0 + 1.0e4 * source_strength

            # 热传导 (扩散)
            if i > 0:
                d2T = np.zeros(nx)
                d2T[1:-1] = (tele[i - 1, 2:] - 2 * tele[i - 1, 1:-1] + tele[i - 1, :-2]) / self.dx**2
                tele[i, 1:-1] += 0.01 * d2T[1:-1] * (t[1] - t[0])

            tele[i, :] = np.clip(tele[i, :], self.T0, 1.0e6)
            trad[i, :] = tele[i, :] * 0.8  # 辐射温度 ~ 0.8 * Te

        # 4. 密度演化 (热膨胀)
        dens = np.zeros((nt, nx))
        gamma = 5.0 / 3.0
        for i in range(nt):
            # 压力 ~ tele^1.5
            pressure = (tele[i, :] / 1.0e4) ** 1.5
            dens[i, :] = self.rho0 / (1.0 + 0.1 * pressure)
            dens[i, :] = np.clip(dens[i, :], self.rho0 * 0.01, self.rho0 * 2.0)

        # 5. 电离 (Saha 简化)
        zbar = np.zeros((nt, nx))
        for i in range(nt):
            T_eV = tele[i, :] / 11605.0  # K → eV
            # 简化 Saha: Z* ~ Z * (1 - exp(-T_eV / I_eV))
            I_eV = 6.0 * (self.Z**2) / (self.A ** (1 / 3))  # 近似电离能
            zbar[i, :] = self.Z * (1.0 - np.exp(-T_eV / (I_eV + 1.0)))
            zbar[i, :] = np.clip(zbar[i, :], 0.0, self.Z)

        # 6. 电子温度/离子温度
        tion = tele * 0.7  # Ti ~ 0.7 Te (非平衡)
        nele = dens * zbar * 6.022e23 / self.A  # ne = rho * Z* * Na / A

        # 7. 冲击前沿位置
        shock_front = np.zeros(nt)
        shock_speed = 1.0e5  # cm/s (近似)
        for i in range(nt):
            shock_front[i] = min(shock_speed * t[i], self.x_max)
            # 找到密度跳跃位置
            ddens = np.diff(dens[i, :])
            if np.any(np.abs(ddens) > 0.01 * self.rho0):
                idx = np.argmax(np.abs(ddens))
                shock_front[i] = x[idx]

        # 存储
        self.results = {
            "dens": dens,
            "tele": tele,
            "tion": tion,
            "trad": trad,
            "zbar": zbar,
            "nele": nele,
            "shock_front": shock_front,  # 1D: (n_time,)
            "laser_power": laser_power,  # (n_time,)
            "time": t,  # (n_time,)
            "x": x,  # (nx,)
        }
        return self.results

    def save_hdf5(self, path: Optional[str] = None) -> str:
        """保存结果为 HDF5。

        Args:
            path: 输出路径 (None = 使用 self.output_path)

        Returns:
            输出路径
        """
        out = Path(path or self.output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        try:
            import h5py

            with h5py.File(out, "w") as f:
                # 元数据
                meta = f.create_group("metadata")
                meta.attrs["wavelength_nm"] = self.wavelength_nm
                meta.attrs["peak_power_w_cm2"] = self.peak_power
                meta.attrs["pulse_duration_s"] = self.pulse_duration
                meta.attrs["nx"] = self.nx
                meta.attrs["x_max_cm"] = self.x_max
                meta.attrs["n_time"] = self.n_time
                meta.attrs["target_material"] = self.target_material
                meta.attrs["Z"] = self.Z
                meta.attrs["A"] = self.A
                meta.attrs["geometry"] = "Cartesian"

                # 坐标
                f.create_dataset("time", data=self.t)
                f.create_dataset("x", data=self.x)

                # 物理量 (n_time, nx)
                for key in ["dens", "tele", "tion", "trad", "zbar", "nele"]:
                    if key in self.results:
                        f.create_dataset(key, data=self.results[key])

                # 冲击前沿 (n_time,)
                if "shock_front" in self.results:
                    f.create_dataset("shock_front", data=self.results["shock_front"])

                # 激光功率 (n_time,)
                if "laser_power" in self.results:
                    f.create_dataset("laser_power", data=self.results["laser_power"])

            print(f"[LaserSlabCa1D] HDF5 saved: {out}")
            return str(out)

        except ImportError:
            # 无 h5py: 保存为 npz
            np_path = out.with_suffix(".npz")
            np.savez(np_path, **self.results)
            print(f"[LaserSlabCa1D] h5py not found, saved as NPZ: {np_path}")
            return str(np_path)

    def get_summary(self) -> Dict[str, Any]:
        """获取结果摘要。"""
        if not self.results:
            return {"error": "No results. Run first."}
        return {
            "peak_tele_eV": float(np.max(self.results["tele"]) / 11605.0),
            "avg_final_dens": float(np.mean(self.results["dens"][-1, :])),
            "max_zbar": float(np.max(self.results["zbar"])),
            "shock_front_final_cm": float(self.results["shock_front"][-1]),
            "n_time": self.n_time,
            "nx": self.nx,
        }


# ── FlashMathTest 通用框架 ─────────────────────


class FlashMathTest:
    """FLASH 数学测试通用框架 (1D/2D/3D)。"""

    def __init__(self, config: Optional[MultimodalInput] = None):
        self.config = config or MultimodalInput()
        self.results: Dict[str, np.ndarray] = {}
        self.dimension = self.config.dimension

    def run(self) -> Dict[str, np.ndarray]:
        """运行仿真 (根据 dimension 分发)。"""
        if self.dimension == SimDimension.D1:
            return self._run_1d()
        elif self.dimension == SimDimension.D2:
            return self._run_2d_shell()
        elif self.dimension == SimDimension.D3:
            return self._run_3d_shell()
        else:
            raise ValueError(f"Unknown dimension: {self.dimension}")

    def _run_1d(self) -> Dict[str, np.ndarray]:
        """1D 仿真 (解析模型)。"""
        cfg = self.config
        nx = cfg.nx
        nt = cfg.n_time_steps
        x = np.linspace(0, cfg.domain_x_cm, nx)
        t = np.linspace(0, cfg.t_max_s, nt)

        # 激光功率 (高斯)
        t0 = cfg.pulse_duration_s
        P0 = cfg.peak_power_w_cm2
        laser = P0 * np.exp(-0.5 * ((t - t0) / (t0 / 2.5)) ** 2)
        laser[t < 0] = 0.0
        laser[t > 2 * t0] = 0.0

        # 温度
        tele = np.zeros((nt, nx))
        for i in range(nt):
            depth = 1e-4 * (laser[i] / P0 + 0.01) ** 0.5
            tele[i, :] = cfg.target_density_g_cm3 * 1e3 + 1e4 * laser[i] / P0 * np.exp(-x / (depth + 1e-6))
            tele[i, :] = np.clip(tele[i, :], 300, 1e6)

        # 密度
        dens = cfg.target_density_g_cm3 * np.ones((nt, nx))
        for i in range(nt):
            dens[i, :] /= 1.0 + 0.1 * (tele[i, :] / 1e4) ** 1.5
            dens[i, :] = np.clip(dens[i, :], cfg.target_density_g_cm3 * 0.01, cfg.target_density_g_cm3 * 2)

        # 其他量
        zbar = self.config.target_z * (1.0 - np.exp(-tele / 11605.0 / 10.0))
        zbar = np.clip(zbar, 0, self.config.target_z)

        self.results = {
            "time": t,
            "x": x,
            "dens": dens,
            "tele": tele,
            "tion": tele * 0.7,
            "trad": tele * 0.8,
            "zbar": zbar,
            "nele": dens * zbar * 6.022e23 / self.config.target_a,
            "shock_front": np.minimum(1e5 * t, cfg.domain_x_cm),
            "laser_power": laser,
        }
        return self.results

    def _run_2d_shell(self) -> Dict[str, np.ndarray]:
        """2D 仿真空壳 (待实现)。"""
        print("[FlashMathTest] 2D mode: shell only, returning zeros.")
        nt = self.config.n_time_steps
        nx, ny = self.config.nx, max(self.config.ny, 2)
        shape = (nt, nx, ny)
        self.results = {k: np.zeros(shape) for k in self.config.output_vars}
        self.results["time"] = np.linspace(0, self.config.t_max_s, nt)
        return self.results

    def _run_3d_shell(self) -> Dict[str, np.ndarray]:
        """3D 仿真空壳 (待实现)。"""
        print("[FlashMathTest] 3D mode: shell only, returning zeros.")
        nt = self.config.n_time_steps
        nx = self.config.nx
        ny = max(self.config.ny, 2)
        nz = max(self.config.nz, 2)
        shape = (nt, nx, ny, nz)
        self.results = {k: np.zeros(shape) for k in self.config.output_vars}
        self.results["time"] = np.linspace(0, self.config.t_max_s, nt)
        return self.results

    def save_hdf5(self, path: Optional[str] = None) -> str:
        """保存 HDF5。"""
        out = Path(path or self.config.output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        try:
            import h5py

            with h5py.File(out, "w") as f:
                # 元数据
                meta = f.create_group("metadata")
                meta.attrs["dimension"] = self.dimension.value
                meta.attrs["target_material"] = self.config.target_material
                meta.attrs["wavelength_nm"] = self.config.wavelength_nm

                # 坐标
                f.create_dataset("time", data=self.results["time"])
                f.create_dataset("x", data=np.linspace(0, self.config.domain_x_cm, self.config.nx))
                if self.dimension.value >= 2:
                    f.create_dataset("y", data=np.linspace(0, self.config.domain_y_cm, max(self.config.ny, 1)))
                if self.dimension.value >= 3:
                    f.create_dataset("z", data=np.linspace(0, self.config.domain_z_cm, max(self.config.nz, 1)))

                # 物理量
                for key in self.config.output_vars:
                    if key in self.results:
                        f.create_dataset(key, data=self.results[key])

            print(f"[FlashMathTest] HDF5 saved: {out}")
            return str(out)

        except ImportError:
            np_path = out.with_suffix(".npz")
            np.savez(np_path, **self.results)
            print(f"[FlashMathTest] h5py not found, saved as NPZ: {np_path}")
            return str(np_path)


# ── 空壳函数 ──────────────────────────────────


def input_gen_1d(
    output_par: str = "flash_1d.par",
    wavelength_nm: float = 351.0,
    peak_power: float = 1e13,
    nx: int = 400,
    **kwargs,
) -> str:
    """1D 仿真输入文件生成 (空壳)。

    Args:
        output_par: 输出 .par 文件路径
        wavelength_nm: 激光波长 (nm)
        peak_power: 峰值功率密度 (W/cm²)
        nx: 网格点数

    Returns:
        输出文件路径
    """
    print(f"[input_gen_1d] Shell: would generate {output_par}")
    print(f"  wavelength={wavelength_nm}nm, peak_power={peak_power:.2e} W/cm², nx={nx}")
    # TODO: 实现 1D .par 文件生成
    return output_par


def input_gen_2d(output_par: str = "flash_2d.par", **kwargs) -> str:
    """2D 仿真输入文件生成 (空壳)。"""
    print(f"[input_gen_2d] Shell: would generate {output_par}")
    print("  TODO: implement 2D mesh generation")
    return output_par


def input_gen_3d(output_par: str = "flash_3d.par", **kwargs) -> str:
    """3D 仿真输入文件生成 (空壳)。"""
    print(f"[input_gen_3d] Shell: would generate {output_par}")
    print("  TODO: implement 3D mesh generation")
    return output_par


def run_config_local(
    par_file: str = "flash.par",
    flash_exe: str = "./flash4",
    nprocs: int = 4,
) -> Dict[str, Any]:
    """本地运行配置 (空壳)。

    Returns:
        {"success": bool, "output_dir": str, ...}
    """
    print(f"[run_config_local] Shell: would run {flash_exe} with {par_file}")
    print("  TODO: implement local FLASH execution")
    return {"success": False, "shell": True, "par_file": par_file}


def run_config_remote(
    par_file: str,
    ssh_credential: str = "flash_ssh",
    slurm_partition: str = "cpu",
    nprocs: int = 32,
) -> Dict[str, Any]:
    """远程超算运行配置 (空壳)。"""
    print(f"[run_config_remote] Shell: would submit to {ssh_credential}")
    print("  TODO: implement remote SBATCH submission")
    return {"success": False, "shell": True}


def analyze_critical_density(
    hdf5_path: str,
    output_dir: str = "analysis",
) -> Dict[str, Any]:
    """临界密度面分析 (空壳)。

    Returns:
        {"critical_density_surface": ndarray, ...}
    """
    print(f"[analyze_critical_density] Shell: would analyze {hdf5_path}")
    print("  TODO: implement critical density surface extraction")
    return {"shell": True, "output_dir": output_dir}


def extract_shock_front(
    hdf5_path: str,
    var_name: str = "dens",
    threshold: float = 0.5,
) -> np.ndarray:
    """冲击前沿提取 (空壳)。

    Returns:
        shock_front_position (n_time,)
    """
    print(f"[extract_shock_front] Shell: would extract from {hdf5_path}, var={var_name}")
    print("  TODO: implement shock front position extraction")
    return np.array([])


# ── 便捷函数 ──────────────────────────────────


def quick_test_1d(
    wavelength_nm: float = 351.0,
    peak_power: float = 1e13,
    output_path: str = "quick_test_1d.h5",
) -> Dict[str, Any]:
    """便捷函数: 1D 快速测试。

    Returns:
        结果摘要字典
    """
    tester = LaserSlabCa1D(
        wavelength_nm=wavelength_nm,
        peak_power_w_cm2=peak_power,
        output_path=output_path,
    )
    results = tester.run()
    tester.save_hdf5()
    return tester.get_summary()


def quick_test_material(
    material: str = "CH",
    z: int = 6,
    a: float = 12.0,
    dimension: int = 1,
    output_path: str = "material_test.h5",
) -> Dict[str, Any]:
    """便捷函数: 不同材料的快速测试。"""
    dim = SimDimension(dimension)
    cfg = MultimodalInput(
        target_material=material,
        target_z=z,
        target_a=a,
        dimension=dim,
        output_path=output_path,
    )
    tester = FlashMathTest(cfg)
    results = tester.run()
    tester.save_hdf5()
    return {"material": material, "dimension": dimension, "n_vars": len(results)}


if __name__ == "__main__":
    print("FLASH Math Test Demo")
    print("=" * 40)

    # 1D 快速测试
    print("\n[1/2] LaserSlabCa1D 1D test...")
    summary = quick_test_1d()
    print(f"  Peak Te (eV): {summary['peak_tele_eV']:.2f}")
    print(f"  Max Z*: {summary['max_zbar']:.2f}")

    # 2D 空壳测试
    print("\n[2/2] 2D shell test...")
    input_gen_2d("flash_2d.par")
    analyze_critical_density("dummy.h5")
