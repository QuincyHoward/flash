import os, re

R = 'src/Multi1D++Portable20241128'

# Find actual .sesame / .SESAME files
targets = []
for dp, dn, fn in os.walk(os.path.join(R, 'matter++')):
    for f in fn:
        if f.lower().endswith(('.sesame', '.sesame_', '.sesame_planck', '.sesame_rosseland')):
            targets.append(os.path.join(dp, f))
print('sesame-family files:', len(targets))
for t in targets:
    print('  %10d  %s' % (os.path.getsize(t), os.path.relpath(t, R)))
