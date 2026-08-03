# FLASH Skills / Docs / 流程文档 再组织计划

## 一、当前问题分析

| 痛点 | 原因 |
|------|------|
| WorkBuddy 不知道用 `input_gen/` 生成 .par | `flash-create-simulation` skill 太自包含，没有指向现有模块 |
| WorkBuddy 不知道用 `output_processors/` 分析 | `flash-output-processor` skill 也一样自包含 |
| WorkBuddy 不知道有 `test/grid_redex/`、`test/newpara/` 等模板 | 没有任何 skill 提及这些模板 |
| 9 个 PhySimX 级 cascade skill 过于通用 | 仅包含原则性指导，不包含 FLASH 具体操作路径 |
| 10 个 memory 日志 + MEMORY.md 没有被有效利用 | 没有记录哪些代码已被验证 |

**根因：不存在一个"FLASH 编排器"知道 FLASH 有哪些模块可用，以及何时用哪个。**

---

## 二、设计方案

### 核心思路：三层结构

```
上层 (简单轮廓)：        ~/.workbuddy/skills/flash/README.md
中层 (模块技能)：        ~/.workbuddy/skills/flash/xxx/SKILL.md
下层 (API 引用)：        ~/.workbuddy/skills/flash/xxx/references/api-ref-xxx.md
项目层 (代码引用)：      input_gen/  output_processors/  flash_run/
```

**每层只指向下一层，不越级。** WorkBuddy 通过"意图识别→模块技能→API 引用→Python 模块"的链条快速定位到现有代码。

---

## 三、具体步骤

### Phase 0 — 准备（创建 flash/ 命名空间）

**Step 0.1**: 创建 `~/.workbuddy/skills/flash/` 目录

### Phase 1 — 创建上层轮廓

**Step 1.1**: 在 `flash/README.md` 中创建极简大纲

- 只写一段话描述 FLASH 模块包含哪些能力
- 列出 7 个子技能的 1 行简介
- 约定："定稿后不要修改本文件，只修改子技能"

### Phase 2 — 创建中层模块技能（7 个子技能）

**Step 2.1 — `flash-workflow-orchestrator/SKILL.md`** ★ 最关键

这是 FLASH 专用的 Level 0 元技能。描述意图→技能→代码的映射关系：

```
用户意图 → 子技能 → Python 模块 → 核心 API

"生成 .par 文件" → flash-input-gen → input_gen/gen_par/ → ParGeneratorExtended
"运行仿真"      → flash-run-deploy → flash_run/env/ → FlashEnvManager
"分析 HDF5"     → flash-output-process → output_processors/ → FlashDataLoader
"开发 F90"      → flash-f90-dev → gen_otherf90s/ → BlockGenerator
"创建测试"      → flash-test-templates → test/grid_redex/ → step1_generate_par.py
```

同时定义**优先级规则**：
1. 有现成模块 → 直接引用，不从头写
2. 有测试模板 → 复制并修改，不新建
3. 先查 memory 日志 → 再做决定

**Step 2.2 — `flash-input-gen/SKILL.md`**（替代旧的 flash-create-simulation）

- 大纲：5 步流程（Config→Simulation_data→Simulation_init→initBlock→.par）
- 引用 `input_gen/gen_par/defaults.py` 作为参数权威出处
- 引用 `docs/par_format_guide.md` 排版规则
- 引用 `input_gen/gen_checker/` 做依赖检查
- references/api-reference.md 存放：
  - ParGeneratorExtended 调用方式
  - BlockGenerator + GridBuilder 网格构建
  - NewParaGenerator 多区剖面
  - ConfigGenerator / MakefileGenerator / ShellScriptGenerator 等

**Step 2.3 — `flash-output-process/SKILL.md`**（替代旧的 flash-output-processor）

- 大纲：HDF5 读取 → 数据加载 → 可视化
- 引用 `output_processors/hdf5processor/FlashHDF5File`
- 引用 `output_processors/loader/FlashDataLoader`
- 引用 `output_processors/plotter/FlashPlotter`
- references: 各 API 签名 + 使用示例

**Step 2.4 — `flash-run-deploy/SKILL.md`** ★ 新增

