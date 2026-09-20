# 源码中的格式定义

> 目标：用「写出端的格式化语句」反推每种数据文件的精确读写格式。
> 纪律：本文件引用的每一行均来自真实文件，附 `路径:行号`。凡源码中确无定义者，明确标注。
> 生成时间：2026-09-18

---

## 0. 关键结论（先读这一段）

**本工作区内可用的"程序源码"只有一份 Fortran 源文件**：

```
ionmix/ionmix/src/Ionmix/abjt_03.f    381,216 B    5,363 行    F77 定格式
```

`Multi1D++Portable20241128` **是一个纯二进制发行版**（含 `Multi1D++.exe` / `Multi.exe` /
`Snop++.exe` / `FEOS.exe` / `mpqeos.exe` / `ShowEOS.exe`），**没有附带 Fortran/C++ 源码**。
因此**绝大多数后缀（`.dem` `.eps` `.nofree` `.avsqfree` `.cst` `.feos` `.base` `.template`
`.301` `.304` `.305` 等）在源码层面无定义可查**。

但本工作区仍存在**三类"权威写出端"**，其地位等同于源码：

| 类别 | 文件 | 覆盖后缀 | 权威性 |
|---|---|---|---|
| **A. Fortran 源码** | `ionmix/…/abjt_03.f` | `.cn4` `.cnr` | ★★★★★ 唯一真源码 |
| **B. MATLAB 写出器** | `…/matlab/outputMULTIOpacity.m`、`outputHyadesEOS.m`、`output2file.m`、`exportData2File.m` | MULTI 不透明度、Hyades EOS、通用曲线 | ★★★★★ 程序内附的官方写出脚本 |
| **C. 官方文档** | `doc/SNOP.MANUAL`、`doc/multi1d7.6/manual`、`material.base` 注释区 | SNOP、fort.10、`.base` 关键字 | ★★★★ 官方文字规格 |

**已验证的 Python 镜像实现** `eosop_pro/eosop_pro/convert/writers_multi.py` 明确写出其
逐条对照上述 MATLAB 写出器（见该文件第 5–9 行注释），可作为交叉验证的第二证据。

---

## 1. 源码清单

### 1.1 真正的源码（Glob + 内容确认）

| 路径 | 字节 | 行数 | 形式 | 说明 |
|---|---|---|---|---|
| `ionmix/ionmix/src/Ionmix/abjt_03.f` | 381,216 | 5,363 | F77 定格式 | IONMIX 全套程序（MacFarlane 1989） |

**这是本工作区唯一含 `WRITE`/`FORMAT` 语句的文件。** 其余全部为 `.exe` / `.dll` / 数据文件 / 文档。

### 1.2 参与定义格式的"程序内附写出脚本"

| 路径 | 字节 | 行数 | 语言 | 定义的后缀 |
|---|---|---|---|---|
| `…/matlab/outputMULTIOpacity.m` | — | 71 | MATLAB | MULTI 不透明度表（F2 族） |
| `…/matlab/outputHyadesEOS.m` | — | 99 | MATLAB | Hyades EOS（F3 族） |
| `…/matlab/output2file.m` | — | 8 | MATLAB | 通用 x-y 两列曲线（`.hug`/`.zeff`/`.planck`/`.ross` 等） |
| `…/matlab/exportData2File.m` | — | 22 | MATLAB | 时间序列多列（后处理输出） |

### 1.3 官方文档中的规格

| 路径 | 行数 | 覆盖内容 |
|---|---|---|
| `…/doc/SNOP.MANUAL` | 174 | SNOP 输入 namelist + 输出文件说明（`SNOP.TAB` 为 MULTI 格式） |
| `…/doc/multi1d7.6/manual` | 301 | 原始 MULTI-7.6 的输入 section + **fort.10 二进制记录结构**（第 208–277 行） |
| `…/matter++/material.base` | — | 材料注册表；关键字 `PLANCK`/`ROSSELAND`/`EMS`/`ColdOpacity`/`ZEFF`/`ZeffSquared`（第 20–29 行注释区） |

### 1.4 明确"无源码"的清单

以下均为**二进制可执行文件**，不含任何可读格式定义：

```
Multi1D++.exe  Multi1D.exe  multi7.exe  MULTIfs.exe
Snop++.exe     snop.exe
FEOS.exe       mpqeos.exe   ShowEOS.exe   Ioniz.exe
GUI4Multi1D.exe  gnuplot.exe  wgnuplot.exe
gsl.dll  gslcblas.dll  msvcr71.dll  ZedGraph.dll
```

---

## 2. 摘要表

| 后缀 | 定义位置 | 格式串 | 维数 | 置信度 |
|---|---|---|---|---|
| `.cn4` | `abjt_03.f:4662–4743`（`owtf`, `isw(21)≠0`） | `4e12.6` / `i12` / `2i10` | nt×nd；ng×nt×nd | ★★★★★ |
| `.cnr` | `abjt_03.f:4598–4621`（`owtf`, `isw(8)=1/12/13`） | `4e12.6` / `4e12.6+i12` | nt×nd；ntrad 维 | ★★★★★ |
| `*.dat`(MULTI 不透明度) | `outputMULTIOpacity.m:39–69` | `%15.7e` ×4/行 | nr+nt+nr·nt | ★★★★★ |
| Hyades EOS (`*.hyades.dat`) | `outputHyadesEOS.m:55–97` | `%15.8e` ×5/行 | L=2+nr+nt+2·nr·nt | ★★★★★ |
| 通用两列曲线 | `output2file.m:5` | `%13.7e\t%13.7e` | 2 列 | ★★★★★ |
| 时间序列多列 | `exportData2File.m:13–19` | `%12.8e` + `\t` | 1+ncol | ★★★★★ |
| `.coldopacity` | **源码中无定义**（仅数据样例） | 实测表头 `Eph\tmiu` / `eV\tcm2/g` + 2 空行 + 数值对 | 2 列 | ★★ 实测 |
| `.dem` | 仅 `wgnuplot.mnu:13` 菜单项 → **文件格式无源码定义** | — | — | ☆ |
| `.eps` `.nofree` `.avsqfree` | **源码中无定义** | — | — | ☆ |
| `.feos` `.301` `.304` `.305` | **源码中无定义**（`FEOS.exe` 为二进制） | — | — | ☆ |
| `.base` | `material.base` 仅为**注册表**，非数据格式定义 | — | — | ☆ |
| `.template` `.cst` `.mexport` `.snop` | **源码中无定义** | — | — | ☆ |
| `fort.10` | `doc/multi1d7.6/manual:208–277` | 二进制记录（非文本） | — | ★★★★ 文档 |

