# flash-sim Agent Skills 编写计划

> **文档状态**：审核稿 v1.0（2026-11-06）
> **最后核对**：2026-11-06
> **适用仓库**：`E:/PhySimX/PhySimX/simulation/flash_test/sandwich/flash`（gitee.com/physimx/flash，master）
> **目标**：将 flash-sim 相关 Agent skills 沉淀到仓库内部，随 git 分发，使 WorkBuddy / Claude Code / Codex / OpenCode 等各类 Agent 可直接阅读执行。

---

## 1. 背景与目标

### 1.1 背景问题

当前 flash-sim 的 Agent skill 资产散落在三处，且均无法随项目分发：

| 位置 | 资产 | 问题 |
|---|---|---|
| `sandwich/flash`（主工作区） | 无自有 skill；`temp/FLASH-Expert/` 有上游 18 skill | `temp/` 已 gitignore，不随 git 分发 |
| `layer3/flash`（旧副本，2026-10-29） | `.workbuddy/skills/flash-scenario-family/SKILL.md` 等 | 仅 1 个存活 skill，含硬编码路径；本项目级副本不随 git 分发 |
| `C:\Users\Administrator\.workbuddy\skills\`（用户级） | 约 20 个 FLASH 相关 skill | 用户级目录天然不随项目分发，他人无法获得 |

同时存在多处过时引用：`docs/skills-map.md` 有 3 处死链/失实路径；physimx-* 系列 9 个 skill 存在双重 frontmatter；`flash-scenario-family` 硬编码 `/root/QC/FLASH/...`；迁移日志显示曾有 43 个 skill 被删除但索引未清理。

### 1.2 已确认的决策（4 条）

1. **格式**：仓库级 `skills/<name>/SKILL.md` + 顶层 `AGENTS.md` 索引；WorkBuddy 通过项目级 `.workbuddy/skills/` 同步脚本加载。
2. **范围**：只纳入与当前 flash-sim 包直接相关的 skill；依赖外部仓库（flychk-sim、SPECTIME/MATLAB、KnNum）的 skill 不纳入。
3. **与 `docs/FLASH-Expert吸收计划.md` 的关系**：并入本计划统一执行，上游 18 skill 的吸收作为其中阶段。
4. **过时内容**：重读当前代码后重写；代码已不存在的接口不写。沿用「最后核对：日期」防腐锚点惯例。

### 1.3 多 Agent 兼容性结论（2026-11-06 生态证据核实）

本方案可被主流 Agent 识别与利用，机制分两层：

| Agent/Harness | 入口文件 | 识别方式 | 加载 skills/ 的路径 |
|---|---|---|---|
| OpenAI Codex CLI | AGENTS.md | **原生**（spec 发起方，工作前必读） | 经 AGENTS.md 索引按需读 SKILL.md |
| OpenCode | AGENTS.md | **原生**（CLAUDE.md 亦兼容） | 同上；另支持 skills 加载 |
| Claude Code | CLAUDE.md | **不读 AGENTS.md**（官方文档明示） | CLAUDE.md 首行 `@AGENTS.md` 导入 → 索引 → 按需读 |
| WorkBuddy | `.workbuddy/skills/` | 项目级 skills 自动加载 | sync 脚本镜像复制（见 §5.2） |
| Gemini CLI | GEMINI.md（默认） | 需用户配置 `context.fileName=AGENTS.md` | 经索引 |
| Cursor / Zed / Warp / Amp / Factory Droid / Jules / VS Code | AGENTS.md | **原生** | 经索引 |
| GitHub Copilot | AGENTS.md | 部分urface支持（cloud agent 支持） | 经索引 |
| 其他任意 Agent | — | 有文件读取能力即可 | 「AGENTS.md → skills/README.md → 对应 SKILL.md」纯 markdown 链路，零格式依赖 |

**关键设计**：SKILL.md frontmatter 沿用 Anthropic Agent Skills 规范（name/description）。支持原生 skill 加载的 harness（Claude Code / OpenCode / Codex / WorkBuddy）可自动触发；不支持的按 AGENTS.md 索引手动加载——**两条路都通**。

---

## 2. 现状盘点（已核实）

### 2.1 主工作区 `sandwich/flash`（2026-11-05，最新）

- 包名 flash-sim v0.1.15；CLI 入口 `flash-cred` / `flash-setup`；`start_flash.py` 一键环境自愈；Makefile（test/lint/build）。
- `mcp_server.py`：零依赖 MCP stdio server，9 工具（flash_overview / module_map / api_reference / docs_index / workflow_guide / list_scenarios / search_docs / read_doc / env_check），`read_doc/search_docs` 基于 PROJECT_ROOT 下 `.md` —— **skills/*.md 天然可被 MCP 读取，零改动衔接**。
- `docs/`：README（主索引）、FLASH三模式运行体系（wsl/hpc-remote/hpc-insitu）、flash_operation_standard、flash_simulation_execution_knowledge、par_format_guide、FLASH-Expert吸收计划（待执行）、skills-map（**3 处死链需修正**）、DUAL_MODE_TESTING（早于三模式定案，需标过时）。
- `flash/` 子包 258 篇 README（11-05 重建，均有防腐锚点）。
- `scripts/`：01_env_diagnose、02_hpc、03_git_publish、05_test、08_docs（check_docs.py 门禁）、git-hooks/（已有 pre-commit/pre-push）。
- `temp/FLASH-Expert/`：上游 github.com/boxu-pku/FLASH-Expert 浅克隆，18 skill ≈ 48,000 行（知识层 11 + 工具层 5 + 操作层 2），配套 AGENTS.md/CLAUDE.md、agent/{LESSONS_LEARNED, GOVERNANCE, ARCHITECTURE, TEMPLATES}。

### 2.2 代码锚点核实结果（skill 编写前已验证存在）

| 锚点 | 状态 |
|---|---|
| `flash/scenarios/private/tracer/`（CHTi/TiTi/VCH_ml/OneSi_ml/OneC_ml/SNB 等） | ✅ 存在 |
| `flash/input_gen/gen_flychk_his/` | ✅ 存在 |
| `flash/input_gen/gen_eos_op/`（GEN_EOS_OP_GUIDE.md、eosop_pro、ionmix） | ✅ 存在 |
| `scripts/04_backup/usb_backup.py` | ✅ 存在 |
| `flash/output_pro/loader` + `extraction_modes.py` + `plotter` | ✅ 存在 |
| `pf_*` 系列脚本与 `CASES_Comp` 目录 | ❌ **全仓不存在** → flash-cases-focus-plot 不可独立成 skill |
| `docs/flash4_ug_4p8.md`、`input_gen/gen_otherf90s/ref_f90s/` | ❌ 不存在（skills-map 死链） |

### 2.3 layer3/flash 素材（仅作提取源，不回写）

- `flash-scenario-family/SKILL.md`：内容扎实（SCENE VARS 模板 + build_family、cn4/IONMIX4 能群核查、运行时三开关 _F、tmax 覆盖守卫、套件批量测试、WSL 故障快查），仅 §7 硬编码需重写。
- `.workbuddy/memory/reference/SNB_FLASH_reference.md`（105KB SNB 工程参考全文）。
- `gen_eos_op/.workbuddy/memory/MEMORY.md`：IONMIX cn4/cnr 判据、E12.6 指数溢出正则、uk/uv 标记、绘图规约（含硬编码解释器路径，需删）。

### 2.4 用户级 skill 素材（重写来源，不直接搬运）

纳入候选：`snb-flash-scenario-setup`（60KB）、`flash-to-flychk-history`、`hpc-sftp-parallel-fetch`、`physimx-h5py-yt-extract`、`physimx-h5py-batch-read`、`physimx-float64-cv-fix`、`physimx-flash-backup-verify`。

不纳入（外部仓库依赖或代码已不存在）：`flash-cases-focus-plot`（pf_*/CASES_Comp 已不存在）、flychk 四件套、spectime 双 skill、`knnum-mc-ploter`、`eos-table-family-census`、`literature-citation-graph-harvest` 等。

已知通病（重写时修正）：physimx-* 9 个 skill 双重 frontmatter → 统一单一 frontmatter；`cascade_parent` 相对路径依赖旧仓库布局 → 改为仓内语义路径。

---

## 3. 目录布局与命名规范

### 3.1 目标目录树

```
sandwich/flash/
├── AGENTS.md                          # 新增：顶层 Agent 索引（Codex/OpenCode/Cursor 等原生读取）
├── CLAUDE.md                          # 新增：@AGENTS.md 导入桥接（Claude Code 专用，2–3 行）
├── skills/
│   ├── README.md                      # 目录说明 + SKILL.md 模板 + 防腐锚点
│   ├── flash-sim-overview/SKILL.md    # P0 入口导航
│   ├── flash-scenario-setup/
│   │   ├── SKILL.md
│   │   └── references/                # SNB 部署/端到端长文、SNB_FLASH_reference.md
│   ├── flash-scenario-family/SKILL.md
│   ├── flash-run-deploy/SKILL.md
│   ├── flash-output-analysis/SKILL.md
│   ├── flash-par-gen/SKILL.md
│   ├── flash-eos-op/SKILL.md
│   ├── flash-flychk-history/SKILL.md
│   ├── flash-hpc-fetch/SKILL.md
│   ├── flash-data-extract/SKILL.md
│   ├── flash-backup-verify/SKILL.md
│   ├── flash-knowledge/               # FLASH-Expert 知识层吸收（导航型）
│   │   ├── SKILL.md
│   │   └── knowledge/                 # 按需精选拷贝（laser/eos/hydro，标上游 commit）
│   └── flash-pitfalls/SKILL.md        # 报错→根因→修复库
└── scripts/
    └── sync_workbuddy_skills.py       # 新增：WorkBuddy 同步脚本
