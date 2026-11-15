# scripts/ — 脚本工具目录（按功能分类）
> 最后核对：2026-11-15 · commit 97d5e5d


本目录包含 PhySimX FLASH 模块的辅助脚本，按功能分为 **环境诊断 / 超算 HPC / Git 发布 / 备份 / 测试 / 迁移管理 / 私有保留 / 文档门禁** 八类（编号目录 `01_`–`08_`），另有 `utils/`（独立小工具）、`git-hooks/`（Git 钩子）与两个根级脚本。
（注：`07_private_keep/` 为私有脚本，不随发布包运行链分发；每个一级子目录均有自己的 README，见下方「子目录 README 索引」。）

Windows 下带 `.bat` 包装的入口（`git_push.bat` / `git_pull.bat` / `manage.bat`）可双击执行；其余 `.py` 脚本用 `python scripts/<目录>/<脚本>.py` 调用。
凭据统一通过加密存储读取（见文末「凭据管理」），无需在脚本中硬编码敏感信息。

---

## 目录结构

```
scripts/
├── README.md                      # 本文档（总索引）
├── __init__.py                    # Python 包标识
├── clean_sandwich_txn_wsl.sh      # WSL 侧 sandwich TxN 产物清理（一次性）
├── sync_workbuddy_skills.py       # skills/ → .workbuddy/skills/ 单向镜像
│
├── 01_env_diagnose/               # 环境诊断与修复（README.md）
│   ├── check_env.py / diag_flash_env.py
│   ├── check_plot_style.py / fix_plot_style.py
│   ├── fix_bootstrap.py / gen_resource_config.py
│   └── test_dual_mode.py
│
├── 02_hpc/                        # 超算部署与结果回传（README.md）
│   ├── hpc_laserslab_test.py / hpc_run_laserslab.sh
│   ├── hpc_run_uploader.py / hpc_download_results.py
│   └── probes/                    # 一次性诊断探针（README.md）
│
├── 03_git_publish/                # ★ Git 推送 / 发版 / 手工 Git 速查（README.md）
│   ├── git_push.py / .bat / git_pull.py / .bat
│   ├── _git_auth.py / _git_credential_helper.py
│   ├── git_size_report.py / .bat / publish_pypi.py / update_readme_gitee.py
│   ├── install-git-hooks.sh / git-tag-with-test.sh / tag-release.sh
│   ├── private/git_push_private.py
│   └── reports/                   # xlsx 产物目录（已忽略，不入库）
│
├── 04_backup/                     # 发布前备份（README.md）: usb_backup.py
├── 05_test/                       # 全局测试（README.md）: run_global_tests.py
├── 06_migration/                  # 迁移 / 合规清理（README.md）: migrate_imports.py / manage.bat
├── 07_private_keep/               # 私有保留（README.md）: keep_private_only.py（破坏性，人工专用）
├── 08_docs/                       # 文档门禁（README.md）: check_docs.py / dump_docstrings.py
├── utils/                         # 独立小工具（README.md）: check_hdf5_time.py / convert_*.py
│
└── git-hooks/                     # Git 钩子（README.md, 勿移动）
    ├── pre-commit                 #   提交前: Black 格式检查 + 导入检查
    └── pre-push                   #   推送前: 框架 pytest 测试
```

---

## 子目录 README 索引

README 体系按「自底向上」维护：先定稿叶子目录 README，父级只引用子级结论；每条声明以当前代码为准。