**统计：目标后缀 17 个；有权威定义 6 个（`.cn4` `.cnr` + 4 个 MATLAB 写出器族）；无定义 11 个。**

---

## 3. 逐后缀格式定义卡

### `.cn4` —— IONMIX CONRAD 格式（isw(21)≠0 分支）

#### 定义位置

`ionmix/ionmix/src/Ionmix/abjt_03.f:4662–4743`，位于 `SUBROUTINE OWTF`（起始于第 4510 行）。

**前置头写语句**（第 4662–4681 行）：

```fortran
4662:      if ( isw(21) .ne. 0) then
4663:
4664:c ...    write output for 'cn4'
4665:c ...    set up additional header records first
4666:c ...    write the numbver of temperature and density points.
4667:         write (header,923) ntemp, ndens
4668:c ...    write the atomic number of each element in this material
4669:         write (headr2,921) (izgas(l),l=1,ngases)
4670:c ...    write the fraction (by number of ions) of each element in this
4671:c ...    material
4672:         write (headr3,922) (fracsp(l),l=1,ngases)
4673:
4674:c ...    now, write data tables
4675:
4676:         write (123,980) header
4677:         write (123,980) headr2
4678:         write (123,980) headr3
4679:
4680:c ...    write the number of radiation energy groups
4681:         write (123,982) ngrups
```

**数据块序列**（第 4683–4740 行，逐条抄录，中文注释原样保留）：

```fortran
4683:c ...    write the temperature points (in ev)
4684:         write (123,991) (tplsma(it), it=1, ntemp)
4685:c ...    write the number density points (in cm^-3)
4686:         write (123,991) (densnn(id), id=1, ndens)
4687:c ...    write out the zbar at each temperature/density ponit (nele/nion)
4688:         write (123,991) ((densne(it,id)/densnn(id),it=1,ntemp),
4689:     &                     id=1, ndens)
4690:c ...    write d(zbar)/dT
4691:         write (123,991) ((dzdt(it,id), it=1,ntemp), id=1, ndens)
4692:c ...    write the ion pressure
4693:         write (123,991) ((densnn(id)*tplsma(it)*1.602E-19,
4694:     &                     it=1,ntemp), id=1, ndens)
4695:c ...    write the electron pressure
4696:         write (123,991) ((densne(it,id)*tplsma(it)*1.602E-19,
4697:     &                     it=1,ntemp), id=1, ndens)
4698:c ...    write the d(pion)/dT (in Joules/cm^3/eV)
4699:         write (123,991) ((densnn(id)*1.602E-19,
4700:     &                     it=1, ntemp), id=1, ndens)
4701:c ...    write the d(pele)/dT (in Joules/cm^3/eV)
4702:         write (123,991) (((densnn(id)*tplsma(it)*dzdt(it,id) +
4703:     &                      densne(it,id))*1.602E-19,
4704:     &                      it=1, ntemp), id=1, ndens)
4705:c ...    write out the ion specific internal energy (in Joules/gram)
4706:         write (123,991) ((enrgyion(it,id), it=1, ntemp), id=1, ndens)
4707:c ...    write out the electron specific internal energy (in Joules/gram)
4708:         write (123,991) (( enrgy(it,id) - enrgyion(it,id),
4709:     &                      it=1, ntemp), id=1, ndens)
4710:c ...    write out the ion specific heat (in Joules/gram/eV)
4711:         write (123,991) ((heatcpion(it,id), it=1, ntemp), id=1, ndens)
4712:c ...    write out the electron specific heat (in Joules/gram/eV)
4713:         write (123,991) ((heatcp(it,id) - heatcpion(it,id),
4714:     &                     it=1, ntemp), id=1, ndens)
4715:c ...    write out d(eion)/d(nion) (not sure)
4716:         condd = -6.242e18 * avgatw / avgdro
4717:         write (123,991)
4718:     &         ((dedden_ion(it,id)*condd*densnn(id)/tplsma(it)**2,
4719:     &           it=1, ntemp), id=1,ndens)
4720:c ...    write out d(eele)/d(nele) (not sure)
4721:         condd = -6.242e18 * avgatw / avgdro
4722:         write (123,991)
4723:     &         (((dedden(it,id)-dedden_ion(it,id))*
4724:     &            condd*densnn(id)/tplsma(it)**2,
4725:     &            it=1, ntemp), id=1,ndens)
4726:c ...    write out electron specific entropy
4727:c         write (123,991) ((0.0, it=1, ntemp), id=1, ndens)
4728:c ...    write out the energy group boundaries (in ev)
4729:         write (123,991) (engrup(ig), ig=1, ngrups+1)
4730:c ...    write the opacities
4731:         opacity_lim = 1.0
4732:c ...    write the Rosseland group opacities
4733:         write (123,991) (((orgp(it,id,ig)*opacity_lim, it=1, ntemp),
4734:     &                      id=1, ndens), ig=1, ngrups)
4735:c ...    write the Planck absorption opacities
4736:         write (123,991) (((opgpa(it,id,ig)*opacity_lim, it=1, ntemp),
4737:     &                      id=1, ndens), ig=1, ngrups)
4738:c ...    write the Planck emission opacities
4739:         write (123,991) (((opgpe(it,id,ig)*opacity_lim, it=1, ntemp),
4740:     &                      id=1, ndens), ig=1, ngrups)
```

#### 写出的数组与声明处

`SUBROUTINE OWTF` 参数表（第 4510–4513 行）与 `DIMENSION` 声明（第 4573–4582 行）：

```fortran
4573:      dimension enrgy(mxtemp,mxdens),heatcp(mxtemp,mxdens)
4574:      dimension enrgyion(mxtemp,mxdens),enrgyele(mxtemp,mxdens)
4575:      dimension dzdt(mxtemp,mxdens),densne(mxtemp,mxdens)
4576:      dimension dedden(mxtemp,mxdens),heatcpion(mxtemp,mxdens)
4577:      dimension dedden_ion(mxtemp,mxdens)
4578:      dimension opgpa(mxtemp,mxdens,mxgrps),opma(mxtemp,mxdens)
4579:      dimension opgpe(mxtemp,mxdens,mxgrps),opme(mxtemp,mxdens)
4580:      dimension orgp(mxtemp,mxdens,mxgrps),orm(mxtemp,mxdens)
4581:      dimension op2tp(mxtemp,mxdens,mxtemp)
4582:      dimension op2tr(mxtemp,mxdens,mxtemp)
```

