# test_multi —— mat_CELIA (CH 聚苯乙烯 MID201) 集成测试（独立运行）

> 最后核对：2026-11-14 · commit 093519e 后新增 · **不接入 parsers/test/run_all.py**（用户裁定）

## 定位

对 `src/Multi1D++Portable20241128/matter++/mat_CELIA/` 的两个数据文件做**组合**集成测试，
与用户提供的查看工具边界标注（POLYSTYRENE / SESAME 7590 / MURAKAMI 1990 / MFP 公式）
做语义交叉验证。被测解析器：`multi_inverted_eos.py`（F1）+ `multi_opacity.py`（F2）。

| 文件 | 族 | 数值表头（数据文件无文本头，REM 备注在 material.base） |
|---|---|---|
| `CH_ieos`（无扩展名） | multi_inverted_eos | `7590 / 0 / 101 / 100`；尾部 2 个未声明数值 → raw_tail |
| `C_AN.PLANCK` | multi_opacity | `1 / PLANCK 1 / 20 / 20`（单群灰；material.base 中 PLANCK 与 ROSSELAND 双角色指向它） |

## 运行

```bash
cd <gen_eos_op>
python eosop_pro/parsers/test/test_multi/test_celia_combined.py
```

产物：`../../test/_out/test_multi/`（summary.txt + report.html + png）。

## 测试函数（6 个）

1. `test_ch_ieos_parse` — 表头 7590/101×100、计数守恒（含 tail）、raw_tail、轴末端 20880、
   **单位假设交叉验证**（P/E/T 原生值 vs 操作者视图 vs 解析器约定，逐场比值证据）
2. `test_c_an_planck_parse` — PLANCK 1 灰、20×20、444 数值、轴范围对操作者视图（1e-6..100 g/cm³、1..1e5 eV）、
   κ log10 存储
3. `test_material_base_combo` — MID201 组合关系（EOS→CH_ieos，PLANCK/ROSSELAND→C_AN.PLANCK）+
   REM 四条备注逐字提取
4. `test_combined_plots` — EOS (rho,de) 批量图 + 不透明度 (rho,Te) 热图 + `invert_eos.to_Te_grid`
   反演骨架（P 等温线族）
5. `test_cn4_comparison_stub` — 定位解析 Z06 参考表 + 对比 TODO 清单（无数值断言）
6. `test_multi_report` — 图文 HTML 报告（REM 摘录/首行判读/组合表/单位对照/图像/TODO）

## 单位裁定证据（重要）

CH_ieos 原生最大值：P=4.89e8（=操作者 4.89e20 dyne/cm² ÷1e12 → **Mbar**）、
T=3.714e8 K（×8.617e-5 ≈ 32003 eV = 操作者 "32001.1 eV" → **Kelvin 原生**）、
E 同 1e12 关系（→ **Mbar·cm³/g**）。**操作者工具的 dyne/cm² / eV 标注是换算后显示值，
解析器 F1 约定（P Mbar / E Mbar·cm³/g / T Kelvin→eV）与数据自洽**——待人工最终确认后关闭 TODO-1。

## 与 Z06 cn4 对比（后续）

见 report.html §6 TODO：① 单位裁定（证据已倾向解析器约定）② F1 反演 + rho 轴对齐
（build_grid_for_tables + resample_2d）③ 灰 vs 6 群灰化口径 ④ 物理模型差异
（IONMIX vs SESAME+Murakami）→ 差值大属预期，对比目标是量级与趋势。

---

# test_cn4_to_multi —— cn4 → MULTI (F1/F2) 转换评估（独立运行）

> 2026-11-14 新增 · **不接入 run_all.py** · 上面 §"与 Z06 cn4 对比" 的 TODO ② 已由本测试落地

## 定位

把 `Z06_0.50-Z01_0.50` cn4（与 polystyrene CH 同成分）经 `eosop_pro.convert` 转成
F1（no_e0 布局）与 F2（6 群）文件，并与 mat_CELIA 的 CH 文件对比评估。

