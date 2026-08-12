# 版本号命名协议 (Versioning Protocol)

## 概述

flash-sim 采用 **Semantic Versioning (SemVer) 2.0.0** 进行版本管理。本文档正式定义版本号的格式、变更规则和发布流程。

---

## 1. 版本号格式

```
MAJOR.MINOR.PATCH
```

### 编码位置

| 位置 | 格式 | 示例 |
|------|------|------|
| `pyproject.toml` | `X.Y.Z` (PEP 440) | `1.0.0` |
| Git tag | `vX.Y.Z` (前缀 `v`) | `v1.0.0` |

> **注意**: pyproject.toml 中不带 `v` 前缀（PEP 440 规范要求）；Git tag 带 `v` 前缀（社区惯例）。
>
> **文档不标注版本号**: 用户文档 (README / 场景指南 / 子模块文档) **不写具体版本号**,
> 以避免频繁维护时文档与版本脱节。需要版本号时统一以 `pyproject.toml` 为准,
> 历史版本见 `git tag -l` 与 PyPI Releases。

---

## 2. 版本维护策略 (Gitee 分支为主, PyPI 阶段性更新)

- **开发主阵地**: Gitee 仓库 (`gitee.com/physimx/flash`) 的各分支
  (`master` 开发主线, `release_pypi` 发布分支, `release/*` 阶段性分支)。
- **PyPI 按阶段发布**: 不随每个 commit 发布 PyPI; 仅在功能达到阶段里程碑
  (bug 修复集 / 新特性集) 时, 按 SemVer 递增版本并发布。
- **版本号唯一权威**: `pyproject.toml` 的 `version` 字段是唯一权威;
  Git tag 与 PyPI 版本必须与之保持一致。
- **TestPyPI 先行**: 新版本先发 TestPyPI 验证 (安装 + 全局测试), 通过后再发正式 PyPI。

---

## 2. 版本增量规则

| 段位 | 触发条件 | 从 v1.0.0 的例子 |
|------|----------|------------------|
| **MAJOR** | 不兼容的 API 变更、模块重构、重大里程碑发布 | `1.0.0` → `2.0.0` |
| **MINOR** | 向下兼容的新功能、新模块、新增 API | `1.0.0` → `1.1.0` |
| **PATCH** | 向下兼容的 bug 修复、性能优化、文档修正 | `1.0.0` → `1.0.1` |

### 具体判定标准

**MAJOR 增量（需团队讨论）：**
- 删除或重命名公开 API / 类 / 函数
- 修改函数签名导致旧调用失效
- 移除或替换核心模块
- 配置文件格式不兼容变更
- Python 最低版本要求提升（如 3.10 → 3.11）

**MINOR 增量（常规发布）：**
- 新增模块、类、函数（不破坏旧 API）
- 新增可选参数（有默认值）
- 新增仿真类型支持
- API 扩展或增强

**PATCH 增量（可随时发布）：**
- 修复计算逻辑错误
- 修复文件路径、参数传递等 bug
- 更新文档、注释、类型注解
- 优化性能（不改变外部行为）
- 修复 CI / 测试配置

---

## 3. 预发布版本

在正式发布前，可使用预发布标签：

```
MAJOR.MINOR.PATCH-{alpha|beta|rc}.N
```

| 标签 | 含义 | 示例 |
|------|------|------|
| `alpha.N` | 内部开发版，功能不全 | `2.0.0-alpha.1` |
| `beta.N` | 功能冻结，测试验证 | `2.0.0-beta.1` |
| `rc.N` | 候选发布，仅修 bug | `2.0.0-rc.1` |

预发布版本不单独打 Git tag，仅在开发分支内使用。Git tag 仅针对正式版本。

---

## 4. 发布流程

### 标准发布步骤

```bash
# 1. 确认 pyproject.toml 中的 version 已更新
#    编辑 pyproject.toml, 将 version 改为目标版本

# 2. 运行完整测试套件
python -m pytest test/ input_gen/test/ output_processors/test/

# 3. 使用发布脚本打标签（自动运行全部测试）
bash scripts/tag-release.sh vX.Y.Z

# 4. 推送标签到远程
git push origin vX.Y.Z

# 5. 构建并发布（可选）
python -m build
twine upload dist/flash_sim-X.Y.Z*
```

### 热修复流程

当主分支已发布 vX.Y.Z，需要紧急修复时：

```bash
# 1. 从标签切出热修复分支
git checkout -b hotfix/critical-bug vX.Y.Z

# 2. 修复 bug + 提交
git commit -m "fix: 修复关键问题"

# 3. 打 PATCH 标签
bash scripts/tag-release.sh vX.Y.Z+1

# 4. 合并回主分支
git checkout main
git merge hotfix/critical-bug
```

---

## 5. 版本历史

| 版本 | Git tag | 日期 | 说明 |
|------|---------|------|------|
| 0.0.1 | `v0.0.1` | — | 初始原型 |
| 0.1.0 | `v0.1.0` | — | 基础框架搭建 |
| 0.2.0 | `v0.2.0` | — | 扩展功能模块 |
| **1.0.0** | **`v1.0.0`** | **2026-07-04** | **首个正式发布 (Beta)** |

---

## 6. 兼容性承诺

- **Python 版本**: 当前最低支持 Python 3.10。MAJOR 版本变更可能提升最低版本要求。
- **依赖库**: 主要依赖（h5py, numpy, matplotlib）的版本约束在 pyproject.toml 中声明，MINOR/PATCH 发布不会收紧约束。
- **配置文件**: `.par` 参数文件格式向后兼容。MAJOR 变更会提前一个 MINOR 版本发出弃用警告。

---

## 7. 变更决策流程

| 增量类型 | 决策者 | 是否需要创建 Issue |
|----------|--------|-------------------|
| PATCH | 开发者自行决定 | 否 |
| MINOR | 开发者 + 代码审查 | 建议 |
| MAJOR | 团队讨论 + 代码审查 | 是 |

---

*Last updated: 2026-07-05*
