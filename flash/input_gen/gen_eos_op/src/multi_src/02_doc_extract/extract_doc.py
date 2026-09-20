# -*- coding: utf-8 -*-
"""Extract text from legacy Word .doc (OLE2 compound file, Word 6/95/97-2003 binary).

Root-cause fix for the garbled 'legacy_doc_full.txt':
the WordDocument stream text is stored either as CP1252 (1 byte/char) or
UTF-16LE (2 bytes/char, when FIB fExtChar=1). The previous attempt read the
UTF-16LE bytes and decoded them as if they were a codepage, producing
byte-swapped mojibake.
"""
import os
import struct
import sys

import olefile


def find_text_stream(ole):
    """Return (raw_bytes, is_unicode, fcMin, fcMac) for the main text."""
    if not ole.exists('WordDocument'):
        return None
    wd = ole.openstream('WordDocument').read()
    if len(wd) < 0x20:
        return None
    # FIB
    wIdent, nFib = struct.unpack_from('<HH', wd, 0)
    flags = struct.unpack_from('<H', wd, 0x0A)[0]
    fWhichTblStm = (flags >> 9) & 1
    # fExtChar is bit 12 of the flags word at 0x0A in nFib>=101
    fExtChar = (flags >> 12) & 1
    fcMin, fcMac = struct.unpack_from('<II', wd, 0x18)
    # ccpText from the fibRgLw97 (offset 0x4C for nFib>=193)
    ccpText = 0
    try:
        ccpText = struct.unpack_from('<i', wd, 0x4C)[0]
    except Exception:
        pass
    return wd, fcMin, fcMac, ccpText, nFib, fExtChar, fWhichTblStm


def extract_word6_text(wd, fcMin, fcMac):
    return wd[fcMin:fcMac]


def get_tbl_stream(ole, fWhichTblStm):
    name = '1Table' if fWhichTblStm else '0Table'
    if ole.exists(name):
        return ole.openstream(name).read(), name
    for alt in ('1Table', '0Table'):
        if ole.exists(alt):
            return ole.openstream(alt).read(), alt
    return None, None


def decode_piece_table(wd, tbl, fcMin, fcMac):
    """Word97 piece table (CLX) based extraction -> (text, note)."""
    idx = wd.find(b'\x02\x00\x01\x00') if False else -1
    # locate CLX: fcClx/lcbClx in FIB (nFib 193+): offset 0x01A2
    try:
        fcClx, lcbClx = struct.unpack_from('<II', wd, 0x01A2)
    except Exception:
        return None, 'no CLX offsets'
    if lcbClx == 0 or fcClx + lcbClx > len(tbl):
        return None, 'CLX out of range (fc=%d lcb=%d tbl=%d)' % (fcClx, lcbClx, len(tbl))
    clx = tbl[fcClx:fcClx + lcbClx]
    # walk CLX
    i = 0
    plcpcd = None
    while i < len(clx):
        clxt = clx[i]
        if clxt == 0x01:
            cb = struct.unpack_from('<H', clx, i + 1)[0]
            i += 3 + cb
        elif clxt == 0x02:
            lcb = struct.unpack_from('<I', clx, i + 1)[0]
            plcpcd = clx[i + 5:i + 5 + lcb]
            break
        else:
            i += 1
    if plcpcd is None:
        return None, 'no Pcdt (CLX has Prc only, lcb=%d)' % lcbClx
    n = (len(plcpcd) - 4) // 12
    if n <= 0:
        return None, 'Pcdt too short (len=%d)' % len(plcpcd)
    cps = list(struct.unpack_from('<%dI' % (n + 1), plcpcd, 0))
    out = []
    base = 4 * (n + 1)
    for k in range(n):
        off = base + k * 8
        if off + 8 > len(plcpcd):
            break
        pcd = plcpcd[off: off + 8]
        fc = struct.unpack_from('<I', pcd, 2)[0]
        fCompressed = (fc >> 30) & 1
        fcv = fc & 0x3FFFFFFF
        ln = cps[k + 1] - cps[k]
        if fCompressed:
            fcv = fcv // 2
            chunk = wd[fcv:fcv + ln]
            out.append(chunk.decode('cp1252', 'replace'))
        else:
            chunk = wd[fcv:fcv + ln * 2]
            out.append(chunk.decode('utf-16-le', 'replace'))
    return ''.join(out), 'piece table OK (n=%d)' % n


def clean(t):
    reps = {'\r': '\n', '\x07': '\t|\t', '\x0b': '\n', '\x0c': '\n',
            '\x13': '', '\x14': '', '\x15': '', '\x01': '', '\x02': '',
            '\x08': '', '\x1e': '-', '\xa0': ' '}
    for k, v in reps.items():
        t = t.replace(k, v)
    lines = [ln.rstrip() for ln in t.split('\n')]
    out = []
    blank = 0
    for ln in lines:
        if ln.strip() == '':
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        out.append(ln)
    return '\n'.join(out)


def extract(path):
    ole = olefile.OleFileIO(path)
    info = find_text_stream(ole)
    if not info:
        return '', 'no WordDocument stream'
    wd, fcMin, fcMac, ccpText, nFib, fExtChar, fWhichTblStm = info
    tbl, tblname = get_tbl_stream(ole, fWhichTblStm)
    note = 'nFib=%d fcMin=%d fcMac=%d ccpText=%d fExtChar=%d tbl=%s' % (
        nFib, fcMin, fcMac, ccpText, fExtChar, tblname)
    if tbl is not None and nFib >= 193:
        txt, sub = decode_piece_table(wd, tbl, fcMin, fcMac)
        if txt is not None and len(txt.strip()) > 50:
            return clean(txt), note + ' | ' + sub
    # Fallback: naive fcMin..fcMac with encoding guess
    raw = wd[fcMin:fcMac]
    best, bestscore = '', -1
    for enc, name in (('cp1252', 'cp1252'), ('utf-16-le', 'utf-16le')):
        try:
            cand = raw.decode(enc, 'replace')
        except Exception:
            continue
        score = sum(1 for c in cand if c.isprintable() or c in '\r\n\t')
        if score > bestscore:
            best, bestscore = cand, score
    return clean(best), note + ' | fallback naive'


def main():
    src = sys.argv[1]
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    files = []
    if os.path.isdir(src):
        for root, dirs, fs in os.walk(src):
            for f in fs:
                if f.lower().endswith('.doc') and not f.startswith('~$'):
                    files.append(os.path.join(root, f))
    else:
        files = [src]
    for p in sorted(files):
        try:
            txt, note = extract(p)
            base = os.path.splitext(os.path.basename(p))[0]
            op = os.path.join(outdir, base + '.txt')
            with open(op, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(txt)
            cjk = sum(1 for c in txt if '\u4e00' <= c <= '\u9fff')
            print('OK  %-45s %7d chars  %6d CJK  | %s' % (
                os.path.basename(p), len(txt), cjk, note))
        except Exception as e:
            print('ERR %-45s %s: %s' % (os.path.basename(p), type(e).__name__, e))


if __name__ == '__main__':
    main()
