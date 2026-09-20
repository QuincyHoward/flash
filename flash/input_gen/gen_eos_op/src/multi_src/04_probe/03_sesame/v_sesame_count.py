import re

# Test both candidate formulations against the real files.
# Recount the actual numeric-token count of each .sesame file.
R = 'src/Multi1D++Portable20241128/'
files = {
    'Ta2O5/PowerLawTa2O5_EOS.SESAME': 2217,
    'Ta2O5/PowerLawTa2O5_EOS.SESAME_': 4650,
    'Au/Au_2003POPHammerRosen_EOS.SESAME': 6495,
    'SiO2/eos_21.sesame': 2381499,
    'SiO2/eos_22.sesame': 2028826,
    'SiO2/eos_23.sesame': 6310035,
    'SiO2/eos_24.sesame': 5639334,
}

tok = re.compile(rb'[+-]?\d*\.?\d+(?:[EeDd][+-]?\d+)?')
for rel, sz in files.items():
    raw = open(R + rel, 'rb').read()
    toks = tok.findall(raw)
    print('=' * 70)
    print(rel)
    print('  bytes=%d  numeric tokens=%d' % (sz, len(toks)))
    print('  first 8 tokens:', [t.decode() for t in toks[:8]])
    print('  last 8 tokens :', [t.decode() for t in toks[-8:]])