```

### 3.2 单 skill 内部结构规范

- **SKILL.md**：主文件，目标 ≤200 行。frontmatter（`name` / `description`，单一 frontmatter，禁双重）+ 正文。frontmatter 结束后首行写防腐锚点：`> 最后核对：YYYY-MM-DD · commit <8位hash>`；上游吸收内容另加 `> 上游：FLASH-Expert @ <hash>`。
- **references/**：仅长文/大参考。SKILL.md 按需指引，不默认加载。
- **scripts/**：原则上**不设**——脚本实现留在仓库原位（scripts/、flash/ 子包），SKILL.md 只写调用方式与护栏，避免双份拷贝漂移。
- **命名规范**：统一 `flash-` 前缀 + 小写连字符。操作型 skill 用「flash-<动作>」，知识型为 `flash-knowledge` / `flash-pitfalls`，与上游 18 skill 名称区分，避免触发词抢答。

### 3.3 AGENTS.md 结构

1. 项目一句话简介 + 快速上手命令（start_flash.py / Makefile test / flash-cred）。
2. 技能索引表：| skill | 触发场景 | 关键入口（命令/模块） |。
3. **分工声明**：flash-sim 工具操作走本仓 skills/；FLASH 物理/参数语义问答走 flash-knowledge / flash-pitfalls。
4. MCP 提示：`python mcp_server.py` 接入方式（引用 mcp_server.py 头部说明，不复制）。
5. 指向 `skills/README.md` 与 `docs/README.md`。

---

## 4. Skill 清单与优先级

| # | skill | 来源素材 | 重读的代码锚点 | 优先级 |
|---|---|---|---|---|
| 1 | flash-sim-overview | README.md + mcp_server OVERVIEW_TEXT | 仓库根结构、flash/ 子包 README | P0 |
| 2 | flash-scenario-setup | 用户级 snb-flash-scenario-setup + layer3 SNB reference | flash/scenarios/README、private/SNB、gen_newpara、flash_run README | P1 |
| 3 | flash-scenario-family | layer3 flash-scenario-family | flash/scenarios/private/tracer/* | P1 |
| 4 | flash-run-deploy | docs/FLASH三模式运行体系 + flash_simulation_execution_knowledge | flash_run/env、flash_run/remote、scripts/02_hpc | P1 |
| 5 | flash-output-analysis | output_pro/README + 上游 result-analyzer 诊断清单 + flash-cases-focus-plot 方法论（仅 pcolormesh 纪律/csnd 派生场） | output_pro/loader、extraction_modes.py、plotter | P1 |
| 6 | flash-par-gen | docs/par_format_guide + input_gen/README | gen_par、gen_checker、gen_newpara | P1 |
| 7 | flash-eos-op | gen_eos_op/GEN_EOS_OP_GUIDE + layer3 gen_eos_op MEMORY 经验 | flash/input_gen/gen_eos_op/eosop_pro、ionmix | P2 |
| 8 | flash-flychk-history | 用户级 flash-to-flychk-history | flash/input_gen/gen_flychk_his/ | P2 |
| 9 | flash-hpc-fetch | 用户级 hpc-sftp-parallel-fetch | scripts/02_hpc/ | P2 |
| 10 | flash-data-extract | 用户级 physimx-h5py-* 三合一（含 float64-cv-fix） | output_pro/loader、extraction_modes.py | P2 |
| 11 | flash-backup-verify | 用户级 physimx-flash-backup-verify | scripts/04_backup/usb_backup.py | P2 |
| 12 | flash-knowledge | 上游 11 知识层 skill 精选 | temp/FLASH-Expert/skills/flash-{laser..multispecies} | P2 |
| 13 | flash-pitfalls | 上游 flash-pitfall-finder 19 条 + 本仓工程铁律合并去重 | temp/FLASH-Expert/skills/flash-pitfall-finder/ | P2 |

### 4.1 FLASH-Expert 18 skill 吸收方式：精选吸收，不整体搬入

理由：`temp/` 已 gitignore 不随分发；手册转写有「学术研究使用」版权约束（吸收计划 §5）；48,000 行全量入库违背 skill 精简原则。处置：

- **知识层 11**：不复制原文主体。`flash-knowledge/SKILL.md` 每单元写 20–40 行精华（物理原理一句 + 关键参数语义表节选 + 典型坑一句），保留 `source/.../F90:行号` 锚点与 `last_verified`；`knowledge/` 五件套仅按需拷贝 2–3 个高频单元（laser/eos/hydro），标上游 commit hash。其余单元注明「原文在 temp/FLASH-Expert（git pull 更新通道），需要时按单元读取」。
- **工具层 5**：`param-index.md`（150+ 参数）收纳 `docs/reference/param_index_flash48.md`（吸收计划 §3.3 既定）；pitfall-finder 19 条 → flash-pitfalls；source-reader / manual-search / setup-builder 不搬（知识已由 flash-knowledge 覆盖）。
- **操作层 2**：case-runner 的日志解析关键字段（dt/nstep/simTime/block 数/NaN）并入 flash-run-deploy；restart 的 checkpointFileNumber+NXB 一致性校验点并入 flash-run-deploy 与 flash-scenario-family；result-analyzer 诊断清单并入 flash-output-analysis。不搬其 setup/make/mpirun 流程（与三模式体系重叠，吸收计划 §3.5 已定）。
- 吸收产物统一标注：`上游：github.com/boxu-pku/FLASH-Expert @ <commit>`。

### 4.2 三副本取舍原则

**以 sandwich/flash 为唯一事实源**；layer3 与用户级仅作只读素材源，提取后不回写；用户级对应条目在内容并入后标记 deprecated（另行整理清单，不在本仓 git 内操作）。

---

## 5. 多 Agent 兼容与同步机制

### 5.1 入口文件

- **AGENTS.md**：单一事实源，Codex / OpenCode / Cursor / Zed / Warp / Amp / Factory / Jules / VS Code / Copilot 原生读取。
- **CLAUDE.md**：首行 `@AGENTS.md` 导入（Anthropic 官方推荐桥接方式；Windows 下优于 symlink——symlink 需管理员/开发者模式），可附 Claude 专属注意事项。
- Gemini CLI 用户：在其配置中设 `context.fileName=AGENTS.md`（写入 AGENTS.md 使用说明即可，不改工具配置）。

### 5.2 WorkBuddy 项目级 `.workbuddy/skills/` 同步：复制脚本方案

| 方案 | 结论 | 理由 |
|---|---|---|
| **复制脚本（选定）** | ✅ | Windows 零权限；`.workbuddy/` 本地生成物不入 git，单向镜像幂等；可 `--dry-run` 预览 |
| symlink | ❌ | Windows 需特权，git `core.symlinks` 默认 false，多机分发不可靠 |
| git hook 自动同步 | ⭕ 可选增强 | 需用户先启用 hooksPath，不作唯一机制 |

`scripts/sync_workbuddy_skills.py`（纯标准库）：
- 行为：清点 `skills/*/`（跳过 README.md）→ 镜像复制到 `.workbuddy/skills/<name>/` → 删除目标中源里已不存在的 skill 目录 → 输出变更清单。
- 参数：`--dry-run` 只打印；`--check` 仅校验一致性并以退出码报告（可挂 CI）。
- `.gitignore` 确认 `.workbuddy/` 已忽略。
- 可选增强（不阻塞）：现有 `scripts/git-hooks/pre-commit` 末尾追加软提醒「skills/ 有变更时运行 sync 脚本」，仅提醒不阻断。

---

## 6. 防腐与门禁机制

1. **锚点规范**：每篇 SKILL.md 头部 `> 最后核对：YYYY-MM-DD · commit <hash>`；上游吸收另加 `> 上游：FLASH-Expert @ <hash>`。
2. **check_docs.py 扩展**（Phase 3，唯一门禁代码改动）：
   - `MD_PATTERNS` 增加 `"SKILL.md"`（AGENTS.md/CLAUDE.md 一并加入）；
   - 锚点校验条件从「README*」扩为「README* 或 SKILL.md」；
   - **`DEFAULT_EXCLUDES` 追加 `"temp"`**（必须，否则扫到 temp/FLASH-Expert 的 18 个上游 SKILL.md 产生海量误报）；
   - 敏感信息扫描复用现有 SENSITIVE_RES，自然覆盖 SKILL.md。
3. **skills-map.md 重写**（修 3 处死链）：删 `docs/flash4_ug_4p8.md` 行；修正 `gen_otherf90s/ref_f90s` 为当前实际布局；删除已不存在的用户级/项目级 skill 行；表结构改为「仓内 skill ↔ docs ↔ flash.* 模块」三列。
4. **DUAL_MODE_TESTING.md**：文件头加「已过时（早于三模式定案），仅历史参考」标注。
5. **mcp_server.py**：`OVERVIEW_TEXT` 增加 skills/ 索引段（Phase 3，唯一一处代码内容改动）。

---

## 7. 分阶段实施计划

### Phase 0 — 骨架与分发机制（约半天）✅ 2026-11-06 完成

- [x] `skills/README.md`（含 SKILL.md 模板）
- [x] `AGENTS.md`、`CLAUDE.md`
- [x] `skills/flash-sim-overview/SKILL.md`
- [x] `scripts/sync_workbuddy_skills.py`
- [x] `.gitignore` 确认 `.workbuddy/` 忽略（§1.5 既有规则，无需修改）

**验证**：check_docs 通过 ✅；`sync_workbuddy_skills.py --dry-run/--check` 输出正确镜像计划 ✅。

### Phase 1 — 核心工作流 skill 重写（1–2 天）✅ 2026-11-06 完成

- [x] skill #2 flash-scenario-setup（含 references/：SNB_FLASH_reference.md 105KB + flashsnb-build-and-deploy.md + end-to-end-workflow.md）
- [x] skill #3 flash-scenario-family（已重写硬编码 §7 → 通用 objdir 表述 + check-env 指引）
- [x] skill #4 flash-run-deploy
- [x] skill #5 flash-output-analysis
- [x] skill #6 flash-par-gen

**验证**：check_docs 通过 ✅；引用路径均存在 ✅；6 个 skill 已镜像 `.workbuddy/skills/` ✅。

### Phase 2 — 外围 skill + FLASH-Expert 吸收（1–2 天）✅ 2026-11-06 完成

- [x] skill #7–#11（eos-op 101 行 / flychk-history 83 行 / hpc-fetch 115 行 / data-extract 113 行 / backup-verify 84 行）
- [x] flash-knowledge/（11 单元导航 146 行 + laser/eos/hydro 五件套精选拷贝至 references/）
- [x] flash-pitfalls/（上游 19 条 + 本仓铁律合并，79 行）
- [x] `docs/reference/param_index_flash48.md` 收纳（~150 参数，15KB）
- [x] 记录上游 commit hash（FLASH-Expert @ 25013c5）

**验证**：链接校验通过；13 个 skill 已镜像 `.workbuddy/skills/`。

### Phase 3 — 索引修正与门禁（约半天）✅ 2026-11-06 完成

- [x] `docs/skills-map.md` 重写（3 处死链已修，改三向索引）
- [x] `check_docs.py` 扩展（+temp/.workbuddy 排除 +SKILL.md/AGENTS.md 模式）
- [x] `mcp_server.py` OVERVIEW 更新（skills/ 索引段，语法已验证）
- [x] DUAL_MODE_TESTING.md 过时标注
- [x] 用户级旧 skill deprecated 清单（见下表，标记动作待用户确认后在 `~/.workbuddy/skills/` 侧执行）
- [x] 本计划文档勾选完成状态

**用户级 → 仓内 skill 映射（deprecated 待标记清单）**：

| 用户级 skill（`~/.workbuddy/skills/`） | 状态 | 仓内替代 |
|---|---|---|
| snb-flash-scenario-setup | 内容已并入 | skills/flash-scenario-setup |
| flash-to-flychk-history | 内容已并入 | skills/flash-flychk-history |
| hpc-sftp-parallel-fetch | 内容已并入 | skills/flash-hpc-fetch |
| physimx-h5py-yt-extract / physimx-h5py-batch-read / physimx-float64-cv-fix | 内容已并入（三合一） | skills/flash-data-extract |
| physimx-flash-backup-verify | 内容已并入 | skills/flash-backup-verify |
| flychk 四件套 / spectime 双 skill / knnum-mc-ploter / eos-table-family-census 等 | 保留原位（外部仓库依赖，不在本计划范围） | — |

**验证**：`check_docs.py` 全仓扫描 126 篇 · ERROR=0（2 条既有 WARN 为非本次引入：deploy/README 版本号误报、根 README 锚点位于 1500 字符截断窗口外）；sync `--check` 一致；改动 py 文件经 black/ruff 复验无新增违规（mcp_server.py 既有 35 条风格项非本次引入）。

---

## 8. 风险与对策

| 风险 | 对策 |
|---|---|
| 敏感信息入 git（凭据、/root/QC、机器名、解释器路径） | 重写时统一占位符化；check_docs 敏感启发式覆盖 SKILL.md；Phase 1/2 每篇过一遍 SENSITIVE_RES |
| skill 与代码漂移 | 防腐锚点 + check_docs 路径/模块校验；脚本不复制进 skill，留仓库原位 |
| FLASH-Expert 版权（手册转写） | 仅私有研究线；knowledge/ 仅精选 2–3 单元；不复制大段源码 |
| 三副本冲突 | sandwich 为唯一事实源；layer3/用户级只读提取；完成后旧条目标 deprecated |
| 上游漂移（temp git pull） | 吸收产物标上游 commit；temp 保留 git 更新通道 |
| 触发词抢答 | AGENTS.md 分工声明 + 命名规范（操作型 vs 知识型区分） |
| 双重 frontmatter 历史通病 | 统一单一 frontmatter 模板（写入 skills/README.md） |
| WorkBuddy 同步遗忘 | sync 脚本 `--check` 可入 CI；pre-commit 软提醒 |

---

## 9. 附录

### 9.1 SKILL.md 模板

```markdown
---
name: flash-<name>
description: <一句话说明何时使用本 skill，含触发场景关键词>
---

> 最后核对：YYYY-MM-DD · commit <8位hash>
> （如含上游吸收内容）上游：FLASH-Expert @ <hash>

## 适用场景
## 前置条件
## 操作步骤（命令/模块调用方式）
## 护栏与铁律（禁止事项、稳定性判据）
## 常见坑
## 关联资源（docs/、flash.* 模块、references/）
```

### 9.2 CLAUDE.md 模板

```markdown
@AGENTS.md
```

### 9.3 sync 脚本用法

```bash
python scripts/sync_workbuddy_skills.py            # 全量镜像
python scripts/sync_workbuddy_skills.py --dry-run  # 只打印计划
python scripts/sync_workbuddy_skills.py --check    # 一致性校验（CI 可用）
```
