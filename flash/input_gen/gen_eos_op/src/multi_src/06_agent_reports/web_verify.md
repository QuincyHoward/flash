# Web 核验记录（[S-WEB]）

> 访问日期：2026-09-17 / 2026-09-18（GMT+8）
> 纪律：本文件内容仅用于**书目核验与补白**，不得改写本地结论。与本地冲突时以本地为准并在正文显式记录。

---

## W1 — SESAME 表号编码约定（LANL 官方）

- 源：LANL《Fundamentals of SESAME Equation of State》
  URL: https://cdn.lanl.gov/files/sesame-eos-intro_59fd3.pdf
- 源：LANL SESAME Database 官方页
  URL: https://www.lanl.gov/engage/organizations/aldsct/theoretical/pcm/sesame
- 源：OSTI《Sesame ASCII File Format》
  URL: https://www.osti.gov/servlets/purl/1524342
- 源：OSTI《The SESAME database》(Johnson, J. D., 1994)，LA-UR-94-1451
  URL: https://osti.gov/biblio/10150216

**核验要点（可与本地对账）**

1. **材料 ID 段位约定**（LANL slides）：
   - EOS：`0–9999`，`50000`、`90000` 仅 beta/experimental
   - Opacity：`10000` 或 `60000`
   - Conductivity：`20000` 或 `70000`
   - Melt and Shear：`30000` 或 `80000`
2. **表型 `nnn`**：
   - `100` 系列 = 注释；`101` = 定长基本信息；`102–199` = 自由文本
   - `201` = 原子序数、原子量、参考密度等
   - `300` 系列 = ρ-T 网格上的函数：`301` 总（=304+305+306）、`303` cold+nuclear、`304` 电子、`305` 离子（含零点）、`306` cold only、`311` Maxwell 构造的 301（internal only）、`321` 多相质量分数
   - `400` 系列 = 沿曲线：`401` vapor dome、`411` solidus、`412` liquidus、`431`/`432` shear modulus
   - `500` 系列 = opacity；`600` 系列 = conductivity
3. **OSTI ASCII 格式记录的列索引**（1-based）：
   File Number 1-2 / Material ID 3-8 / Table ID 9-14 / Num. Words 15-20 / `r` 21-24 /
   Creation Date 25-33 / Update Date 34-42 / Version 43-46 / Spaces 47-78 / File Number 79-80
   - File Number 第 1 字符恒为空格，第 2 字符：`0`=每材料首条描述记录、`1`=中间记录、`2`=文件结束
   - 数据记录：**每行最多 5 个值，值间无空格，行尾 5 位 boolean mask**
   - 这与本地 `B.mexport`（`0104005   101   160   r        0        0   1                                 1`）**完全同构** ⇒ FEOS 的 `.mexport` 是 SESAME ASCII 整库导出，非自创格式。`[S-L1]` 转为有网核支撑。
4. **opacplot2 前缀**（第三方实现，可作交叉参考）：
   `301→total_`、`303→ioncc_`、`304→ele_`、`305→ion_`、`306→cc_`；
   顶层数据点：`abar`(Mean Atomic Mass)、`bulkmod`、`excoef`、`rho0`、`zmax`(Mean Atomic number)
   ⇒ **注意：opacplot2 的 `zmax` 名为 "Mean Atomic number"，与本地 `AL_eos` 第 2 字段 `<Z>=2.7`（Al 应约 13）不符**，而是与本地实测 `.66000000E+02`/`.74000000E+02` 等网格计数相邻。本地 `AL_eos` 第 2 字段 2.7 **不是** mean atomic number，须按本地实测解读，勿采信 opacplot2 命名。
5. **SESAME 覆盖范围**：ρ 典型 `1e-6 – 1e4 g/cm³`，T 典型 `0 – 1e5 eV`；opacity 下限约 `1 eV`。
6. **引用格式**（LANL 要求）：`SESAME [material number] [authors], SESAME [material number], in Los Alamos National Laboratory Report No. LA-UR-[year-number], ([month, year])`

## W2 — SNOP / MULTI 血统（Eidmann 1994）

- 源：K. Eidmann, "Radiation transport and atomic physics modeling in high-energy-density laser-produced plasmas",
  *Laser and Particle Beams* **12**(2), June 1994, pp. 223–244
  DOI: https://doi.org/10.1017/S0263034600007709
- 源：Ramis, Schmalz, Meyer-ter-Vehn (1988), *Comput. Phys. Commun.* **49** — 被上文献反复援引为 MULTI 原始出处（本地 `doc/References/1988CPC49` 对应）
- 源（间接，佐证 SNOP 参数语义）：https://ar5iv.arxiv.org/html/2207.14026

