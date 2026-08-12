"""
flash_hdf5.py — FLASH HDF5 文件的底层读取与解析
================================================================

FLASH 使用 PARAMESH AMR 库，其 HDF5 输出具有以下特点：
  - 所有数据集在根组 (root group) 下平铺，无子组
  - 物理量数组形状: (nblocks, Nz, Ny, Nx)    ← C/h5py 维度顺序
  - 边界框: (nblocks, 3, 2) — 每个块在 x/y/z 方向的 min/max
  - checkpoint 文件: float64, 完整变量集 (~44 个)
  - plot 文件: float32, 部分变量集 (~9 个)
  - "unknown names" 数据集: 记录物理变量名到索引的映射
  - "real scalars" 中记录仿真时间 time/dt
  - "real runtime parameters" 中记录 ed_time_N_M / ed_power_N_M 等激光参数

== yt 风格数据提取 (extract_var_yt_style) ==

在超算环境中通常无法安装 yt 库，因此提供了纯 h5py 的 yt 风格数据提取
方法 extract_var_yt_style()，使用与 yt 相同的 AMR 提取逻辑:

1. 叶节点筛选:
   - 读取 node_type 数据集，只使用 node_type == 1 的块（叶节点）
   - 在 PARAMESH AMR 中，叶节点是最终参与物理计算的块
   - 父节点 (node_type > 1) 的数据被子节点覆盖，不应使用

2. 坐标重建:
   - 使用 bounding box 数据重建每个块的单元中心坐标
   - 对每个叶节点块，按 (Nx, Ny, Nz) 生成线性网格

3. 去重:
   - AMR 块在边界处有重叠单元
   - 使用 (x), (x,y), (x,y,z) 元组去重，保留每个空间位置的一个值

4. 坐标系统自动检测:
   - 自动检测 Cartesian / Cylindrical 坐标系统
   - 基于 z 轴范围是否 ≈ 2π 或 ≈ 1° 判断

支持的组合:
  - cartesian_1d  (1D Cartesian)           ✅ 已实现
  - cartesian_3d  (3D Cartesian)           ✅ 已实现
  - cylindrical_rz (2D R-Z Cylindrical)     ✅ 已实现
  - cartesian_2d  (2D Cartesian)            ❌ 未实现（会抛错误）
  - cylindrical_3d (3D R-θ-Z Cylindrical)   ❌ 未实现（会抛错误）
  - cylindrical_1d (1D Cylindrical)         ❌ 未实现（会抛错误）
  - spherical_*  (球坐标)                   ❌ 未实现（会抛错误）
"""

import numpy as np
import h5py
from pathlib import Path
import re


# ═══════════════════════════════════════════════════════════════
#  data_config — 变量元信息注册表
# ═══════════════════════════════════════════════════════════════
# 格式: 变量名 -> {unit, unit_si, to_si, description, category, depends}
#
#   unit:      常用单位（字符串）
#   unit_si:   SI 单位
#   to_si:     从常用单位转换到 SI 的系数（乘数）
#   description:  物理意义描述
#   category:  "raw" | "derived"  (原始变量/派生变量)
#   depends:   派生变量依赖的变量列表（用于自动计算）
#   formula:   计算公式描述 (仅 derived)
# ═══════════════════════════════════════════════════════════════

NA = 6.02214076e23  # 阿伏伽德罗数 [1/mol]

