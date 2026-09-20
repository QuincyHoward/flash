"""补全下载 NC-E job 4864358 的全部输出到本地 hpc_flash_ssh/。

★★★ 2026-09-12 事故与修正 (必读):
    现象: 首次运行时 10.1 MB 的 chk **全部下载失败**, 留下 20 个 0 字节 `.part`,
          而只有 2 MB 的 plt 与 1.8 MB 的 log 成功。
    根因: 项目 `RemoteSession.download()` -> `scp_download(route, r, l, verbose=True)`
          **没有转发 timeout** -> 永远用默认 `timeout=120`。10.1 MB chk 在
          121 ms RTT 的 SFTP 链路上常需 >120 s -> `subprocess` 被超时杀掉,
          写出的 `.part` 为 0 字节。
          （`_paramiko_get` 里的 `sftp.get()` 更是**完全没有 timeout**。）
    修正: 本脚本**不走 `RemoteSession.download`**, 直接用 paramiko 自建 SFTP,
          并对每个文件设置:
            - 显式 `sock.settimeout(600)` (单次 socket 读超时)
            - 外层**重试 3 次**, 每次失败清掉半截文件
            - 下载后**校验字节数**, 一致才原子改名
          小文件与大文件用同一路径, 不再有 120 s 暗坑。

用法:
  python _fetch_nce_results.py              # 补齐 (尺寸一致则跳过)
  python _fetch_nce_results.py --force      # 全部重下
  python _fetch_nce_results.py --dry-run    # 只列差异
"""
import argparse
import os
import posixpath
import re
import socket
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "..", ".."))

LOCAL_DIR = os.path.join(SCRIPT_DIR, "flash_output", "hpc_flash_ssh")

sys.path.insert(0, SCRIPT_DIR)
import SNBOneCH_ml as S  # noqa: E402

REMOTE_OBJ = f"{S._remote_snb_home()}/" + S.OBJDIR

SOCK_TIMEOUT = 900      # 单次 socket 读超时 (s)
CONN_TIMEOUT = 60
RETRY = 3


def _log(msg, tag="i"):
    print(f"[{tag}] {msg}", flush=True)


def _route(account):
    """取路由 (host/port/user/password), 复用项目动态探测。"""
    from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import (
        _resolve_route_and_credential)
    return _resolve_route_and_credential(account)


def _ssh(route, timeout=CONN_TIMEOUT):
    import paramiko
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(hostname=route["host"], port=int(route["port"]),
                username=route["username"], password=route["password"],
                timeout=min(timeout, 30), banner_timeout=60,
                auth_timeout=60, allow_agent=False, look_for_keys=False)
    tr = cli.get_transport()
    if tr is not None:
        tr.set_keepalive(30)
    return cli


def remote_ls(sftp, rdir):
    """{name: size} —— 用 SFTP listdir_attr (比 ls -la 解析更可靠)。"""
    res = {}
    for a in sftp.listdir_attr(rdir):
        try:
            if a.st_mode and (a.st_mode & 0o170000) == 0o10000000:
                pass
        except Exception:  # noqa: BLE001
            pass
        res[a.filename] = int(a.st_size)
    return res


