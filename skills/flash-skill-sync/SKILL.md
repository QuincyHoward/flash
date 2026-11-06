---
name: flash-skill-sync
description: 全体系 skill 维护更新流程：先跑 README 巡检（flash-readme-sync）→ 读根 README 建立全局视角 → 自底向上遍历所有 SKILL.md，实访其引用的文件/脚本并做接口冒烟验证（import/最小调用）→ 梳理相似 skill 的合并与边界。skill 体系巡检、代码接口变更后同步 skills、技能整合与分工梳理时使用。触发词：skill 巡检、技能维护、skill 体系、接口验证、技能合并、skill 边界、skill sync。
---

> 最后核对：2026-11-06 · commit 14e320f

# 全体系 skill 维护（flash-skill-sync）

## 适用场景

- 定期（或代码接口变更后）对 `skills/` 全体系做可用性巡检
- 新增/改名/合并 skill 后的一致性收尾
- 相似 skill 的合并决策与分工边界梳理

## 执行顺序（四步，依赖递进）

### Step 1: 先跑 README 巡检（底座）

按 `flash-readme-sync` 执行全仓 README 维护——README 是 skill 声明的对照面，
README 不准则 skill 巡检的"文档侧"失真。已有近期巡检时可只做增量：
`check_docs` 门禁 + 空 README 检查（`find ... -name README.md -empty`）。

### Step 2: 读根 `README.md`（全局视角）

通读根 README 的模块地图/工作流章节（≥L900 的模块索引表尤其重要），
建立"官方叙事"基线；skill 声明与之冲突时以代码实测为准并回改 README。

### Step 3: 自底向上遍历 skills（先底层代码，后 SKILL.md）

对每个 `skills/<name>/SKILL.md`：

1. **底层可用性先行**：该 skill 引用的模块/脚本做接口冒烟——
   Python 模块 `python -c "import ..."`（生成器/加载器实例化一次最小调用）；
   脚本 `--help` 或读头注释确认入口仍在；pytest 抽跑对应单测
   （如 `pytest flash/input_gen/test -q`）
2. **声明核对**：frontmatter（name/description/锚点）、文中引用路径存在性
   （复用 flash-readme-sync 的审计脚本思路，范围换 `skills/*/SKILL.md`）、
   跨 skill 引用（`skills/<other>/SKILL.md`）有效
3. **更新**：只修不符处；锚点更新为当日 commit；发现底层接口变更则
   同步修正 skill 正文与 references/

### Step 4: 体系梳理（合并 / 边界）

对触发词/职责重叠的 skill 对，按决策树处理：

- **触发词与操作对象基本重合（>60%）→ 合并**：保留信息量大者为主干，
  另一方精华并入其正文/references，删除旧目录，同步 AGENTS.md/skills-map/镜像
- **互补型重叠 → 边界声明**：在双方 SKILL.md 的「分工声明」写明
  "本 skill 管 X；Y 管 Z"，并在 AGENTS.md 索引行体现
- 通用型（非 flash- 专属）skill 单独分组，不与操作型混排

**当前体系边界基线**（2026-11-06 巡检定案）：
`flash-par-gen`（.par 排版规范）∥ `flash-input-gen`（生成全流程）；
`flash-output-analysis`（分析绘图纪律）∥ `flash-data-extract`（无 yt 提取/批读）；
`flash-knowledge`（源码语义问答）∥ `flash-param-lookup`（官方 rpDoc 权威定义）；
`flash-code-execute-verify`（代码级验证）∥ `flash-scenario-setup` 短时验证（场景级）；
`flash-run-deploy`（运行部署）∥ `flash-hpc-fetch`（结果回收）。

## 护栏与铁律

1. **先验证后改文档**：接口冒烟失败 → 修 SKILL.md 适配现实；代码坏了 → 报告不擅改
2. 合并/删除 skill 必须用户确认；边界声明类整理可直接做
3. 每次整理后必须同步：`AGENTS.md` 索引、`docs/skills-map.md` 三向索引、
   `sync_workbuddy_skills.py` 镜像、被并方正文中的跨引用
4. 冒烟用最小调用（1 个类实例化 / 1 条命令），不跑长仿真
5. 全程记录：更新 N / 冒烟通过 M / 失败清单 / 合并与边界决策，写入当日 memory 日志

## 常见坑

- SKILL.md 里的 references/ 文件常被改名遗忘（GUIDE→README 类改名后）——路径审计必须含 references/
- 触发词重叠 ≠ 职责重叠：先看操作对象（改什么文件）再看触发词
- 通用技能（flash-code-* 等）易被误当 FLASH 专属边界外——AGENTS.md 单独分组展示

## 关联资源

- `skills/README.md`（编写规范）、`AGENTS.md`（索引与分工声明）、`docs/skills-map.md`（三向索引）
- `skills/flash-readme-sync/`（Step 1 底座）、`scripts/08_docs/check_docs.py`（门禁）
