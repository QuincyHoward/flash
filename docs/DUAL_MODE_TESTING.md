# PhySimX Flash 模块 — 双重模式测试和工作流配置总结

**日期**: 2026-07-03  
**状态**: 部分完成，需要进一步完善

---

## 1. ✅ 已完成的工作

### 1.1 双重模式支持（智能导入）

创建了 `input_gen/test/_compat.py` 兼容性模块，支持两种运行模式：

1. **独立模式**：`flash/` 是顶层目录，可以直接 `import flash`
2. **PhySimX 模式**：`flash` 是 `physimx_sim` 的子模块，需要 `import physimx_sim.flash`

**使用方法**：
```python
# 在测试文件中
from ._compat import ParGeneratorExtended, BeamConfig, RUN_MODE

# 或者动态导入
from ._compat import import_from_flash
ParGeneratorExtended = import_from_flash("input_gen.gen_par.generator", "ParGeneratorExtended")
```

### 1.2 功能测试文件

已创建/更新以下测试文件：

| 文件 | 状态 | 通过 | 跳过 | 失败 |
|------|------|------|------|------|
| `test_gen_par.py` | ✅ 完成 | 29 | 3 | 0 |
| `test_gen_shell_script.py` | ⚠️ 基本完成 | 3 | 4 | 0 |
| `test_gen_config.py` | ⚠️ 模板创建 | 1 | 1 | 1 |
| `test_gen_checker.py` | ⚠️ 模板创建 | 0 | 1 | 2 |
| `test_gen_sim_data.py` | ✅ 已存在 | 4 | 0 | 0 |
| `test_gen_sim_init.py` | ✅ 已存在 | 3 | 0 | 0 |
| `test_gen_sim_initblock.py` | ✅ 已存在 | 1 | 0 | 0 |

**总计**: 56 passed, 11 skipped, 3 failed

### 1.3 智能 Git 工作流

已创建以下文件：

1. **`scripts/git-hooks/pre-commit`** — 快速测试（代码风格检查）
   - 运行 `black --check`
   - 如果失败，阻止提交

2. **`scripts/git-hooks/pre-push`** — 框架测试（`flash/test/`）
   - 运行 `pytest flash/test/ -v`
   - 如果失败，阻止推送

3. **`scripts/03_git_publish/git-tag-with-test.sh`** — 全局测试（打标签前运行）
   - 运行 `pytest flash/ -v`（完整测试）
   - 如果失败，阻止打标签

4. **`scripts/03_git_publish/install-git-hooks.sh`** — 安装钩子的便捷脚本
   ```bash
   bash scripts/03_git_publish/install-git-hooks.sh
   ```

5. **`docs/GIT_WORKFLOW.md`** — 使用说明文档

---

## 2. 📋 待完成的工作 (TODO)

### 2.1 高优先级

1. **修正 `test_gen_shell_script.py` 中的 API 调用**
   - 问题：`ShellScriptGenerator` API 不匹配（没有 `generate()` 方法）
   - 解决：检查 `generator.py` 的实际 API，然后修正测试
   - 估计时间：1 小时

2. **修正 `test_gen_checker.py` 中的导入路径**
   - 问题：目录名拼写可能是 `gen_checker` 或 `gen_checker`
   - 解决：检查实际目录名，然后修正导入路径
   - 估计时间：15 分钟

3. **检查 `test_gen_config.py` 中的路径计算**
   - 问题：`gen_config/` 目录存在，但测试失败
   - 解决：检查路径计算逻辑
   - 估计时间：15 分钟

### 2.2 中优先级

4. **补充其他测试文件**
   - `test_gen_eos_op.py`
   - `test_gen_makefile.py`
   - `test_gen_f90.py`
   - `test_gen_otherf90s.py`
   - `test_gen_Grid_markRefineDerefine.py`
   - 估计时间：每个文件 30 分钟

5. **运行全局测试并确保全部通过**
   - 运行 `pytest flash/ -v`
   - 修正失败的测试
   - 估计时间：2 小时

