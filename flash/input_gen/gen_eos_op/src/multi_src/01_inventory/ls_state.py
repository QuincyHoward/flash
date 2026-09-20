import os, glob
root = r'E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\flash\input_gen\gen_eos_op'
d = os.path.join(root, 'src', 'multi_docs')
print('=== multi_docs ===')
for f in sorted(os.listdir(d)):
    p = os.path.join(d, f)
    print(f'{f}  {os.path.getsize(p)}')
print()
print('=== tmp md files ===')
t = os.path.join(root, '.workbuddy', 'tmp')
for f in sorted(glob.glob(os.path.join(t, '*.md'))):
    print(f'{os.path.basename(f)}  {os.path.getsize(f)}')
