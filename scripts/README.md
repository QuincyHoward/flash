# scripts/ — 脚本工具目录（按功能分类）

本目录包含 PhySimX FLASH 模块的辅助脚本，按功能分为 **环境诊断 / 超算 HPC / Git 发布 / 备份 / 测试 / 迁移管理** 六类。

所有 `.py` 脚本均支持 **双击直接执行**（Windows 下双击 `.bat` 或 `.py` 即可），无需手动输入。
凭据统一通过 `flash/_core/credentials` 模块加密管理，无需在脚本中硬编码敏感信息。

---

## 目录结构

```
scripts/
├── README.md                     # 本文档
├── __init__.py                   # Python 包标识
│
├── 01_env_diagnose/              # 环境诊断与修复
│   ├── check_env.py              #   环境自检 (Python/依赖/FLASH 路径)
│   ├── diag_flash_env.py         #   FLASH 环境诊断 (用户名/安装路径探测)
│   ├── check_plot_style.py       #   绘图规范扫描 (PPT 演讲级)
│   ├── fix_plot_style.py         #   自动修复绘图样式违规
│   ├── fix_bootstrap.py          #   修复包引导/导入问题
│   ├── gen_resource_config.py    #   生成资源配置文件 (MPI 进程数等)
│   └── test_dual_mode.py         #   双重导入模式测试 (standalone / PhySimX)
│
├── 02_hpc/                       # 超算 HPC 部署
│   ├── hpc_laserslab_test.py     #   一键编译 + 运行 + 报告 (LaserSlab)
│   ├── hpc_run_laserslab.sh      #   超算运行脚本 (上传后执行)
│   ├── hpc_run_uploader.py       #   脚本上传 + 执行器 (SFTP)
│   └── hpc_download_results.py   #   SFTP 打包下载 HDF5 结果
│
├── 03_git_publish/               # Git 推送 / 发布 / 版本管理
│   ├── git_push.py               #   ★ 核心: 统一 Git 推送脚本 (双击可用)
│   ├── git_push.bat              #   Windows 批处理包装 (双击入口)
│   ├── install-git-hooks.sh      #   安装 Git 钩子 (pre-commit / pre-push)
│   ├── git-tag-with-test.sh      #   打标签前运行全局测试
│   ├── tag-release.sh            #   完整发布流程 (格式检查 + 测试 + 构建 + 标签)
│   ├── publish_pypi.py           #   PyPI 发布 (twine)
│   └── update_readme_gitee.py    #   更新 Gitee 仓库 README
│
├── 04_backup/                    # 备份
│   └── usb_backup.py             #   USB/本地备份 (gitee/full 双模式)
│
├── 05_test/                      # 测试
│   └── run_global_tests.py       #   全局三套 pytest (framework/input/output)
│
├── 06_migration/                 # 迁移 / 管理 / 清理
│   ├── migrate_imports.py        #   导入路径迁移工具
│   ├── remove_flash_copyrighted.sh #  移除 FLASH 版权材料 (合规)
│   └── manage.bat                #   凭据管理中心入口 (双击)
│
└── git-hooks/                    # Git 钩子脚本 (自动触发, 勿移动)
    ├── pre-commit                #   提交前: Black 格式检查 + 导入检查
    └── pre-push                  #   推送前: 框架 pytest 测试
```

---

## 快速参考