**核验要点**
1. **SNOP 模型定位**：steady-state **screened hydrogenic explicit ion model**，生成 **non-LTE opacity tables** 供 MULTI 使用。与本地 `SNOP.MANUAL` 一致。
2. **SNOP 频率网格实测惯例**（第三方使用）：**3000 photon frequency points**，下界 **1 eV**、上界 **5 keV**；**20 photon energy groups** 求 Rosseland/Planck 平均。
   ⇒ 与本地 `SNOP_LTE.PLANCK` 实测群边界 `1.0 – 100 eV`（第 2 行 `0.10000000E+01 0.10000000E+02`）**不一致**，说明群边界依 namelist `X1/X2` 与 `IGROUP` 而变，**不是固定 1 eV–5 keV**。本地为准，须记录差异。
3. **dielectronic recombination 参数 `d`**：文献中使用 `d = 10`；`d` 从 0→1000 使平均电离度显著下降。可用作本地 SNOP 参数 `DREK` 的语义参照（**注意：本地参数名是 `DREK`，与文献的 `d` 是否同一量须标 `[S-UNK]`，勿强行等同**）。
4. **MULTI** 为 Lagrangian 一维辐射流体程序，辐射输运用多群扩散近似，通量限制因子（flux limiter）常取 `0.03` 量级 —— 可作第 0 章血统叙述的旁证。

## W3 — LEDCOP / TOPS / u 网格（LANL 官方，**完全核实**）

- 源（**u 网格权威定义**）：LANL TOPS Opacities 官方文档 "Photon Energy Grid"
  URL: https://aphysics2.lanl.gov/static/opacdocs/photgrid.html
- 源：N. H. Magee, Jr. & R. E. H. Clark, "Los Alamos Opacity Web Page",
  LA-UR-97-4606 / CONF-970960, Feb 1998（会议：ICAMDATA, Gaithersburg, 1997-09-29~10-02）
  URL: https://physics.nist.gov/Icamdata/PDF/1Databases/magee.pdf
  URL: https://digital.library.unt.edu/ark:/67531/metadc690872/
- 源（第三方交叉核实 u 网格七段，**与官方逐段一致**）：arXiv:1203.5832v2 "The Los Alamos Supernova Light Curve Project: Computational Methods"
  URL: https://arxiv.org/html/1203.5832v2

**核验要点（与本地完全吻合，可升格为 `[S-L1]`+`[S-WEB]` 双重佐证）**

1. **u 定义**：`u = hν / kT`（hν 单位 eV，kT 单位 eV）。选 u 网格而非光子能量网格的理由（官方原文语义）：同一 u 网格可用于所有温度，且能覆盖积分 Rosseland/Planck 灰不透明度所需的重要光子能量区间——T=1 eV 需覆盖 0–20 eV，T=100 eV 需覆盖 0–2000 eV；改用 u 后两者都只需 0–20。**这一"为何用 u 网格"的理由是本地文档缺失的，可补白。**
2. **14,900 点七段表（官方原表，与本地清单逐段一致）**：

   | u 区间 | 点数 | 步长 |
   |---|---|---|
   | 0.0 – 12.5 | 9600 | 0.00125 |
   | 12.5 – 20.0 | 1600 | 0.005 |
   | 20.0 – 30.0 | 1000 | 0.01 |
   | 30.0 – 100.0 | 700 | 0.1 |
   | 100.0 – 1000.0 | 900 | 1.0 |
   | 1000.0 – 10000.0 | 900 | 10.0 |
   | 10000.0 – 30000.0 | 200 | 100.0 |
   | **合计** | **14900** | |

   9600+1600+1000+700+900+900+200 = **14,900** ✔ 算术闭合。
   ⇒ 本地计划中的"3000/3900 点频率依赖谱"与官方 14900 点 u 网格是**两个不同网格**（前者可能是导出时的抽样密度），须在正文区分，勿混为一谈。
3. **LEDCOP 代码定位**：Light Element Detailed Configuration OPacity，用 detailed LS terms（复杂离子阶段用 average configuration terms）计算 Z ≤ 30 元素的不透明度。
4. **网格与范围（官方 Table "Quantity/Range/Comments"）**：
   - 温度：`0.5 或 1.0 eV – 100,000 eV`
   - 密度：`1e-10 – 1e+9 g/cm³`
   - **10 temperatures/decade**；**1 to 3 densities/decade**；**最高密度依温度而定**
   - 1977 年版数据止于 `u = 30`
5. **OPLIB 关系式**（可作第 4 章/第 11 章补白）：
   - `κ_ν(ρ,T) = (N0/M) · σ_ν(η,T)`（N0 = Avogadro 数，M = 原子量）
   - `ρ(η,T) = M·N_I(η,T)/N0 = M·N_e(η,T)/(Z̄(η,T)·N0)`
   - `N_e = (4/√π)·(2π m_e kT)^{3/2}/h³ · F_{1/2}(η)`（F_{1/2} 为 1/2 阶 Fermi-Dirac 积分）
   ⇒ **TOPS 内部坐标是 (T, η, u) 而非 (T, ρ, u)**，ρ 由 η 经上述关系换算。这是本地文档未强调的重要事实。
