# -*- coding: utf-8 -*-
"""fetch_hpc_output.py — SNBVTi1um / SNBVTi3um 远端结果并行取回 (NC-E)。

复用既有权威组件，不引入第二套真相源:
  - 会话原语: SNBOneCH_ml._HpcRemote (凭据动态路由 + paramiko)
  - 文件选择: flash/flash_run/remote/fetch_policy.py (chk-only 为全场景默认,
    plt 须 --with-plt 显式开启; fixed=日志/.dat 恒保留)
  - 幂等闸门: 远端/本地文件大小一致即跳过; 收敛遍顺序重下缺失项
  - 并行策略: 每 worker 线程一个复用会话 (threading.local, 规避 paramiko
    非线程安全挂死) + 单文件 3 次重试 —— 2026-09-15 实测 4.81 MB/s / 失败率 0.6%

用法 (仓库根目录执行):
  python flash/scenarios/private/tracer/SNB/SNBVTi1um/scripts/fetch_hpc_output.py \
      --scen SNBVTi1um SNBVTi3um --account flash_ssh --jobs 6
  --list-only  # 只清点远端与队列状态, 不下载
"""
from __future__ import annotations

import argparse
import importlib
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import paramiko

HERE = Path(__file__).resolve().parent          # .../SNBVTi1um/scripts
REPO = HERE.parents[6]                          # flash 包根 (含 pyproject.toml)
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import (  # noqa: E402
    _resolve_route_and_credential,
)
from flash.scenarios.private.tracer.SNB.SNBOneCH_ml import (  # noqa: E402
    SNBOneCH_ml as R,
)

ROUTE: dict | None = None   # main() 内解析一次; 快速通道与 _HpcRemote 同一凭据源


def _new_sftp(tries: int = 4):
    """新建持久 Transport+SFTP (大窗口+1MB 包, keepalive)。

    与旧路径 (每文件新建连接) 对比: 2026-10-09 实测每文件握手开销在网络
    慢时段可达 10-30 s, 是聚合吞吐的支配项。凭据仍来自
    remote_ssh_helper._resolve_route_and_credential (唯一真相源)。
    """
    last = None
    for i in range(tries):
        try:
            t = paramiko.Transport((ROUTE["host"], int(ROUTE["port"])))
            t.set_keepalive(15)
            t.connect(username=ROUTE["username"], password=ROUTE["password"])
            if not t.is_active():
                raise RuntimeError("transport inactive")
            sftp = paramiko.SFTPClient.from_transport(
                t, window_size=1 << 25, max_packet_size=1 << 20)
            return t, sftp
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"SFTP 连接失败 x{tries}: {last}")


def _sftp_get(sftp, rp: str, lp: Path, size: int | None) -> None:
    """流式下载单文件 (prefetch 管道化 + 1MB 读块)。"""
    with sftp.open(rp, "rb") as fr:
        if size is None:
            size = fr.stat().st_size
        with open(lp, "wb") as fw:
            fr.prefetch(size)
            while True:
                buf = fr.read(1 << 20)
                if not buf:
                    break
                fw.write(buf)
# fetch_policy 按文件路径加载, 避免 import flash 包副作用 (与既有消费方一致)
import importlib.util as _ilu  # noqa: E402


def _load_fetch_policy():
    for _root in Path(__file__).resolve().parents:
        _f = _root / "flash" / "flash_run" / "remote" / "fetch_policy.py"
        if _f.is_file():
            _spec = _ilu.spec_from_file_location("_fetch_policy", _f)
            _mod = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)
            return _mod
    raise ImportError("fetch_policy.py not found above " + str(__file__))


FP = _load_fetch_policy()


def load_scen(name: str):
    """按裸模块名加载场景模块。

    ★ 不能用 `importlib.import_module('flash...SNB.' + name)`: 同名目录
      (无 __init__.py) 会作为命名空间包**遮蔽** .py 模块 (实测 __file__=None,
      全部常量缺失)。与 _longrun_lib 同法: 场景目录加入 sys.path 后按裸名导入
      —— 目录内 <name>.py 与 <name>/ 目录不重名冲突, 文件模块稳定胜出。
    """
    scen_dir = REPO / "flash" / "scenarios" / "private" / "tracer" / "SNB" / name
    if str(scen_dir) not in sys.path:
        sys.path.insert(0, str(scen_dir))
    return importlib.import_module(name)