尺寸上限（第 4540–4542 行）：

```fortran
4540:      parameter ( mxtemp = 100, mxdens = 100 )
4541:      parameter ( mxphot = 30000, mxgrps = 100 )
4542:      parameter ( mxgass = 10, mxatom = 100 )
```

关键点：**Fortran 内是 `(itemp, idens)` / `(it, id, ig)` 列主序**，但写出的**存储序**由
隐式 DO 的嵌套决定，见下。

#### 循环顺序（决定 t-major / rho-major）

源码写法 `((x(it,id), it=1,ntemp), id=1,ndens)`：

```
外层 id=1..ndens，内层 it=1..ntemp
→ 内存序：id 慢、it 快  ⇒  t 变化最快
→ numpy: flat.reshape(ndens, ntemp)，即 .T 得到 (ntemp, ndens)
```

源码写法 `(((x(it,id,ig), it=1,ntemp), id=1,ndens), ig=1,ngrups)`：

```
外层 ig、中层 id、内层 it
→ 内存序：ig 慢、id 中、it 快
→ numpy: flat.reshape(ngrups, ndens, ntemp)
```

#### 格式串（逐字段拆解）

```fortran
4749:  921 format (' atomic #s of gases: ',5i10)
4750:  922 format (' relative fractions: ',1p5e10.2)
4751:  923 format (2i10)
4752:  980 format (a80)
4753:  981 format (4e12.6,i12)
4754:  982 format (i12)
4755:  991 format (4e12.6)
```

| 格式号 | 串 | 用在哪 | 拆解 |
|---|---|---|---|
| `980` | `(a80)` | 头 1/2/3 行 | 单行 80 字符文本，含尾随空格 |
| `923` | `(2i10)` | 头 1 行内容 | `ntemp`(宽 10) + `ndens`(宽 10) |
| `921` | `(' atomic #s of gases: ',5i10)` | 头 2 行 | 20 字符字面串 + 最多 5 个宽 10 整数 |
| `922` | `(' relative fractions: ',1p5e10.2)` | 头 3 行 | 21 字符字面串 + 最多 5 个 `1p e10.2` |
| `982` | `(i12)` | 第 4 行 | `ngrups`，宽 12 整数 |
| `991` | `(4e12.6)` | **全部数据块** | 每行 4 个定宽 12 字符字段，无分隔符，`0.d+dd`（无 `E` 字母） |

**`4e12.6` 的关键陷阱**：字段宽 12、小数位 6 → 形如 `-1.234567+123`
（指数 3 位、无 `E`）。当指数 ≥ 100 或值为 `Inf`/`NaN` 时字段会溢出，产生 **"打包指数缺陷"**
——相邻两数粘连。解析必须按**定宽 12 切分**，不能按空白切分。

#### 表头行（逐字段）

```
line 1 : (a80)  header  ← 预置内容见第 4667 行 write(header,923)，即 "(2i10)" 展开
line 2 : (a80)  headr2  ← " atomic #s of gases: " + 5i10   [格式 921]
line 3 : (a80)  headr3  ← " relative fractions: " + 1p5e10.2 [格式 922]
line 4 : (i12)  ngrups  [格式 982]
```

⚠️ 注意源码顺序：第 4667–4672 行先把内容写进内部字符变量 `header`/`headr2`/`headr3`，
第 4676–4678 行再以 `(a80)` 把它们整行吐出。故**实际文件第 1 行是 `(2i10)` 的 20 字符**，
而**不是** `ntemp, ndens` 的浮点表示。

#### 完整 18 块序列（顺序 = 文件顺序）

| 块 | 表达式 | 个数 | 物理量 | 单位 |
|---|---|---|---|---|
| 1 | `tplsma(it)` | ntemp | 温度网格 | eV |
| 2 | `densnn(id)` | ndens | 核子数密度 | cm⁻³ |
| 3 | `densne/densnn` | nt·nd | 平均电离度 zbar | 无量纲 |
| 4 | `dzdt` | nt·nd | d(zbar)/dT | eV⁻¹ |
| 5 | `densnn·tplsma·1.602E-19` | nt·nd | 离子压强 | J/cm³ |
| 6 | `densne·tplsma·1.602E-19` | nt·nd | 电子压强 | J/cm³ |
| 7 | `densnn·1.602E-19` | nt·nd | d(p_ion)/dT | J/cm³/eV |
| 8 | `(densnn·tplsma·dzdt+densne)·1.602E-19` | nt·nd | d(p_ele)/dT | J/cm³/eV |
| 9 | `enrgyion` | nt·nd | 离子比内能 | J/g |
| 10 | `enrgy-enrgyion` | nt·nd | 电子比内能 | J/g |
| 11 | `heatcpion` | nt·nd | 离子比热 | J/g/eV |
| 12 | `heatcp-heatcpion` | nt·nd | 电子比热 | J/g/eV |
| 13 | `dedden_ion·condd·densnn/tplsma²` | nt·nd | d(e_ion)/d(n_ion) | J·cm³/g |
| 14 | `(dedden-dedden_ion)·condd·densnn/tplsma²` | nt·nd | d(e_ele)/d(n_ele) | J·cm³/g |
| 15 | `engrup(ig)` | ngrups+1 | 能群边界 | eV |
| 16 | `orgp·opacity_lim` | ng·nt·nd | **Rosseland** 群不透明度 | cm²/g |
| 17 | `opgpa·opacity_lim` | ng·nt·nd | **Planck 吸收**群不透明度 | cm²/g |
| 18 | `opgpe·opacity_lim` | ng·nt·nd | **Planck 发射**群不透明度 | cm²/g |

其中 `condd = -6.242e18 * avgatw / avgdro`（第 4716 / 4721 行），
`opacity_lim = 1.0`（第 4731 行，当前为占位恒等缩放）。

#### 读取方法（Python / numpy 伪代码）

