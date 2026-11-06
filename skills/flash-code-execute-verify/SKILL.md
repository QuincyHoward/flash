---
name: flash-code-execute-verify
description: 代码级执行验证纪律：AI 添加/修改代码后必须实际运行代码验证功能正确，禁止仅做语法检查就声称完成。写新函数/类/模块、迁移老代码、修改现有逻辑后必须触发。与场景级短时验证（flash-scenario-setup）构成两级验证链。触发词：写完代码、改代码完成、验证一下、跑通、execute verify。
---

> 最后核对：2026-11-06 · commit 54a9f69
> 来源：用户级同名技能吸收（原名 physimx-code-execute-verify，2026-11-06 统一更名 flash- 格式；原文核心保留，补充本仓两级验证分工）

# 代码执行验证（Code Execute & Verify）

## 与场景级验证的分工

- **本技能 = 代码级**：写/改 Python 代码后必须实际运行 + 边界测试
- **场景级 = flash-scenario-setup 短时验证**：FLASH 场景配置好后 `tmax≈1e-11` 短时跑 + `--smoke`，检查中间输出
- 两级构成验证链：**代码跑得通 → 场景跑得过**，缺一不可

## 强制工作流（按顺序，不可跳过）

### Step 1: 写代码
类型注解 + docstring 基本齐全。

### Step 2: 实际运行（禁止仅 `py_compile` 语法检查）
```bash
# 方法1：直接运行脚本
python script.py

# 方法2：最小集成测试（合成输入 + 断言）
python -c "
from flash.input_gen.gen_par import ParGeneratorExtended
gen = ParGeneratorExtended(simulation_name='T', dimension=1)
gen.set('lrefine_max', 5)
assert gen.get('lrefine_max') == 5
print('OK: set/get')
"
```
- `ModuleNotFoundError` → 先装依赖；`ImportError/SyntaxError` → 修代码回到 Step 1；`RuntimeError` → 读 traceback 修逻辑

### Step 3: 边界测试
空输入/None、越界参数、文件不存在、类型错误至少各验一类。

### Step 4: 确认通过
输出 `✅ 验证通过：<模块名> - <功能描述>`，附测试输入与输出摘要。

## 失败处理规则

- 同一错误失败 2 次 → 换思路，不死循环
- 依赖安装失败 → 报告用户说明依赖问题
- 逻辑错误无法自修 → 向用户描述问题等待指导
- FLASH 场景类验证失败 → 转 `flash-pitfalls` 按报错检索根因

## 禁止行为

- ❌ 仅语法检查/仅看代码就声称"完成"
- ❌ 不运行任何命令就跳过测试
- ❌ 连续 3 次运行失败仍不换策略
- ❌ `python -c` 塞超过 30 行复杂代码（写成临时文件再跑）
