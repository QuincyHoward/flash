# FLASH 技能 ↔ 文档 ↔ Python 模块 三向索引

> 最后核对：2026-11-06 · commit 54a9f69

本表是仓库内 skill（`skills/`，随 git 分发）与 docs、flash.* 模块的双向索引。
入口索引与分工声明见根 `AGENTS.md`；skill 编写规范见 `skills/README.md`。

> 2026-11-06 重写说明：旧版索引引用的用户级/项目级 skill（flash-workflow-orchestrator、
> flash-orchestrator-activator、physimx-* 系列等）已在 2026-09-14 的 skill 规范化迁移中
> 删除或并入；`docs/flash4_ug_4p8.md`（FLASH 用户指南，版权材料）与
> `input_gen/gen_otherf90s/ref_f90s/` 路径已不存在，相关行移除。
>
> 2026-11-06 二次吸收说明：本轮自用户级 skills 副本（Desktop / .workbuddy - 副本，两者内容一致）
> 与 `simulation/flash` 旧仓技能再次吸收——新建 flash-input-gen / flash-newpara /
> flash-grid-refine-constraint 与 3 个通用技能（flash-code-refactor-safe / flash-code-execute-verify /
> flash-token-budget；吸收时原名 code-refactor-safe / physimx-code-execute-verify / physimx-token-budget，
> 同日统一更名为 flash- 格式）；orchestrator 路由矩阵并入 flash-sim-overview，旧 output/run-deploy/
> examples API 修正后并入对应现有技能；`flash_src/docs/src_finding/` 7 份方程↔源码对照文档
> 完整迁入 flash-knowledge/references/src_finding/（源目录移至 flash/temp_delete/）。
> 跳过：flash-f90-development（ref_f90s 已删）、flash-orchestrator-activator（指向的用户级
> 编排器已不存在）、new-module-scaffold / physimx-migration / physimx-pipeline-state /
> physimx-debug-loop / physimx-code-quality（AITask/physimx_core/OldVersion 等依赖已删）、
> physimx-database-usage（DatabaseManager 已删）、physimx-sm-ga-workflow（genetic_sm 已删）。

## Skills → Docs / Modules

| 仓内 skill | 关联 docs | 关联模块/脚本 |
|---|---|---|
| `flash-sim-overview` | `README.md`, `docs/README.md` | 全部 |
| `flash-scenario-setup` | `docs/flash_operation_standard.md` | `flash/scenarios/private/SNB/`（SNB/ 核心模块 + scripts/） |
| `flash-scenario-family` | `docs/flash_operation_standard.md` | `flash/scenarios/private/tracer/`（CHTi/TiTi/OneSi_ml 等） |
| `flash-run-deploy` | `docs/FLASH三模式运行体系.md`, `docs/flash_simulation_execution_knowledge.md` | `flash/flash_run/`（env/modes/remote）, `scripts/02_hpc/` |
| `flash-output-analysis` | `docs/flash_operation_standard.md` | `flash/output_pro/`（loader/plotter/extraction_modes/parallel） |
| `flash-par-gen` | `docs/par_format_guide.md` | `flash/input_gen/gen_par/`, `flash/input_gen/gen_checker/` |
| `flash-input-gen` | `flash/input_gen/README.md`, `gen_par/README.md`, `gen_checker/README.md` | `flash/input_gen/` 全部 gen_* 子包；references/api-reference.md |
| `flash-newpara` | `flash/input_gen/gen_newpara/README.md`, `RP_Reference.md` | `flash/input_gen/gen_newpara/`, `test/newpara/` |
| `flash-grid-refine-constraint` | `flash/input_gen/gen_otherf90s/README.md` | `flash/input_gen/gen_Grid_markRefineDerefine/generator.py` |
| `flash-eos-op` | `flash/input_gen/gen_eos_op/README.md` | `flash/input_gen/gen_eos_op/`（eosop_pro/ionmix/eos_op_data） |
| `flash-flychk-history` | — | `flash/input_gen/gen_flychk_his/` |
| `flash-hpc-fetch` | — | `scripts/02_hpc/` |
| `flash-data-extract` | `flash/output_pro/FLASH物理量说明.md` | `flash/output_pro/loader/`, `flash/output_pro/extraction_modes.py`, `flash/output_pro/parallel.py` |
| `flash-backup-verify` | — | `scripts/04_backup/usb_backup.py` |
| `flash-knowledge` | `docs/reference/param_index_flash48.md`；references/src_finding/（方程↔源码对照，迁自 flash_src） | 上游 `temp/FLASH-Expert/skills/`（不入 git）；FLASH4.8 源码树（仓外 `simulation/flash/flash_src/FLASH4.8/FLASH4.8/`） |
| `flash-pitfalls` | `docs/FLASH-Expert吸收计划.md` | 上游 `temp/FLASH-Expert/skills/flash-pitfall-finder/` |