| 子 README | 内容 | 典型场景 |
|---|---|---|
| [01_env_diagnose/README.md](01_env_diagnose/README.md) | 环境自检、绘图规范、资源配置 | 新机器初始化、字体/DPI 合规检查 |
| [02_hpc/README.md](02_hpc/README.md) | 超算部署、结果回传 | 提交作业、下载 HDF5 |
| [02_hpc/probes/README.md](02_hpc/probes/README.md) | 一次性诊断探针清单 | 超算环境排障 |
| [03_git_publish/README.md](03_git_publish/README.md) | ★ Git 常用指令速查、从 Gitee 删除文件（夹）、当前清理任务 | **手工 Git 操作** |
| [04_backup/README.md](04_backup/README.md) | 双模式备份 | 发布前备份 |
| [05_test/README.md](05_test/README.md) | 三套 pytest 分层 | 提交/发版前验证 |
| [06_migration/README.md](06_migration/README.md) | 导入迁移、版权清理、凭据入口 | 结构调整、合规清理 |
| [07_private_keep/README.md](07_private_keep/README.md) | 私有保全（含破坏性脚本边界） | 本机数据保全 |
| [08_docs/README.md](08_docs/README.md) | 文档门禁与 AST 摘要工具 | README 批量维护 |
| [utils/README.md](utils/README.md) | 独立小工具 | HDF5 时间戳核对、文档转换 |
| [git-hooks/README.md](git-hooks/README.md) | pre-commit / pre-push 行为 | 钩子不触发、推送被拦 |

