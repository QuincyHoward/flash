# -*- coding: utf-8 -*-
"""p15: 补回 §14.5 重写时丢失的 §14.5.10–§14.5.13（token 语义 / 记账语法 / stub / _ieos）。"""
import os
ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
DOC = os.path.join(ROOT, 'src', 'multi_docs', 'MultiEOSOP格式说明.md')
t = open(DOC, encoding='utf-8').read()

ADD = """
#### 14.5.10 命名 token 的语义（文件名承载的元信息）

本族的文件名不是随手起的，而是**把"表类 / 来源 / 变体"编码进 token** `[S-L2] 手册 + 文件名实测`：

| token | 含义 | 来源 |
|---|---|---|
| `_op03e` | 多群 **non-LTE factor**（SNOP 输出） | `matter++/Readme.txt` 手册明文 |
| `_op03p` / `_op03r` | **Planck / Rosseland**（SNOP 输出） | 同上 |
| `_op03z` | **自述 unknown provenance**（手册原文如此） | 同上 |
| `_SIMPLE_PLANCK` | 幂律近似 `κ = 3.0e-07·T^1.2/ρ^1.2` | 手册明文 |
| `_SIMPLE_PLANCK_MG` | 同式，但**24 个频率群** | 手册明文 |
| **`_PLANCKx03`** | **对基准 Planck 整体 ×0.3（不是 ×3！）** | token 字面 + 样本比例 |
| `_WorkOp_Ross` | 引用 **WorkOp-III:94** 的 Rosseland 表 | 手册明文 |
| `_info` | SNOP 运行参数（Tsakiris & Eidmann 1987） | 手册明文 |
| `_eos` / `_eosd` | 手册原文：**"SESAME library, probably"** | 手册明文（措辞不确定） |
| `_IDEAL_GAS` | 理想气体参数 `Z=19.998, A=197, γ=1.2168` | 文件内嵌 |
| `_op100PLANCK` / `_100G` / `100` 后缀 | 群数 **100** | 与带界行计数一致 |

> **⚠ 最易错的一条**：`_PLANCKx03` 的 `x03` 读作 **×0.3**，与直觉（×3）相反。
> 本轮三个独立来源（手册措辞、样本比例、命名并列项）一致支持 ×0.3，故定案。

#### 14.5.11 stub 文件：两种长度，是"采样表"而非空壳

一些看起来很薄的同名文件其实是**解析式不透明度被离散采样后的表**，可**直接读取使用**：

| 字节数 | 行数 | 涉及 token |
|---|---|---|
| **183 B** | 3 行 | `*_SIMPLE_PLANCK` / `*_SIMPLE_ROSSELAND` / `*_WorkOp_Ross` / `*_PLANCKx03` |
| **280 B** | 3 行 | `Thermos/mat_Mo/Mo_Ideal_Gas`、`mat_W/W_Ideal_Gas`（第 2 字段 = **密度**，见 §14.5.3） |
| **305 B** | 5 行 | 5 个 `*_IDEAL_GAS` / `*_eos_i` |

格式 = `E+04 value` 与 `E+02 value` **交替**的常数采样表（能量点 + 对应值），
形状符合 §14.5.2 的单群公式 `1 + D`（如 183 B 档：表头 1 行 + 数据 2 行 ⇒ `NR=NT=2, D=2`）。

#### 14.5.12 伴随的"记账文件"语法

本族目录下常伴随四个**非数据**文件，其语法已全部解出 `[S-L4] 实测`：

| 文件 | 语法 | 实测要点 |
|---|---|---|
| `MODINFO` | `key=value` 行 | 键全集 = `name` / `author` / `info` / `parent` / `cdate` / `ldate` / `m94version`；`m94version=2.0` ⇒ **MULTI-94 系谱** |
| `FILELIST` | 纯清单，**含 glob** | 如 `AU_*`，不是逐文件枚举 |
| `LOCK` | 单行日期串 | 如 `Mon Oct 20 15:42:58 MET 1997` |
| `CHECKSUM` | `<文件>:<5位十进制>:<5位十进制>:` | **非 MD5**，末尾带冒号 |

**`CHECKSUM` 算法已破解**：为 **(SysV-16, BSD-16)** 双 16 位校验和拼接，**7/7 命中**；
把两值**对调即全部失配**，据此排除了 Fletcher-16 / Adler-32 / CRC-16 / 裸 `sum` 等候选。

#### 14.5.13 `_ieos` 首行格式

`_ieos` 文件首行为 `<材料号> <T[eV]> <ρmax> <ρmin>`，实测：

```
41_ieos        → 41    2.7   44.0   22.0
CH10Water1_ieos → 61310 ...
511_ieos       → (材料号 511)  2.45 ...
422_ieos       → (材料号 422)  4.54 ...
```

`41_` / `42_` / `422_` / `511_` 这类**纯数字前缀**的编码规则**仍未解**（已排除"材料号本身 /
群数 / 温度点数"三种假设），登记于 §15.12.2 残差表。

"""

ANCHOR = '## 第15章 仍未完全解析的格式'
if ANCHOR in t:
    i = t.index(ANCHOR)
    t = t[:i] + ADD.lstrip('\n') + '\n' + t[i:]
    open(DOC, 'w', encoding='utf-8', newline='\n').write(t)
    print('PATCH15 done: size =', len(t))
else:
    print('PATCH15: anchor missing')