| 分类 | 脚本 | 功能 | 执行方式 |
|------|------|------|----------|
| 环境 | `01_env_diagnose/check_env.py` | 环境自检 | `python scripts/01_env_diagnose/check_env.py` |
| 环境 | `01_env_diagnose/diag_flash_env.py` | FLASH 环境诊断 | `python scripts/01_env_diagnose/diag_flash_env.py` |
| 环境 | `01_env_diagnose/check_plot_style.py` | 绘图规范扫描 | `python scripts/01_env_diagnose/check_plot_style.py` |
| 环境 | `01_env_diagnose/fix_plot_style.py` | 修复绘图样式 | `python scripts/01_env_diagnose/fix_plot_style.py` |
| 环境 | `01_env_diagnose/gen_resource_config.py` | 生成资源配置 | `python scripts/01_env_diagnose/gen_resource_config.py` |
| HPC | `02_hpc/hpc_laserslab_test.py` | 超算一键测试 | `python scripts/02_hpc/hpc_laserslab_test.py` |
| HPC | `02_hpc/hpc_download_results.py` | 下载超算结果 | `python scripts/02_hpc/hpc_download_results.py` |
| Git | `03_git_publish/git_push.py` | ★ 一键推送 | 双击 `git_push.bat` 或 `python scripts/03_git_publish/git_push.py` |
| Git | `03_git_publish/tag-release.sh` | 完整发布流程 | `bash scripts/03_git_publish/tag-release.sh v0.2.0` |
| 备份 | `04_backup/usb_backup.py` | USB/本地备份 | `python scripts/04_backup/usb_backup.py --mode gitee E:\` |
| 测试 | `05_test/run_global_tests.py` | 全局三套测试 | `python scripts/05_test/run_global_tests.py` |
| 管理 | `06_migration/manage.bat` | 凭据管理入口 | 双击 `manage.bat` |

---

## 详细说明

### 1. 统一 Git 推送 — `03_git_publish/git_push.py` (核心)

**双击即可一键推送**。自动完成：读取凭据 → 自动提交 → 推送到远程，全程无需手动输入。

```
python scripts/03_git_publish/git_push.py           # 默认: 自动提交 + 推送 (双击即此)
python scripts/03_git_publish/git_push.py -m "fix: typo"   # 自定义提交信息
python scripts/03_git_publish/git_push.py -b main   # 推送到 main 分支
python scripts/03_git_publish/git_push.py -f        # 强制推送
python scripts/03_git_publish/git_push.py -n        # dry-run (只展示不执行)
python scripts/03_git_publish/git_push.py --tag v1.0  # 打标签 + 推送 (先跑测试)
python scripts/03_git_publish/git_push.py --status  # 查看 git 状态 (不推送)
python scripts/03_git_publish/git_push.py --setup   # 进入凭据设置 (唯一需要交互的选项)
```

**凭据从 `flash/_core/credentials` 模块自动读取**（Fernet 加密存储），无需手动指定 Token。

**钩子机制** (通过 git 命令自动触发):
| 操作 | 触发钩子 | 测试内容 |
|------|----------|----------|
| `git commit` (脚本内部) | **pre-commit** | Black 格式检查 + 导入检查 |
| `git push` (脚本内部) | **pre-push** | 框架 pytest 测试 |
| `--tag` 模式 | **git-tag-with-test.sh** | 全局三套测试 |
| `git commit --no-verify` | 跳过钩子 | 不执行任何测试 |

### 2. 环境诊断与修复 — `01_env_diagnose/`

```bash
python scripts/01_env_diagnose/check_env.py          # Python/依赖/FLASH 路径自检
python scripts/01_env_diagnose/diag_flash_env.py     # 用户名/FLASH 安装路径/凭据诊断
python scripts/01_env_diagnose/check_plot_style.py   # 扫描全包绘图规范 (title>=24pt, DPI>=450)
python scripts/01_env_diagnose/fix_plot_style.py     # 自动修复绘图样式违规
python scripts/01_env_diagnose/gen_resource_config.py --total-cpus 64 --device hpc  # 生成资源配置
```

### 3. 超算 HPC 部署 — `02_hpc/`

```bash
python scripts/02_hpc/hpc_laserslab_test.py    # 一键编译 + 运行 + 报告 (需 SSH 凭据)
bash   scripts/02_hpc/hpc_run_laserslab.sh     # 超算运行脚本 (上传后执行)
python scripts/02_hpc/hpc_run_uploader.py      # 脚本上传 + 执行器
python scripts/02_hpc/hpc_download_results.py  # SFTP 打包下载 HDF5
```

用户名统一通过环境变量 `FLASH_SIM_USER_DIR` 控制（默认 `hello`，与 credentials 默认用户名一致），**勿硬编码用户名**。

### 4. 备份 — `04_backup/usb_backup.py` (双模式)

```
python scripts/04_backup/usb_backup.py                          # gitee 模式 (默认) 备份到同级目录
python scripts/04_backup/usb_backup.py --mode gitee E:\         # 仿 Gitee 备份到 U 盘
python scripts/04_backup/usb_backup.py --mode full E:\          # 几乎全量备份
python scripts/04_backup/usb_backup.py --dest D:\backups        # 指定目标目录
python scripts/04_backup/usb_backup.py -n                       # dry-run 试运行
```

备份目录命名: `flash_backup_<mode>_<时间戳>` (如 `flash_backup_gitee_20260801_110455`)。

### 5. 全局测试 — `05_test/run_global_tests.py`

```bash
python scripts/05_test/run_global_tests.py           # 全局三套测试 (framework/input_gen/output_processors)
python scripts/05_test/run_global_tests.py --framework
python scripts/05_test/run_global_tests.py --input
python scripts/05_test/run_global_tests.py --output
python scripts/05_test/run_global_tests.py --module test/test_gitee.py
```

> output_processors 套件的测试数据 (`inputfiles/`, .gitignore 排除, **不发布 hdf5 源文件**)
> 由 `flash/output_processors/test/gen_test_data.py` **并行生成 → 测试 → 通过即自动删除**:
> - 测试全部通过 → 自动删除生成的 HDF5 文件;
> - 有测试失败 → 打印失败信息并**保留**数据文件供调试
>   (调试完成后 `python flash/output_processors/test/gen_test_data.py --cleanup` 手动清理)。

### 6. Git 钩子与发布 — `03_git_publish/`

```bash
# 安装钩子 (首次克隆后一次)
bash scripts/03_git_publish/install-git-hooks.sh

