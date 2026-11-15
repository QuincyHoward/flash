> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

# pipeline/ —— 编排层：批处理实现（batch）与命令行唯一入口（cli）

三个入口的分工纪律：`batch.py` 是**唯一实现**（976 行，每个动作都能被
`test/pipeline/test_batch.py` 直接调用测试）、`cli.py` 只做参数解析（605 行，
`scripts/*.py` 只是薄包装）。CLI 入口：
`python -m eosop_pro.pipeline.cli <子命令>`。每个批处理动作都产出
`outputs/reports/<name>.<stamp>.{csv,json,md}`，头部写明数据来源、生成时刻、
样本总数——结论必须可回溯到具体文件。向下依赖 registry/（声明、材料、字典）、
parsers/、convert/、plotting/、ops/。

## 模块

### batch.py（976 行）
批处理编排——`inventory` / `audit` / `convert-all` / `plot-all` / `infer-unknown`
五个动作的唯一实现。每个动作回答一个问题：`inventory`——matter++ 里到底有什么
（后缀/目录/编码/行尾分布）；`audit`——按声明类型逐文件解析，覆盖率闸口过不过、
谁解析不了为什么；`convert-all`——能解析的表能不能写出双轨 HDF5（native 逐字 +
unified 插值）；`plot-all`——数据长什么样、能不能出 PPT 级英文图；
`infer-unknown`——没有任何声明的文件，零先验能不能反演出结构。

关键 API：
- `inventory(*, outdir=None, matter_dir=None, report_dir=None) -> dict` ——
  全量文件清单 + 目录画像（字节层画像只读文件头，代价 O(1)）
- `audit_sweep(*, outdir=None, multigroup=False, matter_dir=None, limit=0)
  -> dict` —— 阶段 A 全量声明式审计；闸口：已解析 + 已跳过 == 样本数；
  返回值含 `pass` 布尔
- `convert_all(*, outdir=None, limit=0, family=None, multigroup=False,
  native_only=False, unified_only=False, n_x=None, n_te=None, ...) -> dict` ——
  批量写双轨 HDF5；内部做名称碰撞检查（`_check_name_collisions`）、2D 网格
  判定（`_is_2d`/`_has_grid_axes`）
- `plot_all(*, outdir=None, limit=40, family=None, ...) -> dict` —— 批量 QA
  出图（`_plot_one` 每图落盘即 close）
- `plot_cn4_all(*, outdir=None, ...) -> dict` —— 批量 cn4 出图（缺省根目录
  `matter++/Ionmix` 或 `eos_op_data`）
- `infer_unknown(relpath, *, outdir=None) -> dict` —— 单文件零先验反演报告
- `infer_unrecognized(*, from_report=None, outdir=None, limit=0, ...) -> dict`
  —— 对审计报告里的未决集合批量反演；`latest_audit_report(outdir)` 取最新
  `audit_all.<ts>.csv`

### cli.py（605 行）
命令行入口——**所有动作的唯一 argparse 定义**。子命令共 **19 个**（以
argparse 定义为准，分四组）；所有路径均可给出相对 `matter++` 的相对路径，
缺失的相对路径经 `config.MATTER(rel)` 解析。

| # | 子命令 | 说明 | 关键参数 |
| --- | --- | --- | --- |
| 1 | `targets` | 列出可转换目标（名称、说明、所需字段） | — |
| 2 | `parse <relpath>` | 解析单文件并打印摘要（声明类型/状态/维度/计数/单位来源） | — |
| 3 | `infer <relpath>` | 通用反演报告（阶段 B） | — |
| 4 | `identify [<relpath>]` | 声明 vs 内容比对；给 relpath 单文件，否则全树 + 报告 | — |
| 5 | `zeff` | Z̄ 盘点并写报告 | — |
| 6 | `convert <relpath>` | 跨格式转换（默认 `--to cn4`） | `--to` `--out`(必填) `--izgas` `--fracsp` `--atomwt` `--invert` |
| 7 | `h5 <relpath>` | 写单表 HDF5 | `--out` `--A` |
| 8 | `plot <relpath>` | QA 出图（单文件） | `--outdir` |
| 9 | `inventory` | ② 全量文件清单与目录画像 | `--outdir` `--matter-dir` `--report-dir` |
| 10 | `extract-docs` | ① 抽取说明文档 → docs/extracted | `--root` `--outdir` |
| 11 | `audit` | ③ 阶段 A 全量声明式审计 | `--limit` `--multigroup` `--matter-dir` `--report-dir` |
| 12 | `convert-all` | ⑤ 批量写双轨 HDF5 | `--limit` `--family`(可重复) `--multigroup` `--native-only` `--unified-only` `--n-x` `--n-te` `--relpath`(可重复) |
| 13 | `plot-all` | ⑥ 批量 QA 出图 | `--limit`(默认 40) `--family` `--report-dir` |
| 14 | `prune-reports` | ① 报告目录每类只留最新 N 批 | `--keep`(默认 1) `--dry-run` |
| 15 | `infer-unknown [<rel>]` | ④ 零先验反演；单文件或未决集合 | `--limit` `--from-report` `--rescan` `--no-dump` |
| 16 | `cn4-plot <cn4>` | 单个 cn4 出图（彩图/曲线/群大图） | `--kind` `-q`(可重复) `-x/-y` `--ig` `-L` `-g` `-A` `-o` `--outdir` `--cmap` `--zlog` `--no-xlog` `--no-ylog` |
| 17 | `cn4-plot-all` | 批量：目录下全部 .cn4 出图 | `--cn4-dir` `--limit` `-q` `--axes` `--curve` `--opacity-figures` `-L` |
| 18 | `cn4-paths <cn4>` | cn4 EOS 路径：等温/等压/等熵/雨贡纽/P-V/probe | `--what`(必选) `--t-idx` `--i0/--j0` `--temp` `--pressure` `--rho0` `--x-axis` `--n-rho` `--n-T` |
| 19 | `cn4-fit <cn4>` | cn4 关系拟合：幂律/指数/理想气体 | `--what`(必选) `--field` `--t-idx` |

用法示例：
```bash
python -m eosop_pro.pipeline.cli parse   mat_Al-1.0/AL_eos.feos
python -m eosop_pro.pipeline.cli convert mat_Al-1.0/AL_eos.feos --to cn4 --out al.cn4
python -m eosop_pro.pipeline.cli audit --limit 40          # 冒烟
python -m eosop_pro.pipeline.cli convert-all --family ionmix
python -m eosop_pro.pipeline.cli infer-unknown --rescan    # 重新全树扫描（慢）
python -m eosop_pro.pipeline.cli cn4-plot sample.cn4 -g 3  # 第 3 群 2x2 大图
```
```python
# batch 可编程调用（测试即如此）
from eosop_pro.pipeline import batch
r = batch.audit_sweep(limit=40)
assert r["pass"]
```
