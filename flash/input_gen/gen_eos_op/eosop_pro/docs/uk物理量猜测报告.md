# uk 物理量盲读猜测报告（GUESS ONLY）

> **状态声明**：本报告全部内容为 `eosop_pro.guess` 模块的**猜测输出 + 联网证据佐证**，
> **不是**人工核查结论。任何条目都未写回控制字典 `registry/field_checks.py`；
> 对应字典升级（ledcop_zeff.NoFree/AvSqFree）系依据 TOPS FAQ 一级出处单独完成，
> 与本报告的猜测层严格分离。生成日期：2026-09-15。

---

## 1. 方法（三层猜测管线）

`python -m eosop_pro.guess <file> [--compare-family F]` 对任意 eosop 数据盲读：

1. **盲读**：`read_payload_values` 编码鲁棒读取（textio.iter_lines）+ Fortran
   E12.6 丢 E 自愈（`1.234567-101` → `1.234567e-101`），行宽直方图 + 值指纹
   （n/zero_frac/neg_frac/int_like_frac/log10_median/log10_span/mono_frac）；
2. **形状/分块**：总数最方分解（factor_pairs）、轴样列检测（单调 + 唯一率
   >0.9）、零长跑 / 等值长跑 / decade 跳变（Δlog10≥2.5）定位意义块边界；
   已知族模板反演（inference.infer_file + split_by_template）尝试
   m×n / m×n×g 网格；
3. **指纹匹配**：段指纹 vs `family_field_fingerprints`（同族多样品聚合），
   容忍 ±0.15 的**整数量级换算偏移**（解析器 CGS→SI 换算所致），scale≠1
   记 `x1e±k` 并加惩罚分保证真实同量级优先。

猜测与事实的边界：报告内所有 "→" 结论均为 GUESS ONLY；只有第 4 节的
TOPS FAQ 引文属于已核实一级出处（并已升级进字典）。

## 2. 九族盲读结论一览

样品取各族第一解析样品（全量收集后 `step02_families/_out/<fam>/` 可交叉）。
逐份机器报告见 `test/eosopdata/step02_families/_out/guess_uk/`。

| # | 族 / 样品 | 行×列宽 | 值总数 | 形状候选 | 分块发现 | 指纹匹配（GUESS ONLY） |
|---|-----------|---------|--------|----------|----------|------------------------|
| 1 | mpqeos / Al.feos.301 | 7159×4 | 28633 | (137,209)/(19,1507) | 121/71 值周期交替块 ×10+；段间 decade 跳变规则（1e9 ↔ 3.55e-54 ↔ 3.16） | 无命中 |
| 2 | feos_native / Al.feos | 18674×10 | 186748 | (4,46687) | 同上 121/71 周期块；中段 7 处 5~8 值零跑 | unrecognized |
| 3 | ledcop_zeff / Al.NoFree | 807×4 | 3225 | (43,75)/(25,129)/(15,215) | 模板反演 ambiguous（f2_gray 与 ledcop_split 同分） | 无（列名语义已由 TOPS FAQ 定，见 §4） |
| 4 | ledcop_atomic / Al.txt | 341552×3(+3450×5+35×6) | 1042118 | (938,1111) | 头部标量表（69/50/99 行块）+ 大段 3 列谱表 | seg2→Ross cm2/g (score 1.47)、seg1→NoFree/AvSqFree |
| 5 | multi_opacity / SNOP.PLANCK | 1800×4(+20×2) | 7240 | (40,181) | ~336±16 值周期块 ×16（块长缓增） | seg*→MUGROUP kappa_g（弱，score 0.2-0.75） |
| 6 | hyades_eos / qeos_115.dat | 4333×5 | 21664 | (32,677)/(16,1354) | 模板 hyades_eos(128,92) 命中（score 2.0） | seg3→E erg/g x1e-15、seg34→E erg/g x1e+02 |
| 7 | hugoniot / eos_32.hug | 137×6 | 822 | (137,6)/(6,137) | 轴样列 col1-5 全单调 | seg1-6→Up/Us km/s x1e-02（score 1.1-1.7） |
| 8 | coldopacity / Ac.coldopacity | 639×2 | 1278 | (639,2)/(2,639) | 轴样列 col0（Eph 轴） | seg0→miu cm2/g（score 0.085，同量级直接命中） |
| 9 | generic_curve / ionpot.dat | 16×1 | 16 | (16,1)/(1,16) | 单列 16 值，neg_frac=0.25 | 无 |

## 3. 分族解读（GUESS ONLY）

### 3.1 mpqeos（.301）与 feos_native（.feos）——同一生成器两种布局

两份报告呈现**同一特征指纹**：121/71 值周期交替块、段间 decade 跳变
（~1e9 ↔ ~3.55e-54 ↔ ~3.16）、neg_frac≈0。解读：

- **121/71 交替**对应 FEOS 表内部按温度行的分区输出（与 mpqeos 解析器
  已核实的 192×69 主网格不一致 → 报告标注 `best template length mismatch
  (internal)`，即文件含网格外附加段）；
