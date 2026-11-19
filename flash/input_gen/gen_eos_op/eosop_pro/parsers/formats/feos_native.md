# feos_native.py —— FEOS 原生表（F4b；`*.feos`）★ 布局已由源码定案

> **适用仿真软件**：FEOS 包（Faik et al.）原生输出 `*.feos`（含 matter++ 分发实例）| **官方链接**：FEOS 项目页 https://physik.faik.de/feos.php
> **权威依据（2026-11-15 定案，R3 废除）**：`feos/src/FEOS/Code/FE-01_TABTOOLS.C` `write_FEOS_format`（196–355 行）+ 三方实测一致（gen_eos_op/feos 产物 Al/SiO2/Au、matter++ 25 个 `.feos`、C 源码）。同材料两表（`mat_Al-1.0/Al.feos` vs `Z13_1.00-20261114_2316.feos`，同 SESAME#3717）**离子块 Pi/Ei/Si/Fi/FTF 逐字节一致**——布局切分精确性的最强实证。
> **概要**：行 0 十字段 + 行 1 十参数 + `A/Z/X`（各 ne 个）+ rho/T 网格（**前导 `Qstart=0.0` 哨兵**）+ 16 个 T-major 二维块 + Qtot + Q（k 最内层交错）——**全部确定性解码，无猜测**。| **标记规约**：与《[eosop变量控制字典](../../docs/eosop变量控制字典.md)》同步；格式权威版本 = [20 手册 §5.2](../../docs/20_格式规格与物理量单位手册.md)

## 1. 格式布局与计数公式（FE-01_TABTOOLS.C 定案）

```
行 0（10 数）: [FileVersion, NRho_decl, NT_decl, Nelements,
                Tcalclimit, Rhocalclimit, RhoRef, TRef, B0, SESAME#]
行 1（10 数）: [ElectronOffset, IonOffset, Ecoh, ss_n, ss_m,
                ss_A, ss_B, Atot, Ztot, Xtot]
连续流: A[]/Z[]/X[]（各 ne 个）
     -> rho 网格（NRho_decl 个，首点 = Qstart = 0.0 前导哨兵）
     -> T 网格（NT_decl 个，首点同上）
     -> 16 个二维块（T 外循环、rho 内循环 = T-major）:
        P,E,S,F | Pe,Ee,Se,Fe | Pi,Ei,Si,Fi | PTF,ETF,STF,FTF
        （每块 NRho_decl × NT_decl，含哨兵行列）
     -> Qtot（同形状）
     -> Q（ne 个元素按 k 最内层交错: 流序 = for j, for i, for k）
```

**计数公式**（全文件数值总数，含两行头部）：

```
N = 10 + 10 + 3·ne + NR_decl + NT_decl + (17 + ne) · NR_decl · NT_decl
```

Al（ne=1, 192×69）：N = 20 + 3 + 192 + 69 + 18·13248 = **238748** ✓（实测闭合）。

**网格语义**：`NR_decl/NT_decl` = 真实点数 **+ 1**（`makeRTPointArray` 把 `array[0]=Qstart=0.0` 写进网格首点，哨兵行/列计入声明值）。解析器确定性切分后修剪哨兵，输出严格正的真实网格。⚠️ **哨兵在前导，不在尾部**——旧文档"尾部 0.0 哨兵"是 `lead=rest[:4]` 硬编码错位导致的误诊，已勘误。

**Qtot 语义（关键勘误）**：`LIB-03_TF_MIXTURE.C:123` `*Qtot += Qtemp * Xtot[i]` + `FE-03_MAIN.C:267` "Qtot for molecule" —— Qtot = Σₖ Qₖ·Xₖ 为**每化学式单位**总电离（未归一）；每核平均电离 = Qtot/Xtot。ne=1 时 Xtot=1 无差别；混合物（SiO2）必须除——feos_to_cn4 的 zbar 映射已按此归一（实测 SiO2 zbar 上限 10 = 30/3）。

**Q 交错实证**：SiO2 双元素表流首 `[33.06, 8.959, 2.482, 1.975, ...]`，Qtot[0]=50.98 = 33.06+2×8.959、Qtot[1]=6.431 ≈ 2.482+2×1.975 —— 交错解释精确守恒，连续块解释被否证（8.959 > 6.431 单值即超总量）。

## 2. 物理量与单位（uv 标记；kind = source code）

单位体系 cgs + eV（压强 dyn/cm²、比能/自由能 erg/g、熵 erg/g/eV、rho g/cm³、T eV、Qtot/Q 无量纲），解析器**不换算**（换算在 feos_to_cn4）：

| 字段 | 意义 | 单位 | 来源类型 | 标记 |
|---|---|---|---|---|
| `rho` | Mass density axis（哨兵已修剪） | `g/cm3` | code | **uv** |
| `Te` | Electron temperature axis（哨兵已修剪） | `eV` | code | **uv** |
| `P` / `Pi` / `Pe` / `PTF` | 总压 / 离子分压 / 电子分压（TF+冷曲线修正）/ 原始 TF | `dyn/cm2` | code | **uv** |
| `E` / `Ei` / `Ee` / `ETF` | 总比能 / 离子 / 电子 / TF（已减 ElectronOffset） | `erg/g` | code | **uv** |
| `S` / `Si` / `Se` / `STF` | 总熵 / 离子 / 电子 / 原始 TF | `erg/g/eV` | code | **uv** |
| `F` / `Fi` / `Fe` / `FTF` | 总自由能 / 离子 / 电子 / TF（已减偏移） | `erg/g` | code | **uv** |
| `Qtot` | 每化学式单位总电离（Σ Qₖ·Xₖ） | `-` | code | **uv** |
| `Q0`/`Q1` | 元素 k 平均电离（k 交错） | `-` | code | **uv** |

