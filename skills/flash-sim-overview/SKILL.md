---
name: flash-sim-overview
description: flash-sim 项目入口导航：分层架构、5 分钟上手、典型工作流（场景调用/par 生成/HDF5 分析/多模式运行）。初次接触本项目、需要全局结构地图或寻找"该用哪个模块"时使用。触发词：flash-sim 是什么、项目结构、怎么上手、工作流、模块地图、场景系统、FlashSimulator。
---

> 最后核对：2026-11-06 · commit 54a9f69
> 「请求→技能→模块」路由矩阵自旧 flash-workflow-orchestrator（L0 元技能）校正并入（2026-11-06）

# flash-sim 项目概览与导航

flash-sim 是 FLASH 高能量密度物理（HEDP）仿真的全功能 Python 封装
（Gitee: physimx/flash）。一站式工作流：

```
物理参数设计 → .par 文件生成 → FLASH 编译运行 → HDF5 输出处理
                                              → 自适应可视化 (1D/2D/3D) + 物理量分析
```

注意：flash-sim 是第三方 Python 接口（Apache 2.0, PhySimX 团队）；FLASH 引擎本身
需从 flash.rochester.edu 单独获取。**本包不分发任何 FLASH 源码/二进制/EOS 表**（License §3）。

## 1. 分层架构

| 层 | 模块 | 职责 |
|----|------|------|
| 接口/适配层 | `interface.py`（FlashSimulator: mock/real） | 对外统一入口；mock 模式用 Planck/Saha 闭式公式，real 模式调 FLASH 二进制 |
| 输入生成层 | `flash/input_gen/`（gen_par, gen_config, gen_makefile, gen_sim_data, gen_eos_op, gen_newpara, gen_flychk_his …） | 结构化参数 → .par / Fortran 源 / Config / Makefile / .cn4 表 |
| 仿真执行层 | `flash/scenarios/`（base, registry, simulator, core.runner）、`flash/flash_run/`（env, remote） | FlashSimulatorEngine 编排"编译→运行→采集→插值→保存"；本地 WSL 与超算 SSH/SLURM |
| 输出处理层 | `flash/output_pro/`（hdf5pro → loader → plotter, parallel） | 纯 h5py 解析 FLASH AMR HDF5，自适应 1D/2D/3D 绘图 |
| 核心抽象层 | `flash/_core/`（BaseSimulator, schema, registry, credentials） | capability()/simulate() 契约、SimulationRequest/Result、加密凭据 |

## 2. 5 分钟上手

1. **环境安装/自检**（自愈式）：`python start_flash.py` — 创建平台专属 venv
   （Windows→`.venv-win`，Linux/WSL→`.venv-linux`），安装依赖，跑三套全局测试。
   只装不测：`--no-tests`；离线：`--offline`（查 `wheelhouse/`）。
2. **一键场景仿真**（默认 `RUN_MODE="wsl"`，零修改可跑）：
   ```bash
   # Windows
   .venv-win\Scripts\python.exe flash\scenarios\center_evolution\ch_center\laserslab1d_local_custom.py
   # WSL
   .venv-linux/bin/python flash/scenarios/public/center_evolution/ch_center/laserslab1d_local_custom.py
   ```
   超算模式：脚本顶部 `RUN_MODE` 改 `"hpc"`，或环境变量 `FLASH_RUN_MODE=hpc`。
3. **场景系统调用**：
   ```python
   from flash.scenarios.core.scene_reg.registry import get_scenario, list_scenarios
   from flash.scenarios.core.engine.simulator import FlashSimulatorEngine
   engine = FlashSimulatorEngine(get_scenario("thin_layer_sandwich_si"))
   output = engine.run()   # 自动编译→运行→插值→输出
   ```
4. **HDF5 分析**：
   ```python
   from flash.output_pro import FlashDataLoader, FlashPlotter
   container = FlashDataLoader("..._hdf5_chk_0001").load(compute_derived=True)
   FlashPlotter(container).plot("dens", save_path="dens.png")
   ```
5. **凭据/配置**：CLI `flash-cred`（凭据菜单）、`flash-setup`（配置）。

