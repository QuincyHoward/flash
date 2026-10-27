import os, shutil

P = 'src/multi_docs/MultiEOSOP格式说明.md'
shutil.copy(P, P + '.bak4')

t = open(P, encoding='utf-8').read()
orig_len = len(t)

# ============================================================
# PATCH 1 — new §14.5: 无扩展名多群不透明度表
# inserted right before "## 第15章"
# ============================================================
NEW_145 = '''
### 14.5 无扩展名多群不透明度表（`PLANCK` / `ROSSELAND` / `EPS` / `ZEFF`）

本节处理 `matter++/` 下**完全不使用扩展名**的一类数据文件。它们数量最多（**150 个文件**，
占 `matter++/` 文件总数的 12.4%），但 `matter++/Readme.txt` 的分派规则**完全没有提到**
它们该如何读取 —— 这是随包文档的一处**实质性缺口**，本节据实补足。

#### 14.5.1 为什么它们没有扩展名

这批文件由 **SNOP / MULTI-94 工具链**直接写出，而非由 FEOS 或 IONMIX 导出。其命名沿用
MULTI 的**族标记**约定（`_op` / `_mop` / `_opp` / `_opr` / `PLANCK` / `ROSS`），
并在文件名中直接携带**材料号、群数、能带范围**等元信息，因此**不需要扩展名**做类型分派 —— 
这与 MULTI 程序"按文件名而非内容嗅探"的传统（见 §1.2）一脉相承。

#### 14.5.2 五个大类

| 大类 | 命名特征 | 内容 |
|---|---|---|
| EOS 总表 | `*_eos` / `*_EOS` / `*_eosd` | SESAME 风格 EOS（"SESAME library, probably"，手册自述存疑） |
| 反演 EOS | `*_ieos` / `*_ieos_e` / `*_ieos_i` | 由 MULTI 反演出的 EOS；`_e`/`_i` = 电子/离子分量 |
| 不透明度 | `_op*` / `_mop*` / `*PLANCK*` / `*ROSS*` / `*EPS*` / `*ZEFF*` | **本节重点**，多群不透明度表 |
| 光学常数 | `*_SIMPLE_PLANCK` / `*_SIMPLE_ROSSELAND` / `*_IDEAL_GAS` | 解析式不透明度的**离散常数采样点**（stub） |
| 记账 | `FILELIST` / `LOCK` / `MODINFO` / `CHECKSUM` / `README` | 数据库元数据，非数据格式 |

#### 14.5.3 记录结构（多群不透明度表）

```
文件级表头 : 1 行 × 60 字符 = 4 × 15
   [0:15]   表号（6–7 位；也可写成 15 字符浮点如 '.27100000E+04'）
   [15:30]  类别名 + ' M'（'PLANCK M' / 'ROSSELAND M' / 'EPS M'）
            注意 ZEFF 无 ' M'，只有 3 个后续字段
   [30:45]  NR（密度网格点数）
   [45:60]  NT（温度网格点数）

随后 K 个能量群，每群占 2 + ceil((NR+NT+NR·NT)/4) 行：
   a) 2 值行（30 字符）：[E_lo, E_hi]              能量带上下界，单位 eV
   b) 4 值行（60 字符）：[E_lo, E_hi, NR, NT]       记录骨架，前两值与 a) 重复
   c) 数据区          ：log10(ρ[NR]) | log10(T[NT]) | log10(κ[NR·NT])
                        共 NR + NT + NR·NT 个值，每行 4 × 15 = 60 字符
```

**行数公式**：`总行数 = 1 + K · (2 + ⌈(NR+NT+NR·NT)/4⌉)`

**格式串**：`%15.7e`（与 §15.9 的 `outputMULTIOPacity.m` 明文一致）

#### 14.5.4 走向：外层 T、内层 ρ ⇒ 密度变化最快

由官方 MATLAB 写出器 `matlab/outputMULTIOPacity.m:58–68` 明文：

```matlab
for i=1:nt
  for j=1:nr
    fprintf(fout, '%15.7e', log10(kappa((i-1)*nr + j)));
  end
end
```

展平索引 = `(i_T − 1)·NR + j_ρ`。**与 §15.2 的 `.sesame` 走向完全一致**（二者可共用同一
转置工具）。独立实测印证：数据区的"局部凹陷"间隔恒为 **NT = 20**。

#### 14.5.5 闭合验算（7/7 全部精确闭合）

| 文件 | 表号 | NR×NT | 群数 K | 每群数据区值数 | 总行数 | 闭合 |
|---|---|---|---|---|---|---|
| `mat_Au-1.0/AU_op03p` | 27003003 | 20×20 | **20** | 440 | 2,240 | **20/20 ✓** |
| `mat_Gd/Gd20PLANCK` | 27003000 | 20×20 | **20** | 440 | 2,240 | **20/20 ✓** |
| `mat_Gd/Gd100PLANCK` | 27003000 | 30×50 | **100** | 1,580 | 39,700 | **100/100 ✓** |
| `mat_Au-1.0/Au100PLANCK` | 79003000 | 30×50 | **100** | 1,580 | 39,700 | **100/100 ✓** |
| `CH/CHSi1_mopp` | 1400003 | 43×42 | **20** | 1,891 | 9,500 | **20/20 ✓** |
| `CH/CHSi1_mopp100` | 1400003 | 43×42 | **100** | 1,891 | 47,500 | **100/100 ✓** |
| `mat_Be-1.0/opbe` | 20203000 | 20×20 | 80 | 440 | — | **79/80**（末群截断） |

验算实例 `AU_op03p`：1 + 20·(2 + ⌈440/4⌉) = 1 + 20·112 = **2,241** 行 ✓

#### 14.5.6 群数 K 由「文件名后缀」与「文件本身」双重编码

- **文件名后缀**：`*20*` → 20 群；`*100*` → **100 群**
  - `Gd20PLANCK`(20) 与 `Gd100PLANCK`(100) **表号同为 27003000**
  - `CHSi1_mopp`(20) 与 `CHSi1_mopp100`(100) **表号同为 1400003**，字节数恰好 ×5
- **文件本身**：数 2 值（30 字符）行的个数即 K

> **⚠ 解析规约**：**必须由文件本身判定 K**，文件名后缀仅作交叉校验。
> 反例 `mat_Be-1.0/opbe`：文件名不含群数提示，实际却有 **80 群**。

#### 14.5.7 能量带边界（eV）实例

| 文件 | 前 8 个带界 |
|---|---|
| `AU_op03p`（20 群） | 1, 10, 50, 100, 150, 250, 400, … |
| `Gd20PLANCK`（20 群） | 1, 10, 50, 100, 150, 250, 400, 550, … |
| `Gd100PLANCK`（100 群） | 1, 2.8, 4.6, 6.4, 8.2, 10, 18, 26, … |
| `opbe`（80 群） | 1, 62, 70.86, 82.67, 95.38, 103.3, 105.6, … |

**权威佐证**：`mat_Au/AU_info`（手册明文）写有
`"Z:27002003; P:27003003; R:27004003; E:27005003"` 及
`"20 GRUPPEN ZWISCHEN 0 UND 5 KEV"`（20 群，0–5 keV 之间）；
`mat_Ce/Ce.INPUT` 的 `FG(1)=1,10,50` 即群界定义。

> **⚠ 截断警告**：`CHSi1_mopp100` 的带界到 `198–200` 即止 ⇒ 该表**在 200 eV 截断**；
> 而 `CHSi1_mopp` 到 400 eV。**两者带宽划分不同，不可混用。**

#### 14.5.8 表号语义（与 SESAME 不透明度表号区相容）

| 类别 | 表号模式 | 实例 |
|---|---|---|
| `ZEFF` | 材料ID + `2000` | `27002000`、`79002000` |
| `PLANCK` | 材料ID + `3000` 或 `0003` | `27003003`、`79003000`、`1400003` |
| `ROSSELAND` | 材料ID + `4000` 或 `0002` | `27004003`、`79004000`、`1400002` |
| `EPS` | 材料ID + `5000` 或 `0003` | `27005003`、`79005000`、`0700003` |

`AU_info` 的 `Z/P/R/E` 四位缩写与 `0x2xxx/0x3xxx/0x4xxx/0x5xxx` 段位一一对应，
落在 SESAME 的 Opacity 表号区（0–9999 / 10000 / 60000）之内。

#### 14.5.9 `ZEFF` 表头的差异

`*ZEFF*` 文件的表头**没有类别名**，字段为 **3 个数值**：

```
 27002000       0.60000000E+02        0.20000000E+02  0.20000000E+02
   表号              Z (=6.0)                NR              NT
```

解析须按"**取最后两个数作 (NR, NT)**"处理，不可套用 `PLANCK` 的 4 字段布局。

> **⚠ 数据侧矛盾**：`mat_Ce/Ce.ZEFF` 的 Z 字段为 **6.0**（碳），但该文件属于 `mat_Ce`
> （铈，Z=58）。这是**数据侧的已知矛盾**，解析器不应据此推断元素，只宜原样保留。

#### 14.5.10 记账文件语法（非数据格式）

| 文件 | 语法 | 实例 |
|---|---|---|
| `MODINFO` | `key=value` 行 | 键全集：`name` / `author` / `info` / `parent` / `cdate` / `ldate` / `m94version`；`m94version=2.0` 提示 **MULTI-94 系谱** |
| `FILELIST` | 纯清单，**允许 glob** | `AU_*`、`AU.INV` |
| `LOCK` | 单行日期串 | `Mon Oct 20 15:42:58 MET 1997` |
| `CHECKSUM` | `<文件>:<十进制>:<十进制>:` | `AU.INV:44905:05669:` —— **两个 5 位十进制校验和，非 MD5**，末尾带冒号 |

#### 14.5.11 stub 文件（183 B / 305 B）

| 大小 | 文件 | 结构 |
|---|---|---|
| 183 B = 3 行 | `*_SIMPLE_PLANCK` / `*_SIMPLE_ROSSELAND` / `*_WorkOp_Ross` / `*_PLANCKx03` | `E+04 value` 与 `E+02 value` 交替的**常数采样表** |
| 305 B = 5 行 | `*_IDEAL_GAS` / `*_eos_i` 等 5 个 | 同上，5 行 |

它们是**解析式不透明度**（如 `_SIMPLE_PLANCK` = `3.0e-07 · T^1.2 / ρ^1.2`）的离散化采样点，
而非独立数据源。

#### 14.5.12 命名 token 语义（手册与 README 明文）

| token | 含义 | 依据 |
|---|---|---|
| `_op03e` | 多群**非局域热平衡因子**（multigroup non-LTE factor），由 SNOP 产生 | README 明文 |
| `_op03p` | Planck 不透明度（SNOP） | README 明文 |
| `_op03r` | Rosseland 不透明度（SNOP） | README 明文 |
| `_op03z` | Z-effective | README **自述 unknown provenance** |
| `_SIMPLE_PLANCK` | `3.0e-07 · T^1.2 / ρ^1.2` | README 明文 |
| `_SIMPLE_PLANCK_MG` | 同上，但分 **24 频率群** | README 明文 |
| `_PLANCKx03` | 即 `_SIMPLE_PLANCK × 0.3` | README 明文 |
| `_WorkOp_Ross` | WorkOp-III:94 数据 | README 明文 |
| `_info` | SNOP 参数（Tsakiris & Eidmann 1987） | README 明文 |
| `_eos` / `_eosd` | "SESAME library, probably"（手册自述存疑） | README 明文 |
| `_IDEAL_GAS` | `Z=19.998, A=197.0, γ=1.2168` | README 明文 |

> **⚠ 易错点**：`x03` 是 **×0.3**，**不是 ×3**。README 原文为
> `BE_PLANCKx03 = BE_SIMPLE_PLANCK × 0.3`。

#### 14.5.13 `_ieos` 的首行格式

`*_ieos` 文件的首行为 **4 个整数/浮点数**：

```
<材料号> <T[eV]> <ρ_max> <ρ_min>
```

实例：`mat_Al-1.0/41_ieos` → `41 2.7 44.0 22.0`；
`mat_C-1.0/511_ieos` → `511 …`；`mat_Others/CH10Water1/CH10Water1_ieos` → 材料号 `61310`。

> `41` / `42` / `422` / `511` 这类**纯数字前缀的编码规则尚未解出**（见 §15.14）。

#### 14.5.14 定稿解析器

```python
def read_multigroup_opacity(path):
    """读无扩展名多群不透明度表（PLANCK / ROSSELAND / EPS / ZEFF）。

    返回 (table_no, kind, NR, NT, groups)，其中 groups 为长度 K 的列表，
    每项含 band=(E_lo, E_hi) / log10rho / log10T / log10kappa / complete。
    """
    raw = open(path, 'rb').read().replace(b'\\r\\n', b'\\n')
    L = [l.decode('latin-1') for l in raw.split(b'\\n') if l.strip()]

    hdr = L[0]
    table = hdr[0:15].strip()
    kind  = hdr[15:30].strip()          # 'PLANCK M' / 'ROSSELAND M' / 'EPS M' / '' (ZEFF)
    NR    = int(float(hdr[30:45]))
    NT    = int(float(hdr[45:60]))

    # 每个群以 2 值（30 字符）行为界；须先排除文件级表头所在行
    marks = [i for i, l in enumerate(L) if len(l) == 30]
    groups = []
    for k, s in enumerate(marks):
        # 骨架行：4 值，其前两值应与带界行一致
        skel = L[s + 1]
        e_lo, e_hi = float(L[s][0:15]), float(L[s][15:30])
        assert abs(float(skel[0:15]) - e_lo) < 1e-9, '骨架行与带界行不一致'
        assert abs(float(skel[15:30]) - e_hi) < 1e-9

        # 数据区终点 = 下一群的带界行/骨架行之前
        e = marks[k + 1] if k + 1 < len(marks) else len(L)
        vals = []
        for l in L[s + 2:e]:
            for j in range(0, len(l) - 14, 15):
                vals.append(float(l[j:j + 15]))
        n = NR + NT + NR * NT
        groups.append({
            'band':       (e_lo, e_hi),
            'log10rho':   vals[0:NR],
            'log10T':     vals[NR:NR + NT],
            'log10kappa': vals[NR + NT:NR + NT + NR * NT],
            'complete':   len(vals) == n,      # opbe 末群为 False
        })
    return table, kind, NR, NT, groups
```

> **⚠ 三个陷阱**
> 1. 必须先**排除含类别名的行**（文件级表头为 60 字符）再找 30 字符行，否则误判群界。
> 2. 每群的**骨架行（4 值）与带界行（2 值）前两值重复**，计数时不可把骨架行算进数据区，
>    否则每群会多算 4 个值（440 → 444）。
> 3. **末群可能截断**（`opbe` 第 80 群仅 884 值），解析器须标记 `complete=False`
>    而非断言崩溃。

'''

anchor15 = '## 第15章 仍未完全解析的格式：逐项处置与解读边界'
assert anchor15 in t, 'anchor 第15章 not found'
t = t.replace(anchor15, NEW_145.lstrip('\n') + '\n' + anchor15, 1)

open(P, 'w', encoding='utf-8', newline='\n').write(t)
print('PATCH1 done: +%d chars  (%d -> %d)' % (len(t) - orig_len, orig_len, len(t)))