注意：`ETF/FTF` 已减电子零点偏移而 `PTF/STF` 为原始 TF（`GetElectronEOSQuantities`）。熵块相边界点归属受 Maxwell 构建数值路径影响（同材料两表 S 块相边界点实测差 2.4e-4，属物理行为）。

## 3. 解析器 API 与用法

```python
FAMILY = "feos_native"
HEADER_FIELDS = ("file_version", "nrho_decl", "nt_decl", "nelements",
                 "tcalc_limit", "rhocalc_limit", "rho_ref", "t_ref",
                 "bulk_modulus", "sesame_no")
LINE1_FIELDS = ("electron_offset", "ion_offset", "ecoh",
                "ss_n", "ss_m", "ss_A", "ss_B", "atot", "ztot", "xtot")
FEOS_BLOCKS = ("P","E","S","F","Pe","Ee","Se","Fe",
               "Pi","Ei","Si","Fi","PTF","ETF","STF","FTF")

def decode(path) -> FeosTable              # 权威结构化解码（网格含哨兵）
def parse(path, relpath="", *, unit_hint_T=None) -> ParsedTable   # 布局定案全解码
def parse_all(path, relpath="", *, unit_hint_T=None) -> list[ParsedTable]
def grid_length(seq, start, declared) -> int    # 防御性单调前缀辅助（兼容保留）
def find_sibling_301(path, relpath) -> Path | None   # .301 兄弟（两种命名都试）
def positive_indices(t_axis, rho_axis) -> tuple   # 哨兵修剪索引
```

示例：

```python
from eosop_pro.parsers.feos_native import parse

t = parse("matter++/mat_B/B.feos", "mat_B/B.feos")
print(t.summary())                  # 修剪后真实网格
print(t.fields["Pi"][:5])           # 16 块已解码（T-major 扁平）
print(t.n_numbers_seen == t.n_numbers_expected)  # 计数公式闭合
```

跨包消费：`feos/feos_run/feos_to_cn4.py` 复用本模块 `decode/FeosTable/FEOS_BLOCKS/positive_indices`（布局知识单一事实源），仅做单位换算（×1e-7/×1e-4）、zbar=Qtot/Xtot 归一与 cn4 组装。

`.feos` 分派候选顺序 `[feos_native, multi_eos]`：`mat_Al-1.0/AL_eos.feos` 名为 FEOS 实为 SESAME（与 `AL_eos` 字节相同）回退 F1；`hyades/**.dat.feos` 让位 hyades 族。

## 4. 陷阱与已知边界

1. **前导哨兵（定案）**：`0.0` 在网格**首点**，声明值 = 真实 + 1；确定性切分 + 修剪，禁用猜测式盲切。
2. **Qtot 是每化学式总量**：混合物转 cn4 时 zbar 必须除以 Xtot（每核平均）；ne=1 无差别。
3. **Q 按 k 最内层交错**：`for j, for i, for k`；ne>1 时连续块解释会打乱 Q（计数校验抓不到，必须用 zbar=ΣwₖQₖ 守恒检验）。
4. **简并角落越界**：压力反演电离度在低 T × 低 rho 角点可超 Z（实测 Cl/F/K/Sc2，如 Cl zbar=41.77@Z=17）——FEOS 已知局限，解析器 notes 显式告警。
5. **3 位指数粘连变体**：`mat_Others/SiO2.feos` 行 0 无分隔且指数 3 位（`1.20600000e+001`=12.06），`extract_numbers` 拒收（旧版同样拒收，非回归）；29 个 matter++ `.feos` 中 25 个可解析，其余 4 个为非本族文件（hyades ×2、改名 SESAME ×1）+ 此变体。
6. `.301` 兄弟命名两种都试：`Al.feos` ↔ `FEOS/Al.feos.301`、`B.feos` ↔ `B.301`；NR/NT 不一致时显式告警。
7. 行 1 参数可能含粘连 denormal（B/Cr 的软球参数未初始化）——`fortran_numbers.extract_numbers` 已正确抢救。

## 5. 溯源

| 等级 | 记号 | 依据 | 本地定位（gen_eos_op 相对路径） |
|---|---|---|---|
| L1 | `code:` | `FE-01_TABTOOLS.C::write_FEOS_format`（196–355 行：布局逐段锚点） | `feos/src/FEOS/Code/FE-01_TABTOOLS.C` |
| L1 | `code:` | `LIB-03_TF_MIXTURE.C:123`（Qtot = Σ Qₖ·Xₖ）+ `FE-03_MAIN.C:267` | `feos/src/FEOS/Code/` |
| L1 | `measured:` | 三方实测一致 + 同材料离子块逐字节一致（SESAME#3717 双表） | `feos/feos_run/outputfiles/`、`src/Multi1D++Portable20241128/matter++/` |
| L5 | `uv` | 人工复核待用户在 `registry/field_checks.py` 置 `checked=True` | `registry/field_checks.py::_FEOS_NATIVE` |

实现脚本：`eosop_pro/parsers/feos_native.py`；转换器：`feos/feos_run/feos_to_cn4.py`；理论背景与 FEOS 物理模型详见 `feos/feos_run/FEOS用户指南.md`。
