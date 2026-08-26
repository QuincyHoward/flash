# 文件内在关联检查 — 设计与验证报告

**模块**: `flash/input_gen/gen_checker`
**新增**: `check_relations.py` + `relations/` 子包
**版本**: 关联检查升级（checker v0.1.5）
**日期**: 2026-08-26
**维护**: PhySimX Team

---

## 1. 背景与目标

原有的 `checker.py`（`DependencyChecker`）只校验 7 个关键文件**是否存在**：

```
.par / .cn4 / Config / Simulation_initBlock.F90 / Simulation_init.F90 /
Simulation_data.F90 / Makefile
```

但"文件都在"并不代表"能跑通"。例如：`.par` 引用了某个 `.cn4` 但 `Config` 没在
`DATAFILES` 里声明、或 `Simulation_data.F90` 忘了声明 `Simulation_init.F90` 要用的
变量——这些都会在编译/运行时才暴露，排查成本高。

本升级新增 **`check_relations.py`**，在"存在性"之上做**内容一致性**检查，让
不一致在编译/运行前就被发现。

## 2. 架构

```
gen_checker/
├── checker.py            # (已有) 文件存在性检查 DependencyChecker
├── check_relations.py    # (新增) 内在关联检查主脚本 + CLI
├── relations/            # (新增) 规则子包（注册式规则引擎）
│   ├── __init__.py       # 导入所有规则模块，完成注册
│   ├── _core.py          # RelationResult / RelationContext / relation_rule / REGISTRY
│   ├── _parsers.py       # 公共解析工具（.par/Config/F90/脚本 提取）
│   ├── rules_reference.py  # A类 规则 1-3 文件级引用
│   ├── rules_parameter.py  # B类 规则 4-6 参数级一致性
│   ├── rules_dimension.py  # C类 规则 7-11 维度/光束/脉冲
│   └── rules_script.py     # D类 规则 12-14 脚本级装配
└── ploter/               # (已有) 绘图工具
```

**行数**：主脚本 `check_relations.py` 217 行（≪1000），规则拆分至 `relations/` 各模块，
清晰可维护。

## 3. 内置 14 条规则

### A. 文件级引用（`rules_reference.py`）

| id | 规则 | 判定 |
|----|------|------|
| `par_cn4_on_disk` | `.par` 引用的 `.cn4` 必须存在于磁盘 | 缺失 → FAIL |
| `par_cn4_in_config_datafiles` | `.par` 引用的 `.cn4` 必须已声明于 `Config` 的 `DATAFILES` | 引用未声明 → FAIL |
| `config_table_parameter` | `*TableFile`/`*FileName` 键取值应为 `.cn4/.ses` 文件名 | 误填模式名/类型名 → FAIL |

### B. 参数级一致性（`rules_parameter.py`）

| id | 规则 | 判定 |
|----|------|------|
| `par_sim_in_config` | `.par` 的 `sim_*` 键需在 `Config` 有 `PARAMETER` 定义 | 白名单外 → FAIL |
| `simdata_init_consistency` | `Simulation_init.F90` 写入的变量须在 `Simulation_data.F90` 声明 | 未声明 → FAIL |
| `par_init_key_match` | `.par` 的 `sim_*` 键与 `Simulation_init.F90` 读取键一致 | `.par` 设了但 init 没读 → FAIL |

### C. 维度 / 光束 / 脉冲（`rules_dimension.py`）

| id | 规则 | 判定 |
|----|------|------|
| `dimension_grid_vs_setup` | `.par` 维度(nblocky/z)与 `setup` 的 `-1d/2d/3d` 及 geometry 一致 | 不一致 → FAIL |
| `beam_number_match` | `ed_numberOfBeams=N` 需有 `ed_lensX_1..N`/`ed_targetX_1..N` | 缺失 → FAIL |
| `pulse_beam_binding` | `ed_pulseNumber_i` 须在 `1..ed_numberOfPulses` | 越界 → FAIL |
| `pulse_sections_limit` | `ed_numberOfSections_*` 超 20 时 `setup` 需设 `ed_maxPulseSections` | 缺参数 → FAIL |
| `beam_in_domain` | 靶 `ed_targetX_i` 应在仿真域内（透镜可域外） | 目标在域外 → FAIL |

