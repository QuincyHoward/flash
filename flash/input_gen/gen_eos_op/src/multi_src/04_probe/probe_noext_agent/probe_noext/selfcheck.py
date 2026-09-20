# -*- coding: utf-8 -*-
"""自检：报告 §10.3 / §10.4 的代码块必须原样可运行且结果与报告一致。"""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
MAT  = os.path.join(ROOT, "src", "Multi1D++Portable20241128", "matter++")

def raw(path):
    with open(path, "rb") as fh:
        return fh.read()

def tok15(line, w=15):
    s = line.rstrip(b"\r")
    return [s[i:i+w].decode("latin-1") for i in range(0, len(s) - len(s) % w, w)]

def all_tokens(path, w=15):
    d = raw(path).replace(b"\r\n", b"").replace(b"\n", b"")
    n = len(d) // w
    return [d[i*w:(i+1)*w].decode("latin-1") for i in range(n)], d[n*w:]

def num(f):
    try:
        return float(f)
    except Exception:
        return None

# ---- §10.3 ----
def bsd16(b):
    s = 0
    for x in b:
        s = ((s >> 1) | ((s & 1) << 15)) & 0xFFFF
        s = (s + x) & 0xFFFF
    return s

def sysv16(b):
    s = sum(b) & 0xFFFFFFFF
    s = (s & 0xFFFF) + (s >> 16)
    s = (s & 0xFFFF) + (s >> 16)
    return s & 0xFFFF

print("### 10.3 CHECKSUM")
ok = True
for name, t1, t2 in [("AU.INV", 44905, 5669), ("AU_WorkOp_Ross", 8222, 19378),
                     ("BE.INV", 61026, 59441), ("BE_PLANCKx03", 9203, 35000),
                     ("FILELIST", 4609, 64318), ("MODINFO", 12381, 16019),
                     ("LOCK", 2555, 51712)]:
    d = raw(os.path.join(MAT, "mat_CPC", name))
    got = (sysv16(d), bsd16(d))
    hit = got == (t1, t2)
    ok &= hit
    print("  %-18s target=(%5d,%5d) got=(%5d,%5d) %s" % (name, t1, t2, got[0], got[1], "OK" if hit else "FAIL"))
print("  ALL:", ok)

# ---- §10.4 ----
print("### 10.4 1041_PLANCK")
p = os.path.join(MAT, "mat_Al-1.0", "1041_PLANCK")
f, tail = all_tokens(p, 15)
hdr = tok15(raw(p).split(b"\n")[0], 15)
id_, zbar, nr, nt = (num(x) for x in hdr)
nr, nt = int(nr), int(nt)
print("  len(f)=%d  4+nr+nt+nr*nt=%d  tail=%r  hdr=(%s,%s,%d,%d)" % (
    len(f), 4 + nr + nt + nr * nt, tail, hdr[0].strip(), hdr[1], nr, nt))
print("  len(f)==4+nr+nt+nr*nt ->", len(f) == 4 + nr + nt + nr * nt, " tail==b'' ->", tail == b"")

# ---- §10.1 组 A 闭合（抽查 3 个） ----
def groupA_solve(rel, k):
    p = os.path.join(MAT, rel.replace("/", os.sep))
    ne = [l.rstrip(b"\r") for l in raw(p).split(b"\n") if l.rstrip(b"\r") != b""]
    f, _ = all_tokens(p, 15)
    N = len(f)
    if N % k:
        return None, None, False
    R = N // k - 1
    W = R - 5
    for nt in range(1, 4000):
        if W - nt <= 0 or (W - nt) % (nt + 1):
            continue
        nr = (W - nt) // (nt + 1)
        if nr < 2:
            continue
        vv = []
        for i, l in enumerate(ne[:len(ne) // k]):
            t = tok15(l, 15)
            if i == 0:
                t = t[:1] + t[2:]
            vv += t
        rho = [num(x) for x in vv[5:5+nr]]
        T = [num(x) for x in vv[5+nr:5+nr+nt]]
        if None in rho or None in T:
            continue
        if all(rho[i] < rho[i+1] for i in range(nr-1)) and all(T[i] < T[i+1] for i in range(nt-1)):
            return nr, nt, (5 + nr + nt + nr*nt == R)
    return None, None, False

print("### 10.1 组A抽查")
for rel, k in [("mat_Au-1.0/AU_op03p", 20), ("mat_Al-1.0/1041_PLANCK", 1),
               ("CH/CHSi1_mopp", 20)]:
    print("  %-28s k=%-4d -> %s" % (rel, k, groupA_solve(rel, k)))

# ---- §10.2 组 D/E ----
def groupDE_check(rel, nr, nt):
    p = os.path.join(MAT, rel.replace("/", os.sep))
    f, _ = all_tokens(p, 15)
    N = len(f)
    v = [num(x) for x in f[4:]]
    v = [x for x in v if x is not None]
    rho = v[0:nr]; T = v[nr:nr+nt]
    mr = all(rho[i] < rho[i+1] for i in range(nr-1))
    mt = all(T[i] < T[i+1] for i in range(nt-1))
    return (N == 4 + 2*nr + nt + 2*nr*nt), mr, mt

print("### 10.2 组D/E")
for rel, nr, nt in [("mat_Ti/422_ieos", 43, 22), ("mat_Al-1.0/AL_eos", 66, 74),
                    ("mat_Be-1.0/BE_eos", 101, 50), ("mat_CELIA/DD_ieos", 50, 25)]:
    print("  %-24s (%d,%d) -> %s" % (rel, nr, nt, groupDE_check(rel, nr, nt)))
