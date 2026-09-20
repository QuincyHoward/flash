# -*- coding: utf-8 -*-
"""Core toolkit: fixed-width field tokenizer + MULTI opacity table parser (Group A/D/E/F/B/H)."""
import os, re, hashlib, math, json

ROOT = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
MAT = os.path.join(ROOT, "src", "Multi1D++Portable20241128", "matter++")
OUT = os.path.join(ROOT, ".workbuddy", "tmp", "probe_noext")


def raw(path):
    with open(path, "rb") as f:
        return f.read()


def lines_raw(path):
    """Return list of raw lines (bytes, newline stripped)."""
    return raw(path).split(b"\n")


def line_ends(path):
    d = raw(path)
    crlf = d.count(b"\r\n")
    lf = d.count(b"\n")
    bare_lf = lf - crlf
    return {"crlf": crlf, "lf": lf, "bare_lf": bare_lf}


def tok15(line: bytes, w=15):
    """Fixed-width tokenizer. Returns list of str fields of width w."""
    s = line.rstrip(b"\r")
    return [s[i:i + w].decode("latin-1") for i in range(0, len(s) - len(s) % w, w)]


def all_tokens(path, w=15):
    """Tokenize whole file as fixed-width stream of w, skipping CR/LF.
    Returns (fields, npad) where npad = leftover non-whitespace chars."""
    d = raw(path)
    d = d.replace(b"\r\n", b"").replace(b"\n", b"")
    n = len(d) // w
    fields = [d[i * w:(i + 1) * w].decode("latin-1") for i in range(n)]
    tail = d[n * w:]
    return fields, tail


def num(f):
    f = f.strip()
    if not f:
        return None
    try:
        return float(f)
    except Exception:
        return None


def nums(fields):
    return [num(f) for f in fields]


def show_bytes(path, n=64):
    return raw(path)[:n]


def first_lines(path, k=4, nbytes=200):
    d = raw(path)
    out = []
    for ln in d.split(b"\n")[:k]:
        out.append(ln.rstrip(b"\r"))
    return out


def report(path, label="", w=15, nlines=6):
    print("=" * 100)
    print(label or path)
    print("  bytes =", os.path.getsize(path), " lineends =", line_ends(path))
    ls = raw(path).split(b"\n")
    print("  total lines(split \\n) =", len(ls))
    for i, ln in enumerate(ls[:nlines]):
        s = ln.rstrip(b"\r")
        print(f"  L{i} len={len(s):>3} repr={s[:200]!r}")
        if len(s) % w == 0 and len(s) > 0:
            print(f"       tok{w} -> {tok15(s, w)}")
    f, tail = all_tokens(path, w)
    print(f"  fixed-w {w} full-file token count = {len(f)}   leftover={tail!r} ({len(tail)} bytes)")
    return f
