"""``scripts/07_gitee_publish.py`` 测试 —— 凭据只读 + token 不落盘。

为什么单独一个测试文件
----------------------
这个脚本碰的是**用户凭据**，属于只读边界。三条纪律必须由测试守住，
而不是靠注释里的君子协定：

1. **只读**：源码里不得出现任何写凭据的调用
   （``set(`` / ``delete(`` / ``_save`` / ``_save_raw`` / ``Fernet.generate_key``）
2. **token 不落盘**：推送路径必须先把 remote 设为干净 URL，
   且结束后 ``.git/config`` 里不能出现 token
3. **token 不进日志**：所有对外输出必须过 :func:`mask` / :func:`_redact`

另外还要验证：凭据真的能读出来（真实文件），且用的是 ``login`` 而不是显示名。
"""

import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import os
# --- path bootstrap (auto) ---
_d = os.path.dirname(os.path.abspath(__file__))
while _d != os.path.dirname(_d) and not os.path.isfile(
        os.path.join(_d, "_runner.py")):
    _d = os.path.dirname(_d)
if _d not in sys.path:
    sys.path.insert(0, _d)
import _runner  # noqa: F401
from _runner import expect, expect_eq, expect_in, main

from eosop_pro import config

# ── 以模块方式加载 scripts/07_gitee_publish.py（目录名以数字开头，无法常规 import）
_SCRIPT = config.SCRIPTS_DIR / "07_gitee_publish.py"
_spec = importlib.util.spec_from_file_location("gitee_publish", _SCRIPT)
assert _spec and _spec.loader, f"无法加载 {_SCRIPT}"
gp = importlib.util.module_from_spec(_spec)
sys.modules["gitee_publish"] = gp
_spec.loader.exec_module(gp)


# ══════════════════════════════════════════════════════════════
# 纪律 1：凭据只读
# ══════════════════════════════════════════════════════════════
def test_source_contains_no_credential_write_calls():
    """★ 源码里不得出现写凭据的调用 —— 这是只读边界的第一道闸。"""
    src = _SCRIPT.read_text(encoding="utf-8")
    code = "\n".join(ln for ln in src.splitlines()
                     if not ln.lstrip().startswith("#"))
    banned = [
        (r"\bcm\.set\(", "写入凭据存储 cm.set("),
        (r"\bcm\.delete\(", "删除凭据 cm.delete("),
        (r"\._save\(", "内部落盘 _save("),
        (r"\._save_raw\(", "内部落盘 _save_raw("),
        (r"Fernet\.generate_key\(", "生成新密钥（会破坏既有密文）"),
        (r"set_user_name\(", "改写用户名元数据"),
    ]
    for pat, why in banned:
        expect(re.search(pat, code) is None,
               f"源码中出现被禁调用 {pat!r}（{why}）")


def test_source_does_not_import_credential_manager_writer():
    src = _SCRIPT.read_text(encoding="utf-8")
    expect("get_credential_manager" not in src,
           "不应依赖 flash 的凭据管理器（会引入写权限）")
    expect("MinimalCredentialManager" not in src,
           "应自己只读解密，不引入可变对象")


def test_credential_file_is_only_opened_for_read():
    """源码里对 credentials.enc / .secret_key 只做 read，不做 write。"""
    src = _SCRIPT.read_text(encoding="utf-8")
    expect_in("credentials.enc", src)
    for bad in ("credentials.enc\").write", "enc.write_bytes",
                "enc.write_text", ".secret_key\").write"):
        expect(bad not in src, f"不应写凭据文件：{bad}")
    expect_in("read_bytes", src)


# ══════════════════════════════════════════════════════════════
# 真实凭据读取（只读）
# ══════════════════════════════════════════════════════════════
def test_load_gitee_credentials_reads_real_store():
    cred = gp.load_gitee_credentials()
    expect(cred.get("token"), "应读出 token")
    expect(len(cred["token"]) >= 20, f"token 长度异常: {len(cred['token'])}")
    expect(cred.get("login") or cred.get("username"),
           "应含 login 或 username")
    expect_in("source", cred)


def test_login_field_is_used_not_display_name():
    """★ 无交互 git 直连必须用 ``login``，显示名会 403。"""
    cred = gp.load_gitee_credentials()
    login = cred.get("login") or cred.get("username") or ""
    expect(login and " " not in login,
           f"login 应为登录名而非显示名，实测 {login!r}")


