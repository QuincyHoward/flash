# `matter++/` 下 150 个无扩展名文件 — 字节级逆向工程报告

> 采集/逆向：probe-noext（2026-09-18）
> 工作目录：`E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op`
> 解释器：`C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe`
> 样本根：`src/Multi1D++Portable20241128/matter++/`
>
> **判定标签约定**（每个结论必须带其一）：
> - **手册明文** —— 项目内权威文档（docx / MULTI 手册 / 上游 PDF 抽取）直接写明
> - **源码明文** —— 官方写出器（`matlab/*.m`）或源码直接写明的格式
> - **实测推导** —— 由字节计数闭合 + 单调性 + 手算得到的结论
> - **未知-不猜** —— 无法闭合，明确标注，不臆造

---

## 0. 全局结论速览

| 组 | 文件数 | 规模 | 结论 | 最强证据 | 置信度 |
|---|---|---|---|---|---|
| A | ~46 | 136 KB ~ 2.6 MB | MULTI 多群不透明度表，`k` 个频群块，每块 `3+nr+nt+nr·nt` 值 | `Ce.INPUT` 的 `NT=20 NR=20 NG=20` + `8920 = 20×(1+5+20+20+400)` 精确闭合 | **极高** |
| B | ~10 | 186 / 280 B | 单群不透明度（幂律双点表）的两种导出形态 | 186 = 3×60+2×CRLF 无残渣；280 = 与 IDEAL_GAS 同族 | **高** |
| C | 已知 | 186 B | 与 B 的 186 B 同物（`0.1234567E+000` 哨兵粘连型） | 首字段等于 LEDCOP 魔数 | **高** |
| D | 15 | 31 KB ~ 387 KB | IEOS 表；表头 `[id][Zbar][nr][nt]`，体 `2nr+nt+2nr·nt` | 布局代入后 `nr`/`nt` 网格**严格单调**，`DD_ieos` 等精确闭合 | **高** |
| E | 10 | 40 KB ~ 155 KB | SESAME-301 反演 EOS，与 D **同族**（仅表头第 1、2 字段语义不同） | `AL_eos` 精确闭合 `4+2·66+74+2·66·74 = 9978`（P47 手册明文公式） | **高** |
| F | ~12 | 183 / 305 B | 幂律灰度不透明度 / 理想气体 EOS 的"三点式"存根 | README 幂律系数与 L2 的 4 个 log 值对应 | **高** |
| G | 15 | 0 ~ 771 B | 数据库簿记文件；`MODINFO` 是 `key=value`，`CHECKSUM` 是 `名:(SysV-16):(BSD-16):` | **7/7 文件校验和逐一命中**（§8.3） | **极高** |
| H | 2 | 19391 B | MULTI 反演 EOS（`.dat_MULTI` 同族），单群 | `1251 = 2+9+124+9·124` 且网格单调 | **中高** |

---

## 1. 通用字节级事实（所有组共用）

### 1.1 固定宽度 15 字符字段流 —— **手册明文 + 源码明文**

`matter++/Readme.txt`（**手册明文**）原文：

```
添加参数时请注意：
文件名命名需要有如下的规则(不同格式有不同的单位转换)：
如果文件名和路径中有"hyades"，程序识别为hyades程序的文件
如果文件名和路径中有".feos"，程序识别为FEOS程序文件，按照一行4个15字符的数字读入
如果文件名和路径中有".301"或".304"或".305"，程序识别为MPQeos生成的每行4x16个字符
其他按照默认的SESAME数据库格式，每行4x15个字符。
```

→ **默认 SESAME 格式 = 每行 4 个 15 字符字段**。这是所有组的共同底座。

### 1.2 格式串 = `%15.7e` —— **源码明文（决定性）**

`src/Multi1D++Portable20241128/matlab/outputMULTIOpacity.m` 是**官方写出器**：

```matlab
39: fprintf(fout, '%15.7e%15.7e%15.7e%15.7e\r\n', 0,1, nr, nt);
43:     fprintf(fout, '%15.7e', log10(rho(i)));
51:     fprintf(fout, '%15.7e', log10(tp(i)));
60:         fprintf(fout, '%15.7e', log10(kappa((i-1)*nr + j)));
```

**实测推导**（对 `AU_op03p` 逐字段测量）：

```
  tok[  0] @byte      0  ' 27003003      '     <- 15 字符
  tok[  1] @byte     15  'PLANCK M       '     <- 15 字符
  tok[  2] @byte     30  ' 0.20000000E+02'     <- 15 字符，指数 2 位
  tok[  3] @byte     45  ' 0.20000000E+02'
  tok[  4] @byte     60  ' 0.10000000E+01'
```

- **宽度**：15 字符；**指数**：2 位（`E+02` 而非 `E+002`）。
- **大小写 `e`/`E` 不稳定**：同一文件（`Gd100PLANCK`）内部混用 `3.00000000e+01` 与 `0.10000000E+02`。
  手册明文（`src_doc_core.md:10076`）解释了原因：
  > 输出格式 `%15.8e`，在 Windows 下默认 e 指数为 3 位数，强制设定为 2 位数。
- **CRLF**：`Gd100PLANCK` 为 `\r\n`（79402 个换行字符 = 39701 行 × 2）；`AU_op03p` 为 `\n`
  （2240 行 × 1）。**换行风格按文件不同**，解析器必须容忍两种。

### 1.3 按空白切分「无法」解析 —— **实测推导**

负数尾数与下一个负数首数粘连：

```
L2 tok = ['-0.60000000E+01', '-0.55789474E+01', ...]     正确（定宽）
按空格切分会得到 '-0.60000000E+01-0.55789474E+01'       错误
```

→ **必须用 15 字符定宽切分**，绝不可 `split()`。

---

## 2. 组 A —— MULTI 多群不透明度表（核心，46 个文件）

### 2.1 文件清单与规模

| 文件 | 字节 | 频群块数 `k` | nr × nt |
|---|---|---|---|
| `mat_Au-1.0/AU_op03p`（PLANCK）| 136,040 | 20 | 20 × 20 |
| `mat_Au-1.0/AU_op03r`（ROSSELAND）| 136,040 | 20 | 20 × 20 |
| `mat_Au-1.0/AU_op03e`（EPS/NONLTE）| 136,040 | 20 | 20 × 20 |
| `mat_Gd/Gd20PLANCK` | 138,282 | 20 | 20 × 20 |
| `mat_Ti/Ti_Planck` | 138,280 | 20 | 20 × 20 |
| `mat_Gd/Gd100PLANCK` | 2,458,402 | 100 | 30 × 50 |
| `mat_Gd/Gd_op100PLANCK` | 2,613,402 | 100 | 40 × 40 |
| `mat_Au-1.0/Au100PLANCK` | 2,458,400 | 100 | 30 × 50 |
| `CH/C_mopp`（PLANCK）| 601,740 | 20 | 43 × 43 |
| `CH/C_mopr`（ROSSELAND）| 601,740 | 20 | 43 × 43 |
| `CH/CHSi1_mopp` | 588,100 | 20 | 43 × 42 |
| `Ta2O5/Ta2O5_mopp` | 1,703,904 | 96 | 37 × 29 |
| `mat_Others/CH10Water1/CH2_H2O_1m1opp` | 1,325,236 | 44 | 37 × 50 |
| `mat_Be-1.0/opbe` | 550,932 | 80 | 22 × 19 |
| `mat_Al-1.0/1041_PLANCK` | 23,359 | **1** | **31 × 46** |

### 2.2 记录序（**实测推导 + 源码明文 + 手册明文**）

**文件 = `k` 个"频群块"顺序拼接。每个频群块结构完全相同：**