```python
import re
import numpy as np

W = 12          # 4e12.6 字段宽
PER_LINE = 4

def parse_cn4(path):
    txt = open(path, "r", encoding="latin-1").read()
    lines = txt.splitlines()

    # ---- 头部（前 4 行）----
    l1 = lines[0]
    ntemp = int(l1[0:10]);  ndens = int(l1[10:20])          # 格式 923: 2i10
    # 头 2/3 行是 a80 文本（人类可读），含 izgas / fracsp
    # 第 4 行：ngrups，格式 982: i12
    ngrups = int(lines[3][0:12].strip())

    # ---- 数据区：从第 5 行起，全部为 4e12.6 ----
    body = "".join(lines[4:])

    def take(n):
        """按定宽 12 切分取出 n 个数（绝不能按空白切）"""
        nonlocal body
        out = []
        while len(out) < n:
            field = body[:W]
            body = body[W:]
            s = field.strip()
            if not s:
                continue
            # 4e12.6 无 'E'：形如 -1.234567+123 → 补 'E'
            s = re.sub(r"(?<=\d)([+-]\d{2,3})$", r"E\1", s)
            out.append(float(s))
        return np.array(out)

    n2 = ntemp * ndens
    n3 = ngrups * ntemp * ndens

    T     = take(ntemp)                       # 块 1  eV
    rho_n = take(ndens)                       # 块 2  cm^-3
    zbar  = take(n2).reshape(ndens, ntemp)    # 块 3
    dzdt  = take(n2).reshape(ndens, ntemp)    # 块 4
    pion  = take(n2).reshape(ndens, ntemp)    # 块 5   J/cm^3
    pele  = take(n2).reshape(ndens, ntemp)    # 块 6
    dpion = take(n2).reshape(ndens, ntemp)    # 块 7
    dpele = take(n2).reshape(ndens, ntemp)    # 块 8
    eion  = take(n2).reshape(ndens, ntemp)    # 块 9   J/g
    eele  = take(n2).reshape(ndens, ntemp)    # 块 10
    cion  = take(n2).reshape(ndens, ntemp)    # 块 11  J/g/eV
    cele  = take(n2).reshape(ndens, ntemp)    # 块 12
    deion = take(n2).reshape(ndens, ntemp)    # 块 13
    deele = take(n2).reshape(ndens, ntemp)    # 块 14
    egrup = take(ngrups + 1)                  # 块 15  eV
    kross = take(n3).reshape(ngrups, ndens, ntemp)   # 块 16  cm^2/g
    kpabs = take(n3).reshape(ngrups, ndens, ntemp)   # 块 17
    kpems = take(n3).reshape(ngrups, ndens, ntemp)   # 块 18

    return dict(T=T, rho_n=rho_n, ngrups=ngrups, egrup=egrup,
                zbar=zbar, dzdt=dzdt, eion=eion, eele=eele,
                kross=kross, kpabs=kpabs, kpems=kpems)
```

> 仓库内已有该逻辑的成熟实现：`eosop_pro/eosop_pro/parsers/cn4_io.py`
> （其第 104 行注明字段宽来自 `abjt_03.f:4755`，第 899 行"严格复刻 OWTF 的 write 序列"）。

---

### `.cnr` —— IONMIX late-1986 CONRAD 格式（isw(8)=1/12/13）

#### 定义位置

`ionmix/ionmix/src/Ionmix/abjt_03.f:4598–4621`，同样在 `SUBROUTINE OWTF`。

```fortran
4598:      if ( isw(8).eq.1 .or. isw(8).eq.12 .or. isw(8).eq.13 ) then
4599:
4600:c ...    write output in "original" (i.e., late 1986) CONRAD-acceptable
4601:c        format
4602:
4603:         write (8,980) header
4604:         write (8,981) dlgden,log10( densnn(1) ),dlgtmp,
4605:     &                 log10( tplsma(1) ),ngrups
4606:         write (8,991) ((densne(it,id)/densnn(id),it=1,ntemp),
4607:     &                  id=1,ndens)
4608:         write (8,991) ((enrgy(it,id),it=1,ntemp),id=1,ndens)
4609:         write (8,991) (((op2tr(itp,id,itr),itr=1,ntrad),
4610:     &                  itp=1,ntemp),id=1,ndens)
4611:         write (8,991) (((op2tp(itp,id,itr),itr=1,ntrad),
4612:     &                  itp=1,ntemp),id=1,ndens)
4613:         write (8,991) (engrup(ig),ig=1,ngrups+1)
4614:         write (8,991) (((orgp(it,id,ig),it=1,ntemp),id=1,ndens),
4615:     &                  ig=1,ngrups)
4616:         write (8,991) (((opgpe(it,id,ig),it=1,ntemp),id=1,ndens),
4617:     &                  ig=1,ngrups)
4618:
4619:      endif
```

#### 与 `.cn4` 的区别（务必注意）

| 项 | `.cn4`（isw(21)≠0） | `.cnr`（isw(8)=1/12/13） |
|---|---|---|
| 头部行数 | 4 行（2i10 / 921 / 922 / i12） | **2 行**（`a80` + `4e12.6,i12`） |
| 第 2 行格式 | — | `981 format (4e12.6,i12)`（第 4753 行） |
| 块数 | 18 | **7** |
| 是否含 EOS 二维场 | 是（块 3–14 共 12 个） | **否** —— 只有 zbar + 比内能 |
| 是否含 `op2tp/op2tr` | 否 | **是**（双温不透明度，ntrad 维） |

**`.cnr` 的两个头部字段含义**（第 4604–4605 行）：
`dlgden`（密度对数步长）、`log10(densnn(1))`（起始密度）、
`dlgtmp`（温度对数步长）、`log10(tplsma(1))`（起始温度）、`ngrups`。

#### `.cnr` 的 7 块序列

| 块 | 表达式 | 个数 | 物理量 |
|---|---|---|---|
| 1 | `densne/densnn` | nt·nd | zbar |
| 2 | `enrgy` | nt·nd | 比内能 J/g |
| 3 | `op2tr(itp,id,itr)` | nd·nt·ntrad | Rosseland 双温不透明度 |
| 4 | `op2tp(itp,id,itr)` | nd·nt·ntrad | Planck 双温不透明度 |
| 5 | `engrup` | ngrups+1 | 能群边界 eV |
| 6 | `orgp` | ng·nt·nd | Rosseland 群不透明度 |
| 7 | `opgpe` | ng·nt·nd | Planck 发射群不透明度 |

⚠️ **`ntrad` 不在头部写出** —— 只能由总计数守恒反解。
仓库内实现（`eosop_pro/eosop_pro/parsers/cnr_io.py`）正是这么做的，
并在不可整除时返回 `None`、标 `unknown`、**不猜**。

#### 读取伪代码

