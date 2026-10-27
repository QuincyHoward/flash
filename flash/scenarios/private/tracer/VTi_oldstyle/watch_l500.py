"""L500 系列（xmin=-500µm / tmax=2.5ns）作业守护：轮询 → 首帧网格自检 → 自动下载。

流程
----
1. `sacct` 轮询三个作业，全部离开 RUNNING/PENDING/COMPLETING 后进入下一步
   （任一作业进入 FAILED/CANCELLED/TIMEOUT 也立即进入，以便取回日志定位）。
2. 首个 `chk_0000` 一出现就下载并**核对网格**：xmin/xmax/dx 必须等于设计值
   （xmin=-500 µm, xmax=+150 µm, dx_min=0.019836 µm）。这一步在开工 15–20 分钟
   内就能发现"par 改对了但没生效"这类问题，不用等 2 小时。
3. 全部结束后：
   a. `fetch_hpc_inputs.py` —— 回取超算上**实际提交**的输入（本地 flash_input 会被
      后续生成覆写，不能当正本）；
   b. `fetch_vti_oldstyle.py --tag L500` —— 取 plt 全帧 + 首末 chk + 日志；
   c. `compare_old_new_series.py --new ...` —— 与 VTi_old 在公共时间窗内对照。

用法:
    python watch_l500.py                 # 默认 4 分钟轮询, 最长 6 小时
    python watch_l500.py --interval 180 --max-hours 7
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAG = "L500"
DEPTHS = (1, 2, 3)
EXPECT = {"xmin_um": -500.0, "xmax_um": 150.0, "dx_min_um": 0.019836}

_root = HERE
while _root != _root.parent and not (_root / "pyproject.toml").exists():
    _root = _root.parent
sys.path.insert(0, str(_root))
from flash.scenarios.core.runner import Remote  # noqa: E402

PY = str(_root / ".venv" / "Scripts" / "python.exe")
BUSY = {"RUNNING", "PENDING", "COMPLETING", "CONFIGURING", "REQUEUED"}


def scene(depth: int) -> str:
    return f"VTi{depth}{TAG}"


def job_ids() -> dict[str, str]:
    out = {}
    for d in DEPTHS:
        p = HERE / "flash_output" / f"hpc_task_{scene(d)}.json"
        if p.exists():
            st = json.loads(p.read_text(encoding="utf-8"))
            if st.get("job_id"):
                out[scene(d)] = str(st["job_id"])
    return out


def states(ids: list[str]) -> dict[str, str]:
    with Remote("flash_ssh") as r:
        o, _, _ = r.run(
            f"sacct -j {','.join(ids)} --format=JobID%12,State --noheader --parsable2 "
            f"| grep -v '\\.'", timeout=90)
    st: dict[str, str] = {}
    for ln in o.strip().splitlines():
        p = ln.split("|")
        if len(p) >= 2:
            st[p[0].strip()] = p[1].strip()
    return st


def check_first_frame(scene_name: str) -> bool | None:
    """下载 chk_0000 并核对网格。返回 True=通过 / False=不符 / None=还没有。"""
    import h5py
    import numpy as np

    with Remote("flash_ssh") as r:
        home = r.run("echo $HOME", timeout=60)[0].strip().splitlines()[-1]
        obj = f"{home}/QC/FLASH/FLASH4.8/QC/LaserSlab_{scene_name}"
        o, _, _ = r.run(f"ls -1 {obj}/lasslab_hdf5_chk_0000 2>/dev/null", timeout=60)
        if "chk_0000" not in o:
            return None
        dst = HERE / "flash_output" / scene_name / "lasslab_hdf5_chk_0000"
        dst.parent.mkdir(parents=True, exist_ok=True)
        r.sftp.get(f"{obj}/lasslab_hdf5_chk_0000", str(dst))

    with h5py.File(dst, "r") as h:
        bb = np.asarray(h["bounding box"][:], float)
        n = h["dens"].shape[-1]
    dx = (bb[:, 0, 1] - bb[:, 0, 0]) / n
    xmin, xmax = float(bb[:, 0, 0].min()) * 1e4, float(bb[:, 0, 1].max()) * 1e4
    # 每个块 dx 不同（AMR），最细层的 dx 才是 dx_min
    dx_min = float(dx.min()) * 1e4
    ok = (abs(xmin - EXPECT["xmin_um"]) < 0.5 and abs(xmax - EXPECT["xmax_um"]) < 0.5
          and abs(dx_min / EXPECT["dx_min_um"] - 1) < 2e-3)
    print(f"  [grid] {scene_name}: xmin={xmin:.3f} xmax={xmax:.3f} um "
          f"dx_min={dx_min:.6f} um  blocks={bb.shape[0]}  -> {'OK' if ok else 'MISMATCH'}",
          flush=True)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=240)
    ap.add_argument("--max-hours", type=float, default=6.0)
    ap.add_argument("--skip-wait", action="store_true", help="跳过轮询, 直接下载")
    args = ap.parse_args()

    jobs = job_ids()
    if not jobs:
        print("[X] 找不到 hpc_task_VTi*L500.json")
        return 2
    print(f"[i] 监控 {len(jobs)} 个作业: {jobs}", flush=True)

    checked: set[str] = set()
    deadline = time.time() + args.max_hours * 3600

    if not args.skip_wait:
        while time.time() < deadline:
            try:
                st = states(list(jobs.values()))
            except Exception as exc:                       # noqa: BLE001
                print(time.strftime("%H:%M:%S"), "poll err", type(exc).__name__, flush=True)
                time.sleep(args.interval)
                continue
            print(time.strftime("%H:%M:%S"), st, flush=True)

            # 首个检查点一出现就做网格自检（只做一次/场景）
            for name in jobs:
                if name in checked:
                    continue
                try:
                    verdict = check_first_frame(name)
                except Exception as exc:                   # noqa: BLE001
                    print(f"  [grid] {name}: 检查失败 {type(exc).__name__}: {exc}", flush=True)
                    verdict = None
                if verdict is not None:
                    checked.add(name)
                    if not verdict:
                        print(f"  [!] {name} 网格不符合设计值，请人工确认", flush=True)

            if st and not (set(st.values()) & BUSY):
                print("ALL_DONE", st, flush=True)
                break
            time.sleep(args.interval)
        else:
            print("[!] 超时未结束，仍尝试下载已有产物", flush=True)

    print("\n=== 1/3 回取超算实际提交的输入 ===", flush=True)
    subprocess.run([PY, str(HERE.parent / "fetch_hpc_inputs.py"), "--workers", "4"])

    print("\n=== 2/3 下载输出 (plt 全帧 + 首末 chk + 日志) ===", flush=True)
    for d in DEPTHS:
        subprocess.run([PY, str(HERE / "fetch_vti_oldstyle.py"),
                        "--depth", str(d), "--tag", TAG, "--workers", "8"])

    print("\n=== 3/3 与 VTi_old 对照（公共时间窗内）===", flush=True)
    for d in DEPTHS:
        subprocess.run([PY, str(HERE / "compare_old_new_series.py"),
                        "--depth", str(d), "--new", str(HERE / "flash_output" / scene(d))],
                       check=False)

    print("PIPELINE_DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
