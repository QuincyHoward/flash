# legacy/ — 一次性工具归档区（2026-11-05 归档）
> 最后核对：2026-11-05 · commit 7e04857


本目录收纳 2026-09~10 月 private/tracer 家族建设期的**一次性批量工具**。
它们的 docstring 与路径锚点均指向旧的 `flash/scenarios/private/tracer/`
平铺布局（`HERE/"CHTi"/...` 兄弟目录式定位），**在现位置多数已失效**——
使命已完成（家族场景与 `.par` 均已生成、清单已执行完毕），故归档留档。

## 归档清单与使命状态

| 文件 | 使命 | 状态 |
|---|---|---|
| `build_family.py` / `build_sic_family.py` / `build_titi_family.py` / `build_vti_family.py` | CHTi/OneSi/TiTi/VTi 家族场景派生器 | ✅ 产物已生成 |
| `run_ml_suite.py` / `run_titi_suite.py` / `run_vti_suite.py` / `run_sic_suite.py` | 家族一键批量极短验证 | ✅ 已执行 |
| `run_msfix_rerun.py` / `submit_msfix_all.py` | ms_shldA/Z 事故修复重算（2026-10-18） | ✅ 已完成 |
| `audit_material_bindings.py` | 材料绑定五元组审计 | ✅ 一次性质检 |
| `compare_old_par.py` | VTi_old vs 新 VTi par 差异 | ✅ 已比对 |
| `fetch_hpc_inputs.py` | 回取超算提交输入 | ⚠️ 需场景根参数 |
| `_par_layers.py` | 旧 par 全文快照（**禁止 import**，物性基线已迁 `flash.input_gen.gen_par.defaults.LAYER_TRACER_BASELINE`） | 🗄️ 只读留档 |

## 若需复用

1. 修改文件头部的 `HERE = Path(__file__).parent` 类锚点，指向目标场景族根
   （推荐改用 `flash.scenarios.core.scene_paths.scenarios_root()` 或经
   `core.scene_reg.discovery` 按场景名定位）；
2. 核对 docstring 中的用法路径；
3. 注意 `flash/scenarios/private/tracer/VTi_oldstyle/watch_l500.py` 仍以
   旧兄弟路径调用 `fetch_hpc_inputs.py`（断链已挂账 KNOWN_DEBT，复用时一并修）。
