# AGENTS.md — flash-sim Agent 指引（单一事实源）

> 最后核对：2026-11-06 · commit 54a9f69

**flash-sim**：FLASH 高能量密度物理（HEDP）仿真的全功能 Python 封装（Gitee: physimx/flash）。提供场景系统、参数文件生成、多环境运行管理（wsl / hpc-remote / hpc-insitu）、HDF5 输出分析与可视化的一站式工作流。本包不分发任何 FLASH 源码/二进制/EOS 表（License §3）。

## 快速上手

```bash
python start_flash.py          # 环境自检自愈 + 安装 + 全局测试（--no-tests 只装不测；--offline 离线）
make test                      # pytest 三套件
make lint                      # black + ruff (line-length=120)
python -m flash.scenarios.core.runner --check-env   # 三模式环境自检
```

- venv 约定：Windows 用 `.venv-win/`，Linux/WSL 用 `.venv-linux/`（平台 venv 物理上不能共用）。
- 默认运行模式 `RUN_MODE="wsl"`；模式切换必须显式（`FLASH_RUN_MODE` / `--mode`），不做平台自动兜底。
- 运行输出外置到 `<repo>/../flash_sim_runs/`（`FLASH_RUNS_DIR` 可覆盖）；包目录内 `git status` 永远干净。

## 技能索引（skills/）

**任务开始时先读本表，按需加载对应 SKILL.md（`skills/<name>/SKILL.md`）。**

| skill | 触发场景 | 关键入口 |
|---|---|---|
| `flash-sim-overview` | 初次接触本项目 / 需要全局结构与工作流地图 | `start_flash.py`、`flash/` 子包 README |
| `flash-scenario-setup` | 新建/修改 SNB 或 FL-SH 场景；dtmax/限流器/辐射开关；SNB 分享合规 | `flash/scenarios/private/SNB/` |
| `flash-scenario-family` | 场景家族派生（SCENE VARS + build_family）；cn4 表核查；关辐射变体；套件测试 | `flash/scenarios/private/tracer/` |
| `flash-run-deploy` | 三模式（wsl/hpc-remote/hpc-insitu）运行与超算部署；slurm 作业 | `flash/flash_run/`、`scripts/02_hpc/` |
| `flash-output-analysis` | HDF5 chk/plt 读取、x-t 图、健康检查、边界伪迹判据 | `flash/output_pro/` |
| `flash-par-gen` | .par 参数文件生成与排版规范；新增参数流程 | `flash/input_gen/gen_par/` |
| `flash-input-gen` | 仿真输入文件全流程生成（8+ 种文件、create_input_files 一键、逐生成器定制、运行脚本+预诊断图） | `flash/input_gen/`（12 个 gen_* 子包） |
| `flash-newpara` | 新增 sim_* 参数 5 步注册；多区密度/增量边界/5 种渐变剖面；物种名 4 字符约束 | `flash/input_gen/gen_newpara/` |
| `flash-grid-refine-constraint` | 自定义 AMR 网格细化约束（逐材料分层、超薄层保护，可选组件） | `flash/input_gen/gen_Grid_markRefineDerefine/` |
| `flash-eos-op` | IONMIX cn4/cnr EOS/不透明度表处理（eosop_pro） | `flash/input_gen/gen_eos_op/` |
| `flash-flychk-history` | FLASH 输出 → NIST FLYCHK history 上传 zip | `flash/input_gen/gen_flychk_his/` |
| `flash-hpc-fetch` | 超算结果批量下载（SFTP 并行、完整性校验） | `scripts/02_hpc/` |
| `flash-data-extract` | 无 yt 环境纯 h5py 提取 FLASH AMR；批读提速；float32 溢出 | `flash/output_pro/loader` |
| `flash-backup-verify` | 发布前备份与独立验证 | `scripts/04_backup/usb_backup.py` |
| `flash-knowledge` | FLASH 物理/setup/参数语义问答（激光/EOC/网格/流体/EOS/辐射输运等 11 单元）；方程↔源码对照反查（src_finding 文档组） | 导航型 skill（references/src_finding/） |
| `flash-pitfalls` | 报错→根因→修复速查（编译/运行/物理失真） | 报错信息检索 |
| `flash-param-lookup` | 不认识的 FLASH runtime 参数查权威定义/默认值/取值范围（联网 rpDoc + 本地 4050 参数索引） | `skills/flash-param-lookup/`（联网 skill） |
| `flash-readme-sync` | 全仓 README 自底向上巡检维护（叶子先/父级后，先读代码后更新文档）、空白 README 补写 | `skills/flash-readme-sync/` |
| `flash-skill-sync` | 全体系 skill 巡检（接口冒烟/声明核对）与合并/边界梳理；含当前 22 skill 边界基线 | `skills/flash-skill-sync/` |
| `flash-git-publish` | 仓库推送/拉取/打标签发版/PyPI 发布；凭据体系与 403 排障 | `scripts/03_git_publish/` |

### 通用工程技能（非 FLASH 专属，2026-11-06 吸收）

| skill | 触发场景 |
|---|---|
| `flash-code-refactor-safe` | 重命名/拆分大文件/提取接口的安全重构流程与风险分级 |
| `flash-code-execute-verify` | 写/改代码后必须实际运行验证（代码级，与场景级短时验证互补） |
| `flash-token-budget` | token 节约纪律：先 Grep 后读、HDF5 不直读、子代理承载宽泛搜索 |

## 分工声明（防触发词抢答）

- **flash-sim 工具操作**（跑场景、生成 par、读输出、部署超算）→ 用本表中的操作型 skill。
- **FLASH 物理 / setup 标志 / 参数语义问答**（如 `mgd_meshgroups` 是什么、`+ug` 语义）→ 用 `flash-knowledge` / `flash-pitfalls`。
- 两者重叠时：操作优先用操作型 skill，理论背景再查 flash-knowledge。

## MCP 接入

`python mcp_server.py`（零第三方依赖 stdio server，9 工具：flash_overview / module_map / api_reference / docs_index / workflow_guide / list_scenarios / search_docs / read_doc / env_check）。WorkBuddy 接入方法见 `mcp_server.py` 文件头注释；`read_doc/search_docs` 天然覆盖 `skills/*.md`。

## 关联资源

- `skills/README.md` — skill 编写规范与 SKILL.md 模板
- `docs/README.md` — 文档主索引；`docs/skills-map.md` — skill ↔ docs ↔ 模块三向索引
- `docs/FLASH三模式运行体系.md` — 运行体系定案
- 上游 FLASH 源码级知识库（本地未随 git 分发）：`temp/FLASH-Expert/`，git pull 更新通道
