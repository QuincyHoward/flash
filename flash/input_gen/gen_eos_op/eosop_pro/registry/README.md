> 最后核对：2026-11-14 · commit ba2981e（其后含功能树重组，代码为准）

# registry/ —— 注册表层：文件类型声明、材料映射与变量控制字典的唯一权威

本层回答「matter++ 里每个文件是什么、属于哪个材料、各物理量是什么意思什么单位」。
上层 `pipeline/cli.py`（parse/audit/identify/zeff 子命令）与 `plotting/`（标签、报告）
都经这里取事实；本层向下依赖 `core/`（config 路径、text 读文件、infer 反演）与
`parsers/`（dispatch 按声明族调解析器）。细分四个子层：

| 子层 | 职责 |
| --- | --- |
| `field_checks.py` | **变量控制字典**——物理意义/单位/来源/核查状态唯一登记（本文件详解） |
| `identify/` | 阶段 A 分派解析 + 阶段 B「声明 vs 内容」比对 |
| `material/` | material.base + DatabaseIndex.xml + *.list 三源合并的材料注册表 |
| `schema/` | 声明式类型表（零内容推断）、伴随注释配对、DatabaseIndex 解析 |
| `zeff/` | Z̄ 数据源注册表、材料级覆盖度盘点、T 轴单位裁决 |

## 模块

### field_checks.py
eosop 家族**大型控制字典**——每个变量（字段/轴）的物理意义、单位、来源与核查状态
的唯一权威登记（用户 2026-09-15 规约：一切绘图与分析操作都须经本字典）。

核心概念：
- **标记只有 `uk`/`uv` 两个**：`uk` = 无可指认来源（`kind == "none"`）；`uv` =
  未人工核查。有源且已核查 → 标记整体省略（当前仅 cn4/ionmix 全 18 块）。
  统一出口 `tags_label()` 折叠为 `"uk, uv"` / `"uv"` / `""`。
- **字段结构**：`meaning`（长标签，ASCII）、`short`（短标签，绘图默认，内联在
  `FieldCheck(..., short=...)` 构造处）、`unit`（未判定写 `"unknown"`，不猜测）、
  `kind`（来源类型受控词表 KIND_*）、`source`（长文本一级出处详述）、`checked`。
- **source 必须下探一级出处**，四类：文件内明文声明（in-file declaration）、
  一级说明文档（primary document，原文摘录写入 source 字段）、
  源码行号（source code）、代码内派生公式（code-derived）；另有 parser-measured
  预留词与 none。⚠️ `docs/20_格式规格与物理量单位手册.md` 是中间产物，**不得**引用。
  （原 `docs/extracted/` 抽取文本已于 2026-11-06 清理，摘录直接落 source 字段。）

关键 API：
- `FieldCheck(meaning, unit, checked, kind=KIND_NONE, source="", short="")` —— frozen
  dataclass 条目；`fc.doc` 为只读派生属性（有源→`"doc"`，无源→`"uk"`）
- `field_check(family, field) -> FieldCheck` —— 查询条目；顺序：精确字段名 → `"*"`
  兜底 → 未注册族兜底，永不崩溃也绝不冒充已核查
- `tags_label(fc) -> str` —— 标记统一出口（uk/uv 折叠规则）
- `doc_label(fc) / verify_label(fc) -> str` —— 单一认证的显示标记
- `register_family(name, entries, *, overwrite=False)` —— 把未来未知格式族注册进
  字典；注册后 gridmap 报告/绘图链路立即采用，不得绕过字典；默认拒绝覆盖已注册族
- `dump_markdown(title=...) -> str` —— 渲染字典 Markdown 全文（人工核查对照底稿）
- `checked_families() -> tuple[str, ...]` / `family_check_stats(family) -> dict[str, int]`
- 常量：`FIELD_CHECKS`（族→条目总表）、`KIND_IN_FILE / KIND_DOC / KIND_CODE /
  KIND_MEASURED / KIND_DERIVED / KIND_NONE`、`DICT_DOC_RELPATH`

**与文档、守护测试的逐字同步关系**：
- `docs/eosop变量控制字典.md` 是生成物，由本模块 `dump_markdown()` 渲染，落盘位置
  `DICT_DOC_RELPATH`。再生命令：
  ```bash
  python -m eosop_pro.registry.field_checks
  ```
- 守护测试 `test/eosopdata/step02_families/test_field_checks.py` 的
  `test_control_dictionary_doc_in_sync` 断言磁盘上该文档与 `dump_markdown()`
  **逐字同步**——字典改动后必须重跑上述命令再生成，否则测试失败；
  `test_plot_labels.py` 同步守护绘图模块不得再硬编码物理量标签。

用法示例：
```python
from eosop_pro.registry.field_checks import field_check, tags_label

fc = field_check("ionmix", "P")        # -> FieldCheck(meaning=..., unit=..., ...)
tags_label(fc)                          # -> ""（cn4/ionmix 已核查，标记省略）
fc2 = field_check("hugoniot", "Us")     # 未核查族
tags_label(fc2)                         # -> "uv" 或 "uk, uv"
```
```bash
# 字典改动后再生文档（守护测试要求逐字同步）
python -m eosop_pro.registry.field_checks
```

## 子层导航

- `identify/README.md` —— 阶段 A 分派器 + 阶段 B 比对
- `material/README.md` —— 三源合并材料注册表
- `schema/README.md` —— 声明式类型表 / 伴随注释 / DatabaseIndex
- `zeff/README.md` —— Z̄ 注册表 / 覆盖度盘点 / 单位裁决
