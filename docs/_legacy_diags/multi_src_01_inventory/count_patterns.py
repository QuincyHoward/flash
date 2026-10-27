# -*- coding: utf-8 -*-
"""第十一轮探查：按族模式统计 matter++ 全树匹配文件数与体积（全量复制决策用）。"""
import sys
import fnmatch

sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op\eosop_pro\test")
sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op\eosop_pro")

from eosopdata._samples import _all_matter_files

FAMILY_PATTERNS = {
    "mpqeos": ("*.301",),
    "hyades_eos": ("qeos_*",),
    "feos_native": ("*.feos",),
    "multi_inverted_eos": ("AL_eos",),
    "ledcop_atomic": ("Al.txt",),
    "ledcop_zeff": ("*.NoFree",),
    "multi_opacity": ("*.planck",),
    "sesame_dat": ("*.dat",),
    "coldopacity": ("*.coldopacity",),
    "generic_curve": ("ionpot*",),
    "hugoniot": ("*.hug",),
}

files = _all_matter_files()
lines = [f"total matter files: {len(files)}"]
claimed: set = set()
for fam, pats in FAMILY_PATTERNS.items():
    m = [f for f in files if any(fnmatch.fnmatch(f.name, p) for p in pats)]
    claimed.update(m)
    tot = sum(f.stat().st_size for f in m if f.exists())
    lines.append(f"[{fam}] n={len(m)} bytes={tot}")
    for f in m:
        lines.append(f"    {f}  ({f.stat().st_size})")
un = [f for f in files if f not in claimed]
lines.append(f"unclaimed-by-name: {len(un)}")

out = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op\.workbuddy\tmp\count_patterns.txt"
with open(out, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(lines))
print("written", out)
