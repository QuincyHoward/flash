# core/scene_reg — 发现注册族

> 最后核对：2026-11-05 · commit 7e04857

**一句话职责**：场景的全树发现、身份解析、声明式注册与可执行目录。

| 文件 | 行数 | 职责 | 关键入口 |
|---|---|---|---|
| `discovery.py` | 395 | 全树扫描 scene*.json；**位置优先身份派生**（scene.json→目录名，scene.<变体>.json→变体名）；三级路径解析（显式绝对/显式相对/自动派生） | `iter_scene_manifests`、`load_manifest`、`resolve_scene_meta` |
| `registry.py` | 86 | 声明式场景对象注册表（engine/main 型） | `get_scenario`（name 优先→别名回退） |
| `catalog.py` | 238 | 可执行场景目录（CLI list 的数据源；懒加载保零场景 import） | `CATALOG`、`get_scene` |
| `policies.py` | 54 | 场景族执行策略常量 | — |
| `device_defaults.py` | 86 | 场景核数默认值表（按名最长前缀匹配） | `get_scene_nprocs` |

**唯一性规则**：生效 name（位置派生）全树硬唯一；别名重复不阻塞发现，歧义延迟到按别名查找时报候选。详见 [../README.md](../README.md) 与根 README「位置优先」章。

**上级导航**：[../README.md](../README.md)（core）
