"""
data_loader.py — 将 FLASH HDF5 原始数据加载为结构化容器

FlashDataLoader 是用户的主要入口，提供了:
  - 自动维度检测
  - 按名称读取物理量
  - 全局坐标网格构建
  - 仿真时间/激光参数提取
  - 派生变量自动计算
  - 单个文件 / 目录批量加载
  - 结构化数据容器 FlashDataContainer (也可直接通过 __main__ 测试)

FlashDataContainer 保存了处理后的数据，可直接传入 plotter。
"""

import os
import numpy as np
from pathlib import Path
from ..hdf5processor import FlashHDF5File, DataCalculator, DATA_CONFIG, NA


class FlashDataContainer:
    """结构化数据容器，保存处理后的仿真数据

    Attributes:
        ndim: int             空间维度 (1/2/3)
        nblocks: int          AMR 块数
        nx/ny/nz: int         每块网格数
        filepath: str         源文件路径
        file_type: str        'checkpoint' / 'plot'
        sim_info: dict        仿真元信息
        simulation_time: float 仿真时间 [s]
        simulation_step: int  仿真步数
        laser_groups: dict    激光脉冲分组数据
        varnames: list        物理量名称列表
        data: dict            物理量名称 -> ndarray (squeezed, block-wise)
        derived: dict         派生变量计算结果
        grid: dict            坐标网格信息
        x/y/z: ndarray        (可选) 全局坐标数组
        config: dict          变量配置信息
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data = {}
        self.derived = {}
        self.grid = {}
        self.x = None
        self.y = None
        self.z = None
        self.ndim = 1
        self.nblocks = 0
        self.nx = self.ny = self.nz = 0
        self.file_type = "unknown"
        self.sim_info = {}
        self.simulation_time = 0.0
        self.simulation_step = 0
        self.laser_groups = {}
        self.varnames = []
        self.refine_level = None
        self.bbox = None
        self.config = DATA_CONFIG.copy()

    def __repr__(self) -> str:
        nvars = len(self.data)
        nderived = len(self.derived)
        if self.data:
            first_key = list(self.data.keys())[0]
            shape_str = str(self.data[first_key].shape)
        else:
            shape_str = "?"
        return (f"FlashDataContainer({self.ndim}D, {self.nblocks} blocks, "
                f"{nvars} vars, {nderived} derived, t={self.simulation_time:.3e}s, "
                f"data shape: {shape_str})")

    def get(self, varname: str) -> np.ndarray:
        """统一获取变量：先查原始数据，再查派生变量"""
        if varname in self.data:
            return self.data[varname]
        if varname in self.derived:
            return self.derived[varname]
        raise KeyError(f"变量 '{varname}' 不存在于 data 或 derived 中")

    def unit(self, varname: str) -> str:
        """获取变量单位"""
        cfg = self.config.get(varname, {})
        return cfg.get("unit", "")

    def to_si(self, varname: str) -> float:
        """获取到 SI 单位的转换系数"""
        cfg = self.config.get(varname, {})
        return cfg.get("to_si", 1.0)


class FlashDataLoader:
    """FLASH 数据加载器——用户的主要入口

    用法:
        loader = FlashDataLoader("flash_hdf5_chk_0000")
        container = loader.load()
        dens = container.data["dens"]

        # 批量加载目录中所有 HDF5 文件
        containers = FlashDataLoader.load_folder("output_dir/")
    """

    def __init__(self, filepath: str):
        self.filepath = str(Path(filepath).resolve())
        self._flash_file = FlashHDF5File(self.filepath)

    # ── 核心加载 ──────────────────────────────────────────────

    def load(self, compute_derived: bool = True,
             use_cell_centers: bool = True,
             return_global_coords: bool = True) -> FlashDataContainer:
        """加载 HDF5 文件并返回结构化数据容器

        参数:
            compute_derived: 是否自动计算派生变量
            use_cell_centers: (API 兼容) 是否使用单元中心坐标
            return_global_coords: (API 兼容) 是否返回全局坐标

        说明:
            所有数据读取完成后底层 h5py 文件句柄立即关闭
            (数据已拷贝为 numpy 数组, 容器不依赖句柄),
            避免文件被进程锁住 (Windows 上测试/批处理会因此无法删除文件)。
        """
        container = FlashDataContainer(self.filepath)
        ff = self._flash_file
        try:
            # 元信息
            container.ndim = ff.ndim
            container.nblocks = ff.nblocks
            container.nx = ff.nx
            container.ny = ff.ny
            container.nz = ff.nz
            container.file_type = ff.file_type
            container.sim_info = ff.sim_info
            container.varnames = ff.varnames
            container.simulation_time = ff.simulation_time
            container.simulation_step = ff.simulation_step
            container.laser_groups = ff.laser_groups

            # 读取所有物理量
            for vname in ff.varnames:
                try:
                    container.data[vname] = ff.read_var(vname)
                except KeyError:
                    pass

            # AMR 元信息（兼容 yt 风格访问）
            container.refine_level = ff._f["refine level"][()]
            container.bbox = ff._f["bounding box"][()]

            # 读取网格信息
            container.grid = ff.read_grid()
            self._build_global_coords(container)

            # 计算派生变量
            if compute_derived and container.data:
                calc = DataCalculator(container.data)
                # 传入网格信息以便梯度计算
                calc._data["_grid_info"] = container.grid
                container.derived = calc.compute_all()
        finally:
            ff.close()

        return container

    def load_vars(self, *var_names: str, compute_derived: bool = True,
                  use_cell_centers: bool = True,
                  return_global_coords: bool = True) -> FlashDataContainer:
        """仅加载指定变量，速度更快"""
        container = FlashDataContainer(self.filepath)
        ff = self._flash_file
        try:
            container.ndim = ff.ndim
            container.nblocks = ff.nblocks
            container.nx = ff.nx
            container.ny = ff.ny
            container.nz = ff.nz
            container.file_type = ff.file_type
            container.sim_info = ff.sim_info
            container.simulation_time = ff.simulation_time
            container.simulation_step = ff.simulation_step
            container.laser_groups = ff.laser_groups

            for vname in var_names:
                try:
                    container.data[vname] = ff.read_var(vname)
                    container.varnames.append(vname)
                except KeyError:
                    print(f"  [警告] 变量 '{vname}' 不在文件中")

            # AMR 元信息
            container.refine_level = ff._f["refine level"][()]
            container.bbox = ff._f["bounding box"][()]

            container.grid = ff.read_grid()
            self._build_global_coords(container)

            if compute_derived and container.data:
                calc = DataCalculator(container.data)
                calc._data["_grid_info"] = container.grid
                container.derived = calc.compute_all()
        finally:
            ff.close()

        return container

    # ── 文件夹批量加载 ────────────────────────────────────────

    @staticmethod
    def load_folder(folder_path: str, pattern: str = "*chk*",
                    compute_derived: bool = True,
                    sort_by_time: bool = True) -> list:
        """加载文件夹中所有匹配的 HDF5 文件

        参数:
            folder_path: 文件夹路径
            pattern:     文件通配模式, 默认 "*chk*"
            compute_derived: 是否计算派生变量
            sort_by_time: 是否按仿真时间排序
        返回:
            [FlashDataContainer, ...] 按时间顺序排列
        """
        folder = Path(folder_path)
        if not folder.is_dir():
            raise NotADirectoryError(f"文件夹不存在: {folder_path}")

        containers = []
        for fpath in sorted(folder.glob(pattern)):
            try:
                loader = FlashDataLoader(str(fpath))
                c = loader.load(compute_derived=compute_derived)
                containers.append(c)
                print(f"  [OK] {fpath.name}  t={c.simulation_time:.4e}s")
            except Exception as e:
                print(f"  [FAIL] {fpath.name}: {e}")

        if sort_by_time:
            containers.sort(key=lambda c: c.simulation_time)

        print(f"  共加载 {len(containers)} 个文件")
        return containers

    @staticmethod
    def load_folder_parallel(folder_path: str, pattern: str = "*chk*",
                              max_workers: int = None,
                              verbose: bool = True) -> list:
        """并行加载文件夹中所有匹配的 HDF5 文件

        使用 ProcessPoolExecutor 并行加载多个文件。

        参数:
            folder_path: 文件夹路径
            pattern:     文件通配模式, 默认 "*chk*"
            max_workers: 最大并行数 (None=自动)
            verbose:     是否打印进度
        返回:
            [FlashDataContainer, ...] 按时间顺序排列
        """
        from ..parallel import parallel_load_folder

        if verbose:
            print(f"  [并行] 加载文件夹: {folder_path}")

        slices = parallel_load_folder(
            folder_path, pattern=pattern, max_workers=max_workers, verbose=verbose,
        )

        # 转回 FlashDataContainer (仅包含基础信息)
        from .data_loader import FlashDataLoader
        containers = []
        for s in slices:
            container = FlashDataContainer()
            container.filepath = s.get("filepath", "")
            container.simulation_time = s.get("time", 0.0)
            container.varnames = [k for k in s.keys() if k not in ("time", "x", "filepath", "step")]
            container.data = {k: s[k] for k in container.varnames}
            container.x = s.get("x", np.array([]))
            containers.append(container)

        containers.sort(key=lambda c: c.simulation_time)
        if verbose:
            print(f"  [并行] 加载完成: {len(containers)} 个文件")
        return containers

    # ── 内部方法 ─────────────────────────────────────────────

    @staticmethod
    def _build_global_coords(container: FlashDataContainer):
        g = container.grid
        ndim = container.ndim
        if ndim >= 1 and g.get("x_1d") is not None:
            container.x = g["x_1d"]
        if ndim >= 2 and g.get("y_1d") is not None:
            container.y = g["y_1d"]
        if ndim == 3 and g.get("z_1d") is not None:
            container.z = g["z_1d"]

    def print_info(self, detailed: bool = False):
        print(f"FlashDataLoader")
        print(f"  文件: {self.filepath}")
        self._flash_file.print_info(detailed=detailed)


# ═══════════════════════════════════════════════════════════════
#  __main__ 测试入口
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("FLASH HDF5 输出处理器 — 诊断测试工具")
    print("=" * 60)

    # 确定目标文件
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        # 默认测试 1D checkpoint
        BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "inputfiles", "hdf5files_1d")
        target = os.path.join(BASE, "lasslab_hdf5_chk_0001")
        print(f"\n未指定文件，使用默认 1D 样例: {os.path.basename(target)}")

    print(f"\n目标: {target}\n")

    # 1. 创建 HDF5 文件对象
    ff = FlashHDF5File(target)

    # 2. 打印结构信息
    print("── 文件结构摘要 ──")
    ff.print_info(detailed=True)

    # 3. 关键标量
    print("\n── 关键标量 ──")
    rs = ff.real_scalars
    for k in ["time", "dt", "dtold", "dtnew"]:
        if k in rs:
            print(f"  {k} = {rs[k]:.6e}")
    isc = ff.integer_scalars
    for k in ["nstep", "nxb", "nyb", "nzb", "dimensionality", "globalnumblocks"]:
        if k in isc:
            print(f"  {k} = {isc[k]}")

    # 4. 激光数据
    print("\n── 激光参数 ──")
    laser = ff.laser_groups
    if laser:
        for g, data in laser.items():
            print(f"  组 {g}:")
            for t, p in zip(data["time"], data["power"]):
                print(f"    t={t:.4e}s  P={p:.4e}W/cm2")
    else:
        print("  (无激光参数)")

    # 5. 变量配置信息
    print("\n── 变量注册信息 (data_config 前 10 个) ──")
    for i, (vname, cfg) in enumerate(DATA_CONFIG.items()):
        if i >= 10:
            print(f"  ... 共 {len(DATA_CONFIG)} 个注册变量")
            break
        cat = "原始" if cfg["category"] == "raw" else "派生"
        print(f"  {vname:15s} [{cat}] {cfg['unit']:12s} {cfg['description']}")

    # 6. 数据加载测试
    print("\n── 数据加载测试 ──")
    loader = FlashDataLoader(target)
    container = loader.load(compute_derived=True)

    print(f"  容器: {container}")
    print(f"  原始变量: {len(container.data)} 个")
    print(f"  派生变量: {len(container.derived)} 个")

    # 打印前 5 个原始变量的形状
    for i, (vname, arr) in enumerate(container.data.items()):
        if i >= 5:
            break
        print(f"    {vname:15s} shape={str(arr.shape):20s} "
              f"min={float(np.min(arr)):.4e} max={float(np.max(arr)):.4e}")

    # 7. 派生变量测试
    if container.derived:
        print(f"\n── 派生变量 ──")
        for vname, arr in container.derived.items():
            print(f"    {vname:15s} shape={str(arr.shape):20s} "
                  f"min={float(np.min(arr)):.4e} max={float(np.max(arr)):.4e}")

    # 8. 全场统计
    print(f"\n── 全场统计 ──")
    ff2 = container
    for v in ["dens", "tele", "pres"]:
        if v in container.data:
            s = ff.stats(v, container.data)
            print(f"  {v:8s}: min={s['min']:.4e}  max={s['max']:.4e}  "
                  f"mean={s['mean']:.4e}  std={s['std']:.4e}")

    print("\n  ✅ 诊断完成")
    ff.close()
