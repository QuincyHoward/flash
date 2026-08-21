# -*- coding: utf-8 -*-
"""
一键运行测试 + 生成 HTML 报告
================================

等价于依次执行 test_all.py 与 generate_report.py。
支持所有 test_all.py 的过滤参数 (--only / --cn4 / --tasks)。

用法:
    python run_tests.py
    python run_tests.py --only CH
    python run_tests.py --tasks A,B,C
"""

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--cn4", dest="cn4", default=None)
    ap.add_argument("--tasks", default="A,B,C,D,E")
    args = ap.parse_args()

    py = sys.executable
    base = ["-u", os.path.join(HERE, "test_all.py")]
    if args.only:
        base += ["--only", args.only]
    if args.cn4:
        base += ["--cn4", args.cn4]
    if args.tasks:
        base += ["--tasks", args.tasks]

    print(">>> 运行测试 ...")
    rc1 = subprocess.run([py] + base).returncode
    if rc1 != 0:
        print(f"[!] test_all.py 返回非零: {rc1}")

    print("\n>>> 生成报告 ...")
    rc2 = subprocess.run(
        [py, "-u", os.path.join(HERE, "generate_report.py")]).returncode
    if rc2 != 0:
        print(f"[!] generate_report.py 返回非零: {rc2}")

    rep = os.path.join(HERE, "report.html")
    print(f"\n报告: {rep}")
    print(f"测试摘要: {os.path.join(HERE, 'test_summary.json')}")
    print(f"图像目录: {os.path.join(HERE, 'output')}")


if __name__ == "__main__":
    main()