## Docs → Skills

| 文档 | 相关 Skill |
|---|---|
| `docs/README.md`（FLASH 仿真使用指南） | `flash-sim-overview` |
| `docs/par_format_guide.md`（.par 排版规范） | `flash-par-gen` |
| `docs/FLASH三模式运行体系.md` | `flash-run-deploy` |
| `docs/flash_operation_standard.md`（操作规范） | 全部 |
| `docs/flash_simulation_execution_knowledge.md` | `flash-run-deploy` |
| `docs/FLASH_深度调研.md` | `flash-knowledge` |
| `docs/reference/param_index_flash48.md`（FLASH 4.8 参数索引） | `flash-knowledge` |
| `docs/FLASH-Expert吸收计划.md`（上游吸收规划，已并入 skills编写计划.md 执行） | `flash-knowledge`, `flash-pitfalls` |
| `input_gen/gen_newpara/README.md` / `RP_Reference.md` | `flash-par-gen`, `flash-newpara` |
| `flash/output_pro/FLASH物理量说明.md` | `flash-output-analysis`, `flash-data-extract` |
| `skills/flash-scenario-setup/references/examples.md`（端到端示例） | `flash-scenario-setup`, `flash-input-gen`, `flash-newpara`, `flash-output-analysis`, `flash-run-deploy` |

## 与本仓外 skill 资产的关系

| 位置 | 状态 |
|---|---|
| `temp/FLASH-Expert/`（上游 18 skill，gitignored） | flash-knowledge / flash-pitfalls / param_index 的吸收源；git pull 更新通道 |
| 用户级 `~/.workbuddy/skills/`（不随项目分发） | 部分内容已重写并入本仓 skills/（scenario-setup、flychk-history、hpc-fetch、data-extract、backup-verify）；对应条目以本仓为准 |
| `layer3/flash` 工作副本（旧，2026-10-29） | flash-scenario-family 与 SNB reference 的素材源；以本仓 sandwich 为唯一事实源 |
| 用户级 skills 副本：`C:\Users\Administrator\Desktop\skills` 与 `C:\Users\Administrator\.workbuddy - 副本\skills`（两者 diff 零差异） | 2026-11-06 吸收源：6 个新技能 + 4 处并入（见文首二次吸收说明）；原件保留为历史存档 |
| `simulation/flash/.workbuddy/skills/`（旧仓） | input-gen-generator 并入 flash-input-gen；output_processors-usage 并入 flash-output-analysis；flash-orchestrator-activator 跳过（失效） |
| `flash/flash_src/docs/src_finding/`（已移至 `flash/temp_delete/docs/src_finding/`） | 7 份方程↔源码对照文档 2026-11-06 完整迁入 flash-knowledge/references/src_finding/ |
| FLASH4.8 源码树（仓外 `simulation/flash/flash_src/FLASH4.8/FLASH4.8/source/`） | src_finding 文档与 flash-knowledge 锚点的核验对象；仓外只读，不入 git |
