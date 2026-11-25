"""下载 SandwichTxN 二维四场景的 HPC 短跑产物（chk/plt/log）。

使用 RemoteSession 的动态 SSH 路由，不依赖旧 demo 脚本的硬编码 host/port。
--dry-run 只列出远端文件与大小；正式下载用 .part 临时文件 + 字节数校验。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from flash.flash_run.remote.session import RemoteSession

REMOTE_BASE = (
    "/publicfs01/fs1-e/home/scfa2696/PhySimX/PhySimX/simulation/flash/"
    "flash_sim/flash_output"
)
SCENES = {
    "SandwichTxN_cartesian2d": "950001",
    "SandwichTxN_cartesian2d_one": "950002",
    "SandwichTxN_cylindrical2d": "950003",
    "SandwichTxN_cylindrical2d_one": "950004",
}
KEEP = re.compile(r"(lasslab_hdf5_chk_\d+|lasslab.*\.log)$")
KEEP_CHK = re.compile(r"lasslab_hdf5_chk_\d+$")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--chk-only", action="store_true", help="只下载所有原始 chk 到报告子目录")
    ap.add_argument("--scene", choices=list(SCENES), help="只下载指定场景（便于四进程并行）")
    ap.add_argument("--out-root", default=str(
        REPO / "flash" / "scenarios" / "private" / "Sandwich" / "TxN" / "hpc_results"))
    args = ap.parse_args(argv)
    out_root = Path(args.out_root)
    keep = KEEP_CHK if args.chk_only else KEEP
    scenes = {args.scene: SCENES[args.scene]} if args.scene else SCENES

    with RemoteSession(verbose=False) as s:
        for scene, rid in scenes.items():
            remote_dir = f"{REMOTE_BASE}/{scene}/{rid}"
            out_dir = out_root / scene / rid
            out_dir.mkdir(parents=True, exist_ok=True)
            out, _, _ = s.run(f"ls -1 {remote_dir}", timeout=60)
            names = [n.strip() for n in (out or "").splitlines() if keep.search(n.strip())]
            print(f"[{scene}] {remote_dir} -> {out_dir}")
            if not names:
                print("  [WARN] 未找到匹配产物")
                continue
            for name in names:
                remote = f"{remote_dir}/{name}"
                size_out, _, _ = s.run(f"stat -c %s {remote}", timeout=30)
                size = int((size_out or "0").strip().splitlines()[-1])
                local = out_dir / name
                print(f"  {name}: {size / 1e6:.1f} MB")
                if args.dry_run:
                    continue
                if local.is_file() and local.stat().st_size == size:
                    print("    已存在且大小一致，跳过")
                    continue
                part = local.with_name(local.name + ".part")
                if not s.download(remote, str(part)):
                    print(f"  [FAIL] 下载失败: {name}", file=sys.stderr)
                    return 1
                if part.stat().st_size != size:
                    print(f"  [FAIL] 字节数不符: {name}", file=sys.stderr)
                    return 1
                part.replace(local)
                print("    校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
