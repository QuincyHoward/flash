# multi_src —— 《MultiEOSOP格式说明.md》配套源码与素材库

> 本目录存放撰写与维护 `src/multi_docs/MultiEOSOP格式说明.md` 过程中产生的**全部脚本、
> 探针、抽取文本、验证输出与代理报告**，按**功能**分门别类归档，便于后续**抽象固化**
> 为可复用的解析器/工具库。

## 0. 快速导航

| 我想…… | 去哪个子目录 |
|---|---|
| 了解包内到底有哪些文件、多大、什么后缀 | `01_inventory/` |
| 找上游官方文档的原文 | `02_doc_extract/` |
| 核对文档里某句"实测"结论的依据 | `03_anchors/` |
| 看某个格式是怎么被逆向出来的 | `04_probe/<族>/` |
| 验证"同一材料不同格式数据一致" | `05_cross_validation/` |
| 看某代理交付的调研素材 | `06_agent_reports/` |
| 重新生成/修改文档 | `07_doc_build/` |
| 重新跑一次质量核查 | `08_audit/audit_v3.py` |
| 找格式的**终极权威**（源码级） | `09_source_verify/vendor/` |

## 1. 目录结构

```
src/multi_src/
├── README.md                    本文件（索引与约定）
├── MANIFEST.tsv                 源→目标完整映射（338 条）
├── EXCLUDED.md                  未收录项及理由（110 个，属另一工作流）
│
├── 01_inventory/                盘点与索引
├── 02_doc_extract/              一手文档抽取（.doc/.docx/.pdf/.xlsx → txt）
│   ├── docext/                  散篇说明抽取物
│   ├── legacy/                  旧版说明抽取物
│   └── pdfext/                  PDF 抽取物（FEOS / MPQeos / 论文）
├── 03_anchors/                  实测锚点库（全文引用的实证底座）
├── 04_probe/                    格式逆向探针
│   ├── 01_cst_and_noext/        .cst 双变体 + 无扩展名族
│   ├── 02_multigroup_planck/    多群不透明度表（PLANCK/ROSSELAND/EPS/ZEFF）
│   ├── 03_sesame/               SESAME 族
│   ├── 04_feos/                 FEOS / MPQeos 族
│   ├── 05_hyades_ionmix/        Hyades / IONMIX 族
│   ├── 06_general/              跨族通用探针
│   └── probe_noext_agent/       代理 probe-noext 完整作业目录（37 文件）
├── 05_cross_validation/         交叉验证 + 三方仲裁
├── 06_agent_reports/            代理交付的调研素材报告
├── 07_doc_build/                文档装配线（计划/分稿/合并/补丁）
│   ├── multi_doc_parts/         分批撰写稿（17 文件）
│   └── parts/                   后期替换稿
├── 08_audit/                    审计与核查（质量门禁）
└── 09_source_verify/            源码级核验与官方包
    └── vendor/                  FEOS 官方发行包（37 源码 + 文档 + 参数）
```

## 2. 各子目录职责

### `01_inventory/` —— 盘点与索引

对 `src/Multi1D++Portable20241128/` 与项目根做**全量清点**：文件树、后缀频次、体积、体积分档、路径 token 索引、材料目录清单。产出 JSON/TXT 索引，供后续所有章节引用同一套"事实底座"。

### `02_doc_extract/` —— 一手文档抽取

把上游 `.doc/.docx/.pdf/.xlsx` 权威说明**逐份转成纯文本**（对应溯源级 `[S-L1]`）。子目录 `docext/ legacy/ pdfext/` 为抽取产物；根下 TXT 为各级汇总（`doc_misc.txt` 汇总散篇、`dataheaders.txt` 汇总数据文件头、`textdocs.txt` 汇总纯文本说明等）。

### `03_anchors/` —— 实测锚点库

**全文引用的实证底座**：`anchors.md` 收录各族真实文件的头部原文 + 字节数，写作时所有"实测"结论必须溯源到这里。`sample_index.md` 为样本索引，`build_anchors.py` 为生成器（可重跑以刷新锚点）。

### `04_probe/` —— 格式逆向探针

按**格式族**分组的探针脚本与原始输出。每个子目录自成闭环：脚本 + 输出 + 结论。

### `04_probe/01_cst_and_noext/` —— `.cst` 与无扩展名族

`probe_00`–`probe_14` 系列探针及 `out_01`–`out_14` 原始输出。核心成果：`.cst` 双变体（德文/英文）记录结构、`-1.#INF00e+000` 处理、无扩展名多群不透明度表识别。属代理 `probe-cst-naming` 的完整作业痕迹。

### `04_probe/02_multigroup_planck/` —— 多群不透明度表

`my_planck_*.py` 系列（本人实测）：逐族验证 `PLANCK`/`ROSSELAND`/`EPS`/`ZEFF` 的记录结构、群数双重编码、能量带语义、闭合算术。

### `04_probe/03_sesame/` —— SESAME 族

`.sesame` / `.sesame_` / `.sesame_PLANCK` 的尺寸公式闭合、首字段哨兵常量、粘连表头修复。`v_sesame_*` 为独立复算脚本（用于仲裁代理结论）。

### `04_probe/04_feos/` —— FEOS / MPQeos 族

