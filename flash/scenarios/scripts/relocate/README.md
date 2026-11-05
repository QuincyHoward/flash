# scenarios/scripts/relocate

> 最后核对：2026-11-05 · commit 7e04857

**一句话职责**：场景收纳整理工具链（六件套）

**内容导航**：audit_portable.py（可移植性审计, strict 须 ERROR=0）· make_scene_portable.py（manifests/parents/initfiles 幂等改造）· decouple_imports.py（跨场景 import 解耦）· relocate_scene.py（收纳执行器: git mv+锚点重写+残留扫描）· verify_all_scenes.py（全场景静态验证）· clone_scene.py（场景克隆+身份再标识）

**上级导航**：[../../README.md](../../README.md)