改完 README 后运行 `python scripts/08_docs/check_docs.py` 做链接/锚点/模块引用门禁。

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
| 离线 | `deploy/build_wheelhouse.py`（**已提至根目录 deploy/**） | 联网机造离线包 | `python deploy/build_wheelhouse.py` |
| 离线 | `deploy/install_offline.py` | 离线机一键安装 | `python deploy/install_offline.py` |
| 管理 | `06_migration/manage.bat` | 凭据管理入口 | 双击 `manage.bat` |
| 文档 | `08_docs/check_docs.py` | README 链接/锚点门禁 | `python scripts/08_docs/check_docs.py` |
| Git | `03_git_publish/README.md` | 手工 Git 指令速查 / 从 Gitee 删除文件 | 见该 README 第 3、4 节 |
| 镜像 | `sync_workbuddy_skills.py` | 仓库 skills 同步到项目级 | `python scripts/sync_workbuddy_skills.py --check` |

---

## 详细说明

### 1. 统一 Git 推送 — `03_git_publish/git_push.py` (核心)

**双击即可一键推送**。自动完成：读取凭据 → 自动提交 → 推送到远程，全程无需手动输入。

```
python scripts/03_git_publish/git_push.py           # 默认: 自动提交 + 推 Gitee + 同步超算
python scripts/03_git_publish/git_push.py -m "fix: typo"   # 自定义提交信息
python scripts/03_git_publish/git_push.py -b main   # 推送到指定分支
python scripts/03_git_publish/git_push.py --no-hpc  # 只推 Gitee, 跳过超算同步
python scripts/03_git_publish/git_push.py -f        # 强制推送
python scripts/03_git_publish/git_push.py -n        # dry-run (只展示不执行)
python scripts/03_git_publish/git_push.py --tags 0.2.1  # 推送已打好的标签 (发版用)
python scripts/03_git_publish/git_push.py --allow-deletes # 允许提交删除 (默认拦截)
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
| `git commit --no-verify` | 跳过钩子 | **禁止使用**；钩子失败应先修代码或测试 |

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
> 由 `flash/output_pro/test/gen_test_data.py` **并行生成 → 测试 → 通过即自动删除**:
> - 测试全部通过 → 自动删除生成的 HDF5 文件;
> - 有测试失败 → 打印失败信息并**保留**数据文件供调试
>   (调试完成后 `python flash/output_pro/test/gen_test_data.py --cleanup` 手动清理)。

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

### 8. 手工 Git 操作 — 详见 `03_git_publish/README.md`

不调用一键脚本、直接在 Git Bash 操作时的完整指令集（状态同步、从 Gitee 删除文件/文件夹、撤销回滚、分支标签、体积排查、403 排障）集中在 [03_git_publish/README.md](03_git_publish/README.md) 第 3 节；第 4 节为 2026-11-15 的当前清理任务。

**最常用的一条**（只从 Gitee 移除，本地文件全部保留）：

```bash
git rm -r --cached -- path/to/dir/       # --cached 是关键: 工作区文件一个都不动
git add .gitignore                        # 同步忽略规则, 防止再次被 add -A 收入
git commit -m "chore: stop tracking path/to/dir"
git push origin master
```

⚠ 不要对 `git ls-files -ci --exclude-standard` 的全量结果批量执行删除：本仓实测 114 个命中，其中 84 个为有意保留的场景脚本与文档。必须按明确模式筛选后再操作。

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

### 凭据如何交给 git（HTTPS 认证机制）

**统一走 git credential helper，token 既不落盘、也不进命令行参数。**

调用链：`git_push.py` / `git_pull.py` / `git_size_report.py` / `private/git_push_private.py`
→ `_git_auth.py::auth_prefix()` 拼出 `-c credential.helper=!"<python>" "<helper.py>"`
→ git 调用 `_git_credential_helper.py`，它从加密库取凭据后经 **stdin/stdout 管道**回给 git。

三种做法的对比（前两种均已废弃）：

| 做法 | token 落 `.git/config` | token 进 `argv`（`ps` 可见） |
|------|:---:|:---:|
| 认证 URL 写进 remote（`https://user:token@…`） | ❌ 明文长期落盘 | — |
| 认证 URL / base64 头当命令行参数 | ✅ | ❌ |
| **credential helper（当前）** | ✅ | ✅ |

要点：
- `auth_prefix()` 先写一个空的 `credential.helper=` 来**清空** git 已有的 helper 列表，
  保证只有本项目这一个 helper 生效（系统 GCM 不会抢答、也不会弹窗）。
- helper 只服务 `gitee.com`（主机名不匹配时返回空），避免凭据被喂给其它远端。
- helper 用 `sys.executable` 启动，与调用脚本的解释器一致。
- ⚠ 凭据库依赖 `cryptography`；该包是**惰性导入**，因此各脚本在启动时显式探测，
  缺失时直接给出「换解释器 / 安装依赖」的可操作提示，而不是抛出深层 ImportError。

---

## 故障排除

| 问题 | 解决 |
|------|------|
| Gitee 推送 403 | Token 失效，运行 `python scripts/03_git_publish/git_push.py --setup` 重新设置 |
| `ModuleNotFoundError: cryptography` | 当前解释器缺依赖，改用含该依赖的解释器，或 `"<该解释器>" -m pip install cryptography` |
| Git 钩子不触发 | 运行 `bash scripts/03_git_publish/install-git-hooks.sh` 重新安装 |
| 双重模式导入失败 | 运行 `python scripts/01_env_diagnose/test_dual_mode.py` 诊断 |
| usb_backup 路径不存在 | 检查 U 盘盘符是否正确 |
| output_processors 测试失败 | 数据文件会自动**保留**供调试；调试完成后运行 `python flash/output_pro/test/gen_test_data.py --cleanup` 清理，重跑测试自动重新生成 |

---

## ⚠ 2026-10-22 模块化改造：08_offline_install 已提至根目录 `deploy/`

离线安装（造包/安装/护栏/自检）+ 超算离线部署链（`deploy/hpc_deploy/`）统一
收编到**根目录 `deploy/`**，与运行层 `flash/flash_run/`、场景层
`flash/scenarios/` 解耦；构建产物统一落根目录 `artifacts/`。
详见 `deploy/README.md` 与 `DEPENDENCIES.md`。

## ⚠ 2026-10-26：场景诊断探针迁至 `scripts/02_hpc/probes/`

原先放在 remote 层 test/scripts/ 子目录（已不存在）的一次性诊断探针（`_probe_*.py`
/ `diag_*.py` / `try_yt*.py` 等）迁至 **`scripts/02_hpc/probes/`**：

- 它们 `import flash.scenarios` ⇒ 属于**场景侧工具**，留在执行层会污染
  `flash_run`（护栏 `R-LAYER-03` 现会拦执行层里的场景名）；
- `scripts/` **不入 wheel**（wheel 只含 `flash` 包）⇒ 探针不再随包分发；
- 超算常用指令与部署测试记录同时迁至 `deploy/hpc_deploy/`。