```python
def parse_cnr(path):
    lines = open(path, "r", encoding="latin-1").read().splitlines()
    # 行 1: a80 头（含 ntemp/ndens 的人类可读文本）
    # 行 2: 981 = 4e12.6 + i12  → 5 个字段
    l2 = lines[1]
    dlgden = float(fix_e(l2[0:12]))
    logrho0 = float(fix_e(l2[12:24]))
    dlgtmp = float(fix_e(l2[24:36]))
    logT0  = float(fix_e(l2[36:48]))
    ngrups = int(l2[48:60].strip())
    ntemp, ndens = parse_counts_from_header(lines[0])

    # 余下全为 4e12.6 定宽流，按块消费
    # ntrad 由 zbar 块之外的总数反解：
    #   total = nt*nd*2 + nd*nt*ntrad*2 + (ngrups+1) + ng*nt*nd*2
    ...
```

---

### MULTI 不透明度表（F2 族，`outputMULTIOpacity.m`）

#### 定义位置

`src/Multi1D++Portable20241128/matlab/outputMULTIOpacity.m:39–69`

```matlab
 39: fprintf(fout, '%15.7e%15.7e%15.7e%15.7e\r\n', 0,1, nr, nt);
 40: numbers_per_line = 4;
 41: number_of_data_in_line = 0;
 42: for i=1:nr
 43:     fprintf(fout, '%15.7e', log10(rho(i)));
 ...
 50: for i=1:nt
 51:     fprintf(fout, '%15.7e', log10(tp(i)));
 ...
 58: for i=1:nt
 59:     for j=1:nr
 60:         fprintf(fout, '%15.7e', log10(kappa((i-1)*nr + j)));
 ...
 69: fprintf(fout, '\r\n');
```

#### 格式定义

```
line 1 : id(≈0), 1, nr, nt        四个 %15.7e，行宽 60，CRLF
line 2 : log10(rho(1..nr))        %15.7e，4 个/行，不足则续行
line 3 : log10(tp(1..nt))         %15.7e，4 个/行
line 4+: log10(kappa)             %15.7e，**T-major**：
            for i=1:nt  (温度外)
              for j=1:nr (密度内)
                kappa((i-1)*nr + j)
```

- **输入单位转换**：`tp(i) = tp(...)*1000`（keV → eV，第 35 行）。
- **全部取 log10**（第 43/51/60 行）→ 文件中存的是对数。
- **不加表头**，纯数值。
- 每个子表自带头（id, 类型枚举, nr, nt）；多群时子表串联。

#### 读取伪代码

```python
import numpy as np
v = np.array([float(fix_e(s[i:i+15])) 
              for line in open(path, "rb").read().decode().splitlines()
              for i in range(0, len(line), 15) if line[i:i+15].strip()])
# v[0]=id, v[1]=type, v[2]=nr, v[3]=nt
nr, nt = int(v[2]), int(v[3])
rho = 10 ** v[4:4+nr]
Te  = 10 ** v[4+nr : 4+nr+nt]
kap = (10 ** v[4+nr+nt : 4+nr+nt+nr*nt]).reshape(nt, nr)   # T-major → (nt, nr)
```

> 交叉验证：`eosop_pro/eosop_pro/convert/writers_multi.py:75–79` 的 `fmt15()` 即
> `f"{v:15.8e}"`，其模块 docstring 第 5 行明确写"对照 `matlab/outputMULTIOpacity.m`
> —— F2 的列宽（`%15.7e`×4）"。

---

### Hyades EOS（F3 族，`outputHyadesEOS.m`）

#### 定义位置

`src/Multi1D++Portable20241128/matlab/outputHyadesEOS.m:48–97`

```matlab
 48: fout = fopen([fileName, '.hyades.dat'], 'w');
 49: fprintf(fout, 'Ta2O5 EOS Fit: ...\r\n');     ← 第 1 行自由注释
 50: id = 0;
 51: zbar = 186;
 52: abar = 441.890764;
 53: rho0 = 1.0;
 54: length_of_data_array = nr*nt*2 + 2 + nr + nt;
 55: fprintf(fout, '%15g%15.8e%15.8e%15.8e%15g\r\n', id, zbar, abar, rho0, length_of_data_array);
 56: fprintf(fout, '%15.8e%15.8e', nr, nt);
 ...
 60:     fprintf(fout, '%15.8e', rho(i));
 ...
 68:     fprintf(fout, '%15.8e', tp(i));
 ...
 77:         fprintf(fout, '%15.8e', p((i-1)*nr + j));
 ...
 88:         fprintf(fout, '%15.8e', e((i-1)*nr + j));
 ...
 97: fprintf(fout, '\r\n');
```

#### 格式定义

```
line 1 : 自由文本注释（a80 级）                                    CRLF
line 2 : id(%15g) zbar(%15.8e) abar(%15.8e) rho0(%15.8e) L(%15g)   CRLF
line 3+: nr, nt 然后 rho(1..nr) 然后 T(1..nt) 然后 P 然后 E
         全部 %15.8e，**5 个/行**，整块连排（不因块边界换行）
         首行已有 2 个值（nr, nt），计数器初值 = 2
```

- **长度公式**：`L = 2 + nr + nt + 2·nr·nt`（第 54 行）—— 与文件头声明的数组长度一致。
- **单位**：T 以 **keV** 写出（第 45 行 `tp(i) = tp(i)/1000.0; % in keV`）。
- **展平序**：`P[(i-1)*nr + j]`，`i=1..nt` 外、`j=1..nr` 内 → **T-major**。
- **`zbar`/`abar`/`rho0`**：材料参数（此例 Z=186、A=441.89、ρ₀=1.0）。

#### 读取伪代码

```python
v = np.array([float(fix_e(line[i:i+15]))
              for line in open(path,"rb").read().decode().splitlines()[1:]  # 跳过注释
              for i in range(0, len(line), 15) if line[i:i+15].strip()])
id_, zbar, abar, rho0, L = v[0], v[1], v[2], v[3], int(v[4])
nr, nt = int(v[5]), int(v[6])
o = 7
rho = v[o:o+nr];                o += nr
Te  = v[o:o+nt] * 1000.0;       o += nt      # keV → eV
P   = v[o:o+nr*nt].reshape(nt, nr);  o += nr*nt
E   = v[o:o+nr*nt].reshape(nt, nr);  o += nr*nt
assert o == len(v), f"块尾不齐: {o} != {len(v)}"
```

---

### 通用两列曲线（`output2file.m`）—— 覆盖 `.hug` / `.zeff` / `.planck` / `.ross` 等

#### 定义位置

`src/Multi1D++Portable20241128/matlab/output2file.m:1–8`（完整文件）：

```matlab
1: function output2file(x, y, file_name)
2: fid = fopen(file_name, 'w');
3: n = max(size(x,1), size(x,2));
4: for i=1:n
5:     fprintf(fid, '%13.7e\t%13.7e\r\n', x(i), y(i));
6: end
7: fclose(fid);
8: end
```

