# -*- coding: utf-8 -*-
"""原始行 dump: 逐行打印 cn4 前 200 行的 repr, 弄清真实列布局。"""
import io, os

WS = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
OUT = WS + r"\_cn4_raw.txt"

p = os.path.join(WS, r"flash\scenarios\private\tracer\SNB\SNBOneCH_ml\flash_input\CH-BADGER-TOPS-Final.cn4")
raw = io.open(p, "r", encoding="utf-8", errors="replace").read().splitlines()

L = [f"FILE {p}", f"total lines {len(raw)}", ""]
for i in range(min(160, len(raw))):
    L.append(f"[{i:3d}] len={len(raw[i]):4d} {raw[i]!r}")

io.open(OUT, "w", encoding="utf-8").write("\n".join(L))
print("WROTE", OUT)
