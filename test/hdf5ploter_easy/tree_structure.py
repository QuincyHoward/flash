import h5py, os, sys
from collections import defaultdict

fname = sys.argv[1] if len(sys.argv) > 1 else 'lasslab_hdf5_plt_cnt_0066'
outname = os.path.splitext(os.path.basename(fname))[0] + '_tree.html'

f = h5py.File(fname, 'r')
groups = defaultdict(list)
for k in f:
    d = f[k]
    if isinstance(d, h5py.Dataset):
        groups[(tuple(d.shape), str(d.dtype))].append(k)

# category info per (shape,dtype) group
cats = []
for sig, names in sorted(groups.items(), key=lambda x: -len(x[1])):
    shape, dtype = sig
    n = len(names)
    dts = str(dtype)
    if dts.startswith('[') or dts.startswith('{'):
        parts = 'compound'
    else:
        parts = dts
    info = '(%s) %s' % (','.join(str(x) for x in shape), parts)
    cats.append((names, n, info))

colors = [
    ('#EEEDFE','#534AB7'), ('#E1F5EE','#0F6E56'), ('#FAEEDA','#854F0B'),
    ('#EAF3DE','#3B6D11'), ('#FBEAF0','#993556'), ('#E6F1FB','#185FA5'),
    ('#FCEBEB','#A32D2D'), ('#F1EFE8','#5F5E5A'),
]

def esc(s):
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

html = []
html.append('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">')
html.append('<title>FLASH HDF5 Tree</title>')
html.append('<style>')
html.append('body{font-family:system-ui,sans-serif;font-size:13px;color:#222;background:#f8f9fa;padding:24px;max-width:700px;margin:0 auto}')
html.append('.root{background:#E6F1FB;border:1px solid #185FA5;border-radius:10px;padding:10px 18px;display:inline-block;margin-bottom:2px}')
html.append('.root .t{font-weight:600;font-size:14px}.root .s{font-size:12px;color:#555}')
html.append('.tree{padding-left:20px}')
html.append('.branch,.branch-last{position:relative;padding-left:20px;margin:0}')
html.append('.branch-line{position:absolute;left:0;top:0;bottom:0;border-left:1.5px solid #bbb}')
html.append('.branch-last>.branch-line{height:50%}')
html.append('.branch-line::before{content:"";position:absolute;left:-1px;top:21px;width:18px;border-top:1.5px solid #bbb}')
html.append('.node{position:relative;z-index:1;border-radius:7px;padding:6px 12px;margin:4px 0;border:1px solid;display:inline-block}')
html.append('.node .t{font-weight:600;font-size:13px}.node .s{font-size:12px;color:#666;margin-left:6px}')
html.append('.node .d{font-size:12px;color:#777;margin-top:1px}')
html.append('.note{margin-top:16px;padding-top:10px;border-top:1px solid #ddd;font-size:11px;color:#999}')
html.append('</style></head><body>')

# root
html.append('<div class="root">')
html.append('<div class="t">%s</div>' % esc(os.path.basename(fname)))
html.append('<div class="s">FLASH PLT &middot; %d datasets &middot; flat (no groups)</div>' % len(f))
html.append('</div><div class="tree">')

# tree nodes
for i, (names, n, info) in enumerate(cats):
    bg, st = colors[i % len(colors)]
    is_last = (i == len(cats) - 1)
    cls = 'branch-last' if is_last else 'branch'
    if n >= 3:
        detail = '%s, %s &middot;&middot;&middot;' % (esc(names[0]), esc(names[1]))
        suffix = ' <span class="s">(x%d)</span>' % n
    else:
        detail = ', '.join(esc(nm) for nm in names)
        suffix = ''
    html.append('<div class="%s"><div class="branch-line"></div>' % cls)
    html.append('<div class="node" style="background:%s;border-color:%s">' % (bg, st))
    html.append('<span class="t">%s</span>%s' % (esc(info), suffix))
    html.append('<div class="d">%s</div>' % detail)
    html.append('</div></div>')

# footnote
html.append('</div>')
html.append('<div class="note">similar = same shape + dtype &middot; max 2 items per collapsed group</div>')
html.append('</body></html>')

open(outname, 'w', encoding='utf-8').write('\n'.join(html))
print('Tree saved to %s' % outname)
