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

★★★ 下载速率实测经验（2026-09-16 固化, 勿删）
====================================================
| 批次                        | 聚合吞吐   | 说明 |
|-----------------------------|-----------|------|
| 120 chk (~1.6 GB) 首次下载  | ~0.9 MB/s | 晚间时段, 线路拥堵 |
| 增量补 chk (6 线程)         | ~6.57 MB/s | 白天时段, 同一线路 |
结论:
  1. **瓶颈 = 本地↔超算网络路径质量**, 随时段波动可达 ~7×; 与线程数关系
     不大（6 线程已基本饱和路径）, 与代码无关 → 慢时重跑 --stage fetch
     即可（幂等, 已下且 md5 一致的文件自动跳过）。
  2. **大文件占优**: chk ~13.7 MB/个 vs plt ~2.7 MB/个 → 大文件摊薄
     SFTP 握手/建连开销, 有效吞吐更高。
  3. **分析链只需要 chk**: 04_analyze_plots.py 的剖面/标量/x-t/dt 演化图
     全部读 chk; plt 仅特殊诊断才用 → **默认只下载 chk**（2026-09-16
     用户定案）, 需要时显式 `--with-plt`。

流程阶段（可单独指定）:
  [submit]  生成 / 上传 / setup+make / sbatch 提交
  [wait]    轮询作业直到 RUN_DONE（或超时）
  [fetch]   多线程下载 chk(+log/dat) 到 flash_output/hpc_<acct>_16ns/
  [plot]    调用 04_analyze_plots.py 绘图
  [all]     以上全部（默认）

用法:
  python 03_run_16ns_pipeline.py                       # 全流程（默认 tmax=1.6e-9）
  python 03_run_16ns_pipeline.py --stage fetch         # 只下载（默认 chk-only）
  python 03_run_16ns_pipeline.py --stage fetch --frames 400 --jobs 8
                                                       # 更多 chk 帧、8 线程
  python 03_run_16ns_pipeline.py --stage fetch --with-plt
                                                       # 连 plt 一起下（默认不下）
  python 03_run_16ns_pipeline.py --stage submit        # 只提交
  python 03_run_16ns_pipeline.py --stage wait          # 只等待（可反复调用续看）
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
# ★ nproc 默认值从场景模块自动派生 (2026-09-15 改进):
#   原硬编码 131 是 SNBVTi2_ml 专属实测值; 派生场景 (如 SNBVTi2 精确网格
#   iprocs=125/nxb=200) 复制本脚本后若忘改, stage_submit 会显式传 --nproc 131
#   覆盖场景配置 ⇒ 网格/核数静默错配。改为读场景 config_constants["nprocs"]。
NPROC_DEFAULT = int(getattr(getattr(L, "M", None), "config_constants", {}).get(
    "nprocs", 131) or 131)
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


# ── 作业名（与 SNBOneCH_ml.py 的 sbatch 模板一致: SNB1CH_r_<tag>）──────────
_JOB_TAG = {"flash_ssh": "nce", "flash_ssh_2": "bscc"}


def _run_job_name(account: str) -> str:
    """本场景 run 作业名（SNBOneCH_ml.py:1376 `#SBATCH --job-name=SNB1CH_r_{tag}`）。"""
    return f"SNB1CH_r_{_JOB_TAG.get(account, 'nce')}"


def _squeue_jobs(rm, timeout: int = 90):
    """返回 [(jobid, name, state, time, nodes), ...]；空列表 = 队列中无作业。"""
    out, _, _ = rm.run("squeue -u $USER -h -o '%i|%j|%T|%M|%N' 2>/dev/null", timeout=timeout)
    jobs = []
    for ln in (out or "").splitlines():
        if "|" in ln:
            f = [x.strip() for x in ln.split("|")]
            if len(f) >= 5 and f[0]:
                jobs.append(tuple(f[:5]))
    return jobs


