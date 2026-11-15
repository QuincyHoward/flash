# parsers/test —— 产物核查套件（人工核查用）

> 最后核对：2026-11-14 · commit f8225de · 独立 runner，不接入 eosop_pro/test/run_all.py

## 定位与分工

- **本目录**：产物核查套件——每解析器一个 `test_<名>.py`（与 `formats/<名>.md`、
  `../<名>.py` 同名同序），真实解析 matter++/eos_op_data 样例，产出**解析统计
  summary.txt + 代表性图像 png**，供人工逐解析器核查格式理解是否有歧义。
- **`../../test/parsers/`**：纯断言测试（不产图），进主测试体系（run_all.py 递归发现）。

## 运行

```bash
cd <gen_eos_op>
python eosop_pro/parsers/test/run_all.py        # 全量 + 汇总 log
python eosop_pro/parsers/test/test_cn4_io.py    # 单文件裸跑
```

退出码 = 失败测试数；全量运行的 console 输出写入 `_out/test_log.txt`。

> 注：`test_multi/` 为**独立子目录测试**（不进 run_all，单文件裸跑，
> 产物 `_out/test_multi/`）——见 `test_multi/README.md`。

### 生成数据专项（test_cn4_generated.py）

核查 IONMIX 生成的新命名 cn4（`Z.._{n}g-...` 群数后缀，数据源
`gen_eos_op/ionmix/Ionmix_run/outputfiles/cn4/`）：解析统计 → 批量出图 →
**图文并茂 HTML 报告**（`_out/cn4_io/generated/report.html`，base64 内嵌图像
+ ionmxinp 节选 + EOS 字段单位表）。产物缺失时 SKIP；守护断言：文件名群数
== 头部 ngrups、cn4_to_parsed_tables 拆 4 表。样例为 None 时全部 SKIP（不 FAIL）。

## 产物树

```
_out/
├─ test_log.txt              # run_all 汇总（PASS/FAIL/SKIP 明细）
├─ cn4_io/                   # cn4_io.py 解析器核查（test_cn4_io.py）
│  ├─ summary.txt / roundtrip_*.cn4 / 00_IONMIX_*/
│  └─ generated/             # 数据核查（test_cn4_generated.py，被测解析器同为 cn4_io）
│     ├─ report.html         # 图文报告（默认聚焦 CH 参考表，base64 内嵌图像）
│     ├─ data_summary.txt    # 数据核查统计
│     └─ <stem>/00_CN4_*_EOS/*.png 等
└─ <解析器名>/
   ├─ summary.txt            # 样例路径 / kind / axes 计数 / field_units /
   │                         #   unit_source / notes（uk/uv 语义线索）
   └─ *.png                  # 每族 1-3 张代表性图（plotting 层真实函数产出）
```

## 语义约定

- 样例**惰性发现**（matter++ 全树 + eos_op_data）：找不到可解析样例 → 记
  `SKIP` 并通过（不 FAIL）——数据缺失不阻塞核查。
- 绘图失败（matplotlib 缺失/异常）→ `SKIP-plot` 记入 summary，不 FAIL。
- 每测试文件含 **dictionary_consistency** 断言：该族在
  `registry.field_checks.FIELD_CHECKS` 已注册且 `tags_label()` 输出与
  `../formats/<名>.md` 第 2 节所录标记一致——防止文档与字典漂移。
- uk/uv 标记规约：uk=无来源确认 / uv=未人工核查；权威见
  `../../registry/field_checks.py` 与 `../../docs/eosop变量控制字典.md`。
