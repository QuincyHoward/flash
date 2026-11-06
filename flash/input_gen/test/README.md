> 最后核对：2026-11-06 · commit 20337b6（flash-readme-sync 首轮补写）

# input_gen 单元测试

## 职责

`flash/input_gen/` 各 gen_* 子包的单元测试（生成内容正确性、兼容性）。

## 内容清单

| 文件 | 覆盖 |
|---|---|
| `test_gen_par.py` | ParGeneratorExtended（参数/脉冲/光束/物质绑定） |
| `test_gen_config.py` | ConfigGenerator |
| `test_gen_makefile.py` | MakefileGenerator |
| `test_gen_sim_data.py` / `test_gen_sim_init.py` / `test_gen_sim_initblock.py` | F90 生成器 |
| `test_gen_eos_op.py` | EOS/Opacity 表复制 |
| `test_gen_checker.py` | DependencyChecker |
| `test_gen_shell_script.py` | ShellScriptGenerator |
| `test_demo_scripts_compat.py` / `_compat.py` / `conftest.py` | 演示脚本兼容性与共享固件 |

## 运行

```bash
pytest flash/input_gen/test -q
```

## 关联资源

- `flash/input_gen/README.md`（被测子包总览）、`skills/flash-input-gen/`