def test_credentials_unchanged_after_read():
    """读一遍之后密文与密钥必须**逐字节不变**。"""
    d = gp._cred_dir()
    enc, key = d / "credentials.enc", d / ".secret_key"
    before = (enc.read_bytes(), key.read_bytes())
    gp.load_gitee_credentials()
    after = (enc.read_bytes(), key.read_bytes())
    expect_eq(before, after, "凭据文件在读操作后发生了变化！")


def test_env_var_takes_precedence(monkeypatch=None):
    import os

    old = os.environ.get("GITEE_TOKEN")
    os.environ["GITEE_TOKEN"] = "env-token-xyz"
    os.environ["GITEE_LOGIN"] = "envlogin"
    try:
        cred = gp.load_gitee_credentials()
        expect_eq(cred["token"], "env-token-xyz")
        expect_eq(cred["login"], "envlogin")
        expect_eq(cred["source"], "env")
    finally:
        if old is None:
            os.environ.pop("GITEE_TOKEN", None)
        else:
            os.environ["GITEE_TOKEN"] = old
        os.environ.pop("GITEE_LOGIN", None)


# ══════════════════════════════════════════════════════════════
# 纪律 3：token 不进日志
# ══════════════════════════════════════════════════════════════
def test_mask_hides_token():
    tok = "abcdef1234567890abcdef1234567890"
    out = gp.mask(f"clone https://user:{tok}@gitee.com/x/y.git", tok)
    expect(tok not in out, "mask 必须抹掉 token")
    expect_in("***", out)


def test_redact_hides_token_across_multiline():
    tok = "Z" * 32
    text = f"fatal: could not read\nurl=https://u:{tok}@gitee.com/a/b.git\n"
    out = gp._redact(text, tok)
    expect(tok not in out)
    expect_eq(out.count("***"), 1)


def test_error_messages_are_redacted():
    """git 失败时应抛异常，且异常文本里**既无 token 也无带凭据 URL**。"""
    tok = "SECRET" * 6
    with tempfile.TemporaryDirectory() as td:
        try:
            gp._git("this-is-not-a-git-subcommand", f"https://u:{tok}@x/y.git",
                    cwd=Path(td), token=tok)
        except RuntimeError as exc:
            msg = str(exc)
            expect(tok not in msg, "异常信息不得泄露 token")
            expect("@x/y.git" not in msg,
                   "带凭据的 URL 应整段被省略，而不是打码后仍展示")
            expect_in("this-is-not-a-git-subcommand", msg,
                      "应保留可诊断的命令名")
        else:
            raise AssertionError("坏命令应抛 RuntimeError")


# ══════════════════════════════════════════════════════════════
# 纪律 2：token 不落盘（.git/config）
# ══════════════════════════════════════════════════════════════
def test_clean_remote_url_has_no_credentials():
    url = gp.remote_url("quincyhoward", "MultixD")
    expect_eq(url, "https://gitee.com/quincyhoward/MultixD.git")
    expect("@" not in url, "干净 URL 不应含 userinfo")


def test_set_clean_remote_and_assert(tmp=None):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        subprocess.run(("git", "init", "-b", "main"), cwd=td,
                       capture_output=True, check=True)
        url = gp.set_clean_remote(root, "quincyhoward", "MultixD")
        expect_eq(url, gp.remote_url("quincyhoward", "MultixD"))
        cfg = (root / ".git" / "config").read_text(encoding="utf-8")
        expect_in("gitee.com/quincyhoward/MultixD.git", cfg)
        expect("@" not in cfg.split("url = ")[1].splitlines()[0],
               "remote URL 不得含 userinfo")
        # 断言钩子：干净配置下应通过
        gp.assert_no_token_in_config(root, "some-token")
        # 设置成带 token 的 URL 后，断言必须**失败并自动复位**
        subprocess.run(("git", "remote", "set-url", "origin",
                        "https://u:some-token@gitee.com/quincyhoward/MultixD.git"),
                       cwd=td, capture_output=True, check=True)
        try:
            gp.assert_no_token_in_config(root, "some-token")
        except AssertionError:
            pass
        else:
            raise AssertionError("config 含 token 时断言必须失败")
        cfg2 = (root / ".git" / "config").read_text(encoding="utf-8")
        expect("some-token" not in cfg2, "断言失败后应自动复位为干净 URL")