def log(msg: str, level: str = "INFO") -> None:
    tag = {"INFO": "[i]", "OK": "[OK]", "WARN": "[!]", "ERROR": "[X]"}.get(level, "[i]")
    print(f"  {tag} {msg}", flush=True)


def human(nb: float) -> str:
    for u in ("B", "KB", "MB", "GB", "TB"):
        if abs(nb) < 1024:
            return f"{nb:.1f} {u}"
        nb /= 1024.0
    return f"{nb:.1f} PB"


def human_dur(sec: float) -> str:
    if sec < 60:
        return f"{sec:.0f}s"
    if sec < 3600:
        return f"{sec/60:.1f}min"
    return f"{sec/3600:.2f}h"


def remote_list(remote, rdir: str, timeout: int = 90):
    """远端目录普通文件 (名, 大小); 排除软链 (find -type f)。"""
    out, _, _ = remote.run(
        f"cd {rdir} 2>/dev/null && "
        f"find . -maxdepth 1 -type f -printf '%s %f\\n' 2>/dev/null | sort -k2",
        timeout=timeout)
    names, sizes = [], []
    for l in (out or "").splitlines():
        parts = l.split(maxsplit=1)
        if len(parts) == 2 and parts[0].isdigit():
            sizes.append(int(parts[0]))
            names.append(parts[1].strip())
    return names, sizes


def resolve_snb_home(remote, retries: int = 3) -> str:
    """解析远端 FLASHSNB/FLASH4.8 绝对路径 (SFTP 不展开 ~, 铁律)。"""
    lit = R._remote_snb_home()
    for attempt in range(retries):
        for pc in ('printf %s "$HOME"', 'echo $HOME'):
            try:
                out, _, _ = remote.run(pc, timeout=30)
            except Exception:
                continue
            cand = (out or "").strip()
            if cand.startswith("/"):
                return cand.rstrip("/") + "/" + lit[2:]
        log(f"  $HOME 探测第 {attempt+1}/{retries} 轮为空, 5s 后重试", "WARN")
        time.sleep(5)
    raise RuntimeError(f"远端 $HOME 探测失败; 无法解析 {lit}")


def preflight(remote, scen_names) -> bool:
    """作业仍在排队/运行 → 返回 False (中止下载)。"""
    out, _, _ = remote.run(
        'squeue -u "$USER" -h -o "%i|%j|%T|%M" 2>/dev/null || true', timeout=60)
    lines = [l for l in (out or "").splitlines() if l.strip()]
    if not lines:
        log("squeue: 队列为空 (无本用户在跑/排队作业)")
        return True
    hit = []
    for l in lines:
        for s in scen_names:
            if s.lower() in l.lower():
                hit.append(l.strip())
    if hit:
        for l in hit:
            log(f"  作业仍在: {l}", "WARN")
        return False
    for l in lines:
        log(f"  队列: {l.strip()}")
    return True