`.feos` / `.301`/`.304`/`.305` / `.mexport` / `.cst` 的字节级验证；`al_feos_probe.out` 为本地 FEOS 族文件全量定位输出（192 KB）。

### `04_probe/05_hyades_ionmix/` —— Hyades / IONMIX 族

Hyades ASCII EOS 与 IONMIX `.cn4`/`.cnr` 的头部解码、`ntrad` 反解、计数闭合。`verify_cnr*` / `verify_cn4` 为逐属性验证脚本。

### `04_probe/06_general/` —— 通用探针

跨族探针：尾部块剥离、手册记录序比对、路径核实（`path_verify*`）、断言复核（`verify2`–`verify7`）。

### `04_probe/probe_noext_agent/` —— 代理 probe-noext 作业目录

代理 `probe-noext` 的**完整工作目录**（37 文件）：`groupA*` 系列按族分组探针、`selfcheck.py` 自检、`noext_list.json` / `groupA_grids.json` 中间数据。保留原样以便追溯。

### `05_cross_validation/` —— 交叉验证与仲裁

**同材料跨格式一致性验证**：`xval_s1`–`xval_s14` 分阶段脚本与输出；`eos_readers.py` 为各族读取器原型；`cross_validation.md` 为汇总报告。`arb*.py` / `arbitration.md` 为**三方结论仲裁**（主理人独立复算，否决代理假阳性）。

### `06_agent_reports/` —— 代理产出报告

各代理交付的**素材报告**（写作时直接引用的中间成果）：格式调研、源码定义反推、网络核验记录、遗漏目录补查、族报告拆分件（`src_doc_*`）。注意：这些是**素材**，正式结论以 `src/multi_docs/` 为准。

### `07_doc_build/` —— 文档生成与打补丁

**文档装配线**：`plan_multi_doc.md`（写作计划）、`multi_doc_parts/`（分批撰写稿）、`merge_doc.py`（合并器）、`patch_*.py` / `p*_*.py`（历次结构性补丁）。**每个补丁脚本都是幂等可重跑的**，且带 `count` 断言防误改。

### `08_audit/` —— 审计与核查

**质量门禁**：`audit_v3.py` 为终版综合核查（汉字门禁 / 围栏配对 / 表号唯一性 / 章节单调性 / 交叉引用有效性 / 表格列数 / 残留标记）；`audit*.txt` / `audit_report*.md` 为历次报告；`chk_*.py` 为专项检查；`diag*.py` 为诊断脚本。

### `09_source_verify/` —— 源码级核验与官方包

**最硬证据源**：`vendor/` 内为 FEOS 官方发行包（`Code/` 37 个 `.C/.H` 为全部表写出器的格式定义、`Documents/` 官方文档、`EOS-Data/` 参数文件）。`dl_feos.py` / `dl_ionmix.py` 为获取脚本。

## 3. 完整文件清单

### `01_inventory/`（盘点与索引）

```
  _candtok.json                                                  6825
  _filelist_tmp.txt                                                 0
  _fl.txt                                                        1746
  _idx_portable.json                                           134009
  _idx_repo.json                                               278420
  _ls.py                                                         1375
  _ls2.py                                                        1685
  _mats.py                                                       1066
  _mhead.py                                                      1127
  _miss.json                                                     1360
  _pathtok.json                                                 22084
  _tree.py                                                       2330
  build_inventory.py                                             5491
  count_patterns.py                                              1580
  count_patterns.txt                                            92370
  cov_check.py                                                   1086
  diag_issues.py                                                 1210
  dirlist.txt                                                    3280
  dirlist2.txt                                                   2761
  find2.py                                                        596
  find_lower.py                                                   988
  find_lower2.py                                                  560
  inv_classified.txt                                            48509
  inv_classify.py                                                2792
  inv_matter.json                                                3057
  inv_matter.py                                                  2086
  inv_two_tmp.py                                                  967
  ls_head.py                                                      513
  ls_state.py                                                     471
  out_feosls.txt                                                  114
  out_lsroot.txt                                                 1072
  out_srcs.txt                                                      3
  paths_resolve.json                                            53846
  probe_00_env.py                                                 905
  probe_09_lsroot.py                                             1237
  probe_lower.py                                                 1103
  scan.txt                                                      16471
  uncovered.py                                                   1151
  z_amb.py                                                       1796
  z_amb_out.txt                                                 27274
  z_classify.py                                                  3200
  z_classify.tsv                                                20645
  z_err.txt                                                         0
  z_f12.py                                                       2023
  z_f12b.py                                                      2024
  z_final.py                                                     1942
  z_inv.py                                                       1958
  z_inv2.py                                                      1646
  z_inv_list.txt                                                38569
  z_mem.py                                                       6514
  z_mem2.py                                                      5648
  z_memskill.py                                                  7248
  z_org_out.txt                                                     0
  z_organize.py                                                 12820
  z_punit.py                                                     3841
  z_readme.py                                                   15420
  z_recon.py                                                     2211
  z_status.py                                                    1818
```

### `02_doc_extract/`（一手文档抽取）

