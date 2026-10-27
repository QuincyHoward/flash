# .cst 双变体 + 无扩展名命名约定 —— 代理 probe-cst-naming 核查结论摘要

**来源**：`.workbuddy/tmp/naming_cst_formats.md`（代理产出，含 probe_01…14 脚本与 out_01…14）
**状态**：✅ 已核（含 4 项诚实未解）

## 一、`.cst` 双变体（24 文件 = 23 DE + 1 EN）

### 变体判定
- **DE（23 个）**：`Isotherme T = <%.0f> Kelvin ` + `Moleküldichte[1/cm^3]  Massendichte[g/cm^3]  Druck[MBar]  Ladungszustand`
- **EN（1 个，也是唯一大写）**：`mat_He/Untitled.CST`，`Isotherm T = 0 Kelvin ` + `Particle density[1/cc]  Mass density[g/cc]  Pressure[MBar]load state`
  - ⚠️ `[MBar]load` **无空格** ⇒ **只能按列序定位，不能按列名定位**

### 【重要修正】不能按固定字符宽度切片
- DE 第 3 token 起始在 **60/61 抖动**（Ne 492/8，F 412/88）
- EN 第 3 token 起始在 **63/64 抖动**（328/172）
- **根因**：INF token（15 字符）与常规 `%e`（13 字符）宽度不同 + writer 用固定空白填充
  （C 源码 `"%e          %e          %e    %e\n"`）
- ⇒ **必须按空白 split 并断言 `len==4`**；实测 24 文件 / **298,152 数据行 100% 恰好 4 token**
- ⇒ **定宽切片会静默错位，不可用**（此前若按定宽写解析器必然出错）

### 【重要修正】首行 T 不是常量 0
- T 单位为 Kelvin（源码 `(*table).T[j]*eV2Kelvin`），**逐块变化**
- 实例：`Ne` 为 `0,1,1,2,3,3,4…` 最高 **16,509,924**；`Ta2O5` 最高 **652,566,179**
- `%.0f` 已取整 ⇒ 低温区出现重复整数（**精度截断，非数据重复**）

### 四列单位（源码明文 `FEOS/Code/FE-01_TABTOOLS.C:883-907` `write_Rostock_format`）
| 列 | 含义 | 单位 |
|---|---|---|
| col0 | `ρ/(A_tot·M_proton)` | 1/cm³ |
| col1 | `ρ` | g/cm³ |
| col2 | `P·1e-12` | MBar |
| col3 | `Q_tot` | 无量纲（**电荷态总和，非平均**） |

常量 `M_proton=1.6726231e-24`、`cgs2MBar=1e-12` 见 `COMMON-00_DEFINITS.H`；
手册 `FEOS-Package-Documentation.txt` §16.4 亦有明文。
**交叉验证**：He 的 col0/col1 = 6.024e25 ≈ `1/(4·m_p)×ρ` ✓

### `-1.#INF00e+000` 精确统计
- **仅第 2 列（压力），仅零粒子密度行**（每等温块第 0 行）
- EN = 79 行/块 × 101 块 = **7,979 次**；DE = 1 行/块 × 101 块 = **101 次**
- ⚠️ **`float('-1.#INF00e+000')` 抛 ValueError（不是 inf）**，numpy 同
- 正确做法：正则 `^([+-]?)1\.#(INF|IND|QNAN|SNAN)00e[+-]?\d+$` 预处理

### 闭合（精确，N = 125×B = 1 标题 + 1 表头 + 123 数据）
- 12,625 物理行 → B=101 → 预测 12,423 数据行，**实测 12,423 ✓**（B/Ne/He 等）
- 12,125 物理行 → B=97 → 预测 11,931 数据行，**实测 11,931 ✓**（Ta2O5/Cerium）
- ⚠️ 踩坑：CRLF 使 `split('\n')` 多出末尾空串（12,626），早期 off-by-one 假象

## 二、无扩展名命名约定（150 个）

