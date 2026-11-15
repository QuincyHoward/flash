# scripts/04_backup — 发布前备份

> 最后核对：2026-11-15 · commit 97d5e5d

**职责**：把仓库按「Gitee 视角」或「近全量」复制到 U 盘/本地目录，用于发布前备份与独立使用验证。

## 文件清单

| 文件 | 职责 |
|---|---|
| `usb_backup.py` | 双模式备份：`gitee`（按 .gitignore/.gitattributes 规则，文件表来自已跟踪文件 + 未跟踪且未忽略，文本统一 LF）/ `full`（仅排除脚本内置黑名单） |

## 常用命令

```bash
python scripts/04_backup/usb_backup.py                       # gitee 模式, 备份到同级目录
python scripts/04_backup/usb_backup.py --mode gitee E:\      # 仿 Gitee 备份到 U 盘
python scripts/04_backup/usb_backup.py --mode full E:\       # 近全量备份
python scripts/04_backup/usb_backup.py --dest D:\backups -n  # dry-run, 只打印计划
```

备份目录命名：`flash_backup_<mode>_<时间戳>`。

## 约定

- 先跑 `-n` 预览再实际复制；目标路径须已存在。
- 备份完成后按 `flash-backup-verify` skill 做独立环境验证，不以复制成功代替验证。

**上级导航**：[../README.md](../README.md)
