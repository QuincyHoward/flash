# eosop_pro 文档

> `Multi1D++Portable20241128/matter++` 的 EOS / 不透明度数据 → 统一解析 → 统一网格 → HDF5
>
> **闸口**：`已解析 992 + 已跳过 222 == 1214`，问题文件 **0**，耗时 144.7 s
> **交叉验证**：`identify` 比对 997 个文件 → `conflict` **0**（首轮 10 → 修掉 7 处缺陷）
> **下游**：`convert-all` 写出 992 个 h5 / 335.3 MiB / 0 失败
> **测试**：`all tests passed across 51 file(s)`（2026-09-15 复跑，无回归；含新增
> `test/eosopdata/` 材料测试套件 —— `step01_cn4/`（提取/彩图/路径 79，彩图含
> nion-T / **ne-T / rho-T 双坐标**）+
> `step02_families/`（11 族提取 26 / 彩图 15 / 物理路径 18 / 两重认证守护 7 /
> **逐类型批量出图 `test_plot_<type>.py` × 11（33，含 source_data 副本守护）**）+
> `step03_transcn4/`（跨族转 cn4 + NaN 占位 44））
> 与 `test/io/test_convert_default.py`（convert 默认目标 cn4，11）；
> **产物跟测试走**：各 step 文件夹内 `_out/`（图/cn4 产物/test_log.txt，已 gitignore））
> **统一绘图模块**：`plotting/gridmap.py` —— 任意族 ParsedTable 批量出图 +
> `_report.txt` 核查报告（网格点/物理意义/单位/认证标记）；**标记规约**
> （2026-09-15 第二次裁定：**标记只有 `uk`/`uv` 两个**）：`uk` = 无来源
> 确认（无可指认的文献/文档/文件内声明）、`uv` = 未人工核查；有源且
> 已人工核查则**标记整体省略**（当前仅 cn4）。报告行写 `tags=uk,uv` /
> `tags=uv`（全通过省略该键），图上 colorbar/**x/y 轴**写
> `Name (unit, <tags>)`（全通过只写 `Name (unit)`）。**来源规约**
> （2026-09-15 补充裁定）：字典条目带 `kind` 来源类型（文件内声明 /
> 一级说明文档 / 源码行号 / 派生公式 / none）与长文本 `source`
> （一级出处原文摘录，**不得**引用中间产物 docs/20 手册）。有源白名单
> = cn4 全部（abjt_03.f + 指南）+ 一级文档条目：multi_inverted_eos
> 全部、multi_opacity 的 rho/Te/kappa、hyades_*/sesame_dat 的
> rho/Te/P/E/kappa、mpqeos 的 rho/Te/P/E、ledcop_zeff 的 rho/Te、
> snop_input 全部（SNOP.MANUAL）+ 文件内声明条目：ledcop_atomic 的
> rho/Te/Ross/Planck、coldopacity 的 Eph/miu/"*"、hugoniot 全部 +
> 派生轴 n_e（code-derived）；其余条目 `uk`（无一级出处，如实登记）；
> **控制字典**：`registry/field_checks.py`（eosop 家族唯一权威，未来
> 未知格式经 `register_family` 注册即可被绘图/分析链路采用）；字典
> Markdown 全文 `docs/eosop变量控制字典.md`（与字典逐字同步，测试守护，
> `python -m eosop_pro.registry.field_checks` 再生成）；**raw 兜底规约**：语义映射不可行的
> 字段画 `raw values vs element index` 序列图（数值可读即可画，标注
> semantics unknown），不再静默零图；**原始数据跟图走**：每族处理前 3 个
> 可解析文件，源文件复制到 `<type>/_out/source_data/`（核查对照）
> **已知诚实边界**：feos_native 全树 29 个 `.feos` payload 不可解码（列语义无法
> 从 PDF 文档恢复）—— 带物理语义的场彩图仍不可能，raw 序列图照出（契约锁定测试）
> **跨格式互转**：`convert` 注册表已含 **cn4（默认目标）** / multi_opacity / hyades_eos /
> multi_inverted_eos / h5 —— `convert(t, out)` 默认出 cn4，`target=...` 可指定其他
> **本地 git**：已提交 151 文件 / 27142 行（分支 main，提交 b3f1df6）；Gitee 推送见 [18](18_Gitee推送.md)

---

## 快速导航