DATA_CONFIG = {
    # ── 原始 FLASH 变量 ──────────────────────────────────────
    "dens": {
        "unit": "g/cm^3", "unit_si": "kg/m^3", "to_si": 1000.0,
        "description": "Mass density", "category": "raw",
    },
    "tele": {
        "unit": "K", "unit_si": "K", "to_si": 1.0,
        "description": "Electron temperature", "category": "raw",
    },
    "tion": {
        "unit": "K", "unit_si": "K", "to_si": 1.0,
        "description": "Ion temperature", "category": "raw",
    },
    "trad": {
        "unit": "K", "unit_si": "K", "to_si": 1.0,
        "description": "Radiation temperature", "category": "raw",
    },
    "temp": {
        "unit": "K", "unit_si": "K", "to_si": 1.0,
        "description": "Temperature (general)", "category": "raw",
    },
    "pres": {
        "unit": "dyne/cm^2", "unit_si": "Pa", "to_si": 0.1,
        "description": "Pressure", "category": "raw",
    },
    "velx": {
        "unit": "cm/s", "unit_si": "m/s", "to_si": 0.01,
        "description": "x-direction velocity", "category": "raw",
    },
    "vely": {
        "unit": "cm/s", "unit_si": "m/s", "to_si": 0.01,
        "description": "y-direction velocity", "category": "raw",
    },
    "velz": {
        "unit": "cm/s", "unit_si": "m/s", "to_si": 0.01,
        "description": "z-direction velocity", "category": "raw",
    },
    "depo": {
        "unit": "erg/cm^3/s", "unit_si": "W/m^3", "to_si": 0.1,
        "description": "Laser energy deposition rate", "category": "raw",
    },
    "eint": {
        "unit": "erg/g", "unit_si": "J/kg", "to_si": 0.0001,
        "description": "Internal energy", "category": "raw",
    },
    "erad": {
        "unit": "erg/cm^3", "unit_si": "J/m^3", "to_si": 0.1,
        "description": "Radiation energy density", "category": "raw",
    },
    "ye": {
        "unit": "1/mol", "unit_si": "1/mol", "to_si": 1.0,
        "description": "Electron abundance (mol e- per g matter)", "category": "raw",
    },
    "sumy": {
        "unit": "1/mol", "unit_si": "1/mol", "to_si": 1.0,
        "description": "Ion abundance sum (mol ions per g matter)", "category": "raw",
    },
    "cham": {
        "unit": "1", "unit_si": "1", "to_si": 1.0,
        "description": "CH ablator mass fraction", "category": "raw",
    },
    "targ": {
        "unit": "1", "unit_si": "1", "to_si": 1.0,
        "description": "DT target mass fraction", "category": "raw",
    },
    "shok": {
        "unit": "1", "unit_si": "1", "to_si": 1.0,
        "description": "Shock indicator", "category": "raw",
    },
    "game": {
        "unit": "1", "unit_si": "1", "to_si": 1.0,
        "description": "Electron adiabatic index gamma_e", "category": "raw",
    },
    "gamc": {
        "unit": "1", "unit_si": "1", "to_si": 1.0,
        "description": "Coupled adiabatic index gamma_c", "category": "raw",
    },
    "lase": {
        "unit": "W/cm^2", "unit_si": "W/m^2", "to_si": 1e4,
        "description": "Laser intensity (ray tracing)", "category": "raw",
    },
    "eele": {
        "unit": "erg/g", "unit_si": "J/kg", "to_si": 0.0001,
        "description": "Electron internal energy", "category": "raw",
    },
    "eion": {
        "unit": "erg/g", "unit_si": "J/kg", "to_si": 0.0001,
        "description": "Ion internal energy", "category": "raw",
    },
    "pele": {
        "unit": "dyne/cm^2", "unit_si": "Pa", "to_si": 0.1,
        "description": "Electron pressure", "category": "raw",
    },
    "pion": {
        "unit": "dyne/cm^2", "unit_si": "Pa", "to_si": 0.1,
        "description": "Ion pressure", "category": "raw",
    },
    "prad": {
        "unit": "dyne/cm^2", "unit_si": "Pa", "to_si": 0.1,
        "description": "Radiation pressure", "category": "raw",
    },
    "cond": {
        "unit": "erg/cm/K/s", "unit_si": "W/m/K", "to_si": 0.01,
        "description": "Thermal conductivity (FLASH built-in)", "category": "raw",
    },
    "emis": {
        "unit": "erg/cm^3/s", "unit_si": "W/m^3", "to_si": 0.1,
        "description": "Radiation emissivity", "category": "raw",
    },
    "ener": {
        "unit": "erg/g", "unit_si": "J/kg", "to_si": 0.0001,
        "description": "Total energy", "category": "raw",
    },
    # ── 派生变量（由 data_calculator 计算产生）────────────
    "dens_targ": {
        "unit": "g/cm^3", "unit_si": "kg/m^3", "to_si": 1000.0,
        "description": "Target component density = dens * targ",
        "category": "derived", "depends": ["dens", "targ"],
        "formula": "dens * targ",
    },
    "dens_cham": {
        "unit": "g/cm^3", "unit_si": "kg/m^3", "to_si": 1000.0,
        "description": "Ablator component density = dens * cham",
        "category": "derived", "depends": ["dens", "cham"],
        "formula": "dens * cham",
    },
    "dens_shld": {
        "unit": "g/cm^3", "unit_si": "kg/m^3", "to_si": 1000.0,
        "description": "Shield component density = dens * shld (if present)",
        "category": "derived", "depends": ["dens", "shld"],
        "formula": "dens * shld",
    },
    "dens_samp": {
        "unit": "g/cm^3", "unit_si": "kg/m^3", "to_si": 1000.0,
        "description": "Sample component density = dens * samp (if present)",
        "category": "derived", "depends": ["dens", "samp"],
        "formula": "dens * samp",
    },
    "nele": {
        "unit": "1/cm^3", "unit_si": "1/m^3", "to_si": 1e6,
        "description": "Electron number density = ye * dens * NA",
        "category": "derived", "depends": ["ye", "dens"],
        "formula": "ye * dens * NA",
    },
    "nion": {
        "unit": "1/cm^3", "unit_si": "1/m^3", "to_si": 1e6,
        "description": "Ion number density = sumy * dens * NA",
        "category": "derived", "depends": ["sumy", "dens"],
        "formula": "sumy * dens * NA",
    },
    "ls_nele": {
        "unit": "cm", "unit_si": "m", "to_si": 0.01,
        "description": "Electron density gradient scale length = nele / |grad(nele)|",
        "category": "derived", "depends": ["nele"],
        "formula": "nele / |grad(nele)|",
    },
    "ls_tele": {
        "unit": "cm", "unit_si": "m", "to_si": 0.01,
        "description": "Electron temp. gradient scale length = tele / |grad(tele)|",
        "category": "derived", "depends": ["tele"],
        "formula": "tele / |grad(tele)|",
    },
}

# 别名映射：原始 FLASH 中可能的其他变量名
VAR_ALIASES = {
    "targ": ["target"],
    "cham": ["ch", "ablator"],
    "shld": ["shield", "shielding"],
    "samp": ["sample"],
    "sumy": ["sum_ye", "total_ye"],
}


# ═══════════════════════════════════════════════════════════════
#  data_calculator — 派生变量计算器
# ═══════════════════════════════════════════════════════════════

