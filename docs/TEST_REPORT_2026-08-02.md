# PhySimX FLASH 全局测试报告

- **测试日期**: 2026-08-02 23:50 ~ 2026-08-03 00:59 (GMT+8)
- **测试环境**: Windows 11 (win32) + Python 3.13.14 (pytest 9.1.1)
- **项目根目录**: `D:\PhySimX\PhySimX\sim\flash`
- **测试命令**: `python scripts/05_test/run_global_tests.py` (等价于三套 pytest 全量运行)

---

## 一、测试结果总览

| 套件 | 测试目录 | 通过 | 跳过 | 失败 | 状态 |
|------|----------|------|------|------|------|
| Flash 框架测试 | `test/` | 132 | 0 | 0 | ✅ **通过** |
| InputGen 测试 | `input_gen/test/` | 78 | 0 | 0 | ✅ **通过** |
| OutputProcessors 测试 | `output_processors/test/` | 23 | 3 | 0 | ✅ **通过** |
| **合计** | — | **233** | **3** | **0** | ✅ **全部通过** |

- **总计**: 233 passed, 3 skipped, 0 failed (含 1 个 benign UserWarning)
- **总耗时**: 约 8 分 25 秒 (505.98s)
- **通过率**: 100% (233/233, 跳过项为依赖缺失的可选测试)

> 3 个 skipped 均为 `amr_visualization/d*/test_flash_hdf5_vs_yt.py` — 需要 `yt` 库
> (未安装), 属可选增强测试, 不影响核心功能验证。

---

## 二、测试修复与代码微调记录

本次测试发现并修复了 **3 类问题** (均为环境适配/模块缺失, 无核心逻辑缺陷):

### 1. 缺失场景模块恢复 — `thin_layer_sandwich`

**现象**: 2 个测试收集失败 (循环导入):
```
ImportError: cannot import name 'thin_layer_sandwich' from partially
initialized module 'flash.scenarios.collision_compression'
```

**根因**: `scenarios/collision_compression/thin_layer_sandwich/` 为正式场景模块
(备份清单确认存在), 但当前工作区缺失, 导致 `scenarios/__init__.py` 链式导入失败,
`grad_dens_sandwich` / `ch_center` 场景全部无法加载。

**修复**: 恢复完整模块 (从旧版适配 + 复用 grad_dens 的 Z 表 EOS):
- `interpolator.py`: 恢复时空插值引擎, import 路径 `physimx_sim.flash.*` → `flash.*`
- `defaults_si.py` / `defaults_al.py` / `defaults.py`: si (Z02/Z14/Z06 新表, 3500K) 与
  al (he-imx/al-imx/polystyrene 旧表, 290K) 双默认参数
- `par_builder.py`: 复用 .par 生成器
- `__init__.py`: 注册 `thin_layer_sandwich_si` / `thin_layer_sandwich_al` 两个场景
- `sim_input_si/` / `sim_input_al/`: FLASH 源文件 (Config/Makefile/F90/EOS 表)
- 补齐 `analysis/` `io/` `viz/` 子模块空包

**恢复后**: 4 个场景全部注册成功
(`ch_center`, `grad_dens_sandwich`, `thin_layer_sandwich_si/al`),
相关 10 个场景测试全部通过。

### 2. 缺失依赖安装

| 依赖 | 用途 | 状态 |
|------|------|------|
| `pytest` 9.1.1 | 测试框架 | ✅ 安装 |
| `numpy` 2.5.1 / `h5py` 3.16.0 / `matplotlib` 3.11.1 | 数值/IO/绘图 | ✅ 安装 |
| `paramiko` 5.0.0 | SSH 远程部署测试 | ✅ 安装 |
| `pandas` 3.0.5 | OutputProcessors yt 对比测试 | ✅ 安装 |

### 3. WSL 真实 FLASH 仿真测试环境适配 — `scenarios/simulator.py`

**现象**: `test_real_flash_run.py` 失败 (真实 FLASH 端到端测试):
```
timeout: failed to execute process: No such file or directory (os error 2)
EXIT_CODE=127
```

**根因**: 生成的 `run_flash.sh` 中调用 `mpirun`, 但 WSL 非交互 shell 不加载
`~/.bashrc` (其前段有 `case $- in *i*) ;; *) return;; esac` early-return),
导致 `/usr/local/mpich/bin` 不在 PATH。

**修复**: 在 `run_flash.sh` 生成模板头部显式注入 FLASH 环境变量:
```bash
export MPI_HOME=/usr/local/mpich
export HDF5_HOME=/usr/local/hdf5
export HYPRE_HOME=/usr/local/hypre
export PATH=$MPI_HOME/bin:$HDF5_HOME/bin:$PATH
export LD_LIBRARY_PATH=$MPI_HOME/lib:$HDF5_HOME/lib:$HYPRE_HOME/lib:${LD_LIBRARY_PATH:-}
```

**修复后**: 真实 FLASH 仿真 (LaserSlab 1D, thin_layer_sandwich_si) 完整跑通,
耗时 382s, 生成 result.h5 并通过数据校验。

### 4. 测试数据文件就位

