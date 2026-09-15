#!/usr/bin/env python
"""③ 阶段 A 收官审计 —— 对 ``matter++`` 全树做声明式解析并产出三份报告。

用法::

    <venv>/Scripts/python.exe scripts/03_audit_sweep.py            # 全量
    <venv>/Scripts/python.exe scripts/03_audit_sweep.py --limit 40 # 冒烟（前 40 个）
    <venv>/Scripts/python.exe scripts/03_audit_sweep.py --multigroup  # 额外解析多群段（慢）

产出（``outputs/reports/``）::

    audit_all.<ts>.csv    每文件一行，全部字段（Excel/pandas 可直接分析）
    audit_all.<ts>.json   同内容的结构化版本
    audit_all.<ts>.md     人读：按 status/family 计数、问题清单、闸口结论

闸口：``已解析 + 已跳过 == 审计样本数``，且 ``error`` / ``count_mismatch``
清单可逐条定性。

★ 本文件只是**薄包装**。真正的实现是 ``eosop_pro.batch.audit_sweep`` ——
这样它才能被 ``test/test_batch.py`` 直接调用测试，而不是只能靠命令行跑。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eosop_pro import batch  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="matter++ 阶段 A 全量审计扫描")
    ap.add_argument("--multigroup", action="store_true",
                    help="额外解析 LEDCOP 多群段（显著更慢/更吃内存）")
    ap.add_argument("--limit", type=int, default=0,
                    help="只审计前 N 个声明文件（0 = 全量）")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--matter-dir", dest="matter_dir", default=None)
    args = ap.parse_args(argv)

    r = batch.audit_sweep(outdir=args.outdir, multigroup=args.multigroup,
                          matter_dir=args.matter_dir, limit=args.limit)
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
