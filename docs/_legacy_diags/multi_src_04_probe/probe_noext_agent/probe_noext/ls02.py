# -*- coding: utf-8 -*-
import os
root = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
tp = os.path.join(root, ".workbuddy", "tmp")
for n in sorted(os.listdir(tp)):
    fp = os.path.join(tp, n)
    if os.path.isfile(fp):
        print("F", os.path.getsize(fp), n)
    else:
        print("D", "", n)