class DataCalculator:
    """FLASH 派生变量计算器

    根据 DATA_CONFIG 中定义的 derived 变量，基于已有 raw 变量自动计算。
    计算函数注册在 _CALC_FUNCS 中。
    """

    def __init__(self, data_dict: dict):
        """
        参数:
            data_dict: {变量名: ndarray} 的字典，由 FlashDataContainer.data 提供
        """
        self._data = data_dict

    def get_available_derived(self) -> list:
        """返回当前数据可计算的派生变量列表"""
        available = []
        for vname, cfg in DATA_CONFIG.items():
            if cfg["category"] != "derived":
                continue
            deps = cfg.get("depends", [])
            if all(d in self._data for d in deps):
                available.append(vname)
        return available

    def compute(self, varname: str) -> np.ndarray:
        """计算单个派生变量

        参数:
            varname: 派生变量名（必须在 DATA_CONFIG 中注册为 derived）
        返回:
            ndarray
        """
        if varname not in DATA_CONFIG:
            raise KeyError(f"未知变量: {varname}")
        cfg = DATA_CONFIG[varname]
        if cfg["category"] != "derived":
            raise ValueError(f"'{varname}' 不是派生变量")

        # 先查看是否有专门的计算函数
        if varname in _CALC_FUNCS:
            return _CALC_FUNCS[varname](self._data)

        # 通用公式计算: 替换变量名 + eval
        formula = cfg.get("formula", "")
        deps = cfg.get("depends", [])
        local_vars = {d: self._data[d] for d in deps if d in self._data}
        # 补充常数
        local_vars["NA"] = NA
        return eval(formula, {"__builtins__": {}}, local_vars)

    def compute_all(self) -> dict:
        """计算所有可计算的派生变量，返回 {变量名: ndarray}"""
        result = {}
        for vname in self.get_available_derived():
            try:
                result[vname] = self.compute(vname)
            except Exception as e:
                print(f"  [警告] 计算 '{vname}' 失败: {e}")
        return result

    def register(self, varname: str, formula: str, description: str,
                 unit: str = "", unit_si: str = "", to_si: float = 1.0,
                 depends: list = None) -> None:
        """注册新的派生变量

        参数:
            varname: 变量名
            formula: 计算公式（变量名可用已有变量和 NA 常数）
            description: 物理描述
            unit: 常用单位
            unit_si: SI 单位
            to_si: 转换系数
            depends: 依赖变量列表（自动推断）
        """
        if depends is None:
            # 自动解析 formula 中出现的变量名
            tokens = set(re.findall(r"[a-zA-Z_]\w*", formula))
            excludes = {"NA", "np", "abs", "sqrt", "exp", "log", "sin", "cos",
                        "grad", "div", "curl", "max", "min", "mean"}
            depends = sorted(tokens - excludes)

        DATA_CONFIG[varname] = {
            "unit": unit, "unit_si": unit_si, "to_si": to_si,
            "description": description,
            "category": "derived", "depends": depends,
            "formula": formula,
        }


# 特殊计算函数注册表（对需要复杂数值处理的变量）
_CALC_FUNCS = {}


def _gradient_1d(arr: np.ndarray, dx: float) -> np.ndarray:
    """1D 梯度计算"""
    grad = np.zeros_like(arr)
    grad[..., 1:-1] = (arr[..., 2:] - arr[..., :-2]) / (2 * dx)
    grad[..., 0] = (arr[..., 1] - arr[..., 0]) / dx
    grad[..., -1] = (arr[..., -1] - arr[..., -2]) / dx
    return grad


def _calc_ls_nele(data: dict) -> np.ndarray:
    """计算电子密度梯度标长 ls_nele = nele / |grad(nele)|

    对于 AMR 块结构，对每个块内部计算梯度。
    简化: 假设 x 方向占主导，仅计算 x 方向梯度标长。
    """
    nele = data["nele"]
    return _calc_gradient_scale_length(nele, data.get("_grid_info", None),
                                       var_name="nele")


def _calc_ls_tele(data: dict) -> np.ndarray:
    """计算电子温度梯度标长 ls_tele = tele / |grad(tele)|"""
    tele = data["tele"]
    return _calc_gradient_scale_length(tele, data.get("_grid_info", None),
                                       var_name="tele")


def _calc_gradient_scale_length(var: np.ndarray, grid_info: dict = None,
                                var_name: str = "") -> np.ndarray:
    """计算梯度标长（仅 x 方向）

    对任意维度: 取最后空间轴 (Nx) 计算梯度。
      - 1D (nblocks, Nx):        直接计算
      - 2D (nblocks, Ny, Nx):    在每个块的 Ny 行中各取 Nx 方向
      - 3D (nblocks, Nz, Ny, Nx):取中间平面的 x 方向
    """
    ndim = var.ndim

    if ndim == 2:  # 1D: (nblocks, Nx)
        return _gradient_scale_1d_blocks(var, grid_info)

    nblocks = var.shape[0]
    result = np.zeros_like(var)

    for b in range(nblocks):
        # 获取 x 方向网格间距
        dx = 1.0
        if grid_info and "x_global" in grid_info:
            xg = grid_info["x_global"]
            if b < len(xg) and len(xg[b]) > 1:
                dx = float(np.mean(np.diff(xg[b])))

        if ndim == 3:  # 2D: (nblocks, Ny, Nx)
            ny, nx = var.shape[1], var.shape[2]
            # 对每一行计算梯度
            for iy in range(ny):
                row = var[b, iy, :]
                grad = _gradient_1d(row[np.newaxis, :], dx)[0]
                eps = 1e-30
                lstemp = np.where(np.abs(grad) > eps,
                                  np.abs(row / (grad + eps)), 1e30)
                result[b, iy, :] = lstemp

        else:  # 3D: (nblocks, Nz, Ny, Nx)
            nz, ny, nx = var.shape[1], var.shape[2], var.shape[3]
            iz = nz // 2
            # 仅取 z 中间平面的 x 方向，广播到全局
            for iy in range(ny):
                row = var[b, iz, iy, :]
                grad = _gradient_1d(row[np.newaxis, :], dx)[0]
                eps = 1e-30
                lstemp = np.where(np.abs(grad) > eps,
                                  np.abs(row / (grad + eps)), 1e30)
                # 广播到整个块
                for iz_ in range(nz):
                    result[b, iz_, iy, :] = lstemp

    return result


def _gradient_scale_1d_blocks(var: np.ndarray, grid_info: dict) -> np.ndarray:
    """对块结构的 1D 数据计算梯度标长"""
    nblocks = var.shape[0]
    nx = var.shape[1]
    result = np.zeros_like(var)
    for b in range(nblocks):
        dx = 1.0
        if grid_info and "x_global" in grid_info:
            xg = grid_info["x_global"]
            if b < len(xg) and len(xg[b]) > 1:
                dx = float(np.mean(np.diff(xg[b])))
        grad = _gradient_1d(var[b:b+1, :], dx)[0]
        eps = 1e-30
        ls = np.where(np.abs(grad) > eps,
                       np.abs(var[b] / (grad + eps)), 1e30)
        result[b, :] = ls
    return result