OutputProcessors 测试需要真实 FLASH HDF5 输出 (被 `.gitignore` 排除, 发布包不含):
- `output_processors/inputfiles/hdf5files_1d/`: 41 个 chk (WSL LaserSlab 1D 实跑生成)
- `output_processors/inputfiles/hdf5files_2d/`: 55 个文件 (旧版复用)
- `output_processors/inputfiles/hdf5files_3d/`: 43 个文件 (旧版复用)

---

## 三、各套件详细结果

### 3.1 Flash 框架测试 (`test/`, 132 passed)

| 模块 | 测试数 | 说明 |
|------|--------|------|
| `remote_connect/test_sbatch.py` | 4 | sbatch 脚本生成 |
| `scenarios/test_ch_center_run.py` | 1 | CH 中心演化场景 |
| `scenarios/test_engine_dryrun.py` | 3 | 引擎 dry-run (si/al/plot) |
| `scenarios/test_real_flash_run.py` | 1 | **真实 FLASH 端到端仿真** |
| `scenarios/test_scenario_par_build.py` | 4 | .par 生成/EOS 校验/覆盖 |
| `scenarios/test_scenarios_imports.py` | 3 | 场景注册与元信息 |
| `test_flash_env_manager.py` | 15 | 环境管理 |
| `test_flash_input_gen.py` | 6 | InputGen 集成 |
| `test_flash_math_test.py` | 25 | 数学验证 |
| `test_flash_output_processors.py` | 13 | 输出处理集成 |
| `test_flash_remote_deploy.py` | 8 | SSH 远程部署 (paramiko) |
| `test_flash_simulator.py` | 24 | 仿真引擎 |
| `test_gitee.py` | 4 | Gitee 凭据管理 |
| `test_interface.py` | 9 | 接口层 |
| `test_math_test.py` | 12 | 数学测试 |

### 3.2 InputGen 测试 (`input_gen/test/`, 78 passed)

| 模块 | 测试数 |
|------|--------|
| `test_gen_checker.py` / `test_gen_config.py` / `test_gen_eos_op.py` | ~30 |
| `test_gen_makefile.py` / `test_gen_par.py` / `test_gen_shell_script.py` | ~30 |
| `test_gen_sim_data.py` / `test_gen_sim_init.py` / `test_gen_sim_initblock.py` | ~18 |
| `test_demo_scripts_compat.py` | 兼容性 |

### 3.3 OutputProcessors 测试 (`output_processors/test/`, 23 passed + 3 skipped)

| 模块 | 测试数 | 说明 |
|------|--------|------|
| `amr_visualization/d3/test_amr_visualization_3d.py` | 1 | 3D AMR 可视化 |
| `amr_visualization/test_amr_visualization.py` | 1 | AMR 可视化 |
| `batch_loading/test_batch_loading.py` | 2 | 文件夹批量加载 |
| `derived_variables/test_derived_variables.py` | 4 | 派生变量 |
| `dimension_test/test_dimension_loading.py` | 3 | 1D/2D/3D 加载 |
| `lazy_loading/test_lazy_loading.py` | 3 | 懒加载 |
| `loader/test_loader_validation.py` | 2 | Loader vs h5py 验证 |
| `parallel/test_parallel_processing.py` | 1 | 并行处理 |
| `shock_position/test_shock_position.py` | 2 | 冲击波位置 |
| `test_yt_style_extraction*.py` | 2 | yt 风格提取 |
| `unit_conversion/test_unit_conversion.py` | 2 | 单位换算 |
| `amr_visualization/d*/test_flash_hdf5_vs_yt.py` | 3 **skipped** | 需 `yt` 库 (可选) |

---

## 四、质量结论

1. **核心功能全部验证通过**: 场景注册/加载、.par 生成、引擎 dry-run、
   真实 FLASH 端到端仿真、HDF5 读取/派生/可视化、输入生成、远程部署、Gitee 凭据。
2. **真实仿真闭环**: `thin_layer_sandwich_si` 场景完成
   build → compile (cache) → run → collect → interpolate → result.h5 全链路,
   证明 WSL 中 FLASH 4.8 安装可用 (详见 hello_flash 部署记录)。
3. **代码质量**: 无失败测试, 无运行时错误; 仅有 1 个预期 UserWarning
   (grad_dens 场景 3500K 初始温度说明) 与若干 benign 资源警告。
4. **可发布性**: 全局测试全绿, 满足 `git_push.py --tag` 流程前置条件
   (打标签前自动运行全局测试)。

---

## 五、复现方式

```bash
# 一键运行全局测试 (三套件)
cd D:/PhySimX/PhySimX/sim/flash
PYTHONPATH="D:/PhySimX/PhySimX/sim" python scripts/05_test/run_global_tests.py

# 或单套件
python scripts/05_test/run_global_tests.py --framework   # Flash 框架
python scripts/05_test/run_global_tests.py --input       # InputGen
python scripts/05_test/run_global_tests.py --output      # OutputProcessors
```

---

*报告生成: 2026-08-03 00:59 GMT+8 · 由全局测试运行器自动采集数据*
