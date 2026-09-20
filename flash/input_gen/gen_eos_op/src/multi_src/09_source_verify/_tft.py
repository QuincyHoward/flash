# -*- coding: utf-8 -*-
import os, sys, io, hashlib, csv
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op\src\Multi1D++Portable20241128"

a = os.path.join(ROOT, "tabelle/tabelle1197.TFT")
b = os.path.join(ROOT, "FEOS_TF-Table_1197.dat")
ha = hashlib.sha256(open(a,'rb').read()).hexdigest()
hb = hashlib.sha256(open(b,'rb').read()).hexdigest()
print("sha256 tabelle/tabelle1197.TFT      =", ha)
print("sha256 FEOS_TF-Table_1197.dat       =", hb)
print("IDENTICAL:", ha == hb)
print()

# block structure analysis
raw = open(a,'rb').read().decode('latin-1')
lines = [L for L in raw.splitlines() if L.strip()]
print("total nonblank lines =", len(lines))
# a rho block header line has exactly 1 field
n1 = 0; n6 = 0
rho_lines = []
for i, L in enumerate(lines):
    nf = len(L.split())
    if nf == 1:
        n1 += 1; rho_lines.append(i)
    elif nf == 6:
        n6 += 1
    else:
        print("ANOMALY line %d nf=%d : %s" % (i+1, nf, L[:120]))
print("lines with 1 field (rho block headers) =", n1)
print("lines with 6 fields (data rows)        =", n6)
print("6-field lines per rho block            =", n6/n1 if n1 else 0)
print()
print("first 6 rho values:")
for i in rho_lines[:6]:
    print("  ", lines[i])
print("last 4 rho values:")
for i in rho_lines[-4:]:
    print("  ", lines[i])
print("last line of file:", repr(lines[-1][:120]))
print()
# Te column values from first block
blk0 = lines[rho_lines[0]+1:rho_lines[1]]
tes = [float(L.split()[0]) for L in blk0]
print("block0 NT =", len(blk0), " Te range:", tes[0], "->", tes[-1])
print("Te first 3:", tes[:3], " Te last 3:", tes[-3:])
print()
# check all blocks same NT
nts = set()
for k in range(len(rho_lines)):
    end = rho_lines[k+1] if k+1 < len(rho_lines) else len(lines)
    nts.add(end - rho_lines[k] - 1)
print("distinct NT per block =", sorted(nts))