**转换口径（用户裁定）**：
- de ≡ E_total = e_ion + e_ele（no_e0；IONMIX 零点=冷态 → E_c≡0，即文献 E−E_c）；
- 单位链 P ÷1e5→Mbar、E ÷1e5→Mbar·cm³/g、T eV（文件写 K）；
- 群边界不同（cn4 6 群 0.1–1e5 eV vs C_1G/20G/100G）→ **只转换+绘图，不数值对比**；
- 物理声明：IONMIX vs SESAME/Celia，对比是邻近度评估非一致性验证。

## 运行

```bash
cd <gen_eos_op>
python eosop_pro/parsers/test/test_multi/test_cn4_to_multi.py
```

产物：`../../test/_out/cn4_to_multi/`（CH_from_cn4_eos、CH_from_cn4_rosseland、
CH_from_cn4_planck、f1_curves.png、f1_heatmap_T.png、f2_heatmaps.png、
report.html、summary.txt）。

## 测试函数（6 个）

1. `test_convert_f1` — 转换 + 读回：no_e0 布局、形状 (60,31)、P/T 全正无 NaN、de 单调
2. `test_f1_roundtrip` — 转换链闭合：生成 F1 → `to_Te_grid` 反演 → vs cn4 原始
   （P 中位 0.03%、E 0.32%，断言 <10%）
3. `test_convert_f2` — F2 读回：6 群归并 1 表、群边界与 cn4 一致、log10(κ) 范围合理
4. `test_group_bounds_vs_multi` — 群边界对照表（cn4 vs C_1G/20G/100G/C_AN）：
   边界不同 → 记录"只绘图"决策
5. `test_f1_vs_ch_ieos` — 公共 (rho,Te) 窗口对比（rho 0.008–216 g/cm³ 取 CH 网格∩cn4 范围）：
   P 中位 17.8% / E 中位 15.9%（跨模型差异，属预期）
6. `test_multi_report` — HTML 评估报告（口径声明/单位链/统计表/群边界表/图）

## 新增 API（convert 层）

- `invert_eos.to_de_grid` — (rho,Te)→(rho,de) 正演反演（`to_Te_grid` 的逆）
- `invert_eos.cn4_eos_to_rho_base` / `cn4_opac_to_rho_base` — nion(cm⁻³)→rho(g/cm³) 轴适配
- `writers_multi.write_multi_inverted_eos_from_cn4` — cn4→F1（no_e0）
- `writers_multi.write_multi_opacity_from_cn4` — cn4→F2（log10 κ + 群边界）

---

# test_si_combined —— Si（Z14 / matter++）组合核查（独立运行）

> 2026-11-14 新增 · **不接入 run_all.py** · 与 CH 轮同策略；数据与外部根
> `E:\...\Multi1D++Portable20241128` 逐字节相同（SHA256 比对）

## 定位

Si 材料全套核查：`hyades/qeos/qeos_392.dat`（F3 Hyades/QEOS，68×67）+
`Thermos/mat_Si/` 四件套（Si_Planck/Si_Rosseland 110 群、Si_Zeff/Si_Z）+
`Si.ini`（群边界明文）+ `Z14_1.00` cn4 对比。操作者视图 oracle =
用户提供的 Multi 程序加载输出（2026-11-14）。

## 关键事实与裁定

- **qeos_392 磁盘是 (rho,T) 基 68×67**（Hyades F3，L=9249，行 1 QEOS 注释/行 2 表头）；
  用户粘贴的 "Inverted EOS 68×299 + e0/de" 是 **Multi 程序运行时自产**（磁盘无此文件，
  [S-PROG]）→ 测试自反演软核验：de_max 命中（<2%）、e0_max 精确一致、
  e0_min 差 ×1e3 记 [S-UNK]（程序低温端 e0 定义未公开）。
- **T 轴单位链**：文件存 log10(T_keV) ∈ [-4.39794, 2.0] → ×1e3 → 0.025–1e5 eV
  ＝ 操作者显示值。