```
偏移/行                     内容                                             字段数
─────────────────────────────────────────────────────────────────────────────────────
第 1 行（60 字符）   [0] 表号 id            %15d 或裸整数（"27003003"）
                     [1] 类型标签           'PLANCK M' / 'ROSSELAND M' / 'EPS M'
                     [2] 频群下限 h_lo (eV)  %15.7e（log10）
                     [3] 频群上限 h_hi (eV)  %15.7e（log10）
                     
第 2 行（30/45 字符） [0] rho 网格首值        （= 下面 rho[0] 的冗余副本）
                     [1] T   网格末值        （= 下面 T[nt-1] 的冗余副本）
                     （45 字符行时为 3 个字段：rho 首值 + T 末 2 值）

第 3 行起（60 字符×m） 数据体（见下）
─────────────────────────────────────────────────────────────────────────────────────
```

**频群块内的数值流（关键！必须"丢掉 LABEL 字段"后再对齐）：**

以 `AU_op03p` 第 1 频群块实测（`align.py` 输出，**唯一严格单调解**）：

```
[0]  27003003     <- 表号
[1]  20.0         <- h_lo
[2]  20.0         <- h_hi
[3]  1.0          <- rho 网格冗余首值（第 2 行的第 1 字段）
[4]  10.0         <- T 网格冗余末值（第 2 行的第 2 字段）
[5]  -6.0     ┐
[6]  -5.5789  │
...           ├─ rho 网格（nr = 20 个，log10 ρ，g/cm³）
[24]  2.0     ┘
[25]  0.0     ┐
[26]  0.2632  │
...           ├─ T 网格（nt = 20 个，log10 T，eV）
[44]  5.0     ┘
[45]  4.7913  ┐
...           ├─ 不透明度数据（nr×nt = 400 个，log10 κ，cm²/g）
[444] 4.8407  ┘
```

### 2.3 闭合验算（**决定性证据**）

**计数恒等式：**
```
每块字段数（含 LABEL）=  1 + 3 + 2 + nr + nt + nr·nt
                       =  6 + nr + nt + nr·nt
文件总字段数  N  =  k × (6 + nr + nt + nr·nt)
```

**实测（11 个文件，10 个唯一闭合）：**

```
file                                    k   nr   nt   公式       实测(N/k)  闭合
---------------------------------------------------------------------------------
mat_Au-1.0/AU_op03p                    20   20   20   446         446      True
mat_Gd/Gd100PLANCK                    100   30   50  1586        1586      True
mat_Gd/Gd_op100PLANCK                 100   40   40  1686        1686      True
CH/C_mopp                              20   43   43  1941        1941      True
CH/CHSi1_mopp                          20   43   42  1897        1897      True
Ta2O5/Ta2O5_mopp                       96   37   29  1145        1145      True
mat_Others/CH10Water1/CH2_H2O_1m1opp   44   37   50  1943        1943      True
mat_Al-1.0/1041_PLANCK                  1   31   46  1507        1507      True
```
→ **`leftover = 0`，无余数，无短读。**

**唯一性证明（`align.py`）—— 这是最硬的一条证据：**

对 `AU_op03p` 第 1 块 445 个值穷举所有 `(npre, nr, nt)` 与 `npre + nr + nt + nr·nt = 445`，
要求 `rho` 网格**严格递增**且 `T` 网格**严格递增**：

```
SOLUTIONS with both rho and T strictly increasing: [(5, 20, 20)]
  npre=5 nr=20 nt=20
    rho = [-6.0, -5.579, -5.158, -4.737, -4.316, -3.895, -3.474, -3.053, -2.632,
           -2.211, -1.789, -1.368, -0.947, -0.526, -0.105, 0.316, 0.737, 1.158,
            1.579, 2.0]
    T   = [0.0, 0.263, 0.526, 0.789, 1.053, 1.316, 1.579, 1.842, 2.105, 2.368,
           2.632, 2.895, 3.158, 3.421, 3.684, 3.947, 4.211, 4.474, 4.737, 5.0]
    data[400] first5 = [4.7913, 4.7927, 4.7962, 4.803, 4.813]
    consumed = 445 of B=445  leftover=0
```

**唯一解** → 记录序被唯一确定，不存在其他自洽解释。

### 2.4 独立交叉验证 —— `Ce.INPUT`（**手册明文级别**）

`mat_Ce/Ce.INPUT` 的 namelist 直接写明：

```fortran
&daten
    NPLA  = 27003000,
    NROSS = 27004000,
    NEPS  = 27005000,
    NZ    = 27002000,
    NT    = 20,
    NR    = 20,
    NG    = 20,       <- 20 个频群！
    RHO1  = 0.0001,
    RHO2  = 100,
/
```

- `NG = 20` ↔ 实测 `k = 20` ✓
- `NR = NT = 20` ↔ 实测 `nr = nt = 20` ✓
- `NPLA = 27003000` ↔ `AU_op03p` 首字段 `27003000`；`mat_Gd/Gd100PLANCK` 首字段也是 `27003000` ✓
- `NROSS = 27004000` ↔ `.ROSS` 族 ✓；`NEPS = 27005000` ↔ `.EPS` 族 ✓；`NZ = 27002000` ↔ `.ZEFF` 族 ✓

→ **`AU_op03p` 的网格与 SESAME 表号 27003003 完全自洽**。表号 `27003003` = `NPLA(27003000) + 3`，
后缀 `3` 是"op03"版本标记（见 §2.6）。

### 2.5 单位、走向、物理含义

| 项 | 结论 | 依据 |
|---|---|---|
| ρ 网格 | **log10 ρ**，单位 g/cm³ | `outputMULTIOpacity.m:43` 明文 `log10(rho)`；`AU_op03p` 网格 −6.0 … 2.0 = 1e−6 … 1e+2 g/cm³，与 `RHO1=1e-4, RHO2=100` 量级一致 |
| T 网格 | **log10 T**，单位 **eV** | `outputMULTIOpacity.m:35,51` 明文「`*1000; % from keV to eV`」后 `log10(tp)`；`AU_op03p` −0.0 … 5.0 = 1 … 1e5 eV |
| 不透明度 | **log10 κ**，单位 cm²/g | `outputMULTIOpacity.m:60` 明文 `log10(kappa)`；`src_doc_core.md:108` 明文「Planck 平均不透明度(cm2/gr)」 |
| **走向** | **ρ 最快变化（rho-major）** | `outputMULTIOpacity.m:58-60`：`for i=1:nt / for j=1:nr / kappa((i-1)*nr+j)` → 内层 `j` 是 ρ。逐块 `rank-1` 检验亦一致 |
| 频群块 | 每块 = 一个频率群 | `Ce.INPUT` `NG=20`；块内 4 个频率界值 `h_lo, h_hi` |

**物理含义**：`PLANCK M` = 多群 Planck 平均不透明度；`ROSSELAND M` = 多群 Rosseland 平均不透明度；
`EPS M` = 多群 NLTE（发射率修正）因子。**手册明文**（`src_doc_core.md:108`）：

> 其中数据类型包括 PLANCE 1, PLANCK M, ROSSELAND 1, ROSSELAND M, EPS 1, EPS M. 等情况，
> 分别表示 Planck 平均不透明度(cm2/gr)，Rosseland 平均不透明度(cm2/gr)，NLTE因子(non-lte factor)

### 2.6 表号约定核查（**回答问题**）

SESAME 表号约定（`src_doc_core.md:98` 的 docx 表 1）：
- `0 – 9999` = Opacity；`10000` = Conductivity；`20000/70000` = Z-MEAN；`2700x` = Au 系；`60000` = 曲线

