---
name: flash-credential-audit
description: 全库硬编码与凭证审查：扫描所有脚本/文档/配置中的硬编码凭据（token/password/真实账号/内网地址/URL 内嵌凭据），白名单仅允许默认用户名 hello、默认密码 123 作演示与占位符。发布前、新脚本/文档入库前、定期巡检时使用。触发词：硬编码、凭证审查、敏感信息、secret、token 泄露、账号扫描、发布前检查。
---

> 最后核对：2026-11-07 · commit 1586052

# 硬编码与凭证审查（flash-credential-audit）

## 适用场景

- 发布（Gitee 推送 / PyPI 上传）前的强制检查
- 新增/修改脚本、文档、场景配置后
- 定期全库巡检（建议随 flash-skill-sync 一并执行）

## 白名单（唯一允许的明文）

| 项 | 值 | 用途 |
|---|---|---|
| 默认用户名 | `hello` | 示例/演示/回退默认值 |
| 默认密码 | `123` | 示例/演示（仅文档示例，不得用于真实服务） |
| 占位符 | `<ACCOUNT>` `<TOKEN>` `<HPC_WORKDIR>` `<USER>` 等 | 文档与 SKILL.md |
| 凭据体系实现 | `flash/_core/credentials/` | 字段名列表（`_SECRET_FIELDS`）、加解密逻辑本身不是凭据 |
| 测试假数据 | pytest fixture 中自造的 `fake_token` 等 | 明显非真实的测试桩 |

## 禁止出现的真实凭据（无论文件类型）

1. **真实超算/平台账号名**：`scfa2696`、`sch0348` 等（含代码标识符派生，如
   `ROUTES_SCFA2696`——账号名进了常量名同样算泄露）
2. **token/password/secret/api_key/access_key/private_key 的字面量赋值**
   （`X = "非123非占位符"` 或 YAML/JSON 明文值）
3. **URL 内嵌凭据**：`https://user:pass@host`
4. **API 调用携带 token**：`?access_token=xxx`、`Authorization: Bearer xxx` 的真实值
5. **内网地址 + 账号组合**：真实 IP/域名与用户名成对出现
6. **~/.pypirc / netrc 内容复制入库**

## 操作步骤

### 1. 确定审查面

以 **git 追踪文件**为审查面（真正会推到 Gitee 的内容）：

```bash
git ls-files | grep -vE "PlasmaPy/|_legacy_diags/" > /tmp/audit_list.txt
```

豁免：`PlasmaPy/**`（vendored 上游）、`docs/_legacy_diags/**`（历史归档）、
`temp*/`（不入库）、`flash/_core/credentials/`（凭据体系实现，白名单第 4 条）。

### 2. 分层正则扫描（python 脚本内联执行）

```
L1 账号名:  scfa2696|sch0348 及新增真实账号（维护在下方"已知真实账号"清单）
L2 密钥赋值: (?i)(token|password|passwd|secret|api_key|access_key|private_key)\s*[=:]\s*["'][^"']+["']
L3 URL 凭据: https?://[^\s/"']+:[^\s/"']+@
L4 token 传输: access_token=[A-Za-z0-9]{8,} | Bearer [A-Za-z0-9._\-]{16,}
L5 内网地址: \b(?:10\.\d+\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+|192\.168\.\d+\.\d+)\b   # 四段 IP（排除文档小节号 10.2.1 与依赖版本表 10.3.0）
L6 pypirc/netrc 泄露: -\wpypirc|\[pypi\].*password
```

白名单过滤：命中行含 `hello`/`"123"`/`<`占位符`>`/`_SECRET_FIELDS`/注释说明
"示例"/"占位" → 降级为人工复核项而非违规。

### 3. 处置

- **文档/SKILL.md**：真实账号/值 → 占位符（`<ACCOUNT>` 等）或改述（"凭据同走 helper"）
- **代码标识符**（常量/变量名含真实账号）：重命名为中性名
  （如 `ROUTES_HPC_PRIMARY`），旧名保留一个发布周期的兼容别名
- **代码逻辑中的真实值**：改走 `flash._core.credentials` 动态读取
- **无法自动处置**（如需改协议/接口）：列入报告交用户决策
- **已入 git 历史的泄露**：只报告；历史重写（filter-repo/force push）必须用户确认

### 4. 收尾

修复后重跑本 skill 扫描直至 0 违规 → `check_docs` 门禁 → 涉码改动跑对应单测
→ git 提交（审查报告写入 `.workbuddy/memory/` 当日日志）。

## 护栏与铁律

1. 白名单外**零容忍**；宁可误报人工复核，不可漏报
2. 修复不得破坏凭据体系功能——改完必须跑凭据相关测试
3. `hello`/`123` 仅限示例语境；出现在**可执行的真实连接逻辑**中同样算违规
4. 审查脚本本身入库（`scripts/08_docs/` 或随本 skill 文档化），保证可重复执行

## 常见坑

- 字段**名**（`"password":` 作为 JSON key 或 `_SECRET_FIELDS` 成员）不是泄露——
  泄露的是**值**；正则必须区分键与值
- 文档里"凭据同走 helper/helper 管道传递"是安全描述，保留
- `hdf5/1.8.18` 这类版本号会被 `1.8.3.1` 式 IP 误报——L5 需排除 `module load` 行
  与依赖版本表（如 `pillow 10.3.0`）；负面对比例文档（"❌ 明文落盘"）与运行期
  f-string 组合 URL（`{login}:{token}`）属白名单语境
- `git ls-files` 中文文件名默认转义——加 `-c core.quotepath=false`（否则 OSError）
- Windows Git Bash heredoc 会把 `\\` 转成 `/`——含反斜杠的替换模式用 `chr(92)` 构造
- **账号名进了代码标识符**（如 `ROUTES_<账号>` 常量名）同样算泄露：重命名为中性名
  （`ROUTES_NC_E`/`ROUTES_BSCC_T6`），历史账号名归一化统一走
  `flash/_core/credentials/hpc_config.py` 的 `_LEGACY_ROUTE_KEY`（该白名单文件是
  全仓唯一允许出现真实账号名的位置，R-ID-01 守卫动态引用它）
- 文档中的盘符绝对路径（`E:\PhySimX\...`、`C:\Users\<user>\...`）会被 R-ID-01
  拦截——一律写成 `<PhySimX 根>/...` 或 `~/.workbuddy/...` 相对形式
- git 历史里已删除的文件（如 credentials_legacy.py）内容仍在历史中——
  该文件含默认示例数据（hello/123），确认为假数据则无需重写历史

## 关联资源

- `flash._core.credentials`（凭据唯一来源；`--setup` 交互配置）
- `scripts/08_docs/check_docs.py`（文档门禁，含敏感信息 WARN 项）
- `skills/flash-git-publish`（推送前检查的执行时机）、`skills/flash-skill-sync`（定期巡检触发）