- **Si.ini Frequency=111 边界** 与解析器 group_bounds、操作者 110 群清单三方逐点一致。
- **ZEFF 载荷为 log10(zbar)（2026-11-14 用户裁定，已落库）**：45 个 mat_*_Zeff.dat
  族校准，10^Z 与核电荷数逐一吻合（Si 1.1715→14.8、U 1.966→92.5）；
  Z≤-9.9 为哨兵（log10(1e-10)）。field_checks "Z" 条目已转 checked
  （parser-measured, log10(zbar)），解析器 field_units/field_log10 同步，
  字典 md 已重生成；ZEFF2（Z2）Thermos 无样本，裁定不适用。
- **Si_Z.dat(eV log10) / Si_Zeff.dat(keV log10)**：Readme.txt 约定成立，
  unit_hint 必须分别为 eV / keV（错用差 ×1e3）。
- **对比口径（2026-11-14 用户裁定升级）**：EOS 数值对比（P 中位 9.6% / E 17.6%，
  跨模型预期）；不透明度 cn4 6 群 vs Si 110 群 → **边界拼接群数值对比**
  （5/6 群可精确拼接：1/1/9/49/42 个 Si 子群，能量宽度加权聚合——Rosseland 调和 /
  Planck 算术，平谱近似；0.25–1.35 dex，跨模型预期；群6 超出 Si 40000 eV 上限不比）；
  zbar vs Zeff 软对比（log10 校准后中位 12.0%）。对比图统一单位
  log10(cm2/g) / log10(zbar) + 共享色标。
- **Planck 发射 vs 吸收机制**（报告 §6.2）：MULTI = Kirchhoff 绑定
  （η=κ·B，非 LTE 用独立 EPS/NLTE 因子表，SNOP.MANUAL NEPS）；
  abjt_03.f = 两条独立链（吸收受激辐射修正+实际布局 L762-774/1047-1083，
  发射恒用 LTE 平衡布局；opacgp Planck 权分别积分 → 块18/19）；
  Z14 实证块18 vs 19 有 7497/9486 点不同（中位 68%）→ 独立生成、不可互替。

## 运行

```bash
cd <gen_eos_op>
python eosop_pro/parsers/test/test_multi/test_si_combined.py
```

产物：`../../test/_out/test_multi_si/`（qeos_axes_overview.png、qeos_inverted_check.png、
si_opacity_heatmaps.png、cn4_vs_si_opac_heatmaps.png、stitched_rosseland.png、
stitched_planck.png、cn4_vs_si_eos_curves.png、
zeff_compare.png、f2_from_cn4_ross/、f2_from_cn4_planck/、report.html、summary.txt）。

## 测试函数（10 个）

1. `test_qeos_parse` — 行 2 表头 392/14/28.08/2.42/9249、计数守恒、68×67、
   P/E 轴范围 vs oracle、T keV→eV 单位链
2. `test_qeos_self_inversion` — 68×299 程序自产边界软核验（de_max<2%）+
   `to_de_grid` 正演反演演示（coverage 100%）
3. `test_si_opacity_parse` — 110 群 MUGROUP、111 边界逐点 oracle、κ max 命中、
   Planck≥Rosseland 98.2%
4. `test_si_zeff_parse` — ZEFF 双文件（eV/keV 各自 hint）、log10(zbar) 口径、
   哨兵掩膜、Si.ini 三方交叉
5. `test_cn4_z14_load` — Z14 cn4 51×31×6
6. `test_cn4_eos_vs_qeos` — 公共窗口（rho 0.001–932 / Te 1–2e4）数值对比
7. `test_cn4_opacity_vs_si` — 群边界不匹配记录 + **块18 vs 块19 发射/吸收独立生成实证**
8. `test_cn4_opacity_stitched_groups` — 边界拼接群数值对比（dex 统计 + 2×5 共享色标图）
9. `test_cn4_zbar_vs_zeff` — log10 校准后的软对比（中位 12.0%）
10. `test_si_report` — HTML 报告（文件树/oracle 表/单位链/拼接对比/§6.2 机制/图库）