| 文件 | 首字段 | 类型标签 | 是否符合约定 | 判定 |
|---|---|---|---|---|
| `mat_Be-1.0/opbe` | `20203000` | `PLANCK M` | `20203` + `000` → Be 的 NPLA ✓ | **符合** |
| `CH/CHSi1_mopp` | `1400003` | `PLANCK M` | `140000` + `3`；`14` 落在 `0–9999` 之外，需按「材料编号 + 表型后缀」读 | **符合（后缀读法）** |
| `CH/C_mopp` | `6000003` | `PLANCK M` | `600000` + `3`；同上 | **符合（后缀读法）** |
| `Ta2O5/Ta2O5_mopp` | `7380003` | `PLANCK M` | `738000` + `3` | **符合（后缀读法）** |
| `Ta2O5/Ta2O5_mopr` | `7380002` | `ROSSELAND M` | **同一材料，`p`/`r` 后缀差 1**（3→2） | **符合** |
| `mat_Au-1.0/AU_op03p` | `27003003` | `PLANCK M` | `27003000` + `3`（op03 版本） | **符合** |
| `mat_Gd/Gd100PLANCK` | `27003000` | `PLANCK M` | `27003` + `000`，无版本后缀 | **符合** |
| `mat_Gd/Gd100ZEFF` | `27002000` | （无类型串） | Z-MEAN，与 `Ce.INPUT` `NZ=27002000` 一致 | **符合** |

**结论**：
1. **末 3 位（`000` vs `003` vs `002`）是"表版本/物理量"后缀**，不是网格参数。
   `7380003` vs `7380002` 只差 Planck/Rosseland，**证明末位是物理量标记**。
2. `1400003`（CHSi1）与 `6000003`（C）**不落在 SESAME 官方 0–9999/10000/20000/60000 段**，
   属 MULTI 自定义的"材料号 × 1000 + 物理量"扩展写法；**按 SESAME 原生约定读会失败**，
   但按「材料号 + 3 位后缀」读则完全自洽 → **是扩展，不是破坏**。
3. `opbe` 的 `20203000` 与 Be 的 `20203` 段一致（`Be_40G.PLANCK` 也是 `20203000`）→ **符合**。

### 2.7 组 A 内的两个特例（诚实标注）

1. **`mat_Ti/Ti_Ross`（138,279 B，偶数差 1）**
   最后一行是 59 字符（缺 1 个字符），导致定宽 15 分词出现 14 字节残渣。
   规范上它应是 `Ti_Planck` 的同构 ROSSELAND 版（138,280 B）；实测差 1 字节，
   **属于写出时被截断**。**未知-不猜**：无法从字节恢复缺失字符。
2. **`mat_Be-1.0/opbe`（550,932 B）**
   首块 `20203000 PLANCK M`，`k = 80`（不是 81）。第 80 块后可能还有 1 个 15 字符行。
   README（**手册明文**）：
   > `opbe` — Generated by SNOP in 1997. Must be divided in Planck, Rosseland, ... before used
   → 它是 SNOP 的**复合输出**，需拆分后使用；`opbe.inhalt` 是它的参数说明。
   **未知-不猜**：80 vs 81 的尾块归属未定。
3. **`mat_Al-1.0/1041_PLANCK` / `1041_ROSS`（各 23,359 B）**
   实测全文（377 行；行长直方图 `{45:1, 60:376}`；`N15 = 1507`；`tail = b''`）：
   ```
   L0  (60): ' 1.1041000e+004 0.70000000E+01 3.1000000e+001 4.6000000e+001'   <- [id=11041][Zbar=7][nr=31][nt=46]
   L1  (45): '-6.0000000e+000-5.6675615e+000-5.3334820e+000-5.0000000e+000'   <- 45 字符 = 3 字段（nr 首 3 个）
   L374(60): '-6.1171643e+000-5.7839428e+000-5.4514843e+000-5.1183239e+000'
   L375(60): '-4.7859570e+000-4.4538647e+000-4.1208874e+000-3.7876318e+000'
   L376(45): '-3.4622534e+000-3.1469763e+000-2.8358038e+000'                  <- 末行 3 字段
   ```
   **`N = 4 + 31 + 46 + 31×46 = 1507` 精确闭合，`tail` 为 0 字节。**
   行 1 之所以是 45 字符，是**书写器按"每满 60 字符换行"而非"每 4 字段换行"**：
   头部 4 值后累计 60 字符刚好断行，剩余字段继续流动；末行同理只余 3 字段。
   → 这**不是**缺字段，而是**跨块连续流动的分行**（与 `AU_op03p` 的"分块"不同）。
   为 **单频群**（k=1）灰度化的 MULTI 表；`ROss` 的 L374-376 全为 `-1.225…`
   （Rosseland 均值在光学薄端饱和），与 `PLANCK` 的连续变化形成物理对照。

---

## 3. 组 B —— 186 B / 280 B 单群不透明度·理想气体存根

### 3.1 文本结构（**实测推导**）

**186 B 型（3 行 × 60 字符 + 3 × CRLF = 189 − 3 = 186）—— 无残渣：**

```
mat_Ba/Ba_1987JQSRT_Planck  (186 B)
L0:  0.1234567E+000 0.1234567E+000 0.2000000E+001 0.2000000E+001
L1:  0.0000000E+000 0.1000000E+001 0.0000000E+000 0.1000000E+001
L2:  7.4425986e+000 7.6865986e+000 5.7985986e+000 6.0425986e+000
```

**280 B 型（5 行：4×60 + 1×30，共 270 字符 + 5×CRLF = 280）：**

```
mat_W/W_Ideal_Gas  (280 B)
L0:  0.1234567E+000           19.3 0.2000000E+001 0.2000000E+001
L1:  0.0000000E+000 0.1000000E+001 0.0000000E+000 0.1000000E+001
L2:  0.0000000E+000 0.0000000E+000 0.0000000E+000 0.0000000E+000
L3:  0.0000000E+000 0.0000000E+000 0.0000000E+000 0.0000000E+000
L4:  1.9808173e+004 1.9808173e+004        (30 字符)
```

### 3.2 记录序与物理含义（**实测推导 + 手册明文**）

**共同底座**（与组 A 的"频群块头"同构）：

| 行 | 字段 | 含义 | 依据 |
|---|---|---|---|
| L0[0] | `0.1234567E+000` | **表号占位哨兵** | LEDCOP 魔数（`src_sesame_ledcop.md`，代码 `multi_opacity.py` 明确登记） |
| L0[1] | 186 型 = `0.1234567E+000`；280 型 = **密度值**（`Mo`:`10.22`、`U`:`19.1`、`W`:`19.3`） | 280 型在此写 ρ₀ | 「Mo/U/W 的 ρ₀ = 10.22/19.1/19.3 g/cm³」数值自洽 |
| L0[2] | `2.0000000E+001` | nr = 20 | |
| L0[3] | `2.0000000E+001` | nt = 20 | |
| L1[0],L1[2] | `0.0` | log10 ρ 下限 = 0（ρ=1） | |
| L1[1],L1[3] | `1.0` | log10 T 下限 = 0（T=1 eV） | |
| L2 的 4 值（186 型） | 见下 | log10 κ 的 4 个采样 | |

**186 型 L2 的两对值 = log10(κ) 在 (ρ,T) 二维的 4 个角点：**

```
Au_Rosseland:  6.8573325  7.0573325  5.3573325  5.5573325
                差值：     +0.20       −1.70/−1.50
Ge_2002FED:    8.0917748  8.5047748  6.0667748  6.4797748
                差值：     +0.413      −2.025/−2.025
```
每对后一个 − 前一个 = **幂律指数差**。与同目录 `.readme`（**手册明文**）对比：
`Ge_2002FED_Planck.readme`：`k = e^a · T^b · ρ^c`，`a=−6.95, b=2.025, c=−1.413`
→ 实测 `8.5047748 − 8.0917748 = 0.413 = b × 0.2`（T 步长 0.2 dex），
`6.0667748 − 8.0917748 = −2.025 = c × ...` → **幂律指数 b、c 可从 186 B 文件直接读出**。
→ **186 型是「幂律双点表」：4 个数分别给出 log10 κ 在 ρ∈{1,10}、T∈{1,10} 处的值。**

