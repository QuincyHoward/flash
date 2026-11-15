> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

# core/infer/ —— 盲读推断（阶段 B）：结构反演 + 自洽性验证

core 的语义层：把表头整数当未知量，用「计数守恒 × 单调 × 包络」求解布局。
立场：**不做格式清单匹配，做结构反演**——已知格式只是先验，最终由数值证据
定案；结论三态 ok / ambiguous / unrecognized，多解并列交人工、绝不静默挑一个。
依赖 `core.numbers`、`core.profile`、`core.text`、`core.config`；guess 另用 numpy。

## 模块

### inference.py
通用布局反演（④）。对 k=1..4 个前导行逐个假设为表头并分别反演（F1/F2/F4
表头是纯数字，按字母找文本头找不到）；对每个 (维度候选 × 布局模板) 解计数
方程，只有精确整数解才保留；校验前两个 segment 网格严格单调、量级落在物理包络。

关键 API：
- `infer_layout(lines, *, declared_families=(), env=None, max_dim_candidates=12) -> InferenceResult` —— 主入口；表头/payload 分界本身也是未知量
- `infer_file(path, **kw) -> InferenceResult` —— 文件版便捷封装
- `split_by_template(values, tmpl, d1, d2, ng=1) -> list[tuple[int, ...]] | None` —— 按模板切分数值下标；长度不符返回 None
- `TEMPLATES` —— 8 个布局模板（f2_gray / f2_multigroup / ledcop_split / f1_with_e0 / f1_no_e0 / hyades_eos / mpqeos / grids_only）
- `InferenceResult` —— 反演结果（status/best/candidates/header_nums/dim_candidates/profile/columns；`ok`、`report()` 完整反演报告）
- `LayoutCandidate` —— 自洽布局解（template/d1/d2/ng/monotonic/in_envelope/exact/score；`describe()`）

### envelope.py
物理包络与单位裁决（⑤）—— 自洽性校验最后一关。阈值全部来自 config、显式
可配并在报告中打印；越界只标 suspect 不改数据。诚实声明：这些阈值是预设的，
不是物理定律。

关键 API：
- `check_values(axes=None, fields=None, *, envelope=None, log10_flags=None) -> EnvelopeCheck` —— 校验轴/场量级是否落在包络内；`log10_flags` 标记 log10 存储的量（先 10** 还原再比）
- `Envelope` —— 一组包络阈值（rho∈[1e-8,1e6] g/cm³、Te∈[1e-2,1e6] eV、P∈[1e-12,1e12] Mbar；`describe()`）
- `DEFAULT_ENVELOPE` —— 默认包络实例
- `EnvelopeCheck` —— 校验结果（ok/n_checked/n_outside/offenders/notes；`describe()`）

### anchors.py
L3 锚点库 —— 表头/注释/自由文本的唯一合法解析方式。锚点匹配结果**绝不进入
数值数组**，只用于材料身份、生成器来源、维度、单位、表号→类型映射、群方案、
幂律系数（`ALUMINUM ... #3711 DATED: 22581 11483` 里的数字若走 L2 会被当数据）。

关键 API：
- `ANCHORS` —— 具名正则库（LEDCOP/ATOMIC、Hyades/SESAME、SNOP 德语段、伴随 .info、幂律说明、material.base 等约 40 个锚点）
- `find(text, name) -> re.Match | None` / `find_all(text, name) -> list[re.Match]` —— 找第一个 / 全部锚点命中
- `search_lines(lines, name) -> tuple[int, re.Match] | None` —— 逐行搜索，返回 (行号, match)
- `match_line(line, name) -> re.Match | None` —— 行首匹配

### annotations.py
注释证据通道：把「注释」从要跳过的噪声升级为一等证据——纯数字无法区分
`Al_Zeff.dat`(keV) 与 `Al_Z.dat`(eV)，注释通道把这类问题从「猜」变成「声明」。
抽取材料名/成分、维度（NT/NR/NG/IME/IMI）、单位声明（含单位变更史
`Changed to` 优先于旧值）、表号映射、群方案、幂律系数、来源（SESAME/FEOS/QEOS/
LEDCOP/SNOP/Thermos…）。绝不抛异常，失败降级为 note。

关键 API：
- `extract_annotations(doc: TextDoc, *, kind="companion", source="") -> Annotation` —— 从 TextDoc 抽全部注释证据
- `extract_from_text(text, *, source="", kind="companion", lines=None) -> Annotation` —— 从原始文本抽取
- `canon_unit(u) -> str` —— 单位规范化（大小写/写法统一，如 `gm/cc`→`g/cm3`；未知原样返回）
- `Annotation` —— 证据容器（material_name/provenance/dims/units/table_ids/file_unit_hints/group_scheme/powerlaw/notes；`to_row()`）
- `GroupScheme` —— SNOP 群划分方案（scheme_id/ng/bounds_eV；`summary()`）
- `PROVENANCE_KEYWORDS` —— 生成器/来源关键词 → 规范名映射表

### guess.py
任意 eosop 数据的「盲读」猜测层：意义块划分猜测（行宽统计 + 因数分解 +
单调列识别 + 常值/零长跑 + 数量级跳变 + 模板反演合议）与物理意义/单位猜测
（块指纹与已知族字段指纹对比）。★ 边界：一切输出都是假设（GUESS ONLY），
只进屏幕/报告，绝不写回事实字典；报告纯 ASCII，Windows GBK 不乱码。

关键 API：
- `analyze_file(path, *, compare_family=None, max_bytes=64000000) -> GuessReport` —— 完整盲读猜测（>max_bytes 诚实拒绝）
- `read_payload_values(path, *, coverage_min=0.99, max_lines=None) -> tuple[list[float], list[int], LineProfile]` —— 盲读 payload 数值序列与行宽（任一 token 不可解析则整行降级，不硬猜）
- `value_fingerprint(vals) -> dict` —— 数值序列指纹（n/zero_frac/neg_frac/int_like_frac/log10_median/log10_span/mono_frac）
- `match_fingerprints(seg_fps, field_fps, *, top_k=6, ...) -> list[dict]` —— 段指纹 × 字段指纹 → 疑似候选（含 `guess_scale` 十进制换算因子，scale≠1 加惩罚分）
- `factor_pairs(n) -> list[tuple[int, int]]` —— 全部因数对（最"方"优先）
- `render_report(rep) -> str` —— ASCII 纯文本报告
- `GuessReport` / `SegmentGuess` —— 报告容器 / 段猜测（kind: axis_like | data_block | zero_run | constant_run）

CLI 入口：
```bash
python -m eosop_pro.core.infer.guess <file> [--compare-family FAMILY]
#   --compare-family  与已知族（如 ionmix）已解析表的字段指纹做对比
```

用法示例：
```python
from eosop_pro.core.infer.inference import infer_file
from eosop_pro.core.infer.envelope import check_values

res = infer_file("unknown_table.dat")
print(res.status)          # ok | ambiguous | unrecognized
if res.ok:
    print(res.best.describe())
elif res.status == "ambiguous":
    print(res.report())    # 列出全部并列候选
```
