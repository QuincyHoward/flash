"""
FLASH 超算 SSH 操作助手 (基于 ssh CLI / paramiko + 动态路由)
═════════════════════════════════════════════════════════════════════

两种传输后端:
  1. **paramiko** (Windows 默认) —— 进程内纯 Python SSH 认证，
     不依赖 SSH_ASKPASS / tty。实测 2026-09-12: Windows 上
     `ssh` CLI + SSH_ASKPASS 注入密码时**挂起至超时**（askpass 不被触发），
     而 paramiko 直连 2.7 s 成功 → Windows 一律走 paramiko。
  2. **ssh/scp CLI + SSH_ASKPASS** (Linux/macOS 默认) —— 传统路径。
     可用环境变量 `FLASH_SSH_BACKEND` 强制指定（`paramiko` / `cli`）。

自动从凭据系统加载密码 + 动态选择最佳路由 (TCP 延迟探测)。
"""

import os
import sys
import time
import tempfile
import subprocess
import posixpath
import platform
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Callable


# ── 传输后端选择 ────────────────────────────────

def _use_paramiko() -> bool:
    """是否使用 paramiko 后端。

    默认: Windows 用 paramiko (CLI+ASKPASS 在 Windows 上会挂起),
    Linux/macOS 用 CLI。`FLASH_SSH_BACKEND` 可强制覆写。
    """
    force = os.environ.get("FLASH_SSH_BACKEND", "").strip().lower()
    if force == "paramiko":
        return True
    if force == "cli":
        return False
    return platform.system().lower() == "windows"


def _connect_paramiko(route: Dict[str, Any], timeout: int = 45):
    """建立 paramiko 连接 (密码认证)。调用方负责 close()。"""
    import paramiko
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(
        hostname=route["host"],
        port=int(route["port"]),
        username=route["username"],
        password=route["password"],
        timeout=min(timeout, 30),
        banner_timeout=45,
        auth_timeout=45,
        allow_agent=False,
        look_for_keys=False,
    )
    return cli


def _paramiko_run(route: Dict[str, Any], command: str, timeout: int = 60) -> Tuple[str, str, int]:
    """paramiko 执行远程命令，返回 (stdout, stderr, exit_code)。"""
    try:
        cli = _connect_paramiko(route, timeout)
    except Exception as e:
        return "", f"paramiko connect failed: {e}", -1
    try:
        _si, so, se = cli.exec_command(command, timeout=timeout)
        out = so.read().decode("utf-8", errors="replace")
        err = se.read().decode("utf-8", errors="replace")
        code = so.channel.recv_exit_status()
        return out, err, code
    except Exception as e:
        return "", f"paramiko exec failed: {e}", -1
    finally:
        cli.close()


def _paramiko_put(route: Dict[str, Any], local_path: str,
                  remote_path: str, timeout: int = 120) -> bool:
    """paramiko SFTP 上传（自动创建远端父目录）。"""
    try:
        cli = _connect_paramiko(route, timeout)
    except Exception:
        return False
    try:
        sftp = cli.open_sftp()
        remote_dir = posixpath.dirname(remote_path)
        if remote_dir:
            cur = ""
            for part in remote_dir.split("/"):
                if not part:
                    cur = "/"
                    continue
                cur = (cur.rstrip("/") + "/" + part) if cur else part
                try:
                    sftp.stat(cur)
                except OSError:
                    try:
                        sftp.mkdir(cur)
                    except OSError:
                        pass
        sftp.put(local_path, remote_path)
        sftp.close()
        return True
    except Exception:
        return False
    finally:
        cli.close()


def _paramiko_get(route: Dict[str, Any], remote_path: str,
                  local_path: str, timeout: int = 120) -> bool:
    """paramiko SFTP 下载。"""
    try:
        cli = _connect_paramiko(route, timeout)
    except Exception:
        return False
    try:
        sftp = cli.open_sftp()
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        sftp.get(remote_path, local_path)
        sftp.close()
        return True
    except Exception:
        return False
    finally:
        cli.close()


# ── SSH 可执行文件查找 ──────────────────────────

_SSH_PATH: Optional[str] = None
_SCP_PATH: Optional[str] = None


