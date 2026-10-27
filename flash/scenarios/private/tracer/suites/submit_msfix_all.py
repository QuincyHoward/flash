"""
submit_msfix_all — ms_shld 修复后 5 场景一次性并行提交 (NC-E)
═══════════════════════════════════════════════════════════════════

顺序约束: TiTi1/2/3 **共用** `TiTi/flash_input` ⇒ 它们的 upload 必须串行
(否则后一个场景的 generate_input_files 会把前一个的 par 覆盖掉)。
VCH_ml / VCH_ml_F 各有独立目录, 可与 TiTi 链并行。

两阶段:
  阶段 A (并行 3 组): [TiTi1→TiTi2→TiTi3] ‖ [VCH_ml] ‖ [VCH_ml_F]   ← upload
  阶段 B (串行 5 条): 逐场景 sbatch, 间隔仅数秒 ⇒ 5 个作业同时在队/在跑

用法:
  ... submit_msfix_all.py --dry-run     # 只打印计划
  ... submit_msfix_all.py               # 真提交
"""

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
TMAX = 1.6e-9

GROUPS = [
    ("TiTi", [("TiTi1", HERE / "TiTi" / "TiTi1.py"),
              ("TiTi2", HERE / "TiTi" / "TiTi2.py"),
              ("TiTi3", HERE / "TiTi" / "TiTi3.py")]),
    ("VCH_ml", [("VCH_ml", HERE / "VCH_ml" / "VCH_ml.py")]),
    ("VCH_ml_F", [("VCH_ml_F", HERE / "VCH_ml_F" / "VCH_ml_F.py")]),
]


def root() -> Path:
    r = HERE
    while r != r.parent and not (r / "pyproject.toml").exists():
        r = r.parent
    return r


def run(script: Path, action: str, tmax: float):
    cmd = [sys.executable, str(script), action, "--tmax", repr(tmax)]
    p = subprocess.run(cmd, cwd=str(root()), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    jobs = [ln for ln in out.splitlines()
            if "JobID=" in ln or "上传完成" in ln or "[X]" in ln]
    return p.returncode, jobs


def upload_group(items, tmax, dry):
    rc_all = 0
    for name, script in items:
        if dry:
            print(f"  [dry] upload {name}")
            continue
        t0 = time.time()
        rc, lines = run(script, "upload", tmax)
        print(f"  [upload] {name} rc={rc} {time.time()-t0:.0f}s "
              + (lines[-1].strip() if lines else ""), flush=True)
        rc_all |= rc
    return rc_all


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tmax", type=float, default=TMAX)
    args = ap.parse_args()

    print("=" * 70)
    print(f" ms_shld 修复后并行提交 — {sum(len(g[1]) for g in GROUPS)} 个场景")
    print(f" tmax={args.tmax:.2e} s   模式={'dry-run' if args.dry_run else '★ 实际提交'}")
    print(f" {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 70)

    # ── 阶段 A: 三组并行 upload ──
    print("\n[A] upload (TiTi 链串行; VCH_ml / VCH_ml_F 与链并行)")
    with ThreadPoolExecutor(max_workers=len(GROUPS)) as ex:
        futs = [ex.submit(upload_group, g[1], args.tmax, args.dry_run) for g in GROUPS]
        rcs = [f.result() for f in futs]
    if any(rcs):
        print(f"[X] upload 有失败 (rc={rcs}), 停止提交")
        return 1

    # ── 阶段 B: 逐场景 submit ──
    print("\n[B] submit (逐条 sbatch, 数秒内全部入队 ⇒ 并行运行)")
    results = []
    for _, items in GROUPS:
        for name, script in items:
            if args.dry_run:
                print(f"  [dry] submit {name}")
                results.append((name, None, 0))
                continue
            rc, lines = run(script, "submit", args.tmax)
            jid = None
            for ln in lines:
                if "JobID=" in ln:
                    jid = ln.split("JobID=")[-1].strip()
            print(f"  [submit] {name:<9} rc={rc} job={jid}", flush=True)
            results.append((name, jid, rc))

    print("\n=== 汇总 ===")
    ok = True
    for name, jid, rc in results:
        ok = ok and bool(rc == 0 and (jid or args.dry_run))
        print(f"  {name:<9} job={str(jid):<10} rc={rc}")
    (HERE / "msfix_submit_log.json").write_text(
        json.dumps({"ts": datetime.now().isoformat(timespec="seconds"),
                    "tmax": args.tmax,
                    "jobs": {n: j for n, j, _ in results}}, indent=2),
        encoding="utf-8")
    print(f"\n[i] 提交记录: {(HERE / 'msfix_submit_log.json')}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