```
  _ch8.txt                                                      35996
  _feos_pdf_dump.txt                                           107210
  ch.txt                                                          762
  doc_misc.txt                                                  98065
  docx_extract.txt                                              61998
  enum_doc_matter.txt                                           42468
  extract_doc.py                                                 6090
  extract_legacy.py                                              5623
  fds_gui.txt                                                   17247
  legacy_doc.txt                                                14096
  legacy_doc_be.txt                                             25564
  legacy_doc_full.txt                                           30691
  pdf_extract.py                                                 1325
  seg.txt                                                        4368
  tbl.txt                                                        2218
  textdocs.txt                                                 101617
  toc.txt                                                        4905
  xlsx_extract.txt                                               8558
  docext/
  Atomic(LEDCOP)说明.txt                                          20640
  Hyades 数据格式说明.txt                                             16396
  Restart.txt                                                    5022
  legacy/
  Atomic(LEDCOP)不透明度格式说明.txt                                    22163
  Atomic(LEDCOP)说明.txt                                          38369
  GUI,IO相关.txt                                                  13160
  Hyades 数据格式说明.txt                                             28410
  MULTI使用的SESAME数据文件格式.txt                                       7607
  QuietStart.txt                                                 3190
  Restart.txt                                                   26289
  反弹冲击波的撞击壳的时刻.txt                                               1858
  多群辐射源(FDS).txt                                                 2091
  pdfext/
  2011(Chernogolovka)_Physics of Extreme States of matter_LIFETIME OF METASTABLE STATES IN ION-BEAM IRRADIATED SiO2 FOILS.txt      21849
  FEOS-Package-Documentation2012.txt                           101008
  FEOS-Package-Documentation2016.txt                           100684
  MPQeos-JWGU-Documentation.txt                                 48683
  Multi1D++ EOS and Opacity - FEOS程序说明.txt                      46354
  _sec10_15.txt                                                  6752
  _sec16.txt                                                    15360
```

### `03_anchors/`（实测锚点库）

```
  anchors.md                                                    66702
  build_anchors.py                                               5868
  find_anchors.py                                                 451
  sample_index.md                                                9359
```

### `04_probe/`（格式逆向探针）

```
  01_cst_and_noext/
  cst_inventory.json                                            12515
  noext_cst.py                                                   1714
  noext_inventory.json                                           6901
  out_01.txt                                                     7983
  out_02.txt                                                     4345
  out_03.txt                                                     9786
  out_04.txt                                                     5649
  out_05.txt                                                     5504
  out_06.txt                                                     2450
  out_07.txt                                                     1457
  out_08.txt                                                    14055
  out_09.txt                                                     2818
  out_10.txt                                                     5240
  out_11.txt                                                   107127
  out_12.txt                                                    14708
  out_13.txt                                                     3915
  out_14.txt                                                     5971
  out_14_log.txt                                                    9
  out_dummy.txt                                                    13
  probe_01_cst.py                                                2493
  probe_02_cst_cols.py                                           5347
  probe_03_structure.py                                          3124
  probe_04_blocks.py                                             3067
  probe_05_closure.py                                            2864
  probe_06_final_closure.py                                      2294
  probe_07_closure_exact.py                                      1316
  probe_08_noext.py                                              1826
  probe_10_docs.py                                               1849
  probe_11_stubs.py                                              3489
  probe_12_verify.py                                             6520
  probe_13_cst_equiv.py                                          5294
  probe_14_splitfix.py                                           2599
  probe_cst_noext.py                                             1438
  02_multigroup_planck/
  census_mg.tsv                                                 40317
  census_mg2.txt                                                87617
  multigroup_opacity_FINAL.md                                    9187
  multigroup_opacity_finding.md                                  7265
  my_groups_cmp.py                                               2331
  my_plancK_probe.py                                             1981
  my_planck_blocks.py                                            2061
  my_planck_close.py                                             1445
  my_planck_close2.py                                            1865
  my_planck_close3.py                                            2792
  my_planck_final.py                                             2110
  my_planck_groups.py                                            2035
  my_planck_groupsolve.py                                        1851
  my_planck_h.py                                                 2052
  my_planck_period.py                                            2148
  my_planck_recount.py                                           1877
  my_planck_seg.py                                               1716
  my_planck_solve.py                                             2236
  my_planck_struct.py                                            2051
  q_cards.py                                                     3766
  q_cards2.py                                                    4551
  q_cards2_out.txt                                              18420
  q_census.py                                                    3787
  q_census2.py                                                   3670
  q_opbe.py                                                      2062
  q_skel.py                                                      2196
  q_struct.py                                                    1785
  q_taxis.py                                                     3484
  q_zeff.py                                                      3292
  03_sesame/
  RECHECK_sesame.py                                              3428
  RECHECK_sesame.txt                                             3885
  _sesame_au.txt                                                 6155
  probe_sesame_E_P.py                                            3697
  probe_sesame_layout.py                                         3456
  probe_sesame_tail.py                                           2700
  sesame_dump.txt                                                9241
  sesame_extract.txt                                             7756
  v_sesame_confirm.py                                             950
  v_sesame_count.py                                               835
  v_sesame_solve.py                                              1267
  verify_sesame_list.py                                           451
  verify_sesame_semantics.py                                     2826
  04_feos/
  _dump_c20g.txt                                                14994
  al_feos_probe.out                                            192777
  dbg_feos.py                                                     548
  dbg_sio2.py                                                     495
  feos_src_adjudication.md                                      13769
  feos_src_q1.out.txt                                           40691
  feos_src_q1.py                                                 1943
  feos_src_q1b.out.txt                                           7493
  feos_src_q1b.py                                                5538
  feos_src_q2.out.txt                                           11117
  feos_src_q2.py                                                 5310
  feos_src_q4.out.txt                                            6016
  feos_src_q4.py                                                 9187
  probe_al_feos.py                                               2167
  probe_feos.py                                                   768
  probe_feos2.py                                                  986
  probe_feos3.py                                                  683
  verify_feos.py                                                 1567
  verify_feos2.py                                                1883
  verify_feos3.py                                                1057
  verify_feos4.py                                                1221
  verify_feos5.py                                                1074
  verify_feos6.py                                                 742
  05_hyades_ionmix/
  atomic_dump.txt                                               24021
  dataheaders.txt                                               73230
  dbg_cn4.py                                                      918
  hyades_doc.txt                                                18302
  list_hyades.py                                                  394
  probe_hyades.py                                                1108
  verify_hyades.py                                               2808
  06_general/
  _dump.py                                                        802
  _probe.py                                                       867
  _probe2.py                                                     1863
  _x.py                                                           951
  path_verify2.py                                                2864
  path_verify3.py                                                2522
  probe_anchors2.py                                              1188
  probe_manual_order.py                                          4582
  probe_tail2.py                                                 3528
  probe_tail3.py                                                 3941
  verify2.py                                                     2404
  verify3.py                                                      743
  verify4.py                                                     1722
  verify5.py                                                     1279
  verify6.py                                                     2035
  verify7.py                                                     1763
  probe_noext_agent/
  probe_noext_agent\probe_noext/
  align.py                                                       2297
  docsearch.py                                                   1630
  docsearch.txt                                                 58402
  enum_noext.py                                                  1386
  final_checks.py                                                2194
  groupA.py                                                      3800
  groupA10.py                                                    2774
  groupA11.py                                                    4067
  groupA12.py                                                    2000
  groupA13.py                                                    3474
  groupA14.py                                                    2593
  groupA15.py                                                    4033
  groupA2.py                                                     2226
  groupA3.py                                                     3246
  groupA4.py                                                     1938
  groupA5.py                                                     1639
  groupA6.py                                                     1811
  groupA7.py                                                     1824
  groupA8.py                                                     2665
  groupA9.py                                                     2824
  groupA_def.py                                                  2803
  groupA_final.py                                                2353
  groupA_final2.py                                               3355
  groupA_grids.json                                               989
  groupDE.py                                                     2893
  groupDE2.py                                                    2432
  groups.py                                                      3038
  groups_out.txt                                                31485
  hexA.py                                                         656
  ls01.py                                                         684
  ls02.py                                                         338
  noext_list.json                                                9718
  rest.py                                                        3055
  rest_out.txt                                                  14397
  selfcheck.py                                                   4107
  tk.py                                                          2379
  verify_last.py                                                 2570
```

