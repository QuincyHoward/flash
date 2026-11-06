> 最后核对：2026-11-06 · commit 20337b6（flash-readme-sync 首轮补写）

# flash_src — FLASH 引擎侧辅助资源

## 职责

存放与 FLASH 引擎安装/文档相关的辅助资源（本目录内容不入 git 分发契约的
FLASH 源码/二进制，License §3）。

## 内容清单

| 文件/目录 | 说明 |
|---|---|
| `FLASH_one_click_install.sh` | FLASH 4.8 一键安装脚本（WSL Ubuntu-22.04 实测流程；hello_flash 安装包引用） |
| `docs/` | 引擎侧工具文档（`flash_tools/README.md` 等） |

## 关联资源

- `flash/scenarios/flash_demo/hello_flash/README.md`（零基础一键安装包，调用本目录安装脚本）
- `flash/flash_run/`（三模式运行体系）