- 大纲：本地运行 / WSL 运行 / 超算远程 / 批量
- 引用 `flash_run/env/FlashEnvManager`
- 引用 `flash_run/remote/FlashRemoteDeploy`
- 引用 `flash_run/remote/RouteTester` 选最优路由
- 引用 `test/remote_connect/` 诊断脚本

**Step 2.5 — `flash-f90-development/SKILL.md`** ★ 新增

- 大纲：5 步新增参数 + 增量边界模式 + 物种名 ≤4 字符
- 引用 `input_gen/gen_otherf90s/ref_f90s/` 全部 5 个子目录的参考文件
- 引用 `test/newpara/README.md` 多区控制参考
- 引用 `test/newpara/flash_profile/` 5 种剖面类型
- references: f90 变体选择矩阵

**Step 2.6 — `flash-test-templates/SKILL.md`** ★ 新增

- 大纲：测试模板选择矩阵
- 网格分辨率 → test/grid_redex/
- 多区密度 → test/newpara/
- 快速绘图 → test/hdf5ploter_easy/
- 数学测试 → test/math_test.py
- 远端诊断 → test/remote_connect/

**Step 2.7 — `flash-examples/SKILL.md`** ★ 新增

- 5 个典型场景的完整代码示例（一行一行地写）
- example-2beam-al.md
- example-grid-resolution.md
- example-multi-zone-density.md
- example-batch-hpc.md
- example-new-parameter.md

### Phase 3 — 清理旧的单文件 skill

**Step 3.1**: 删除 `~/.workbuddy/skills/flash-create-simulation/`

内容已全部迁移到 `flash/flash-input-gen/`

**Step 3.2**: 删除 `~/.workbuddy/skills/flash-output-processor/`

内容已全部迁移到 `flash/flash-output-process/`

**Step 3.3**: 修复 `~/.workbuddy/skills/flash-source-lookup/` 嵌套结构

当前：`flash-source-lookup/flash-source-lookup/SKILL.md`（嵌套一层）
改为直接：`flash-source-lookup/SKILL.md`

### Phase 4 — 更新项目级 skills

**Step 4.1**: 更新 `flash/.workbuddy/skills/CASCADE.md`

以前引用的是 9 个通用 PhySimX skill，现在增加 FLASH 特定技能路径

**Step 4.2**: 创建 `flash/.workbuddy/skills/flash-orchestrator-activator.md`

一个小型 cascade skill，`frequency: always`，其唯一作用就是：
- 告诉 AI "你在 flash 目录下工作，请加载 ~/.workbuddy/skills/flash/flash-workflow-orchestrator 来理解 FLASH 模块结构"
- 引用最近 3 天的 memory 日志做上下文感知

**Step 4.3**: 更新 `flash/.workbuddy/skills/CASCADE.md` 引用这个新的 activator

### Phase 5 — 更新文档

**Step 5.1**: 在 `flash/docs/` 创建 `docs/skills-map.md`

一个双向索引表：
```
技能名称              → docs 文件           → Python 模块
flash-input-gen      → docs/README.md      → input_gen/gen_par/
...                  → par_format_guide.md  → ...
```

**Step 5.2**: 更新 `flash/.workbuddy/memory/MEMORY.md`

添加关于新技能结构的记录："FLASH 技能已重组为 flash/ 命名空间，包含 7 个子技能"

---

## 四、执行顺序

```
Phase 0  ──→  Phase 1  ──→  Phase 2  ──→  Phase 3  ──→  Phase 4  ──→  Phase 5
 创建目录     写轮廓      写 7 个子技能     清理旧文件    更新级联     更新文档索引
```

每个 Phase 完成后，WorkBuddy 会：
1. ✅ 保存截图/输出
2. ✅ 追加当天的 memory 日志
3. ✅ 等待您确认后才进入下一 Phase

---

## 五、风险评估

| 风险 | 缓解措施 |
|------|----------|
| 旧的 flash-create-simulation/ 中可能有遗失内容 | 迁移前先读取旧文件全文，确认全部涵盖 |
| cascade 映射路径不对导致不会自动加载 | 只使用 `~/.workbuddy/skills/` 绝对路径 |
| 修改后 WorkBuddy 仍然不按新结构工作 | activator skill 设置 `frequency: always` 强制加载 |
| memory 日志中有重要的实验记录 | 不移除或修改 memory 目录，只追加不替换 |

---

请审阅本计划，确认后我将按 Phase 0 → Phase 5 的顺序执行。
