# scripts/06_migration — 迁移与合规清理

> 最后核对：2026-11-15 · commit 97d5e5d

**职责**：包结构调整期的导入路径迁移、FLASH 版权材料清理，以及凭据管理中心的 Windows 双击入口。

## 文件清单

| 文件 | 职责 |
|---|---|
| `migrate_imports.py` | 把硬编码 `sys.path` 引导替换为标准 bootstrap；自动 `.bak` 备份，跳过第三方与临时文件 |
| `remove_flash_copyrighted.sh` | 移除 FLASH 版权材料（License §3 合规）；**删除类操作，执行前先人工审阅脚本** |
| `manage.bat` | 凭据管理中心双击入口；等价命令 `python -m flash._core.credentials.manage` |

## 约定

- 迁移类脚本会改写源码，先在干净工作区运行并保留备份，以便逐文件 diff 复核。
- 凭据由用户手动管理；Agent 不读取、不修改凭据存储内容。
- 版权清理脚本属破坏性操作，仅限人工在确认清单后执行。

**上级导航**：[../README.md](../README.md)
