"""VTi_oldstyle 输出下载器。

只拉**分析需要的**部分：全部 plt 帧（单帧 ~0.4 MB）+ 首个/末个 chk + flash_run.log。
chk 全量 3.1 GB 对本轮"新旧一致性核验"无用（plt 已含全部时间切片）。

用法:
    python tracer/VTi_oldstyle/fetch_vti_oldstyle.py                    # 默认 2um, tag=L500
    python tracer/VTi_oldstyle/fetch_vti_oldstyle.py --depth 2 --tag L500
    python tracer/VTi_oldstyle/fetch_vti_oldstyle.py --scene VTi2old     # 直接指定场景名
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRACER = HERE.parent


def _add_repo_root() -> None:
    root = HERE
    while root != root.parent and not (root / "pyproject.toml").exists():
        root = root.parent
    sys.path.insert(0, str(root))


_add_repo_root()
from flash.scenarios.core.runner import Remote  # noqa: E402

_local = threading.local()


def conn() -> Remote:
    r = getattr(_local, "r", None)
    if r is None:
        r = Remote("flash_ssh")
        r.__enter__()
        _local.r = r
    return r


def listdir(remote_dir: str) -> list[str]:
    r = conn()
    out, _, _ = r.run(f"ls -1 {remote_dir} 2>/dev/null", timeout=60)
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def sizemap(remote_dir: str) -> dict[str, int]:
    r = conn()
    out, _, _ = r.run(f"ls -l {remote_dir} 2>/dev/null | awk '{{print $5, $9}}'", timeout=120)
    m: dict[str, int] = {}
    for ln in out.splitlines():
        p = ln.split()
        if len(p) == 2 and p[0].isdigit():
            m[p[1]] = int(p[0])
    return m


def want(name: str, last_chk: int) -> bool:
    """取全部 plt + 首个/末个 chk + 运行日志。

    ⚠ chk 索引上限必须用**最大 chk 编号**，不能用 plt 数量（两者节奏不同：
      chk 每 50 步、plt 每 500 步，2.5 ns 时 chk≈2200 / plt≈220）。
    """
    if name == "flash_run.log" or "plt_cnt" in name:
        return True
    m = re.search(r"chk_(\d+)", name)
    if m:
        return int(m.group(1)) in (0, last_chk)
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", default="2", help="1/2/3 (µm)")
    ap.add_argument("--tag", default="L500", help="场景名后缀 (L500 = xmin -500um / tmax 2.5ns)")
    ap.add_argument("--scene", default=None, help="直接指定场景名, 覆盖 --depth/--tag")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    scene = args.scene or f"VTi{args.depth.strip()}{args.tag}"
    state = HERE / "flash_output" / f"hpc_task_{scene}.json"
    if not state.exists():
        print(f"[X] 缺状态文件 {state}")
        return 2
    st = json.loads(state.read_text(encoding="utf-8"))
    upload = st["remote_dir"]
    r = conn()
    up = r._res(upload)
    out, _, _ = r.run(f"ls -d {up}/outputfiles_* 2>/dev/null | tail -1", timeout=60)
    src = out.strip().splitlines()[-1].strip() if out.strip() else r._res(
        f"$HOME/QC/FLASH/FLASH4.8/QC/LaserSlab_{scene}")
    print(f"[i] {scene} 远端源: {src}")

    names = listdir(src)
    sizes = sizemap(src)
    n_plt = sum(1 for n in names if "plt_cnt" in n)
    chk_idx = [int(m.group(1)) for n in names if (m := re.search(r"chk_(\d+)", n))]
    last_chk = max(chk_idx) if chk_idx else -1
    todo_names = [n for n in names if want(n, last_chk) and n in sizes]
    print(f"[i] 远端 {len(names)} 项, 取 {len(todo_names)} 项 "
          f"(plt={n_plt}, chk 0..{last_chk})")

    dest_root = HERE / "flash_output" / scene
    dest_root.mkdir(parents=True, exist_ok=True)

    def fetch(name: str) -> tuple[str, str]:
        dst = dest_root / name
        sz = sizes[name]
        if dst.exists() and dst.stat().st_size == sz:
            return "skip", name
        tmp = dst.with_suffix(dst.suffix + ".part")
        try:
            conn().sftp.get(posixpath.join(src, name), str(tmp))
            if tmp.stat().st_size != sz:
                tmp.unlink(missing_ok=True)
                return "fail", name
            tmp.replace(dst)
            return "ok", name
        except Exception as exc:                       # noqa: BLE001
            tmp.unlink(missing_ok=True)
            return f"fail:{type(exc).__name__}", name

    stat: dict[str, int] = {}
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(fetch, n): n for n in todo_names}
        for f in as_completed(futs):
            k, name = f.result()
            stat[k] = stat.get(k, 0) + 1
            done += 1
            if done % 40 == 0 or done == len(futs):
                print(f"  [{done}/{len(futs)}] {stat}", flush=True)

    total = sum(p.stat().st_size for p in dest_root.iterdir() if p.is_file())
    print(f"[OK] {stat}; 本地 {total/1e6:.0f} MB → {dest_root}")
    return 0 if not any(k.startswith("fail") for k in stat) else 1


if __name__ == "__main__":
    raise SystemExit(main())
