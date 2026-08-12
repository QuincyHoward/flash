# 开发者工作流手册

> `flash/output_processors` 包的开发、测试与发布工作流。
> 最后更新: 2026-07-04

---

## 目录

1. [开发环境设置](#1-开发环境设置)
2. [测试工作流](#2-测试工作流)
3. [h5py yt 风格提取工作流](#3-h5py-yt-风格提取工作流)
4. [发布工作流](#4-发布工作流)

---

## 1. 开发环境设置

```bash
# 安装依赖
pip install numpy h5py matplotlib pytest

# yt 对比需要（开发用）
pip install yt

# 运行测试
cd flash/output_processors
pytest test/ -v
```

## 2. 测试工作流

### 运行全部测试
```bash
pytest test/ -v --tb=short
```

### 运行单个测试
```bash
pytest test/amr_visualization/d1/test_flash_hdf5_vs_yt.py -v
```

### 测试配置
- 配置文件: `pytest.ini`
- 排除目录: `test/temp_delete/`（已废弃）
- 测试文件使用晚时间 FLASH 输出文件（AMR 网格更丰富）

## 3. h5py yt 风格提取工作流

### 3.1 核心 API

参考: `docs/api_reference.md` — `extract_var_yt_style()` 章节

### 3.2 精度验证

验证 h5py 提取结果与 yt 的一致性：

```bash
# 运行对比脚本
python test/compare_h5py_vs_yt.py
```

输出:
- `outputfiles/test/comparison_1d_h5py_vs_yt.png`
- `outputfiles/test/comparison_2d_h5py_vs_yt.png`
- `outputfiles/test/comparison_3d_h5py_vs_yt.png`
- 控制台输出差异统计摘要

### 3.3 新增坐标系统

步骤:
1. 在 `flash_hdf5.py` 的 `coordinate_system` 属性中添加检测分支
2. 在 `coord_labels` 属性中添加对应的坐标标签
3. 实现 `_extract_yt_Xd()` 私有方法
4. 在 `extract_var_yt_style()` 的 `supported_combos` 字典中注册
5. 在 `__init__.py` 和 `docs/api_reference.md` 文档中更新
6. 运行对比验证:
   ```bash
   python test/compare_h5py_vs_yt.py
   pytest test/ -v
   ```

### 3.4 测试文件选择

测试脚本自动选择目录中最晚时间的 hdf5 文件:
- `test_1d_extraction` → `lasslab_hdf5_chk_0039`
- `test_2d_extraction` → `lasslab_hdf5_plt_cnt_0049`
- `test_3d_extraction` → `lasslab_hdf5_plt_cnt_0020`

## 4. 发布工作流

### 4.1 版本更新
- 更新 `__init__.py` 中的 `__version__`
- 更新 `docs/api_reference.md` 的 "最后更新" 日期
- 生成对比图检查回归

### 4.2 发布检查清单
- [ ] `pytest test/ -v` 全部通过（27/27）
- [ ] 对比图无异常
- [ ] API 文档已更新
- [ ] 工作流文档已更新
