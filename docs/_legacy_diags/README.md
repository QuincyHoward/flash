# _legacy_diags — 历史一次性诊断脚本收纳区（指定归档文件夹）

> 2026-10-27 全库去硬编码改造（见仓库根《硬编码位置及修改计划.md》）建立。
> **本目录是全仓库唯一允许保留历史机器绝对路径的代码区**（身份泄漏守卫的豁免区）。

## 收纳内容（原始位置 → 现位置）

| 原始位置 | 现位置 | 说明 |
|---|---|---|
| `flash/input_gen/gen_eos_op/src/multi_src/01_inventory/` | `multi_src_01_inventory/` | MultiEOSOP 源码盘点一次性脚本 |
| `flash/input_gen/gen_eos_op/src/multi_src/02_doc_extract/` | `multi_src_02_doc_extract/` | 文档抽取一次性脚本 |
| `flash/input_gen/gen_eos_op/src/multi_src/04_probe/` | `multi_src_04_probe/` | 格式探测一次性脚本 + 报告 |
| `flash/input_gen/gen_eos_op/src/multi_src/06_agent_reports/` | `multi_src_06_agent_reports/` | 阶段性 agent 报告 |
| `flash/input_gen/gen_eos_op/src/multi_src/07_doc_build/` | `multi_src_07_doc_build/` | 文档构建一次性脚本 |
| `flash/input_gen/gen_eos_op/src/multi_src/08_audit/` | `multi_src_08_audit/` | 审计一次性脚本 |
| `flash/input_gen/gen_eos_op/src/multi_src/09_source_verify/` | `multi_src_09_source_verify/` | 源码核验一次性脚本 |
| `flash/scenarios/private/tracer/SNB/SNBOneCH_ml/tools_local/cores_parallel_diag_20260912/` | `cores_parallel_diag_20260912/` | 核数并行诊断归档（2026-09-12） |

另：`docs/_diagnostics/2026-09-12_snb_debug/`（SNB 调试一次性脚本，22 MB）已于同日
**删除**，完整备份在仓库外 `../flash_backup_20261027/docs__diagnostics/`
（git 分支 `backup/pre-dehardcode-20261027` 亦可恢复）。

## 约定

1. **只进不出、只减不增**：新的一次性诊断脚本不得再落仓库活跃区；进入本目录
   视为永久归档，不再维护、不再运行。
2. 脚本内的 `E:\PhySimX\...`、`C:\Users\<用户名>` 等为**历史快照**，反映当时的
   机器布局；不指当前仓库，不可直接运行。
3. 身份泄漏守卫（gen_checker）对本目录豁免；在本目录之外出现同类硬编码即 CI 失败。
4. 引用这些目录的文档（multi_src/README.md、MANIFEST.tsv 等）为历史记录，
   路径描述以本 README 为准。