# ══════════════════════════════════════════════════════════════════════
# 阶段 1: 提交
# ══════════════════════════════════════════════════════════════════════
def stage_submit(args, st: dict) -> int:
    L.step(f"阶段 [submit]  正式仿真 tmax={args.tmax}  nproc={args.nproc}")

    # ★★★ 重复提交护栏 (2026-09-13 事故后新增)
    # 事故: 上一轮 --stage submit 的**父进程**因网络中断死亡, 但远端 SLURM 作业
    #   仍在跑; 重新 submit 又提交了第二个作业 ⇒ 两个作业共用同一 objdir / 日志 /
    #   chk 编号, 互相覆盖 (实测 chk_0751 mtime 属 A, chk_0750 属 B;
    #   snbvti.log 含 599,131 行 step ≈ 2 × 299,613)。
    #   侥幸: 两者输入与 131 任务分解完全相同 ⇒ 逐位一致, 数据未坏;
    #   但白烧 131 核 × 14.2 h 机时。
    # 护栏: 提交前查队列, 若已有同名 run 作业 → 中止 (除非 --allow-duplicate)。
    if not getattr(args, "allow_duplicate", False):
        jobname = _run_job_name(args.account)
        try:
            rm = L.R._HpcRemote(args.account)
            rm.__enter__()
            try:
                jobs = _squeue_jobs(rm)
            finally:
                try:
                    rm.__exit__(None, None, None)
                except Exception:
                    pass
            same = [j for j in jobs if j[1] == jobname]
            if same:
                L.log(f"★ 检测到 {len(same)} 个同名作业已在队列中 → 拒绝重复提交", "ERROR")
                for j in same:
                    L.log(f"    JobID={j[0]:<10s} {j[1]:<14s} {j[2]:<10s} {j[3]:<10s} {j[4]}")
                L.log("  重复作业会共用同一 objdir/日志/chk 编号并互相覆盖, 严禁并存。", "ERROR")
                L.log("  处理: ① 等它跑完 (--stage wait / _track.py);", "ERROR")
                L.log("        ② 或先 `scancel <JobID>` 再重提;", "ERROR")
                L.log("        ③ 确需并存请显式加 --allow-duplicate。", "ERROR")
                others = [j for j in jobs if j[1] != jobname]
                if others:
                    L.log(f"  (队列中另有 {len(others)} 个其它作业, 不参与本次判定)")
                return 2
            L.log(f"  队列检查: 本账号作业 {len(jobs)} 个, 无同名 {jobname} → 允许提交")
        except Exception as e:
            L.log(f"  重复提交护栏查询失败: {type(e).__name__}: {e} → 保守放行", "WARN")
    else:
        L.log("  --allow-duplicate → 跳过重复提交护栏", "WARN")

    # 远端旧产物清理（防混帧）—— 只清 glob，不动 objdir
    # ★★★ 构建指纹校验 (2026-09-13 事故后新增)
    # 事故: 4 物种精简后仍复用 8 物种 flash4 → RUN_EXIT=0 但 chk 里
    #   仍带 tar1/tar3/tar4/tar6 (静默错误)。
    # 根因: NSPECIES 是编译期常量, flash4 是上一轮产物; 只查"flash4
    #   是否存在"不足以判定二进制与当前输入一致。
    # 护栏: 比对 objdir/_BUILD_STAMP.json 与本地输入指纹, 不一致则强制全量构建。
    L.log("清理远端 objdir 旧产物（防新旧 chk 编号相撞）...")
    try:
        rm = L.R._HpcRemote(args.account)
        rm.__enter__()
        try:
            snb_home = L.abs_snb_home(rm)
            obj = f"{snb_home}/{L.M.OBJDIR}"
            n = L.remote_batch_remove(
                rm, [f"{L.M.BASENM}*", "wsl_run_*.log", "_t_start", "_t_end"],
                dry_run=False, rdir=obj, label="提交前清理")
            L.log(f"  已清 {n} 项旧产物")
            # ★ 指纹判定（取代原先"只查 flash4 是否存在"）
            if args.force_build:
                skip_build = False
                L.log("  --force-build → 强制全量构建", "WARN")
            else:
                need, reason = L.needs_rebuild(rm, obj)
                skip_build = not need
                if need:
                    L.log(f"  ★ 需全量构建: {reason}", "WARN")
                else:
                    L.log(f"  {reason} → 使用 --skip-build 省编译")
        finally:
            try:
                rm.__exit__(None, None, None)
            except Exception:
                pass
    except Exception as e:
        L.log(f"远端清理失败（继续尝试提交）: {type(e).__name__}: {e}", "WARN")
        # ★ 网络失败时**不再默认 --skip-build**（旧行为会静默复用错二进制）
        #   改为走全量构建 —— 构建耗时但正确性优先。
        skip_build = False
        L.log("  ★ 网络异常 → 保守走全量构建（避免误用旧二进制）", "WARN")

    # ★★ 参数契约 (2026-09-13 实测修正):
    #   SNBVTi.py 与参考 SNBOneCH_ml.py 的 CLI **不同** —— 参考模块用
    #   `--mode hpc` 选择运行模式, 而 SNBVTi.py 的 action 是**位置参数**
    #   且 main() 无条件走 HPC 委托 (位置 action 只作文档说明)。
    #   ⇒ 绝不能照搬 `--mode hpc` (会 rc=2 unrecognized arguments)。
    #   还须显式传 `--poll-timeout`: SNBVTi 默认仅 7200 s, 而 1.6 ns
    #   实跑 ≈ 9 h, 不调大会在轮询超时处被误判失败。
    cmd = [
        sys.executable, str(L.SCEN_DIR / f"{L.SCEN_MODULE}.py"),
        "--account", args.account,
        "--nproc", str(args.nproc), "--tmax", str(args.tmax),
        "--poll-timeout", str(args.poll_timeout),
    ]
    if skip_build:
        cmd.append("--skip-build")

    rc = _run_with_net_retry(cmd, cwd=str(L.REPO_ROOT),
                             desc="SNBVTi.py HPC 委托")
    if rc != 0:
        L.log("提交/运行失败。检查上方 ERROR 与远端 run_*_out.txt", "ERROR")
        return rc

    # ★ 仿真成功后写构建戳：证明当前 objdir 的 flash4 与本次输入一致
    if not skip_build:
        try:
            rm = L.R._HpcRemote(args.account)
            rm.__enter__()
            try:
                snb_home = L.abs_snb_home(rm)
                obj = f"{snb_home}/{L.M.OBJDIR}"
                fp = L.compute_build_fingerprint()
                ok = L.write_remote_fingerprint(
                    rm, obj, fp, extra={"nproc": args.nproc,
                                        "tmax": str(args.tmax),
                                        "species": ",".join(L.M.SPECIES_LIST)})
                L.log(f"  构建戳写入: {'✓' if ok else '✗'} ({fp[:12]}…)", "OK" if ok else "WARN")
            finally:
                try:
                    rm.__exit__(None, None, None)
                except Exception:
                    pass
        except Exception as e:
            L.log(f"  写构建戳失败（不影响结果）: {type(e).__name__}: {e}", "WARN")

    L.save_state(stage_submit_done="done", tmax=str(args.tmax),
                 nproc=args.nproc, account=args.account,
                 submitted_at=datetime.now().strftime("%F %T"))
    L.log("✓ 阶段 [submit] 完成（仿真已完成并收集到 hpc_<acct>/）", "OK")
    return 0


