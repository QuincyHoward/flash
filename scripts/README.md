# scripts/ — 脚本工具目录

本目录包含 PhySimX FLASH 模块的辅助脚本，主要用于 **Git 推送**、**备份**、**测试** 和 **发布** 流程。

所有 `.py` 脚本均支持 **双击直接执行**（Windows 下双击 `.bat` 或 `.py` 即可），无需手动输入。
凭据统一通过 `_core/credentials` 模块加密管理，无需在脚本中硬编码敏感信息。

---

## 目录结构

```
scripts/
├── README.md                     # 本文档
├── __init__.py                   # Python 包标识
│
├── git_push.py                   # ★ 核心: 统一 Git 推送脚本 (双击可用)
├── git_push.bat                  # Windows 批处理包装 (双击入口)
├── manage.bat                    # 凭据管理中心入口 (双击)
│
├── usb_backup.py                 # USB/本地备份脚本
├── test_dual_mode.py             # 双重导入模式测试 (standalone / PhySimX)
│
├── install-git-hooks.sh          # 安装 Git 钩子 (pre-commit / pre-push)
├── git-tag-with-test.sh          # 打标签前运行全局测试
├── tag-release.sh                # 完整发布流程 (格式检查 + 测试 + 构建 + 标签)
│
└── git-hooks/                    # Git 钩子脚本 (自动触发)
    ├── pre-commit                #   提交前: Black 格式检查 + 导入检查
    └── pre-push                  #   推送前: 框架 pytest 测试
```

---

## 快速参考

| 脚本 | 功能 | 执行方式 |
|------|------|----------|
| `git_push.py` | 自动提交变更 + 推送到远程 | 双击 `git_push.bat` 或 `python git_push.py` |
| `git_push.py --status` | 查看 git 状态 (不推送) | `python git_push.py --status` |
| `git_push.py --setup` | 设置/更新 Gitee 凭据 (唯一有交互) | `python git_push.py --setup` |
| `usb_backup.py` | 备份项目到 U 盘/本地 (gitee/full 双模式) | `python usb_backup.py --mode gitee E:\` |
| `test_dual_mode.py` | 测试 standalone / PhySimX 导入 | `python -m flash.scripts.test_dual_mode` |
| `git-tag-with-test.sh` | 打标签前跑全局测试 | `bash git-tag-with-test.sh v1.0` |
| `install-git-hooks.sh` | 安装 Git 钩子 | `bash install-git-hooks.sh` |

---

## 详细说明

### 1. 统一 Git 推送 — `git_push.py` (核心)

**双击即可一键推送**。自动完成：读取凭据 → 自动提交 → 推送到远程，全程无需手动输入。

```
python git_push.py                     # 默认: 自动提交 + 推送 (双击即此)
python git_push.py -m "fix: typo"     # 自定义提交信息
python git_push.py -b main            # 推送到 main 分支
python git_push.py -f                 # 强制推送
python git_push.py -n                 # dry-run (只展示不执行)
python git_push.py --tag v1.0         # 打标签 + 推送 (先跑测试)
python git_push.py --status           # 查看 git 状态 (不推送)
python git_push.py --setup            # 进入凭据设置 (唯一需要交互的选项)
```

**凭据从 `_core/credentials` 模块自动读取**（Fernet 加密存储），无需手动指定 Token。

**钩子机制** (通过 git 命令自动触发):
| 操作 | 触发钩子 | 测试内容 |
|------|----------|----------|
| `git commit` (脚本内部) | **pre-commit** | Black 格式检查 + 导入检查 |
| `git push` (脚本内部) | **pre-push** | 框架 pytest 测试 |
| `--tag` 模式 | **git-tag-with-test.sh** | 全局三套测试 |
| `git commit --no-verify` | 跳过钩子 | 不执行任何测试 |

### 2. Windows 入口 — `git_push.bat`

双击 `git_push.bat` 即等同于 `python git_push.py`，自动打开命令行窗口并等待结果。

### 3. 凭据管理 — `manage.bat`

双击打开凭据管理中心（交互式菜单），用于首次设置 Gitee/SSH/API 凭据。
自动检测运行模式（standalone / PhySimX），双击即用。

```bash
# 等价于命令行:
python -m flash._core.credentials.manage
```

### 4. 备份脚本 — `usb_backup.py` (双模式, 2026-08-01 重写)

支持两种备份模式:

```
# gitee 模式 (默认): 仿 Gitee 仓库备份
#   文件列表 = git ls-files (索引 + 未忽略未跟踪), 不含 .git, 不跑测试,
#   文本文件按 .gitattributes 规范化为 LF 行尾
python usb_backup.py                          # 备份到同级目录
python usb_backup.py --mode gitee E:\         # 仿 Gitee 备份到 U 盘