#### 格式定义

```
每一行：x(i) 用 %13.7e，然后一个 TAB，然后 y(i) 用 %13.7e，然后 CRLF
无表头，无注释，n = length(x)
```

这是 Hyades/SESAME 族里 `.hug`、`.zeff`、`.planck`、`.ross`、`.eps` 等
**两列曲线类文件最可能的通用写出模板**（但注意：**本脚本并未硬编码这些后缀**，
后缀名由调用方传入，故不能断言某具体后缀必由它写出）。

#### 读取伪代码

```python
import numpy as np
d = np.loadtxt(path, delimiter="\t")    # 每行恰 2 列
x, y = d[:, 0], d[:, 1]
```

---

### 时间序列多列（`exportData2File.m`）

#### 定义位置

`src/Multi1D++Portable20241128/matlab/exportData2File.m:13–20`

```matlab
13:     fprintf(fid,'#FileName: %s; Variable size:%dx%d\n',file_name,size1,size2);
14:     for i=1:size1
15:         fprintf(fid, '%12.8e', Time1D(i));
16:         for j=1:size2
17:             fprintf(fid, '\t%12.8e', var(i,j));
18:         end
19:         fprintf(fid,'\n');
20:     end
```

#### 格式定义

```
line 1 : "#FileName: <name>; Variable size:<nrow>x<ncol>\n"   ← 仅 LF
line 2+: Time(i) 用 %12.8e，随后每列 "\t" + %12.8e，行尾 \n
```

**注意换行是 LF（`\n`）**，与 `output2file.m` / `outputMULTIOpacity.m` 的 CRLF 不同。
文件头注释行明确给出矩阵形状，可作自校验。

#### 读取伪代码

```python
import re
txt = open(path, "r").read()
m = re.match(r"#FileName: .*; Variable size:(\d+)x(\d+)", txt)
nrow, ncol = int(m.group(1)), int(m.group(2))
data = np.array([[float(f) for f in re.findall(
    r"[+-]?\d+\.\d{8}[eE][+-]\d+", line)] for line in txt.splitlines()[1:]])
assert data.shape == (nrow, ncol)
Time, var = data[:, 0], data[:, 1:]
```

---

### `.coldopacity` —— 源码中无定义，但有一手数据样例

#### 查询结果

在**全部 Fortran 源码 / MATLAB 写出器 / 官方文档**中搜索关键词：

```
coldopacity, ColdOpacity, coldop, coldt, coldt
```

- `abjt_03.f`（唯一源码）：**0 处匹配**
- `matlab/*.m`：**0 处匹配**
- `doc/*`：**0 处匹配**

命中仅出现在：
- `matter++/material.base:23–26` —— 材料注册表关键字注释，**不是格式定义**：
  ```
  23: #          - ColdOpacity <module> <file>   Cold opacity
  24: #          * Temperature4ColdOpacity <real>  Temperature at which cold opacities are used
  26: #          * Density4ColdOpacity <real>  Density at which cold opacities are calculated. Not useful.
  ```
- `cases_ZhangLu/*.case.log:119,150,183` —— 运行时日志，值恒为 `[Undefined]`：
  ```
  119: ColdOpacity filename= [Undefined]
  ```

**结论：`.coldopacity` 的写出端不在本工作区。它由外部工具或旧版程序生成。**

#### 一手数据样例（最硬证据）

`src/Multi1D++Portable20241128/matter++/ColdOpacity/Al.coldopacity` 前 12 行：

```
1: Eph	miu
2: eV	cm2/g
3: 	
4: 	
5: 10	486606.52638
6: 10.1617	469396.24406
7: 10.3261	452791.00338
8: 10.4931	436776.37403
9: 10.6628	421327.98079
10: 10.8353	406424.13741
11: 11.0106	392047.78705
12: 11.1886	379445.69365
```

#### 由实测推出的格式（置信度 ★★，非源码）

```
line 1 : 列名行，TAB 分隔：      "Eph"        TAB  "miu"
line 2 : 单位行，TAB 分隔：      "eV"         TAB  "cm2/g"
line 3 : 空行（仅一个制表符）
line 4 : 空行（仅一个制表符）
line 5+: 数据行，TAB 分隔两列：  Eph(TAB)miu
```

| 列 | 名称 | 单位 | 含义 |
|---|---|---|---|
| 1 | `Eph` | eV | 光子能量 |
| 2 | `miu` | cm²/g | 冷（未电离）质量吸收系数 |

- **无序言、无维度行、无尾注**。
- **列分隔符为 TAB**，非定宽。
- **表头是自描述的**（列名行 + 单位行）——这是该族最显著特征。
- 数值为十进制小数（**不是**科学计数），列数恒为 2。
- 现有工具链的解析器：`eosop_pro/eosop_pro/parsers/coldopacity.py`，
  其测试 `eosop_pro/test/parsers/test_coldopacity.py:3` 亦注明
  "**两行自描述表头**（列名 / 单位，制表符分隔）"，与本次读取一致。

#### 读取方法

```python
import numpy as np

def parse_coldopacity(path):
    with open(path, "r", encoding="latin-1") as fh:
        lines = fh.read().splitlines()
    # line 1: 列名（Eph, miu）；line 2: 单位（eV, cm2/g）
    names  = lines[0].split("\t")
    units  = lines[1].split("\t")
    # 跳过空行（可能含单个制表符）与可能的注释
    rows = [ln for ln in lines[2:]
            if ln.strip() and not ln.lstrip().startswith("#")]
    data = np.array([[float(c) for c in ln.split("\t")] for ln in rows])
    return {"names": names, "units": units,
            "Eph_eV": data[:, 0], "mu_cm2_per_g": data[:, 1]}
```

#### 尚存的未知点（不得猜测）

1. **写出端程序名与版本未知**——本工作区无任何可执行文件声明会产出该后缀。
2. **表头是否可缺省**（即是否存在无表头变体）——现有 67 个样例全部带双行表头，
   但样本不足以断言"必然带表头"。
3. **空行数量是否恒定**（此处为 2 行）——未跨全部 67 个文件统计。
4. 若某文件列数 > 2，第二列之后的物理量无定义依据。

---

### `fort.10` —— 原始 MULTI-7.6 二进制记录格式

#### 定义位置

`src/Multi1D++Portable20241128/doc/multi1d7.6/manual:206–277`

