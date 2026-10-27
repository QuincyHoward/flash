# -*- coding: utf-8 -*-
"""p13: ① 更正"第 2 字段恒为 6.0"（实为 7 种类别码）
         ② 新增 §15.12.8「第四问集：FEOS 源码裁定」（TRef=eV、.feos 10×15、.cst 四列、英文 .cst 不存在）
         ③ 补 .301 头第 2 字段 = 密度 g/cm³
         ④ 关闭附录 E 的两条缺口（TRef 单位 / 英文 .cst）
   宽松模式。"""
import os

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
DOC = os.path.join(ROOT, 'src', 'multi_docs', 'MultiEOSOP格式说明.md')
txt = open(DOC, encoding='utf-8').read()
orig = txt
miss, hit = [], []


def rep(old, new, tag, count=1):
    global txt
    n = txt.count(old)
    if n != count:
        miss.append('%s (found %d want %d) %r' % (tag, n, count, old[:80]))
        return
    txt = txt.replace(old, new, count)
    hit.append(tag)


# ═══ ① §14.5.3 表格行 + 段落 ═══
rep('| **数值**（实测恒为 `6.0`，见下） | **ZEFF 式**（有效电荷数，无频率维度） | 无 | `1+D` |',
    '| **数值**（**类别码**，共 7 种取值，见下） | **ZEFF 式 / LEDCOP 式**（无频率维度） | 无 | `1+D` |',
    'A1: §14.5.3 表行')

rep("""**`ZEFF` 式表头的第 2 字段是常量 `6.0`，不是 Z。** 本轮实测 **全部 164 个 ZEFF 式文件的该字段
都是 `0.60000000E+01`**（覆盖 Ce、Al、C、Be、Au、Ti、He、Ta、W、U、Thermos 全族）——
对 Al（Z=13）、Ce（Z=58）、D（Z=1）取值完全相同，故**它绝不可能是原子序数**。
第一版把 `Ce.ZEFF` 的该字段读作"Z=6.0，与铈矛盾"，属**字段语义误判**，本轮更正。""",
    """**数值型表头的第 2 字段是「类别码」，不是常量、更不是 Z。** 第三轮对 404 个归属文件做了
**闭合条件下的全量取值统计**，该字段只有 **7 种取值**：

| 取值 | 文件数 | 对应类别 | 实例 |
|---|---:|---|---|
| `6.00000000E+00` | **115** | ZEFF 系（有效电荷数） | `mat_Al-1.0/Al_Z67.dat`、`mat_Au-1.0/Au100ZEFF` |
| `1.0000000e+000`（另一写法 `1.0000000E+000`） | 18 + 2 | LEDCOP 拆分件 / `_MULTI` | `ATOMIC/Al.AvSqFree`、`ATOMIC/Al.NoFree` |
| `0.1234567E+000` | 14 | LEDCOP 哨兵写入第 2 字段 | `mat_Au/Au_Rosseland_2003POPHammerRosen` |
| `7.00000000e+00`（另一写法 `0.70000000E+01`） | 3 + 5 | **Planck 系** | `mat_Be-1.0/BE_PLANCKx03`、`mat_Al-1.0/1041_PLANCK` |
| `4.00000000e+00`（另一写法 `0.40000000E+01`） | 7 | **Rosseland 系** | `mat_Al-1.0/1041_ROSS`、`AL_SIMPLE_ROSSELAND` |

**判据链（可复现）**：同一材料的成对文件给出**一致而非 Z 的**映射 ——
`1041_PLANCK` → `7.0`、`1041_ROSS` → `4.0`（成对、同名、只差 Planck/Rosseland）；
`BE_PLANCKx03` → `7.0`；`Al_Z67.dat` / `Au100ZEFF` → `6.0`（均为 ZEFF）；
`*.AvSqFree` / `*.NoFree` → `1.0`（均为 LEDCOP 拆分件）。
若该字段是原子序数，则 Al（Z=13）、Ce（Z=58）、D（Z=1）、Be（Z=4）**不可能取同一值**。

> **⚠ 本轮的第二处自我更正。** 上一轮曾断言"该字段**恒为** `6.0`，覆盖 Ce/Al/C/Be/Au/Ti/He/Ta/W/U 全族"。
> 该断言**错误**：它对**闭合集合内的 7 种取值**只看到了最常见的一种（115/164）。
> 根因是以"17 个 ZEFF 样本"外推为全族常量，**未做全量取值统计**。
> 教训（已写入 §15.13.1 规约 **R20**）：*凡声称某字段为"常量"，必须给出该字段在全体样本上的
> 取值直方图；只凭同类样本的一致不能推出常量。*

**字段语义仍未完全定**：`6.0/7.0/4.0/1.0` 与类别一一对应这一点是实测事实，但
**`6` 为何对应 ZEFF、`7` 为何对应 Planck、`4` 为何对应 Rosseland** 的**编码规则无本地文档**
（`[S-UNK]`）。已知的旁证只有一个：`PLANCKx03` 的 `x03 = ×0.3` 缩放规则见 §14.5.10，
与本字段无关。**不得据本字段反推物理量**，只能用作"类别提示"。""",
    'A2: §14.5.3 段落重写')

