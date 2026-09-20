# -*- coding: utf-8 -*-
"""追加 r20 日志：FEOS 源码裁定 + 第 2 字段更正 + 覆盖矩阵接入。"""
import os
ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
MEM = os.path.join(ROOT, '.workbuddy', 'memory')

ADD = """
## r20：FEOS 源码裁定四问 + 第 2 字段"类别码"更正 + 覆盖矩阵接入

### 1. 代理状况（诚实记录）
- `rev-feos-src2`：**FAILED**（网络故障 `getaddrinfo ENOTFOUND copilot.tencent.com`，502）。
  落盘探针 `feos_src_q1/q1b/q2/q4.*` 但**未交付** `feos_src_adjudication.md`。
  经核查该任务**输入全在本地**（`vendor/FEOS_src/`），**不需要联网** ⇒ 由主理人**直接接手完成**。
- `xval-materials`：**成功**。产出 `coverage_matrix.tsv`(181 KB / 1213 行) + `coverage_summary.md`
  + `cross_validation_round2.md` + `cov_*`/`xv2*` 脚本（已归档到 `05_cross_validation/`）。

### 2. FEOS 源码裁定（§15.12.8 新增，交付 `04_probe/04_feos/feos_src_adjudication.md`）
| # | 裁定 | 依据 |
|---|---|---|
| 1 | **`.feos` 头 `TRef` 单位 = eV**（Hartree 说作废） | `FE-01_TABTOOLS.C:204` `// FEOS units are cgs (+ eV for temperature)` + 全包 `*eV2Kelvin` 旁证 |
| 2 | `.feos` 行0/行1 字段序确认 | `FE-01_TABTOOLS.C:206,222-223` |
| 3 | **`.feos` 行宽 = 10×15 = 150**（"4×15"错） | `FE-00_DEFINITS.H:28` `#define SF_TRENN \"\"` + `:233…258` `if(++count%10) … else \"\\n\"` |
| 4 | `.cst` 四列确认（数密度/质量密度/压强 MBar/电荷态总和） | `FE-01_TABTOOLS.C:896-903`（格式串 `\"%e          %e          %e    %e\\n\"`） |
| 5 | **英文 `.cst` 模板 FEOS 16.7 中不存在** | 全 vendor 对 `Particle density|load state` **零命中**；德文模板在 `:897` 命中 |
| 6 | 不透明度 T 轴：**FEOS 不产出该表**（写出器穷举 10 个无此函数）⇒ 权威在 `SNOP.MANUAL` | 穷举 `^void write_` |

**方法论**：单位裁定的**首选证据 = 源码 `printf` 里自带的单位字样**
（`FE-03_MAIN.C:136` 写 `eV`、`:141` 写 `g/cm^3`），比数值反推硬。

### 3. ⚠ 第二处自我更正：数值型表头第 2 字段**不是常量 6.0**
上一轮断言"恒为 6.0（164 个文件）"**错误**。闭合集合内全量取值统计 = **只有 7 种取值**：
```
6.0               115   → ZEFF 系
1.0000000e+000     18   → LEDCOP 拆分件 (.AvSqFree/.NoFree)
0.1234567E+000     14   → LEDCOP 哨兵
4.0                 7   → Rosseland 系 (1041_ROSS / _SIMPLE_ROSSELAND)
7.0（两种写法）       8   → Planck 系 (1041_PLANCK / BE_PLANCKx03 / _SIMPLE_PLANCK)
1.0                 2   → Ta2O5_1G_MULTI / Ta_1G_MULTI
```
⇒ 它是**类别码**（文本写 `PLANCK M` 时用文本，否则用数值码）。
根因：以 17 个 ZEFF 样本外推全族常量，**未做全量取值直方图**。
**新规约 R20**：*凡声称某字段为"常量"，必须给出该字段在全体样本上的取值直方图。*

### 4. 附带确证：`.301/.304/.305` 头第 2 字段 = **密度 (g/cm³)**
用**元素密度表独立交叉验证**（Al 2.7 / Au 19.300003 / W 19.3 / Mo 10.22 / Co 8.9 / Cr 7.15 /
Bi 9.78 / Pd 12.023 / Ba 3.51 / Dy 8.54 / Sm 7.52 / Sc 2.985 / P 1.823 / O 1.26205 / N 0.857226 /
K 0.862 / Na 0.53149 / Ne 1.21798e-3 / F 1.7e-3 / Cl 3.2e-3 / Ce 6.77）**全部吻合** ⇒ 写入 §10.2。

### 5. 覆盖矩阵接入（xval-materials 产出）
- `coverage_matrix.tsv`：1,213 文件 / 20 族 / 608 可解析 / 515 部分 / 90 不可
- **31 个完全未识别** + **7 个空文件**（`material.list` 等）—— 这是"识别未完成"的真实清单
- 其中若干可**直接归位**（本轮已判）：`Ta2O5_1G_MULTI`/`Ta_1G_MULTI`（首行 `0.0 1.0 25 47`
  ⇒ 与 §15.11.2 的 `.dat_MULTI` 同族，`nρ=25, nT=47`）；`Mo_Ideal_Gas`/`W_Ideal_Gas`
  ⇒ §14.5.11 的 stub（第 2 字段 = 密度）
- **口径差异须诚实标注**：代理的"20 族"是**按命名/启发式**分类，主理人的"404 文件"是**按公式闭合**；
  两者不可直接相加（如代理"无扩展名多群不透明度表 237" ≠ 主理人"单群+多群 404"）。
  文档中两套数字**并列给出并注明口径**。

### 6. 文档操作
- `p13_feos_fix.py`：更正 §14.5.3（7 种类别码 + R20 教训）、§15.12.6 表行 2、§10.2 补密度列、
  新增 **§15.12.8**（FEOS 四问裁定）、关闭附录 E #12/#13
- `p14_close.py`：关闭 §10.4 缺口第 1 行（`.feos` 4×15 vs 10×15）
- `p15_restore.py`：**补回 §14.5 重写时丢失的 §14.5.10–14.5.13**（token 语义 / stub / 记账语法 / `_ieos`）
  —— 由审计的"内部悬空引用 §14.5.10"抓出，属**重写导致的内容回归**
- 备份：`.bak6`（§14.5 重写前）

### 7. 终态
文档 **117,428 汉字 / 584,398 字符 / 868,237 B**；核查全绿：
围栏 522 配对 ✓ / 表号唯一（仅 T11 合法占用）✓ / 章节顺序全单调 ✓ /
**内部引用 98 条全有效** ✓ / 表格 319 个列数一致 ✓ / 残留标记 0 ✓

### 8. 教训（供后续轮次）
- **重写整节 = 高风险**：必须先把该节的全部子节标题列出来，重写后逐一比对，防丢内容。
  本轮的补救成本（审计发现 → 补写 §14.5.10–13）高于当初多花 1 分钟清点。
- **块替换务必 `t[:a] + new + t[b:]`**（本轮 p11 曾漏 `+ t[b:]`，被下游断言拦下）。
- **"恒为常量"是最容易犯的过强主张**，必须配全量直方图。
"""

p = os.path.join(MEM, '2026-09-19.md')
with open(p, 'a', encoding='utf-8', newline='\n') as f:
    f.write('\n\n---\n\n' + ADD)
print('APPENDED', p, os.path.getsize(p), 'B')
