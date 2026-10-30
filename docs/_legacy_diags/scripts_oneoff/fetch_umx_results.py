# -*- coding: utf-8 -*-
"""fetch_umx_results.py — 并行下载 SNBVTi{1,2,3}umx run 000003 产物到本地.

每场景取: 全部 *_hdf5_plt_cnt_* (绘图分析用) + 末帧 chk + LaserEnergyProfile.dat
+ 作业日志。远端先 tar 打包成单文件, 再并行 scp 拉回本地 flash_output/000003/。
"""
from __future__ import annotations

import sys
import tarfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash")
sys.path.insert(0, str(REPO))

SCENES = [
    ("SNBVTi1umx", "4926893"),
    ("SNBVTi2umx", "4926894"),
    ("SNBVTi3umx", "4926895"),
]
BASE = ("/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash"
        "/flash_sim")


def fetch(scene: str, job: str) -> str:
    from flash.flash_run.remote.session import RemoteSession
    from flash.flash_run.env.devices import credential_name

    run_dir = f"{BASE}/scratch_run_{job}"
    log_path = f"{BASE}/flash_logs/{scene}/000003/flash_{scene}_{job}.out"
    tar_remote = f"{BASE}/flash_output/{scene}/000003/_fetch_{scene}.tar"
    # 末帧 chk 名在远端解析 (数字最大的 chk)
    with RemoteSession(credential_name(), verbose=False) as s:
        o, _, _ = s.run(
            f'cd {run_dir} && LAST=$(ls -1 {scene.lower()}ug_hdf5_chk_* 2>/dev/null '
            f'| sort -V | tail -1) && echo LAST=$LAST && tar cf {tar_remote} '
            f'{scene.lower()}ug_*plt_cnt_* {scene.lower()}ug_LaserEnergyProfile.dat '
            f'"$LAST" 2>&1 | tail -1; ls -la {tar_remote}', timeout=600)
        print(f"[{scene}] 打包完成:\n{o.strip()}", flush=True)
        local_dir = REPO / "flash" / "scenarios" / "private" / "tracer" / "SNB" \
            / scene / "flash_output" / "000003"
        local_dir.mkdir(parents=True, exist_ok=True)
        tar_local = local_dir / f"_fetch_{scene}.tar"
        ok = s.download(tar_remote, str(tar_local))
        if not ok:
            return f"[{scene}] [X] 下载失败"
        s.run(f"rm -f {tar_remote}", timeout=60)
        log_ok = s.download(log_path, str(local_dir / f"job_{job}.out"))
        print(f"[{scene}] 日志下载: {'OK' if log_ok else 'FAIL'}", flush=True)
    with tarfile.open(tar_local) as tf:
        tf.extractall(local_dir)  # noqa: S202 (自产自 unpack)
    tar_local.unlink()
    return f"[{scene}] [OK] → {local_dir}"


def main() -> int:
    with ThreadPoolExecutor(max_workers=3) as ex:
        for res in ex.map(lambda a: fetch(*a), SCENES):
            print(res, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