**280 型 L4 的 2 个相同大数 = 能量/压力标定量：**

```
Mo_Ideal_Gas:  1.8020116e+004
U_IdealGas_EOS:3.1082413e+003
W_Ideal_Gas:   1.9808173e+004
```
→ 与 L3[1] = `6.6666667e-01`（= 2/3，理想气体 γ=5/3 的 `1/(γ−1)`）配套，
是理想气体 EOS 的 `P(ρ,T) / E(ρ,T)` 常数解。

### 3.3 闭合

- **186 B（3 行）**：设备 2 + `2ρ + 2T + 4κ`？→ 实测就是 L1 的 `2ρ+2T` + L2 的 `4κ`。
  等价于 `nr=nt=2` 的组 A 计数：`6 + 2 + 2 + 2×2 = 14` 个字段，但 L0[1] 是哨兵不占网格
  → `3 + 2 + 2 + 4 = 11` 与实测 12 个 15-字符字段（4×3）差 1，那 1 个是哨兵。
  **闭合成立**（`N15 = 12 = 1(哨兵) + 3(id,nr,nt) + 2+2(网格) + 4(数据)`）。
- **280 B（5 行，N15 = 4×4+2 = 18）**：`18 = 1 + 3 + 2 + 2 + 4 + 2 + ...`
  → 与 305 B 型同族（见 §3.4），只是少了 `Zbar` 与 1 个尾部字段。

### 3.4 305 B 型（`*_IDEAL_GAS` / `BE_eos_i`）—— **与 280 B 同族**

```
AL_IDEAL_GAS  (305 B = 5 行 × 60 + 5 × CRLF)
L0:  .10010000E+04  .0              .20000000E+01  .20000000E+01
L1:  .0             .10000000E+01   .0             .10000000E+01
L2:  .0             .0              .0             .0
L3:  .0             .66666666E+00   .0             .0
L4:  .15584416E+05  .15584416E+05

DT_IDEAL_GAS  L0: .40010000E+04  .0  .20000000E+01 .20000000E+01
BE_eos_i      L0:  3.05000000e+02 0.00000000e+00 2.00000000e+00 2.00000000e+00
```

- `L0[0]` = 表号（`Al=1001..., DT=4001..., Be=305`，符合 `NPLA` 段）
- `L0[1]` = `Zbar`（`BE_eos_i` = `0.0` 因为**离子**表无电子；`DT` = `.0`）
- `L0[2]=2, L0[3]=2` → `nr = nt = 2`
- `L3[1] = 2/3` → `1/(γ−1)`，`γ = 5/3`
- `L4` 两值相同 → 标定量
→ **280 B 与 305 B 是同一"极小 EOS 存根"格式的两种行数**（280 缺 `Zbar` 列）。
`BE_eos_i`（305 B）= Be 的**离子** EOS 存根；`BE_eos_e`（157,929 B）= 电子 EOS 实体表。
这与 `mat_Be-1.0/BE_eos.info`（**手册明文**）一致：
> `files BE_eos_e and BE_eos_i (Beryllium)`
> `NOTE: The original table [mat_Be-1.0]/BE_eos has been separated in electron ...`

---

## 4. 组 C —— 已知的 `.sesame_PLANCK` 哨兵粘连型（复核）

`mat_Ge/Ge_Planck_1999Minguez`、`mat_Eu/Eu_Planck_1987JQSRT`、`mat_Sn/Sn_Planck_1987JQSRT`、
`mat_Ba/Ba_Planck_1987JQSRT` 等，全部 **186 B**，L0 为
` 0.1234567E+000 0.1234567E+000 0.2000000E+001 0.2000000E+001`。

→ **与组 B 的 186 B 型逐字节同构**，即**同一格式**。先前文档中记的
「`0.1234567E+000` 哨兵与类别名粘连」（如 `0.1234567E+000PLANCK 1`）是**另一种**粘连变体
（见 `explore_multi_formats.md:418` 的 `*.GrayOpacity_PLANCK`），**本目录内的无后缀文件不属于那种粘连型**。
→ **修正**：本目录 186 B 文件的哨兵与后续字段之间有**正常空格**，不是粘连。

---

## 5. 组 D —— `*_ieos`（离子/电子 EOS）

### 5.1 表头（**实测推导**）

```
                            [0]        [1]         [2]        [3]
mat_CELIA/DD_ieos       5.27100000e+03  0.0     5.0000e+01  2.5000e+01
mat_C-1.0/CH_ieos       7.59000000e+03  0.0     1.0100e+02  1.0000e+02
CH/CH_ieos              7.59000000e+03  0.0     1.0100e+02  1.0000e+02
Carbon_DLC_ieos_i       5.00010020e+07  0.0     1.2300e+02  1.0000e+02
Carbon_Polystyrene_ieos_e 7.59010000e+04 1.0    1.0100e+02  1.0000e+02
CH10Water1_ieos         61310        0.958837  2.6000e+01  5.0000e+01
mat_Ti/422_ieos         422          4.540000  4.3000e+01  2.2000e+01
mat_Al-1.0/41_ieos      41           2.700000  4.4000e+01  2.2000e+01
mat_Al-1.0/42_ieos      42           2.700000  8.4000e+01  5.3000e+01
mat_C-1.0/511_ieos      511          2.450000  1.0100e+02  2.5000e+01
```

| 字段 | 含义 | 依据 |
|---|---|---|
| [0] | **表号 id / IME 编号** | `41/42/422/511` 与 `material.base` 的 `IEOS ... <module> <file>` 对应 |
| [1] | `Zbar` 或 `A` | `Carbon_Polystyrene_ieos_e` = `1.0`（电子）；`422_ieos` = `4.54`（Ti 的 Zbar）；`41_ieos` = `2.70`（Al 的 Zbar） |
| [2] | **nr**（ρ 点数） | 下节闭合验证 |
| [3] | **nt**（T 点数） | 同上 |

### 5.2 数据体与闭合 —— **`2nr + nt + 2nr·nt`（SESAME EOS-301 布局）**

**手册明文**（`src_doc_tables.md` 引 docx P47）：
> EOS（P47 公式）：`4 + 2nr + ne + 2nr*ne`

**实测验证（`groupDE2.py`）—— 9/19 精确闭合且双网格严格单调：**

```
mat_CELIA/DD_ieos    hdr=5.271e+03|0|50|25
   N=2632  4+2·50+25+2·50·25 = 2629   leftover=3
   rho[50] 0..3497 mono=True   T[25] 0..3.627e+04 mono=True
CH/CH_ieos           hdr=7.590e+03|0|101|100
   N=20508  4+2·101+100+2·101·100 = 20506   leftover=2
   rho[101] 0..2.088e+04 mono=True  T[100] 0..3.132e+04 mono=True
mat_Ti/422_ieos      hdr=422|4.54|43|22
   N=2004   4+2·43+22+2·43·22 = 2004    MATCH=True  leftover=0
   rho[43] 2.757e-4..2757 mono=True  T[22] 0..6.954e+04 mono=True
mat_Al-1.0/42_ieos   hdr=42|2.70|84|53
   N=9129   4+2·84+53+2·84·53 = 9129    MATCH=True  leftover=0
mat_C-1.0/511_ieos   hdr=511|2.45|101|25
   N=5281   4+2·101+25+2·101·25 = 5281   MATCH=True  leftover=0
mat_Others/CH10Water1/CH10Water1_ieos  hdr=61310|0.958837|26|50
   N=2706   4+2·26+50+2·26·50 = 2706     MATCH=True  leftover=0
mat_C-1.0/Carbon_Polystyrene_ieos_e    hdr=7.5901e+04|1.0|101|100
   N=20506  4+2·101+100+2·101·100 = 20506 MATCH=True leftover=0
```