# 注册梯度标长计算函数
_CALC_FUNCS["ls_nele"] = _calc_ls_nele
_CALC_FUNCS["ls_tele"] = _calc_ls_tele


# ═══════════════════════════════════════════════════════════════
#  FlashHDF5File — 核心 I/O 类
# ═══════════════════════════════════════════════════════════════

class FlashHDF5File:
    """FLASH HDF5 输出文件的底层读写器"""

    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(f"FLASH HDF5 文件不存在: {filepath}")

        self._f = h5py.File(str(self.filepath), "r")

        self._cached_shape = None
        self._cached_ndim = None
        self._cached_nblocks = None
        self._cached_nx = None
        self._cached_ny = None
        self._cached_nz = None
        self._cached_varnames = None
        self._cached_available = None
        self._cached_file_type = None
        self._cached_sim_info = None
        self._cached_dtype_info = None
        self._cached_real_scalars = None
        self._cached_integer_scalars = None
        self._cached_runtime_params = None
        self._cached_laser_params = None
        self._cached_simulation_time = None
        self._cached_coord_system = None

    # def close(self):
    #     if self._f is not None:
    #         self._f.close()
    #         self._f = None

    def close(self):
        if self._f is not None:
            try:
                self._f.close()
            except Exception:
                # h5py 某些版本在重复关闭时可能抛出异常，此处忽略以保证鲁棒性
                pass
            finally:
                self._f = None


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    # ── 标量 / 参数 读取 ─────────────────────────────────────

    @property
    def real_scalars(self) -> dict:
        """返回所有 real scalar 值"""
        if self._cached_real_scalars is None:
            result = {}
            if "real scalars" in self._f:
                for r in self._f["real scalars"]:
                    name = r["name"].decode().strip()
                    result[name] = r["value"]
            self._cached_real_scalars = result
        return self._cached_real_scalars

    @property
    def integer_scalars(self) -> dict:
        if self._cached_integer_scalars is None:
            result = {}
            if "integer scalars" in self._f:
                for r in self._f["integer scalars"]:
                    name = r["name"].decode().strip()
                    result[name] = r["value"]
            self._cached_integer_scalars = result
        return self._cached_integer_scalars

    @property
    def runtime_params(self) -> dict:
        """返回所有 real runtime parameters"""
        if self._cached_runtime_params is None:
            result = {}
            if "real runtime parameters" in self._f:
                for r in self._f["real runtime parameters"]:
                    name = r["name"].decode().strip()
                    result[name] = r["value"]
            self._cached_runtime_params = result
        return self._cached_runtime_params

    @property
    def simulation_time(self) -> float:
        """获取仿真当前时间 [s]"""
        return self.real_scalars.get("time", 0.0)

    @property
    def simulation_step(self) -> int:
        """获取仿真步数"""
        return int(self.integer_scalars.get("nstep", 0))

    # ── 激光参数解析 ─────────────────────────────────────────

    @property
    def laser_groups(self) -> dict:
        """解析激光脉冲分组数据

        FLASH 中激光按 ed_time_GROUP_POINT 和 ed_power_GROUP_POINT 命名。
        每组的 time/power 点配对构成脉冲波形。

        返回:
            {group_index: {"time": [...], "power": [...]}}
            如: {1: {"time": [t1,t2,...], "power": [p1,p2,...]}, 2: {...}}
        """
        if self._cached_laser_params is not None:
            return self._cached_laser_params

        rp = self.runtime_params
        groups = {}

        # 按组号和点号收集
        time_pattern = re.compile(r"ed_time_(\d+)_(\d+)")
        power_pattern = re.compile(r"ed_power_(\d+)_(\d+)")

        time_items = {}
        power_items = {}

        for name, val in rp.items():
            m = time_pattern.match(name)
            if m:
                g, p = int(m.group(1)), int(m.group(2))
                time_items.setdefault(g, {})[p] = val
            m = power_pattern.match(name)
            if m:
                g, p = int(m.group(1)), int(m.group(2))
                power_items.setdefault(g, {})[p] = val

        all_groups = set(time_items.keys()) | set(power_items.keys())
        for g in sorted(all_groups):
            times = []
            powers = []
            max_p = max(set(list(time_items.get(g, {}).keys()) +
                           list(power_items.get(g, {}).keys())))
            for p in range(1, max_p + 1):
                t = time_items.get(g, {}).get(p, -1.0)
                pw = power_items.get(g, {}).get(p, -1.0)
                if t >= 0 and pw >= 0:
                    times.append(t)
                    powers.append(pw)
            if times:
                groups[g] = {"time": np.array(times), "power": np.array(powers)}

        self._cached_laser_params = groups
        return groups

    # ── 文件属性 ──────────────────────────────────────────────

    @property
    def available_datasets(self) -> list:
        if self._cached_available is None:
            self._cached_available = sorted(self._f.keys())
        return self._cached_available

    @property
    def file_type(self) -> str:
        if self._cached_file_type is None:
            if "sim info" in self._f:
                if "unknown names" in self._f and self._f["unknown names"].shape[0] > 20:
                    self._cached_file_type = "checkpoint"
                else:
                    self._cached_file_type = "plot"
            else:
                self._cached_file_type = "unknown"
        return self._cached_file_type

    @property
    def sim_info(self) -> dict:
        if self._cached_sim_info is None:
            if "sim info" not in self._f:
                self._cached_sim_info = {}
            else:
                info = self._f["sim info"][0]
                result = {}
                for name in info.dtype.names:
                    val = info[name]
                    if isinstance(val, bytes):
                        val = val.decode("utf-8", errors="replace").strip()
                    result[name] = val
                self._cached_sim_info = result
        return self._cached_sim_info

    # ── 维度检测 ──────────────────────────────────────────────

    def _probe_shape(self):
        if self._cached_shape is not None:
            return
        f = self._f
        candidates = ["dens", "tele", "pres", "temp"]
        arr = None
        for c in candidates:
            if c in f:
                arr = f[c]
                break
        if arr is None:
            for k in f.keys():
                ds = f[k]
                if hasattr(ds, "shape") and len(ds.shape) == 4 and ds.dtype.kind == "f":
                    arr = ds
                    break
        if arr is None:
            raise RuntimeError("无法从文件中探测物理量数组结构")

        self._cached_shape = arr.shape
        self._cached_nblocks = arr.shape[0]
        self._cached_nz = arr.shape[1]
        self._cached_ny = arr.shape[2]
        self._cached_nx = arr.shape[3]
        self._cached_ndim = sum(1 for s in [self._cached_nx, self._cached_ny, self._cached_nz] if s > 1)

    @property
    def ndim(self) -> int:
        self._probe_shape()
        return self._cached_ndim

    @property
    def nblocks(self) -> int:
        self._probe_shape()
        return self._cached_nblocks

    @property
    def nx(self) -> int:
        self._probe_shape()
        return self._cached_nx

    @property
    def ny(self) -> int:
        self._probe_shape()
        return self._cached_ny

    @property
    def nz(self) -> int:
        self._probe_shape()
        return self._cached_nz

    @property
    def dims_string(self) -> str:
        self._probe_shape()
        active = []
        if self._cached_nx > 1:
            active.append(f"x={self._cached_nx}")
        if self._cached_ny > 1:
            active.append(f"y={self._cached_ny}")
        if self._cached_nz > 1:
            active.append(f"z={self._cached_nz}")
        cells = " x ".join(active) if active else "scalar"
        return f"{self._cached_ndim}D ({self._cached_nblocks} blocks | {cells})"

    # ── 坐标系统自动检测 ─────────────────────────────────────

    @property
    def coordinate_system(self) -> str:
        """自动检测坐标系统

        通过检查 bounding box 中各个轴的范围来确定坐标系统类型。
        返回: 'cartesian_1d', 'cartesian_2d', 'cartesian_3d',
              'cylindrical_rz', 或 'unknown'
        """
        if self._cached_coord_system is not None:
            return self._cached_coord_system

        self._probe_shape()
        nx, ny, nz = self._cached_nx, self._cached_ny, self._cached_nz
        ndim = self._cached_ndim

        bbox = self._f["bounding box"][()]
        x_ext = float(bbox[:, 0, 1].max() - bbox[:, 0, 0].min())
        y_ext = float(bbox[:, 1, 1].max() - bbox[:, 1, 0].min())
        z_ext = float(bbox[:, 2, 1].max() - bbox[:, 2, 0].min())
        approx_2pi = 2 * np.pi
        approx_1deg = np.pi / 180  # ~0.01745

        is_cylindrical = abs(z_ext - approx_2pi) < 0.01 or abs(z_ext - approx_1deg) < 0.001

        if ndim == 1:
            if is_cylindrical:
                self._cached_coord_system = "cylindrical_1d"
            else:
                self._cached_coord_system = "cartesian_1d"
        elif ndim == 2:
            if is_cylindrical:
                # FLASH stores 2D cylindrical as (nz=1, ny, nx) where z=theta
                self._cached_coord_system = "cylindrical_rz"
            else:
                self._cached_coord_system = "cartesian_2d"
        elif ndim == 3:
            if is_cylindrical:
                self._cached_coord_system = "cylindrical_3d"
            else:
                self._cached_coord_system = "cartesian_3d"
        else:
            self._cached_coord_system = "unknown"
        return self._cached_coord_system

    @property
    def coord_labels(self) -> dict:
        """返回坐标轴标签

        根据坐标系统类型，返回每个 FLASH 轴对应的物理坐标标签。
        返回: {0: "x_label", 1: "y_label", 2: "z_label"}
        """
        cs = self.coordinate_system
        if cs == "cylindrical_rz":
            return {0: "r [cm]", 1: "z [cm]", 2: r"$\theta$ [rad]"}
        elif cs == "cylindrical_3d":
            return {0: "r [cm]", 1: r"$\theta$ [rad]", 2: "z [cm]"}
        elif cs == "cylindrical_1d":
            return {0: "r [cm]", 1: "z (const) [cm]", 2: r"$\theta$ (const) [rad]"}
        else:
            return {0: "x [cm]", 1: "y [cm]", 2: "z [cm]"}

    # ── 变量名解析 ────────────────────────────────────────────

    @property
    def varnames(self) -> list:
        if self._cached_varnames is not None:
            return self._cached_varnames
        f = self._f
        if "unknown names" in f:
            unames = f["unknown names"][:]
            if unames.dtype.names:
                # 复合结构: (name, flag)
                names = [str(x["name"].decode("utf-8", errors="replace").strip())
                         for x in unames]
            else:
                # 简单字符串数组 (yt 风格): (n,) S80
                names = [str(x.decode("utf-8", errors="replace").strip())
                         for x in np.atleast_1d(unames)]
        else:
            names = []
            for k in f.keys():
                ds = f[k]
                if hasattr(ds, "shape") and len(ds.shape) == 4 and ds.dtype.kind == "f":
                    if k not in ("bounding box", "block size", "coordinates",
                                "gsurr_blks", "unknown names"):
                        names.append(k)
            names = sorted(set(names))
        self._cached_varnames = names
        return names

    def resolve_var_name(self, name: str) -> str:
        """解析变量名（支持别名）"""
        if name in self.varnames:
            return name
        for canonical, aliases in VAR_ALIASES.items():
            if name in aliases:
                return canonical
        return name

    @property
    def dtype_info(self) -> dict:
        if self._cached_dtype_info is None:
            result = {}
            for k in self._f.keys():
                ds = self._f[k]
                if hasattr(ds, "shape"):
                    result[k] = {"shape": ds.shape, "dtype": str(ds.dtype)}
            self._cached_dtype_info = result
        return self._cached_dtype_info

    # ── 数据读取 ──────────────────────────────────────────────

    def read_dataset(self, name: str) -> np.ndarray:
        if name not in self._f:
            raise KeyError(f"数据集中不存在 '{name}'，可用数据集: {list(self._f.keys())}")
        return self._f[name][()]

    def read_var(self, name: str) -> np.ndarray:
        """读取物理量数组，仅挤压空间单例维度，保留块维度

        原始 4D 形状: (nblocks, Nz, Ny, Nx)
          - 1D: (16, 1, 1, 16) -> (16, 16)
          - 2D: (1, 1, Ny, Nx) -> (1, Ny, Nx)
          - 3D: (4, 16, 16, 16) -> (4, 16, 16, 16)
        """
        data = self.read_dataset(name)
        if len(data.shape) == 4:
            squeeze_axes = tuple(
                i for i in [1, 2, 3] if data.shape[i] == 1
            )
            if squeeze_axes:
                return np.squeeze(data, axis=squeeze_axes)
            return data
        return data

    def read_var_flat(self, name: str) -> np.ndarray:
        data = self.read_var(name)
        return data.reshape(-1)

    # ── 坐标重建 ──────────────────────────────────────────────

    def extract_var_yt_style(self, var_name: str = "dens",
                             use_cell_centers: bool = True):
        """使用纯 h5py 的 yt 风格数据提取

        yt 提取 FLASH AMR 数据的核心逻辑:
          1. 只使用叶节点 (leaf) block — node_type == 1 的块
          2. 对每个叶块计算单元中心坐标
          3. 展平并去重重叠的边界单元
          4. 按坐标排序后返回

        返回值（按维度）:
          1D: (x, data)
          2D: (x, y, data)
          3D: (x, y, z, data)

        支持的坐标系统:
          - cartesian_1d  (1D Cartesian)
          - cartesian_2d  (2D Cartesian)  — 暂未实现，会抛错误
          - cartesian_3d  (3D Cartesian)
          - cylindrical_rz (2D R-Z, FLASH 2D 柱坐标)
          - cylindrical_3d (3D Cylindrical r-θ-z) — 暂未实现，会抛错误
          - cylindrical_1d (1D Cylindrical) — 暂未实现，会抛错误
        """
        # 获取坐标系统
        cs = self.coordinate_system
        ndim = self.ndim

        # ── 检查支持的维度+坐标系统组合 ───────────────────
        supported_combos = {
            "cartesian_1d": "1D Cartesian (1D 直角坐标)",
            "cartesian_3d": "3D Cartesian (3D 直角坐标)",
            "cylindrical_rz": "2D Cylindrical R-Z (2D 柱坐标 R-Z)",
        }
        # 当前已实现
        if cs == "cartesian_2d":
            print(f"[WARNING] extract_var_yt_style: 2D Cartesian 尚未实现完整支持"
                  f" (ndim={ndim}, coord_system='{cs}')")
            print(f"[WARNING] 当前支持: {', '.join(supported_combos.values())}")
            raise NotImplementedError(
                f"2D Cartesian (cartesian_2d) 尚未实现。\n"
                f"当前支持的坐标系统:\n"
                + "\n".join(f"  - {v} ({k})" for k, v in supported_combos.items())
            )
        if cs not in supported_combos:
            print(f"[WARNING] extract_var_yt_style: 不支持的坐标系统/维度组合"
                  f" (ndim={ndim}, coord_system='{cs}')")
            print(f"[WARNING] 当前支持: {', '.join(supported_combos.values())}")
            raise NotImplementedError(
                f"不支持的坐标系统: '{cs}' (ndim={ndim})。\n"
                f"当前支持的坐标系统:\n"
                + "\n".join(f"  - {v} ({k})" for k, v in supported_combos.items())
            )

        # 获取叶节点块索引
        raw_nt = self._f["node type"][()]
        nt = np.asarray(raw_nt).flatten()
        leaf_idx = np.where(nt == 1)[0]

        if len(leaf_idx) == 0:
            leaf_idx = np.arange(self.nblocks)

        data_raw = self.read_dataset(var_name)  # (nblocks, nz, ny, nx)

        self._probe_shape()
        nx, ny, nz = self._cached_nx, self._cached_ny, self._cached_nz
        bbox = self._f["bounding box"][()]

        ndim = self.ndim

        if ndim == 1:
            return self._extract_yt_1d(data_raw, leaf_idx, bbox, nx)
        elif ndim == 2:
            return self._extract_yt_2d(data_raw, leaf_idx, bbox, nx, ny)
        elif ndim == 3:
            return self._extract_yt_3d(data_raw, leaf_idx, bbox, nx, ny, nz)
        else:
            raise ValueError(f"不支持 {ndim}D 数据")

    def _extract_yt_1d(self, data_raw, leaf_idx, bbox, nx):
        """1D yt 风格提取"""
        x_list, d_list = [], []
        for b in leaf_idx:
            xmin, xmax = bbox[b, 0, 0], bbox[b, 0, 1]
            xs = np.linspace(xmin + (xmax - xmin) / (2 * nx),
                             xmax - (xmax - xmin) / (2 * nx), nx)

            # 数据形状: (nblocks, nz, ny, nx) -> squeeze to (nx,)
            dd = data_raw[b]
            # 挤压单例维度
            while dd.ndim > 1 and dd.shape[0] == 1:
                dd = dd.squeeze(axis=0)
            if dd.ndim > 1:
                dd = dd.reshape(-1)
            d_list.append(dd)
            x_list.append(xs)

        x_flat = np.concatenate(x_list)
        d_flat = np.concatenate(d_list)

        # 去重重叠边界
        _, uniq_idx = np.unique(np.round(x_flat, decimals=10), return_index=True)
        si = np.sort(uniq_idx)
        return x_flat[si], d_flat[si]

    def _extract_yt_2d(self, data_raw, leaf_idx, bbox, nx, ny):
        """2D yt 风格提取"""
        x_list, y_list, d_list = [], [], []
        for b in leaf_idx:
            xmin, xmax = bbox[b, 0, 0], bbox[b, 0, 1]
            ymin, ymax = bbox[b, 1, 0], bbox[b, 1, 1]

            xs = np.linspace(xmin + (xmax - xmin) / (2 * nx),
                             xmax - (xmax - xmin) / (2 * nx), nx)
            ys = np.linspace(ymin + (ymax - ymin) / (2 * ny),
                             ymax - (ymax - ymin) / (2 * ny), ny)

            dd = data_raw[b]
            # 挤压 nz 单例维度
            while dd.ndim > 2 and dd.shape[0] == 1:
                dd = dd.squeeze(axis=0)
            if dd.ndim == 2:
                # meshgrid: shape (ny, nx) for both Xb and Yb
                Yb, Xb = np.meshgrid(ys, xs, indexing='xy')
                # Convert to (nx, ny) to match FLASH convention
                Xb = Xb.T  # now (ny, nx)
                Yb = Yb.T  # now (ny, nx)
                x_list.append(Xb.reshape(-1))
                y_list.append(Yb.reshape(-1))
                d_list.append(dd.reshape(-1))
            else:
                d_list.append(dd.reshape(-1))

        x_flat = np.concatenate(x_list)
        y_flat = np.concatenate(y_list)
        d_flat = np.concatenate(d_list)

        # 去重: 使用 (x, y) 二元组去重
        xy_pairs = np.column_stack([np.round(x_flat, decimals=10),
                                    np.round(y_flat, decimals=10)])
        _, uniq_idx = np.unique(xy_pairs, axis=0, return_index=True)
        si = np.sort(uniq_idx)
        return x_flat[si], y_flat[si], d_flat[si]

    def _extract_yt_3d(self, data_raw, leaf_idx, bbox, nx, ny, nz):
        """3D yt 风格提取 — 全 3D 坐标重建"""
        x_list, y_list, z_list, d_list = [], [], [], []
        for b in leaf_idx:
            xmin, xmax = bbox[b, 0, 0], bbox[b, 0, 1]
            ymin, ymax = bbox[b, 1, 0], bbox[b, 1, 1]
            zmin, zmax = bbox[b, 2, 0], bbox[b, 2, 1]

            xs = np.linspace(xmin + (xmax - xmin) / (2 * nx),
                             xmax - (xmax - xmin) / (2 * nx), nx)
            ys = np.linspace(ymin + (ymax - ymin) / (2 * ny),
                             ymax - (ymax - ymin) / (2 * ny), ny)
            zs = np.linspace(zmin + (zmax - zmin) / (2 * nz),
                             zmax - (zmax - zmin) / (2 * nz), nz)

            dd = data_raw[b]  # (nz, ny, nx)
            # 全 3D meshgrid
            Zb, Yb, Xb = np.meshgrid(zs, ys, xs, indexing='ij')
            x_list.append(Xb.reshape(-1))
            y_list.append(Yb.reshape(-1))
            z_list.append(Zb.reshape(-1))
            d_list.append(dd.reshape(-1))

        x_flat = np.concatenate(x_list)
        y_flat = np.concatenate(y_list)
        z_flat = np.concatenate(z_list)
        d_flat = np.concatenate(d_list)

        # 去重: 使用 (x, y, z) 三元组
        xyz_pairs = np.column_stack([np.round(x_flat, decimals=10),
                                     np.round(y_flat, decimals=10),
                                     np.round(z_flat, decimals=10)])
        _, uniq_idx = np.unique(xyz_pairs, axis=0, return_index=True)
        si = np.sort(uniq_idx)
        return x_flat[si], y_flat[si], z_flat[si], d_flat[si]

    def read_grid(self, use_cell_centers: bool = True, **kwargs) -> dict:
        self._probe_shape()
        bbox = self._f["bounding box"][()]
        nx, ny, nz = self._cached_nx, self._cached_ny, self._cached_nz

        x_global_list = []
        y_global_list = []
        z_global_list = []
        x_edges_list = []

        all_x = set()
        all_y = set()
        all_z = set()

        for b in range(self.nblocks):
            xmin, xmax = bbox[b, 0, 0], bbox[b, 0, 1]
            ymin, ymax = bbox[b, 1, 0], bbox[b, 1, 1]
            zmin, zmax = bbox[b, 2, 0], bbox[b, 2, 1]

            x_cells = np.linspace(xmin + (xmax - xmin) / (2 * nx),
                                  xmax - (xmax - xmin) / (2 * nx), nx) if nx > 1 else np.array([xmin])
            y_cells = np.linspace(ymin + (ymax - ymin) / (2 * ny),
                                  ymax - (ymax - ymin) / (2 * ny), ny) if ny > 1 else np.array([ymin])
            z_cells = np.linspace(zmin + (zmax - zmin) / (2 * nz),
                                  zmax - (zmax - zmin) / (2 * nz), nz) if nz > 1 else np.array([zmin])

            x_global_list.append(x_cells)
            y_global_list.append(y_cells)
            z_global_list.append(z_cells)

            x_edge = np.linspace(xmin, xmax, nx + 1) if nx > 1 else np.array([xmin, xmax])
            x_edges_list.append(x_edge)

            all_x.update(np.round(x_cells, decimals=10))
            all_y.update(np.round(y_cells, decimals=10))
            all_z.update(np.round(z_cells, decimals=10))

        result = {
            "x_1d": np.array(sorted(all_x)),
            "y_1d": np.array(sorted(all_y)) if all_y and not (len(all_y) == 1 and 0.0 in all_y) else None,
            "z_1d": np.array(sorted(all_z)) if all_z and not (len(all_z) == 1 and 0.0 in all_z) else None,
            "x": x_global_list,
            "y": y_global_list,
            "z": z_global_list,
            "x_global": x_global_list,
            "y_global": y_global_list,
            "z_global": z_global_list,
            "x_edges": x_edges_list,
        }
        return result

    # ── 统计与计算（原 data_processor.py 功能）─────────────

    def mean(self, varname: str, data_dict: dict = None) -> float:
        """全场平均值"""
        d = data_dict if data_dict else {}
        arr = d.get(varname)
        if arr is None:
            arr = self.read_var(varname)
        return float(np.mean(arr))

    def median(self, varname: str, data_dict: dict = None) -> float:
        d = data_dict if data_dict else {}
        arr = d.get(varname)
        if arr is None:
            arr = self.read_var(varname)
        return float(np.median(arr))

    def min(self, varname: str, data_dict: dict = None) -> float:
        d = data_dict if data_dict else {}
        arr = d.get(varname)
        if arr is None:
            arr = self.read_var(varname)
        return float(np.min(arr))

    def max(self, varname: str, data_dict: dict = None) -> float:
        d = data_dict if data_dict else {}
        arr = d.get(varname)
        if arr is None:
            arr = self.read_var(varname)
        return float(np.max(arr))

    def stats(self, varname: str, data_dict: dict = None) -> dict:
        d = data_dict if data_dict else {}
        arr = d.get(varname)
        if arr is None:
            arr = self.read_var(varname)
        return {
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "mean": float(np.mean(arr)),
            "median": float(np.median(arr)),
            "std": float(np.std(arr)),
        }

    def slice_1d(self, varname: str, grid: dict = None, data_dict: dict = None):
        """对 1D 数据：将各块按 x 坐标排序拼接"""
        if self.ndim != 1:
            raise ValueError(f"slice_1d 仅适用于 1D, 当前 {self.ndim}D")
        d = data_dict if data_dict else {}
        arr = d.get(varname)
        if arr is None:
            arr = self.read_var(varname)
        g = grid if grid else self.read_grid()
        x_list = g["x_global"]
        all_x, all_y = [], []
        for b in range(self.nblocks):
            all_x.extend(x_list[b])
            all_y.extend(arr[b])
        idx = np.argsort(all_x)
        return np.array(all_x)[idx], np.array(all_y)[idx]

    def slice_2d_flat(self, varname: str, grid: dict = None, data_dict: dict = None):
        """对 2D 数据展平"""
        if self.ndim != 2:
            raise ValueError(f"slice_2d_flat 仅适用于 2D, 当前 {self.ndim}D")
        d = data_dict if data_dict else {}
        arr = d.get(varname)
        if arr is None:
            arr = self.read_var(varname)
        g = grid if grid else self.read_grid()
        x_list, y_list = g["x_global"], g["y_global"]
        all_x, all_y, all_v = [], [], []
        for b in range(self.nblocks):
            ny, nx = arr[b].shape
            xv, yv = np.meshgrid(x_list[b], y_list[b])
            all_x.extend(xv.ravel())
            all_y.extend(yv.ravel())
            all_v.extend(arr[b].ravel())
        return np.array(all_x), np.array(all_y), np.array(all_v)

    def slice_3d_flat(self, varname: str, axis: int = 0, index: int = 0,
                       grid: dict = None, data_dict: dict = None):
        """对 3D 数据沿指定轴切片"""
        if self.ndim != 3:
            raise ValueError(f"slice_3d_flat 仅适用于 3D, 当前 {self.ndim}D")
        d = data_dict if data_dict else {}
        arr = d.get(varname)
        if arr is None:
            arr = self.read_var(varname)
        g = grid if grid else self.read_grid()
        x_list, y_list, z_list = g["x_global"], g["y_global"], g["z_global"]

        all_c1, all_c2, all_v = [], [], []
        for b in range(self.nblocks):
            sl = [slice(None)] * 3
            sl[axis] = index
            sliced = arr[b][tuple(sl)]
            if axis == 0:
                c1, c2 = np.meshgrid(x_list[b], y_list[b])
            elif axis == 1:
                c1, c2 = np.meshgrid(x_list[b], z_list[b])
            else:
                c1, c2 = np.meshgrid(y_list[b], z_list[b])
            all_c1.extend(c1.ravel())
            all_c2.extend(c2.ravel())
            all_v.extend(sliced.ravel())
        return np.array(all_c1), np.array(all_c2), np.array(all_v)

    # ── 信息输出 ──────────────────────────────────────────────

    def print_info(self, detailed: bool = False):
        """打印文件结构摘要"""
        print(f"文件: {self.filepath.name}")
        print(f"类型: {self.file_type}")
        print(f"维度: {self.dims_string}")
        print(f"仿真时间: t={self.simulation_time:.6e} s, step={self.simulation_step}")

        # 激光参数
        laser = self.laser_groups
        if laser:
            print(f"激光脉冲组数: {len(laser)}")
            for g, data in laser.items():
                n_pts = len(data["time"])
                print(f"  组 {g}: {n_pts} 个时点, "
                      f"t=[{data['time'][0]:.3e}..{data['time'][-1]:.3e}], "
                      f"P=[{data['power'][0]:.3e}..{data['power'][-1]:.3e}]")

        print(f"变量数: {len(self.varnames)}")
        print(f"  物理量: {', '.join(self.varnames)}")

        # 检查可计算的派生变量
        derived = [k for k, v in DATA_CONFIG.items()
                   if v["category"] == "derived"]
        print(f"  可派生: {len(derived)} 个 (如 {', '.join(derived[:6])}...)")

        info = self.sim_info
        if info:
            print(f"  Flash 版本: {info.get('flash version', '?')}")
            print(f"  设置命令: {info.get('setup call', '?')[:100]}")

        if detailed:
            print(f"所有数据集 ({len(self.available_datasets)}):")
            dtypes = self.dtype_info
            for k in sorted(self.available_datasets):
                info = dtypes.get(k, {})
                shape_str = str(info.get("shape", "?"))
                dtype_str = str(info.get("dtype", "?"))
                print(f"    {k:30s} {shape_str:30s} {dtype_str}")

    @staticmethod
    def get_config(varname: str) -> dict:
        """获取变量配置信息"""
        return DATA_CONFIG.get(varname, {})
