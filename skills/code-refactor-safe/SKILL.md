---
name: code-refactor-safe
description: 通用安全重构工作流：重命名函数/类、拆分大文件（>300 行）、提取公共接口、移动模块时的必要步骤与风险分级，防止引用断裂和功能损坏。触发词：重命名、重构、拆分文件、提取接口、移动模块、safe refactor。
---

> 最后核对：2026-11-06 · commit 54a9f69
> 来源：用户级 code-refactor-safe 技能吸收（备份机制已按本仓约定适配）

# 安全重构工作流（Safe Refactor）

## 适用场景

- 重命名函数/类
- 拆分大文件（>300 行）
- 提取公共接口
- 移动模块到新目录

## 重构前检查

1. **确认影响范围**：用 Grep 全仓检索旧名（排除 `flash/temp_delete/`、`__pycache__/`）；`git status` 确认工作区干净后再动手
2. **评估风险分级**：
   - 引用数 0-3：低风险，直接改
   - 引用数 4-10：中风险，按顺序改，每改一处就测试
   - 引用数 >10：高风险，保留旧名别名兼容，分批改

## 重构流程

### 方案一：直接重命名
```bash
# 1. Grep 确认全部引用点 → 2. 逐一替换 → 3. 运行测试
make test        # pytest 三套件
```

### 方案二：拆分大文件
1. 先通读结构（Grep `^class |^def ` 拿骨架，勿全量读）
2. 规划拆分：每个新文件一个主题
3. 写新文件；原文件末尾留向后兼容别名：`from .new_module import OldClass`
4. 逐个验证新文件可独立 import → `make test` → 确认后下一版本再删别名

### 方案三：提取接口
1. 定义 Protocol/ABC → 2. 原实现类继承 → 3. 验证 isinstance → 4. `make test`

## 重构后验证

```bash
make lint        # black + ruff (line-length=120)
make test        # 全量测试
git diff --stat  # 最终确认变更范围符合预期
```

## 回滚方案

- Git 管理：`git checkout -- <file>` 回滚单文件；重构前确保有干净 commit 可回退
- 大规模移动/批量操作前先备份（本仓约定参考 `flash-backup-verify` 技能 / `scripts/04_backup/`）

## 铁律

- 重构与功能修改**不同时进行**：纯重构 commit 不夹带逻辑变更
- 一次只做一种方案；中高风险每步验证后再继续
- 改完包内模块后检查 `test/` 三套件与相关 SKILL.md/docs 中的路径引用是否同步更新
