# -*- coding: utf-8 -*-
"""Verify the two weakest claims before finalizing:
   (1) CHECKSUM: is it bsd16/sysv16/fletcher?  Test against actual files.
   (2) 1041_PLANCK: k=1 with a 45-char line -> confirm the real layout."""
import os, sys, zlib, binascii
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk import *


def bsd16(data):
    s = 0
    for b in data:
        s = (s >> 1) + ((s & 1) << 15)
        s = (s + b) & 0xFFFF
    return s


def sysv16(data):
    s = sum(data) & 0xFFFFFFFF
    return (s & 0xFFFF) + (s >> 16)


def fletcher16(data):
    a = b = 0
    for x in data:
        a = (a + x) % 255
        b = (b + a) % 255
    return (b << 8) | a


print("### (1) CHECKSUM reverse-engineering")
cs = os.path.join(MAT, "mat_CPC", "CHECKSUM")
txt = open(cs, encoding="latin-1").read()
rows = [l for l in txt.splitlines() if l.strip()]
print("  mat_CPC/CHECKSUM:")
for l in rows:
    print("   ", l)
print()
for l in rows:
    parts = l.split(":")
    fn, f2, f3 = parts[0], parts[1], parts[2]
    p = os.path.join(MAT, "mat_CPC", fn)
    if not os.path.isfile(p):
        print(f"  {fn:<20} MISSING"); continue
    d = raw(p)
    tgt = (int(f2), int(f3))
    print(f"  {fn:<20} size={len(d):>7} target={tgt}"
          f"  bsd16={bsd16(d):>5} sysv16={sysv16(d):>5} fletcher={fletcher16(d):>5}"
          f"  sum&0xFFFF={sum(d)&0xFFFF:>5} crc16={binascii.crc_hqx(d,0):>5}"
          f"  adler={zlib.adler32(d)&0xFFFF:>5}")

print("\n### CHECKSUM of the CHECKSUM file itself? and FILELIST")
for fn in ["FILELIST", "MODINFO", "LOCK"]:
    p = os.path.join(MAT, "mat_CPC", fn)
    if os.path.isfile(p):
        d = raw(p)
        print(f"  {fn:<12} bsd16={bsd16(d):>5} sysv16={sysv16(d):>5} fletcher={fletcher16(d):>5}")

print("\n\n### (2) 1041_PLANCK full structure")
for rel in ["mat_Al-1.0/1041_PLANCK", "mat_Al-1.0/1041_ROSS"]:
    p = os.path.join(MAT, rel.replace("/", os.sep))
    d = raw(p)
    he = [l.rstrip(b"\r") for l in d.split(b"\n") if l.rstrip(b"\r") != b""]
    f, tail = all_tokens(p, 15)
    print(f"\n-- {rel} bytes={len(d)} lines={len(he)} N15={len(f)} tail={tail!r}")
    from collections import Counter
    print(f"   len hist: {dict(sorted(Counter(len(l) for l in he).items()))}")
    print(f"   L0: {he[0]!r}")
    print(f"   L1: {he[1]!r}")
    print(f"   L374: {he[374]!r}")
    print(f"   L375: {he[375]!r}")
    print(f"   L376: {he[376]!r}")

print("\n\n### (3) Ce.INPUT: full &daten namelist (authoritative)")
ce = os.path.join(MAT, "mat_Ce", "Ce.INPUT")
print(open(ce, encoding="latin-1").read()[:2500])