### `04_probe/01_cst_and_noext/`（`.cst` 与无扩展名族）

```
  cst_inventory.json                                            12515
  noext_cst.py                                                   1714
  noext_inventory.json                                           6901
  out_01.txt                                                     7983
  out_02.txt                                                     4345
  out_03.txt                                                     9786
  out_04.txt                                                     5649
  out_05.txt                                                     5504
  out_06.txt                                                     2450
  out_07.txt                                                     1457
  out_08.txt                                                    14055
  out_09.txt                                                     2818
  out_10.txt                                                     5240
  out_11.txt                                                   107127
  out_12.txt                                                    14708
  out_13.txt                                                     3915
  out_14.txt                                                     5971
  out_14_log.txt                                                    9
  out_dummy.txt                                                    13
  probe_01_cst.py                                                2493
  probe_02_cst_cols.py                                           5347
  probe_03_structure.py                                          3124
  probe_04_blocks.py                                             3067
  probe_05_closure.py                                            2864
  probe_06_final_closure.py                                      2294
  probe_07_closure_exact.py                                      1316
  probe_08_noext.py                                              1826
  probe_10_docs.py                                               1849
  probe_11_stubs.py                                              3489
  probe_12_verify.py                                             6520
  probe_13_cst_equiv.py                                          5294
  probe_14_splitfix.py                                           2599
  probe_cst_noext.py                                             1438
```

### `04_probe/02_multigroup_planck/`（多群不透明度表）

```
  census_mg.tsv                                                 40317
  census_mg2.txt                                                87617
  multigroup_opacity_FINAL.md                                    9187
  multigroup_opacity_finding.md                                  7265
  my_groups_cmp.py                                               2331
  my_plancK_probe.py                                             1981
  my_planck_blocks.py                                            2061
  my_planck_close.py                                             1445
  my_planck_close2.py                                            1865
  my_planck_close3.py                                            2792
  my_planck_final.py                                             2110
  my_planck_groups.py                                            2035
  my_planck_groupsolve.py                                        1851
  my_planck_h.py                                                 2052
  my_planck_period.py                                            2148
  my_planck_recount.py                                           1877
  my_planck_seg.py                                               1716
  my_planck_solve.py                                             2236
  my_planck_struct.py                                            2051
  q_cards.py                                                     3766
  q_cards2.py                                                    4551
  q_cards2_out.txt                                              18420
  q_census.py                                                    3787
  q_census2.py                                                   3670
  q_opbe.py                                                      2062
  q_skel.py                                                      2196
  q_struct.py                                                    1785
  q_taxis.py                                                     3484
  q_zeff.py                                                      3292
```