### 五大类
`EOS` / `反演 EOS(_ieos)` / `不透明度(op,mop,opp,opr,PLANCK,ROSS)` / `光学常数(SIMPLE_*,IDEAL_GAS)` / `记账(FILELIST,LOCK,MODINFO,CHECKSUM,README)`

### README 一手确认的 token（手册明文）
| token | 含义 |
|---|---|
| `_op03e` | Multigroup NON-LTE factor, **by SNOP** |
| `_op03p` | Planck opacity, SNOP |
| `_op03r` | Rosseland opacity, SNOP |
| `_op03z` | Z-effective（**README 自述 unknown provenance**） |
| `_SIMPLE_PLANCK` | `3.0e-07·T^1.2/ρ^1.2` |
| `_SIMPLE_PLANCK_MG` | 同上，分 **24 频率群** |
| `_WorkOp_Ross` | WorkOp-III:94 |
| `_info` | SNOP 参数（Tsakiris & Eidmann 1987） |
| `_eos` / `_eosd` | "SESAME library, probably" |
| `_IDEAL_GAS` | `Z=19.998, A=197, γ=1.2168` |

### 【重要修正】`x03` = ×**0.3**，不是 ×3
README 原文：`BE_PLANCKx03 = BE_SIMPLE_PLANCK × 0.3`

### 材料号方案（手册明文 `AU_info`）
`Z:27002003; P:27003003; R:27004003; E:27005003`；Z=79，AW=196.97，"20 GRUPPEN ZWISCHEN 0 UND 5 KEV"
实测对照：`AU_op03p`=27003003、`Au100PLANCK`=79003000、`Au100ZEFF`=79002000 ✓

### 100 vs 20 群核验（无错标）
- `CHSi1_mopp` 588,100 B / 9,500 行（20 群） vs `CHSi1_mopp100` 2,940,500 B / 47,500 行（100 群）
  ⇒ **恰好 ×5** ✓（与主理人实测的"群数×5"一致）
- `Gd20PLANCK` 2,241 行（20） vs `Gd100PLANCK` 39,701 行（100）

### `_ieos` 行 0 格式
`<id> <T[eV]> <ρmax> <ρmin>`，如 `41_ieos` → `41 2.7 44.0 22.0`；`CH10Water1_ieos` id=61310

### stub 全量 dump
- **183 B = 3 行**：`*_SIMPLE_PLANCK` / `*_SIMPLE_ROSSELAND` / `*_WorkOp_Ross` / `*_PLANCKx03`
- **305 B = 5 行**：5 个 `*_IDEAL_GAS` / `*_eos_i`
- 格式 = `E+04 value, E+02 value, …` 的**常数采样表**（解析式不透明度的离散点）

### 记账语法（实测）
| 文件 | 语法 |
|---|---|
| `MODINFO` | `key=value`，键全集 `name/author/info/parent/cdate/ldate/m94version`（`m94version=2.0` ⇒ MULTI-94 系谱） |
| `FILELIST` | 纯清单，**含 glob**（如 `AU_*`） |
| `LOCK` | 单行日期串（`Mon Oct 20 15:42:58 MET 1997`） |
| `CHECKSUM` | `AU.INV:44905:05669:` —— **两个 5 位十进制校验和，非 MD5**，末尾带冒号 |

## 三、诚实未解项（4 条，不猜）
1. **英文 `.cst` 的生成工具**：FEOS `Code/` 全量检索 `Particle density`/`load state`/`Isotherm` **零命中**，仅德语 writer 存在 ⇒ 断定**非 FEOS 产物**，具体工具未解
2. EN 79 INF/块 vs DE 1 INF/块的**根因未解**（仅知网格/外推策略不同）
3. `_op03z` 来源 README 自述 unknown；`_EPS`/`_MG`/`_Z` 逐字段语义无一手定义；
   `41_`/`422_`/`511_` 数字前缀编码规则未解
4. `matlab/*.m` 中未发现 `.cst`/无后缀名 writer（该侧是后处理）
   ⇒ 权威依据落在 **FEOS C 源码 + 随包 README**
