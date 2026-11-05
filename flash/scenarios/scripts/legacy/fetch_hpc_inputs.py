"""
fetch_hpc_inputs — 拉取超算上"实际用于提交"的那一套 FLASH 输入文件
═══════════════════════════════════════════════════════════════════

为什么单独做: 本地 `flash_input/` 会被后续的 `generate_input_files` **反复覆写**
(而且同族多脚本共用同一个 `flash_input/`), 所以它不一定是"当初提交的那一套"。
真正上机的那套在远端 `<work_base>/<SCENE>_<ts>/` 里 —— 那才是可复现的正本。

本脚本按 `flash_output/hpc_task*.json` 里的 `remote_dir` 取回远端**顶层文件**
(自动跳过 `outputfiles_*` 输出目录与 `*.part`), 落到:

    <场景目录>/hpc_inputs/<SCENE>/

并写 `<场景目录>/hpc_inputs/<SCENE>/MANIFEST.txt`, 记录远端路径/时间戳/文件清单,
以及该场景真正使用的 par (从 submit_flash.sh 的 `PAR_FILE=` 解析)。

用法:
  .venv/Scripts/python.exe flash/scenarios/private/tracer/fetch_hpc_inputs.py
  ... --scenes VTi1,VTi2,VTi3
  ... --workers 4
"""

import argparse
import json
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent          # tracer/
SKIP_RE = re.compile(r"^(outputfiles_|\.|.*\.part$)")


def root() -> Path:
    r = HERE
    while r != r.parent and not (r / "pyproject.toml").exists():
        r = r.parent
    return r


_tls = threading.local()


def remote():
    r = getattr(_tls, "r", None)
    if r is None:
        sys.path.insert(0, str(root()))
        from flash.scenarios.core.runner import Remote
        r = Remote("flash_ssh")
        r.connect()
        _tls.r = r
    return r


def load_jobs():
    """{scene: {"remote_dir":..., "scene_dir": Path}} — 递归扫描 tracer/。"""
    jobs = {}
    for p in sorted(HERE.glob("*/flash_output/hpc_task*.json")):
        try:
            st = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        jid = st.get("job_id")
        if not jid:
            continue
        tag = p.stem[len("hpc_task"):].strip("_")
        scene = tag if tag else p.parent.parent.name
        jobs[scene] = {"remote_dir": st.get("remote_dir", ""),
                       "scene_dir": p.parent.parent}
    return jobs


def list_top(r, d):
    """返回 [(name, size)] — 只取顶层普通文件。"""
    out = []
    for a in r.sftp.listdir_attr(d):
        if SKIP_RE.match(a.filename):
            continue
        try:
            import stat
            if stat.S_ISDIR(a.st_mode or 0):
                continue
        except Exception:
            pass
        out.append((a.filename, a.st_size or 0))
    return out


def get_one(task):
    scene, name, size, rpath, dst = task
    if dst.exists() and dst.stat().st_size == size:
        return ("skip", scene, name, size)
    r = remote()
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".part")
    try:
        r.sftp.get(rpath, str(tmp))
        if tmp.stat().st_size == size:
            tmp.replace(dst)
            return ("ok", scene, name, size)
    except Exception as exc:                            # noqa: BLE001
        tmp.unlink(missing_ok=True)
        return (f"fail({type(exc).__name__})", scene, name, size)
    tmp.unlink(missing_ok=True)
    return ("fail(size)", scene, name, size)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", default=None, help="逗号分隔, 默认全部有状态文件的场景")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    jobs = load_jobs()
    if args.scenes:
        want = {s.strip() for s in args.scenes.split(",")}
        jobs = {k: v for k, v in jobs.items() if k in want}
    if not jobs:
        print("[X] 没有匹配的场景状态文件")
        return 1

    remote()                                            # 建连 (主线程)
    tasks, manifests = [], {}
    for scene, info in jobs.items():
        d = info["remote_dir"]
        if not d:
            print(f"[!] {scene}: 无 remote_dir")
            continue
        rd = remote()._res(d)
        files = list_top(remote(), rd)
        dest = info["scene_dir"] / "hpc_inputs" / scene
        # 该场景真正使用的 par
        par = None
        for name, _ in files:
            if name == "submit_flash.sh":
                try:
                    txt = remote().sftp.open(f"{rd}/{name}").read().decode(errors="replace")
                    m = re.search(r'^PAR_FILE="?([^"\n]+)"?', txt, re.M)
                    par = m.group(1) if m else None
                except Exception:
                    pass
        manifests[scene] = (d, dest, files, par)
        for name, size in files:
            tasks.append((scene, name, size, f"{rd}/{name}", dest / name))
        print(f"[i] {scene}: {len(files)} 个文件 / {sum(s for _, s in files)/1e6:.1f} MB → {dest}")

    ok = skip = fail = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for f in as_completed([ex.submit(get_one, t) for t in tasks]):
            st, scene, name, size = f.result()
            if st == "ok":
                ok += 1
            elif st == "skip":
                skip += 1
            else:
                fail += 1
                print(f"  [!] {scene}/{name}: {st}")
    print(f"\n[OK] 下载完成 ok={ok} skip={skip} fail={fail} "
          f"({time.time()-t0:.0f}s)")

    for scene, (rd, dest, files, par) in manifests.items():
        dest.mkdir(parents=True, exist_ok=True)
        lines = [f"# {scene} 超算实际提交输入副本",
                 f"# 远端: {rd}",
                 f"# 取回时间: {datetime.now():%Y-%m-%d %H:%M:%S}",
                 f"# 本场景实际使用的 par (submit_flash.sh PAR_FILE): {par}",
                 f"# 注意: 远端目录内同时存在同族其它场景的 par (上传时 INPUT_DIR 共用), "
                 f"仅上面这一份是本次作业用的",
                 ""]
        for name, size in files:
            lines.append(f"  {size:>10}  {name}")
        (dest / "MANIFEST.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[i] MANIFEST → {dest/'MANIFEST.txt'}  (par={par})")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