### `04_probe/03_sesame/`（SESAME 族）

```
  RECHECK_sesame.py                                              3428
  RECHECK_sesame.txt                                             3885
  _sesame_au.txt                                                 6155
  probe_sesame_E_P.py                                            3697
  probe_sesame_layout.py                                         3456
  probe_sesame_tail.py                                           2700
  sesame_dump.txt                                                9241
  sesame_extract.txt                                             7756
  v_sesame_confirm.py                                             950
  v_sesame_count.py                                               835
  v_sesame_solve.py                                              1267
  verify_sesame_list.py                                           451
  verify_sesame_semantics.py                                     2826
```

### `04_probe/04_feos/`（FEOS / MPQeos 族）

```
  _dump_c20g.txt                                                14994
  al_feos_probe.out                                            192777
  dbg_feos.py                                                     548
  dbg_sio2.py                                                     495
  feos_src_adjudication.md                                      13769
  feos_src_q1.out.txt                                           40691
  feos_src_q1.py                                                 1943
  feos_src_q1b.out.txt                                           7493
  feos_src_q1b.py                                                5538
  feos_src_q2.out.txt                                           11117
  feos_src_q2.py                                                 5310
  feos_src_q4.out.txt                                            6016
  feos_src_q4.py                                                 9187
  probe_al_feos.py                                               2167
  probe_feos.py                                                   768
  probe_feos2.py                                                  986
  probe_feos3.py                                                  683
  verify_feos.py                                                 1567
  verify_feos2.py                                                1883
  verify_feos3.py                                                1057
  verify_feos4.py                                                1221
  verify_feos5.py                                                1074
  verify_feos6.py                                                 742
```

### `04_probe/05_hyades_ionmix/`（Hyades / IONMIX 族）

```
  atomic_dump.txt                                               24021
  dataheaders.txt                                               73230
  dbg_cn4.py                                                      918
  hyades_doc.txt                                                18302
  list_hyades.py                                                  394
  probe_hyades.py                                                1108
  verify_hyades.py                                               2808
```

### `04_probe/06_general/`（通用探针）

```
  _dump.py                                                        802
  _probe.py                                                       867
  _probe2.py                                                     1863
  _x.py                                                           951
  path_verify2.py                                                2864
  path_verify3.py                                                2522
  probe_anchors2.py                                              1188
  probe_manual_order.py                                          4582
  probe_tail2.py                                                 3528
  probe_tail3.py                                                 3941
  verify2.py                                                     2404
  verify3.py                                                      743
  verify4.py                                                     1722
  verify5.py                                                     1279
  verify6.py                                                     2035
  verify7.py                                                     1763
```

### `04_probe/probe_noext_agent/`（代理 probe-noext 作业目录）

```
  probe_noext/
  align.py                                                       2297
  docsearch.py                                                   1630
  docsearch.txt                                                 58402
  enum_noext.py                                                  1386
  final_checks.py                                                2194
  groupA.py                                                      3800
  groupA10.py                                                    2774
  groupA11.py                                                    4067
  groupA12.py                                                    2000
  groupA13.py                                                    3474
  groupA14.py                                                    2593
  groupA15.py                                                    4033
  groupA2.py                                                     2226
  groupA3.py                                                     3246
  groupA4.py                                                     1938
  groupA5.py                                                     1639
  groupA6.py                                                     1811
  groupA7.py                                                     1824
  groupA8.py                                                     2665
  groupA9.py                                                     2824
  groupA_def.py                                                  2803
  groupA_final.py                                                2353
  groupA_final2.py                                               3355
  groupA_grids.json                                               989
  groupDE.py                                                     2893
  groupDE2.py                                                    2432
  groups.py                                                      3038
  groups_out.txt                                                31485
  hexA.py                                                         656
  ls01.py                                                         684
  ls02.py                                                         338
  noext_list.json                                                9718
  rest.py                                                        3055
  rest_out.txt                                                  14397
  selfcheck.py                                                   4107
  tk.py                                                          2379
  verify_last.py                                                 2570
```

### `05_cross_validation/`（交叉验证与仲裁）

