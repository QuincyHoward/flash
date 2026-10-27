# -*- coding: utf-8 -*-
"""Inspect FEOS package data/parameter files: EOS-Data/*.par, *.dat, and
verify column widths against the writer source."""
import os, sys, io
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op\.workbuddy\tmp\vendor\FEOS_extract\inner\FEOS"

for rel in ["EOS-Data/Al.par", "EOS-Data/SiO2.par"]:
    p = os.path.join(BASE, rel)
    print("=" * 70)
    print("FILE:", rel, os.path.getsize(p), "bytes")
    print("=" * 70)
    with open(p, encoding="latin-1") as f:
        for n, line in enumerate(f, 1):
            print(f"{n:4d}|{line.rstrip()}")

p = os.path.join(BASE, "EOS-Data/FEOS_Material-DB.dat")
print("=" * 70)
print("FILE: EOS-Data/FEOS_Material-DB.dat", os.path.getsize(p), "bytes")
with open(p, encoding="latin-1") as f:
    for n, line in enumerate(f, 1):
        if n <= 25:
            print(f"{n:4d}|{line.rstrip()}")
print(" ...")

p = os.path.join(BASE, "EOS-Data/FEOS_TF-Table_1197.dat")
print("=" * 70)
print("FILE: EOS-Data/FEOS_TF-Table_1197.dat", os.path.getsize(p), "bytes")
with open(p, encoding="latin-1") as f:
    for n, line in enumerate(f, 1):
        if n <= 8:
            print(f"{n:4d}|len={len(line.rstrip())}|{line.rstrip()}")
        else:
            break
