#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flash.flash_run.hpc — 超算技能统一 CLI（2026-10-22 模块化改造）
═══════════════════════════════════════════════════════════

把散落在 FlashRemoteDeploy / slurm_control / route_tester 的超算操作固化为
子命令，**本地驱动**与**超算登录节点 in-situ** 两侧均可调用:

    python -m flash.flash_run.hpc status --job <id>          # squeue 查询
    python -m flash.flash_run.hpc submit  --par x.par --nprocs 131 --account flash_ssh
    python -m flash.flash_run.hpc cancel  --job <id>
    python -m flash.flash_run.hpc download --remote <dir> --local <dir> [--pattern "*.h5"]
    python -m flash.flash_run.hpc route-test                 # 9 路由择优
    python -m flash.flash_run.hpc nodes                      # 分区/节点速览

既有约定保留:
  * 提交前必查 squeue（父进程网络死亡 ≠ 远端作业结束）；
  * SSH 限并发 → 本 CLI 所有远端操作天然串行；
  * 凭据走 flash._core.credentials（credential_name 默认 flash_ssh）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


# ── 子命令实现 ────────────────────────────────────────────

def cmd_status(args: argparse.Namespace) -> int:
    from flash.flash_run.remote.remote_deploy import FlashRemoteDeploy

    with FlashRemoteDeploy(credential_name=args.credential) as d:
        out, err, rc = d.execute(f"squeue --me -o '%.10i %.12j %.8T %.10M %R'")
        print(out or err)
        if args.job:
            out2, _, _ = d.execute(f"sacct -j {args.job} --format=JobID,State,Elapsed,ExitCode -P | head -5")
            print(out2 or "")
    return 0


def cmd_submit(args: argparse.Namespace) -> int:
    from flash.flash_run.remote.remote_deploy import FlashRemoteDeploy

    remote_par = args.par if _is_remote_path(args.par) else None
    with FlashRemoteDeploy(credential_name=args.credential) as d:
        if remote_par is None:
            # 本地 par → 先上传（默认传到远端 HOME 下 flash_run_cli/）
            local = Path(args.par)
            if not local.is_file():
                print(f"[X] 本地 par 不存在: {local}", file=sys.stderr)
                return 2
            remote_dir = "~/flash_run_cli"
            d.execute(f"mkdir -p {remote_dir}")
            d.upload(str(local), f"{remote_dir}/{local.name}")
            remote_par = f"{remote_dir}/{local.name}"
        job_id = d.submit_job(remote_par, nprocs=args.nprocs,
                              wall_time=args.wall_time, job_name=args.job_name)
        print(f"Job submitted: {job_id}")
    return 0


def cmd_cancel(args: argparse.Namespace) -> int:
    from flash.flash_run.remote.remote_deploy import FlashRemoteDeploy

    with FlashRemoteDeploy(credential_name=args.credential) as d:
        out, err, rc = d.execute(f"scancel {args.job}")
        print("[OK] 已提交 scancel" if rc == 0 else f"[X] {err}")
        return 0 if rc == 0 else 1


def cmd_wait(args: argparse.Namespace) -> int:
    from flash.flash_run.remote.remote_deploy import FlashRemoteDeploy

    with FlashRemoteDeploy(credential_name=args.credential) as d:
        state = d.wait_for_job(args.job, timeout=args.timeout)
        print(f"Final state: {state}")
        return 0 if state == "COMPLETED" else 1


def cmd_download(args: argparse.Namespace) -> int:
    from flash.flash_run.remote.remote_deploy import FlashRemoteDeploy

    with FlashRemoteDeploy(credential_name=args.credential) as d:
        d.download_results(args.remote, args.local, pattern=args.pattern)
    print(f"[OK] 已下载 → {args.local}")
    return 0


def cmd_route_test(args: argparse.Namespace) -> int:
    from flash.flash_run.remote.route_tester import main as route_main

    sys.argv = [sys.argv[0]] + args.rest
    return route_main() or 0


def cmd_nodes(args: argparse.Namespace) -> int:
    from flash.flash_run.remote.remote_deploy import FlashRemoteDeploy

    with FlashRemoteDeploy(credential_name=args.credential) as d:
        out, err, _ = d.execute("sinfo -o '%.12P %.6a %.10l %.6D %N' | head -20")
        print(out or err)
    return 0


def _is_remote_path(p: str) -> bool:
    return p.startswith(("~", "/")) or ":" in p and not Path(p).exists()


# ── 参数表 ────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m flash.flash_run.hpc",
        description="超算技能统一 CLI（本地/登录节点两侧可调；远端操作串行）",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("status", help="查询我的作业队列（squeue）+ 可选单作业 sacct")
    p.add_argument("--job")
    p.add_argument("--credential", default="flash_ssh")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("submit", help="提交作业（本地 par 自动上传；远端路径直用）")
    p.add_argument("--par", required=True, help="par 文件（本地路径或远端绝对路径）")
    p.add_argument("--nprocs", type=int, required=True)
    p.add_argument("--wall-time", default="02:00:00")
    p.add_argument("--job-name", default="flash_run")
    p.add_argument("--credential", default="flash_ssh")
    p.set_defaults(fn=cmd_submit)

    p = sub.add_parser("cancel", help="取消作业（scancel）")
    p.add_argument("--job", required=True)
    p.add_argument("--credential", default="flash_ssh")
    p.set_defaults(fn=cmd_cancel)

    p = sub.add_parser("wait", help="等待作业结束（轮询 sacct）")
    p.add_argument("--job", required=True)
    p.add_argument("--timeout", type=int, default=3600)
    p.add_argument("--credential", default="flash_ssh")
    p.set_defaults(fn=cmd_wait)

    p = sub.add_parser("download", help="下载结果文件")
    p.add_argument("--remote", required=True)
    p.add_argument("--local", required=True)
    p.add_argument("--pattern", default="*.h5")
    p.add_argument("--credential", default="flash_ssh")
    p.set_defaults(fn=cmd_download)

    p = sub.add_parser("route-test", help="SSH 多路由延迟测试/择优")
    p.add_argument("rest", nargs="*", help=argparse.SUPPRESS)
    p.set_defaults(fn=cmd_route_test)

    p = sub.add_parser("nodes", help="分区/节点速览（sinfo）")
    p.add_argument("--credential", default="flash_ssh")
    p.set_defaults(fn=cmd_nodes)

    return ap


def main(argv: list | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        print("\n[!] 中断", file=sys.stderr)
        return 130
    except Exception as e:  # noqa: BLE001 — CLI 顶层兜底，给出可定位信息
        print(f"[X] {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