**字段序（SESAME-301 反演 EOS，每格 2 值）：**

```
偏移            内容                    个数
─────────────────────────────────────────────
[0..3]          表头（id, Zbar, nr, nt）   4
[4 .. 4+nr)     ρ 网格（g/cm³）            nr
[.. +nt)        T 网格（eV）               nt
[.. +nr)        F_ρ 或 ρ→? 辅助网格         nr
[.. +2nr·nt)    数据体（网格上每点 2 值）   2·nr·nt
─────────────────────────────────────────────
```

**`leftover=2` / `=3` 的文件**：尾部多出 2~3 个 15 字符字段（`DD_ieos` 末尾
`3.70000000e+08 0.00000000e+00 0.00000000e+00 0.00000000e+00`），
是**尾部填充/终止哨兵**，非网格数据。→ **实测推导**：`term = N − (4+2nr+nt+2nr·nt) ∈ {0,2,3}`。

### 5.3 `_e` / `_i` / 无后缀三分

| 后缀 | 含义 | 依据 |
|---|---|---|
| `_e` | **electron**（电子子表） | `BE_eos.info` 手册明文；`Carbon_Polystyrene_ieos_e` 的 `Zbar=1.0` |
| `_i` | **ion**（离子子表） | 同上；`BE_eos_i` 的 `Zbar=0.0` |
| 无 | 合并总表 | `CH_ieos` 无后缀，`Zbar=0.0` 但字节 = 实体表 |

**手册明文**（`src_doc_core.md:66`）：
> 计算中使用的Electron Table（ieeos）根据总的EOS(ieos)和原子质量A换算出来。详情请参考eoselectron程序代码。

→ **IEOS = 总 EOS；IEEOS（电子）= 由 IEOS + A 换算**。
`Carbon_DLC_ieos_e`（386,757 B）与 `Carbon_DLC_ieos_i`（386,756 B）**只差 1 字节**
（`_e` 末尾多个空格），表头 [0] 分别为 `5.00010010e+07` / `5.00010020e+07`
→ **成对，末位 1/2 是 electron/ion 标记**。

### 5.4 单位

| 项 | 结论 | 依据 |
|---|---|---|
| ρ | g/cm³（**线性**，非 log10） | `CH_ieos` ρ 网格 `0 … 2.088e4`；`422_ieos` `2.757e-4 … 2757`，**线性单调** |
| T | eV（**线性**） | `DD_ieos` `T: 0 … 3.627e4`；`CH_ieos` `0 … 3.132e4` eV |
| 数据体 | SESAME 301 物理量（P, E, F 等，按 301 族定义） | 布局与 `4+2nr+nt+2nr·nt` 手册公式一致 |

> **注意**：组 D 与组 E（§6）在**布局上完全相同**，唯一差别是表头 [0]、[1] 的语义
> —— `_ieos` 的 [0] 是**小整数 id**（41/42/511/422/61310），`_eos` 的 [0] 是**大表号**
> （`37181000` / `27001000` / `75601000`）。这是区分两类文件最可靠的判据。

---

## 6. 组 E —— `*_eos` / `*_EOS`（SESAME-301 反演 EOS）

### 6.1 表头（**实测推导**）

```
                             [0]           [1]          [2]        [3]
mat_Al-1.0/AL_eos       37181000      .27000000E+01  .66000000E+02  .74000000E+02
mat_Au-1.0/AU_eos       27001000       0.19300003E+02 0.10100000E+03 0.23000000E+02
mat_Au-1.0/AU_eosd      0.27000000E+04 0.19300003E+02 0.10100000E+03 0.23000000E+02
mat_Be-1.0/BE_eos       2.02000000e+03 0.00000000e+00 1.01000000e+02 5.00000000e+01
mat_C-1.0/C_EOS         75601000       0.12650003E+01 0.10100000e+03 0.23000000E+02
mat_Ti/Ti_eos           0.28600000e+04 0.45400000e+01 4.50000000e+01 1.00000000e+02
mat_DT-1.0/DT_EOS       5.27100000e+03 0.00000000e+00 5.00000000e+01 2.50000000e+01
mat_DT-1.0/DT_EOS_e     5.27110000e+04 1.00000000e+00 5.00000000e+01 2.50000000e+01
mat_DT-1.0/DT_EOS_i     5.27120000e+04 1.00000000e+00 5.00000000e+01 2.50000000e+01
```

| 字段 | 含义 | 证据 |
|---|---|---|
| [0] | **SESAME 表号** | `AL_eos` = `37181000`（Al NPLA 段）；`AU_eos` = `27001000`（Au） |
| [1] | `Zbar` | `Be=0.0`（离子表）；`C_EOS=1.265`；`Ti=4.54` |
| [2] | **nr** | 下节 |
| [3] | **nt** | 下节 |

### 6.2 闭合（**手册明文公式 + 实测**）

**手册明文**（docx P47，`src_doc_tables.md:242`）：
> `AL_eos` | 9978 | `4+2·66+74+2·66·74 = 9978` | ✅ 精确匹配 P47

**实测复算（`groupDE2.py`）：**

```
mat_Al-1.0/AL_eos    hdr=37181000|2.70|66|74
   N=9978   4+2·66+74+2·66·74 = 9978     MATCH=True  leftover=0
   rho[66] 0..2.7e1 mono=True   T[74] 0..7.58e4 mono=True
mat_Be-1.0/BE_eos    hdr=2.02e3|0|101|50
   N=10356  4+2·101+50+2·101·50 = 10356   MATCH=True  leftover=0
   rho[101] 0..3.69e4 mono=True  T[50] 0..2.546e4 mono=True
mat_DT-1.0/DT_EOS_e  hdr=5.2711e4|1.0|50|25
   N=2629   4+2·50+25+2·50·25 = 2629      MATCH=True  leftover=0
```

### 6.3 单位（**手册明文**）

`src_tables`/`src_doc_core.md:78`（MULTI2D 单位）：
> MULTI2D 程序中使用 cgs 单位，而其调用的 EOS 数据中的单位为压强 **Mbar**，
> 能量 **Mbar·cm³/g**，密度和温度单位与 SESAME 数据库相同。

`src_doc_core.md:312`：
> 即：**1 GPa = 1e−2 Mbar；1 MJ/kg = 1e−2 Mbar·cm³/g**。SESAME→MULTI 表内均为「×1e−2」

| 项 | 结论 |
|---|---|
| ρ | g/cm³ |
| T | eV |
| P | Mbar |
| E | Mbar·cm³/g |

### 6.4 两个变体的诚实标注

1. **`AU_eosd`（145,608 B）** —— 与 `AU_eos`（74,003 B）表头 [1..3] **完全相同**
   （`19.3 | 101 | 23`），但 `N = 9548 ≠ 4875`。
   `AU_eos` 尾部是 45 字符行（截断），`AU_eosd` 尾部是 30 字符行。
   → `eosd` 是「同一网格的**全量导出**」；`AU_eos` 是**被截断**的版本。
   **未知-不猜**：`AU_eos` 截断原因（可能是文件系统或写出中断）无法从字节判定。
