#!/usr/bin/env python3
"""Git credential helper —— 向 git 提供 Gitee 凭据（**运行时**读取加密库）。

为什么要它
----------
`git push` 走 HTTPS 需要用户名 + token。三种做法对比：

| 做法 | token 落 `.git/config` | token 进进程 argv |
|---|---|---|
| `https://<user>:<token>@host/...` | ❌ 明文落盘 | — |
| 把认证 URL 当 push 参数 | ✅ | ❌ `ps` 可见 |
| **本 helper（推荐）** | ✅ | ✅ |

git 通过 **credential helper 协议**调用本程序：stdin 收到
`protocol=https` / `host=gitee.com` 等 `key=value` 行（空行结束），
本程序向 stdout 回 `username=` / `password=` 两行。
凭据经**管道**传递，既不写配置文件、也不出现在命令行。

调用方式（由 git_push.py 在 `-c` 里注入，**不写入任何配置**）：
    git -c credential.helper= -c credential.helper='!"<python>" "<本文件>"' push origin master

安全边界
--------
* 本文件**不含任何凭据**，只负责从加密库读取；
* 只回显处理过的字段，不 echo 输入，避免把无关信息写回 git。
"""

from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── 定位仓库根（含 pyproject.toml），使 flash 包可导入 ──────────
_ROOT = Path(__file__).resolve().parent
for _ in range(8):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _read_request() -> dict:
    """读取 git 发来的 key=value 请求（空行结束）。"""
    req: dict = {}
    for raw in sys.stdin:
        line = raw.rstrip("\r\n")
        if not line:
            break
        if "=" in line:
            k, v = line.split("=", 1)
            req[k.strip()] = v.strip()
    return req


def main() -> int:
    req = _read_request()
    host = (req.get("host") or "").lower()

    # 只服务 Gitee（避免把凭据喂给其它远端）
    if host and "gitee.com" not in host:
        return 0

    try:
        from flash._core.credentials import get_credential_manager
        cred = get_credential_manager().get("gitee") or {}
    except Exception:
        return 0

    token = (cred.get("token") or "").strip()
    login = (cred.get("login") or cred.get("username") or "").strip()
    if not token:
        return 0

    out = []
    if login:
        out.append(f"username={login}")
    out.append(f"password={token}")
    sys.stdout.write("\n".join(out) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
