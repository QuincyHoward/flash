import os, re

M = 'src/Multi1D++Portable20241128/matter++/'
tok = re.compile(rb'[+-]?\d*\.?\d+(?:[EeDd][+-]?\d+)?')

# My earlier established truth: eos_21 nr=43 ne=1765 ; eos_22 36/1792 ; eos_23 75/2695 ; eos_24 73/2474
KNOWN = {
    'eos_21.sesame': (43, 1765),
    'eos_22.sesame': (36, 1792),
    'eos_23.sesame': (75, 2695),
    'eos_24.sesame': (73, 2474),
    'PowerLawTa2O5_EOS.SESAME': (3, 19),
    'PowerLawTa2O5_EOS.SESAME_': (5, 26),
    'Au_2003POPHammerRosen_EOS.SESAME': (6, 31),
}

print('%-42s %8s %5s %6s %14s %10s' % ('file', 'tokens', 'nr', 'ne', 'formula', 'match'))
for dp, dn, fn in os.walk(M):
    for f in fn:
        if f in KNOWN:
            p = os.path.join(dp, f)
            n = len(tok.findall(open(p, 'rb').read()))
            nr, ne = KNOWN[f]
            pred = 4 + 2 * nr + ne + 2 * nr * ne
            print('%-42s %8d %5d %6d %14d %10s' % (f, n, nr, ne, pred, 'OK' if pred == n else 'FAIL(%+d)' % (n - pred)))
