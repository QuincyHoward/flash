# 本地 CI 指南

本文档说明 PhySimX Flash 项目的本地 CI 工作流，包括 Git 钩子配置和测试命令。

---

## 1. 安装依赖

### 首次设置

```bash
# 安装项目（开发模式）
pip install -e ".[dev]"

# 安装 pre-commit 框架
pip install pre-commit

# 初始化 Git 钩子
pre-commit install
pre-commit install --hook-type pre-push
```

### 依赖说明

开发依赖（`pyproject.toml` 中的 `[project.optional-dependencies] dev`）：

- `pytest>=7.0` - 测试框架
- `pytest-cov` - 测试覆盖率
- `black` - 代码格式化
- `ruff` - 代码检查

---

## 2. Git 钩子说明

项目配置了以下 Git 钩子（通过 `.pre-commit-config.yaml` 管理）：

### Pre-commit 钩子（`git commit` 时触发）

**运行内容**：
1. **Black 检查** - 检查代码格式是否符合规范
2. **Ruff 检查** - 检查代码是否有 linting 错误

**耗时**: 几秒钟

**失败处理**: 
- 如果 Black 或 Ruff 检查失败，`git commit` 会被阻止
- 运行 `make format` 自动修复格式问题
- 再次运行 `git commit`

**示例**：
```bash
$ git commit -m "Add new feature"
black................................................(no files to format)
ruff.............................................................(no fixed)
[main abc1234] Add new feature
 2 files changed, 10 insertions(+), 5 deletions(-)
```

### Pre-push 钩子（`git push` 时触发）

**运行内容**：
1. **Flash 框架测试** - 运行 `pytest test -v`（主项目测试）

**耗时**: 几分钟

**失败处理**: 
- 如果测试失败，`git push` 会被阻止
- 修复测试失败的问题
- 再次运行 `git push`

**示例**：
```bash
$ git push origin main
pytest-flash-framework.......................................(running)
======================== test session starts ========================
test/test_interface.py::test_flash_simulator PASSED            [ 50%]
test/test_interface.py::test_flash_simulator_invalid_request PASSED [100%]
======================== 2 passed in 1.23s ========================
```

---

## 3. 测试命令

### 快速测试（Flash 框架测试）

```bash
# 使用 make
make test

# 或直接运行 pytest
pytest test -v
```

**测试范围**: `test/` 目录（主项目测试）

**耗时**: 几分钟

**适用场景**: 
- 日常开发（每次 push 前自动运行）
- 快速验证功能是否正常

### 全局测试（所有子模块测试）

```bash
# 使用 make
make test-all

# 或直接运行脚本
./scripts/tag-release.sh v0.2.0
```

**测试范围**: 
1. `test/` - 主项目测试
2. `input_gen/test/` - 输入生成模块测试
3. `output_processors/test/` - 输出处理模块测试
4. `output_processors/inputfiles/test/` - 输出处理器输入文件测试

**耗时**: 几十分钟

**适用场景**: 
- 发布前（打标签前）
- 定期检查（如每周一次）

---

## 4. 代码检查和格式化

### 代码格式检查

```bash
# 使用 make
make lint

# 或直接运行
black --check . --line-length=120
ruff check .
```

**失败处理**: 
- 运行 `make format` 自动修复
- 或手动修复 Ruff 报告的问题

### 自动格式化代码

```bash
# 使用 make
make format

# 或直接运行
black . --line-length=120
ruff check --fix .
```

**效果**: 
- Black 自动格式化代码
- Ruff 自动修复部分 linting 问题

---

## 5. 标签发布流程

### 为什么需要标签发布脚本？

标签（Tag）通常用于标记版本发布（如 `v0.2.0`）。在打标签前，应该确保：
1. 代码格式正确
2. 所有测试通过
3. 构建检查通过

`scripts/tag-release.sh` 脚本会自动执行这些检查。

### 使用方式

```bash
# 1. 确保你在主分支
git checkout main
git pull origin main

# 2. 运行标签发布脚本
chmod +x scripts/tag-release.sh  # 首次需要
./scripts/tag-release.sh v0.2.0

# 3. 脚本会运行：
#    - 代码格式检查
#    - Linting 检查
#    - 全局测试（所有 4 个测试目录）
#    - 构建检查
#    - 打标签

# 4. 推送标签
git push origin v0.2.0
```

### 脚本行为

- ✅ **任何检查失败**，脚本会立即退出，不会打标签
- ✅ **所有检查通过**，会自动打标签
- ✅ **标签打好后**，需要手动推送标签到远程

---

## 6. 跳过 Git 钩子（不推荐）

在某些情况下（如紧急修复），可能需要跳过 Git 钩子：

### 跳过 Pre-commit 钩子

```bash
git commit --no-verify -m "Emergency fix"
# 或
git commit -n -m "Emergency fix"
```

### 跳过 Pre-push 钩子

```bash
git push --no-verify origin main
# 或
git push -n origin main
```

### ⚠️ 警告

- **不推荐跳过钩子**，除非绝对必要
- **跳过钩子可能导致**：代码格式不一致、测试失败代码被推送
- **如果跳过了钩子**，请在推送后手动运行 `make check` 确保没有问题

---

## 7. 常见问题

### Q1: Pre-commit 钩子运行太慢怎么办？

**A**: 
- Black 和 Ruff 通常很快（几秒钟）
- 如果确实慢，可以只运行修改的文件：
  ```bash
  pre-commit run --files flash/some_file.py
  ```

### Q2: Pre-push 钩子运行测试太慢怎么办？

**A**: 
- Flash 框架测试（`pytest test -v`）通常几分钟
- 如果确实慢，可以跳过 pre-push 钩子（不推荐）：
  ```bash
  git push --no-verify origin main
  ```
- 但请在推送后手动运行测试

### Q3: 如何只运行某个测试文件？

**A**: 
```bash
pytest test/test_interface.py -v
```

### Q4: 如何只运行某个测试函数？

**A**: 
```bash
pytest test/test_interface.py::test_flash_simulator -v
```

### Q5: 如何跳过慢速测试？

**A**: 
- 如果测试标记了 `@pytest.mark.slow`，可以：
  ```bash
  pytest -m "not slow" -v
  ```

---

## 8. 下一步

- 配置 Gitee 私有仓库：查看 `docs/gitee-private-setup.md`
- 查看项目配置：`pyproject.toml`

---

**文档版本**: 2026-07-03
