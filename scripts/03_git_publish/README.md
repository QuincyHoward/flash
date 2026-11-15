# scripts/03_git_publish — Git 推送 / 发版 / 手工 Git 速查

> 最后核对：2026-11-15 · commit 6b565a0

**职责**：Gitee 推送与拉取、标签发版、PyPI 发布、远端文件体积统计；同时作为**手工 Git 操作**的指令速查入口（含「从 Gitee 删除文件/文件夹但保留本地」的完整流程）。

## 1. 文件清单

| 文件 | 职责 |
|---|---|
| `git_push.py` / `git_push.bat` | ★ 一键推送：自动提交 → 推 Gitee → 默认同步超算部署仓；带**删除护栏** |
| `git_pull.py` / `git_pull.bat` | 一键拉取（ff-only，可 `--rebase` / `--stash`） |
| `_git_auth.py` | 认证统一入口：拼装 credential helper 参数 |
| `_git_credential_helper.py` | credential helper 协议实现，只服务 gitee.com |
| `git_size_report.py` / `.bat` | 经 Gitee API 拉取分支文件树 → 按大小统计写 xlsx |
| `publish_pypi.py` | PyPI / TestPyPI 发布：`--build` / `--check` / `--test` / `--no-verify` |
| `update_readme_gitee.py` | 根 README 加 Gitee 地址与 English Overview |
| `install-git-hooks.sh` | 安装钩子到 `.git/hooks/` |
| `git-tag-with-test.sh` | 打标签前跑全局三套测试 |
| `tag-release.sh` | 完整发版：格式检查 + 测试 + 构建 + 标签 |
| `private/git_push_private.py` | 独立私有备份仓推送，不改公开 remote |
| `reports/` | `git_size_report.py` 的默认 xlsx 产物目录（**已被忽略，不入库**） |

## 2. 自动化工具用法

```bash
python scripts/03_git_publish/git_push.py                  # 自动提交 + 推 Gitee + 同步超算
python scripts/03_git_publish/git_push.py --no-hpc         # 只推 Gitee
python scripts/03_git_publish/git_push.py --allow-deletes  # 允许提交删除（默认拦截）
python scripts/03_git_publish/git_push.py -n               # dry-run
python scripts/03_git_publish/git_push.py --tags 0.2.1     # 推送已打好的标签
python scripts/03_git_publish/git_push.py --status         # 只看状态
python scripts/03_git_publish/git_pull.py --ff-only
python scripts/03_git_publish/publish_pypi.py --build --check
python scripts/03_git_publish/git_size_report.py -o ../flash_sim_runs/size.xlsx
```

凭据一律走 credential helper 管道（加密存储读取），origin 保持无凭据 URL，不落盘、不进命令行。Windows 凭据管理器里的 gitee 条目不是本仓推送凭据；403 时先查加密库条目或 `--setup`。

## 3. Git 常用指令速查（手工操作）

以下命令均在**仓库根目录的 Git Bash** 执行；`origin` = Gitee `physimx/flash`，当前分支 `master`。

### 3.1 状态与日常同步

| 目的 | 命令 |
|---|---|
| 查看改动 | `git status --short` |
| 查看已暂存 | `git diff --cached --stat` |
| 取远端信息（不改本地） | `git fetch origin` |
| 比较本地与远端 | `git log --oneline HEAD..origin/master` |
| 仅快进拉取 | `git pull --ff-only` |
| 提交 | `git add -A && git commit -m "msg"` |
| 推送 | `git push origin master` |
| 查看远端地址 | `git remote -v` |

### 3.2 ★ 从 Gitee 删除文件 / 文件夹

**先分清三种语义**——本项目「删除」指**仅解除远端跟踪，本地文件保留**：

| 需求 | 命令 | 本地文件 | Gitee 文件 |
|---|---|---|---|
| **仅从 Gitee 移除、本地保留（当前需求）** | `git rm --cached -- <file>` 或 `git rm -r --cached -- <dir>/` | **保留** | 删除 |
| Gitee + 本地都删 | `git rm -- <file>` / `git rm -r -- <dir>/` | 删除 | 删除 |
| 连 Git 历史一起抹除（体积瘦身） | `git filter-repo --path <path> --invert-paths` | 保留 | 历史重写 |

标准四步（以整个文件夹为例）：

```bash
# ① 在 .gitignore 中加入忽略规则，防止它再次被 add -A 收进索引
#    （本仓有严格章节顺序：请在第一章对应分节内添加，勿破坏第零章白名单与第三章冲突处理）
printf '\npath/to/dir/\n' >> .gitignore
# ② 只解除跟踪（--cached 是关键：工作区文件一个都不动）
git rm -r --cached -- path/to/dir/
# ③ 提交忽略规则 + 删除（此时 git status 中本地文件已被忽略，不再出现）
git add .gitignore
git commit -m "chore: stop tracking path/to/dir"
# ④ 推送：远端文件消失，本地文件原样保留
git push origin master
```

