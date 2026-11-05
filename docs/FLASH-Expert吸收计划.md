# FLASH-Expert 吸收计划

> 最后核对：2026-11-05 · commit 081dcd9 · 状态：**待执行**
> 上游：<https://github.com/boxu-pku/FLASH-Expert.git>（已克隆至 `temp/FLASH-Expert`，浅克隆；`temp/` 已 gitignore，外部仓库独立演进，`git pull` 即可更新）

---

## 1. 上游资产清单（实测盘点）

**FLASH-Expert = 面向 Agent 的 FLASH 4.8 源码级知识库**：18 个 skill ≈ 48,000 行 markdown，多 harness 通用格式（SKILL.md + description + triggers，Claude Code / ZCode / DSH / Codex CLI）。

### 三层结构

| 层 | Skill | 体量 | 核心内容 |
|---|---|---|---|
| **知识层（11）** | flash-laser / driver / grid / hydro / eos / radtrans / sourceterms / material / io / diffuse / multispecies | 各 100–160K | 每个含五件套 `knowledge/`：overview（物理原理+设计动机）、params（参数字典）、internals（调用图+源码流程）、recipes（可抄 parfile 配置集）、pitfalls（单元内踩坑）+ `examples/` 纯 parfile |
| **工具层（5）** | flash-source-reader / **pitfall-finder** / **param-query** / **manual-search** / setup-builder | 32–212K | 源码定位中文解释；**19 条实战报错库**（pitfalls/*.md）；**150+ 核心参数索引**（含单位/典型值）；**31 篇手册转写（661 页→markdown）**；setup 命令生成 |
| **操作层（2）** | flash-case-runner / flash-result-analyzer | 164/204K | setup→make→run→restart 生命周期；yt 可视化/能量守恒/激光吸收率分析 |

### 配套资产

- `agent/LESSONS_LEARNED.md`：20 条建设经验（L-001~L-020，含 L-016 species 命名长度限制、L-018 restart 显式 IO 编号、L-020 MPI 崩溃取证方法论）
- `agent/GOVERNANCE.md` / `TEMPLATES/` / `workflows/`：skill 治理与草稿审核流程（`promote_draft.sh`）
- 源码锚点纪律：知识条目全部带 `source/.../xxx.F90:行号` 锚点 + `last_verified` 日期
- 质量声称：75 道验收考题全过；4 个算例实战验证（LaserSlab 4.6.2/4.8 + Sunliang_laser_CH + Sunliang_Xray）

---

## 2. 互补性分析（我们有什么 / 缺什么 / 它补什么）

| 能力 | flash-sim（本项目） | FLASH-Expert | 关系 |
|---|---|---|---|
| FLASH 输入自动生成 | ★★★ input_gen 12 个 gen_*（par/Config/initBlock…） | ✗（只讲怎么手写 parfile） | **我们强** |
| 场景化执行编排 | ★★★ scenarios + flash_run（WSL/超算/insitu 四模式、护栏、断点续跑） | △ case-runner 是裸 FLASH 手动流程 | **我们强，其诊断知识可借** |
| 输出分析 | ★★★ output_pro（hdf5/loader/plotter + 对拍 yt） | △ result-analyzer 有能量守恒/吸收率/yt 方法 | 互补（见 §3.4） |
| **FLASH 参数语义知识** | ★★ gen_par defaults 有值但**缺单位/物理含义/典型值系统化** | ★★★ param-index 150+ 参数 + 各单元 params.md | **它强 → 注入** |
| **FLASH 单元内部机理** | ★（散见 README 提示） | ★★★ 11 单元 internals/overview 带源码锚点 | **它强 → 直接挂载** |
| **报错→根因→修复库** | ★★ 工程铁律 7 条 + hello_flash 已知问题 | ★★★ 19 条结构化踩坑库（含 xray/restart/EOS 收敛） | **合并去重** |
| **官方手册可检索性** | ★（无手册） | ★★★ 31 篇转写 | **直接收纳（注意版权隔离）** |
| Agent 触发/治理机制 | ★★ WorkBuddy skills 体系 | ★★★ 验收考题/草稿审核/经验沉淀流程 | 借鉴方法论 |

**结论**：两者是**"知识大脑"与"执行四肢"**关系——FLASH-Expert 回答"FLASH 怎么工作、参数什么含义、为什么报错"；flash-sim 解决"怎么自动生成/跑/分析"。结合后 Agent 可**带物理知识驱动工具链**（如：查 ed_maxBeams 语义 → 直接改 gen_par 配置 → 场景跑通）。

---

## 3. 吸收策略（五类处置，逐 skill 定案）

### 3.1 直接挂载（零改造，立即生效）—— 全部 18 个 skill

- **方式 A（推荐）**：WorkBuddy 用户级技能——按其 SKILL.md 结构适配为本仓库技能（保留 knowledge/ 原文）；或
- **方式 B**：项目级 `.agents/skills/` 符号链接/复制挂载（其 `install.sh --copy` 支持 Windows）；
- **挂载点注意**：18 个 skill 的 description/triggers 与本项目 WorkBuddy skills **无命名冲突**（其前缀 `flash-`，我们的是操作型 skill）；在 CLAUDE.md/AGENTS.md 层面声明「flash-sim 工具操作走本仓 skills，FLASH 物理问答走 flash-* 知识库」，避免抢答。

### 3.2 踩坑库合并（flash-pitfall-finder ↔ 本项目实战沉淀）

| 上游条目 | 本项目对应 | 处置 |
|---|---|---|
| `libmpi-conflict.md` | flash_run/README §7.4（module purge + Intel MPI 库路径） | 交叉引用：两方案对应**不同机器形态**（其 LD_PRELOAD 方案=裸 Linux 本机；我们=超算 module 体系），互挂链接不合并 |
| `restart-incompatibility` / `restart-*` 3 条 | hpc-remote 断点续跑（hpc_task.json） | 补入我们 restart 流程的**checkpointFileNumber+NXB 一致性**校验点 |
| `eos-newton-convergence` / `negative-3t-internal-energy` / `ffpe-trap-and-nan` | （无） | 直接采纳 → 注入 gen_checker 前置校验思路 + 场景 README |
| `species-name-and-hdf5`（L-016） | Layer_tracer 8 材料场景 | 对照检查我们的 species 命名（Ti/V 短名已合规，记录为规则） |
| `xray-imaging-setup` / `xray-sideon-crash-sortparticles` | （无 xray 诊断场景） | 暂存——未来 X 射线诊断场景的现成参考 |
| `h5py-flash-plotfile-index-order` | output_pro hdf5pro 对拍经验 | 与 `compare_h5py_vs_yt.py` 结论交叉核对 |

### 3.3 参数知识注入（param-index + 11 × params.md → input_gen / gen_checker）

- `gen_par/defaults.py`（810 行）与 `gen_config`：用 param-index 的**单位/典型值/含义**三列校对补全参数注释——生成器产出的 `.par` 注释直接携带物理语义；
- `gen_checker`：把上游 12 类 abort 模式（flash-laser SKILL 所列）转化为**生成期静态校验规则**（能群一致性已有，可加 species 命名长度、ed_ 参数范围等）；
- `flash-param-query/knowledge/param-index.md` 单独收纳为 `docs/reference/` 查询资产。

### 3.4 分析方法对照（flash-result-analyzer ↔ output_pro）

- 激光吸收率（读 `LaserEnergyProfile.dat`）与能量守恒检查 → 评估是否作为 output_pro 新增派生量/分析入口（对齐 `FLASH物理量说明.md` 字典）；
- yt 可视化方法我们已有对拍基线（57 passed），只借鉴其**诊断检查清单**，不引入其脚本。

### 3.5 不吸收 / 暂缓

| 项 | 理由 |
|---|---|
| `flash-case-runner` 的 setup/make/mpirun 操作流程 | 与场景系统重叠且面向裸 FLASH 目录；只取其**日志解析关键字段**（dt/nstep/simTime/block 数/NaN）充实 flash_run 日志知识 |
| `flash_env.sh`（LD_PRELOAD 方案） | 机器特定（其 ares 本机）；我们 WSL/超算方案已验证，仅记录对照 |
| `flash-setup-builder` | 我们有 gen_makefile/gen_config 自动化，保留其 setup 语法知识供参考 |

---

## 4. 分阶段实施

| 阶段 | 内容 | 产物 | 验证 |
|---|---|---|---|
| **P1 挂载即用** | 18 skill 复制/链接挂载（方式 A 或 B）+ AGENTS/CLAUDE 层声明分工；`temp/FLASH-Expert` 保持 `git pull` 更新通道 | Agent 即获 FLASH 物理问答/排障能力 | 用其 §5 的 4 道测试题实测触发 |
| **P2 踩坑库合并** | §3.2 表逐条处置：交叉引用 2 条、采纳 6 条、暂存 2 条 | flash_run/README §7 扩充、gen_checker 新规则提案 | pytest 基线不回退 |
| **P3 参数知识注入** | param-index 校对 defaults.py/gen_config 注释；param-index 收纳 docs/reference/ | 生成器参数带物理语义 | 生成 .par 抽查注释 |
| **P4 手册库收纳** | 31 篇转写移入**私有参考区**（见 §5 版权），建索引页 | docs 可检索的 FLASH 权威参考 | 手册索引链接校验 |
| **P5 分析增强（可选）** | 激光吸收率/能量守恒入口评估 | output_pro 提案（不立即实现） | — |

## 5. 版权与合规边界（硬约束）

- FLASH-Explorer 上游标注**「仅供学术研究使用」**；其手册转写（661 页）是 FLASH User Guide 的衍生品——**全部吸收内容只进私有研究线**，**不得进入 PyPI 发布包 / public 分区**（与本项目 `public/private` 分区纪律一致）；
- 其 knowledge 中引用的 FLASH 源码片段遵守 FLASH License §4 声明惯例，我们引用时保持锚点+出处，不再复制大段源码；
- 本计划文档与后续吸收产物均**不包含** FLASH 源码本体。

## 6. 风险

| 风险 | 对策 |
|---|---|
| 18 skill 触发词过宽，与 WorkBuddy skill 抢答 | 分工声明写在挂载层协议文件；用其验收考题实测调整 |
| 上游持续更新，复制模式会漂移 | temp 保留 git 通道；吸收产物标注上游 commit hash |
| 手册转写版权 | §5 硬约束：私有区隔离 |
| 知识与本仓 FLASH 4.8 配置不一致（其含 4.6.2 经验） | 吸收条目保留其 `last_verified` 字段；冲突以本仓实测为准 |

---

**下一步**：等用户批准后从 P1 开始执行。
