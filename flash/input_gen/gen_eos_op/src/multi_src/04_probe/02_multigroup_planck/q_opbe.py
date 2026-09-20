# -*- coding: utf-8 -*-
"""opbe 异常溯源：是否 = opbe.Planck + 自身副本 + 111 行尾巴。"""
import os, hashlib

ROOT = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
M = os.path.join(ROOT, 'src', 'Multi1D++Portable20241128', 'matter++', 'mat_Be-1.0')

opbe = open(os.path.join(M, 'opbe'), 'rb').read().replace(b'\r\n', b'\n')
pl = open(os.path.join(M, 'opbe.Planck'), 'rb').read().replace(b'\r\n', b'\n')
ro = open(os.path.join(M, 'opbe.Rosseland'), 'rb').read().replace(b'\r\n', b'\n')

def h(b):
    return hashlib.md5(b).hexdigest()[:12]

print('opbe          %9d B  md5=%s' % (len(opbe), h(opbe)))
print('opbe.Planck   %9d B  md5=%s' % (len(pl), h(pl)))
print('opbe.Rosseland%9d B  md5=%s' % (len(ro), h(ro)))
print()
print('opbe == opbe.Planck + opbe.Planck + tail ?',
      opbe.startswith(pl))
print('  opbe[:len(pl)] == opbe.Planck          :', opbe[:len(pl)] == pl)
print('  opbe[len(pl):2*len(pl)] == opbe.Planck :', opbe[len(pl):2 * len(pl)] == pl)
print('  opbe[len(pl):2*len(pl)] == opbe.Rosseland:',
      opbe[len(pl):2 * len(pl)] == ro)
tail = opbe[2 * len(pl):]
print('  tail len = %d B  行数 = %d' % (len(tail), len(tail.split(b'\n'))))
print('  tail 前 3 行:')
for i, l in enumerate(tail.split(b'\n')[:4]):
    print('     %d [%3d] %r' % (i, len(l), l.decode('latin-1')[:80]))
print()
print('  opbe 全体 30/60 计数: 30=%d 60=%d'
      % (sum(1 for l in opbe.split(b'\n') if len(l) == 30),
         sum(1 for l in opbe.split(b'\n') if len(l) == 60)))
print('  61 字符行的索引与内容:')
for i, l in enumerate(opbe.split(b'\n')):
    if len(l) == 61:
        print('     idx=%d %r' % (i, l.decode('latin-1')))
print()
print('  第 41 群的表头（idx=4481 对应行）:')
Ln = [l for l in opbe.split(b'\n') if l.strip()]
for i in range(4479, 4484):
    print('     %4d [%3d] %r' % (i, len(Ln[i]), Ln[i].decode('latin-1')[:80]))

print()
print('对比 opbe.Rosseland 头部:')
print('   ', ro.split(b'\n')[0].decode('latin-1'))
print('   ', pl.split(b'\n')[0].decode('latin-1'))
