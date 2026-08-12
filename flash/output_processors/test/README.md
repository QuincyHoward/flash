# Output Processors 测试文档

> 本目录包含 `flash/output_processors` 包的全部测试。
> 最后更新: 2026-07-04

---

## 快速开始

```bash
cd flash/output_processors

# 运行功能验证脚本
python demo_output_processor.py

# 运行 pytest 测试
pytest test/ -v
```

---

## 测试目录结构

```
test/
├── README.md                          ← 本文件
├── TEST_SUMMARY.md                   ← 最新测试总结（含通过状态）
├── run_all_tests.py                   ← 一键运行全部测试
│
├── derived_variables/                 ← 派生变量计算测试
├── loader/                          ← FlashDataLoader 测试
├── batch_loading/                   ← 批量加载测试
├── dimension_test/                   ← 1D/2D/3D 维度支持测试
├── amr_visualization/                ← AMR 网格可视化测试
│   ├── d1/                          ← 1D 测试
│   ├── d2/                          ← 2D 测试
│   └── d3/                          ← 3D 测试
├── temp_delete/                      ← 临时测试脚本（可删除）
└── ...
```

---

## 测试说明

| 测试类别 | 文件 | 说明 |
|---------|------|------|
| 功能验证 | `demo_output_processor.py` | 完整功能验证（推荐首先运行） |
| 派生变量 | `derived_variables/test_derived_variables.py` | `DataCalculator` 功能验证 |
| Loader | `loader/test_loader_validation.py` | `FlashDataLoader.load()` 数据一致性 |
| 批量加载 | `batch_loading/test_batch_loading.py` | `load_folder()` 功能测试 |
| 多维支持 | `dimension_test/test_dimension_loading.py` | 1D/2D/3D 全部维度 |
| AMR 可视化 | `amr_visualization/d*/test_*.py` | AMR 网格可视化测试 |

---

## 新增测试步骤

1. 在对应子目录创建 `test_xxx.py`
2. 脚本开头添加 `PYTHONPATH` 设置（见现有测试）
3. 测试函数命名遵循 `test_xxx()` 规范
4. 运行后输出测试结果
5. 更新 `TEST_SUMMARY.md` 和本文件

---

## 运行示例

### 运行功能验证脚本

```bash
cd flash/output_processors
python demo_output_processor.py
```

输出:
```
============================================================
output_processors 功能完整性验证
输出目录: .../outputfiles
============================================================

============================================================
TEST 1: 基础 I/O — 文件结构/仿真时间/激光参数
============================================================
...
  [OK] 基础 I/O

============================================================
TEST 2: 派生变量计算 (data_calculator)
============================================================
...
  [OK] 派生变量计算

...

============================================================
测试结果: 8/8 通过
输出文件位于: .../outputfiles
============================================================
```

### 运行 pytest

```bash
cd flash/output_processors
pytest test/ -v
```

---

## CI/CD 集成

### pytest 配置

项目根目录已包含 `pytest.ini`，运行：

```bash
# 安装测试依赖
pip install pytest pytest-cov

# 运行测试并生成覆盖率报告
cd flash/output_processors
pytest test/ --cov=output_processors --cov-report=html -v
```

### 覆盖率目标

- **行覆盖率 ≥ 80%**
- 核心模块 (`hdf5processor/`, `loader/`) 覆盖率 ≥ 90%

---

## 故障排查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `ModuleNotFoundError: output_processors` | `PYTHONPATH` 未设置 | 在测试脚本开头添加 `sys.path.insert(0, ...)` |
| `KeyError: 'dens'` | HDF5 文件路径错误 | 检查 `test_file` 路径是否正确 |
| 编码错误 (Windows) | 控制台不支持 UTF-8 | 设置 `PYTHONIOENCODING=utf-8` |

---

## 相关文档

- 使用说明: `docs/output_processors_usage.md`
- 自定义变量教程: `docs/how_to_add_custom_variables.md`
- 性能调优指南: `docs/performance_tuning.md`
- API 参考手册: `docs/api_reference.md`

---

**维护者**: WorkBuddy AI
**最后更新**: 2026-07-04
