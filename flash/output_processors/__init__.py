"""
output_processors — FLASH 仿真的通用输出处理器包

支持自适应处理 FLASH 1D/2D/3D 的 checkpoint (.chk) 和 plot (.plt) HDF5 输出文件。

子包:
  hdf5processor/   — HDF5 文件核心 I/O 层，解析 FLASH AMR 数据结构
                    包括: FlashHDF5File, DataCalculator, DATA_CONFIG
  loader/          — 数据加载层，将原始 HDF5 数据转为结构化数组
                    包括: FlashDataLoader, FlashDataContainer
  plotter/         — 可视化层，自适应维度生成图形 + AMR 网格图 + 文件夹批量绘图
  parallel/        — [新增] 并行处理模块，支持多文件、多物理场、多文件夹并行
                    包括: parallel_load_folder, parallel_interpolate, ParallelProcessor

核心功能 — extract_var_yt_style():
  纯 h5py 的 yt 风格数据提取，无需安装 yt 即可在超算上使用。
  通过 node_type(叶节点)+bounding box(坐标重建)+(x,y)/(x,y,z)去重，
  实现与 yt 一致的 AMR 数据提取。支持坐标系统自动检测 (Cartesian/Cylindrical)。

模式字典 — extraction_modes.py:
  统一管理 AMR 数据提取方案，一行代码切换当前模式 (默认优先 h5py):
    from flash.output_processors.extraction_modes import CURRENT_EXTRACTION_MODE
    CURRENT_EXTRACTION_MODE = "yt"      # ← 切换默认提取模式
  FlashHDF5File.extract_var(mode=...) 按模式调度:
    - "h5py": extract_var_yt_style (纯 h5py, 超算环境优先)
    - "yt":   extract_var_with_yt  (基于 yt 库)
  两种模式返回格式一致 (1D: (x, data) / 2D: (x,y,data) / 3D: (x,y,z,data))。

用法示例:
    from output_processors.loader import FlashDataLoader
    from output_processors.plotter import FlashPlotter

    # 单个文件
    loader = FlashDataLoader("path/to/hdf5_chk_0000")
    container = loader.load(compute_derived=True)
    plotter = FlashPlotter(container)
    plotter.plot("dens", save_path="dens.png")
    plotter.plot_amr_grid("tele", save_path="amr_tele.png")

    # 文件夹批量
    FlashPlotter.plot_folder("output_dir/", "dens", save_dir="plots/")

    # 激光脉冲数据
    print(container.laser_groups)
    print(f"时间: {container.simulation_time:.4e}s")

    # yt 风格提取（超算环境无 yt 可用）
    from output_processors.hdf5processor import FlashHDF5File
    ff = FlashHDF5File("path/to/hdf5_chk_0000")
    x, dens = ff.extract_var_yt_style("dens")        # 1D
    x, y, dens = ff.extract_var_yt_style("dens")      # 2D
    x, y, z, dens = ff.extract_var_yt_style("dens")   # 3D
    print(f"坐标系统: {ff.coordinate_system}")
    print(f"坐标标签: {ff.coord_labels}")

  old output_analysis/ 已被本处理器替代，请使用 output_processors。
"""

__version__ = "2.0.0"