def fetch_one(rm, scen_mod, account: str, local_dir: Path,
              jobs: int, with_plt: bool, frames: int) -> int:
    """单场景取回。返回 0=完成 / 2=仍有不完整文件。"""
    name = scen_mod.SCENE_NAME
    obj = SNB_HOME + "/" + scen_mod.OBJDIR
    log(f"远端源: {obj}")
    log(f"本地目标: {local_dir}")

    names, sizes = remote_list(rm, obj)
    if not names:
        log(f"远端目录为空或不可达: {obj}", "ERROR")
        return 2
    rsize = dict(zip(names, sizes))

    picked, st = FP.select_fetch_files(
        names, basenm=scen_mod.BASENM,
        log_names=[getattr(scen_mod, "LOG_FILE", "") or ""],
        with_plt=with_plt, frames=frames)
    log(f"远端清单: chk={st['n_chk']}, plt={st['n_plt']}, fixed={st['n_fixed']}")
    if st["plt_skipped"]:
        log(f"chk-only 策略: 跳过 {st['plt_skipped']} 个 plt 文件 (--with-plt 可改)")
    tot_b = sum(rsize.get(n, 0) for n in picked)
    log(f"选取 {len(picked)} 文件 / {human(tot_b)} (frames={frames or 'ALL'})")

    local_dir.mkdir(parents=True, exist_ok=True)
    have = {p.name: p.stat().st_size for p in local_dir.iterdir() if p.is_file()}
    todo = [n for n in picked if have.get(n) != rsize.get(n, -1)]
    log(f"本地已有(大小匹配): {len(picked)-len(todo)}; 需下载: {len(todo)} "
        f"({human(sum(rsize.get(n, 0) for n in todo))})")
    if not todo:
        log(f"[{name}] ✓ 全部已同步", "OK")
        return 0

    # ── 并行下载: 每线程一个持久 SFTP 会话 + 4 次重试(断线重连) + 大小闸门 ──
    tls = threading.local()
    lock = threading.Lock()
    stats = {"ok": 0, "fail": 0, "bytes": 0}
    t0 = time.time()

    def _sess():
        st = getattr(tls, "sp", None)
        if st is None:
            st = tls.sp = _new_sftp()
        return st

    def _drop():
        st = getattr(tls, "sp", None)
        if st is not None:
            try:
                st[1].close()
                st[0].close()
            except Exception:  # noqa: BLE001
                pass
            tls.sp = None

    def _one(nm: str):
        rp = f"{obj}/{nm}"
        lp = local_dir / nm
        exp = rsize.get(nm)
        tt = time.time()
        last = None
        for attempt in range(1, 5):
            try:
                _sftp_get(_sess()[1], rp, lp, exp)
                dt = time.time() - tt
                act = lp.stat().st_size if lp.exists() else -1
                if act > 0 and (exp is None or act == exp):
                    return nm, True, act, dt
                last = f"sizeFAIL(act={act},exp={exp})"
            except Exception as e:  # noqa: BLE001
                last = f"{type(e).__name__}: {e}"[:120]
            _drop()                      # 会话可能已坏 → 弃置重连
            if attempt < 4:
                time.sleep(3 * attempt)
        return nm, False, (lp.stat().st_size if lp.exists() else -1), \
            time.time() - tt

    workers = min(jobs, max(1, len(todo)))
    log(f"启动 {workers} 线程并行下载 (持久 SFTP 会话 + 4 次重试)...")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_one, nm): nm for nm in todo}
        done = 0
        for fu in as_completed(futs):
            done += 1
            try:
                nm, good, act, dt = fu.result()
            except Exception as e:  # noqa: BLE001
                with lock:
                    stats["fail"] += 1
                log(f"  ✗ {futs[fu]}: {type(e).__name__}: {e}", "WARN")
                continue
            with lock:
                if good:
                    stats["ok"] += 1
                    stats["bytes"] += act
                else:
                    stats["fail"] += 1
                if done % 20 == 0 or done == len(todo):
                    el = time.time() - t0
                    log(f"  [{done}/{len(todo)}] ok={stats['ok']} fail={stats['fail']} "
                        f"{human(stats['bytes'])} {stats['bytes']/1e6/max(el,1e-9):.2f}MB/s")

    el = time.time() - t0
    log(f"并行下载完成: 成功 {stats['ok']}, 失败 {stats['fail']}, "
        f"{human(stats['bytes'])} / {human_dur(el)} "
        f"= {stats['bytes']/1e6/max(el,1e-9):.2f} MB/s")

    # ── 收敛遍: 顺序重下缺失/尺寸不符者 ──
    def _sizes():
        return {p.name: p.stat().st_size for p in local_dir.iterdir() if p.is_file()}

    bad = [n for n in picked if _sizes().get(n) != rsize.get(n, -1)]
    if bad:
        log(f"收敛遍: 顺序重下 {len(bad)} 个...", "WARN")
        st = _new_sftp()             # 收敛遍用单个持久会话顺序补齐
        try:
            for n in bad:
                lp = local_dir / n
                try:
                    if lp.exists():
                        lp.unlink()
                except OSError as e:
                    log(f"  [converge] ✗ {n}: 旧文件删除失败 {e}", "WARN")
                    continue
                try:
                    _sftp_get(st[1], f"{obj}/{n}", lp, rsize.get(n))
                except Exception as e:  # noqa: BLE001
                    log(f"  [converge] ✗ {n}: {type(e).__name__}: {e}", "WARN")
                    try:
                        st[1].close()
                        st[0].close()
                    except Exception:  # noqa: BLE001
                        pass
                    st = _new_sftp()
                act = lp.stat().st_size if lp.exists() else -1
                good = act == rsize.get(n, -1)
                log(f"  [converge] {'OK' if good else 'FAIL'} {n} {act}",
                    "OK" if good else "WARN")
        finally:
            try:
                st[1].close()
                st[0].close()
            except Exception:  # noqa: BLE001
                pass

    still = [n for n in picked if _sizes().get(n) != rsize.get(n, -1)]
    fs = [f for f in local_dir.iterdir() if f.is_file()]
    log(f"[{name}] 本地最终: {len(fs)} 文件 / {human(sum(f.stat().st_size for f in fs))}")
    if still:
        log(f"仍有 {len(still)} 个不完整 → 重跑本脚本自动补齐", "WARN")
        return 2
    log(f"[{name}] ✓ 同步完成", "OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="SNBVTi1um/3um HPC 结果并行取回")
    ap.add_argument("--scen", nargs="+",
                    default=["SNBVTi1um", "SNBVTi3um"])
    ap.add_argument("--account", default="flash_ssh")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--with-plt", action="store_true",
                    help="连 plt 一起下载 (默认 chk-only, 2026-09-16 全场景定案)")
    ap.add_argument("--frames", type=int, default=0,
                    help="chk 抽帧数; 0=全量")
    ap.add_argument("--list-only", action="store_true",
                    help="只清点远端与队列状态, 不下载")
    args = ap.parse_args()

    print("=" * 70)
    print(f" SNBVTi HPC fetch — scen={args.scen} account={args.account} "
          f"jobs={args.jobs}")
    print("=" * 70)

    rm = R._HpcRemote(args.account)
    rm.__enter__()
    global SNB_HOME, ROUTE
    try:
        SNB_HOME = resolve_snb_home(rm)
        log(f"远端 SNB_HOME = {SNB_HOME}")
        if not args.list_only:
            ROUTE = _resolve_route_and_credential(args.account)
            log("快速通道就绪: 持久 SFTP 会话 (凭据源 remote_ssh_helper)")
        if not preflight(rm, args.scen):
            log("检测到同场景作业仍在队列中 → 中止下载 (防取到半截数据)", "ERROR")
            return 3
        if args.list_only:
            for s in args.scen:
                m = load_scen(s)
                obj = SNB_HOME + "/" + m.OBJDIR
                names, sizes = remote_list(rm, obj)
                chks, plts, fixed = FP.classify_names(
                    names, basenm=m.BASENM,
                    log_names=[getattr(m, "LOG_FILE", "") or ""])
                cb = sum(dict(zip(names, sizes)).get(n, 0) for n in chks)
                pb = sum(dict(zip(names, sizes)).get(n, 0) for n in plts)
                fb = sum(dict(zip(names, sizes)).get(n, 0) for n in fixed)
                log(f"[{s}] objdir: chk={len(chks)}/{human(cb)}, "
                    f"plt={len(plts)}/{human(pb)}, fixed={len(fixed)}/{human(fb)}")
                for n in fixed:
                    log(f"    fixed: {n} ({dict(zip(names, sizes)).get(n, 0)} B)")
                if chks:
                    log(f"    chk 首帧: {chks[0]}, 末帧: {chks[-1]}")
            log("--list-only 完成, 未下载", "OK")
            return 0
        rc = 0
        for s in args.scen:
            m = load_scen(s)
            local_dir = Path(m.OUTPUT_DIR) / f"hpc_{args.account}"
            r = fetch_one(rm, m, args.account, local_dir,
                          args.jobs, args.with_plt, args.frames)
            rc = rc or r
        return rc
    finally:
        try:
            rm.__exit__(None, None, None)
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    sys.exit(main())
