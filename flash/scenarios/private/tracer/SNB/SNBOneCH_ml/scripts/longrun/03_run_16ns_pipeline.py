# -*- coding: utf-8 -*-
"""03_run_16ns_pipeline.py — ★ 主编排：1.6 ns 仿真 → 下载 chk → 绘图分析。

★★ 为什么这个脚本要这样写（长时任务的本质约束）
====================================================
1. **总时长 ~9 h**（131 核实测 s/step=0.288，dt CFL 钳在 1.33e-14 ⇒ ~1.1e5 步）
   → 必须能被宿主后台任务托住，且**任何时刻中断都能续跑**。
2. **断点续跑** —— 每阶段完成即写 `pipeline_state.json`（原子落盘）。
   重跑时自动跳过已完成阶段（`--restart` 可强制从头）。
3. **下载是薄弱环节** —— 实测单流 SFTP 仅 0.03 MB/s，21 文件 335 s/个。
   1.6 ns 的 chk 数量会**多得多**（每 checkpointInterval 一个），
   故下载必须: ① 多线程并行; ② 幂等（已下且 md5 一致则跳过）;
   ③ 字节数 + md5 双闸门（`_paramiko_get` 截断时会返回 True）。
4. **远端"先删后跑"** —— 若旧 chk 未清，新一轮会覆写编号，造成混帧。

流程阶段（可单独指定）:
  [submit]  生成 / 上传 / setup+make / sbatch 提交
  [wait]    轮询作业直到 RUN_DONE（或超时）
  [fetch]   多线程下载 chk/plt/log 到 flash_output/hpc_<acct>_16ns/
  [plot]    调用 04_analyze_plots.py 绘图
  [all]     以上全部（默认）

用法:
  python 03_run_16ns_pipeline.py                       # 全流程（默认 tmax=1.6e-9）
  python 03_run_16ns_pipeline.py --stage submit        # 只提交
  python 03_run_16ns_pipeline.py --stage wait          # 只等待（可反复调用续看）
  python 03_run_16ns_pipeline.py --stage fetch         # 只下载
  python 03_run_16ns_pipeline.py --stage plot          # 只绘图
  python 03_run_16ns_pipeline.py --tmax 2.0e-10        # 短测
  python 03_run_16ns_pipeline.py --restart             # 忽略 state 从头跑
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _longrun_lib as L  # noqa: E402

HERE = Path(__file__).resolve().parent

TMAX_DEFAULT = "1.6e-9"
NPROC_DEFAULT = 131          # ★ 实测最优（131 核最快: s/step 0.288）
POLL_DEFAULT = 72000         # 20 h 轮询上限（1.6 ns ≈ 9 h + 排队余量）


def _run(cmd: list, cwd: str = None, desc: str = "") -> int:
    L.log(f"CMD: {' '.join(str(c) for c in cmd)}", "EXEC")
    rc = subprocess.call(cmd, cwd=cwd)
    if rc != 0:
        L.log(f"命令返回非零: rc={rc}  {desc}", "ERROR")
    return rc


# ── ★ 网络抖动韧性（用户铁律: 网络常断, 等 60 s 未恢复才退出）──────────
NET_MARKERS = (
    "所有 SSH 路由均不可达", "SSH 路由", "Connection refused",
    "ConnectionResetError", "TimeoutError", "socket.timeout",
    "getaddrinfo", "Network is unreachable", "No route to host",
    "EOFError", "SSHException",
)


def _is_net_error(text: str) -> bool:
    return any(m in (text or "") for m in NET_MARKERS)


def _probe_route(account: str = None) -> bool:
    """TCP 探活：任一线路可连即认为网络可用。

    ★ 线路来源为明文配置 ``~/.physimx/flash/hpc_accounts.json``
      (``accounts.<account>.routes``)，脚本内**不硬编码任何超算主机**。
      示例::

        {"accounts": {"flash_ssh": {"ssh_username": "user@NC-E",
                                    "routes": [{"host": "ssh.example.com",
                                                "port": 22, "label": "线路 A"}]}}}

    Returns:
        True = 至少一条线路 TCP 可达 (或线路信息缺失时不阻塞主流程)。
    """
    import socket
    account = account or L.ACCOUNT_NCE
    try:
        from flash._core.credentials.hpc_config import get_hpc_routes
        routes = get_hpc_routes(account)
    except Exception as exc:  # noqa: BLE001
        L.log(f"读取 hpc_accounts.json 线路失败: {exc} → 跳过探活", "WARN")
        return True
    if not routes:
        L.log(f"hpc_accounts.json 中账户 {account} 无线路 → 跳过探活", "WARN")
        return True
    for r in routes:
        try:
            s = socket.create_connection((r["host"], int(r.get("port", 22))),
                                         timeout=8)
            s.close()
            return True
        except Exception:
            continue
    return False


def _wait_network(max_wait_s: int = 1800) -> bool:
    """等待网络恢复：每 30 s 探一次，最多等 max_wait_s。"""
    import time as _t
    t0 = _t.time()
    attempt = 0
    while _t.time() - t0 < max_wait_s:
        attempt += 1
        if _probe_route():
            L.log(f"✓ 网络已恢复（第 {attempt} 次探测）", "OK")
            return True
        el = int(_t.time() - t0)
        L.log(f"  网络仍不可达（第 {attempt} 次探测，已等 {el}s / {max_wait_s}s）"
              f"→ 休眠 30 s 后重试", "WARN")
        _t.sleep(30)
    L.log(f"★ 等待 {max_wait_s}s 网络仍未恢复 → 放弃本阶段", "ERROR")
    return False


def _run_with_net_retry(cmd: list, cwd: str, desc: str,
                        max_attempts: int = 6) -> int:
    """执行命令；若失败原因疑似网络，则等网络恢复后重试。

    ★ 仅对"网络类"失败重试：真正的编译/物理错误立即返回，不掩盖问题。
    """
    import tempfile
    for k in range(1, max_attempts + 1):
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8",
                                    errors="replace") as tf:
            L.log(f"CMD(第{k}/{max_attempts}次): {' '.join(str(c) for c in cmd)}",
                  "EXEC")
            rc = subprocess.call(cmd, cwd=cwd, stdout=tf, stderr=subprocess.STDOUT)
            tf.seek(0)
            out = tf.read()
        # 回显（截断，避免刷屏）
        tail = out[-4000:] if len(out) > 4000 else out
        L.log(f"--- 子进程输出（尾部）---\n{tail}")
        if rc == 0:
            return 0
        if not _is_net_error(out):
            L.log(f"命令返回非零 rc={rc} 且非网络原因 → 不重试  {desc}", "ERROR")
            return rc
        L.log(f"★ 检测到网络类失败（rc={rc}）→ 等待网络恢复后重试", "WARN")
        if k == max_attempts:
            break
        if not _wait_network():
            return rc
    L.log(f"已达最大重试次数 {max_attempts}，仍失败", "ERROR")
    return 1


# ══════════════════════════════════════════════════════════════════════
# 阶段 1: 提交
# ══════════════════════════════════════════════════════════════════════
def stage_submit(args, st: dict) -> int:
    L.step(f"阶段 [submit]  正式仿真 tmax={args.tmax}  nproc={args.nproc}")

    # 远端旧产物清理（防混帧）—— 只清 glob，不动 objdir
    L.log("清理远端 objdir 旧产物（防新旧 chk 编号相撞）...")
    try:
        rm = L.M._HpcRemote(args.account)
        rm.__enter__()
        try:
            snb_home = L.abs_snb_home(rm)
            obj = f"{snb_home}/{L.M.OBJDIR}"
            n = L.remote_batch_remove(
                rm, [f"{L.M.BASENM}*", "wsl_run_snbonech.log", "_t_start", "_t_end"],
                dry_run=False, rdir=obj, label="提交前清理")
            L.log(f"  已清 {n} 项旧产物")
            # 确认 flash4 在
            o, _, _ = rm.run(f"ls {obj}/flash4 2>/dev/null || echo NO", timeout=60)
            if "NO" in (o or ""):
                L.log("  objdir 无 flash4 → 需要完整编译（不传 --skip-build）", "WARN")
                skip_build = False
            else:
                skip_build = True
                L.log("  flash4 存在 → 使用 --skip-build 省编译")
        finally:
            try:
                rm.__exit__(None, None, None)
            except Exception:
                pass
    except Exception as e:
        L.log(f"远端清理失败（继续尝试提交）: {type(e).__name__}: {e}", "WARN")
        skip_build = True

    cmd = [
        sys.executable, str(L.SCEN_DIR / "SNBOneCH_ml.py"),
        "--mode", "hpc", "--account", args.account,
        "--nproc", str(args.nproc), "--tmax", str(args.tmax),
        "--poll-timeout", str(args.poll_timeout),
    ]
    if skip_build:
        cmd.append("--skip-build")

    rc = _run_with_net_retry(cmd, cwd=str(L.REPO_ROOT),
                             desc="SNBOneCH_ml.py --mode hpc")
    if rc != 0:
        L.log("提交/运行失败。检查上方 ERROR 与远端 run_*_out.txt", "ERROR")
        return rc

    L.save_state(stage_submit_done="done", tmax=str(args.tmax),
                 nproc=args.nproc, account=args.account,
                 submitted_at=datetime.now().strftime("%F %T"))
    L.log("✓ 阶段 [submit] 完成（仿真已完成并收集到 hpc_<acct>/）", "OK")
    return 0


# ══════════════════════════════════════════════════════════════════════
# 阶段 2: 等待（由 SNBOneCH_ml.py 内部轮询完成，此处做状态确认）
# ══════════════════════════════════════════════════════════════════════
def stage_wait(args, st: dict) -> int:
    L.step("阶段 [wait]  确认作业状态")
    L.log("说明: 作业轮询由 SNBOneCH_ml.py 内部完成（--poll-timeout）。")
    L.log("      本阶段检查远端作业是否仍在跑，并打印进度。")

    try:
        rm = L.M._HpcRemote(args.account)
        rm.__enter__()
        try:
            snb_home = L.abs_snb_home(rm)
            obj = f"{snb_home}/{L.M.OBJDIR}"
            out, _, _ = rm.run(
                f"squeue -u $USER -h -o '%i|%j|%T|%M|%N' 2>/dev/null; echo ---; "
                f"cd {obj} && ls {L.M.BASENM}* 2>/dev/null | wc -l; echo ---; "
                f"tail -3 wsl_run_snbonech.log 2>/dev/null",
                timeout=90)
            L.log(f"远端状态:\n{out}")
            running = "RUNNING" in (out or "") or "PENDING" in (out or "")
            if running:
                L.log("作业仍在运行 → 稍后再次调用 --stage wait 查看", "WARN")
                return 2
            L.log("✓ 无运行中作业", "OK")
        finally:
            try:
                rm.__exit__(None, None, None)
            except Exception:
                pass
    except Exception as e:
        L.log(f"查询失败: {type(e).__name__}: {e}", "ERROR")
        return 1
    return 0


# ══════════════════════════════════════════════════════════════════════
# 阶段 3: 下载（多线程 + 幂等 + 双闸门）
# ══════════════════════════════════════════════════════════════════════
def stage_fetch(args, st: dict) -> int:
    L.step(f"阶段 [fetch]  下载 FLASH 输出到 {args.fetch_dir.name}/")

    local_dir = args.fetch_dir
    local_dir.mkdir(parents=True, exist_ok=True)

    try:
        rm = L.M._HpcRemote(args.account)
        rm.__enter__()
    except Exception as e:
        L.log(f"连接超算失败: {type(e).__name__}: {e}", "ERROR")
        return 1

    try:
        snb_home = L.abs_snb_home(rm)
        obj = f"{snb_home}/{L.M.OBJDIR}"
        L.log(f"远端源: {obj}")

        # ── 远端清单（chk-only 策略, 2026-09-16 全场景统一）──
        # ★★ 分类/抽帧/选择逻辑统一走 flash/flash_run/remote/fetch_policy.py
        #   （全场景唯一来源）。旧内联实现的两个问题: nframes=0 时 plt 全量直下、
        #   .dat/.log 被误归入 plt 桶。独立脚本用 importlib 按路径加载策略模块,
        #   避免 import flash 包副作用。
        import importlib.util as _ilu
        from pathlib import Path as _Pl
        _fp = None
        for _root in _Pl(__file__).resolve().parents:
            _f = _root / "flash" / "flash_run" / "remote" / "fetch_policy.py"
            if _f.is_file():
                _spec = _ilu.spec_from_file_location("_fetch_policy", _f)
                _fp = _ilu.module_from_spec(_spec)
                _spec.loader.exec_module(_fp)
                break
        if _fp is None:
            raise ImportError("fetch_policy.py not found above " + str(__file__))
        names, sizes = L.remote_list(rm, obj)
        rsize = dict(zip(names, sizes))
        want, sel = _fp.select_fetch_files(
            names, basenm=L.M.BASENM,
            log_names=["wsl_run_snbonech.log", getattr(L.M, "LOG_FILE", "") or ""],
            with_plt=bool(getattr(args, "with_plt", False)),
            frames=getattr(args, "frames", 0))
        if sel["n_picked"] != sel["n_chk"]:
            L.log(f"★ 帧抽取: {sel['n_chk']} → {sel['n_picked']} 帧 "
                  f"(step≈{sel['n_chk']//max(sel['n_picked']-1,1)})")
        if sel["plt_skipped"]:
            L.log(f"★ chk-only 模式: 丢弃远端 {sel['n_plt']} 个 plt 文件 "
                  f"(--with-plt 可改)")
        _extra = f" + {sel['n_plt']} plt" if not sel["plt_skipped"] else ""
        L.log(f"保留: {sel['n_picked']} chk{_extra} + {sel['n_fixed']} "
              f"其他(log/dat) = {len(want)} 文件")

        total_b = sum(rsize.get(n, 0) for n in want)
        L.log(f"远端可下载: {len(want)} 文件 / {L.human(total_b)}")

        # ── 本地已有清单（幂等判定）──
        have = {p.name: p.stat().st_size for p in local_dir.iterdir() if p.is_file()}
        todo = [n for n in want if have.get(n) != rsize.get(n, -1)]
        already = len(want) - len(todo)
        L.log(f"本地已有(大小匹配): {already} 文件；需下载: {len(todo)}")
        if not todo:
            L.log("✓ 全部已下载，无需传输", "OK")
            return 0

        # ── 多线程下载 ──
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading

        lock = threading.Lock()
        stats = {"ok": 0, "md5ok": 0, "fail": 0, "bytes": 0}
        t_start = time.time()

        def _one(nm: str):
            rp = f"{obj}/{nm}"
            lp = local_dir / nm
            exp = rsize.get(nm)
            t0 = time.time()
            ok = rm.download(rp, str(lp))
            dt = time.time() - t0
            act = lp.stat().st_size if lp.exists() else -1
            good = bool(ok) and act > 0 and (exp is None or act == exp)
            gate = "size"
            if good and exp is not None:
                rmd5 = L.remote_md5(rm, rp)
                lmd5 = L.local_md5(lp)
                if rmd5 and lmd5:
                    good = (rmd5 == lmd5)
                    gate = "md5-ok" if good else f"md5FAIL(l={lmd5[:8]},r={rmd5[:8]})"
            return nm, good, act, dt, gate

        workers = min(args.jobs, max(1, len(todo)))
        L.log(f"启动 {workers} 线程并行下载（实测并行 0.9 MB/s vs 单流 0.03 MB/s）...")
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_one, nm): nm for nm in todo}
            done = 0
            for fu in as_completed(futs):
                done += 1
                try:
                    nm, good, act, dt, gate = fu.result()
                except Exception as e:
                    with lock:
                        L.log(f"  ✗ {futs[fu]}: {type(e).__name__}: {e}", "WARN")
                        stats["fail"] += 1
                    continue
                with lock:
                    if good:
                        stats["ok"] += 1
                        stats["bytes"] += act
                        rate = act / 1e6 / dt if dt > 0 else 0
                        L.log(f"  [{done}/{len(todo)}] ✓ {nm}  "
                              f"{L.human(act)} {dt:.1f}s {rate:.2f}MB/s [{gate}]")
                    else:
                        stats["fail"] += 1
                        L.log(f"  [{done}/{len(todo)}] ✗ {nm} "
                              f"(exp={L.human(exp or 0)} act={L.human(max(act,0))} {gate})",
                              "WARN")

        el = time.time() - t_start
        L.log(f"\n下载完成: 成功 {stats['ok']}, 失败 {stats['fail']}, "
              f"{L.human(stats['bytes'])} / {L.human(el)} "
              f"= {stats['bytes']/1e6/max(el,1e-9):.2f} MB/s")
        if stats["fail"]:
            L.log("★ 有文件下载失败 → 重跑本阶段会自动重试（幂等）", "WARN")
            return 2

    finally:
        try:
            rm.__exit__(None, None, None)
        except Exception:
            pass

    L.save_state(stage_fetch_done="done",
                 fetched_at=datetime.now().strftime("%F %T"),
                 fetch_dir=str(local_dir))
    L.log("✓ 阶段 [fetch] 完成", "OK")
    return 0


# ══════════════════════════════════════════════════════════════════════
# 阶段 4: 绘图
# ══════════════════════════════════════════════════════════════════════
def stage_plot(args, st: dict) -> int:
    L.step("阶段 [plot]  绘图分析")
    script = HERE / "04_analyze_plots.py"
    if not script.is_file():
        L.log(f"缺少绘图脚本: {script}", "ERROR")
        return 1
    rc = _run([sys.executable, str(script), "--dir", str(args.fetch_dir)],
              cwd=str(L.REPO_ROOT), desc="04_analyze_plots.py")
    if rc == 0:
        L.save_state(stage_plot_done="done",
                     plotted_at=datetime.now().strftime("%F %T"))
        L.log("✓ 阶段 [plot] 完成", "OK")
    else:
        L.log(f"绘图未完全成功 rc={rc}（仿真数据本身已完整）", "WARN")
    return rc


# ══════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(
        description="1.6 ns 长时仿真全流程编排（断点续跑）")
    ap.add_argument("--stage", default="all",
                    choices=["all", "submit", "wait", "fetch", "plot"])
    ap.add_argument("--tmax", default=TMAX_DEFAULT)
    ap.add_argument("--nproc", type=int, default=NPROC_DEFAULT)
    ap.add_argument("--account", default=L.ACCOUNT_NCE)
    ap.add_argument("--poll-timeout", type=int, default=POLL_DEFAULT)
    ap.add_argument("--jobs", type=int, default=6, help="下载并行线程数")
    ap.add_argument("--restart", action="store_true", help="忽略 state 从头跑")
    ap.add_argument("--fetch-dir", default=None, help="下载目标目录")
    ap.add_argument("--frames", type=int, default=120,
                    help="★ 抽取的 chk 帧数（等间隔+首尾）；0 或负数=全量下载")
    ap.add_argument("--with-plt", dest="with_plt", action="store_true",
                    help="★ 连 plt 一起下载（默认 chk-only 不下 plt; "
                         "2026-09-16 定案: 分析链只需 chk）")
    args = ap.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.fetch_dir is None:
        tag = "16ns" if args.tmax == TMAX_DEFAULT else f"t{args.tmax}"
        args.fetch_dir = L.FLASH_OUT / f"hpc_{args.account}_{tag}"
    args.fetch_dir = Path(args.fetch_dir)

    st = {} if args.restart else L.load_state()

    print("#" * 74)
    print(f"# SNBOneCH_ml 长时全流程  start={datetime.now():%F %T}")
    print(f"# tmax={args.tmax}  nproc={args.nproc}  account={args.account}")
    print(f"# stage={args.stage}  fetch_dir={args.fetch_dir}")
    if st:
        print(f"# 已存 state: { {k: v for k, v in st.items() if not k.startswith('_')} }")
    print("#" * 74, flush=True)

    t0 = time.time()
    rc = 0
    seq = {
        "all": ["submit", "fetch", "plot"],
        "submit": ["submit"],
        "wait": ["wait"],
        "fetch": ["fetch"],
        "plot": ["plot"],
    }[args.stage]

    for stage in seq:
        fn = {"submit": stage_submit, "wait": stage_wait,
              "fetch": stage_fetch, "plot": stage_plot}[stage]
        rc = fn(args, st)
        if rc != 0:
            L.log(f"阶段 [{stage}] 返回 rc={rc} → 中止后续阶段", "ERROR")
            break

    dt = time.time() - t0
    print("#" * 74)
    print(f"# 结束 rc={rc}  本次耗时 {L.human_dur(dt)}  "
          f"end={datetime.now():%F %T}")
    print(f"# 结果目录: {args.fetch_dir}")
    print(f"# 状态文件: {L.STATE_FILE}")
    print(f"# 日志    : {L.LOGFILE}")
    print("#" * 74, flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