```
  DELIVERABLES.txt                                               1292
  arb2.py                                                        1743
  arb3.py                                                        1697
  arb_au.py                                                      1375
  arbitration.md                                                 6781
  check_deliverables.py                                          1064
  cov_inventory.log                                               490
  cov_inventory.py                                              16419
  cov_summary.log                                                 199
  cov_summary.py                                                 6854
  coverage_counts.txt                                          107623
  coverage_matrix.tsv                                          181284
  coverage_records.json                                        347566
  coverage_summary.md                                           10908
  cross_validation.md                                           22153
  cross_validation_round2.md                                    15008
  cst_naming_finding.md                                          5722
  eos_final.py                                                   9796
  eos_readers.py                                                11563
  multigroup_opacity_finding.md                                  7265
  unknown_files.txt                                              4885
  verdictB.txt                                                   2403
  verdictB2.txt                                                  2726
  xv2_multi.log                                                   206
  xv2_multi.py                                                  14058
  xv2b.log                                                        197
  xv2b_probe_cst.py                                              7170
  xv2b_probe_cst.txt                                             4157
  xv2c.log                                                        206
  xv2c_final.py                                                 14103
  xv2d.log                                                        209
  xv2d_unit_probe.py                                             5451
  xv2d_unit_probe.txt                                             651
  xv2e.log                                                         63
  xv2e_ist_exact.py                                              3399
  xv2e_ist_exact.txt                                             3243
  xv2f.log                                                        204
  xv2f_unit_final.py                                             7724
  xv2f_unit_final.txt                                            6848
  xval_s10.log                                                    172
  xval_s10.py                                                    3450
  xval_s10.txt                                                   5401
  xval_s11.log                                                    173
  xval_s11.py                                                    3391
  xval_s11.txt                                                  15402
  xval_s12.log                                                    172
  xval_s12.py                                                    3282
  xval_s12.txt                                                   5758
  xval_s13.log                                                    172
  xval_s13.py                                                    2534
  xval_s13.txt                                                   2575
  xval_s14.log                                                    172
  xval_s14.py                                                    6336
  xval_s14.txt                                                   5130
  xval_s1_inventory.py                                           5797
  xval_s1_inventory.txt                                         49993
  xval_s1b_files.py                                              2416
  xval_s1b_files.txt                                           117955
  xval_s1c_names.py                                              1231
  xval_s1c_names.txt                                            18225
  xval_s2_closure.py                                             9701
  xval_s2_closure.txt                                           43639
  xval_s2b_proof.py                                              7704
  xval_s2b_proof.txt                                             9862
  xval_s4.log                                                     172
  xval_s4.py                                                     5417
  xval_s4.txt                                                   17144
  xval_s5.log                                                     172
  xval_s5.py                                                     4026
  xval_s5.txt                                                   14647
  xval_s6.log                                                     172
  xval_s6.py                                                     2496
  xval_s6.txt                                                   11220
  xval_s7.log                                                     171
  xval_s7.py                                                     2701
  xval_s7.txt                                                    7707
  xval_s8.log                                                     171
  xval_s8.py                                                     3604
  xval_s8.txt                                                    5596
  xval_s9.log                                                     171
  xval_s9.py                                                     4517
  xval_s9.txt                                                    4598
```

### `06_agent_reports/`（代理产出报告）

```
  _w7.txt                                                       11616
  _wv2_idx.txt                                                  12019
  explore_multi_formats.md                                      41045
  explore_python_support.md                                     34300
  feos_formats.md                                               72531
  formats_from_source.md                                        41191
  formats_resolved.md                                           47797
  missed_dirs.md                                                62259
  naming_cst_formats.md                                         23426
  noext_formats.md                                              46213
  src_doc_aux.md                                               261701
  src_doc_core.md                                              441912
  src_doc_tables.md                                             24176
  src_doc_tree.md                                               11184
  src_ionmix_snop.md                                            56329
  src_sesame_ledcop.md                                          49411
  web_verify.md                                                 11396
  web_verify2.md                                                61669
```

### `07_doc_build/`（文档生成与打补丁）

```
  _appE.txt                                                      2975
  add_tnums.py                                                   3502
  appF.txt                                                       9897
  app_tables.py                                                  1423
  append_mem.py                                                  8163
  empty_s1.py                                                     809
  find_real.py                                                   1207
  fix_paths_scan.py                                              3468
  fix_sec_refs.py                                                2712
  merge_doc.py                                                   3090
  new_145.md                                                    14257
  p10_tail.py                                                    3073
  p11_fix145.py                                                  7986
  p12_sync.py                                                    8931
  p13_feos_fix.py                                               10698
  p14_close.py                                                   1289
  p15_restore.py                                                 4073
  p1_add145.py                                                  11781
  p1_ctx.py                                                       621
  p1_fix.py                                                       850
  p1_scan.py                                                     1031
  p2_fix14_159.py                                                6538
  p3_add_1514_appB.py                                           16555
  p4_errata.py                                                   7603
  p5_appE_F.py                                                   7886
  p6_frontmatter.py                                              7979
  p7_reorder.py                                                  7043
  p7b_reorder.py                                                 5160
  p8_fixorder.py                                                 3825
  p9_final_fixes.py                                              9147
  patch_1006.py                                                 26771
  patch_1512.py                                                  7974
  patch_appB.py                                                  7099
  patch_appB2.py                                                 9637
  patch_appF.py                                                  9565
  patch_body.py                                                 12958
  patch_ch15.py                                                  4893
  patch_cleanup.py                                               4958
  patch_final.py                                                 2561
  patch_reindex.py                                               1713
  patch_rules.py                                                 4215
  plan_multi_doc.md                                             37843
  multi_doc_parts/
  00_front.md                                                   22764
  10_ch0.md                                                     33396
  11_ch1.md                                                     48858
  12_ch2.md                                                     47712
  13_ch3.md                                                     44646
  14_ch4.md                                                     55023
  15_ch5.md                                                     49371
  16_ch6.md                                                     20764
  17_ch7.md                                                     52202
  18_ch8.md                                                     32959
  19_ch9.md                                                     49986
  20_ch10.md                                                    41750
  21_ch11.md                                                    39065
  22_ch12.md                                                    44367
  23_ch13.md                                                    30175
  24_ch14.md                                                    35968
  30_appendix.md                                                43472
  parts/
  new_ch15.md                                                   59028
```

### `08_audit/`（审计与核查）

