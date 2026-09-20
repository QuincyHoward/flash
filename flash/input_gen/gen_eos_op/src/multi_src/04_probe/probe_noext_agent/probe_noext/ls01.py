# -*- coding: utf-8 -*-
import os, sys
root = r"E:/PhySimX/PhySimX/simulation/flash_test/layer3/flash/flash/input_gen/gen_eos_op"
for p in [root, os.path.join(root, ".workbuddy"), os.path.join(root, ".workbuddy", "tmp"),
          os.path.join(root, "src"), os.path.join(root, "src", "multi_docs")]:
    print("=== ", p, " exists=", os.path.isdir(p))
    if os.path.isdir(p):
        try:
            for n in sorted(os.listdir(p))[:60]:
                fp = os.path.join(p, n)
                print("   ", ("D" if os.path.isdir(fp) else "F"), n,
                      (os.path.getsize(fp) if os.path.isfile(fp) else ""))
        except Exception as e:
            print("   ERR", e)
