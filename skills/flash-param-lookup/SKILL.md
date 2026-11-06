---
name: flash-param-lookup
description: 联网查询 FLASH4.8 官方 runtime parameters 文档（Flash Center rpDoc）：本地 4050 参数离线索引 + 在线抓取完整定义（类型/默认值/Valid Values/完整说明）。遇到不认识的 FLASH 参数需要权威定义解释、确认默认值与取值范围、核对 .par 参数拼写时使用。触发词：这个参数是什么意思、参数定义、默认值、Valid Values、rpDoc、参数查询、不认识的参数、ed_/gr_/rt_/dr_/io_/eos_/hx_/op_ 参数。
---

> 最后核对：2026-11-06 · commit 0937198
> 索引来源：Flash Center rpDoc_4p8（抓取 2026-11-06，4050 参数 / 333 模块，抽验通过）

# FLASH 官方运行参数联网查询（flash-param-lookup）

## 适用场景

- 遇到不认识的 FLASH runtime 参数（.par 文件、报错信息、上游代码中出现的 `dtmax`、`rt_mgdFlMode`、`hx_dtFactor` 等），需要**权威定义/默认值/合法取值**
- 本地 `flash-knowledge`、`docs/reference/param_index_flash48.md`（精编 ~150 条）未覆盖的参数
- 批量核对 .par 参数拼写（官方参数名全集在本仓索引内）

## 前置条件

- 在线全文查询需网络可达 `flash.rochester.edu`；离线场景用本地索引（仅类型/默认值/描述首行）

## 操作步骤

### 1. 离线快速查（第一步，先查本地索引）

```bash
# 精确查参数（类型/默认值/描述首行）
grep -P "\tdtmax\t" skills/flash-param-lookup/references/param_index.tsv

# 前缀模糊查（如所有 rt_mgd* 参数）
grep "rt_mgd" skills/flash-param-lookup/references/param_index.tsv

# 按模块浏览（如 Laser 单元全部 428 个参数）
grep "^physics/sourceTerms/EnergyDeposition.*Laser" skills/flash-param-lookup/references/param_index.tsv
```

列格式：`module → name → type → default → valid_values → desc_first_line`（TSV，注释行以 `#` 开头）。

### 2. 在线抓取完整定义（本地索引不够时）

```bash
# ① 下载官方全文（~500KB，HTML 包裹 <pre> 纯文本）
curl -sL "https://flash.rochester.edu/site/flashcode/user_support/rpDoc_4p8.py?submit=rpDoc.txt" -o /tmp/rpDoc_4p8.txt

# ② 提取某参数的完整条目（含 Valid Values 与全部说明行）
awk '/^    eosMode \[/{f=1} f && /^    [A-Za-z_]+ \[[A-Z]+\]/ && !/^    eosMode \[/{f=0} f && /^[^ ]/{f=0}' /tmp/rpDoc_4p8.txt
```

也可用 WebFetch 抓取同一 URL 并附参数名提问，但内容经摘要，**精确默认值/取值以 curl 原文为准**。

### 3. 索引再生成（官方文档更新时）

重复本节 ① 下载后，用解析脚本重建 TSV：条目正则 `^    (\S+) \[([A-Z]+)\] \[(.+?)\]$`（4 空格缩进），模块头为顶格行，`Valid Values:` 行单独成列，首个其余缩进行作为描述首行。参考 `references/param_index.tsv` 头部注释。

## 护栏与铁律

1. **官方默认 ≠ 本仓推荐**：rpDoc 默认值是 FLASH 全局缺省；本仓 HEDP/SNB 场景有明确铁律（如 `gr_hypreUseFloor` 官方默认 TRUE，**本仓必须 FALSE**；`diff_thetaImplct` LaserSlab 用 1.0）。场景取值以 `flash-pitfalls` / `flash-knowledge` / `flash-scenario-setup` 为准，rpDoc 只回答"官方定义是什么"。
2. **setup 变量不在 rpDoc**：`ed_maxBeams/ed_maxPulses/RayCount`、`mgd_meshgroups`、`+ug` 等是 setup 编译期变量（须 setup+make），rpDoc 只收 runtime 参数。区分方法：查本索引查不到 → 大概率是 setup 变量 → 查 `flash-knowledge`。
3. **同名参数多模块**：如 `eosMode` 在 `Grid/GridMain` 与 Eos 单元各有一条，提取时会全部输出——注意区分模块归属。
4. **下标参数**：`ed_gaussianExponent_<i>`、`rt_mgdBounds_<g>` 等按序号展开，查下标 1 即可代表该族；索引中是逐个展开的（如 `_1.._20`）。
5. 本仓**不分发 FLASH 源码/EOS 表**（License §3）：rpDoc 是 Flash Center 公开参数文档，本地仅存元数据索引（名/类型/默认值/首行摘要）+ 在线抓取方法，全文不入 git。
6. `4p8` 对应 FLASH 4.8；换版本时 URL 中的版本号同步更换并重建索引。

## 常见坑

- rpDoc 页面是 HTML 包 `<pre>`，直接对整页 grep 会混入导航 HTML；先落盘再按 `^    <参数名> \[` 锚定条目
- `Valid Values: Unconstrained` 表示无枚举限制，不是"任意值都物理合理"
- 默认值含 Fortran 字面量（如 `-HUGE(1.0)`、`1.E5`），写 .par 时须换成十进制实数
- 参数语义与单位坑（波长 μm 不是 cm 等）见 `flash-knowledge` laser 单元——rpDoc 不重复该经验

## 关联资源

- `references/param_index.tsv` — 4050 参数离线索引（2026-11-06 抓取）
- `docs/reference/param_index_flash48.md` — 本仓精编参数索引（~150 条高频参数 + setup 相关性）
- `flash-knowledge`（参数物理语义/源码原理）、`flash-pitfalls`（报错→参数根因）、`docs/par_format_guide.md`（.par 排版）
- 官方 URL：`https://flash.rochester.edu/site/flashcode/user_support/rpDoc_4p8.py?submit=rpDoc.txt`
