---
name: flash-git-publish
description: 仓库推送/拉取/发版/PyPI 发布一站式流程（scripts/03_git_publish 工具组）：git_push.py 一键推送（Gitee+超算、--tags 发版）、git_pull.py 安全拉取、publish_pypi.py 发布、凭据体系（credentials.enc）与 403 排障。需要同步 Gitee、拉取远端、打标签发版、发布 PyPI 时使用。触发词：推送、push、拉取、pull、同步 Gitee、发布 PyPI、打标签、tag、发版、403、token 未授权。
---

> 最后核对：2026-11-06 · commit 68905eb（0.2.1 发布实操验证：Gitee 分支+标签、PyPI 双 PASSED）

# 仓库推送 / 拉取 / 发版（flash-git-publish）

## 适用场景

- 推送本地提交到 Gitee（可同时同步超算部署仓库）
- 拉取远端最新 / 查看同步状态
- 打标签发版、发布 PyPI
- 排障：`403 The token is not authorized`、凭据弹窗、钩子拦截

## 前置条件

- **凭据体系**：所有 token 存于加密存储 `~/.physimx/flash/credentials.enc`
  （Fernet，经 `flash._core.credentials` 读取；`--setup` 交互配置）。
  ⚠️ Windows 凭据管理器里的 gitee.com 条目（系统 GCM）**不是**本仓推送凭据——
  403 时先查 credentials.enc 的 `gitee` 条目，别去改 GCM。
- 工具组：`scripts/03_git_publish/`（git_push/git_pull/publish_pypi/…，勿与
  旧仓 flash_m 的同名脚本混用，以本仓为准）

## 操作步骤

### 1. 推送（git_push.py）

```bash
python scripts/03_git_publish/git_push.py              # 自动提交 + 推 Gitee + 同步超算
python scripts/03_git_publish/git_push.py --no-hpc     # 只推 Gitee
python scripts/03_git_publish/git_push.py --tags 0.2.1 # 推送已打好的标签（发版）
python scripts/03_git_publish/git_push.py --status     # 只看状态
python scripts/03_git_publish/git_push.py -m "msg"     # 自定义提交信息
python scripts/03_git_publish/git_push.py --allow-deletes  # 允许提交删除（默认拦截）
python scripts/03_git_publish/git_push.py -n           # dry-run
```

流程：读凭据 → 自动检测变更并生成提交信息（触发 pre-commit：black+导入检查）
→ 推 Gitee（触发 pre-push：pytest）→ 默认同步超算部署仓库（`--no-hpc` 跳过）。
凭据经 **credential helper 管道**注入，origin 始终保持无凭据 URL，token 不落盘/不进命令行。

### 2. 拉取（git_pull.py）

```bash
python scripts/03_git_publish/git_pull.py          # ff-only 拉取当前分支（要求干净工作区）
python scripts/03_git_publish/git_pull.py --rebase # rebase 保持线性历史
python scripts/03_git_publish/git_pull.py --stash  # 未提交变更先 stash 再 pop
python scripts/03_git_publish/git_pull.py --status # 只看同步状态
```

### 3. 标签与发版

```bash
git tag -a 0.2.1 -m "版本说明"                      # 本地打注释标签
python scripts/03_git_publish/git_push.py --no-hpc --tags 0.2.1  # 推送标签
# 或走测试发版：scripts/03_git_publish/tag-release.sh / git-tag-with-test.sh（tag 前跑全局测试）
```

### 4. PyPI 发布（publish_pypi.py）

```bash
# 版本号先改 pyproject.toml + CHANGELOG，然后：
python scripts/03_git_publish/publish_pypi.py --build --check  # 构建 sdist/wheel + twine check
python scripts/03_git_publish/publish_pypi.py --test           # 试发 TestPyPI
python scripts/03_git_publish/publish_pypi.py                  # 正式发布 pypi.org
```

等价手工流（0.2.1 实操验证）：`.venv-win/Scripts/python.exe -m build` →
`-m twine check dist/*` → `-m twine upload dist/*`（凭据 `~/.pypirc`；
PyPI token 也可配进 credentials 体系 `flash._core.credentials.pypi`）。
产物同名版本不可重传——发版前确认 pyproject version 已递增。

## 护栏与铁律

1. **凭据绝不硬编码**：一切 token 走 credentials.enc 或 ~/.pypirc；origin URL 不含凭据
2. pre-commit/pre-push 钩子不可绕过（`--no-verify` 禁用）；钩子失败先修代码
3. 默认拦截删除类提交（`--allow-deletes` 才放行）——防误删场景资产
4. SNB 分享红线：`private/` 下 gitignored 内容不得入库；推送前敏感扫描
   （`git diff | grep -i "password\|token\|账号"` 无新增侧命中）
5. PyPI 不可撤回：正式发布前先 `--check`，必要时先 `--test` 发 TestPyPI

## 常见坑

- **403 token 未授权**：Windows GCM 的 gitee 条目过期/无权限时，git 直连会 403；
  走 git_push.py（credentials.enc 通道）即可，或 `--setup` 更新凭据
- 推送显示"已与远程同步"前务必 `git fetch origin` 核对 `origin/master` 哈希
- 根 README/其他文件有他人未提交改动时，自动提交会一并收入——发版前先确认
  `git status` 干净或自行分好暂存区
- 超算同步失败不影响 Gitee 已推成功；单独重试去掉 `--no-hpc` 再跑即可

## 关联资源

- `scripts/03_git_publish/`（git_push/git_pull/publish_pypi/_git_auth/_git_credential_helper、
  tag-release.sh、git-tag-with-test.sh）
- `docs/GIT_WORKFLOW.md`（Git 工作流与测试分层）、`deploy/README.md`（离线安装）
- `flash-backup-verify`（发布前备份与独立验证）
