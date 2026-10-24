"""统一命令执行器 —— 四种 target 共用的唯一命令面
═════════════════════════════════════════════════════════════════════

★ 2026-10-24（解耦计划 B1）：本模块把「在哪里执行」压缩成一个协议，
  使 `local` / `wsl` / `hpc-remote` / `hpc-insitu` 的差异**只**剩两处：
  ① executor 装配；② 是否需要传输层。

     target         executor         传输          作业形态
     local          LocalExecutor    同机 copy      bash run_flash.sh
     wsl            WslExecutor      /mnt/<d>/      bash run_flash.sh
     hpc-remote     SSHExecutor      sftp/scp       sbatch + sacct
     hpc-insitu     LocalExecutor    同机 copy      sbatch + sacct   ← 同一个

  因此 hpc_remote 与 hpc_insitu 只差「executor + 是否传输入」，
  不再是两套 3500 行实现。

Windows→wsl.exe 的两个真实坑（都有对应处置，见 WslExecutor）：
  · `wsl bash -c "... ls *.chk"` 的 `*` 会被 Windows 侧先吃掉 ⇒ 一律用
    `ls -1 --` / `find`，不要依赖 shell glob。
  · `wsl ... | tail` 的 `$?` 是 tail 的（恒 0）⇒ 退出码写哨兵再解析，
    绝不信 wsl.exe 自己的 returncode。
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Protocol, Tuple

__all__ = [
    "CommandExecutor",
    "LocalExecutor",
    "WslExecutor",
    "SSHExecutor",
    "make_executor",
]


class CommandExecutor(Protocol):
    """统一命令执行协议。

    ★ 只有 `run()` 是必需的；其余方法带默认实现（按「本地文件系统」语义），
    SSH/WSL 各自覆写传输部分。这样 slurm_control 只依赖 run()，
    而 artifacts 只依赖 listdir/copy_from。
    """

    target: str

    def run(self, cmd: str, timeout: int = 120) -> Tuple[str, str, int]:
        """执行命令，返回 (stdout, stderr, returncode)。"""

    # ── 文件面（默认按"同机"语义实现，远程执行器覆写） ──
    def listdir(self, path: str) -> List[str]:
        out, _err, rc = self.run(f"ls -1 -- '{path}' 2>/dev/null", timeout=60)
        if rc != 0:
            return []
        return [ln.strip() for ln in out.splitlines() if ln.strip()]

    def exists(self, path: str) -> bool:
        _out, _err, rc = self.run(f"test -e '{path}'", timeout=30)
        return rc == 0

    def mkdir_p(self, path: str) -> bool:
        _out, _err, rc = self.run(f"mkdir -p '{path}'", timeout=30)
        return rc == 0

    def copy_from(self, remote: str, local: Path) -> bool:
        return _copy_local(remote, local)

    def put(self, local: Path, remote: str) -> bool:
        return _copy_local(local, Path(remote), src_is_file=True)

    def put_dir(self, local_dir: Path, remote_dir: str) -> bool:
        self.mkdir_p(remote_dir)
        try:
            shutil.copytree(local_dir, remote_dir, dirs_exist_ok=True)
            return True
        except OSError:
            return False

    def close(self) -> None:
        return None


def _copy_local(src, dst: Path, src_is_file: bool = False) -> bool:
    src_p = Path(src)
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src_p.is_dir():
            shutil.copytree(src_p, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src_p, dst)
        return True
    except OSError:
        return False


class LocalExecutor:
    """本机 POSIX 直接执行（`local` 与 `hpc-insitu` 共用）。"""

    target = "local"

    def __init__(self, shell: str = "bash") -> None:
        self.shell = shell

    def run(self, cmd: str, timeout: int = 120) -> Tuple[str, str, int]:
        # `set -o pipefail` + `-c`：管道中段失败不再被最后一段的 0 掩盖
        r = subprocess.run(
            [self.shell, "-c", f"set -o pipefail; {cmd}"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout,
        )
        return r.stdout or "", r.stderr or "", r.returncode

    def listdir(self, path: str) -> List[str]:
        out, _err, rc = self.run(f"ls -1 -- '{path}' 2>/dev/null", timeout=60)
        return [ln.strip() for ln in out.splitlines() if ln.strip()] if rc == 0 else []

    def exists(self, path: str) -> bool:
        return self.run(f"test -e '{path}'", timeout=30)[2] == 0

    def mkdir_p(self, path: str) -> bool:
        return self.run(f"mkdir -p '{path}'", timeout=30)[2] == 0

    def copy_from(self, remote: str, local: Path) -> bool:
        return _copy_local(remote, local)

    def put(self, local: Path, remote: str) -> bool:
        return _copy_local(local, Path(remote))

    def put_dir(self, local_dir: Path, remote_dir: str) -> bool:
        return _copy_local(local_dir, Path(remote_dir))

    def close(self) -> None:
        return None


class WslExecutor:
    """Windows → WSL 执行器。

    关键：**退出码来自哨兵**，不是 wsl.exe 的 returncode。
    `wsl.exe` 在管道/多命令场景会把返回码丢失或透传错误值，
    历史 bug 表现为「rc=0 但日志为空」的静默失败。
    """

    target = "wsl"

    def __init__(self, distro: str = "", user: str = "") -> None:
        self.distro = distro
        self.user = user

    def _base(self) -> List[str]:
        cmd = ["wsl"]
        if self.distro:
            cmd += ["-d", self.distro]
        if self.user:
            cmd += ["-u", self.user]
        return cmd + ["--", "bash", "-lc"]

    def run(self, cmd: str, timeout: int = 120) -> Tuple[str, str, int]:
        # 单引号包裹整段，内部单引号转义 ⇒ 三层传参不再二次展开
        quoted = "'" + cmd.replace("'", "'\"'\"'") + "'"
        wrapped = (
            "set -o pipefail; "
            f"{cmd}\n"
            "__flash_rc=$?\n"
            "echo \"__FLASH_RC__=${__flash_rc}\""
        )
        try:
            r = subprocess.run(
                [*self._base(), wrapped],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return "", f"timeout after {timeout}s", 124
        out, err = r.stdout or "", r.stderr or ""
        rc = r.returncode
        kept: List[str] = []
        for line in out.splitlines():
            if "__FLASH_RC__=" in line:
                try:
                    rc = int(line.split("__FLASH_RC__=", 1)[1].strip())
                except ValueError:
                    pass
            else:
                kept.append(line)
        return "\n".join(kept), err, rc

    def listdir(self, path: str) -> List[str]:
        # 不使用 glob（Windows 侧会吃掉 `*`）
        out, _err, rc = self.run(f"ls -1 -- '{path}' 2>/dev/null", timeout=60)
        return [ln.strip() for ln in out.splitlines() if ln.strip()] if rc == 0 else []

    def exists(self, path: str) -> bool:
        return self.run(f"test -e '{path}'", timeout=30)[2] == 0

    def mkdir_p(self, path: str) -> bool:
        return self.run(f"mkdir -p '{path}'", timeout=30)[2] == 0

    def put_dir(self, local_dir: Path, remote_dir: str) -> bool:
        """Windows 路径 → WSL 内路径的目录复制（走 WSL 内 cp，避免 /mnt 慢速往返）。"""
        wsl_src = to_wsl_path(str(local_dir))
        return self.run(f"mkdir -p '{remote_dir}' && cp -a '{wsl_src}/.' '{remote_dir}/'",
                        timeout=1800)[2] == 0

    def copy_from(self, remote: str, local: Path) -> bool:
        wsl_dst = to_wsl_path(str(local.parent))
        local.parent.mkdir(parents=True, exist_ok=True)
        return self.run(f"mkdir -p '{wsl_dst}' && cp -a '{remote}' '{wsl_dst}/'",
                        timeout=600)[2] == 0

    def close(self) -> None:
        return None


def to_wsl_path(win_path: str) -> str:
    """`E:\\a\\b` → `/mnt/e/a/b`；已是 POSIX 路径则幂等返回。"""
    p = str(win_path).replace("\\", "/")
    if p.startswith("/"):
        return p
    if len(p) > 1 and p[1] == ":":
        return f"/mnt/{p[0].lower()}{p[2:]}"
    return p


class SSHExecutor:
    """超算远程执行器（包装唯一 SSH 实现 RemoteSession）。

    ★ 会话延迟建立：构造不连接，首次 run/传输才 `__enter__`，
      避免「只想 dry-run 却先连 SSH」。
    """

    target = "hpc-remote"

    def __init__(self, session=None, credential: str = "flash_ssh", verbose: bool = True):
        from .session import RemoteSession   # 延迟导入：本模块可裸跑

        self._session = session or RemoteSession(credential, verbose=verbose)
        self._entered = False

    def _ensure(self):
        if not self._entered:
            self._session.__enter__()
            self._entered = True
        return self._session

    def run(self, cmd: str, timeout: int = 120) -> Tuple[str, str, int]:
        return self._ensure().run(cmd, timeout=timeout)

    def listdir(self, path: str) -> List[str]:
        return self._ensure().listdir(path)

    def exists(self, path: str) -> bool:
        return self._ensure().exists(path)

    def mkdir_p(self, path: str) -> bool:
        return self._ensure().mkdir_p(path)

    def copy_from(self, remote: str, local: Path) -> bool:
        local.parent.mkdir(parents=True, exist_ok=True)
        return self._ensure().download(remote, str(local))

    def put(self, local: Path, remote: str) -> bool:
        self._ensure().mkdir_p(str(Path(remote).parent).replace("\\", "/"))
        return self._ensure().upload(str(local), remote)

    def put_dir(self, local_dir: Path, remote_dir: str) -> bool:
        return self._ensure().put_dir(str(local_dir), remote_dir)

    def close(self) -> None:
        if self._entered:
            self._session.__exit__(None, None, None)
            self._entered = False


def make_executor(target: str, *, distro: str = "", credential: str = "flash_ssh",
                  session=None, verbose: bool = True) -> CommandExecutor:
    """按 target 装配执行器（四种 target 的唯一装配点）。"""
    t = (target or "").strip().lower()
    if t in ("local", "hpc-insitu", "insitu"):
        return LocalExecutor()
    if t == "wsl":
        return WslExecutor(distro=distro)
    if t in ("hpc-remote", "hpc", "remote", "ssh"):
        return SSHExecutor(session=session, credential=credential, verbose=verbose)
    raise ValueError(f"未知 target: {target!r}（应为 local|wsl|hpc-remote|hpc-insitu）")