# ══════════════════════════════════════════════════════════════════════
# 阶段 2: 等待（由 SNBVTi.py 内部轮询完成，此处做状态确认）
# ══════════════════════════════════════════════════════════════════════
def stage_wait(args, st: dict) -> int:
    L.step("阶段 [wait]  确认作业状态")
    L.log("说明: 作业轮询由 SNBVTi.py 内部完成（--poll-timeout）。")
    L.log("      本阶段检查远端作业是否仍在跑，并打印进度。")

    try:
        rm = L.R._HpcRemote(args.account)
        rm.__enter__()
        try:
            snb_home = L.abs_snb_home(rm)
            obj = f"{snb_home}/{L.M.OBJDIR}"
            out, _, _ = rm.run(
                f"squeue -u $USER -h -o '%i|%j|%T|%M|%N' 2>/dev/null; echo ---; "
                f"cd {obj} && ls {L.M.BASENM}* 2>/dev/null | wc -l; echo ---; "
                f"tail -3 wsl_run_*.log 2>/dev/null",
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
        rm = L.R._HpcRemote(args.account)
        rm.__enter__()
    except Exception as e:
        L.log(f"连接超算失败: {type(e).__name__}: {e}", "ERROR")
        return 1

    try:
        snb_home = L.abs_snb_home(rm)
        obj = f"{snb_home}/{L.M.OBJDIR}"
        L.log(f"远端源: {obj}")

        # ── 远端清单（chk 恒取; plt 默认丢弃, --with-plt 才取; log/dat 恒取）──
        # ★ 修 (2026-09-16): 旧代码 `n == "wsl_run_*.log"` 是字面量比较, 永不
        #   匹配 → 运行日志 (L.M.LOG_FILE, 如 snbvti2.log) 漏下, 04 脚本
        #   dt_evolution 图被跳过。改为显式匹配 LOG_FILE + wsl_run_ 前缀。
        # ★★ chk-only 默认策略 (2026-09-16 用户定案): 分类/抽帧/选择逻辑已
        #   收敛到 flash/flash_run/remote/fetch_policy.py（全场景唯一来源）,
        #   本处只调用; 独立脚本用 importlib 按路径加载, 避免 import flash 副作用。
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
            log_names=[getattr(L.M, "LOG_FILE", "") or ""],
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
        L.log(f"启动 {workers} 线程并行下载（实测聚合 0.9–6.6 MB/s, 随网络时段波动）...")
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
                        # ★ 修: 原写 `exp` —— 它只是 `_one()` 的局部量, 此处未定义,
                        #   失败分支会抛 NameError 并被上面的 except 吞成"✗ name"。
                        _exp = rsize.get(nm)
                        L.log(f"  [{done}/{len(todo)}] ✗ {nm} "
                              f"(exp={L.human(_exp or 0)} act={L.human(max(act,0))} {gate})",
                              "WARN")

        el = time.time() - t_start
        L.log(f"\n下载完成: 成功 {stats['ok']}, 失败 {stats['fail']}, "
              f"{L.human(stats['bytes'])} / {L.human(el)} "
              f"= {stats['bytes']/1e6/max(el,1e-9):.2f} MB/s")
        # ★★ 收敛遍 (2026-09-14 事故后新增)
        # 事故: 一次 SFTP 传输被 socket 10054 打断(留下 327,680 B 半截文件),
        #   且 6 线程**共用同一 paramiko 会话** —— `remote_md5` 与 `download`
        #   并发非线程安全; 某线程一旦卡住 `as_completed` 就**永不返回** ⇒
        #   整阶段静默挂死(实测 >23 min, 本地已 272 文件却只报 271/272)。
        # 本遍**顺序**重下所有尺寸不符者, 不依赖线程池 → 必然可收敛。
        def _sizes():
            return {p.name: p.stat().st_size
                    for p in local_dir.iterdir() if p.is_file()}

        bad = [n for n in want if _sizes().get(n) != rsize.get(n, -1)]
        if bad:
            L.log(f"★ 收敛遍: 顺序重下 {len(bad)} 个尺寸不符/缺失文件...", "WARN")
            for n in bad:
                lp = local_dir / n
                rp = f"{obj}/{n}"
                try:
                    if lp.exists():
                        lp.unlink()
                    ok = rm.download(rp, str(lp))
                    act = lp.stat().st_size if lp.exists() else -1
                    good = bool(ok) and act == rsize.get(n, -1)
                    gate = "size"
                    if good:
                        rmd5 = L.remote_md5(rm, rp)
                        lmd5 = L.local_md5(lp)
                        if rmd5 and lmd5:
                            good = (rmd5 == lmd5)
                            gate = "md5-ok" if good else "md5FAIL"
                    L.log(f"  [converge] {'✓' if good else '✗'} {n} "
                          f"{L.human(max(act, 0))} [{gate}]", "OK" if good else "WARN")
                except Exception as e:
                    L.log(f"  [converge] ✗ {n}: {type(e).__name__}: {e}", "WARN")

        still = [n for n in want if _sizes().get(n) != rsize.get(n, -1)]
        if still:
            L.log(f"★ 仍有 {len(still)} 个文件不完整 → 重跑本阶段会自动重试（幂等）", "WARN")
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
    ap.add_argument("--force-build", action="store_true",
                    help="★ 强制全量构建（无视构建指纹；改了 Config 编译期常量时用）")
    ap.add_argument("--allow-duplicate", action="store_true",
                    help="★ 跳过「同名作业已在队列」护栏（会并发写同一 objdir，默认禁止）")
    args = ap.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.fetch_dir is None:
        tag = "16ns" if args.tmax == TMAX_DEFAULT else f"t{args.tmax}"
        args.fetch_dir = L.FLASH_OUT / f"hpc_{args.account}_{tag}"
    args.fetch_dir = Path(args.fetch_dir)

    st = {} if args.restart else L.load_state()

    print("#" * 74)
    print(f"# SNBVTi 长时全流程  start={datetime.now():%F %T}")
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
