# -*- coding: utf-8 -*-
"""追加 2026-09-19 工作日志 + 更新项目 MEMORY.md。"""
import os

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
MEM = os.path.join(ROOT, '.workbuddy', 'memory')
os.makedirs(MEM, exist_ok=True)

LOG = """# 2026-09-19 工作日志

## r19：tmp → multi_src 归档 + MULTI 单群/多群表族**结构性更正**（本轮最重要）

### 1. 归档：`.workbuddy/tmp/` → `src/multi_src/`（按功能分 15 个子目录）

- 规则：**只复制不移动**；显式排除**另一条工作流**（`eosop_pro` 包 r11–r16 开发产物，110 项）。
- 规模：**361 items / ~11.9 MB**；**0 unsorted**。
- 结构：
  `01_inventory` / `02_doc_extract`(docext,legacy,pdfext) / `03_anchors` /
  `04_probe`(01_cst_and_noext, **02_multigroup_planck**, 03_sesame, 04_feos, 05_hyades_ionmix,
  06_general, probe_noext_agent) / `05_cross_validation` / `06_agent_reports` /
  `07_doc_build`(multi_doc_parts, parts) / `08_audit` / `09_source_verify`(vendor)
- 索引：`src/multi_src/README.md`（708 文件全清单 + 职责说明 + 后续归档约定）、
  `MANIFEST.tsv`、`EXCLUDED.md`。
- 归档守则（写入 README §5）：探针按族入 `04_probe/<族>/`；文档补丁入 `07_doc_build/` 命名
  `p<序号>_<主题>.py` 且**必须幂等 + count 断言**；核查脚本入 `08_audit/` 命名 `audit_v<n>.py`；
  中间输出**与产生它的脚本同目录**。

### 2. 重大结构更正：MULTI 单群/多群表族（§14.5 整体重写 + §15.12.6 勘误）

**旧结论（第一/二版，错）→ 新结论（第三轮，对）**：

| 项 | 旧（错） | 新（对） |
|---|---|---|
| 每群组成 | 2 值带界行 + **4 值骨架行** + 数据区 | **群表头(60字符) + 带界行(30字符) + 数据区**（**无骨架行**） |
| 表头粒度 | 文件级 1 条 | **每群 1 条**（逐字重复） |
| 行数公式 | `1 + K·(2 + ⌈(NR+NT+NR·NT)/4⌉)` | **多群 `K·(2+D)`；单群 `1+D`**；`D = ⌈(NR+NT+NR·NT)/4⌉` |
| 规模 | 「150 个无扩展名文件」(12.4%) | **404 个文件 / 20 种命名 (33.3%)**：194 单群 + 210 多群 |
| 群表头第 2 字段 | 仅"类别名" | **`<类别名> <标志>`**：`M`=多群、`1`=单群、**数值**=ZEFF 式 |
| ZEFF 第 2 字段 `6.0` | 读作**原子序数 Z**（"Ce 的 Z=6.0 矛盾"） | **常量 6.0**（164 个文件全同；Al/Ce/D 取值相同）|
| 8 位表号 | "= 材料 ID + 2000/3000/4000/5000"，可反查材料 | **不唯一**：是 **SNOP 模板号**（Ce/Gd/He/Ti 的 Planck 都写 27003000）；材料由**目录**定 |
| T 轴「10× 因子悬案」 | 未解 | **伪命题，已关闭**：`T1/T2` 单位 = **keV**（`doc/SNOP.MANUAL` 38–41 行明文），表内 eV，换算 **×1000**，端点逐位吻合 |
| `.dat`/`.out`/`.PLANCK` 等 | 当作各自的族 | **同族**（共用记录结构与公式），应合并 |

**决定性证据**：`Ce.PLANCK` 非空 **2,240** 行 = `20×112`（不是 2,241）；30 字符行索引
`1,113,225,…` 间距恒 **112**；**索引 112 那行逐字等于索引 0 的表头**；该模式 100 文件复现。
旧版多算的 1 行 = 把每群表头当文件级表头；"骨架行" = 下一条群记录的表头。

**判据（不依赖命名）**：`单群: 行数 == 1+D`；`多群: 行数 == n₃₀×(2+D)`，`n₃₀` = 30 字符行数。
404 个归属文件中除 `opbe` 外全部闭合。

**`opbe` 完整解释**（旧版"80 群/末群截断"作废）：
`40×(PLANCK M) + 40×(ROSSELAND M) + 1×(ZEFF 单群)` = `4480+4480+111 = 9,071` ✓ 精确闭合。
→ 判据更新：**不能只数带界行，必须读每条群表头的类别名**（类别名会中途改变）。

**网格/单位**（`SNOP.MANUAL` 明文）：`RHO1/RHO2` = g/cm³（34–37 行）；`T1/T2` = **keV**（38–41 行）；
`X1/X2` = keV；`F0/F1` = eV；`FG(NG+1)` = **eV**（62 行）。
验证：`Ce`(`T1=1e-5,T2=5` keV) → 表 `0.01…5000 eV` ✓；`Be`(`1e-3,100`) → `1…1e5 eV` ✓。

**ID 四形态**：`00000000`(191, Thermos 占位) / LEDCOP 哨兵 `0.1234567E+000`(72) /
MULTI 8 位表号(~60) / 小整数与浮点(如 `1400003`, `1`, `20071004`, `.24010000E+04`)。

**行宽三档**：30 / 60 / **59–62 抖动**（表头宽度，`Ce.ZEFF` 为 59）→ 按**列位置**切分，
**禁用 `len(line)==60` 筛选**。

### 3. 文档操作（本轮补丁）
- `p11_fix145.py`：§14.5 整体重写（8100 → 9916 字符）+ §15.14.8 悬案关闭 + 新增 §15.12.6 结构勘误
- `p12_sync.py`：全文陈旧表述同步 **23 处全命中 / 0 缺失**（含 §1.2.2、§14 前言、§15.8.0、
  §15.9.1、R19、§15.14.1、附录 B.22、附录 E #14）+ §15.12 子节编号互换（6↔7）+ 块位置调整
- 备份：`MultiEOSOP格式说明.md.bak6`

### 4. 环境坑（本轮新增）
- **环境对 `shutil.rmtree` 有 safe-delete 拦截** → 归档脚本必须用
  `copytree(..., dirs_exist_ok=True)` 做幂等，**不得删目录**。
- shim **无 `cp`**；备份用 Python `shutil.copy2`。
- **块替换务必 `txt[:a] + new + txt[b:]`** —— 本轮流曾漏 `+ txt[b:]`，靠下游断言才拦住
  （否则会整段删掉 §15 之后所有内容）。

### 5. 交付
- 文档：`src/multi_docs/MultiEOSOP格式说明.md` → **116,199 汉字 / 577,596 字符 / 862,297 B**
- 核查全绿：围栏 520 配对 ✓；表号唯一（仅 T11 合法占用）✓；**章节顺序全单调** ✓；
  内部引用 88 条全有效 ✓；表格 314 个列数一致 ✓；残留标记 0 ✓
- 权威记录：`src/multi_src/04_probe/02_multigroup_planck/multigroup_opacity_FINAL.md`
- 逐文件普查：`src/multi_src/04_probe/02_multigroup_planck/census_mg2.txt`
- 归档索引：`src/multi_src/README.md`

### 6. 仍在跑的工作流
- `rev-feos-src2`：FEOS 源码裁定 4 问（`TRef` 单位 eV vs Hartree、`.cst` 四列、
  `.feos` 行 1 十字段、不透明度 T 轴缩放）→ 产出 `04_probe/04_feos/feos_src_adjudication.md`
  （已见其落盘 `feos_src_q1.py`）
- `xval-materials`：全量覆盖矩阵 + 多材料第二轮交叉验证
  → 产出 `05_cross_validation/coverage_matrix.tsv` / `coverage_summary.md` / `cross_validation_round2.md`
"""

p = os.path.join(MEM, '2026-09-19.md')
if os.path.exists(p):
    with open(p, 'a', encoding='utf-8', newline='\n') as f:
        f.write('\n\n---\n\n' + LOG)
    mode = 'APPENDED'
else:
    open(p, 'w', encoding='utf-8', newline='\n').write(LOG)
    mode = 'CREATED'
print('%s %s  (%d B)' % (mode, p, os.path.getsize(p)))
