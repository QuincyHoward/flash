# -*- coding: utf-8 -*-
"""对比两份 FLASH .par 文件的参数值 (忽略注释/空白/格式)。"""
import re
import sys


def parse_par(path):
    params = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.split("#")[0].strip()
            if not line or "=" not in line:
                continue
            m = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)', line)
            if not m:
                continue
            key, val = m.group(1), m.group(2).strip().strip('"').strip("'")
            # 数值规范化: 1.0e2 -> 100.0
            try:
                val = float(val)
                val = f"{val:.6e}"
            except ValueError:
                pass
            params[key] = val
    return params


ref = parse_par(sys.argv[1])
vch = parse_par(sys.argv[2])

keys_ref = set(ref) - set(vch)
keys_vch = set(vch) - set(ref)
common = set(ref) & set(vch)
diff = {k: (ref[k], vch[k]) for k in sorted(common) if ref[k] != vch[k]}

print(f"=== 仅 REF 有 ({len(keys_ref)}) ===")
for k in sorted(keys_ref):
    print(f"  {k} = {ref[k]}")
print(f"\n=== 仅 VCH 有 ({len(keys_vch)}) ===")
for k in sorted(keys_vch):
    print(f"  {k} = {vch[k]}")
print(f"\n=== 值不同 ({len(diff)}) ===")
for k, (a, b) in diff.items():
    print(f"  {k}:  REF={a}   VCH={b}")
print(f"\n=== 值相同: {len(common) - len(diff)} / common {len(common)} ===")
