# flash/output_pro 三层架构 API 参考（已按本仓代码校正）

> 最后核对：2026-11-06 · commit 54a9f69 · 方法名逐一核对自 `flash/output_pro/*/`源码
> 迁自用户级 flash-output-process + output_processors-usage 技能；⚠️ 为相对旧版的变更

## 三层架构

```
HDF5 文件 (.chk / .plt)
  ↓ 第一层 hdf5pro/   FlashHDF5File、DataCalculator、DATA_CONFIG
  ↓ 第二层 loader/    FlashDataLoader、FlashDataContainer
  ↓ 第三层 plotter/   FlashPlotter（另有 parallel.py 并行模块、extraction_modes.py 提取模式注册表）
```

统一导入：`from flash.output_pro import FlashDataLoader, FlashPlotter`
⚠️ 旧路径 `physimx_sim.flash.output_processors.*`、`output_processors.*`、`hdf5processor` 均已废弃。

## 1. FlashHDF5File（`hdf5pro/flash_hdf5.py:593`）

```python
from flash.output_pro.hdf5pro import FlashHDF5File

with FlashHDF5File("sim_output/chk_0039") as ff:
    ff.simulation_time        # float 仿真时间 [s]（property）
    ff.simulation_step        # int
    ff.file_type              # 'checkpoint' / 'plot'
    ff.real_scalars           # dict（name 空格填充 bytes，取值注意 strip）
    ff.integer_scalars        # dict（nxb/nstep/globalnumblocks）
    ff.runtime_params         # dict（生效运行时参数）
    ff.laser_groups           # dict 激光参数
    ff.available_datasets     # list 变量清单

    ff.read_var("dens")       # 原始 (nb, nz, ny, nxb)
    ff.read_var_flat("dens")  # 展平
    ff.read_grid(use_cell_centers=True)   # 网格
    ff.stats("tele")          # 统计摘要（min/max/mean/...）
    ff.extract_var("dens", mode="h5py")   # yt 风格提取（1D: (x,data)…）
    ff.extract_var_yt_style("dens")       # 纯 h5py 实现（超算优先）
    ff.print_info(detailed=True)
```

提取模式注册表：`from flash.output_pro.extraction_modes import CURRENT_EXTRACTION_MODE`（一行切换 "h5py"/"yt"）。

## 2. DataCalculator 与派生变量（`hdf5pro/flash_hdf5.py:272`）

```python
from flash.output_pro.hdf5pro import DataCalculator, DATA_CONFIG

calc = DataCalculator(data_dict)          # ⚠️ 构造参数是变量字典（非文件对象）
calc.get_available_derived()              # 已注册派生变量名
calc.compute("nele") / calc.compute_all() # 按公式计算
DataCalculator.register(varname="pele_calc", formula="ye*dens*NA*1.380649e-16*tele",
                        description="Electron pressure", unit="erg/cm^3", to_si=0.1)
DATA_CONFIG["dens"]                       # 变量元信息（label/unit/factor/derived 公式）
```

已注册派生变量（示例）：`nele = ye·dens·NA`、`nion = sumy·dens·NA`、`dens_targ/dens_cham`、梯度标长 `ls_nele/ls_tele`。权威清单见 `DATA_CONFIG` 与 `flash/output_pro/FLASH物理量说明.md`。

## 3. FlashDataLoader / FlashDataContainer（`loader/data_loader.py`）

```python
from flash.output_pro import FlashDataLoader

loader = FlashDataLoader("sim_output/chk_0039")
container = loader.load("dens", compute_derived=True)   # 指定变量可选
container = loader.load_vars("dens", "tele")            # ⚠️ 仅加载指定变量（提速）
containers = FlashDataLoader.load_folder("out/", pattern="*chk*", sort_by_time=True)
containers = FlashDataLoader.load_folder_parallel("out/")   # 并行批量（本仓新增）

container.data["dens"]      # 原始变量 dict
container.derived["nele"]   # 派生变量 dict
container.get("dens")       # 先 data 后 derived
container.unit("dens")      # "g/cm^3"；container.to_si("dens")
container.grid["x_1d"]      # 全局坐标
container.simulation_time   # float
loader.print_info(detailed=True)
```

## 4. FlashPlotter（`plotter/plot_generator.py`）

```python
from flash.output_pro import FlashPlotter

plotter = FlashPlotter(container)
plotter.plot("dens", save_path="dens.png")            # 自适应 1/2/3D
plotter.plot_all(save_dir="plots/")                   # 全变量
plotter.plot_amr_grid("dens", save_path="amr.png")    # AMR 块结构图
FlashPlotter.plot_folder("out/", "dens", save_dir="plots/")        # classmethod
FlashPlotter.plot_folder_all_vars("out/", save_dir="plots/")
FlashPlotter.collect_xt("out/", "tele")               # x-t 时空数据收集（本仓新增，配 pcolormesh）
FlashPlotter.time_uniformity(times)                   # Δt 均匀性诊断
```

⚠️ 旧 `plotter.plot_folder(loader)` 实例用法已废弃，现为 classmethod 传文件夹路径。

## 5. 性能要点

- 仅加载需要的变量（`load_vars`）、不需要派生量时 `compute_derived=False`
- 批量多文件用 `load_folder_parallel` / `parallel.ParallelProcessor`（自适应 worker）
- float32 统计先 `.astype(np.float64)`（见 SKILL.md 常见坑）
