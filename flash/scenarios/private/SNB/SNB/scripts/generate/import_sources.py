#!/usr/bin/env python3
"""SNB 源文件导入器 —— 把作者 SNB 实现包与参考版归集到 SNB/SNB/source/
═══════════════════════════════════════════════════════════════════════════════

**这个脚本本身不含任何 F90 源码文本** —— 它只做**文件复制 + 校验**，
因此属于"可分享的 py 脚本"（分享规则见 docs/06）。

用途
----
`SNB/SNB/source/` 是 SNB 场景处理的**核心本地模块**（F90 实现包 + 参考版 + 表），
**不入库**（受分享规则与 FLASH License §3 约束）。
新环境重建方式：

    python scripts/generate/import_sources.py --from <旧包目录>

它会：
  1. 按固定清单把 F90 / Config / Makefile / Simulation_* / cn4 复制到 `source/`；
  2. 计算每个文件的 sha256 写入 `manifest.json`；
  3. 校验补丁状态（编译必需的改动是否已打）；
  4. 打印缺失/多余项，便于人工核对。

目录约定
--------
    source/snb_package/   作者 SNB 实现包 (9 个覆盖 F90 + Config + Makefile + Simulation_*)
    source/stock_sh/      限流 Spitzer-Härm 参考版 (对照腿用)
    source/tables/        EOS / opacity 表 (*.cn4)
    source/example/       作者示例 par (仅作参考, 不参与生成)

用法:
    python import_sources.py --from ../../../SNBtest/src/SNB/SNB_1D_laser/SNB_1D_laser
    python import_sources.py --from <dir> --also-stock ../../../SNBtest/src/SNB/f90
    python import_sources.py --verify-only          # 只校验现有 source/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple

_SNB_DIR = Path(__file__).resolve().parents[2]      # .../SNB/SNB
SOURCE = _SNB_DIR / "source"
MANIFEST = _SNB_DIR / "manifest.json"

# ── 固定清单 (顺序即复制顺序) ────────────────────────────────
#   ① 作者 SNB 实现包: 9 个覆盖 F90 (含多群能量权重) + 构建件
SNB_F90 = (
    "diff_advanceTherm.F90",                     # 核心: 电子热传导推进
    "Conductivity.F90",                          # Spitzer-Härm 电导
    "Driver_evolveFlash.F90",                    # 主推进循环
    "Grid_advanceDiffusion.F90",                 # 扩散线性求解接口
    "hy_uhd_DataReconstructNormalDir_PPM.F90",   # 流体重构 (法向 PPM)
    "hy_uhd_dataReconstOneStep.F90",             # 流体重构 (单步)
    "hy_uhd_getRiemannState.F90",                # Riemann 状态
    "hy_uhd_ragelike.F90",                       # RAGE-like 处理
    "mgd_qesh.F90",                              # 多群能量权重 (Makefile 必须列入)
)
SNB_BUILD = ("Config", "Makefile")
SNB_SIM = ("Simulation_data.F90", "Simulation_init.F90", "Simulation_initBlock.F90")
SNB_EXAMPLE = ("flash.par",)

# ② 参考版 (对照腿): 纯限流 SH, 无 SNB 代码块
STOCK_F90 = ("diff_advanceTherm.F90",)

CN4_TABLES = ("He-BADGER-TOPS-Final.cn4", "CH-BADGER-TOPS-Final.cn4")

# ── 编译必需的补丁标记 (只描述**特征串**, 不给出源码) ──────────
#   key = 文件; value = [(特征串, 期望是否存在), ...]
#   特征串为标识符级, 不构成算法实现泄漏。
PATCH_MARKERS: Dict[str, List[Tuple[str, bool]]] = {
    "diff_advanceTherm.F90": [
        ("QENL_VAR,i,j,1) = -(&", True),      # 续行符已补
    ],
    "hy_uhd_DataReconstructNormalDir_PPM.F90": [
        ("use hy_slopeLimiters", True),
        ("use hy_uhd_slopeLimiters", False),
    ],
    "hy_uhd_getRiemannState.F90": [
        ("use hy_slopeLimiters", True),
        ("use hy_uhd_slopeLimiters", False),
    ],
    "Makefile": [("mgd_qesh.o", True)],
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _copy_list(src_dir: Path, names, dst_dir: Path,
               log: List[str]) -> Tuple[int, List[str]]:
    dst_dir.mkdir(parents=True, exist_ok=True)
    n, missing = 0, []
    for name in names:
        s = src_dir / name
        if not s.exists():
            missing.append(name)
            continue
        shutil.copyfile(s, dst_dir / name)
        n += 1
    log.append(f"    {dst_dir.relative_to(_SNB_DIR)}: {n}/{len(names)} 个")
    return n, missing


def _copy_tables(src_dir: Path, log: List[str]) -> List[str]:
    dst = SOURCE / "tables"
    dst.mkdir(parents=True, exist_ok=True)
    missing = []
    for name in CN4_TABLES:
        s = src_dir / name
        if not s.exists():
            missing.append(name)
            continue
        shutil.copyfile(s, dst / name)
        log.append(f"    tables/{name}  ({s.stat().st_size/1e6:.2f} MB)")
    return missing


def scan_patch_status() -> List[Tuple[str, str, bool]]:
    """检查关键补丁标记; 返回 [(文件, 特征串, 是否符合期望)]。"""
    rows: List[Tuple[str, str, bool]] = []
    for fname, checks in PATCH_MARKERS.items():
        p = SOURCE / "snb_package" / fname
        if not p.exists():
            rows.append((fname, "(文件缺失)", False))
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        for needle, want in checks:
            rows.append((fname, needle, (needle in txt) == want))
    return rows


def build_manifest() -> Dict[str, Dict[str, object]]:
    man: Dict[str, Dict[str, object]] = {}
    for p in sorted(SOURCE.rglob("*")):
        if p.is_file():
            rel = p.relative_to(_SNB_DIR).as_posix()
            man[rel] = {"bytes": p.stat().st_size, "sha256": sha256(p)}
    return man


def main() -> int:
    ap = argparse.ArgumentParser(
        description="SNB 源文件导入器 (只复制, 不含 F90 文本)")
    ap.add_argument("--from", dest="src", default=None,
                    help="作者 SNB 实现包目录 (含 9 个覆盖 F90)")
    ap.add_argument("--also-stock", default=None,
                    help="限流 SH 参考版目录 (对照腿用)")
    ap.add_argument("--verify-only", action="store_true",
                    help="仅校验现有 source/ 与补丁状态")
    args = ap.parse_args()

    print("=" * 78)
    print(" SNB 源文件导入器 → source/   (本地核心模块, 不入库)")
    print(f" 目标: {SOURCE}")
    print("=" * 78)

    if not args.verify_only:
        if not args.src:
            print("[X] 需要 --from <作者包目录> (或 --verify-only)")
            return 2
        src = Path(args.src).resolve()
        if not src.is_dir():
            print(f"[X] 源目录不存在: {src}")
            return 2

        log: List[str] = []
        print("\n── ① 作者 SNB 实现包 → source/snb_package/ ──")
        miss_f, m1 = _copy_list(src, SNB_F90, SOURCE / "snb_package", log)
        miss_b, m2 = _copy_list(src, SNB_BUILD, SOURCE / "snb_package", log)
        miss_s, m3 = _copy_list(src, SNB_SIM, SOURCE / "snb_package", log)
        for l in log:
            print(l)

        print("\n── ② 作者示例 par → source/example/ ──")
        _copy_list(src, SNB_EXAMPLE, SOURCE / "example", log)
        print(log[-1])

        print("\n── ③ EOS/opacity 表 → source/tables/ ──")
        miss_t = _copy_tables(src, [])
        for l in log[len(log) - (len(CN4_TABLES) - len(miss_t)):]:
            if "tables/" in l:
                print(l)

        if args.also_stock:
            st = Path(args.also_stock).resolve()
            print(f"\n── ④ 限流 SH 参考版 → source/stock_sh/  (来自 {st}) ──")
            if st.is_dir():
                _copy_list(st, STOCK_F90, SOURCE / "stock_sh", log)
                print(log[-1])
            else:
                print(f"    [!] 目录不存在, 跳过: {st}")

        missing = (m1 + m2 + m3 + miss_t)
        if missing:
            print(f"\n[!] 以下文件在源目录中缺失, 未复制: {missing}")

    # ── 校验 ────────────────────────────────────────────────
    print("\n── ⑤ 补丁状态校验 (编译必需改动) ──")
    ok_all = True
    for fname, needle, ok in scan_patch_status():
        print(f"    {'OK ' if ok else '[X]'} {fname:<45} '{needle}' "
              f"{'应存在' if not ok else ''}".rstrip())
        ok_all &= ok
    if not ok_all:
        print("    [!] 有补丁未打齐 → 编译会失败 (见 docs/03_编译与依赖.md)")

    print("\n── ⑥ 生成清单 manifest.json ──")
    man = build_manifest()
    MANIFEST.write_text(
        json.dumps({"files": man,
                    "note": "SNB 源文件清单 (仅供本地重建与校验; 不入库)"},
                   indent=2, ensure_ascii=False),
        encoding="utf-8", newline="\n")
    total = sum(v["bytes"] for v in man.values())
    print(f"    共 {len(man)} 个文件, {total/1e6:.2f} MB → {MANIFEST.name}")

    print("\n" + "=" * 78)
    print(" [OK] 导入完成" if ok_all else " [!] 导入完成, 但有补丁未打齐")
    print("=" * 78)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
