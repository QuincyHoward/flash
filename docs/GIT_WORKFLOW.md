# Git 工作流指南

本文档说明如何使用智能 Git 钩子和脚本，实现不同 git 操作运行不同测试。

> 完整脚本说明参见: `flash/scripts/README.md`

## 概述

我们配置了以下 Git 钩子和脚本：

| Git 操作 | 触发的测试 | 配置文件 |
|----------|------------|----------|
| `git commit` | 快速测试（代码风格检查） | `scripts/git-hooks/pre-commit` |
| `git push` | Flash 框架测试（`flash/test/`） | `scripts/git-hooks/pre-push` |
| `git tag`（自定义脚本） | 全局测试（`flash/test/` + `input_gen/test/` + 其他模块） | `scripts/git-tag-with-test.sh` |
| `tag-release.sh`（自定义脚本） | 格式检查 + linting + 全局测试 + 构建 | `scripts/tag-release.sh` |

## 安装 Git 钩子

默认情况下，Git 钩子不会自动安装。你需要运行以下命令来安装钩子：

```bash
# 进入项目根目录
cd /path/to/physimx_sim/

# 创建符号链接（推荐）
ln -s ../../scripts/git-hooks/pre-commit .git/hooks/pre-commit
ln -s ../../scripts/git-hooks/pre-push .git/hooks/pre-push

# 或者复制文件
cp scripts/git-hooks/pre-commit .git/hooks/pre-commit
cp scripts/git-hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-commit .git/hooks/pre-push
```

## 使用说明

### 1. `git commit` — 快速测试

当你运行 `git commit` 时，`pre-commit` 钩子会自动运行：

```bash
git commit -m "feat: 添加新功能"
```

**触发的测试：**
- Black 代码风格检查（`black --check`）
- 导入检查（确保 `flash` 模块可导入）

**如果检查失败：**
- Commit 将被中止
- 你需要修复问题后重新 commit

**跳过检查：**
```bash
git commit --no-verify -m "feat: 添加新功能"
```

### 2. `git push` — 框架测试

当你运行 `git push` 时，`pre-push` 钩子会自动运行：

```bash
git push origin main
```

**触发的测试：**
- Flash 框架测试（`flash/test/` 目录下的所有测试）

**如果测试失败：**
- Push 将被中止
- 你需要修复测试后重新 push

**跳过测试：**
```bash
git push --no-verify origin main
```

### 3. `git tag` — 全局测试（自定义脚本）

由于 `git tag` 不会触发 Git 钩子，我们使用自定义脚本 `git-tag-with-test.sh`：

```bash
# 用法
./scripts/git-tag-with-test.sh <tag_name> [tag_message]

# 示例
./scripts/git-tag-with-test.sh v0.0.1 "Version 0.0.1 release"
```

**触发的测试：**
- Flash 框架测试（`flash/test/`）
- Input gen 测试（`flash/input_gen/test/`）
- 其他模块测试（如果存在）

**如果测试失败：**
- 标签创建将被中止
- 你需要修复测试后重新运行脚本

**手动打标签（跳过测试）：**
```bash
git tag -a v0.0.1 -m "Version 0.0.1 release"
git push origin v0.0.1
```

### 4. `tag-release.sh` — 完整发布流程（可选）

`tag-release.sh` 提供更完整的发布流程（格式检查 + linting + 测试 + 构建）：

```bash
# 用法
bash scripts/tag-release.sh <version>

# 示例
bash scripts/tag-release.sh v0.2.0
```

**执行步骤：**
1. Black 代码格式检查
2. Ruff linting 检查
3. 全局测试（flash/test + input_gen/test + output_processors/test）
4. 构建检查（pip install build + python -m build）
5. 创建 git 标签

**如果任何步骤失败：**
- 脚本将中止（set -e）
- 你需要修复问题后重新运行

## 测试分层策略

我们采用测试分层策略，确保不同阶段的代码质量：

### 快速测试（ commit 前）
- **目的：** 快速检查代码风格和导入
- **耗时：** < 5 秒
- **覆盖：** 代码风格、导入检查

### 框架测试（ push 前）
- **目的：** 确保核心功能正常
- **耗时：** < 1 分钟
- **覆盖：** Flash 框架核心模块

### 全局测试（打标签前）
- **目的：** 确保全部功能正常
- **耗时：** < 5 分钟
- **覆盖：** 全部模块

## 编写测试

### 测试文件位置

- **Flash 框架测试：** `flash/test/`
- **Input gen 测试：** `flash/input_gen/test/`
- **Output processors 测试：** `flash/output_processors/test/`
- **其他模块测试：** 对应模块的 `test/` 目录

### 测试编写规范

1. **每个模块一个测试文件：**
   ```
   flash/input_gen/test/test_gen_par.py
   flash/input_gen/test/test_gen_shell_script.py
   ```