## 3. 三模式运行（详见 skill `flash-run-deploy`）

| 模式 | 驱动位置 | FLASH 执行位置 | 入口 |
|---|---|---|---|
| `wsl`（默认） | Windows python | WSL | `FLASH_RUN_MODE=wsl` |
| `hpc-remote` | Windows python（凭据+RemoteSession） | 超算计算节点（sbatch） | `FLASH_RUN_MODE=hpc` |
| `hpc-insitu` | 超算登录节点（.venv-hpc-nce） | 超算计算节点 | `--mode hpc-insitu` |

解析优先级：`--mode` 显式 > 环境变量 `FLASH_RUN_MODE` > 场景常量 `RUN_MODE`。**不做平台自动兜底**。

## 4. 运行产物与目录契约

- 输出外置：`<repo>/../flash_sim_runs/<scenario>/run_NNNNNN/`（`FLASH_RUNS_DIR` 可覆盖）。
- FLASH `setup/make` 一律在 FLASH 树 objdir 内进行；runs 目录只放输入快照、sbatch、日志、回收结果。

## 5. 质量工具链

- `make test` / `make test-all`：pytest 三套件；`make lint`：black + ruff（line-length=120）。
- `python scripts/08_docs/check_docs.py`：文档门禁（链接/模块引用/防腐锚点/敏感信息）。
- `python scripts/01_env_diagnose/fix_plot_style.py`：绘图规范扫描修复（全英文、字号 ≥18pt、Times New Roman）。

## 6. 意图 → 技能 → 模块路由矩阵

| 用户意图 | 技能 | 模块锚点 |
|---|---|---|
| 生成 .par / 新仿真输入文件 | flash-input-gen | `flash.input_gen.create_input_files` / `gen_par.ParGeneratorExtended`（权威默认 `gen_par/defaults.py`） |
| 新增 sim_* 参数 / 多区密度 / 渐变剖面 | flash-newpara | `flash.input_gen.gen_newpara.NewParaGenerator`（流程见 `gen_newpara/README.md`） |
| 自定义 AMR 细化约束（可选组件） | flash-grid-refine-constraint | `gen_Grid_markRefineDerefine.generator.GridMarkRefineDerefineGenerator` + 5 步参数注册 |
| 编译运行 / 超算部署 / SLURM | flash-run-deploy | `flash/scenarios/core/runner`、`flash/flash_run/`（env/remote） |
| 分析 HDF5 / 绘图 / x-t 图 | flash-output-analysis | `flash.output_pro`（loader → plotter） |
| 报错 / 不收敛 / 结果异常 | flash-pitfalls（+ flash-knowledge） | 报错检索 + 源码语义 |
| EOS/不透明度表、FLYCHK history、超算回收 | flash-eos-op / flash-flychk-history / flash-hpc-fetch | 对应子包与 `scripts/02_hpc/` |

新仿真完整链路：`flash-input-gen`（8 文件 + 运行脚本 + 预诊断图，全部落 `sim_input/`）→ [新参数则 flash-newpara] → [可选 flash-grid-refine-constraint] → `flash-scenario-setup` 短时验证（tmax≈1e-11）→ 正式跑 → `flash-output-analysis`。

硬性优先级规则（所有技能共享）：
1. 有现有生成器/加载器就直接用，不手写重复代码
2. 只改用户指定参数，其余保持 defaults.py 默认
3. 生成输入后必须 setup→make→run 实际验证（含短时验证）
4. Config/F90 必须在已验证模板上微调，禁止从零编写；.sh 一律 LF 换行
5. 动手前先查 `.workbuddy/memory/` 近期日志与 MEMORY.md，避免重复造轮子

## 7. 深入阅读

- 根 `README.md` — 完整使用文档（场景系统、input_gen、flash_run、output_pro）
- `flash/scenarios/README.md` — 场景系统（scene.json、位置优先语义）
- `docs/FLASH三模式运行体系.md` — 运行体系定案
- `docs/skills-map.md` — skill ↔ docs ↔ 模块三向索引
- 按任务加载对应 skill：见根 `AGENTS.md` 技能索引表
