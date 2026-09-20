import os

R = 'src/Multi1D++Portable20241128'

def head(p, n=6, w=200):
    try:
        raw = open(p, 'rb').read(4096)
    except OSError as e:
        print('ERR', e); return
    lines = raw.replace(b'\r\n', b'\n').split(b'\n')[:n]
    print('--- %s  (%d bytes)' % (p, os.path.getsize(p)))
    for i, l in enumerate(lines):
        print('  %2d len=%-4d %r' % (i, len(l), l[:w]))

print('########## .CST vs .cst ##########')
print('>>> mat_He/Untitled.CST  (986,832 B)')
head(os.path.join(R, 'matter++/mat_He/Untitled.CST'))
print()
print('>>> reference: a .cst already documented')
for dp, dn, fn in os.walk(os.path.join(R, 'matter++')):
    for f in fn:
        if f.lower().endswith('.cst') and f != 'Untitled.CST':
            head(os.path.join(dp, f), n=4)
            break
    else:
        continue
    break

print()
print('########## no-extension samples ##########')
for p in ['matter++/mat_Gd/Gd100PLANCK',
          'matter++/mat_Gd/Gd100EPS',
          'matter++/CH/CHSi1_mopp100',
          'matter++/mat_Au-1.0/AU100PLANCK',
          'matter++/mat_C-1.0/C100PLANCK']:
    fp = os.path.join(R, p)
    if os.path.exists(fp):
        head(fp, n=4)
    else:
        # find any similar
        print('MISSING', p)
        d = os.path.dirname(fp)
        if os.path.isdir(d):
            cand = [x for x in os.listdir(d) if os.path.isfile(os.path.join(d, x)) and '.' not in x][:4]
            print('   candidates:', cand)
