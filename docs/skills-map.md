# FLASH 技能 ↔ 文档 ↔ Python 模块 双向索引表

## Skills → Docs

| 用户级 Skill | 关联的 Project Docs | 关联的 Python 模块 |
|-------------|-------------------|-------------------|
| `flash-workflow-orchestrator` | — | 全部 |
| `input-gen-generator` | `input_gen/README.md`, `docs/par_format_guide.md` | `input_gen/` (全部子模块) |
| `flash-newpara` | `input_gen/gen_newpara/README.md`, `input_gen/gen_newpara/RP_Reference.md` | `input_gen/gen_newpara/` |
| `flash-output-process` | — | `output_processors/` |
| `flash-run-deploy` | — | `flash_run/env/`, `flash_run/remote/` |
| `flash-f90-development` | `input_gen/gen_otherf90s/ref_f90s/*/README.md` (5 个) | `input_gen/gen_otherf90s/ref_f90s/`, `input_gen/gen_sim_initblock/` |
| `flash-examples` | — | 全部 |

## Project Docs → Skills

| 文档 | 相关 Skill |
|------|-----------|
| `docs/README.md` (FLASH 仿真使用指南) | `flash-input-gen` |
| `docs/par_format_guide.md` (.par 排版规范) | `flash-input-gen` |
| `docs/FLASH_深度调研.md` | `flash-f90-development` |
| `docs/flash_simulation_execution_knowledge.md` | `flash-run-deploy` |
| `docs/flash_operation_standard.md` | 全部 |
| `docs/flash4_ug_4p8.md` (FLASH 用户指南) | 全部 |
| `input_gen/gen_newpara/README.md` | `flash-newpara` |
| `input_gen/gen_newpara/RP_Reference.md` | `flash-newpara`, `flash-input-gen` |
| `input_gen/gen_otherf90s/ref_f90s/*/README.md` | `flash-f90-development` |

## 项目级 skills → 用户级 skills

| 项目级 skill (cascade) | 关联的用户级 skill |
|----------------------|-------------------|
| `flash-orchestrator-activator.md` 🔥 | `~/.workbuddy/skills/flash/flash-workflow-orchestrator/` |
| `physimx-*.md` (通用 PhySimX) | PhySimX 根目录级 skills |