2. **测试类组织：**
   ```python
   class TestClassNameImport:
       """导入测试。"""

   class TestClassNameInit:
       """初始化测试。"""

   class TestClassNameGenerate:
       """生成测试。"""

   class TestClassNameSave:
       """保存测试。"""

   class TestClassNameEdgeCases:
       """边界测试。"""

   class TestClassNameIntegration:
       """集成测试。"""
   ```

3. **使用 fixture：**
   ```python
   @pytest.fixture
   def tmp_output_dir(tmp_path):
       return tmp_path / "output"
   ```

## 跳过测试

如果某些测试暂时无法运行，可以使用以下方法跳过：

### 1. 跳过整个模块

```python
import pytest
pytest.skip("原因：功能尚未实现", allow_module_level=True)
```

### 2. 跳过单个测试

```python
@pytest.mark.skip(reason="功能尚未实现")
def test_something():
    pass
```

### 3. 条件跳过

```python
@pytest.mark.skipif(sys.platform == "win32", reason="在 Windows 上不支持")
def test_something():
    pass
```

##  Troubleshooting

### 1. 钩子不触发

**可能原因：**
- 钩子未安装（缺少符号链接或复制）
- 钩子文件没有执行权限

**解决方法：**
```bash
# 检查钩子是否存在
ls -la .git/hooks/pre-commit .git/hooks/pre-push

# 重新安装钩子
ln -s ../../scripts/git-hooks/pre-commit .git/hooks/pre-commit
ln -s ../../scripts/git-hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-commit .git/hooks/pre-push
```

### 2. Python 路径错误

**可能原因：**
- `PYTHONPATH` 未正确设置
- 钩子中的 Python 路径不正确

**解决方法：**
编辑 `scripts/git-hooks/pre-commit` 和 `scripts/git-hooks/pre-push`，确保 `PYTHON` 变量指向正确的 Python 解释器。

### 3. 测试失败

**解决方法：**
1. 查看测试输出，定位失败原因
2. 修复代码或测试
3. 重新运行 `git commit` / `git push` / `./scripts/git-tag-with-test.sh`

## 行尾格式规范

**所有源文件必须使用 Unix (LF) 换行符**，禁止 Windows CRLF。

### 原因
FLASH 仿真在 Linux 超算上运行，CRLF 会导致：
- Shell 脚本 (`#!/bin/bash`) 报 `$'\r': command not found`
- Fortran 编译器解析错误
- `.par` 参数文件解析异常

### 保障机制
- `.gitattributes`（已提交至仓库根目录）：强制 `* text=auto eol=lf`，二进制文件除外
- git 本地配置：`core.autocrlf=input`，`core.eol=lf`
- 所有 956 个源文件已完成 CRLF → LF 转换

### Git 钩子检查
`pre-commit` 钩子会自动检查新增文件的换行符是否符合规范。

## 示例工作流

### 完整的功能开发工作流

```bash
# 1. 创建功能分支
git checkout -b feat/new-feature

# 2. 开发功能
# ... 编写代码 ...

# 3. 编写测试
# ... 编写测试用例 ...

# 4. 提交（触发快速测试）
git add .
git commit -m "feat: 添加新功能"

# 5. 推送（触发框架测试）
git push origin feat/new-feature

# 6. 合并到主分支
git checkout main
git merge feat/new-feature

# 7. 打标签（触发全局测试）
./scripts/git-tag-with-test.sh v0.1.0 "Version 0.1.0 release"
```

## Python 路径配置

所有 shell 脚本（`git-tag-with-test.sh`、`git-hooks/pre-commit`、`git-hooks/pre-push`）支持通过环境变量 `PYTHON` 覆盖默认的 Python 路径：

```bash
# 默认路径 (WSL)
/c/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe

# 自定义 Python 路径
export PYTHON=/usr/bin/python3
bash scripts/git-tag-with-test.sh v0.1.0

# 或使用系统默认 python3
export PYTHON=python3
git commit -m "feat: add new feature"
```

如果默认路径不存在，脚本会自动尝试从 PATH 查找 `python3` 或 `python`。

## 总结

通过配置智能 Git 钩子和脚本，我们实现了：

1. **自动化测试：** 不同 git 操作自动运行不同测试
2. **测试分层：** 快速测试（commit）→ 框架测试（push）→ 全局测试（tag）
3. **代码质量保障：** 确保提交的代码符合风格规范，核心功能正常，全部功能正常
4. **灵活配置：** 支持通过环境变量覆盖 Python 路径

完整脚本说明参见: `flash/scripts/README.md`

如果你有任何问题或建议，请提出 Issue 或 Pull Request。

---

## 版本号协议

版本号遵循 **Semantic Versioning (SemVer)** 规范，详见 [`docs/VERSIONING.md`](VERSIONING.md)。