### D. 脚本级装配（`rules_script.py`）

| id | 规则 | 判定 |
|----|------|------|
| `par_file_in_script` | `run_flash.sh` 的 `PAR_FILE` 与磁盘 `.par` 名一致 | 不一致 → FAIL |
| `species_setup_match` | `setup` 的 `species=` 须在 `Config` 的 `SPECIES` 声明 | 未声明 → FAIL |
| `makefile_f90_match` | `Makefile` 的 `Simulation += X.o` 须有对应 `X.F90` | 缺文件 → FAIL |

## 4. 使用方式

### CLI

```bash
# 检查一个仿真目录
python check_relations.py <仿真目录> [--verbose]

# 只跑指定规则
python check_relations.py <目录> --rule par_cn4_on_disk

# 列出所有规则
python check_relations.py --rules

# 只输出结论行
python check_relations.py <目录> --summary-only
```

### Python API

```python
from flash.input_gen.gen_checker import RelationChecker

rc = RelationChecker("/path/to/sim_dir")
results = rc.run_all()        # List[RelationResult]
print(rc.summary())           # 文本报告
if rc.all_passed():           # 是否无失败
    print("内在关联全部一致")
else:
    for r in rc.failed():
        print(r.rule_id, r.message)
```

## 5. 场景集成（ch_center）

`flash/scenarios/center_evolution/ch_center/laserslab1d_local_custom.py` 的步骤 1
已集成关联检查：文件存在检查 → 内在关联检查 → WSL/HPC 运行。若关联不一致，
脚本打印 `[FAIL]` 明细并 `return False` 停止，避免带病编译/运行。

**运行日志（磨合验证）**：
```
[-] 进行文件内在关联检查 (check_relations)...
[OK] 内在关联检查通过（14 条规则全部通过/跳过）
```

## 6. 验证结果

对 `ch_center/flash_input` 实测：**通过 13 / 失败 0 / 跳过 1**（`species_setup_match`
因该场景 `Config` 无 `SPECIES` 声明而跳过）。

构造性错误检测（人为破坏后）均正确 FAIL：

| 注入错误 | 命中规则 | 结果 |
|---------|---------|------|
| `Config` 删除 `DATAFILES` | `par_cn4_in_config_datafiles` | FAIL，exit=1 |
| `.par` 引用不存在的 `NOPE.cn4` | `par_cn4_on_disk` | FAIL |
| `ed_numberOfBeams=3` 但只有 2 束 | `beam_number_match` | FAIL |
| 脚本 `PAR_FILE` 改名 | `par_file_in_script` | FAIL |

## 7. 可扩展性

采用**注册式规则引擎**，新增关联无需改主流程：

1. 在 `relations/` 新增/追加规则函数，用 `@relation_rule(id, name)` 装饰：
   ```python
   @relation_rule("my_rule", "我的自定义关联")
   def my_rule(ctx: RelationContext) -> RelationResult:
       ...
       return RelationResult(rule_id="my_rule", name="我的自定义关联",
                             status=True, message="...", details={...})
   ```
2. 在 `relations/__init__.py` 末尾 `from . import my_module`（若新增模块）即可。
3. `run_all()` 自动遍历 `REGISTRY`，新规则自动纳入，无需改 `check_relations.py`。

**共享缓存**：规则通过 `RelationContext`（`_core.py`）共享已解析的 `.par` 字典、
`Config` 行集等，避免重复解析，规则间可安全复用。

## 8. 相关文档

- 内在关联规则详解与扩展指南：`GEN_CHECKER_GUIDE.md` →「检查项的内在关联」「如何扩展自定义关联」
- 文件存在性检查：`checker.py` / `DependencyChecker`

---

**报告版本**: 1.0
**最后更新**: 2026-08-26