# full 模式: 几乎全量备份 (仅脚本内 EXCLUDE_DIRS/EXCLUDE_FILES 排除)
python usb_backup.py --mode full E:\

# 其他选项
python usb_backup.py --dest D:\backups        # 指定目标目录
python usb_backup.py --name flash_release     # 自定义备份目录名前缀
python usb_backup.py -n                       # dry-run 试运行 (不复制)
```

备份目录命名: `flash_backup_<mode>_<时间戳>` (如 `flash_backup_gitee_20260801_110455`)。

### 5. 测试脚本 — `test_dual_mode.py`

测试 standalone（`flash.*`）和 PhySimX（`physimx_sim.flash.*`）两种导入模式是否正常。

```bash
# PhySimX 模式
python -m physimx_sim.flash.scripts.test_dual_mode

# 独立模式
python -m flash.scripts.test_dual_mode
```

### 6. Git 钩子 — `install-git-hooks.sh`

安装 pre-commit（格式检查）和 pre-push（框架测试）钩子。

```bash
bash scripts/install-git-hooks.sh

# 临时跳过钩子
git commit --no-verify
git push --no-verify
```

### 7. 标签发布 — `git-tag-with-test.sh` / `tag-release.sh`

```bash
# 打标签前跑全局测试 (三套测试)
bash scripts/git-tag-with-test.sh v1.0

# 完整发布流程 (格式检查 + linting + 测试 + 构建 + 标签)
bash scripts/tag-release.sh v0.2.0
```

---

## 工作流示例

```bash
# 日常开发: 修改代码 → 双击 git_push.bat
# 内部流程:
#   1. git add -A (自动)
#   2. git commit → pre-commit 钩子 (格式检查)
#   3. git push → pre-push 钩子 (框架测试)
```

```bash
# 发布版本
bash scripts/tag-release.sh v0.3.0
# 流程: Black → Ruff → pytest → build → git tag (三重测试)
```

```bash
# 首次使用新机器
python git_push.py --setup        # 设置 Gitee 凭据 (一次)
bash scripts/install-git-hooks.sh # 安装 Git 钩子 (一次)
python git_push.py                # 完成首次推送
```

---

## 注意事项

1. **双击执行**: Windows 下双击 `.bat` 即可运行，无需打开命令行。
2. **凭据初始化**: 首次使用前需运行 `python git_push.py --setup` 设置 Gitee 凭据（仅一次）。
3. **钩子安装**: 首次克隆仓库后需运行 `bash scripts/install-git-hooks.sh` 安装钩子（仅一次）。
4. **双重模式**: 所有脚本支持 standalone (`flash`) 和 PhySimX (`physimx_sim.flash`) 两种运行模式。
5. **行尾格式**: 所有源文件必须使用 **Unix (LF)** 换行符。`.gitattributes` 已强制归一化，提交时 git 自动将 CRLF 转为 LF。
6. **编码**: Python 文件 UTF-8。**不要使用 GBK** — 所有 `read_text()` / `write_text()` 必须显式指定 `encoding="utf-8"`。
7. **可执行权限**: Linux/WSL 下运行 `.sh` 前需 `chmod +x`。

---

## 凭据管理

所有凭据通过 `_core/credentials` 模块统一加密管理：

```
存储位置: ~/.physimx/physimx_sim/flash/credentials.enc
加密方式: Fernet (symmetric encryption)
管理入口: python git_push.py --setup
          或双击 manage.bat
```

支持的凭据类型: Gitee Token、FLASH SSH (两个超算账户 × 9条线路)、DeepSeek API Key。

---

## 故障排除

| 问题 | 解决 |
|------|------|
| Gitee 推送 403 | Token 失效，运行 `python git_push.py --setup` 重新设置 |
| Git 钩子不触发 | 运行 `bash scripts/install-git-hooks.sh` 重新安装 |
| 双重模式导入失败 | 运行 `python -m flash.scripts.test_dual_mode` 诊断 |
| usb_backup 路径不存在 | 检查 U 盘盘符是否正确 |
