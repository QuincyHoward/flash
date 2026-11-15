# scripts/05_test — 全局测试运行器

> 最后核对：2026-11-15 · commit 97d5e5d

**职责**：一键运行三套 pytest（框架 / 输入生成 / 输出处理），是提交钩子与发版流程的测试入口。

## 文件清单

| 文件 | 职责 |
|---|---|
| `run_global_tests.py` | 默认跑三套；`--framework` / `--input` / `--output` 单跑；`--module PATH` 指定用例；`--list` 只列举；`-v` 详细输出 |

## 常用命令

```bash
python scripts/05_test/run_global_tests.py
python scripts/05_test/run_global_tests.py --framework
python scripts/05_test/run_global_tests.py --module flash/test/
python scripts/05_test/run_global_tests.py --list
```

## 测试分层

| 层级 | 触发时机 | 内容 |
|---|---|---|
| 框架测试 | `git push` 的 pre-push 钩子 | flash 框架用例 |
| 全局三套 | 打标签发版前 | framework + input_gen + output_pro |
| 文档门禁 | 文档变更后 | [../08_docs/check_docs.py](../08_docs/check_docs.py) |

输出层测试的 HDF5 数据按需生成、通过后自动清理；失败时保留供调试，调试完成后再手动清理。

**上级导航**：[../README.md](../README.md)