def _find_ssh() -> str:
    """查找系统上可用的 SSH 可执行文件。

    在 Windows 上优先使用 Git Bash 的 ssh (支持 SSH_ASKPASS)。
    回退到系统 PATH 中的 ssh。
    """
    global _SSH_PATH
    if _SSH_PATH:
        return _SSH_PATH

    if platform.system().lower() == "windows":
        # 常见 Git Bash/msys2 安装路径
        candidates = [
            r"C:\Program Files\Git\usr\bin\ssh.exe",
            r"C:\Program Files\Git\bin\ssh.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Git\usr\bin\ssh.exe"),
            os.path.expanduser(r"~\.workbuddy\vendor\PortableGit\usr\bin\ssh.exe"),
        ]
        for c in candidates:
            if os.path.exists(c):
                _SSH_PATH = c
                return _SSH_PATH

    # 回退: 使用 PATH 中的 ssh
    _SSH_PATH = "ssh"
    return _SSH_PATH


def _find_scp() -> str:
    """查找系统上可用的 SCP 可执行文件。

    优先使用与 ssh 相同目录的 scp (确保版本匹配)。
    """
    global _SCP_PATH
    if _SCP_PATH:
        return _SCP_PATH

    ssh_path = _find_ssh()
    if ssh_path != "ssh":
        scp_candidate = ssh_path.replace("ssh.exe", "scp.exe")
        if os.path.exists(scp_candidate):
            _SCP_PATH = scp_candidate
            return _SCP_PATH

    _SCP_PATH = "scp"
    return _SCP_PATH


def _resolve_route_and_credential(credential_name: Optional[str] = None) -> Dict[str, Any]:
    """解析凭据 + 动态选择最佳路由 (或使用手动指定)。

    根据凭据中的 connection_mode 字段决定:
      - "auto" (默认): 自动测试所有路由，选择最快线路
      - "manual": 使用用户手动指定的 host/port/username

    Returns:
        {"host": str, "port": int, "username": str, "password": str}
    """
    from flash._core.credentials import load_ssh_credentials
    from flash.flash_run.remote.route_tester import (
        RouteTester, test_and_select_best_route,
        ROUTES_SCFA2696, ROUTES_SCH0348,
    )

    cred = load_ssh_credentials(credential_name)
    if cred is None:
        raise RuntimeError(
            f"凭据未找到: {credential_name or '(主账户)'}"
            "\n请先运行: python -m flash._core.credentials.manage"
        )

    # 打印当前选中的账户
    cred_label = credential_name or "flash_ssh (主账户)"
    ssh_user = cred.get("username") or cred.get("ssh_username", "?")
    print(f"  [Credential] 选中: {cred_label}  ({ssh_user})")

    password = cred.get("password", "")
    if not password:
        raise RuntimeError(f"凭据 {credential_name or '(主账户)'} 未设置密码")

    # 检查连接模式
    connection_mode = cred.get("connection_mode", "auto")

    if connection_mode == "manual":
        # 手动指定模式: 使用用户保存的 host/port/username
        host = cred.get("host", "")
        port = int(cred.get("port", 22))
        username = cred.get("username", "")
        if not host or not username:
            raise RuntimeError(
                f"手动模式但 host/username 未设置。\n"
                f"请运行: python -m flash._core.credentials.manage\n"
                f"并选择 manual 模式填写主机/端口/用户名"
            )
        print(f"  [Route] 手动指定: {username}@{host}:{port}")
        return {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
        }

    # 自动模式: 使用 route_tester 选择最佳路由
    # (routes_for_account 认得凭据记录里的 route_key="nc_e"/"bscc_t6";
    #  旧的裸比较 route_key=="scfa2696" 永不匹配 → flash_ssh 被误路由到 BSCC)
    routes = RouteTester.routes_for_account(credential_name or "flash_ssh", cred)

    best = test_and_select_best_route(
        RouteTester.account_label(credential_name or "flash_ssh", cred),
        routes,
    )
    if best is None:
        raise RuntimeError("所有 SSH 路由均不可达 (TCP 连接失败)")

    print(f"  [Route] 最佳路由: {best['host']}:{best['port']} ({best['latency_ms']:.0f}ms)")
    return {
        "host": best["host"],
        "port": int(best["port"]),
        "username": best["username"],
        "password": password,
    }


def _build_ssh_args(route: Dict[str, Any], command: str, timeout: int = 60) -> List[str]:
    """构建 SSH CLI 参数。

    注意:
      - 使用 _find_ssh() 确保使用正确的 ssh 可执行文件
      - 允许 keyboard-interactive (ParaCloud 的密码认证方式)
      - 不加 PreferredAuthentications 限制，让 SSH 客户端自动协商
    """
    ssh_exe = _find_ssh()
    return [
        ssh_exe,
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=15",
        "-o", "BatchMode=no",
        "-o", "NumberOfPasswordPrompts=1",
        "-p", str(route["port"]),
        f"{route['username']}@{route['host']}",
        command,
    ]


