# scripts/07_private_keep — 私有保留脚本

> 最后核对：2026-11-15 · commit 97d5e5d

**职责**：仅服务于本机私有数据保全与场景迁移核验，不参与发布包运行链。

## 文件清单

| 文件 | 职责 |
|---|---|
| `keep_private_only.py` | 反 gitignore 工具：只保留被忽略的私有文件，删除全部已跟踪公开文件并移除 `.git`；支持 `--dry-run` / `--preview` |
| `scene_verify_all_20261030.py` | 2026-10-30 改名迁移后的 35 场景一次性核验：WSL 场景用极短 `tmax`，hpc-only 场景只生成输入档、不部署不提交 |

## ⚠ 执行边界

1. `keep_private_only.py` 是**破坏性脚本**（删除工作区文件与 `.git`）。只允许人工在完整备份后、先用 `--dry-run` 审阅清单再执行；Agent 不代为运行，也不提供绕过方式。
2. 场景核验脚本为一次性历史记录，不是稳定 API；SNB 场景族仍只走超算，本地仅做输入生成与静态核验。
3. 私有目录内容不得进入公开仓，推送前按 `flash-git-publish` skill 做敏感扫描。

**上级导航**：[../README.md](../README.md)
