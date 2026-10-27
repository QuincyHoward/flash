# -*- coding: utf-8 -*-
P = r'E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op/src/multi_docs/MultiEOSOP格式说明.md'
lines = open(P, encoding='utf-8', newline='').read().split('\n')
targets = [8415,8427,8439,8451,8463,8475,8487,8499,8511,8523,8535,8547,8559,8571,8583,8599,8745,8809,8832,8868,8890]
for t in targets:
    print('--- L%d ---' % t)
    for j in range(max(0,t-4), min(len(lines), t+2)):
        print('  %5d| %s' % (j+1, lines[j][:120]))