def _create_askpass_script(password: str) -> str:
    """创建 SSH_ASKPASS 脚本，返回路径。

    在 Windows 上使用 .bat 文件 (而非 .sh)，因为 Windows 无法直接
    执行 .sh 脚本。SSH_ASKPASS 需要系统能直接运行的程序。
    """
    import platform as _plt
    is_windows = _plt.system().lower() == "windows"

    if is_windows:
        # Windows: 使用 .bat 文件
        script = tempfile.NamedTemporaryFile(
            mode="w", suffix=".bat", delete=False, newline="\r\n"
        )
        script.write("@echo off\n")
        script.write(f"echo {password}\n")
        script.close()
    else:
        # Linux/macOS: 使用 .sh 文件
        script = tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", delete=False, newline="\n"
        )
        script.write("#!/bin/sh\n")
        script.write(f'echo "{password}"\n')
        script.close()
        os.chmod(script.name, 0o755)

    return script.name


# ── SSH 命令执行 ──────────────────────────────────

def ssh_cmd(
    route: Dict[str, Any],
    command: str,
    timeout: int = 60,
    verbose: bool = False,
) -> Tuple[str, str, int]:
    """通过 SSH CLI 执行远程命令 (自动密码注入)。

    Args:
        route: {"host", "port", "username", "password"}
        command: 远程命令
        timeout: 超时秒数
        verbose: 是否打印命令

    Returns:
        (stdout, stderr, exit_code)
    """
    if _use_paramiko():
        return _paramiko_run(route, command, timeout=timeout)

    password = route["password"]
    args = _build_ssh_args(route, command, timeout)
    askpass_path = _create_askpass_script(password)

    env = os.environ.copy()
    env["SSH_ASKPASS"] = askpass_path
    env["DISPLAY"] = ":0"  # SSH_ASKPASS needs DISPLAY

    if verbose:
        print(f"  [CMD] ssh -p {route['port']} {route['username']}@{route['host']} '{command[:60]}...'")

    try:
        r = subprocess.run(
            args, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, env=env,
        )
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout", -1
    except Exception as e:
        return "", str(e), -1
    finally:
        # 清理临时脚本
        try:
            os.unlink(askpass_path)
        except OSError:
            pass


# ── SCP 操作 ──────────────────────────────────────

def scp_upload(
    route: Dict[str, Any],
    local_path: str,
    remote_path: str,
    timeout: int = 60,
    verbose: bool = False,
) -> bool:
    """通过 SCP 上传文件。

    Returns:
        是否成功
    """
    if _use_paramiko():
        if verbose:
            print(f"  [SFTP] {Path(local_path).name} -> {remote_path}")
        for attempt in range(3):
            if _paramiko_put(route, local_path, remote_path, timeout=timeout):
                return True
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
        return False

    password = route["password"]
    askpass_path = _create_askpass_script(password)
    scp_exe = _find_scp()

    args = [
        scp_exe,
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=15",
        "-P", str(route["port"]),
        local_path,
        f"{route['username']}@{route['host']}:{remote_path}",
    ]

    env = os.environ.copy()
    env["SSH_ASKPASS"] = askpass_path
    env["DISPLAY"] = ":0"

    if verbose:
        print(f"  [SCP] {Path(local_path).name} -> {remote_path}")

    try:
        for attempt in range(3):
            r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=env)
            if r.returncode == 0:
                return True
            time.sleep(3 * (attempt + 1))
        return False
    except Exception:
        return False
    finally:
        try:
            os.unlink(askpass_path)
        except OSError:
            pass


