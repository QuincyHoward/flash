# -*- coding: utf-8 -*-
"""数值感知 par 对比: flash.par (ref CH_CH_02um8.00e-02) vs laserslab_chml.par"""
from pathlib import Path
import re

import os
REF = os.environ["FLASH_OLD_VM_RUNFILES"] + r"\\flash.par"  # 旧 VM 参考算例 runfiles 目录（显式注入）
OUR = str(Path(__file__).resolve().parents[7] / "flash" /
          "scenarios/private/tracer/layer_tracer_CH_ml/flash_input/run_000001/laserslab_chml.par")


def parse(p):
    d = {}
    for raw in open(p, encoding="utf-8", errors="replace"):
        line = raw.split("#")[0].strip()
        m = re.match(r"^(\w+)\s*=\s*(.+?)\s*$", line)
        if m:
            d.setdefault(m.group(1), []).append(m.group(2).strip().strip('"'))
    return d


def norm(v):
    try:
        f = float(v)
        return round(f, 12 + 8)  # 相对容差比较
    except ValueError:
        return v.strip('"')


def same(a, b):
    try:
        fa, fb = float(a), float(b)
        if fa == fb:
            return True
        return abs(fa - fb) <= 1e-12 * max(abs(fa), abs(fb), 1e-300)
    except ValueError:
        return a.strip('"') == b.strip('"')


ref, our = parse(REF), parse(OUR)
keys = sorted(set(ref) | set(our))
n_diff = 0
print(f"{'param':<34}{'ref(flash.par)':>30}{'ours':>30}")
for k in keys:
    va, vb = ref.get(k), our.get(k)
    a = va[0] if va else None
    b = vb[0] if vb else None
    if a is None:
        print(f"{k:<34}{'<ABSENT>':>30}{b:>30}  ONLY-OURS"); n_diff += 1
    elif b is None:
        print(f"{k:<34}{a:>30}{'<ABSENT>':>30}  ONLY-REF"); n_diff += 1
    elif not same(a, b):
        print(f"{k:<34}{a:>30}{b:>30}  DIFF"); n_diff += 1
print(f"\n真差异: {n_diff} / {len(keys)} 参数")