关键原理：`.gitignore` **只对未跟踪文件生效**；已经入库的文件即使匹配忽略规则，仍会继续同步到 Gitee，必须显式 `git rm --cached`。查询/验证用：

```bash
git ls-files -ci --exclude-standard          # 已跟踪且命中忽略规则的文件（全量）
git check-ignore -v --no-index <path>         # 查某文件命中了哪条规则（已跟踪文件必须加 --no-index）
git ls-tree -r --name-only origin/master -- <dir>/   # 直接查远端还剩哪些文件
```

> ⚠ 不要把 `git ls-files -ci --exclude-standard` 的结果**直接**批量删：它列的是全部被忽略的已跟踪文件，可能包含有意保留的例外。本仓实测 114 个，其中 84 个不在本次清理范围（多为场景脚本与文档）。务必按明确模式筛选后再操作。
> ⚠ `git filter-repo` 会改写历史并需 force push，所有协作者须重新克隆；仅在确需给仓库瘦身时使用，普通「不同步」需求不需要它。

### 3.3 撤销与回滚

| 目的 | 命令 |
|---|---|
| 撤销暂存 | `git restore --staged <path>` |
| 丢弃工作区改动 | `git restore <path>`（本地改动不可恢复） |
| 撤销最近提交、保留改动 | `git reset --soft HEAD~1` |
| 撤销最近提交、丢弃改动 | `git reset --hard HEAD~1`（危险） |
| 生成反向提交（推荐，不改写历史） | `git revert <sha>` |
| 暂存 / 恢复未完成改动 | `git stash push -m "wip"` / `git stash pop` |
| 未跟踪文件清理预演 | `git clean -nd`（去掉 `-n` 才真删） |

### 3.4 分支 / 标签 / 远端删除

| 目的 | 命令 |
|---|---|
| 分支 / 标签列表 | `git branch -a` / `git tag -l` |
| 新建并切换 | `git switch -c dev` |
| 首次推送分支 | `git push -u origin dev` |
| 打注释标签并推送 | `git tag -a 0.2.1 -m "release"` → `git push origin 0.2.1` |
| 删除远端分支 | `git push origin --delete dev` |
| 删除远端标签 | `git push origin --delete tag 0.2.1` |

### 3.5 体积排查与钩子排障

```bash
# 找出仓库中最大的 20 个对象（大文件瘦身依据）
git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | awk '$1=="blob"' | sort -k3 -nr | head -20
```

| 现象 | 处理 |
|---|---|
| 推送 403 | 走 `git_push.py` 的 helper 通道或 `--setup` 更新凭据；不要改 Windows 凭据管理器 |
| 钩子失败 | 先修代码 / 测试；**禁止** `--no-verify` |
| `git_push.py` 报「检测到 N 个已跟踪文件将被删除」 | 删除护栏生效；确属有意删除才加 `--allow-deletes` |
| 推送后远端似乎没变 | `git fetch origin` 后核对 `origin/master` 哈希 |

## 4. 清理任务（2026-11-15，已执行）

> **第二阶段：历史改写瘦身（2026-11-15 13:03，已执行）**
> 为清除历史对象里的 4 个 npz（54.06 MiB），按用户授权把 **0.2.1 之后的 28 个提交压缩为 1 个新提交**
> `6b565a0`（父 `68905eb` = 0.2.1），以显式 lease 强推 `origin/master`（`d3ac606..6b565a0`，forced update）。
> 保留 0.2.1 及更早 60 个提交；本地 3 个标签、远端 16 个标签与 `flat_flash` 分支 SHA **全部未变**。
> 新历史 61 提交 / 2362 文件；4 个 npz blob 已不可达，30 个清单文件未回带，84 个场景脚本与 14 个 cn4/feos 保留。
> 路线是 `git reset --soft 0.2.1` → `git add -A` → `git commit` → `git push --force-with-lease=refs/heads/master:<SHA>`：
> **必须保留索引**，若先清空索引再 `add -A`，84 个「已跟踪但被忽略」的场景脚本会全部丢失。
> 改写前完整备份在仓库外 `../flash_sim_runs/backup_rewrite_20261115/`（mirror / bundle / worktree 2362 文件 / 远端 refs 快照）。
>
> ⚠ **Gitee 页面体积不会自动下降**：需本人到项目配置页手动运行 **Git GC**；GC 前数字会先反增，GNK 对大仓库仅 3 次推送机会，
> PR / Release 引用会阻止 GC。远端另有 13 个指向本地已不存在对象的旧标签及 `flat_flash` 分支，
> 会让部分旧对象保持可达；若 GC 后体积仍偏高，需另行授权清理这些引用（本次未动）。
> 协作者须删除旧克隆后重新 `git clone`，不可直接 `git pull`。

