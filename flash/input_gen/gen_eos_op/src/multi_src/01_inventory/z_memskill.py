# -*- coding: utf-8 -*-
"""追加项目长期记忆（EOSOP 多群表族更正）+ 创建可复用技能。"""
import os, textwrap

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
MEMF = os.path.join(ROOT, '.workbuddy', 'memory', 'MEMORY.md')

ADD = """
- **r19（09-19）多群表族结构性更正 + tmp→multi_src 归档**：`.workbuddy/tmp` 按功能复制入
  **`src/multi_src/`（15 子目录 / 361 items / 0 unsorted；`README.md` 含 708 文件全清单与归档守则）**，
  排除 eosop_pro 包 r11–r16 产物（110 项）见 `EXCLUDED.md`。⚠️ 环境对 `shutil.rmtree` 有
  safe-delete 拦截 → 归档脚本须 `copytree(dirs_exist_ok=True)` 幂等、**禁删目录**；shim 无 `cp`。
  **MULTI 单群/多群表族（原"无扩展名 150 文件"）更正为 `(群表头60字符 + 带界行30字符 + 数据区)×K`**：
  **无"4 值骨架行"**（旧版误认，实为下一条群表头）、**表头每群一条**、行数 **多群 `K·(2+D)` / 单群 `1+D`**
  （`D=⌈(NR+NT+NR·NT)/4⌉`），规模实为 **404 文件 / 20 命名 / 33.3%**；群表头第 2 字段 = `<类别名> <标志>`
  （`M` 多群 / `1` 单群 / **数值=ZEFF 式**且该数值恒 6.0 非 Z）；8 位表号是 **SNOP 模板号不唯一**（材料靠目录）；
  **T1/T2 单位 = keV**（SNOP.MANUAL 38–41）表内 eV 换算 ×1000（"10× 悬案"作废），RHO1/RHO2 = g/cm³。
  `opbe` = `40×(PLANCK)+40×(ROSSELAND)+1×(ZEFF)` = 4480+4480+111 = 9071 ✓。行宽有 59–62 抖动 →
  **按列位置切分，禁 `len(line)==60` 筛选**。权威记录 `src/multi_src/04_probe/02_multigroup_planck/
  multigroup_opacity_FINAL.md`；文档 §14.5(9 子节) + §15.12.6 勘误；**文档 116,199 汉字 / 核查全绿**。
  环境坑：块替换必须 `txt[:a]+new+txt[b:]`（漏尾会整段删掉后续内容，本轮靠断言拦下）。
"""

if os.path.exists(MEMF):
    with open(MEMF, 'a', encoding='utf-8', newline='\n') as f:
        f.write(ADD)
    print('APPENDED MEMORY.md  (%d B)' % os.path.getsize(MEMF))
else:
    open(MEMF, 'w', encoding='utf-8', newline='\n').write(ADD)
    print('CREATED MEMORY.md')

# ── 技能 ─────────────────────────────────────────────────────
SK = os.path.join(os.path.expanduser('~'), '.workbuddy', 'skills',
                  'eos-table-family-census')
