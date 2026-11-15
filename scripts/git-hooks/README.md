# scripts/git-hooks — Git 钩子

> 最后核对：2026-11-15 · commit 97d5e5d

**职责**：提交前代码风格/导入检查、推送前框架测试；由 git 自动触发，勿移动目录（钩子按本目录相对路径定位仓库根）。

## 文件清单

| 文件 | 触发 | 行为 |
|---|---|---|
| `pre-commit` | `git commit` | Black 检查（line-length=120）/ autopep8 兜底 + 包导入检查；导入失败仅告警 |
| `pre-push` | `git push` | 运行 flash 框架 pytest，失败即中止推送 |

## 安装与约定

```bash
bash scripts/03_git_publish/install-git-hooks.sh
```

- 解释器可用环境变量 `PYTHON` 指定；Windows Git Bash 下路径经 `cygpath` 转换。
- 钩子不可绕过：禁止 `--no-verify`，钩子失败应先修复代码或测试。
- 打标签前另行运行全局三套测试，见 [../05_test/README.md](../05_test/README.md)。

**上级导航**：[../README.md](../README.md)