```
  DEBUG_paths.py                                                 1574
  DEBUG_paths.txt                                                 841
  audit.py                                                       3108
  audit.txt                                                      3614
  auditA.py                                                      3337
  auditB.py                                                      2722
  auditB2.py                                                     4016
  auditB2.txt                                                   48287
  auditB3.py                                                     3297
  auditB3.txt                                                    5469
  auditB4.py                                                     3497
  auditB4.txt                                                    2704
  auditB5.py                                                     3530
  auditB6.py                                                     3344
  auditB7.py                                                     3119
  auditB_final.txt                                               5804
  auditCDE.py                                                    6444
  auditCDEF.txt                                                 28872
  auditF.py                                                      3041
  auditF.txt                                                     2533
  audit_BCDEF.txt                                               10732
  audit_raw.txt                                                128063
  audit_report.md                                               29816
  audit_report2.md                                              30087
  audit_round3.py                                                9781
  audit_round3.txt                                               5527
  audit_v2.py                                                    7738
  audit_v2.txt                                                   3515
  audit_v3.py                                                    8421
  audit_v3.txt                                                   3307
  chk15.py                                                        242
  chk3.py                                                        1324
  chk_app_ctx.py                                                  487
  chk_internal_sec.py                                            1242
  chk_sec.py                                                      467
  chk_tail.py                                                     533
  count_cjk.py                                                    363
  diag2.py                                                        990
  diag3.py                                                        960
  diag4.py                                                        568
  doc_conventions.md                                             6498
  final.txt                                                       944
  verify_cn.py                                                   2105
  verify_cn4.py                                                  1907
  verify_cnr.py                                                   948
  verify_cnr2.py                                                 1056
  verify_cnr3.py                                                 1752
  verify_cnr4.py                                                 1598
  verify_cnr5.py                                                 1190
  verify_cnr6.py                                                 1299
```

### `09_source_verify/`（源码级核验与官方包）

```
  _cases.py                                                      1503
  _tft.py                                                        1941
  dl_feos.py                                                     3137
  dl_ionmix.out                                                  1203
  dl_ionmix.py                                                   2455
  inspect_data.out                                              18160
  inspect_data.py                                                1300
  vendor/
  FEOS.tar.gz                                                  777814
  FEOS_inner.tar.gz                                            777639
  vendor\FEOS_extract/
  FEOS.tar.gz                                                  777639
  vendor\FEOS_extract\inner/
  vendor\FEOS_extract\inner\FEOS/
  vendor\FEOS_extract\inner\FEOS\Code/
  COMMON-00_DEFINITS.H                                           4316
  COMMON-01_UTILITIES.C                                         15791
  COMMON-01_UTILITIES.H                                          1794
  COMMON-02_READFILE.C                                          15502
  COMMON-02_READFILE.H                                           1752
  FE-00_DEFINITS.H                                                946
  FE-01_TABTOOLS.C                                              32756
  FE-01_TABTOOLS.H                                               1408
  FE-02_CALCULATIONS.C                                           8691
  FE-02_CALCULATIONS.H                                           1461
  FE-03_MAIN.C                                                  16543
  LIB-00_DEFINITS.H                                              2080
  LIB-01_TF_SERVICES.C                                          15267
  LIB-01_TF_SERVICES.H                                           1270
  LIB-02_TF_TABLE.H                                             16252
  LIB-02_TF_TABLE_1.C                                           14449
  LIB-02_TF_TABLE_2.C                                           12981
  LIB-03_TF_MIXTURE.C                                            7829
  LIB-03_TF_MIXTURE.H                                            2051
  LIB-04_IONMOD.C                                               12136
  LIB-04_IONMOD.H                                                2211
  LIB-05_EOS_SERVICES.C                                          8252
  LIB-05_EOS_SERVICES.H                                          2869
  LIB-06_MAXWELL.C                                              21394
  LIB-06_MAXWELL.H                                               2399
  LIB-07_C_INTERFACE.C                                          16225
  LIB-08_FORTRAN_INTERFACE.C                                     9015
  Makefile                                                       3264
  SE-00_DEFINITS.H                                               1578
  SE-01_READTABLE.C                                             16466
  SE-01_READTABLE.H                                               865
  SE-02_INTERPOLTOOLS.C                                          3081
  SE-02_INTERPOLTOOLS.H                                          1100
  SE-03_SERVICES.C                                              31550
  SE-03_SERVICES.H                                               2171
  SE-04_MAIN.C                                                   5192
  libfeos.h                                                      1923
  vendor\FEOS_extract\inner\FEOS\Documents/
  FEOS-Package-Documentation.pdf                               611826
  FEOS-Package-Documentation.txt                                99338
  Info.txt                                                       2475
  License.txt                                                   28360
  vendor\FEOS_extract\inner\FEOS\EOS-Data/
  Al.par                                                         6531
  FEOS_Material-DB.dat                                           7723
  FEOS_TF-Table_1197.dat                                       567342
  SiO2.par                                                       6530
  vendor\FEOS_src/
  vendor\FEOS_src\FEOS/
  vendor\FEOS_src\FEOS\Code/
  COMMON-00_DEFINITS.H                                           4316
  COMMON-01_UTILITIES.C                                         15791
  COMMON-01_UTILITIES.H                                          1794
  COMMON-02_READFILE.C                                          15502
  COMMON-02_READFILE.H                                           1752
  FE-00_DEFINITS.H                                                946
  FE-01_TABTOOLS.C                                              32756
  FE-01_TABTOOLS.H                                               1408
  FE-02_CALCULATIONS.C                                           8691
  FE-02_CALCULATIONS.H                                           1461
  FE-03_MAIN.C                                                  16543
  LIB-00_DEFINITS.H                                              2080
  LIB-01_TF_SERVICES.C                                          15267
  LIB-01_TF_SERVICES.H                                           1270
  LIB-02_TF_TABLE.H                                             16252
  LIB-02_TF_TABLE_1.C                                           14449
  LIB-02_TF_TABLE_2.C                                           12981
  LIB-03_TF_MIXTURE.C                                            7829
  LIB-03_TF_MIXTURE.H                                            2051
  LIB-04_IONMOD.C                                               12136
  LIB-04_IONMOD.H                                                2211
  LIB-05_EOS_SERVICES.C                                          8252
  LIB-05_EOS_SERVICES.H                                          2869
  LIB-06_MAXWELL.C                                              21394
  LIB-06_MAXWELL.H                                               2399
  LIB-07_C_INTERFACE.C                                          16225
  LIB-08_FORTRAN_INTERFACE.C                                     9015
  Makefile                                                       3264
  SE-00_DEFINITS.H                                               1578
  SE-01_READTABLE.C                                             16466
  SE-01_READTABLE.H                                               865
  SE-02_INTERPOLTOOLS.C                                          3081
  SE-02_INTERPOLTOOLS.H                                          1100
  SE-03_SERVICES.C                                              31550
  SE-03_SERVICES.H                                               2171
  SE-04_MAIN.C                                                   5192
  libfeos.h                                                      1923
  vendor\FEOS_src\FEOS\Documents/
  FEOS-Package-Documentation.pdf                               611826
  Info.txt                                                       2475
  License.txt                                                   28360
  vendor\FEOS_src\FEOS\EOS-Data/
  Al.par                                                         6531
  FEOS_Material-DB.dat                                           7723
  FEOS_TF-Table_1197.dat                                       567342
  SiO2.par                                                       6530
```