```
208: The code writes data into binary file "fort.10". The format of file is divided
209: in "records", each record is formed by several bytes ("data"), preceded and
210: followed by an integer indicating its number. The structure is:
211:
212: record    data
213:
214: 1         integer(4 bytes) indicating the number of words in records 2 and 3
215: 2         each word is a 8 character string with the name of one variable,
216:           for arrays the name appears several times
217: 3         each word is a double precission number with the value of the
218:           variable named above (static values)
219: 4         integer(4 bytes) indicating the number of words in next records
220: 5         each word is a 8 character string with the name of one variable,
221:           for arrays the name appears several times
222: 6         each word is a double precission number with the value of the
223:           variable named above (at some time)
224: more      like 6 but for a different value of time
```

#### 要点

- 这是**Fortran 无格式（unformatted）顺序文件**的经典「记录长度前后缀」结构。
  `record 1` 即前导长度、`record 4` 是下一段的长度 —— 严格说前者是段前缀、
  行 214/219 描述的是 **4 字节整数长度前缀**。
- 名字数组与数值数组**一一对应**（数组变量名重复出现 N 次），故可**自描述解码**。
- 长度单位：8 字符名 + 8 字节 double。
- 变量清单在第 226–277 行（`CMC` `NC` `CMI` `NI` `FREC` `FREI` 为静态；
  `TIME` `ISTEP` `R` `T` `P` `ZI` `XC` `D` `DENE` `S+` `S-` `TR` `I-Left` `I-Right` 等为时序）。

#### 读取伪代码（自描述解码）

```python
import struct
import numpy as np

def read_fort10(path):
    buf = open(path, "rb").read()
    pos = 0
    def rec_len():
        nonlocal pos
        n = struct.unpack_from("<i", buf, pos)[0]; pos += 4
        return n

    n1 = rec_len()                            # record 1（段前缀）
    names = [buf[pos + 8*i : pos + 8*(i+1)].decode("latin-1").strip()
             for i in range(n1)]; pos += 8 * n1
    vals  = np.frombuffer(buf, dtype="<f8", count=n1, offset=pos); pos += 8 * n1
    rec_len()                                 # 段后缀
    static = dict(zip(names, vals))

    frames = []
    while pos < len(buf):
        n = rec_len()
        nm = [buf[pos + 8*i : pos + 8*(i+1)].decode("latin-1").strip()
              for i in range(n)]; pos += 8 * n
        vv = np.frombuffer(buf, dtype="<f8", count=n, offset=pos); pos += 8 * n
        rec_len()
        frames.append(dict(zip(nm, vv)))
    return static, frames
```

⚠️ 该文档描述的是**原始 multi1d-7.6**；`Multi1D++.exe` 的实际输出为 HDF5
（见 `Untitled.case` 中 `Output.IsEmissionSpectrum` 等关键字），**二者不可混用**。

---

## 4. 源码中未找到的后缀

以下后缀在**本工作区全部可读源码 / 官方写出脚本 / 官方文档**中**均无格式定义**。
表中列出**实际搜索过的关键词**（用 ripgrep 全树搜索，大小写不敏感）。

| 后缀 | 搜索关键词 | 命中情况 |
|---|---|---|
| `.dem` | `\.dem`, `dem file`, `load '.*\.dem` | 仅 `wgnuplot.mnu:13` 的菜单字符串 `load '[OPEN]load[EOS]*.dem[EOS]'{ENTER}`，**与文件格式无关**；另有 `doc/gnuplot_files_for_plot/*.dem` 是 **gnuplot 脚本**，非数据文件 |
| `.coldopacity` | `coldopacity`, `ColdOpacity`, `coldop`, `coldt` | 仅 `material.base` 注册表关键字与 `.case.log` 运行时打印（恒 `[Undefined]`）。**无写出语句** |
| `.hug` | `hug`, `hugoniot`, `\.hug` | 源码/脚本 **0 命中**；仅有数据文件 `hyades/sesame/eos_41.hug` 等 |
| `.zeff` | `zeff`, `ZEFF`, `ZeffSquared` | 源码 **0 命中**；`material.base` 仅声明 `ZEFF` 关键字，`Changes.log:710,713,804` 讨论其**单位**（Te 由 eV 改 keV），但**无格式定义** |
| `.planck` / `.ross` | `planck`, `ross`, `PLANCK`, `ROSS`, `ROSSELAND`, `op03p`, `op03r` | 源码 **0 命中**；`material.base:20–21` 仅声明 `PLANCK`/`ROSSELAND` 关键字指向"tabulated ... (Multi-format)"——**即复用上表 F2 格式**，但无独立定义 |
| `.eps` | `eps`, `EPS`, `emiss`, `Emissivity` | 源码 **0 命中**；`Changes.log:229` 提及"有 EPS 数据"，`material.base:22` 有 `EMS` 关键字。**无格式定义** |
| `.nofree` / `.avsqfree` | `nofree`, `NoFree`, `avsqfree`, `AvSq`, `avsq` | **0 命中**（任何文件） |
| `.mexport` | `mexport`, `mexp` | 仅 `mat_*/**.PAR.log:6` 的**数据库清单行** `F.mexport  SESAME mexport format`，**无写出语句** |
| `.cst` | `cst`, `\.cst` | **0 命中** |
| `.feos` | `feos`, `\.feos` | 仅 `FEOS.exe` / `FEOS_Material-DB.dat` / `doc/FEOS/*.pdf` 存在；**无源码** |
| `.301` / `.304` / `.305` | `301`, `304`, `305`, `feos\.301` | 仅数据文件与 `DatabaseIndex.xml` 注册表项；**无源码**。其内部结构见 `doc/FEOS/MPQeos-JWGU-Documentation.pdf`（PDF，非源码） |
| `.base` | `base`, `material.base` | `material.base` **本身是注册表**，不是数据格式；其格式即 `keyword module file` 行式文本（第 20–29 行注释区给出关键字表），**无写出的 FORMAT 语句** |
| `.cn4`（另一分支） | `isw(8).eq.3 or isw(8).eq.13` | 见下文「多分支说明」 |
| `.snop` | `snop`, `SNOP` | `Snop++.exe` / `snop.exe` 为二进制；`doc/SNOP.MANUAL:13` 仅说明 `SNOP.TAB` "Contains the tables in **MULTI-format**" → **复用 F2 格式**，但**SNOP 自己的输入 `SNOP.INPUT` 的 namelist 已给出**（见下） |
| `.template` | `template`, `TEMPLATE` | 仅 `templates/` 目录（GUI 模板资源）与 `matlab/*.solution.dat` 注释；**无格式定义** |

