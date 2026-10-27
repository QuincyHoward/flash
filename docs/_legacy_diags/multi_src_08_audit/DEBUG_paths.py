# -*- coding: utf-8 -*-
import os, io
HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.abspath(os.path.join(HERE, '..', '..'))
MATTER = os.path.join(SRC, 'Multi1D++Portable20241128', 'matter++')
L = []
def P(s=''): L.append(str(s))
P("HERE   = %s" % HERE)
P("SRC    = %s" % SRC)
P("MATTER = %s" % MATTER)
P("isdir(MATTER) = %s" % os.path.isdir(MATTER))
P("")
P("listing of SRC:")
try:
    for n in sorted(os.listdir(SRC)):
        P("   %s  %s" % ('DIR ' if os.path.isdir(os.path.join(SRC,n)) else 'FILE', n))
except Exception as e:
    P("  listdir err %r" % e)
P("")
if os.path.isdir(MATTER):
    tops = sorted(os.listdir(MATTER))
    P("top-level entries of matter++: %d" % len(tops))
    for n in tops[:60]:
        P("   %s  %s" % ('DIR ' if os.path.isdir(os.path.join(MATTER,n)) else 'FILE', n))
    # count files
    cnt = 0; tot = 0
    for root, dirs, files in os.walk(MATTER):
        for f in files:
            cnt += 1
            try: tot += os.path.getsize(os.path.join(root,f))
            except OSError: pass
    P("")
    P("TOTAL FILES = %d ; TOTAL BYTES = %d" % (cnt, tot))
    # show a few .sesame
    ses = []
    for root, dirs, files in os.walk(MATTER):
        for f in files:
            if 'sesame' in f.lower():
                ses.append(os.path.relpath(os.path.join(root,f), MATTER))
    P("")
    P("files containing 'sesame' (%d):" % len(ses))
    for s in sorted(ses)[:30]:
        P("   %s" % s)
with io.open(os.path.join(HERE,'DEBUG_paths.txt'), 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L) + '\n')
print("ok")
