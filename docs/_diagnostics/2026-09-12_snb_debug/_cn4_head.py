# -*- coding: utf-8 -*-
"""本地直接解析 cn4 头 (E: 盘上也有这些表) —— 比走 WSL 更可靠。"""
import io, os, glob

WS = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
OUT = WS + r"\_cn4_head.txt"

SC = os.path.join(WS, "flash", "scenarios", "private", "tracer", "SNB",
                  "SNBOneCH_ml", "flash_input")

lines = []
found = []
for pat in ["**/*.cn4"]:
    found += glob.glob(os.path.join(WS, pat), recursive=True)

# 也搜场景目录
for root in [SC, os.path.join(WS, "flash", "scenarios", "private", "tracer", "SNB")]:
    if os.path.isdir(root):
        for dp, dn, fn in os.walk(root):
            for f in fn:
                if f.endswith(".cn4"):
                    found.append(os.path.join(dp, f))

found = sorted(set(found))
lines.append(f"FOUND {len(found)} cn4:")
for f in found:
    lines.append(f"  {f}")
lines.append("")

for f in found:
    try:
        with io.open(f, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.readlines()
    except Exception as e:
        lines.append(f"### {os.path.basename(f)} READ_FAIL {e}\n")
        continue
    lines.append(f"######## {os.path.basename(f)}  ({os.path.getsize(f)} bytes, {len(raw)} lines)")
    for i in range(min(8, len(raw))):
        lines.append(f"  [{i}] {raw[i].rstrip()[:160]}")
    # 找温度/密度轴行: IONMIX4 头后第一段数字
    num = 0
    for i, ln in enumerate(raw):
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        toks = s.split()
        try:
            float(toks[0])
        except Exception:
            continue
        num += 1
        if num <= 4:
            lines.append(f"  NUM[{i}] n={len(toks)} first3={toks[:3]} last3={toks[-3:]}")
        else:
            break
    lines.append("")

io.open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("WROTE", OUT, "files=", len(found))