> **执行状态（2026-11-15 11:13）**：已按下方命令执行完毕，提交 `d3ac606` 推送至 `origin/master`（`97d5e5d..d3ac606`）。
> 远端三类模式命中 **0**；30 个文件全部**仅解除跟踪、本地保留**；当前树由 2384 文件 / 111.63 MiB 降至 2354 文件 / 57.45 MiB（**-54.18 MiB，-48.5%**）。
> ⚠ 这 4 个 npz（合计约 54 MiB）仍留在 Git **历史对象**中，clone 体积未减小；如需真正瘦身见 3.2 节的 `git filter-repo`，须单独评估后执行。
> 下方命令块保留作「同类批量清理」模板：重复执行前先跑步骤 ① 预览命中数（当前应为 0）。
> 远端大文件分析产物位于仓库外的 `flash_sim_runs/gitee_large_files_20261115.{csv,md,xlsx}`（输出外置契约）。

**目标**：把下列三类文件从 Gitee 上移除（**本地保留**），使其今后不再同步。对应的忽略规则已在 `.gitignore` 中：8 位时间戳目录规则（第 118 行）、`**/reports/`（第 120 行）、`*.npz`（第 67 行）。

| 模式 | 含义 | 实测命中 |
|---|---|---|
| `**/*[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]/` | 带 8 位时间戳后缀的临时测试文件夹 | 26 |
| `**/reports/` | 测试报告文件夹 | 8 |
| `*.npz` | NumPy 压缩数据 | 4 |
| 合计（去重） | | **30** |

命中分布：20 个历史诊断脚本位于 `docs/_legacy_diags/cores_parallel_diag_20260912/`；
6 个私有 SNB 报告位于 `flash/scenarios/private/SNB/SNB/reports/`（移除同时符合 SNB 分享红线）；
`scripts/03_git_publish/reports/` 两份 xlsx；其余为时间戳目录文件与 4 个 npz 数据文件（含 Sandwich/TxN 分析目录中的 1 个）。本地文件均已确认存在。

```bash
# ===== 在仓库根目录（Git Bash）执行；全程不删除任何本地文件 =====
# ① 预览：列出将被解除跟踪的文件（只读，不改索引）
PATTERN='(^|/)[^/]*[0-9]{8}/|(^|/)reports/|\.npz$'
git ls-files | grep -E "$PATTERN" | tee /tmp/flash_gitee_cleanup.txt
wc -l /tmp/flash_gitee_cleanup.txt            # 预期 30

# ② 审阅清单后，仅解除跟踪（--cached 保留本地文件）
while IFS= read -r f; do git rm --cached --quiet --ignore-unmatch -- "$f"; done < /tmp/flash_gitee_cleanup.txt

# ③ 确认规则覆盖与暂存内容
git check-ignore -v --no-index scripts/03_git_publish/reports/gitee_file_stats_flash_master_20260828_001046.xlsx
git status --short

# ④ 提交 + 推送：远端删除、本地保留
git add .gitignore
git commit -m "chore: stop tracking timestamped temp dirs, reports and npz data"
git push origin master
```

**执行注意**：

1. **本次不要用 `git_push.py --allow-deletes` 代做**：脚本内部 `git add -A` 会把工作区其它未提交改动一并收入，且本机 E: 盘存在文件间歇不可见问题（脚本头部记录了 2026-09-12 误提交 10 文件 / 2835 行删除的事故）。手工 `git add .gitignore` 只暂存需要的内容，风险可控。
2. 步骤 ④ 会触发 `pre-commit`（Black/导入检查）与 `pre-push`（框架 pytest）；失败时修复后再提交，不要跳过钩子。
3. `git_size_report.py` 默认把 xlsx 写进 `reports/`，该目录现已忽略且从远端移除；今后请用 `-o` 输出到仓库外（如 `../flash_sim_runs/`），避免产物重新污染索引。
4. `docs/_legacy_diags/` 属历史归档豁免区：本次只解除跟踪、不改内容，本地 20 个诊断脚本仍可查；fresh clone 将不再包含它们。
5. 推送后用 `git ls-tree -r --name-only origin/master | grep -E "$PATTERN"` 复核远端已清空。

## 5. 关联资源

- 上级导航：[../README.md](../README.md)；钩子说明：[../git-hooks/README.md](../git-hooks/README.md)
- 工作流：[docs/GIT_WORKFLOW.md](../../docs/GIT_WORKFLOW.md)；文档门禁：[../08_docs/check_docs.py](../08_docs/check_docs.py)
- 技能：`flash-git-publish`（推送/发版/403 排障）、`flash-backup-verify`（发布前备份）
