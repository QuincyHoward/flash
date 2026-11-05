# Output Processors 测试文档

> 最后核对：2026-11-05 · commit 7e04857 · 维护规则：新增测试后同步本文目录清单与统计

本目录包含 `flash/output_pro` 包的全部测试。**当前实测基线：57 passed**（`pytest flash/output_pro -q --ignore=PlasmaPy`，2026-11-05；PlasmaPy 为 vendored 外部包不收集）。

## 快速开始

```bash
cd flash/output_pro

# 一键运行全部测试（推荐）
python test/run_all_tests.py

# 运行 pytest
pytest test/ -v            # 注意：勿收集 PlasmaPy/（其 conftest 需 hypothesis）
```

## 目录结构

```
test/
├── README.md                          ← 本文件
├── run_all_tests.py                   ← ★ 一键运行全部测试
├── gen_test_data.py                   ← 测试数据生成（合成 H5）
├── compare_h5py_vs_yt.py              ← 两种提取模式交叉验证
├── test_extraction_modes.py           ← 提取模式测试
├── test_yt_style_extraction.py(.improved) ← yt 风格提取
├── fix_test_precision.py              ← 精度判断修复工具
├── all_tests_output.txt               ← 运行产物（生成，勿手改）
│
├── derived_variables/                 ← 派生变量计算
├── loader/                            ← FlashDataLoader
├── batch_loading/                     ← 批量加载
├── dimension_test/                    ← 1D/2D/3D 维度支持
├── lazy_loading/                      ← 懒加载
├── parallel/                          ← 并行处理
├── shock_position/                    ← 冲击波位置 / nele 临界面
├── unit_conversion/                   ← 单位换算
├── amr_visualization/                 ← AMR 可视化（d1/d2/d3 vs yt 对拍；
│                                         详见 d2/README_amr_extraction.md）
└── test_output/                       ← 测试输出落盘点
```

各功能子目录均有一句话 README。

## 测试说明

| 测试类别 | 文件 | 说明 |
|---------|------|------|
| 一键全跑 | `run_all_tests.py` | 顺序执行全部测试并汇总（**推荐首先运行**） |
| 派生变量 | `derived_variables/test_derived_variables.py` | `DataCalculator` 功能验证 |
| Loader | `loader/test_loader_validation.py` | `FlashDataLoader.load()` 数据一致性 |
| 批量加载 | `batch_loading/test_batch_loading.py` | `load_folder()` 功能测试 |
| 多维支持 | `dimension_test/test_dimension_loading.py` | 1D/2D/3D 全部维度 |
| 懒加载 | `lazy_loading/test_lazy_loading.py` | 元数据/数据分阶段加载 |
| 并行 | `parallel/test_parallel_processing.py` | 多进程批量读取 |
| 临界面 | `shock_position/test_shock_position.py` | 冲击波位置 + `nele` 与临界密度 |
| 单位换算 | `unit_conversion/test_unit_conversion.py` | `to_si()` / 派生量单位 |
| AMR 可视化 | `amr_visualization/d*/test_*.py` | AMR 网格可视化 + h5py vs yt 对拍 |

## 历史对拍验证（2026-07-04 报告，并入自 TEST_SUMMARY.md）

| 维度 | 文件 | 时间 | N(h5py) | N(yt) | Match | 线提取 max\|diff\| | 加速比 |
|------|------|------|---------|-------|-------|-------------------|--------|
| 1D | chk_0039 | 9.90e-10s | 272 | 272 | ✅ | **2.2e-15**（机器零） | **627x** |
| 2D | plt_0049 | 4.90e-10s | 22,784 | 22,784 | ✅ | **8e-12**（float32 精度） | **24x** |
| 3D | plt_0020 | 3.10e-10s | 16,384 | 16,384 | ✅ | 0.79（坐标偏差） | **24x** |

当时 2 个失败：`d3/test_amr_visualization_3d`（pcolormesh 维度不匹配——AMR 块状数据需 AMR 感知渲染器）与 `test_amr_visualization`（无头环境缺 tk/tcl，非代码 bug）。

源码修改记录（2026-07-04）：`flash_hdf5.py` 增 `coordinate_system` 6 系自动检测/`coord_labels`/`extract_var_yt_style()`；`data_loader.py` 增 `refine_level`/`bbox` 属性与 `use_cell_centers`/`return_global_coords` 兼容参数。

## 新增测试步骤

1. 在对应子目录创建 `test_xxx.py`；2. 开头添加 `PYTHONPATH` 设置；3. 命名遵循 `test_xxx()`；4. 运行验证；5. 更新本文件目录清单与统计。

## 运行示例 / CI

```bash
cd flash/output_pro
python test/run_all_tests.py                    # 输出以实际打印为准
pytest test/ --cov=output_pro --cov-report=html -v
```

覆盖率目标：行覆盖 ≥ 80%；`hdf5pro/`、`loader/` ≥ 90%。

## 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| `ModuleNotFoundError: output_pro` | PYTHONPATH 未设置 | 测试脚本开头 `sys.path.insert(0, ...)` |
| `KeyError: 'dens'` | H5 文件路径错误 | 检查 `test_file` 路径 |
| 编码错误（Windows） | 控制台非 UTF-8 | `PYTHONIOENCODING=utf-8` |
| 收集错误 hypothesis | 误收集 PlasmaPy | `--ignore=PlasmaPy` |

## 相关文档

- 使用说明：[`docs/output_processors_usage.md`](../docs/output_processors_usage.md)
- 自定义变量：[`docs/how_to_add_custom_variables.md`](../docs/how_to_add_custom_variables.md)
- 性能调优：[`docs/performance_tuning.md`](../docs/performance_tuning.md)
- API 参考：[`docs/api_reference.md`](../docs/api_reference.md)

**上级导航**：[../README.md](../README.md)