# 打标签前跑全局测试 (三套测试)
bash scripts/03_git_publish/git-tag-with-test.sh v1.0

# 完整发布流程 (格式检查 + linting + 测试 + 构建 + 标签)
bash scripts/03_git_publish/tag-release.sh v0.2.0
```

### 7. 凭据管理 — `06_migration/manage.bat`

双击打开凭据管理中心（交互式菜单），用于首次设置 Gitee/SSH/API 凭据。
自动检测运行模式（standalone / PhySimX），双击即用。

```bash
# 等价于命令行:
python -m flash._core.credentials.manage
```

---

## 工作流示例

```bash
# 日常开发: 修改代码 → 双击 scripts/03_git_publish/git_push.bat
# 内部流程:
#   1. git add -A (自动)
#   2. git commit → pre-commit 钩子 (格式检查)
#   3. git push → pre-push 钩子 (框架测试)
```

```bash
# 发布版本
bash scripts/03_git_publish/tag-release.sh v0.3.0
# 流程: Black → Ruff → pytest (三套) → build → git tag
```

```bash
# 首次使用新机器
python scripts/03_git_publish/git_push.py --setup   # 设置 Gitee 凭据 (一次)
bash scripts/03_git_publish/install-git-hooks.sh    # 安装 Git 钩子 (一次)
python scripts/03_git_publish/git_push.py           # 完成首次推送
```

---

## 注意事项

1. **双击执行**: Windows 下双击 `.bat`（`git_push.bat` / `manage.bat`）即可运行，无需打开命令行。
2. **凭据初始化**: 首次使用前需运行 `python scripts/03_git_publish/git_push.py --setup` 设置 Gitee 凭据（仅一次）。
3. **钩子安装**: 首次克隆仓库后需运行 `bash scripts/03_git_publish/install-git-hooks.sh` 安装钩子（仅一次）。
4. **双重模式**: 所有脚本支持 standalone (`flash`) 和 PhySimX (`physimx_sim.flash`) 两种运行模式。
5. **行尾格式**: 所有源文件必须使用 **Unix (LF)** 换行符。`.gitattributes` 已强制归一化。
6. **编码**: Python 文件 UTF-8。**不要使用 GBK** — 所有 `read_text()` / `write_text()` 必须显式指定 `encoding="utf-8"`。
7. **可执行权限**: Linux/WSL 下运行 `.sh` 前需 `chmod +x`。
8. **git-hooks/ 目录勿移动**: pre-commit / pre-push 钩子内部按 `scripts/git-hooks/` 相对路径定位项目根。

---

## 凭据管理

所有凭据通过 `flash/_core/credentials` 模块统一加密管理：

```
存储位置: ~/.physimx/flash/credentials.enc
加密方式: Fernet (symmetric encryption)
管理入口: python scripts/03_git_publish/git_push.py --setup
          或双击 scripts/06_migration/manage.bat
```

支持的凭据类型: Gitee Token、FLASH SSH (超算账户 × 多条线路)、DeepSeek API Key。
默认用户名 `hello`（`DEFAULT_USER_NAME`，可用 `manage.py` 修改）。

---

## 故障排除

| 问题 | 解决 |
|------|------|
| Gitee 推送 403 | Token 失效，运行 `python scripts/03_git_publish/git_push.py --setup` 重新设置 |
| Git 钩子不触发 | 运行 `bash scripts/03_git_publish/install-git-hooks.sh` 重新安装 |
| 双重模式导入失败 | 运行 `python scripts/01_env_diagnose/test_dual_mode.py` 诊断 |
| usb_backup 路径不存在 | 检查 U 盘盘符是否正确 |
| output_processors 测试失败 | 数据文件会自动**保留**供调试；调试完成后运行 `python flash/output_processors/test/gen_test_data.py --cleanup` 清理，重跑测试自动重新生成 |