6. **OPLIB 只考虑电偶极（E1）跃迁**做 bound-bound 贡献（不含禁戒线）；对 LTE 条件足够。OPLIB 会把邻近谱线做平均。
   ⇒ 可作为第 11 章"数据精度与适用性"补白。
7. **TOPS 越界行为**：请求的密度超出表范围时，warning 提示并对所有超范围密度**取最后（最高）密度点的值**。可作为第 6 章陷阱条目。

## W4 — IONMIX / ABJT

**未取得可引用的一手结果。** 检索返回的均为无关内容（刊名缩写规范页等）。
⇒ 正文中 IONMIX 血统一律引用**本地一手源码** `ionmix/`（若存在 `abjt_03.f`）与 IONMIX 用户指南，标 `[S-L1]`/`[S-L4]`；MacFarlane CPC 书目暂标 `[S-UNK]`，并在附录 F 的"待核验清单"中登记。

## W5 — Hyades（**部分核验**）

- 源：Jon Larsen, *Foundations of High-Energy-Density Physics: Physical Processes of Matter at Extreme Conditions*, Cambridge University Press（作者自述章节 Preface）
  URL: https://vdoc.pub/documents/foundations-of-high-energy-density-physics-physical-processes-of-matter-at-extreme-conditions-50dk6ibasuv0
- 源：本地 `matter++/hyades/` 数据文件内嵌血统字符串（`GOLD LANL SESAME #2700-304 DATED: 81678 101582`、`COPPER LLNL-QEOS Dated: 082802`）

**核验要点**
1. **HYADES 诞生年份 = 1988**，作者 Jon Larsen；其个人经历：早期在 UC Lawrence Radiation Laboratory（即 LLNL）参与 ICF 可行性研究 → 1980 年代初转至 KMS Fusion, Inc.（Ann Arbor, Michigan）→ 最终独立创业，开发 HYADES。
   ⇒ 可作第 9 章血统补白，标 `[S-WEB]`。
2. **"CAS Inc." 未被本次检索确证**（检索未返回 CAS Inc. 相关内容）。
   ⇒ 正文中 Hyades 供应商名称**标 `[S-UNK]`**，只引本地数据文件内嵌的 `LANL SESAME` / `LLNL-QEOS` 血统串。
3. **1994 *JQSRT* 51（Larsen）** 未核到具体条目 → 标 `[S-UNK]`。

## W6 — MPQeos / FEOS

**未取得可引用的一手结果。** 检索"MPQeos Kemp 229 LULI"返回的全是 LAMMPS/EAM 势函数与无关政务文档。
⇒ MPQeos 的 `MPQ229` 报告号与 S. Faik 的 FEOS 发布页**一律标 `[S-UNK]`**；正文只引用**本地** `doc/FEOS/Info.txt` 与 `doc/FEOS/*.pdf` 内嵌的血统声明（`[S-L1]`/`[S-L2]`）。
⇒ 本地 `matter++/mat_B/B.mexport` 内嵌 `/source. feos /date 202106191914`、`/comp. LULI /codes. FEOS /`、`contact: tommaso.vinci@polytechnique.edu` 是**比网络核验更强的一手依据**，应优先引用（标 `[S-L2]`）。

---

## 待核验清单（尚未取得可引用结果，标 [S-UNK] 或后续补）

| # | 待核验项 | 目标 | 处置 |
|---|---|---|---|
| P1 | IONMIX / ABJT 出处：MacFarlane, *Comput. Phys. Commun.* **56** (1989) 259–278 | 书目 | **W4 未获结果 → 标 `[S-UNK]`，只引本地源码** |
| P2 | LEDCOP / TOPS：LA-UR-97-4606（实为 97-4606，非 97-1038）；LA-10454（u 网格）；LA-6760-M | 书目 | **W3 已核实 97-4606 与 u 网格；LA-10454 / LA-6760-M 未核 → `[S-UNK]`** |
| P3 | Hyades 程序 (CAS Inc.) 与 Larsen JQSRT 51 | 书目 | **W5 部分核实：HYADES 1988 由 Jon Larsen 始创；"CAS Inc." 与 JQSRT 51 未核 → `[S-UNK]`** |
| P4 | FEOS / MPQeos：A. Kemp MPQ229；S. Faik FEOS_16.7 GPLv3 发布页 | 书目 + 许可 | **W6 未获结果 → `[S-UNK]`；只引本地 `doc/FEOS/Info.txt` 与 `B.mexport` 内嵌声明** |
| P5 | Rostock（`.cst`）德文表头出处 | 出处 | 待核 → 失败则 `[S-UNK]` |
| P6 | KATACO（`.KAT`）出处 | 出处 | 待核 → 失败则 `[S-UNK]` |
| P7 | Young & Corey, *J. Appl. Phys.* **78** (1995) 3748（soft-sphere） | 书目 | 待核 |
