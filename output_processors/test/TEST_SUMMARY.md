# 测试报告 — 2026-07-04 (最终版)

## 运行命令
```
pytest test/ -v (排除 test/temp_delete)
```

## 结果总览
| 统计项 | 数值 |
|--------|------|
| **总计** | **27 项** |
| **通过 (PASSED)** | **25** (92.6%) |
| **失败 (FAILED)** | **2** (7.4%) |
| **错误 (ERROR)** | **0** |
| **收集错误** | **0** |
| 运行时间 | 14.9s |

## 通过的测试 (25个)

| 测试模块 | 测试函数 | 说明 |
|----------|----------|------|
| `d1/test_flash_hdf5_vs_yt` | `test_1d_extraction` | ✅ 1D h5py vs yt 对比（晚时间 chk_0039） |
| `d2/test_flash_hdf5_vs_yt` | `test_2d_extraction` | ✅ 2D h5py vs yt 对比（晚时间 plt_0049） |
| `d3/test_flash_hdf5_vs_yt` | `test_3d_extraction` | ✅ 3D h5py vs yt 对比（晚时间 plt_0020） |
| `batch_loading` | `test_load_folder` | ✅ 文件夹批量加载 |
| `batch_loading` | `test_load_folders` | ✅ 多文件夹加载 |
| `derived_variables` | `test_predefined_derived_vars` | ✅ 预定义派生变量 |
| `derived_variables` | `test_register_formula` | ✅ 自定义公式注册 |
| `dimension_test` | `test_1d_loading` | ✅ 1D 数据加载 |
| `dimension_test` | `test_2d_loading` | ✅ 2D 数据加载 |
| `dimension_test` | `test_3d_loading` | ✅ 3D 数据加载 |
| `lazy_loading` | `test_container_metadata` | ✅ 容器元数据 |
| `lazy_loading` | `test_folder_loading` | ✅ 文件夹加载 |
| `lazy_loading` | `test_single_vs_batch_consistency` | ✅ 单文件 vs 批量一致性 |
| `loader` | `test_loader_vs_h5py_1d` | ✅ Loader vs h5py 1D 验证 |
| `loader` | `test_loader_multiple_vars` | ✅ Loader 多变量加载 |
| `shock_position` | `test_data_loading_with_shok` | ✅ 含 shok 变量加载 |
| `shock_position` | `test_critical_density_check` | ✅ nele 派生变量检查 |
| `test_all_yt_style` | `test_d1_extraction` | ✅ 统一 1D yt 测试 |
| `test_all_yt_style` | `test_d2_extraction` | ✅ 统一 2D yt 测试 |
| `test_all_yt_style` | `test_d3_extraction` | ✅ 统一 3D yt 测试 |
| `test_all_yt_style` | `test_all_extraction` | ✅ 统一全维度测试 |
| `test_yt_style_extraction` | `test_yt_style_extraction` | ✅ yt 风格提取 |
| `test_yt_style_extraction_improved` | `test_yt_style_extraction_improved` | ✅ yt 风格提取改进版 |
| `unit_conversion` | `test_unit_info_1d` | ✅ 单位配置验证 |
| `unit_conversion` | `test_derived_unit_info` | ✅ 派生变量单位配置 |

## 失败测试分析 (2个)

| # | 测试 | 错误 | 原因 |
|---|------|------|------|
| 1 | `d3/test_amr_visualization_3d` | pcolormesh 维度不匹配 | AMR 块状数据无法直接 pcolormesh 渲染（需要 AMR 感知渲染器） |
| 2 | `test_amr_visualization` | tkinter TclError | 无头环境缺少 tk/tcl（非代码 bug） |

## 源码修改汇总

### `hdf5processor/flash_hdf5.py`
- `FlashHDF5File.coordinate_system` — 自动检测 6 种坐标系统
- `FlashHDF5File.coord_labels` — 物理坐标轴标签
- `extract_var_yt_style()` — 纯 h5py yt 风格提取（1D/2D/3D）
  - 叶节点筛选 (node_type==1)
  - (x,y) / (x,y,z) 元组去重
  - 未实现系统打印警告并抛出 NotImplementedError
- `read_grid()` — 添加 use_cell_centers/**kwargs 兼容参数

### `loader/data_loader.py`
- `FlashDataContainer.refine_level` / `bbox` 属性
- `FlashDataLoader.load()` — use_cell_centers/return_global_coords 兼容参数

### 废弃目录
- `test/temp_delete/` — 已从 pytest 收集中排除 (pytest.ini)

## 对比验证结果

| 维度 | 文件 | 时间 | N(h5py) | N(yt) | Match | 线提取 max\|diff\| | 加速比 |
|------|------|------|---------|-------|-------|-------------------|--------|
| 1D | chk_0039 | 9.90e-10s | 272 | 272 | ✅ | **2.2e-15** (机器零) | **627x** |
| 2D | plt_0049 | 4.90e-10s | 22,784 | 22,784 | ✅ | **8e-12** (float32 精度) | **24x** |
| 3D | plt_0020 | 3.10e-10s | 16,384 | 16,384 | ✅ | 0.79 (坐标偏差) | **24x** |