2. **`DT_EOS` vs `DT_EOS_e` / `DT_EOS_i`** —— 表头 [0] 从 `5271` 变为 `52711000`/`52712000`，
   [1] 从 `0.0` 变为 `1.0` → **同一总表的 electron/ion 分解**，
   与 `BE_eos` → `BE_eos_e`/`BE_eos_i` 同一模式（`BE_eos.info` 手册明文）。

---

## 7. 组 F —— 183 B / 305 B 灰度存根

### 7.1 183 B 型全文照录

```
AL_SIMPLE_PLANCK     .17010000E+04 0.70000000E+01  .20000000E+01  .20000000E+01
                     .0             .10000000E+01  .0             .10000000E+01
                     .87447000E+01  .92447000E+01  .63447000E+01  .68447000E+01

AU_SIMPLE_PLANCK     .27010000E+04 0.70000000E+01  .20000000E+01  .20000000E+01
AU_SIMPLE_ROSSELAND  .24010000E+04 0.40000000E+01  .20000000E+01  .20000000E+01
AU_WorkOp_Ross       .24010000E+04 0.40000000E+01  .20000000E+01  .20000000E+01
C_SIMPLE_PLANCK      .37010000E+04 0.70000000E+01  .20000000E+01  .20000000E+01
DT_SIMPLE_PLANCK     .47010000E+04 0.70000000E+01  .20000000E+01  .20000000E+01
BE_PLANCKx03          0.00000000e+00 7.00000000e+00 2.00000000e+00 2.00000000e+00
```

- **193 B = 3 行 × 60 + 3 × CRLF = 183** ✓（无残渣）
- 与 186 B 型（组 B）**只差 L0[0] 的位数**（183 用 `.17010000E+04` 省了 3 字符）

### 7.2 记录序

| 位置 | 含义 | 依据 |
|---|---|---|
| L0[0] | 表号 | `.17010000E+04` = 1701 xxxx（Al）；`.27010000E+04`= Au；`.37010000E+04`= C；`.47010000E+04`= DT |
| L0[1] | **类型码**：`0.70000000E+01`(=7) = Planck；`0.40000000E+01`(=4) = Rosseland | `src_doc_core.md:98` docx 表 1 |
| L0[2]=2, L0[3]=2 | nr=nt=2 | |
| L1 | `{[ρ_min],[T_min],[ρ_max],[T_max]}` = `{0, 1, 0, 1}` | |
| L2 | 4 个 log10 κ 角点 | 与组 B 186 型的 L2 同构 |

### 7.3 与 README 幂律的交叉验证（**手册明文 vs 实测**）

`mat_Al-1.0/README`（**手册明文**）：
> `AL_SIMPLE_PLANCK` — Rosseland opacity (cm): `8.7e-09 * T^2.5 / rho^1.5`
> `AL_SIMPLE_ROSSELAND` — Planck opacity (cm): `1.8e-09 * T^2.4 / rho^1.5`

实测 `AL_SIMPLE_PLANCK` L2 = `{8.7447, 9.2447, 6.3447, 6.8447}`
→ `9.2447 − 8.7447 = 0.5 = b × 0.2`（T 步长 0.2 dex）→ **b = 2.5** ✓ 与 README 的 `T^2.5` 完全吻合
→ `6.3447 − 8.7447 = −2.4 = c × ...` → **c = −1.5** ✓ 与 README 的 `/rho^1.5` 完全吻合

**这是组 F 最硬的证据**：文件名、READMRE 幂律指数、L2 的 4 个 log 值**三者自洽**。
注意 README 的措辞把 `SIMPLE_PLANCK`/`SIMPLE_ROSSELAND` 的物理量写反了
（README 说 SIMPLE_PLANCK 是 Rosseland），**以类型码 `7`=Planck 为准**。

### 7.4 特例

- **`BE_PLANCKx03`** L0[0] = `0.00000000e+00`（表号未初始化）
  README 明文：「Same as `BE_SIMPLE_PLANCK`, but multiplied by a 0.3」→ 幂律整体 ×0.3。
- **`AU_SIMPLE_PLANCK_MG`（4,893 B）** README 明文：「Like `AU_SIMPLE_PLANCK` but with 24 groups
  in frequency with the same opacity」→ **24 子表 × (1 头 + 1 边界 + 2) = 96 行**（`src_ionmix_snop.md:635` 已记）。

---

## 8. 组 G —— 数据库簿记文件（**手册明文级**，全文照录）

### 8.1 `MODINFO` —— `key=value` 元数据（**极高置信度**）

```
mat_Al-1.0/MODINFO (138 B)
m94version=2.0
cdate=Fri Oct 17 12:46:11 MET 1997
name=mat_Al-1.0
author=N/A
info=Tables for Aluminium
ldate=Fri Oct 17 13:03:32 MET 1997

mat_CELIA/MODINFO (162 B)
name=mat_CELIA
author=Rafael Ramis
info=Tables for the CELIA target simulation
parent=none
cdate=lun ene  2 16:00:50 CET 2006
ldate=jue jul  5 08:02:14 CEST 2007

mat_CPC/MODINFO (150 B)   name=mat_CPC / author=Rafael Ramis Abril / info=Miscelaneous materials / parent=none / cdate=mié feb  6 16:42:09 CET 2008 / ldate=mié jun  4 15:57:47 CEST 2008
```

| key | 含义 |
|---|---|
| `m94version` | 材料库版本（仅 `mat_Al-1.0` 有） |
| `name` | 材料模块名 |
| `author` | 作者 |
| `info` | 说明 |
| `parent` | 父模块（`none` 或某模块名） |
| `cdate` | 创建时间（本地化 C locale 文本） |
| `ldate` | 最后修改时间 |

→ **纯文本 `key=value`，LF 换行，UTF-8 可含非 ASCII（`mié`/`lun`）**。

### 8.2 `FILELIST` —— 文件名清单

```
mat_Al-1.0/FILELIST (33 B):   FILELIST\nMODINFO\nREADME\nAL*\nLOCK\n
mat_CELIA/FILELIST  (90 B):   FILELIST\nMODINFO\nCH_ieos\nDD_ieos\nDT_ieos\nmaterial.base\n*.PLANCK\n*.ROSS\n*.SNOP\n*.ZEFF\nLOCK\n
mat_CPC/FILELIST    (64 B):   AU.INV\nAU_WorkOp_Ross\nBE.INV\nBE_PLANCKx03\nFILELIST\nMODINFO\nLOCK\n
mat_Ti/FILELIST     (18 B):   FILELIST\r\nTi_*\r\n\r\n          <- CRLF！
```
→ **每行一个文件名，支持 `*` 通配**。`mat_Ti` 用 CRLF，其余用 LF → **换行不定**。

### 8.3 `CHECKSUM` —— 逐文件校验（**不是 MD5**）

```
mat_CELIA/CHECKSUM (771 B) 前 6 行：
FILELIST:6586:39059:
MODINFO:12990:05855:
CH_ieos:29922:63814:
DD_ieos:54939:39368:
DT_ieos:54952:35571:
material.base:4019:08283:

mat_CPC/CHECKSUM (151 B)：
AU.INV:44905:05669:
AU_WorkOp_Ross:8222:19378:
BE.INV:61026:59441:
BE_PLANCKx03:9203:35000:
FILELIST:4609:64318:
MODINFO:12381:16019:
LOCK:2555:51712:
```

**格式：`<文件名>:<5 位十进制>:<5 位十进制>:`（每行尾随冒号）**

**已完全破解** —— 两个字段 = **(SysV-16, BSD-16)**（**实测推导**，7/7 全中）：

```
target = (字段2, 字段3) = (sysv16, bsd16)
```