### 4.1 多分支说明（纪律 3 要求）

`SUBROUTINE OWTF` 中按 `isw(8)` / `isw(21)` 分流，**全部分支**如下：

| 行号 | 条件 | 输出单元 | 说明 |
|---|---|---|---|
| 4598 | `isw(8)=1, 12, 13` | **8** | "original"（late 1986）CONRAD 格式 → **`.cnr`** |
| 4622 | `isw(8)=2, 12` | — | **空分支！** 源码中 `if ... then` 与 `endif` 之间无任何语句 |
| 4627 | `isw(8)=3, 13` | **10** | "new"（post-Sept 1987）CONRAD 格式 |
| 4662 | `isw(21) ≠ 0` | **123** | → **`.cn4`**（18 块完整 EOS） |

**`isw(8)=3/13` 分支全文**（第 4627–4659 行，此前未列出，补充）：

```fortran
4627:      if ( isw(8).eq.3 .or. isw(8).eq.13 ) then
4628:
4629:c ...    write output in "new" (i.e., post-September 1987)
4630:c        CONRAD-acceptable format
4631:
4632:c ...    set up additional header records first
4633:         write (header,923) ntemp, ndens
4634:         write (headr2,921) (izgas(l),l=1,ngases)
4635:         write (headr3,922) (fracsp(l),l=1,ngases)
4636:
4637:c ...    now, write data tables
4638:
4639:         write (10,980) header
4640:         write (10,980) headr2
4641:         write (10,980) headr3
4642:         write (10,981) dlgden,log10( densnn(1) ),dlgtmp,
4643:     &                  log10( tplsma(1) ),ngrups
4644:         write (10,991) ((densne(it,id)/densnn(id),it=1,ntemp),
4645:     &                  id=1,ndens)
4646:         write (10,991) ((enrgy(it,id),it=1,ntemp),id=1,ndens)
4647:         write (10,991) ((heatcp(it,id),it=1,ntemp),id=1,ndens)
4648:         condd = -6.242e18 * avgatw / avgdro
4649:         write (10,991) ((dedden(it,id)*condd*densnn(id)/tplsma(it)**2,
4650:     &                  it=1,ntemp),id=1,ndens)
4651:         write (10,991) (engrup(ig),ig=1,ngrups+1)
4652:         write (10,991) (((orgp(it,id,ig),it=1,ntemp),id=1,ndens),
4653:     &                  ig=1,ngrups)
4654:         write (10,991) (((opgpa(it,id,ig),it=1,ntemp),id=1,ndens),
4655:     &                  ig=1,ngrups)
4656:         write (10,991) (((opgpe(it,id,ig),it=1,ntemp),id=1,ndens),
4657:     &                  ig=1,ngrups)
4658:
4659:      endif
```

**该分支 = `.cn4` 的「前 10 块裁剪版」**：头部与 `.cn4` 完全相同
（`980`×3 + `981` + `i12`），数据块缩减为 9 个：
zbar、enrgy、heatcp、d(e)/d(ρ)、engrup、orgp、opgpa、opgpe。

**新增证据：`isw(8)=2/12` 为空分支**（第 4622–4625 行）——
该路径**不产生任何输出**，是源码中的历史占位。若遇到声称由该开关产出的文件，
**不可能来自本版本 IONMIX**。

### 4.2 `SUBROUTINE OWT1` 的调试/绘图输出（非 `.cn4`/`.cnr`）

`OWT1`（第 4343 行）把每个 (T, ρ) 点的中间结果写到 **unit 911**（`ionmxbug`），
以及 unit 12/14/15/16/17/18 的绘图文件。**这些是调试通道，非目标后缀。**

关键格式（第 4498–4505 行）：

```fortran
4498:  905 format (t2,i3,t6,1p5e14.3)
4502:  911 format (t2,1p5e14.4)
```

其中 `911` 被 unit 12/14/15/16/17/18 复用为**通用 5 列数值行**
（第 4431/4435/4439/4449/4453/4463 行）。**注意每行恒为 5 个数**，
即使语义上只用 3 个（如第 4431 行 `tp,culrat,oppma,oppme,oprm` 是 5 个，
而第 4439 行 `tp,culrat,zbar,enrgy,pres` 也是 5 个）——**这是刻意的定宽设计**。

### 4.3 SNOP 输入格式（来自官方手册，非源码）

`doc/SNOP.MANUAL` 明确给出 SNOP 的**输入** namelist（第 19–132 行：
`NT` `NR` `NG` `NP` `Z` `RHO1` `RHO2` `T1` `T2` `X1` `X2` `IGROUP` `F0` `F1`
`FG(1..NG+1)` `EQ` `IDEG` `LINEPRO` `NBFSMEAR` `DREK` `XGRIEM` `AV` `FACT`
`NSIGMA` `NPLA` `NROSS` `NEPS` `NZ`；示例见第 136–167 行）。

**但 SNOP 的输出**仅有一句说明（第 13 行）：

```
13: SNOP.TAB:    Contains the tables in MULTI-format.
```

→ **SNOP 的输出表复用上面那张 MULTI 不透明度格式（`%15.7e`×4/行）**，
手册未另行定义格式。第 106–132 行的 `NPLA`/`NROSS`/`NEPS`/`NZ`
是 SESAME 表号（`xxxx3nnn` / `xxxx4nnn` / `xxxx5nnn` / `xxxx2nnn`），
不是文件格式。

---

## 5. 附：一条可复用的判定经验

由本工作区的结构可提炼出一条**通用判据**，建议写入格式说明的"置信度"一节：

1. **Fortran 源码中的 `WRITE(lun, fmt)` 语句是最高权威**——它同时固定
   字段宽度、精度、循环序、块序。
2. **程序内附的 MATLAB/Python 写出脚本是第二权威**——尤其当它与某份数据
   逐字节吻合时（如 `outputMULTIOpacity.m` 的 `%15.7e`×4 ↔ MULTI 不透明度表）。
3. **官方手册中的记录结构表是第三权威**（如 `multi1d7.6/manual` 的 fort.10）。
4. **只有数据样例、无写出端**时，只能给出"实测格式"，必须显式降级置信度
   并列出未知点（`.coldopacity` 即此类）。
5. **当某后缀只出现在"注册表/清单/日志"中时，不构成格式定义**
   （`.mexport`、`.zeff`、`.planck`、`.ross`、`.eps` 皆属此类）。

---

*（本文件仅记录证据与由证据直接得出的结论；凡无源码支撑处均已显式标注。）*