def sftp_get(sftp, rpath, lpath, expect, label):
    """下载单文件: 显式 socket 超时 + 重试 + 字节数校验。"""
    for attempt in range(1, RETRY + 1):
        part = lpath + ".part"
        for f in (part,):
            try:
                if os.path.exists(f):
                    os.remove(f)
            except OSError:
                pass
        try:
            # 关键: 给底层 channel 设超时, 避免无限挂起
            sftp.get_channel().settimeout(SOCK_TIMEOUT)
            t0 = time.time()
            sftp.get(rpath, part)
            dt = time.time() - t0
            got = os.path.getsize(part) if os.path.isfile(part) else -1
            if got == expect and got > 0:
                if os.path.exists(lpath):
                    os.remove(lpath)
                os.rename(part, lpath)
                sp = got / dt / 1e6 if dt > 0 else 0
                _log(f"      OK {label} {got} B in {dt:.1f}s ({sp:.2f} MB/s)")
                return True
            _log(f"      [!] 尝试{attempt}: 尺寸 {got} != 期望 {expect}", "WARN")
        except Exception as exc:  # noqa: BLE001
            _log(f"      [!] 尝试{attempt}: {type(exc).__name__}: {exc}",
                 "WARN")
        time.sleep(3 * attempt)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--account", default="flash_ssh")
    ap.add_argument("--only", default="", help="逗号分隔文件名过滤")
    args = ap.parse_args()

    os.makedirs(LOCAL_DIR, exist_ok=True)
    _log(f"本地: {LOCAL_DIR}")
    _log(f"远端: {REMOTE_OBJ}")

    t0 = time.time()
    route = _route(args.account)
    _log(f"路由: {route['username']}@{route['host']}:{route['port']}")
    cli = _ssh(route)
    _log("SSH/SFTP 已连接")
    try:
        sftp = cli.open_sftp()
        sftp.get_channel().settimeout(SOCK_TIMEOUT)
        # ★★ SFTP 不展开 `~` (与 scp CLI 不同) -> 必须先解析 $HOME 成绝对路径
        try:
            _, home_out, _ = cli.exec_command("printf '%s' \"$HOME\"",
                                              timeout=30)
            home = home_out.read().decode().strip()
        except Exception:  # noqa: BLE001
            home = ""
        if not home.startswith("/"):
            _log(f"$HOME 解析失败 (got={home!r})", "ERR")
            return 1
        # ★★★ 结果**不在 objdir**, 而在 deploy 的 `_out/` 收集目录!
        #   2026-09-12 发现: run.sh 结尾会把 chk/plt 等移入
        #   <HOME>/QC/SNBOneCH_ml_deploy/_out/, objdir 里 0 个 chk。
        #   且 _out 比 objdir 更**权威**(集中、有人为筛选: 实测 23 chk + 6 plt)。
        remote_obj = f"{home}/QC/SNBOneCH_ml_deploy/_out"
        _log(f"远端绝对路径: {remote_obj}")
        try:
            rfiles = remote_ls(sftp, remote_obj)
        except Exception as exc:  # noqa: BLE001
            _log(f"远端列目录失败: {exc}", "ERR")
            return 1
        _log(f"远端文件数: {len(rfiles)}")

        want = []
        for name, size in sorted(rfiles.items()):
            if (name.startswith(S.BASENM) or name.startswith("wsl_run_")
                    or name.startswith("run_") or name == "flash.par"
                    or name == "_t_start"):
                want.append((name, size))
        if args.only:
            keep = set(args.only.split(","))
            want = [(n, s) for n, s in want if n in keep]
        _log(f"候选条目: {len(want)}")

        todo, skip = [], []
        for name, rsize in want:
            lp = os.path.join(LOCAL_DIR, name)
            if args.force:
                todo.append((name, rsize, "force"))
            elif not os.path.isfile(lp):
                todo.append((name, rsize, "missing"))
            elif os.path.getsize(lp) != rsize:
                todo.append((name, rsize,
                             f"size {os.path.getsize(lp)}->{rsize}"))
            else:
                skip.append((name, rsize))

        print("-" * 78)
        print(f"完整(跳过): {len(skip)}")
        for n, s in skip:
            print(f"    OK   {n:<44s} {s:>12d}")
        print(f"需下载     : {len(todo)}  合计 {sum(s for _,s,_ in todo)/1e6:.1f} MB")
        for n, s, w in todo:
            print(f"    TODO {n:<44s} {s:>12d}  ({w})")
        print("-" * 78, flush=True)

        if args.dry_run or not todo:
            _log("dry-run 或无待下载项")
            return 0

        ok = fail = 0
        for i, (name, rsize, why) in enumerate(todo, 1):
            lp = os.path.join(LOCAL_DIR, name)
            rp = posixpath.join(remote_obj, name)
            _log(f"[{i}/{len(todo)}] {name}  ({rsize/1e6:.1f} MB, {why})")
            if sftp_get(sftp, rp, lp, rsize, name):
                ok += 1
            else:
                fail += 1
                _log(f"      [x] 最终失败: {name}", "ERR")

        dt = time.time() - t0
        print("=" * 78)
        _log(f"下载完毕: 成功 {ok} / 失败 {fail}, 耗时 {dt:.1f}s")

        print("-" * 78)
        print("本地 hpc_flash_ssh/ 最终清单:")
        tot = 0
        for f in sorted(os.listdir(LOCAL_DIR)):
            p = os.path.join(LOCAL_DIR, f)
            sz = os.path.getsize(p)
            tot += sz
            print(f"    {f:<46s} {sz:>12d}"
                  + ("   <-- 未完成" if f.endswith(".part") else ""))
        print(f"    合计 {tot/1e6:.1f} MB")
        print("=" * 78, flush=True)
        return 0 if fail == 0 else 2
    finally:
        try:
            cli.close()
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    sys.exit(main())
