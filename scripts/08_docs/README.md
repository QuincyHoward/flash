# scripts/08_docs — 文档体系工具

> 最后核对：2026-11-05 · commit 7e04857

**一句话职责**：为全仓 README/GUIDE 文档体系提供「信息采集」与「防回归校验」两个只读工具，是文档防腐化机制的执行者。

## 文件清单

| 文件 | 职责 |
|---|---|
| `dump_docstrings.py` | 只读 AST 模块摘要：遍历目录输出 Markdown 表（模块/行数/docstring 首段/类/顶层函数/入口），**不 import 不执行任何代码**。重写任何 README 前先跑它作为依据 |
| `check_docs.py` | 文档门禁：校验 README/GUIDE 中的相对链接、`flash.*` 模块引用、头部「最后核对」元信息块；启发式扫描敏感信息（API key/password/IP）。违规退出码非 0 |

## 使用

```bash
# 1) 生成某目录的模块摘要表（README 重写依据）
python scripts/08_docs/dump_docstrings.py --root flash/_core

# 2) 提交前校验某目录文档
python scripts/08_docs/check_docs.py --root flash/_core

# 3) 全仓校验（阶段收尾门禁）
python scripts/08_docs/check_docs.py
```

## 排除区（两工具默认跳过）

`PlasmaPy/`（vendored 外部包）、`__pycache__`、`archive*`、各类输出/产物/数据目录（`flash_output`、`sim_output`、`inputfiles`、`reports`、`test_output` 等）。

## 维护规则

文档元信息块中的「commit 短 hash」是核对锚点：`git diff <hash>..HEAD -- <目录>` 即可判断文档是否已落后于代码。模块清单表的「行数」列偏差 >30% 时 `check_docs` 输出 WARN 提示重读。

**上级导航**：[../README.md](../README.md)（仓库 scripts 工具区索引）
