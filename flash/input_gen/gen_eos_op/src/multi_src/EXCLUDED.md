# EXCLUDED —— 未收录项及理由

`.workbuddy/tmp/` 中另有 **110 项不属于本文档工作流**，故未复制到 `multi_src/`。
它们属于**同一仓库的另一条工作流 —— `eosop_pro` Python 包的开发轮次 (r11–r16)**，
内容为包自身的回归测试日志、提交信息、绘图重绘输出、字段校验再生成等，
与《MultiEOSOP格式说明.md》的**格式规格**工作无关。

**处置**：保留在 `.workbuddy/tmp/` 原位，不删除、不搬运（避免污染两条工作流的归档）。

## 排除清单

| # | 名称 | 归类 |
|---|---|---|
| 1 | `affected_r15.log` | 绘图与拟合检查 (r15) |
| 2 | `affected_tail_r15.txt` | 绘图与拟合检查 (r15) |
| 3 | `append_r12_log.py` | 模块重构与记忆精简 (r12–r14) |
| 4 | `append_r14_log.py` | 模块重构与记忆精简 (r12–r14) |
| 5 | `clear_check_r15.txt` | 绘图与拟合检查 (r15) |
| 6 | `clear_plots_r15.py` | 绘图与拟合检查 (r15) |
| 7 | `cn4fit_probe_r15.py` | 声速/热力学模块调试 (r16) |
| 8 | `commit_msg_r12.txt` | Git 提交信息/校验 |
| 9 | `commit_msg_r13.txt` | Git 提交信息/校验 |
| 10 | `commit_msg_r14.txt` | Git 提交信息/校验 |
| 11 | `commit_msg_r15.txt` | Git 提交信息/校验 |
| 12 | `commit_msg_r16.txt` | Git 提交信息/校验 |
| 13 | `commit_msg_r16b.txt` | Git 提交信息/校验 |
| 14 | `commit_msg_r16c_cleanup.txt` | Git 提交信息/校验 |
| 15 | `commit_verify_r15.txt` | Git 提交信息/校验 |
| 16 | `commit_verify_r16.txt` | Git 提交信息/校验 |
| 17 | `commit_verify_r16b.txt` | Git 提交信息/校验 |
| 18 | `del_family_dirs.py` | 模块重构与记忆精简 (r12–r14) |
| 19 | `demo_sync_r12.py` | 模块重构与记忆精简 (r12–r14) |
| 20 | `diag_gsound_r16.txt` | 声速/热力学模块调试 (r16) |
| 21 | `drop_shorttable_r14.py` | 模块重构与记忆精简 (r12–r14) |
| 22 | `fit_check_r15` | 绘图与拟合检查 (r15) |
| 23 | `fit_probe_err_r15.txt` | 绘图与拟合检查 (r15) |
| 24 | `fit_probe_exit.txt` | 绘图与拟合检查 (r15) |
| 25 | `git_diag_r16.txt` | Git 与环境检查 |
| 26 | `git_diff_body_r15.txt` | Git 与环境检查 |
| 27 | `git_diff_fit_r15.txt` | Git 与环境检查 |
| 28 | `git_diff_r15.txt` | Git 与环境检查 |
| 29 | `git_status_r15.txt` | Git 与环境检查 |
| 30 | `git_status_r16.txt` | Git 与环境检查 |
| 31 | `gitignore_check_r16.txt` | Git 与环境检查 |
| 32 | `guess_smoke.txt` | 包测试与参数扫描 |
| 33 | `guess_uk_summary.log` | 包测试与参数扫描 |
| 34 | `hugo_enc_check.txt` | Git 与环境检查 |
| 35 | `inline_short_r14.py` | 模块重构与记忆精简 (r12–r14) |
| 36 | `linecheck_r16.txt` | Git 与环境检查 |
| 37 | `linecheck_r16b.txt` | Git 与环境检查 |
| 38 | `log_tail_r16.txt` | 其它（包开发） |
| 39 | `mem_len2_r16.txt` | 记忆长度检查 |
| 40 | `mem_len3_r16.txt` | 记忆长度检查 |
| 41 | `mem_len_r16.txt` | 记忆长度检查 |
| 42 | `mem_r13.py` | 模块重构与记忆精简 (r12–r14) |
| 43 | `migrate_cn4_r13.py` | 模块重构与记忆精简 (r12–r14) |
| 44 | `msg_utf8_check.txt` | Git 与环境检查 |
| 45 | `ne_smoke` | 包测试与参数扫描 |
| 46 | `orphan_del_r15.txt` | 绘图与拟合检查 (r15) |
| 47 | `patch_docstrings.log` | 包测试与参数扫描 |
| 48 | `patch_docstrings.py` | 包测试与参数扫描 |
| 49 | `patch_tags_scheme.py` | 包测试与参数扫描 |
| 50 | `patch_tags_scheme2.py` | 包测试与参数扫描 |
| 51 | `patch_test_plots.py` | 包测试与参数扫描 |
| 52 | `patch_test_plots2.py` | 包测试与参数扫描 |
| 53 | `png_left_r15.txt` | 绘图与拟合检查 (r15) |
| 54 | `redraw_step01_r15.log` | 绘图与拟合检查 (r15) |
| 55 | `redraw_step01_tail_r15.txt` | 绘图与拟合检查 (r15) |
| 56 | `redraw_step02_r15.log` | 绘图与拟合检查 (r15) |
| 57 | `redraw_step02_tail_r15.txt` | 绘图与拟合检查 (r15) |
| 58 | `regress_count_r15.txt` | 包回归测试日志 |
| 59 | `regress_count_r16.txt` | 包回归测试日志 |
| 60 | `regress_r11.log` | 包回归测试日志 |
| 61 | `regress_r12.log` | 包回归测试日志 |
| 62 | `regress_r13.log` | 包回归测试日志 |
| 63 | `regress_r14.log` | 包回归测试日志 |
| 64 | `regress_r15.log` | 包回归测试日志 |
| 65 | `regress_r16.log` | 包回归测试日志 |
| 66 | `regress_r16_summary.txt` | 包回归测试日志 |
| 67 | `regress_r16b.log` | 包回归测试日志 |
| 68 | `regress_r16b_fail.txt` | 包回归测试日志 |
| 69 | `regress_r16c.log` | 包回归测试日志 |
| 70 | `regress_r16c_count.txt` | 包回归测试日志 |
| 71 | `regress_r16d.log` | 包回归测试日志 |
| 72 | `regress_summary_r15.txt` | 包回归测试日志 |
| 73 | `regression_final2.txt` | 包回归测试日志 |
| 74 | `regression_phase_c.txt` | 包回归测试日志 |
| 75 | `regression_tags_scheme.txt` | 包回归测试日志 |
| 76 | `regression_twotier.txt` | 包回归测试日志 |
| 77 | `regression_twotier2.txt` | 包回归测试日志 |
| 78 | `round10_fieldchecks_regen.log` | 包回归测试日志 |
| 79 | `run_affected_r14.py` | 包测试与参数扫描 |
| 80 | `run_capture.py` | 包测试与参数扫描 |
| 81 | `run_guess_uk.py` | 包测试与参数扫描 |
| 82 | `run_sv_r16.log` | 声速/热力学模块调试 (r16) |
| 83 | `run_sv_r16_clean.txt` | 声速/热力学模块调试 (r16) |
| 84 | `run_sv_r16b.log` | 声速/热力学模块调试 (r16) |
| 85 | `run_sv_r16b_clean.txt` | 声速/热力学模块调试 (r16) |
| 86 | `run_sv_r16c.log` | 声速/热力学模块调试 (r16) |
| 87 | `run_sv_r16c_clean.txt` | 声速/热力学模块调试 (r16) |
| 88 | `run_sweep.py` | 包测试与参数扫描 |
| 89 | `shrink_memory_r14.py` | 模块重构与记忆精简 (r12–r14) |
| 90 | `shrink_memory_r14b.py` | 模块重构与记忆精简 (r12–r14) |
| 91 | `shrink_memory_r14c.py` | 模块重构与记忆精简 (r12–r14) |
| 92 | `solid_results.txt` | 包测试与参数扫描 |
| 93 | `solid_t1.log` | 包测试与参数扫描 |
| 94 | `solid_t1b.log` | 包测试与参数扫描 |
| 95 | `solid_t1b_results.txt` | 包测试与参数扫描 |
| 96 | `solid_t2.log` | 包测试与参数扫描 |
| 97 | `solid_t3.log` | 包测试与参数扫描 |
| 98 | `solid_t3_results.txt` | 包测试与参数扫描 |
| 99 | `stats_step02.py` | 包测试与参数扫描 |
| 100 | `stats_step02_out.txt` | 包测试与参数扫描 |
| 101 | `step01_regenerated_r15.txt` | 包测试与参数扫描 |
| 102 | `step02_rerun.txt` | 包测试与参数扫描 |
| 103 | `sv_diag_r16.py` | 声速/热力学模块调试 (r16) |
| 104 | `sv_probe_r16.py` | 声速/热力学模块调试 (r16) |
| 105 | `sv_single_results.txt` | 声速/热力学模块调试 (r16) |
| 106 | `sv_t1.log` | 声速/热力学模块调试 (r16) |
| 107 | `sv_t2.log` | 声速/热力学模块调试 (r16) |
| 108 | `tpl_path.txt` | 包测试与参数扫描 |
| 109 | `tpl_r15.log` | 包测试与参数扫描 |
| 110 | `tree_step02.txt` | 包测试与参数扫描 |

## 如需追查

```
.workbuddy/tmp/    ← 全部原始文件仍在原位（未删改）
```

这两条工作流共用同一个 `tmp/` 是历史原因；如后续要彻底分离，建议把包开发产物迁到
`.workbuddy/tmp_eosop/`，并在本文件同步更新排除规则。