# ═══ ② §15.12.6 (二) 表行 2 ═══
rep('| 2 | ZEFF 式表头第 2 字段（`6.0`） | 读作 **原子序数 Z**，并称"Ce 的 Z=6.0 与铈矛盾" | **是常量 `6.0`**：全部 164 个 ZEFF 式文件该字段都是 `0.60000000E+01`，Al/Ce/D 取值相同 ⇒ 绝非 Z |',
    '| 2 | 数值型表头第 2 字段 | 读作 **原子序数 Z**，并称"Ce 的 Z=6.0 与铈矛盾" | **既非 Z、亦非常量**，而是**类别码**（闭合集合内共 7 种取值：`6.0`→ZEFF 115 个、`7.0`→Planck 8 个、`4.0`→Rosseland 7 个、`1.0`/`0.1234567E+000`→LEDCOP 34 个）。**上一轮"恒为 6.0"的说法本轮更正** |',
    'B1: §15.12.6 表行 2')

# ═══ ③ §10.2 补 .301 头第 2 字段 = 密度 ═══
OLD_10_2 = '### 10.2 `.301` / `.304` / `.305`：MPQeos 4 字段定宽（宽度 60/64 双实物）'
NEW_10_2 = OLD_10_2 + """

> **✅ 第三轮新增：头部第 2 字段 = 密度（g/cm³）。** 第三轮在做全树表头普查时，把
> `.301/.304/.305` 的头部一并统计，发现**第 2 字段就是该材料的固态密度**，
> 并可用**独立来源（元素密度表）交叉验证** `[S-L4]`：
>
> | 材料 | `.301` 头第 2 字段 | 已知密度 (g/cm³) | 吻合 |
> |---|---:|---:|---|
> | Al（`mat_Al-1.0/FEOS/Al.feos.301`） | 2.7 | 2.699 | ✓ |
> | Au（`mat_Au-1.0/AU_eos` 同格式） | 19.300003 | 19.3 | ✓ |
> | W、Mo、Co、Cr、Bi、Pd、Ba、Dy、Sm、Sc、P、O、N、K、Na、Ne、F、Cl | 19.3 / 10.22 / 8.9 / 7.15 / 9.78 / 12.023 / 3.51 / 8.54 / 7.52 / 2.985 / 1.823 / 1.26205 / 0.857226 / 0.862 / 0.53149 / 1.21798e-3 / 1.7e-3 / 3.2e-3 | 各自固态（或液/气态参考）密度 | ✓ |
> | Ce（`mat_Ce/Cerium.301`） | 6.77 | 6.77 | ✓ |
>
> 这条更正了第二版的空白（第二版只说"Id / Density / NR / NT"而未给密度列的验证）。
> **同一字段在其他族里含义不同**（见 §14.5.3 的"类别码"），**不可跨族套用**。"""
rep(OLD_10_2, NEW_10_2, 'C1: §10.2 补密度列')