**合计：724 个文件 / 13979801 字节。**

## 4. 复现约定

### 4.1 解释器（必须用托管 venv）

```
C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe
```

### 4.2 数据根（所有探针的相对基准）

```
src/Multi1D++Portable20241128/
```

### 4.3 环境陷阱（本机 bash shim 缺 coreutils）

shim 缺 `dirname` / `cd` / `head` / `tail` / `ls` / `grep` / `cp` / `rm` / `find`，
且**内联 `python -c` 会被二次解释**（含引号/花括号/中文标点必然出错）。
**结论：一律先写 `.py` 脚本文件，再用解释器执行。**

另注：环境对 `shutil.rmtree` 有 safe-delete 拦截，脚本**不得删除目录**；
复制时用 `shutil.copytree(..., dirs_exist_ok=True)` 实现幂等。

### 4.4 重跑文档装配与核查

```bash
# 1) 结构补丁（幂等，可重复执行；每个脚本内含 count 断言防误改）
python 07_doc_build/p7_fixorder.py        # 编号顺序修正
python 07_doc_build/p9_final_fixes.py     # 表号唯一性等
# 2) 质量核查
python 08_audit/audit_v3.py               # 输出 audit_v3.txt
```

## 5. 归档约定（后续新文件请遵守）

1. **探针/诊断脚本** → 归入 `04_probe/<相应族>/`；跨族者入 `04_probe/06_general/`。
2. **文档补丁脚本** → `07_doc_build/`，命名 `p<序号>_<主题>.py`；
   必须**幂等**且用 `count` 断言而非 `replace` 静默替换。
3. **核查脚本** → `08_audit/`，命名 `audit_v<n>.py`，报告落同名 `.txt`。
4. **中间输出/原始 dump** → **与产生它的脚本同目录**，不单独建 dump 目录。
5. **代理交付报告** → `06_agent_reports/`，文件名保持代理原始命名以便追溯。
6. **含凭据、绝对临时路径、一次性调试残留**者**不入库**。

---

## 6. 关键结论索引（本库支撑的核心成果）

| 结论 | 主要支撑文件 |
|---|---|
| 无扩展名多群不透明度表（150 文件）记录结构 7/7 闭合 | `04_probe/02_multigroup_planck/`、文档 §14.5 |
| `.cst` 双变体（德 23 / 英 1）与 `-1.#INF00e+000` 处理 | `04_probe/01_cst_and_noext/`、文档 §15.14.2 |
| `.sesame` 尺寸公式 `4+2nr+ne+2nr·ne` 与首字段哨兵 | `04_probe/03_sesame/`、文档 §15.2.6 |
| 记账文件 `CHECKSUM` = (SysV-16, BSD-16) | 文档 §15.14.3、附录 B.23 |
| `.feos` 四列单位与 `write_Rostock_format` 源码明文 | `09_source_verify/vendor/FEOS_src/FEOS/Code/FE-01_TABTOOLS.C` |
| 同材料跨格式一致性（密度网格逐位一致） | `05_cross_validation/xval_s2_closure.txt` |
| 代理"`.sesame` 公式全错"指控为假阳性 | `05_cross_validation/arbitration.md`、`v_sesame_solve.py` |
