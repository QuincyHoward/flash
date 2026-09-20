"""通用 SLURM 作业低频轮询监控: 终态即打印作业输出尾部 (含 WALL_SECONDS)。

用法:
  python monitor_job.py --account flash_ssh --job 4858800 [--interval 1800] [--max-polls 20]

账号: flash_ssh=NC-E (scfa2696), flash_ssh_2=BSCC (sch0348)。
网络抖动自动重试 (不退出); 到 max-polls 仍未终态则打印 STILL_RUNNING。
"""
import argparse
import os
import sys
import time

# 脚本文件方式运行时 sys.path[0]=脚本目录: 需同时插入外层根 (import flash)
# 与 demo_hpc 目录 (import remote_ssh_helper)。双层 flash 结构注意:
# 外层根 = 本脚本上溯 6 级, 内层 flash = 上溯 5 级。
_HERE = os.path.dirname(os.path.abspath(__file__))
# 脚本位于 SNBOneCH_ml/scripts/monitor/: 上溯 7 级 = 内层 flash, 8 级 = 外层根
_INNER = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "..", "..", ".."))
_ROOT = os.path.abspath(os.path.join(_INNER, ".."))
sys.path.insert(0, os.path.join(_INNER, "scenarios", "flash_demo", "demo_hpc"))
sys.path.insert(0, _ROOT)

from remote_ssh_helper import quick_run  # noqa: E402


def resolve_deploy(credential_name: str) -> str:
    """解析远端部署目录绝对路径。

    ★ 不能用 `~/SNBOneCH_ml_deploy`: paramiko SFTP/exec 不展开 `~` (与 scp CLI 不同),
    会把文件写进**名为 `~` 的字面目录**。必须用 `$HOME` 展开后的绝对路径,
    并叠加与场景一致的 SIM_USER_DIR (由 runner.get_sim_user_dir() 提供, 实测 = QC)。
    """
    try:
        out, _, _ = quick_run('printf "%s" "$HOME"', credential_name=credential_name,
                              timeout=60)
        home = (out or "").strip()
    except Exception:
        home = ""
    if home.startswith("/"):
        return f"{home}/QC/SNBOneCH_ml_deploy"
    print(f"[WARN] $HOME 探测失败 (got={home!r}); 回退字面路径, 可能落错目录", flush=True)
    return "~/QC/SNBOneCH_ml_deploy"


DEPLOY = {
    "flash_ssh": "",   # 运行期由 resolve_deploy() 填充 (NC-E: scfa2696)
    "flash_ssh_2": "",  # 运行期由 resolve_deploy() 填充 (BSCC: sch0348)
}


def main() -> int:
    ap = argparse.ArgumentParser(description="通用 SLURM 作业低频监控")
    ap.add_argument("--account", default="flash_ssh",
                    choices=["flash_ssh", "flash_ssh_2"])
    ap.add_argument("--job", required=True, help="SLURM JobID")
    ap.add_argument("--interval", type=int, default=1800, help="轮询间隔秒 (默认 1800)")
    ap.add_argument("--max-polls", type=int, default=20, help="最大轮询次数")
    args = ap.parse_args()

    # ★ 必须现场解析部署目录: DEPLOY 字典的两个值都是空串占位,
    #   直接 DEPLOY.get(...) 会拿到 "" → tail 的路径变成 /run_<job>_out.txt 之类,
    #   永远读不到日志。旧版这里回退字面 "~/..." 更是错的 (paramiko 不展开 ~)。
    deploy = resolve_deploy(args.account)
    print(f"[i] deploy dir = {deploy}", flush=True)
    for i in range(1, args.max_polls + 1):
        try:
            out, _, _ = quick_run(
                f"sacct -j {args.job} --format=State,Elapsed --noheader | head -1; "
                f"tail -c 300 {deploy}/run_{args.job}_out.txt 2>/dev/null",
                credential_name=args.account, timeout=90)
        except Exception as exc:  # 网络抖动不退出
            print(f"[poll {i}/{args.max_polls}] EXC: {exc}", flush=True)
            time.sleep(120)
            continue
        tail = out[-400:]
        print(f"[poll {i}/{args.max_polls}] {tail}", flush=True)
        if any(s in tail for s in ("COMPLETED", "FAILED", "TIMEOUT",
                                   "CANCELLED", "NODE_FAIL")):
            print("MONITOR_DONE", flush=True)
            return 0
        if i < args.max_polls:
            time.sleep(args.interval)
    print("MONITOR_TIMEOUT_STILL_RUNNING", flush=True)
    return 2


if __name__ == "__main__":
    sys.exit(main())