os.makedirs(SK, exist_ok=True)
body = """---
name: eos-table-family-census
description: 用「公式闭合」作客观判据，对一大类数值表的存储格式做全量普查与结构定案，并据此
  更正权威文档。适用于：某格式族"规模/结构/单位"存疑、需要一次查清并写进规格书；
  或需要判断一批同构文件是否属同一族。触发词：格式普查、全量覆盖矩阵、公式闭合、
  EOS/不透明度表族、表结构定案、tmp 归档到 multi_src。
agent_created: true
---

# EOS/不透明度表族：公式闭合普查 → 结构定案 → 文档更正

## 何时用
- 一份格式规格书里某族写着"规模 N 个文件 / 结构如下"，但**没有客观判据**支撑；
- 需要回答"本地这类数据到底有多少、结构是什么、能不能全读"；
- 需要把散落的探查脚本按功能归档，便于后续固化为解析器。

## 核心方法：**判据必须是"公式闭合"，不能是文件名**
1. **先猜候选结构**，写出**行数/字段数公式**（含 `⌈⌉`）。
2. 对**全树每个文件**跑公式，统计命中率。
3. **命中率不接近 100% ⇒ 结构猜错**；命中率 100% ⇒ 定案。
   > 反例价值：本轮"多群表"第一版猜 `1 + K·(2+D)`，全树 20/20 都"差 1 行"。
   > 那个恒定 +1 就是错因 —— **"所有样本一致地差同一常数"是结构错误的指纹**，
   > 应优先怀疑切分口径，而不是样本。
4. **命名只作提示，不作判据**。文件名后缀（`20`/`100`/`G`）多数吻合，
   但一定有反例（`opbe` 无名却多表串联、`MULTI67` 实测 66 群）。

## 步骤
### A. 普查
- 写一个脚本递归全树，对每个文件：
  取首行 → 按候选宽度切字段 → 校验关键字段可转数值/在合理区间 →
  数结构行（如 30 字符行）→ 算 `pred = f(...)` → 与实测行数比较。
- 输出 **TSV 逐文件矩阵** + **按族/按后缀/按目录计数表** + **不闭合清单**。
- 不闭合者**不是失败**，而是"属于别的族"或"有残差"，单列出来。

### B. 结构定案
- 把"闭合的绝大多数"作为一种结构，把**异类**单独解释（如 `opbe` = 三表串联）。
- **必须给出可复述的字节级证据**：行号、行宽、关键行原文、间距（如"30 字符行间距恒 112"）。
- 单位定案**优先找上游手册明文**，其次源码 `fprintf`，再次端点吻合。
  > 本轮 `T1/T2` 单位：手册 4 行明文一击定案，比任何推理都强。

### C. 归档（供后续固化）
- 按功能分目录；**只复制不移动**；脚本与它产生的输出**同目录**。
- 写 `README.md`：职责说明 + 全文件清单 + **后续归档约定**。
- **排除另一条工作流的产物**，并在 `EXCLUDED.md` 写明排除规则与理由。
- 复制用 `copytree(..., dirs_exist_ok=True)` 实现幂等；
  **不要用 `rmtree`**（宿主可能有 safe-delete 拦截而报错）。

### D. 文档更正（errata 驱动）
- **不改写历史**：新增勘误小节，逐条列「旧（错）→ 新（对）+ 依据 + 根因」。
- 更正后**必须做一次全文同步扫描**：旧数字、旧公式、旧术语在别的章节几乎一定还有残留
  （本轮 23 处）。用宽松模式脚本（锚点未命中记录 MISS 但不中断）批量替换，最后看 MISS 数。
- 收尾跑机械核查：字数门禁、代码围栏配对、编号唯一性、**章节编号单调性**、
  内部引用有效性、表格列数、残留 `TODO`。

## 坑（都踩过）
- **块替换写成 `t[:a] + new + t[b:]`** —— 漏掉 `+ t[b:]` 会整段删掉后面所有内容。
  下游断言能拦住它，但更该在写脚本时就检查。
- **行宽不等于常数**：表头常有 ±1 空格抖动 → 用**列位置**切分，别用 `len(line)==N` 筛选。
- **一个文件可含多张表**：解析器必须是外层循环，不能假设"一个文件一张表"。
- **类别名/标识字段可能在文件中途改变** → 每个记录都要重读，不能只读首行。
- 大文件（数 MB）用一次 `read()` 再按行切；不要逐行 `readline`。
- 环境若缺 coreutils（`ls/head/grep/cp` 等），**一律先写 `.py` 脚本文件再执行**，
  不要用内联 `python -c "...复杂字符串..."`。

## 交付物清单
1. `coverage_matrix.tsv`（逐文件）
2. `coverage_summary.md`（按族/后缀计数 + 未解析清单 + 诚实缺口）
3. `<族名>_FINAL.md`（结构定案 + 可复现脚本路径）
4. 文档的勘误小节
5. 机械核查报告
"""
open(os.path.join(SK, 'SKILL.md'), 'w', encoding='utf-8', newline='\n').write(body)
print('SKILL created:', os.path.join(SK, 'SKILL.md'), os.path.getsize(os.path.join(SK, 'SKILL.md')), 'B')