| # | 文档 | 一句话 |
|---|---|---|
| 01 | [总览](01_总览.md) | 项目定位、目录、模块地图、命令矩阵、实测数字 |
| 02 | [两段式执行](02_两段式执行.md) | **声明优先 + 内容兜底**的契约与闸口 |
| 03 | [注释证据通道](03_注释证据通道.md) | 伴随文件/内联声明的索引、四级单位仲裁 |
| **20** | [**格式规格与物理量单位手册**](20_格式规格与物理量单位手册.md) | ★★ **F1~F6 全部格式规格 + 逐族逐量单位 + 「溯源文档 → 实现脚本」双字段溯源；8 处 `unknown` 不猜**（原 04~09 与两份单位文档已合并至此） |
| 10 | [纯文本提取规范](10_纯文本提取规范.md) | ★ 编码链、定宽、打包负号、注释剥离 |
| 11 | [通用识别协议](11_通用识别协议.md) | ★ 给任意格式文件，我怎么识别并提取 |
| 12 | [HDF5 模式](12_HDF5模式.md) | 双轨（native 逐字 + unified 插值） |
| 13 | [统一网格与插值](13_统一网格与插值.md) | `(rho,Te)` / `(nion,Te)`；F1 需先反演 |
| 14 | [审计报告](14_审计报告.md) | 三份报告的字段与"报告即接口" |
| 15 | [单位换算](15_单位换算.md) | ★ 四个族的四种单位；四级仲裁链 |
| 16 | [Z̄ 数据源盘点](16_Zeff盘点.md) | 九种来源、覆盖 130/251、单位 0 存疑 |
| 17 | [文档抽取](17_文档抽取.md) | doc/docx/pdf/xmind → 纯文本；「文档 vs 数据」闸门 |
| 18 | [Gitee 推送](18_Gitee推送.md) | 本地仓库已提交；远端推送的凭据作用域诊断与三条路径 |

> 📦 原 `04~09_格式规格_F*.md`、`SUPPORTED_TYPES_AND_UNITS.md`、
> `各种类型的eosop数据物理量及其单位说明.md` 共 8 份已**合并**为 [20](20_格式规格与物理量单位手册.md)，
> 原文移至 [`archive/`](archive/) 保留备查。

★ 标记的是**先读这几篇就够了**；其余按需查。

---

## 三个常见问题

**Q：某个后缀是什么数据？**
→ 查 [20 格式规格与物理量单位手册](20_格式规格与物理量单位手册.md) §1 总览表，
或直接跑

```bash
python -m eosop_pro.cli parse <matter++ 相对路径>
```

**Q：我要加一个新格式怎么办？**
→ [10 纯文本提取规范](10_纯文本提取规范.md) 定字节/定宽层，
然后照 [20 §8](20_格式规格与物理量单位手册.md) 的"处理哲学"决定诚实等级，
最后在 `registry/declared_types.py` 的 `EXT_MAP` / `NAME_FAMILY_TOKENS` 挂钩。

**Q：我怎么知道结论可不可信？**
→ 每条结论都能追到三处：
① `outputs/reports/*.md` 里的原始表头文本；
② `docs/extracted/*.txt` 里的规格原文；
③ h5 的 `layout_rule` / `unit_source` 属性字符串。

---

## 产物在哪

| 目录 | 内容 |
|---|---|
| `outputs/reports/` | audit / inventory / convert_all / plot_all / zeff / identify 报告（每次运行带时间戳） |
| `outputs/h5/` | 双轨 HDF5 |
| `outputs/plots/` | QA 图（全英文，DPI ≥ 450，字号 > 18 pt） |
| `outputs/logs/` | 运行日志 |
| `docs/extracted/` | 上游说明书抽取出的纯文本 + `MANIFEST.md` |

---

## 一键运行

```bat
eosop_pro\scripts\env_setup.bat      :: 建 venv 装依赖
eosop_pro\scripts\run_all.bat        :: 全流程 9 步（含测试）
```

单步：`01_extract_docs.bat` … `09_infer_unknown.bat`（双击即可）。

---

## 文档写作约定

本套文档（18 篇）遵循三条自定纪律：

1. **每条规格都标出处**。格式描述尽量逐字引用上游文档，
   并给出 `docs/extracted/` 里的文件名。
2. **实测数字优先于描述**。写"391 个文件"而不是"很多文件"；
   写"115.9 s"而不是"较快"。
3. **不确定就写不确定**。`ok_unverified` / `raw_values` / "列序待定" /
   `⚠️ 单位存疑` 这些状态在文档里都**如实呈现**，
   不粉饰成"已完成"。
