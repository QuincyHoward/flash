# flash-sim 版本更新日志 (Changelog)

> 本文件记录用户可感知的功能变更。历史版本细节见 `git tag -l` 与 PyPI Releases。

## 0.2.1 (2026-11-06)

**README 和 skills 升级**

### 新增

- **技能体系 12 → 22 个**：
  - 自外部技能库吸收并按本仓 API 校正：`flash-input-gen`（输入文件全流程生成）、
    `flash-newpara`（新参数/多区密度剖面）、`flash-grid-refine-constraint`（AMR 细化约束）、
    `flash-param-lookup`（联网查官方 rpDoc 参数定义 + 4050 参数离线索引）、
    `flash-readme-sync`（全仓 README 自底向上巡检）、`flash-skill-sync`（全体系 skill 巡检）；
  - 通用工程技能统一 flash- 命名：`flash-code-refactor-safe` / `flash-code-execute-verify` /
    `flash-token-budget`；
  - L0 编排器路由矩阵并入 `flash-sim-overview`；6 处重叠 skill 分工声明补齐。
- **方程↔源码对照文档组**：`flash-knowledge/references/src_finding/` 7+1 份
  （查找方法论 / hy_uhd / EnergyDeposition / RadTrans / ThermalConduction / MFP-Knudsen / 映射表），
  行号抽验通过，FLASH4.8 源码树锚点注明仓外位置。
- **output_pro API 速查**（`skills/flash-output-analysis/references/output-api.md`）：
  三层架构全签名，含 `collect_xt` / `load_folder_parallel` / `extract_var_yt_style`。

### 修复

- **`flash.output_pro` 根包不 re-export**：5 处文档的错误导入声明
  （`from flash.output_pro import FlashDataLoader`）全部修正为子包导入
  （`from flash.output_pro.loader import FlashDataLoader`），经接口冒烟实测验证。
- `deploy/README` 离线安装路径 16 处（`scripts/08_offline_install/` → `deploy/`）；
  input_gen 各 gen_* 子包 GUIDE 统一改名 `README.md`（10 份）并全仓引用同步。
- 补写空白 README 9 份；全仓 117 份 README 路径声明审计清零。

### 变更

- `SandwichTxN` 场景升级四层结构（Si 0.92μm / 致密 CH 1.0 / 泡沫 CH 0.294 / He），
  梯形脉冲双束对打，`SANDWICH_TXN_TMAX` 环境变量短验证通道。
- 移除 `flash/_core/credentials_legacy.py`（1125 行，由 `credentials` 体系替代）。

## 0.1.15 (2026-10-30)

**PlasmaPy 加入后处理，场景目录优化**

### 新增

- **PlasmaPy 物理量适配层** (`flash/output_pro/plasmapy_bridge.py`)：
  - FLASH 网格量 → astropy `Quantity` 带单位转换（`to_quantity`）；
  - 带单位等离子体诊断量：库仑对数 lnΛ (GMS-6)、Debye 长度 λ_D、
    Spitzer/Braginskii 电子热导率 κ_e、电子平均自由程 λ_mfp、
    Knudsen 数 K_n=λ_mfp/L_Te、量子简并参数 Θ_e、离子耦合参数 Γ_i、
    Saha 电离度 Z̄、临界密度面 n_c(0.351μm)；
  - `HAS_PLASMAPY=False` 时优雅降级，其余功能不受影响；
  - 12 项单元/物理交叉验证测试（`test/test_plasmapy_bridge.py`）。
- **PlasmaPy vendor 快照**：PlasmaPy 2026.2.0 源码随仓库分发
  （`flash/output_pro/PlasmaPy/src/PlasmaPy`，BSD-3 许可，独立双许可边界）；
  win/wsl editable 安装器 `install_editable.py`；HPC (NC-E) 离线 wheel
  bundle 路线并已并入 `.venv-hpc-nce`（py3.12.8 基座，52 passed）。
- **场景统一 CLI**：`python -m flash.scenarios list|run|submit`，
  平台自适应 `--mode auto`，`--tmax` 极短验证，约定式 `scene.json` 零注册发现。
- 全场景本地 WSL 极短验证管线（`scripts/07_private_keep/scene_verify_all_20261030.py`）。

### 优化

- **场景目录重组**：`output_processors` → `output_pro` 全仓更名
  （hdf5processor → hdf5pro），场景/基础设施/文档 108 文件同步迁移；
  旧目录退役移入 `flash/temp_delete/`。
- 场景框架修复：manifest 斜杠 module 路径归一化；无参 `main()` 场景的
  argv 隔离与 `--tmax` 透传。
- wheel/sdist 排除 PlasmaPy vendor 与 temp_delete（5.0 MB，0 泄漏）。

### 测试

- 全局 436 passed / 2 skipped（framework 293 / input_gen 86 / output_pro 57）；
  35 个注册场景本地 WSL `tmax=1e-11` 端到端验证 25 成功 / 8 环境跳过 / 0 回归。

## 0.1.11 (2026-10)

- 基线版本（详见 git tag 与发布说明）。
