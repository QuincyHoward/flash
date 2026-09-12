"""t003 诊断矩阵 —— 隔离「SNB 烧蚀偏快 / 启动失稳」的成因

背景
----
基线 (dx≈0.293 µm, 作者原版热传导) 在 t≈8.2 ps 因
`Negative 3T internal energy` 中止, 而 FL-SH 腿同网格跑满 tmax 正常。
本脚本用**受控单变量**逐一排查最可能的三个因素:

| 因素 | 变量 | 用例 |
|---|---|---|
| ① 时间积分步长限制 | `dtmax` 2e-12 → 2e-14 | D |
| ② **1D 分支 λ_g 限制被旁路 (D1)** | 热传导源 example → limiter | C |
| ③ 网格分辨率 (界面锐度) | dx 0.293 → 1.172 → 9.375 µm | B / A |

判读: 谁能让 SNB 腿从「8 ps 中止」变为「跑满 tmax」, 谁就是主导因素。

★ 用例顺序经过优化 (先把不需要重建的排前面)
   D 复用现有 nxb=128 构建 (只改 par)         → 无重建
   C 仅换热传导源 (同 nxb=128, 跳过 setup)     → 只 make
   B nxb=32 重建
   A nxb=8  重建 (复现作者原始分辨率)

用法 (在 t003 目录下):
    python scripts/analysis/diag_matrix.py
    python scripts/analysis/diag_matrix.py --only C,D
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

_T003 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_T003 / "common"))
import t003_common as C  # noqa: E402

RUNNER = _T003 / "scripts" / "run" / "run_t003.py"
PY = sys.executable
_REPO = C._REPO_ROOT

# (id, 说明, 参数)
CASES: Dict[str, Tuple[str, List[str]]] = {
    "D": ("dtmax 2e-12→2e-14 (复用 nxb=128 构建)",
          ["--model", "snb", "--nxb", "128", "--iprocs", "8",
           "--tmax", "2.0e-10", "--tag", "diag_dtmax2e14",
           "--dtmax", "2.0e-14",
           "--skip-deploy", "--skip-setup", "--skip-make"]),
    "C": ("热传导源 = limiterON (1D λ_g 限制启用, nxb=128)",
          ["--model", "snb", "--nxb", "128", "--iprocs", "8",
           "--tmax", "2.0e-10", "--tag", "diag_limiterON",
           "--therm-variant", "limiter",
           "--skip-setup"]),
    "B": ("nxb=32 → 256 格, dx≈1.172 µm (作者原版热传导)",
          ["--model", "snb", "--nxb", "32", "--iprocs", "8",
           "--tmax", "2.0e-10", "--tag", "diag_n256"]),
    "A": ("nxb=8 → 32 格, dx≈9.375 µm (复现作者原始 setup)",
          ["--model", "snb", "--nxb", "8", "--iprocs", "4",
           "--tmax", "2.0e-10", "--tag", "diag_n32"]),
}


def run_case(cid: str) -> Tuple[bool, str]:
    desc, argv = CASES[cid]
    print("\n" + "#" * 74)
    print(f"# 用例 {cid}: {desc}")
    print("#" * 74, flush=True)
    p = subprocess.run([PY, str(RUNNER)] + argv, cwd=str(_REPO),
                       capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    # 抓关键判据
    aborted = "Negative 3T internal energy" in out
    reached = "reached max SimTime" in out
    ok = reached and not aborted
    # 末尾几行留档
    tail = "\n".join(l for l in out.splitlines()[-14:])
    return ok, ("跑满 tmax" if ok else
                ("负 3T 内能中止" if aborted else "其它失败")) + "\n" + tail


def main() -> int:
    ap = argparse.ArgumentParser(description="t003 诊断矩阵")
    ap.add_argument("--only", default=None,
                    help="仅跑指定用例 (逗号分隔, 如 C,D)")
    args = ap.parse_args()

    ids = list(CASES) if not args.only else \
        [x.strip().upper() for x in args.only.split(",") if x.strip()]
    bad = [i for i in ids if i not in CASES]
    if bad:
        C.log(f"未知用例: {bad}", "ERROR")
        return 2

    print("\n" + "=" * 74)
    print(f" t003 诊断矩阵   {C.stamp()}")
    print(" 基线参照: dx≈0.293 µm + 作者原版热传导 → t≈8.2 ps 负 3T 内能中止")
    print(" 对照参照: FL-SH 腿同网格 → 跑满 tmax 正常")
    print("=" * 74)

    summary: Dict[str, Tuple[bool, str]] = {}
    for cid in ids:
        ok, msg = run_case(cid)
        summary[cid] = (ok, msg.splitlines()[0])
        print("\n" + "-" * 74)
        print(f"用例 {cid} 结果: {'✅ ' if ok else '❌ '}{msg}")
        print("-" * 74, flush=True)

    print("\n" + "=" * 74)
    print(" 诊断矩阵汇总")
    print("=" * 74)
    print(f" {'用例':<5}{'结论':<8}{'说明'}")
    for cid in ids:
        ok, note = summary[cid]
        print(f" {cid:<5}{'存活' if ok else '中止':<8}{CASES[cid][0]}")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