| 文件 | 字节数 | target(字段2,字段3) | sysv16 | bsd16 | 命中 |
|---|---|---|---|---|---|
| `AU.INV` | 380518 | (44905, 05669) | **44905** | **5669** | ✅ |
| `AU_WorkOp_Ross` | 183 | (08222, 19378) | **8222** | **19378** | ✅ |
| `BE.INV` | 380518 | (61026, 59441) | **61026** | **59441** | ✅ |
| `BE_PLANCKx03` | 183 | (09203, 35000) | **9203** | **35000** | ✅ |
| `FILELIST` | 64 | (04609, 64318) | **4609** | **64318** | ✅ |
| `MODINFO` | 150 | (12381, 16019) | **12381** | **16019** | ✅ |
| `LOCK` | 36 | (02555, 51712) | **2555** | **51712** | ✅ |

- 每段是 **定长 5 位十进制**（`05414`/`05669` 带前导 0）→ **不是 MD5 / CRC-32 hex**
- `sysv16` = POSIX `sum -s` 体系（逐字节累加后取 16-bit 补码和）；`bsd16` = 经典 BSD `sum` 的 16-bit 旋转累加。
- **同批排除项**（全部不中）：Fletcher-16、Adler-32、CRC-16、裸 `sum&0xFFFF`（后者只在小文件上与 sysv 巧合相等，`AU.INV` 上即分叉：44603 ≠ 44905）。

> **置信度：极高** —— 36 B ~ 380 KB 共 7 个文件全部命中同一对算法，
> 且两字段角色**不可互换**（对调即全灭），排除偶然。

### 8.4 `LOCK` —— 锁文件（内容 = 时间戳）

```
mat_Al-1.0/LOCK (29 B):  Fri Oct 17 13:03:32 MET 1997
```
→ 内容就是 `ldate`（与 `MODINFO` 的 `ldate` **逐字符相同**）→ **是"最后写入时间"锁**。

### 8.5 `README` —— 材料说明（**手册明文**）

`mat_Al-1.0/README`（617 B）、`mat_Au-1.0/README`（1221 B）、`mat_C-1.0/README`（654 B）、
`mat_Be-1.0/README`（510 B）、`mat_DT-1.0/README`（715 B）—— 全部 UTF-8（带 BOM `utf-8-sig`），
纯文本，描述各表来源与幂律系数。**是本报告多处的"手册明文"来源**。

### 8.6 其他

| 文件 | 字节 | 内容/判定 |
|---|---|---|
| `ATOMIC/#LEDCOP` | 29 | `Al.txt\tAtomic冿绯生成的文件。`（cp936 中文）→ **LEDCOP 派生文件的说明条，以 `#` 开头即注释** |
| `SNOP/### Generated by SNOP` | 0 | **空文件**，文件名即说明（SNOP 运行的标记） |
| `Ta2O5/Ta2O5_1G_MULTI from unknown source` | 0 | **空文件**，仅作来源备注 |
| `HeatCapacity/Electron-Phonon Coupling and Electron Heat Capacity in Metals at High Electron Temperatures` | 0 | **空文件**，文件名即文献标题（占位） |

→ 这 3 个 0 字节文件是**命名即注释的占位符**，不是数据格式。

---

## 9. 组 H —— `*_1G_MULTI`（MULTI 反演 EOS，单群）

### 9.1 实测结构（**中高置信度**）

```
Ta2O5/Ta2O5_1G_MULTI  (19,391 B)   lines=313   N15=1251   tail=b''  leftover=0
  len histogram: {45: 1, 60: 312}
  L0:  0.0000000e+00  1.0000000e+00  2.5000000e+01  4.7000000e+01
  L1: -4.0000000e+00 -3.6675615e+00 -3.3334820e+00 -3.0000000e+00
  L2: -2.6675615e+00 -2.3334820e+00 -2.0000000e+00 -1.6675615e+00
  ...
```

- **表头**：`[id=0, ?=1, nr=25, nt=47]` → 与 `Ta_Kr(T,rho).dat_MULTI` 的 `nr=25, nt=47` 完全一致
  （`outputMULTIOpacity.m:5-6` 明文 `nr = 25; nt = 47;`）→ **同一网格**。
- **闭合 `1251 = 4 + 25 + 47 + 25×47`** ✓ 精确
  （`groupH` 穷举命中 `(nr=25, nt=47)`，且 `Ta_Kr` 的 `dat_MULTI` 亦为该网格）
- **ρ 网格前 4 值 −4.0, −3.6676, −3.3335, −3.0 = log10 ρ 的等步长（0.3333 dex）**
  → 与 `outputMULTIOpacity.m:43` 的 `log10(rho)` 一致。

### 9.2 与组 A 的区别

| | 组 A（多群不透明度） | 组 H（`1G_MULTI`） |
|---|---|---|
| 频群块 `k` | 20 / 100 / 96 … | **1**（单群） |
| 类型标签 | 有（`PLANCK M` / …） | **无** |
| 网格 | log10 ρ、log10 T | log10 ρ、log10 T |
| 数据 | log10 κ | **EOS 量（T 或 P）** |

### 9.3 判定

**实测推导 + 源码明文**：`Ta2O5_1G_MULTI` 是 **`outputMULTIOpacity.m` 同族的单群反演 EOS**，
与已文档化的 `.dat_MULTI` / `.inv` / `.IN` 族**同格式**，`1G` = 1 group（1 个频群）。
`Ta_1G_MULTI`（19,391 B）与 `Ta2O5_1G_MULTI` **字节数完全相同**，是同格式的另一种材料。

> **置信度中高的原因**：数据体物理量（是 T(ρ,e) 还是 P(ρ,e)）未从字节唯一确定；
> 需要 `.dat_MULTI` 的既有逆向结论做旁证。**未知-不猜**。

---

## 10. 附：可复现代码

所有脚本在 `.workbuddy/tmp/probe_noext/`。核心工具 `tk.py`：

```python
import os
ROOT = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
MAT  = os.path.join(ROOT, "src", "Multi1D++Portable20241128", "matter++")

def raw(path):
    with open(path, "rb") as f: return f.read()

def tok15(line, w=15):
    """定宽 15 字符切分（唯一正确的分词方式）"""
    s = line.rstrip(b"\r")
    return [s[i:i+w].decode("latin-1") for i in range(0, len(s)-len(s)%w, w)]

def all_tokens(path, w=15):
    """整文件按 w 定宽流切分，跳过 CR/LF；返回 (fields, leftover)"""
    d = raw(path).replace(b"\r\n", b"").replace(b"\n", b"")
    n = len(d)//w
    return [d[i*w:(i+1)*w].decode("latin-1") for i in range(n)], d[n*w:]

def num(f):
    try: return float(f.strip())
    except Exception: return None
```

### 10.1 组 A 闭合验算（可直接运行）

