# -*- coding: utf-8 -*-
# probe_14: corrected whitespace-split vs fixed-width robustness test
import os, json, re

ROOT = os.path.join("src", "Multi1D++Portable20241128", "matter++")

def find_cst():
    out = []
    for dp, dn, fn in os.walk(ROOT):
        for f in fn:
            if f.lower().endswith(".cst"):
                out.append(os.path.join(dp, f))
    return sorted(out)

NUM_RE = re.compile(r'^[+-]?(\d+\.?\d*|\.\d+)([eEdD][+-]?\d+)?$|^[+-]?1\.#(INF|IND|QNAN|SNAN)00e[+-]?\d+$', re.I)
INF_RE = re.compile(r'-?1\.#(INF|IND|QNAN)00e[+-]?\d+', re.I)

def is_dataline(ln):
    """A data line: made only of numeric-ish tokens (>=2 tokens), no letters except e/E/INF tokens."""
    toks = ln.split()
    if len(toks) < 3:
        return False
    for t in toks:
        tt = INF_RE.sub("1e0", t)
        if not NUM_RE.match(tt):
            return False
    return True

report = {}
for p in find_cst():
    with open(p, "r", encoding="latin-1", newline="") as fh:
        raw = fh.read()
    lines = raw.replace("\r\n", "\n").split("\n")
    rel = os.path.relpath(p, ROOT)
    data = [ln for ln in lines if is_dataline(ln)]
    if not data:
        report[rel] = {"n_data": 0}
        continue
    # whitespace split census
    ntok = {}
    for ln in data:
        ntok[len(ln.split())] = ntok.get(len(ln.split()), 0) + 1
    # fixed-width parse: try widths 12 and 13
    fw_ok, fw_bad = {}, {}
    for w in (12, 13):
        # 4 fields of width w, first field starts at 0
        # DE: 12+10? empirically try even slices
        good = bad = 0
        for ln in data[:200]:
            g = 0
            for k in range(4):
                seg = ln[k * (w + 0):k * (w + 0) + w] if False else None
            # simpler: try offsets list variants
        fw_ok[w] = 0
    # explicit robust test: split-based field extraction vs column-offset extraction
    # Determine observed token start offsets
    offs_census = {}
    for ln in data[:500]:
        offs = []
        pos = 0
        for t in ln.split():
            i = ln.index(t, pos)
            offs.append(i)
            pos = i + len(t)
        key = tuple(offs)
        offs_census[key] = offs_census.get(key, 0) + 1
    top = sorted(offs_census.items(), key=lambda kv: -kv[1])[:5]
    report[rel] = {
        "n_lines_total": len(lines),
        "n_data": len(data),
        "ntok_census": ntok,
        "top_offsets": [[list(k), v] for k, v in top],
    }

with open(os.path.join(".workbuddy", "tmp", "out_14.txt"), "w", encoding="utf-8") as fh:
    fh.write(json.dumps(report, ensure_ascii=False, indent=1))
print("EXIT_OK")
