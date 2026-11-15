# scenarios/scripts/relocate

> 最后核对：2026-11-11

**一句话职责**：场景收纳整理工具链（五件套）

**内容导航**：audit_portable.py（可移植性审计, strict 须 ERROR=0）· make_scene_portable.py（manifests/parents/initfiles 幂等改造）· decouple_imports.py（跨场景 import 解耦）· verify_all_scenes.py（全场景静态验证）· clone_scene.py（场景克隆+身份再标识）

★ 2026-11-11 收纳改造：`relocate_scene.py` **已删除** —— 锚点表 v2
（`<场景名>::<相对路径>` 经 discovery 按名解析）与 scene.json `hpc` 节
（`./` 相对路径）使位置信息随场景目录移动自动跟随，
**场景移动 = 文件管理器直接剪切粘贴，零脚本零配置**。
移动后跑 `pytest test/scenarios -q` 可显式发现任何断点（无静默失效）。

**上级导航**：[../../README.md](../../README.md)