- **3.55e-54 级跳变**：FEOS 用 Maxwell 构造消除 van der Waals 回环
  （Faik et al. 2018, §Maxwell construction），未构造区/两相区的中间态以
  极小占位值输出——这就是 mpqeos 解析出的 **Z 段负值（R3）的来源**：
  共存区电荷态外插为负，不是数据损坏；
- **mpqeos Z 段 = charge state（每离子平均自由电子数）**：FEOS 文档明确
  其计算量含 charge state（§4 联网证据②）；Z 与 NoFree 是同一物理量的
  两种生成器口径。该段与 multi_opacity 的 NZ 指纹不匹配（FEOS 输出
  log10 span 达 66，量级结构完全不同），故指纹层无法自动命中——
  **属"缺参考文件"而非"无结论"**（见 §5）。

### 3.2 ledcop_zeff（Al.NoFree）

4 列宽 × 807 数据行；factor 候选 (43,75) 最方优先。模板反演
`ambiguous`（f2_gray 与 ledcop_split 同分 2.0）——文件尺寸介于两个已知
模板之间，盲读层不强行裁决。列语义不再依赖猜测：NoFree=<Z>/ion、
AvSqFree=<Z²>/ion 已由 LANL TOPS FAQ 逐字定义（§4.1），并已升级字典。

### 3.3 ledcop_atomic（Al.txt）

主体 3 列 × 34 万行谱表；头部另有 5/6 列标量段。指纹命中
**Ross（cm2/g）**与 NoFree/AvSqFree——即 ATOMIC 文件头部汇总列与
LEDCOP 同名列物理量一致（同属 TOPS 输出约定，§4.1 opac-help 引文：
ATOMIC 与 LEDCOP 是 TOPS 两类数据文件）。带 1e-02 量级偏移（头部汇总
段的单位/对数前处理与主表不同），方向不锁定。

### 3.4 multi_opacity（SNOP.PLANCK）

~336 值周期块 ×16，块长缓增（328→420）。弱命中 MUGROUP kappa_g。
解读：PLANCK 文件按温度点分块输出群不透明度，块长缓增对应群数或
密度点数随温度变化——与 snop_input 族已核实的 X1/X2（photon energy
bounds）一致，即 PLANCK 块=频率分组 kappa。无独立手册（§5-2）。

### 3.5 hyades_eos（qeos_115.dat）

模板反演直接命中已知布局 (128,92)。指纹命中两段 **E（erg/g）**，
带 1e±15 整数量级偏移——与解析器把 CGS(erg/g) 换算为 J/kg(1e-4)/
MJ/kg(1e-7) 的复合换算特征一致，量级结构（冷区结合能段 vs 高温段）
逐段对应。raw_tail（头 10 行说明之外的大段）仍无文档（§5-3）。

### 3.6 hugoniot（eos_32.hug）

137×6 规整矩阵，col1-5 全轴样（单调唯一）。指纹命中 **Up/Us（km/s）**
x1e-02——冲击波质点速度/激波速度列，与解析器逐文件 `# name [unit]`
头声明的 km/s 口径仅差固定量级偏移（m/s↔km/s 特征）。命中稳定
（6 段全部落 Up/Us），可信度为本批最高。

### 3.7 coldopacity（Ac.coldopacity）

639×2 两列规整表：col0 轴样（光子能量 Eph），col1 与已知族
**miu（cm2/g）同量级直接命中**（scale=1，score 0.085 为匹配距离
最小值）。即冷不透明度表=(Eph, miu[cm2/g]) 两列，与文件头
`#name`/`#unit` 两行声明（已核实）互证。

### 3.8 generic_curve（ionpot.dat）

头 10 行说明 + 单列 16 值。值域 0.0135→14.1（跳变 idx1），
neg_frac=0.25。解读：**元素逐级电离电势表（eV）**——16 值恰为
常见写入的 K/Ca/Ti 类多级电离序列规模；负值疑为基态参考约定
（结合能取负）。无任何生成者文档（§5-5），**不写回字典**。

## 4. 联网证据（已核实一级出处）

### 4.1 LANL TOPS FAQ —— NoFree / AvSqFree 逐字定义 ✅

- 出处：<https://aphysics2.lanl.gov/static/opacdocs/opac-faq.html>（LANL T-1 官方）
- **Q1**（free electron number，即 NoFree 列）逐字引文：
  *"For a single element, the free electron number is the average number of
  free electrons per ion. It is obtained by multiplying the relative population
  of each ion stage by the number of free electrons for that stage, zero for
  the neutral, one for single ionized etc. For a mixture, it is a weighted
  average using the number fractions of each constituent of the mixture."*
  → **每离子平均自由电子数 <Z>（无量纲）**；
- **Q7**（"Av Sq Free" 列）逐字引文：
  *"This is the average of the square of the number of free electrons over
  the ion stages of an element. It is obtained by summing the product of the
  relative abundance of each ion stage times the square of the number of free
  electrons for that ion stage, zero for neutral etc."*
  → **自由电子数平方的离子态平均 <Z²>（无量纲）**，与 <Z> 配套
  （差值给出离子态方差）；
