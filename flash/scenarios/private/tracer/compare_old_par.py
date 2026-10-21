"""比对 VTi_old 的 flash.par 与当前 VTi 系列的 par，输出差异清单。

用法:
  python compare_old_par.py [--depth 2um]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

OLD_ROOT = Path("E:/ProgramsPATH/VMware/SharedFiles/Ubuntu24/"
                "FLASHWorkspace/FLASHProjectData/data/input")
CUR_ROOT = Path(__file__).resolve().parent

OLD_MAP = {
    "1um": OLD_ROOT / "ReDo042sp_CH042sp1um8.00e-02/ReDo042sp_CH042sp1um8.00e-022026"
                    "/hdf5files_20260331_205557/runfiles/flash.par",
    "2um": OLD_ROOT / "ReDo042sp_CH042sp2um8.00e-02/ReDo042sp_CH042sp2um8.00e-022026"
                    "/hdf5files_20260331_215819/runfiles/flash.par",
    "3um": OLD_ROOT / "ReDo042sp_CH042sp3um8.00e-02/ReDo042sp_CH042sp3um8.00e-022026"
                    "/hdf5files_20260331_231147/runfiles/flash.par",
}
CUR_MAP = {
    "1um": CUR_ROOT / "VTi/hpc_inputs/VTi1/laserslab_vti1.par",
    "2um": CUR_ROOT / "VTi/hpc_inputs/VTi2/laserslab_vti2.par",
    "3um": CUR_ROOT / "VTi/hpc_inputs/VTi3/laserslab_vti3.par",
}

PAT = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$")


def parse(path: Path) -> dict[str, str]:
    """解析 par 为 {key: value}，去掉行尾注释与引号。"""
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        m = PAT.match(line)
        if not m:
            continue
        k, v = m.group(1), m.group(2).strip().strip('"')
        out[k] = v
    return out


def norm(v: str) -> str:
    """数值归一化，便于比较 1.0 vs 1.000000000e+00 这类差异。"""
    try:
        return f"{float(v):.10g}"
    except ValueError:
        return v.strip('"').lower()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", default="2um", choices=["1um", "2um", "3um"])
    ap.add_argument("--full", action="store_true", help="打印全部键，不只差异")
    args = ap.parse_args()

    old_p, cur_p = OLD_MAP[args.depth], CUR_MAP[args.depth]
    print(f"[old] {old_p}\n[cur] {cur_p}\n")
    old, cur = parse(old_p), parse(cur_p)
    print(f"old 键数={len(old)}  cur 键数={len(cur)}\n")

    only_old = sorted(set(old) - set(cur))
    only_cur = sorted(set(cur) - set(old))
    both = sorted(set(old) & set(cur))
    diff = [k for k in both if norm(old[k]) != norm(cur[k])]

    def show(title: str, keys: list[str], src: dict[str, str], other: dict[str, str] | None):
        print(f"\n{'=' * 78}\n{title}  ({len(keys)})\n{'=' * 78}")
        for k in keys:
            if other is None:
                print(f"  {k:<34} = {src[k]}")
            else:
                print(f"  {k:<34} old={src[k]:<24} cur={other.get(k, '-')}")

    show("仅 old 有", only_old, old, None)
    show("仅 cur 有", only_cur, cur, None)
    show("值不同", diff, old, cur)
    print(f"\n汇总: 仅old={len(only_old)} 仅cur={len(only_cur)} 不同={len(diff)} "
          f"相同={len(both) - len(diff)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
