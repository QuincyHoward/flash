---
name: physimx-token-budget
description: token 节约纪律，防止 AI 陷入"读"的泥潭导致上下文爆炸。适用于所有代码阅读、文件搜索、HDF5/仿真输出处理场景。触发词：上下文太大、读太多、token、省着点读、token budget。
---

> 最后核对：2026-11-06 · commit 54a9f69
> 来源：用户级 physimx-token-budget 技能吸收（失效引用已按本仓现行工具链适配）

# Token 预算管理（Token Budget）

## 核心原则

**AI 的工作记忆 = 文件系统，不是上下文窗口。**

## 读文件纪律

**禁止行为**
- ❌ 连续 Read 超过 3 个文件而不做决策
- ❌ 全量读取 >200 行的文件（应先 Grep 定位再读片段）
- ❌ 直接读 HDF5/仿真输出原始内容（用 loader/统计工具）
- ❌ Glob 枚举整个目录再逐个 Read

**正确行为**
```bash
# 找类定义 → 先 Grep 行号，再读片段
grep -n "class FlashDataLoader" flash/output_pro/loader/data_loader.py
# → 只 Read 该行 ±60 行

# 理解模块骨架 → Grep 签名，不全量读
grep -n "    def \|^class " flash/input_gen/gen_par/generator.py
```

## 搜索纪律

- 宽泛/多轮搜索 → 交给 Explore 子代理（结论回传，过程不占主上下文）
- 找文件 → Glob 限定子目录（如 `flash/scenarios/private/**`），不要全仓 `*.py`
- 全局检索明确排除 `flash/temp_delete/`、`__pycache__/`、`artifacts/`

## HDF5 / 仿真输出处理

**规则：不直接读原始 HDF5 内容，只处理决策层信息**
- 用 `flash/output_pro/loader`（批读/按需变量）与 `flash-data-extract` 技能的提取范式
- AI 只消费统计摘要与诊断结论：参数调整、异常判断、结果对比
- `flash-output-analysis` 的健康检查四判据先行，不逐帧翻数据

## 迭代优化场景

每轮迭代上下文只保留：①上一轮摘要（3 行）②当前参数 ③当前结果摘要。
完整历史写入 `.workbuddy/memory/` 日志文件，不进上下文；每 5 轮强制 checkpoint，必要时重置。

## 项目地图优先

- 启动先读 `AGENTS.md`（技能索引）与 `docs/skills-map.md`（三向索引），不要读目录树拼接理解
- FLASH 源码级问题先查 `flash-knowledge` 的 references（含 src_finding 方程↔源码对照），不要直接翻 6800+ 个 F90

## 停止信号

发现自己正在：连续读第 4 个文件 / 全量读大文件 / 在 `temp_delete/` 里找参考
→ 立即停止，换摘要式工具（Grep 骨架、子代理、references 文档）或询问用户。