# ═══ ④ 新增 §15.12.8 FEOS 源码裁定 ═══
ANCHOR = '### 15.13 本章的解析器规约（可直接落地的清单）'
NEW = """#### 15.12.8 【补录】第四问集：FEOS 源码级裁定（与 §10 章配套）

第三轮为关闭 §10 章与 §15.12.2 中**最后几条 FEOS 相关悬案**，对本地 FEOS 官方源码包
（`vendor/FEOS_src/FEOS/Code/`，18 `.C` + 18 `.H`）做了穷举式核验。**四问全部定案**，
完整记录见 `src/multi_src/04_probe/04_feos/feos_src_adjudication.md`。摘要：

| # | 悬案 | 裁定 | 依据（`文件:行号`） | 溯源级 |
|---|---|---|---|---|
| 1 | **`.feos` 头 `TRef` 单位（eV vs Hartree）** | **eV**（差 27.2114 倍的 Hartree 说**作废**） | `FE-01_TABTOOLS.C:204` 注释 `// FEOS units are cgs (+ eV for temperature)`；旁证：全包把内部 T（eV）乘 `eV2Kelvin` 才输出 K（`:896` 等） | `[S-SRC]` |
| 2 | `.feos` 行 0/行 1 字段序 | **确认**为 `FileVersion, NR+1, NT+1, Nel+1, Tcalclimit` / `Rhocalclimit, RhoRef, TRef, BulkModulusRef, SESAMEnumber` | `FE-01_TABTOOLS.C:206,222-223` | `[S-SRC]` |
| 3 | **`.feos` 行宽（"4×15 vs 10×15" 之争）** | **10×15 = 150**；`Readme.txt` 的"4×15"确属错误 | `FE-00_DEFINITS.H:28` `#define SF_TRENN ""` + `FE-01_TABTOOLS.C:233,237,241,247,251,258` 的 `if(++count%10) … else "\\n"` | `[S-SRC]` |
| 4 | `.cst`（Rostock）四列语义 | **确认**：数密度(1/cm³) / 质量密度(g/cm³) / 压强(MBar) / 电荷态总和；格式串 `"%e          %e          %e    %e\\n"` | `FE-01_TABTOOLS.C:896-903` | `[S-SRC]` |
| 5 | **英文 `.cst` 模板（`Particle density` / `load state`）** | **FEOS 16.7 源码包中不存在** ⇒ 由**外部工具或手工**产生（排除范围已收窄） | 全 `vendor/` 74 个文件对 `Particle density\\|load state\\|Isotherm T` **零命中**；德文模板在 `:897` 命中 | `[S-UNK]` |
| 6 | 不透明度表 T 轴缩放 | **FEOS 不产出该表**：写出器穷举共 10 个（`write_criticaldata/FEOS_format/mexport/301/304/305/txt/Rostock`、`write_isobaricdata`、`write_TF_TABLE`），**无 Planck/Rosseland 多群表写出器** ⇒ 权威在 `SNOP.MANUAL:38-41`，即 **keV 输入 / eV 表内 / ×1000**，无 10× 因子 | 穷举 `^void write_` + §14.5.5 | `[S-SRC]`+`[S-L1]` |

**方法论价值**：本轮把"源码注释 + 打印语句里的单位字样"作为**单位裁定的首选证据** ——
`FE-03_MAIN.C:136` 直接写 `printf(" ... limit %.2e eV!")`、`:141` 写 `g/cm^3`。
这比任何数值反推都硬：**源码在打印时自己标了单位**。凡遇单位悬案，应先穷举
`printf` / `fprintf` 里带单位字样的位置，再考虑推导。

**注意**：本次核验**全部在本地完成，不需要联网**。原代理 `rev-feos-src2` 因网络故障
（`getaddrinfo ENOTFOUND`）中断，其任务由主理人直接接手完成（见该文件"与原代理的关系"节）。

---

"""
rep(ANCHOR, NEW + ANCHOR, 'D1: 新增 §15.12.8')

# ═══ ⑤ 关闭附录 E 两条缺口 ═══
rep('| 13 | **`.feos` 头 `TRef` 单位（eV vs Hartree）** | 两种读法差 27.21×；源码 `FE-01_TABTOOLS.C:222-224` 未逐字比读 | 悬置；使用前须带 "±27× 量级" 警告 |',
    '| 13 | ~~**`.feos` 头 `TRef` 单位**~~ | **已关闭**：源码 `FE-01_TABTOOLS.C:204` 注释 `FEOS units are cgs (+ eV for temperature)` ⇒ **eV**，Hartree 说作废 | §15.12.8 |',
    'E1: 附录 E #13')

rep('| 12 | **英文 `.cst` 生成工具** | `mat_He/Untitled.CST` 的英文表头格式串不在随包源码内 | `[S-UNK]`；德文变体已追至 `FE-01_TABTOOLS.C:883-907` |',
    '| 12 | **英文 `.cst` 生成工具** | **已排除 FEOS 16.7**：全 `vendor/` 对 `Particle density`/`load state` 零命中；德文模板在 `:897` 命中 | 仍 `[S-UNK]`；建议查 FEOS ≤2012 版或第三方转换脚本 |',
    'E2: 附录 E #12')

rep('| 3 | **`.feos` 的"4×15"与"10×15"该如何调和** | `[S-L3] matter++/Readme.txt` 说 4 个 15 字符，实测 `Al.feos` 为 10 个 15 字符；可能是该 Readme 描述的是',
    '| 3 | **`.feos` 的"4×15"与"10×15"该如何调和** | `[S-SRC]` **已定案**：`SF_TRENN=""` + `if(++count%10)` ⇒ **10×15 = 150**，`Readme.txt` 的"4×15"是错的；`[S-L3] matter++/Readme.txt` 说 4 个 15 字符，实测 `Al.feos` 为 10 个 15 字符；',
    'E3: §15.12.2 #3')

open(DOC, 'w', encoding='utf-8', newline='\n').write(txt)
print('PATCH13 done: %+d chars (%d -> %d)' % (len(txt) - len(orig), len(orig), len(txt)))
print('\n--- HIT (%d) ---' % len(hit))
for h in hit:
    print('   ', h)
print('\n--- MISS (%d) ---' % len(miss))
for m in miss:
    print('   ', m)
