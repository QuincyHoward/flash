# 18 · Gitee 推送

> **本地 git 仓库已完成**（`E:\PhySimX\PhySimX\simulation\Multi\MultixD`，
> `151 files / 27142 insertions`，分支 `main`，提交 `b3f1df6`）。
> **远端推送被凭据作用域挡住** —— 本文记录实测证据与三条可行路径。

---

## 1. 目标配置

| 项 | 值 |
|---|---|
| 仓库根 | `E:\PhySimX\PhySimX\simulation\Multi\MultixD` |
| 分支 | `main` |
| 目标 | `<owner>/MultixD`（**private**） |
| 推送脚本 | `eosop_pro/scripts/07_gitee_publish.py`（+ `git_publish.bat`） |
| 凭据 | **只读** `~/.physimx/flash/credentials.enc`（Fernet）或环境变量 |

---

## 2. 实测证据：token 是「仓库级」，不能建仓

```
$ python scripts/07_gitee_publish.py --check

[1/4] 读取凭据（只读）...
  ✓ 凭据来源 : file:C:\Users\Administrator\.physimx\flash\credentials.enc
  ✓ token    : 34997126…（已打码）
  ✓ login    : quincyhoward

[2/2] 探测作用域 ...
  ✓ token 有效，登录名 = quincyhoward
  可见仓库 1 个：['physimx/flash']
  目标仓库 quincyhoward/MultixD 存在？ False
```

| 探测 | 结果 | 含义 |
|---|---|---|
| `GET /user` | 200，`login=quincyhoward` | token **有效** |
| `GET /user/repos` | 200，**只列出 `physimx/flash`** | ★ token 是**仓库级**（只看得见一个仓） |
| `POST /user/repos` | **403** `仓库级私人令牌无权执行此操作` | 无 `projects` 作用域 → **不能建仓** |
| `GET /enterprises/physimx` | **401** `no 'enterprises' scope` | 无 `enterprises` 作用域 → 不能管企业 |
| `GET /orgs/physimx` | **404** `{"message":"Group"}` | `physimx` 是 enterprise，不是 organization |

★ 另外查过：`~/.physimx/credentials.enc`（顶层）里**只有** `__meta__`，无 gitee 条目；
`~/.git-credentials` 不存在；环境变量里没有 token。
**因此当前机器上没有可用于建仓的凭据。**

---

## 3. 三条可行路径（任选其一）

### A) 【推荐】网页手动建空仓 → 脚本只推送

```
1. 打开 https://gitee.com/projects/new
     - 仓库名 : MultixD
     - 归属   : quincyhoward        （或 physimx，见路径 C）
     - 勾选   : 私有
     - ★ 不要 初始化 README / .gitignore / License（保持空仓，
                否则远端会有本地没有的提交，首次 push 需要 --force）
2. 执行（仓库级 token 对**已存在**的仓库有写权，所以这一步能过）：
     cd MultixD\eosop_pro
     scripts\git_publish.bat --no-create
```

### B) 换一个作用域含 `projects` 的个人访问令牌

```
1. https://gitee.com/profile/personal_access_tokens  → 新建令牌
     勾选 projects（建仓所必需）
2. set GITEE_TOKEN=<新令牌>
   set GITEE_LOGIN=quincyhoward
   cd MultixD\eosop_pro
   scripts\git_publish.bat            :: 脚本自动建仓 + 推送
```

环境变量优先级**高于**文件凭据（`load_gitee_credentials` 先看 `GITEE_TOKEN`），
所以不必改动 `~/.physimx/flash/credentials.enc`。

### C) 建到 **physimx 企业命名空间**（与 `physimx/flash`、`physimx/flychk` 同级）

需要作用域含 `enterprises` 的令牌：

```
set GITEE_TOKEN=<企业令牌>
cd MultixD\eosop_pro
scripts\git_publish.bat --enterprise physimx --owner physimx
```

★ 企业接口的三个坑（已写进脚本，见 `gitee-enterprise-repo` 技能）：

| 坑 | 说明 |
|---|---|
| 端点是 `/enterprises/{name}/repos` | `POST /orgs/physimx/repos` 会**静默失败**返回 `{"message":"Group"}` |
| 私有参数是 `visibility: "private"` | 传 `private: true` 会报 `private is invalid` |
| 需要 `enterprises` 作用域 | 否则 `GET /enterprises/physimx` 报 401 |

---

## 4. 脚本的安全设计（已由测试守住）

| 纪律 | 实现 | 测试 |
|---|---|---|
| **凭据只读** | 源码里不含 `cm.set(` / `cm.delete(` / `_save(` / `Fernet.generate_key(` | `test_source_contains_no_credential_write_calls` |
| **读后不变** | 读一遍凭据后密文与密钥**逐字节不变** | `test_credentials_unchanged_after_read` |
| **token 不进日志** | 所有输出过 `mask()` / `_redact()` | `test_mask_hides_token`、`test_redact_hides_token_across_multiline` |
| **token 不进磁盘** | 推送用命令行 URL，随后把 remote **复位为干净 URL**，并断言 `.git/config` 不含 token | `test_set_clean_remote_and_assert` |
| **用 `login` 而非显示名** | 无交互 git 认证必须用 `login`（显示名会 403） | `test_login_field_is_used_not_display_name` |
| **403 翻译成可读诊断** | `CredentialScopeError` + 三条路径 | `test_403_is_translated_to_scope_error_not_raw_http` |
| **企业接口参数正确** | `visibility` 而非 `private` | `test_enterprise_payload_uses_visibility_not_private` |

★ 「凭据只读」是**用户的硬边界**（见 `~/.workbuddy/MEMORY.md`）：
脚本永远不会替你新建、修改或删除任何令牌 —— 所以路径 A/B/C 都必须由用户操作一次。

---

## 5. 已提交的内容清单

| 类别 | 数量 |
|---|---|
| `.py` | 104 |
| `.md`（docs/ 17 篇 + README + 报告） | 31 |
| `.bat` 启动器 | 11 |
| 其它（`.gitignore` / `.gitattributes` / `requirements.txt` / `manifest.json` / `.gitkeep`） | 5 |
| **合计** | **151** |

`.gitignore` 排除（不提交）：

| 排除项 | 体积 / 原因 |
|---|---|
| `MultixD/src/Multi1D++Portable20241128/` | **1.5 GB** —— 上游源码+数据+压缩包，且授权不含再分发 |
| `outputs/{h5,plots,logs}` | 可重现（335 MiB h5 + 67 PNG） |
| `outputs/reports/*.{csv,json}` | 可重现（体积大，`.md` 保留作人读证据） |
| `docs/extracted/*.txt` | 抽取的说明书正文（3 MB），只留 `MANIFEST.md` + `manifest.json` |
| 凭据类 | `credentials.enc` / `.secret_key` / `hpc_accounts.json` / `.env` |

`.gitattributes`：`* text=auto eol=lf` + **`*.bat text eol=crlf`** + 二进制标记。

---

## 6. 推送后如何验证

```bash
git -C E:/PhySimX/PhySimX/simulation/Multi/MultixD log --oneline -1
git -C E:/PhySimX/PhySimX/simulation/Multi/MultixD remote -v      # 应为**干净** URL（无 token）
git -C E:/PhySimX/PhySimX/simulation/Multi/MultixD status -sb
```

`remote -v` 必须**不含** `user:token@` —— 这是脚本在 `finally` 里复位并断言的。
