"""从 NC-E 下载 FLASH 结果的稳健并行下载器。

★★★ 2026-09-12 两轮事故总结 (本脚本的设计依据):

  事故1 -- 静默超时:
    项目 `RemoteSession.download()` -> `scp_download(..., verbose=True)`
    **不转发 timeout** -> 恒为默认 120 s; 10.1 MB chk 在 121 ms RTT 上需 ~580 s
    -> subprocess 被超时杀掉, 留下 **0 字节 .part**, 且**误判为"文件已下载"**。

  事故2 -- 连接复用导致雪崩:
    修正超时后首文件成功 (chk_0000, 587 s), 但随后 **SSH 会话被服务端断开**
    (`SSHException: Server connection dropped`), 而我的重试**复用同一个死连接**
    -> 后续 10 个文件全部 `OSError: Socket is closed`, 失败被放大。

  本脚本的对策:
    1. **每个文件独立建连** (开→传→关), 避免长会话被中间设备掐断后连累后续;
    2. **连接级重试**: 文件失败 -> 重建连接再试 (最多 N 轮);
    3. **多线程并行** (默认 4 连接), 绕开单条 SFTP 窗口的 17 KB/s 瓶颈;
    4. **逐文件字节数校验**, 一致才原子改名 (防半截文件被当成品);
    5. 下载前**重新列目录**取权威尺寸 (远端可能已变)。

实测单连接 ~17 KB/s (121 ms RTT); 4 连接并行可望 ~4x。
"""
import argparse
import os
import posixpath
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 本脚本在 <scene>/ 下 → 场景根上溯 5 级 = 内层 flash; 再 1 级 = 外层根
INNER = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "..", ".."))
ROOT = os.path.abspath(os.path.join(INNER, ".."))
LOCAL_DIR = os.path.join(SCRIPT_DIR, "flash_output", "hpc_flash_ssh")

sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.join(INNER, "scenarios", "flash_demo", "demo_hpc"))
sys.path.insert(0, ROOT)
from remote_ssh_helper import _resolve_route_and_credential  # noqa: E402
import SNBOneCH_ml as S  # noqa: E402

REMOTE_SUBDIR = "QC/SNBOneCH_ml_deploy/_out"   # ★ 结果在 deploy/_out, 不在 objdir

SOCK_TIMEOUT = 1800
CONN_TIMEOUT = 60
ROUNDS = 4            # 整体重试轮数


def _log(msg, tag="i"):
    print(f"[{tag}] {msg}", flush=True)


_lock = threading.Lock()


def _connect(route):
    import paramiko
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(hostname=route["host"], port=int(route["port"]),
                username=route["username"], password=route["password"],
                timeout=min(CONN_TIMEOUT, 30), banner_timeout=90,
                auth_timeout=90, allow_agent=False, look_for_keys=False)
    tr = cli.get_transport()
    if tr is not None:
        tr.set_keepalive(20)
    sftp = cli.open_sftp()
    sftp.get_channel().settimeout(SOCK_TIMEOUT)
    return cli, sftp


def remote_dir(route):
    """远端绝对路径 + 文件清单。"""
    cli, sftp = _connect(route)
    try:
        _, o, _ = cli.exec_command('printf "%s" "$HOME"', timeout=30)
        home = o.read().decode().strip()
        rdir = posixpath.join(home, REMOTE_SUBDIR)
        files = {a.filename: int(a.st_size)
                 for a in sftp.listdir_attr(rdir)}
        return rdir, files
    finally:
        try:
            cli.close()
        except Exception:  # noqa: BLE001
            pass


def get_one(route, rdir, name, expect, lpath):
    """单文件下载 (独立连接, 内部短重试)。返回 (name, ok, detail)。"""
    part = lpath + ".part"
    try:
        if os.path.exists(part):
            os.remove(part)
    except OSError:
        pass
    cli = sftp = None
    try:
        cli, sftp = _connect(route)
        t0 = time.time()
        sftp.get(posixpath.join(rdir, name), part)
        dt = time.time() - t0
        got = os.path.getsize(part) if os.path.isfile(part) else -1
        if got == expect and got > 0:
            if os.path.exists(lpath):
                os.remove(lpath)
            os.rename(part, lpath)
            return (name, True, f"{got}B in {dt:.0f}s "
                                f"({got/dt/1e6:.2f} MB/s)")
        return (name, False, f"size {got} != {expect}")
    except Exception as exc:  # noqa: BLE001
        return (name, False, f"{type(exc).__name__}: {exc}")
    finally:
        for c in (sftp, cli):
            try:
                if c is not None:
                    c.close()
            except Exception:  # noqa: BLE001
                pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--account", default="flash_ssh")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    os.makedirs(LOCAL_DIR, exist_ok=True)
    t0 = time.time()
    route = _resolve_route_and_credential(args.account)
    rdir, files = remote_dir(route)
    _log(f"远端: {rdir}  文件数={len(files)}")

    want = {n: s for n, s in files.items()
            if n.startswith(S.BASENM) or n.startswith("wsl_run_")}
    _log(f"候选: {len(want)}")

    todo, skip = [], []
    for n, s in sorted(want.items()):
        lp = os.path.join(LOCAL_DIR, n)
        if not args.force and os.path.isfile(lp) and os.path.getsize(lp) == s:
            skip.append((n, s))
        else:
            todo.append((n, s))
    print("-" * 76)
    print(f"跳过 {len(skip)} / 待下载 {len(todo)} "
          f"({sum(s for _,s in todo)/1e6:.1f} MB)")
    for n, s in todo:
        print(f"    TODO {n:<44s} {s:>12d}")
    print("-" * 76, flush=True)
    if args.dry_run or not todo:
        return 0

    # 多轮 + 并行
    remain = todo
    for rnd in range(1, ROUNDS + 1):
        if not remain:
            break
        _log(f"===== 第 {rnd}/{ROUNDS} 轮, {len(remain)} 个文件, "
             f"{args.workers} 并行 =====")
        nxt = []
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(get_one, route, rdir, n, s,
                              os.path.join(LOCAL_DIR, n)): (n, s)
                    for n, s in remain}
            for fu in as_completed(futs):
                n, s = futs[fu]
                try:
                    nm, ok, det = fu.result()
                except Exception as exc:  # noqa: BLE001
                    nm, ok, det = n, False, f"{type(exc).__name__}: {exc}"
                with _lock:
                    if ok:
                        _log(f"    OK   {nm}  {det}")
                    else:
                        _log(f"    FAIL {nm}  {det}", "WARN")
                        nxt.append((n, s))
        remain = nxt
        if remain and rnd < ROUNDS:
            time.sleep(10)

    okn = len(todo) - len(remain)
    print("=" * 76)
    _log(f"完成: 成功 {okn}/{len(todo)}, 剩余失败 {len(remain)}, "
         f"耗时 {(time.time()-t0)/60:.1f} min")
    if remain:
        for n, s in remain:
            _log(f"     仍缺: {n}", "ERR")

    print("-" * 76)
    print("本地 hpc_flash_ssh/ 清单:")
    tot = 0
    for f in sorted(os.listdir(LOCAL_DIR)):
        p = os.path.join(LOCAL_DIR, f)
        z = os.path.getsize(p)
        tot += z
        print(f"    {f:<46s} {z:>12d}"
              + ("   <-- .part" if f.endswith(".part") else ""))
    print(f"    合计 {tot/1e6:.1f} MB")
    print("=" * 76, flush=True)
    return 0 if not remain else 2


if __name__ == "__main__":
    sys.exit(main())
