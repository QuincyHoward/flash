---
name: flash-readme-sync
description: 全仓 README.md 体系自底向上维护更新流程：盘点所有含 README 的目录 → 按目录深度自底向上（叶子先、父级后）逐个"先读代码、后更新文档"→ 空白 README 按 but 规范补写 → check_docs 门禁收尾。全仓文档巡检、README 更新、空白 README 补写、代码改动后同步文档时使用。触发词：更新 README、文档巡检、全仓文档、README 同步、空白 README、文档遍历、readme sync。
---

> 最后核对：2026-11-06 · commit 20337b6

# 全仓 README.md 自底向上维护（flash-readme-sync）

## 适用场景

- 代码结构/接口变动后，同步更新受影响的 README
- 定期全仓文档巡检（声明 vs 代码一致性）
- 补写空白/缺失的 README

## 核心原则

**先读代码，后更新文档**——README 的每一条声明（文件清单、API 名、入口、职责）都必须以当前代码为准；文档不改代码。自底向上：叶子目录的 README 先定稿，父级 README 才能准确引用子级。

## 操作步骤

### Step 0: 盘点与范围

```bash
# 全仓 README 清单（含行数与目录深度）
find . -name "README.md" -not -path "./.git/*" -not -path "*__pycache__*" \
  -not -path "./.workbuddy/*" -not -path "./*venv*" -not -path "./wheelhouse/*" \
  -not -path "./artifacts/*" | while read f; do echo "$(wc -l < "$f") $f"; done
```

**豁免范围**（只读不写，除非上游同步）：`.pytest_cache/`（自动生成）、`flash/output_pro/PlasmaPy/**`（vendored 上游）、`docs/_legacy_diags/**`（历史归档）、`*_backup_*`（备份快照）、`temp*/`（待删区）。

### Step 1: 自底向上排序

按目录深度**降序**（深→浅）排序处理；同深度按路径字母序。父目录 README 最后处理——它引用子级结论。

### Step 2: 单个 README 的"读代码→更新"循环

1. **读代码**：`ls` 目录全部文件；读 `__init__.py`（导出面）、入口/主模块头注释；有子 README 则读其结论
2. **对照声明**：逐条核对 README 中的文件清单、类/函数名、路径、数字（参数个数、测试数等）
3. **更新**：只改与代码不符处；不重写无错内容；改动处更新文首锚点 `> 最后核对：YYYY-MM-DD · commit <hash>`
4. **空白 README 补写规范**：①目录职责一句话 ②内容清单（文件/子目录表，一句话说明）③关键入口（类/命令）④使用示例或指引 ⑤关联资源。≤60 行，锚点开头

### Step 3: 收尾验证

```bash
python scripts/08_docs/check_docs.py   # 链接/模块引用/锚点/敏感信息门禁
python scripts/sync_workbuddy_skills.py  # skills/ 有改动时
```

## 护栏与铁律

1. **禁止臆造**：代码里没有的功能/接口不得写进 README；拿不准的标注「待核实」并留给用户
2. **文档不改代码**：发现代码 bug 记录到报告，不顺手改（除非用户明确要求）
3. 豁免目录不动；上游 vendored 包的 README 保持原样
4. 每个 README 必须带锚点（check_docs 对 `README.md` 强制）
5. 绘图/示例输出路径遵循 `<repo>/../flash_sim_runs/` 契约，不新增包内输出目录
6. 敏感信息（账号/主机名）一律占位符化
7. 全部完成后 git 提交，附更新统计（更新 N / 补写 M / 确认无误 K）

## 常见坑

- 空目录的 README 描述未来规划时须注明「规划中」，不得写成已实现
- 深层测试目录 README 常复述旧 API——先 grep 目录内测试文件实际 import 的模块名
- 数字类声明（"57 passed"、"150+ 参数"）最易过期——能跑的用实测值，不能跑的删除具体数字改定性描述
- 父级 README 的子目录清单用 `ls -d */` 核对，防新增/删除目录未同步

## 关联资源

- `skills/README.md`（SKILL.md 编写规范，本 skill 同样遵守）
- `scripts/08_docs/check_docs.py`（文档门禁：链接/模块/锚点/敏感信息）
- `flash-readme-sync` 执行报告模板：更新/补写/豁免三列清单（写入 .workbuddy/memory/ 当日日志）