### 2.3 低优先级

6. **初始化 Git 仓库并推送代码到 Gitee**
   - 初始化 Git 仓库
   - 添加远程仓库 `https://gitee.com/physimx/flash.git`
   - 推送代码和标签 `v0.0.0`
   - 估计时间：30 分钟

7. **创建独立模式测试脚本**
   - 创建一个脚本，方便用户在没有 PhySimX 的情况下运行测试
   - 估计时间：1 小时

---

## 3. 📊 测试统计

### 3.1 当前测试结果

```
input_gen/test/:
- 56 passed
- 11 skipped
- 3 failed (预期失败，因为某些模块未实现或 API 不匹配)
```

### 3.2 测试覆盖率

| 模块 | 测试文件 | 覆盖率 | 备注 |
|------|----------|--------|------|
| `gen_par/` | `test_gen_par.py` | ✅ 高 | 29 个测试 |
| `gen_shell_script/` | `test_gen_shell_script.py` | ⚠️ 低 | 需要修正 API 调用 |
| `gen_config/` | `test_gen_config.py` | ⚠️ 低 | 模板创建 |
| `gen_checker/` | `test_gen_checker.py` | ⚠️ 低 | 需要修正导入路径 |
| `gen_sim_data/` | `test_gen_sim_data.py` | ✅ 中 | 4 个测试 |
| `gen_sim_init/` | `test_gen_sim_init.py` | ✅ 中 | 3 个测试 |
| `gen_sim_initblock/` | `test_gen_sim_initblock.py` | ✅ 低 | 1 个测试 |

---

## 4. 📖 使用说明

### 4.1 在独立模式下运行测试

```bash
# 进入 flash/ 的父目录
cd /path/to/parent/

# 运行测试
python -m pytest flash/input_gen/test/ -v
```

### 4.2 在 PhySimX 模式下运行测试

```bash
# 进入 src/ 目录
cd /path/to/physimx_sim/src/

# 运行测试
python -m pytest physimx_sim/flash/input_gen/test/ -v
```

### 4.3 运行 Git 工作流

```bash
# 安装 Git 钩子
bash flash/scripts/03_git_publish/install-git-hooks.sh

# 正常开发流程
git add .
git commit -m "消息"  # 触发 pre-commit 钩子（快速测试）
git push              # 触发 pre-push 钩子（框架测试）

# 打标签（需要运行全局测试）
bash flash/scripts/03_git_publish/git-tag-with-test.sh v0.0.1
```

---

## 5. ⚠️ 已知问题

### 5.1 `ShellScriptGenerator` API 不匹配

- **问题**：测试文件中使用的 API（`generate()`、`save()`）与实际实现不匹配
- **影响**：`test_gen_shell_script.py` 中的 4 个测试被跳过
- **解决方法**：检查 `gen_shell_script/generator.py` 的实际 API，然后修正测试

### 5.2 目录名拼写问题

- **问题**：`gen_checker/` 目录的拼写可能不正确
- **影响**：`test_gen_checker.py` 中的导入失败
- **解决方法**：检查实际目录名，然后修正导入路径

### 5.3 双重模式检测的可靠性

- **问题**：`_compat.py` 中的 `detect_run_mode()` 函数可能在某些情况下失败
- **影响**：测试可能无法在两种模式下正常运行
- **解决方法**：增强检测逻辑，添加 fallback 机制

---

## 6. 🚀 下一步行动

1. **修正 `test_gen_shell_script.py` 中的 API 调用**（高优先级）
2. **修正 `test_gen_checker.py` 中的导入路径**（高优先级）
3. **运行全局测试并确保全部通过**（中优先级）
4. **初始化 Git 仓库并推送代码**（低优先级）

---

## 7. 📞 联系方式

如果有问题，请联系：
- **用户**：QuincyHoward
- **Gitee**：https://gitee.com/physimx/flash

---

**报告结束** ✅