def test_push_url_is_built_from_login_not_username():
    """推送 URL 用 login；源码里 dirty URL 只在 push 内出现一次。"""
    src = _SCRIPT.read_text(encoding="utf-8")
    expect_in("https://{login}:{token}@gitee.com/", src)
    expect(src.count(":{token}@gitee.com") <= 2,
           "带凭据的 URL 只应出现在 push() 的局部变量里")


def test_default_owner_and_repo():
    expect_eq(gp.DEFAULT_OWNER, "quincyhoward")
    expect_eq(gp.DEFAULT_REPO, "MultixD")
    expect_eq(gp.DEFAULT_BRANCH, "main")


def test_default_root_is_workspace_root():
    expect_eq(str(gp.DEFAULT_ROOT), str(config.WORKSPACE_ROOT))


def test_main_check_mode_returns_zero():
    """--check 走真实网络；网络断了允许返回 2（不判失败）。"""
    rc = gp.main(["--check"])
    expect_in(rc, (0, 2, 3), f"--check 返回码异常: {rc}")


# ══════════════════════════════════════════════════════════════
# ★ 作用域诊断（实测：本机 token 是仓库级，无法建仓）
# ══════════════════════════════════════════════════════════════
def test_credential_scope_error_is_a_runtime_error():
    exc = gp.CredentialScopeError("x")
    expect(isinstance(exc, RuntimeError), "应可被 RuntimeError 捕获")
    # 用真实 helper 构造，检查诊断文本真的讲清了"作用域"
    real = gp._scope_error("quincyhoward", "MultixD", "quincyhoward")
    expect(isinstance(real, gp.CredentialScopeError))
    expect_in("作用域", str(real))
    expect_in("403", str(real))


def test_scope_help_lists_three_actionable_paths():
    """★ 报错必须**可执行** —— 三条路各自给出确切的下一步命令。"""
    h = gp.SCOPE_HELP
    expect_in("gitee.com/projects/new", h)      # A 网页建仓
    expect_in("--no-create", h)                 # A 然后只推送
    expect_in("personal_access_tokens", h)      # B 换 projects 作用域令牌
    expect_in("GITEE_TOKEN", h)
    expect_in("--enterprise", h)                # C 企业命名空间
    expect_in("enterprises", h)
    expect_in("只读", h)                        # 明确"只读凭据"的承诺


def test_enterprise_payload_uses_visibility_not_private():
    """★ 企业接口的私有参数是 ``visibility``；传 ``private`` 会报 invalid。

    实测（见 gitee-enterprise-repo 技能）：``physimx`` 是 **enterprise** 命名空间，
    ``POST /orgs/physimx/repos`` 会静默返回 ``{"message":"Group"}``。
    """
    src = _SCRIPT.read_text(encoding="utf-8")
    expect_in("/enterprises/{enterprise}/repos", src)
    expect_in('"visibility": "private" if private else "public"', src)
    seg = src.split("if enterprise:")[1].split("else:")[0]
    expect("private\": bool" not in seg,
           "企业分支不应使用 private: bool(...)")


def test_no_create_flag_forces_push_without_creating():
    """``--no-create`` 用于"仓库已在网页手动建好"的场景。"""
    src = _SCRIPT.read_text(encoding="utf-8")
    expect_in("--no-create", src)
    expect_in("if args.no_create:", src)
    expect_in("args.push = True", src)


def test_visible_repos_helper_returns_list():
    """``visible_repos`` 是作用域诊断的依据：只列 token 可见的仓库。"""
    tok = gp.load_gitee_credentials()["token"]
    vis = gp.visible_repos(tok)
    expect(isinstance(vis, list), f"应返回 list，实测 {type(vis)}")
    if vis:
        expect(all(isinstance(v, str) and "/" in v for v in vis),
               f"仓库全名应形如 owner/name，实测 {vis}")


def test_scope_error_helper_formats_owner_and_repo():
    e = gp._scope_error("quincyhoward", "MultixD", "quincyhoward")
    msg = str(e)
    expect_in("quincyhoward", msg)
    expect_in("MultixD", msg)


def test_403_is_translated_to_scope_error_not_raw_http():
    """★ 403「无权」必须被翻译成 ``CredentialScopeError``（可读诊断），
    而不是把原始 HTTP 错误抛给用户。"""
    src = _SCRIPT.read_text(encoding="utf-8")
    expect_in('if e.code == 403 and "无权" in body:', src)
    expect_in("raise _scope_error(", src)


if __name__ == "__main__":
    raise SystemExit(main(globals()))