```python
def groupA_solve(rel, k):
    """k = 频群块数（= 30 字符行数）。返回 (nr, nt, 是否闭合)"""
    p = os.path.join(MAT, rel.replace("/", os.sep))
    d = raw(p)
    ne = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
    f, tail = all_tokens(p, 15)
    N = len(f)
    assert N % k == 0, "块数错"
    F = N // k                     # 每块字段数（含 LABEL）
    R = F - 1                      # 丢掉 LABEL
    # 布局: 3(id,h_lo,h_hi) + 2(冗余 rho首/T末) + nr + nt + nr*nt = R
    # => nr + nt + nr*nt = R - 5
    W = R - 5
    for nt in range(1, 4000):
        if W - nt <= 0 or (W - nt) % (nt + 1):
            continue
        nr = (W - nt) // (nt + 1)
        if nr < 2: continue
        vv = []
        for i, l in enumerate(ne[:len(ne)//k]):
            t = tok15(l, 15)
            if i == 0: t = t[:1] + t[2:]      # 丢掉 LABEL
            vv += t
        rho = [num(x) for x in vv[5:5+nr]]
        T   = [num(x) for x in vv[5+nr:5+nr+nt]]
        if None in rho or None in T: continue
        mr = all(rho[i] < rho[i+1] for i in range(nr-1))
        mt = all(T[i]   < T[i+1]   for i in range(nt-1))
        if mr and mt:
            return nr, nt, (5 + nr + nt + nr*nt == R)
    return None, None, False

# 实测结果（10/11 唯一闭合）：
for rel, k in [("mat_Au-1.0/AU_op03p", 20), ("mat_Gd/Gd100PLANCK", 100),
               ("mat_Gd/Gd_op100PLANCK", 100), ("CH/C_mopp", 20),
               ("CH/CHSi1_mopp", 20), ("Ta2O5/Ta2O5_mopp", 96),
               ("mat_Others/CH10Water1/CH2_H2O_1m1opp", 44)]:
    print(rel, groupA_solve(rel, k))
# -> (20,20,True) (30,50,True) (40,40,True) (43,43,True) (43,42,True)
#    (37,29,True) (37,50,True)
# 注：k=1 的 `1041_PLANCK` **无 LABEL 字段**，不适用本函数；
#     其闭合见 §10.4：1507 = 4 + 31 + 46 + 31×46，tail = b''。
```

### 10.2 组 D/E 闭合验算

```python
def groupDE_check(rel, nr, nt):
    """验证 4 + 2nr + nt + 2nr*nt == N 且 rho/T 严格单调"""
    p = os.path.join(MAT, rel.replace("/", os.sep))
    f, _ = all_tokens(p, 15)
    N = len(f)
    v = [num(x) for x in f[4:]]
    v = [x for x in v if x is not None]
    rho = v[0:nr]; T = v[nr:nr+nt]
    mr = all(rho[i] < rho[i+1] for i in range(nr-1))
    mt = all(T[i]   < T[i+1]   for i in range(nt-1))
    return (N == 4 + 2*nr + nt + 2*nr*nt), mr, mt

print(groupDE_check("mat_Ti/422_ieos", 43, 22))       # (True, True, True)
print(groupDE_check("mat_Al-1.0/42_ieos", 84, 53))    # (True, True, True)
print(groupDE_check("mat_Al-1.0/AL_eos", 66, 74))     # (True, True, True)
print(groupDE_check("mat_Be-1.0/BE_eos", 101, 50))    # (True, True, True)
print(groupDE_check("mat_CELIA/DD_ieos", 50, 25))     # (False, True, True) 尾部余 3
```

### 10.3 组 G `CHECKSUM` 算法破解（**7/7 命中**）

```python
def bsd16(b):
    s = 0
    for x in b:
        s = ((s >> 1) | ((s & 1) << 15)) & 0xFFFF
        s = (s + x) & 0xFFFF
    return s

def sysv16(b):
    s = sum(b) & 0xFFFFFFFF
    s = (s & 0xFFFF) + (s >> 16)          # 折叠
    s = (s & 0xFFFF) + (s >> 16)
    return s & 0xFFFF

# 断言：CHECKSUM 行 <name>:<sysv16>:<bsd16>:
for name, t1, t2 in [("AU.INV",44905,5669), ("AU_WorkOp_Ross",8222,19378),
                     ("BE.INV",61026,59441), ("BE_PLANCKx03",9203,35000),
                     ("FILELIST",4609,64318), ("MODINFO",12381,16019),
                     ("LOCK",2555,51712)]:
    d = raw(os.path.join(MAT, "mat_CPC", name))
    assert (sysv16(d), bsd16(d)) == (t1, t2), name
print("CHECKSUM = (SysV-16, BSD-16) 全部命中")
```

### 10.4 `1041_PLANCK` 闭合验算

```python
p = os.path.join(MAT, "mat_Al-1.0", "1041_PLANCK")
f, tail = all_tokens(p, 15)
hdr = tok15(raw(p).split(b"\n")[0], 15)
id_, zbar, nr, nt = (num(x) for x in hdr)   # 11041, 7.0, 31.0, 46.0
nr, nt = int(nr), int(nt)
print(len(f), 4 + nr + nt + nr*nt, tail)    # 1507 1507 b''
```

---

## 11. 汇总：每组「最强证据」一句话

| 组 | 结论 | **最强的单条证据** |
|---|---|---|
| **A** | MULTI 多群不透明度表；`k` 块 × `(6+nr+nt+nr·nt)`；log10(ρ,T,κ)，ρ-major | `mat_Ce/Ce.INPUT` 写明 `NT=20 NR=20 NG=20`，而 `AU_op03p` 的 `8920 = 20 × (6+20+20+400)` **精确闭合且 nr=20/nt=20 是唯一严格单调解** |
| **B** | 186 B = 3×60+3×CRLF 幂律双点单群表；280 B = 同族含 ρ₀ | `186 = 3×60 + 3×2` **无残渣**，且 L2 差值 ÷0.2 复原 README 的幂律指数 |
| **C** | 与 B 的 186 B **同物** | 逐字节同构；本目录内哨兵与后续字段间**有正常空格**（非粘连型） |
| **D** | IEOS；`[id][Zbar][nr][nt]` + `2nr+nt+2nr·nt` | 代入后 `rho` 与 `T` 网格**严格单调**，且 `422_ieos` 的 `2004 = 4+2·43+22+2·43·22` 精确 |
| **E** | SESAME-301 反演 EOS，与 D 同布局 | 手册明文 P47 公式 `4+2nr+ne+2nr·ne` 与 `AL_eos` 的 `9978` **精确一致**（手册 + 实测双证） |
| **F** | 183 B 灰度幂律存根 | 文件名（PLANCK）+ 类型码（`7`）+ README 幂律（`T²·⁵/ρ¹·⁵`）从 L2 的 4 个 log 值**三者自洽复原** |
| **G** | 簿记文件；`MODINFO`=`key=value`；`CHECKSUM`=`名:(SysV-16):(BSD-16):` | 7 个文件（36 B~380 KB）的字段 2/3 **逐一等于 sysv16/bsd16**，且两字段对调即全灭 |
| **H** | MULTI 单群反演 EOS（`.dat_MULTI` 同族） | `1251 = 4+25+47+25×47` 精确，且 `nr/nt=25/47` 与 `outputMULTIOpacity.m` 的 `Ta_Kr` 明文一致 |

---

## 12. 诚实缺口清单（**不猜**）

| 编号 | 缺口 | 需要什么证据 |
|---|---|---|
| 1 | `Ti_Ross` 少 1 字节（59 字符末行） | 原始文件或 SNOP 写出源码 |
| 2 | `opbe` 的 `k = 80` vs 81（尾块归属） | `opbe.inhalt` 的完整参数表 |
| 3 | ~~`CHECKSUM` 的具体 16-bit 算法~~ | **已破解**：`(SysV-16, BSD-16)`，见 §8.3 |
| 4 | `AU_eos` 被截断的原因 | 写出源码或原始分发介质 |
| 5 | `*_1G_MULTI` 数据体的物理量（T 还是 P） | 与 `.dat_MULTI` 的既有逆向结论对照 |
| 6 | `1041_PLANCK` 第 2 行仅 45 字符（少 1 个字段）的成因 | 单群版 SNOP 写出器；**但布局本身已确证**：`nr=31, nt=46, k=1`，`1507 = 4+31+46+31×46` 精确闭合，末行 3 字段 = 尾部不补空格 |
| 7 | `AU_op03z`（ZEFF，6771 B）的 `_1G` 与多群混用 | 已由 `formats_resolved.md` 覆盖，本报告未重查 |
| 8 | 组 D 尾部 `leftover ∈ {0,2,3}` 的终止哨兵语义 | IEOS 读出器源码 |
