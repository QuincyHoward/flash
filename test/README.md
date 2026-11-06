> 最后核对：2026-11-06 · commit 20337b6（flash-readme-sync 首轮补写）

# 仓库根测试目录（pytest 三套件之架构/集成腿）

## 职责

flash-sim 包的跨模块 pytest 测试与测试期辅助工具：架构守卫、解耦回归、
场景系统、运行模式、接口契约、远程部署/作业链等集成级测试。

## 内容清单

| 文件/目录 | 说明 |
|---|---|
| `conftest.py` | 共享 fixture；向上搜索项目根并把包根加入 sys.path（源码树直跑 `flash.` 导入） |
| `test_arch_guards.py` | 架构守卫测试（模块边界/分层约束） |
| `test_decoupling_regressions.py` | 解耦回归（防模块间隐性耦合回潮） |
| `test_scenario_layer.py` / `test_scenarios_modes.py` / `test_exec_targets.py` | 场景系统与三模式/执行目标 |
| `test_interface.py` / `test_flash_simulator.py` | 对外接口与模拟器契约 |
| `test_flash_env_manager.py` / `test_flash_remote_deploy.py` / `test_slurm_control.py` / `test_job_layout.py` / `test_job_submit.py` / `test_insitu_runner.py` | 运行/远程/作业链 |
| `test_flash_input_gen.py` / `test_flash_output_processors.py` | 生成器与输出处理集成测试 |
| `test_gitee.py` / `test_math_test.py` / `test_flash_math_test.py` | 仓库/数学测试自检 |
| `_extract_chk_params.py` / `bench_sftp.py` / `check_gen_par_comments.py`（+ `.par`） | 测试辅助脚本 |
| `hdf5ploter_easy/` `newpara/` `outputfiles/` `remote_connect/` `reports/` `scenarios/` | 分主题测试子目录（remote_connect 含 diagnostics/test_sbatch） |

## 运行

```bash
make test        # pytest 三套件
pytest test/ -q  # 仅本目录
```

## 关联资源

- `flash/input_gen/test/`（input_gen 单测）、`flash/output_pro/test/`（输出处理单测）、`docs/GIT_WORKFLOW.md`（测试分层策略）