def scp_download(
    route: Dict[str, Any],
    remote_path: str,
    local_path: str,
    timeout: int = 120,
    verbose: bool = False,
) -> bool:
    """通过 SCP 下载文件。

    Returns:
        是否成功
    """
    if _use_paramiko():
        if verbose:
            print(f"  [SFTP] {remote_path} -> {local_path}")
        for attempt in range(3):
            if _paramiko_get(route, remote_path, local_path, timeout=timeout):
                return True
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
        return False

    password = route["password"]
    askpass_path = _create_askpass_script(password)
    scp_exe = _find_scp()

    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    args = [
        scp_exe,
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=15",
        "-P", str(route["port"]),
        f"{route['username']}@{route['host']}:{remote_path}",
        local_path,
    ]

    env = os.environ.copy()
    env["SSH_ASKPASS"] = askpass_path
    env["DISPLAY"] = ":0"

    if verbose:
        print(f"  [SCP] {remote_path} -> {local_path}")

    try:
        for attempt in range(3):
            r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=env)
            if r.returncode == 0:
                return True
            time.sleep(3 * (attempt + 1))
        return False
    except Exception:
        return False
    finally:
        try:
            os.unlink(askpass_path)
        except OSError:
            pass


# ── 上下文管理器 ──────────────────────────────────

class RemoteSession:
    """远程 SSH 会话上下文管理器。

    自动处理: 凭据加载 → 路由测试 → SSH 命令执行 → 清理。

    用法:
        with RemoteSession() as session:
            out, err, code = session.run("ls -la")
            session.upload(local_path, remote_path)
            session.download(remote_path, local_path)
    """

    def __init__(self, credential_name: Optional[str] = None, verbose: bool = True):
        self.credential_name = credential_name
        self.verbose = verbose
        self._route: Optional[Dict[str, Any]] = None

    def __enter__(self) -> "RemoteSession":
        if self.verbose:
            print("[RemoteSession] 正在连接超算 (动态路由选择)...")
        self._route = _resolve_route_and_credential(self.credential_name)
        # 测试连接 (最多重试 3 次，应对网络波动)
        last_err = ""
        for attempt in range(1, 4):
            out, err, code = self.run("echo REMOTE_SESSION_OK", timeout=30)
            if code == 0:
                if self.verbose:
                    print(f"  [OK] 已连接 ({self._route['host']}:{self._route['port']})"
                          f" (尝试 {attempt})")
                return self
            last_err = err[:200]
            if attempt < 3:
                if self.verbose:
                    print(f"  [WARN] 连接测试失败 (尝试 {attempt}/3): 等待 3s 后重试...")
                import time as _time
                _time.sleep(3)

        # 提供手动诊断命令
        host = self._route["host"]
        port = self._route["port"]
        user = self._route["username"]
        diag_cmd = (
            f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 "
            f"-p {port} {user}@{host} 'echo SSH_OK'"
        )
        raise RuntimeError(
            f"SSH 连接测试失败 (已重试 3 次)\n"
            f"  路由: {user}@{host}:{port}\n"
            f"  最后一次错误: {last_err}\n"
            f"  手动诊断: {diag_cmd}"
        )

    def __exit__(self, *args):
        if self.verbose:
            print("  [RemoteSession] 会话结束")

    def run(self, command: str, timeout: int = 60) -> Tuple[str, str, int]:
        """执行远程命令。"""
        if self._route is None:
            raise RuntimeError("未连接，请在 with 块中使用")
        if self.verbose and len(command) < 150:
            print(f"  [CMD] {command}")
        return ssh_cmd(self._route, command, timeout=timeout, verbose=False)

    def upload(self, local_path: str, remote_path: str) -> bool:
        """上传文件。"""
        if self._route is None:
            raise RuntimeError("未连接")
        return scp_upload(
            self._route, local_path, remote_path,
            verbose=self.verbose,
        )

    def download(self, remote_path: str, local_path: str) -> bool:
        """下载文件。"""
        if self._route is None:
            raise RuntimeError("未连接")
        return scp_download(
            self._route, remote_path, local_path,
            verbose=self.verbose,
        )


# ── 便捷单次调用函数 ──────────────────────────────

def quick_run(
    command: str,
    credential_name: Optional[str] = None,
    timeout: int = 60,
) -> Tuple[str, str, int]:
    """单次执行远程命令 (自动连接/断开)。"""
    route = _resolve_route_and_credential(credential_name)
    return ssh_cmd(route, command, timeout=timeout, verbose=False)


def quick_upload(
    local_path: str,
    remote_path: str,
    credential_name: Optional[str] = None,
) -> bool:
    """单次上传文件。"""
    route = _resolve_route_and_credential(credential_name)
    return scp_upload(route, local_path, remote_path, verbose=False)


def quick_download(
    remote_path: str,
    local_path: str,
    credential_name: Optional[str] = None,
) -> bool:
    """单次下载文件。"""
    route = _resolve_route_and_credential(credential_name)
    return scp_download(route, remote_path, local_path, verbose=False)