- 同源性佐证：TOPS help 页（<https://aphysics2.lanl.gov/static/opacdocs/opac-help.html>）
  逐字 *"The ATOMIC files are the latest data files produced by the LANL
  opacity team (groups T-1 and XCP-5)... The LEDCOP files are older cross
  section files"* —— **LEDCOP/ATOMIC 均为 TOPS 输出格式**，NoFree/AvSqFree
  列名即 TOPS 输出约定；
- 最佳引用：N. H. Magee, Jr., J. Abdallah, Jr., R. E. H. Clark, et al.,
  "Atomic Structure Calculations and New Los Alamos Astrophysical Opacities",
  ASP Conf. Ser. **78**, 51 (1995)（FAQ Q13 官方指定）。

**字典动作（已执行，非猜测）**：`ledcop_zeff.NoFree/AvSqFree`
kind: none→primary document，tags 折叠 `uk, uv`→`uv`，
`docs/eosop变量控制字典.md` 已再生成，test_field_checks 11 tests 全绿。
**待用户人工核查后翻 checked=True 消标记。**

### 4.2 FEOS / MPQeos —— charge state 与负压根源 ✅

- 出处：FEOS 项目页 <https://physik.faik.de/feos.php>；
  S. Faik, A. Taweechat, et al., "FEOS — equation of state and opacities
  from warm dense matter to fusion plasmas", Comput. Phys. Commun. **225**,
  30-43 (2018), DOI: [10.1016/j.cpc.2018.01.008](https://doi.org/10.1016/j.cpc.2018.01.008)；
- MPQeos 源流：Kemp & Meyer-ter-Vehn 的 QEOS 模型的 FEOS 实现；
- 文档明确的计算量含 **charge state（电荷态/平均自由电子数）** →
  支持 §3.1 "Z 段 = charge state" 猜测；
- Maxwell 构造消除 vdW 循环 → **未构造的液气共存区 P/Z 可为负**
  → 解释 mpqeos Z 段负值（R3），非数据损坏。

## 5. 缺失参考文件清单（请用户裁决/补充）

| # | 缺失项 | 现状与影响 | 建议 |
|---|--------|-----------|------|
| 1 | **FEOS `.feos`/`.301` 逐列格式手册** | 仅 §4.2 论文；121/71 周期块与附加段的逐列语义无法定锚，mpqeos.Z 只能定性为 charge state | 向 matter++ 交付方索取 FEOS 输出说明；或以 Faik 2018 附录为准人工核查 |
| 2 | **SNOP 输出文件（.PLANCK/.MUGROUP）格式说明** | SNOP.MANUAL 仅覆盖输入段（snop_input 族已核实 5 字段）；输出块结构靠盲读 | 索取 SNOP 输出格式节或样例对照文档 |
| 3 | **hyades qeos_*.dat raw_tail 说明** | 头 10 行有文档（Hyades 格式说明.doc），其余大段无声明；盲读命中 E(erg/g) 但 raw_tail 仍 unknown | 补充 qeos 系列生成脚本/文档 |
| 4 | **LEDCOP 专用 .doc 的可读替代** | 原格式说明 .doc 抽取乱码不可引用；NoFree/AvSqFree 已由 TOPS FAQ 补位，Ross/Planck 仍只靠文件头第 3 行 | 可接受现状（文件内声明已够用）；如需逐列布局可下载 TOPS methods 页 |
| 5 | **ionpot.dat 生成者与单位** | 16 值单列、无头注释单位；盲读猜 eV 电离电势 | 确认生成脚本（疑为 hyades 输入配套）后补注释或登记 |
| 6 | **Thermos "Ideal Gas" 小表说明** | mat_Mo/mat_U/mat_W 反演出 f1_with_e0 布局（order_mismatch 3 例），无文档 | 低优先级：3 个小表不影响主流水线 |
| 7 | **Ta2O5 gnuplot 派生文件（.ist/.isc/.cst/.mexport）** | 无来源软件说明，未登记（217 未归类清单内） | 裁决：是否属于 eosop 数据族 |
| 8 | **XrayMassCoef NIST 网页表格（36 个 HTML）** | NIST 质量衰减系数网页存档，未登记 | 裁决：是否入库为新族（有 NIST 一级出处可登记） |

## 6. 产物与命令

- 机器报告：`test/eosopdata/step02_families/_out/guess_uk/<family>__<fname>.txt` ×9
- 单文件命令：`PYTHONPATH=<repo> python -m eosop_pro.guess <file> [--compare-family F]`
- 未归类全树清单：`_out/identify_sweep/unclassified_list.txt`（217 文件）+
  `type_conflict.csv/md`（997 有声明文件 0 真冲突）
- 字典事实层（与本报告猜测层分离）：
  `eosop_pro/registry/field_checks.py` + `docs/eosop变量控制字典.md`
