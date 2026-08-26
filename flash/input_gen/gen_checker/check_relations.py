#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_relations.py — FLASH 文件内在关联检查器（主脚本）
════════════════════════════════════════════════════════

在"文件是否存在"（checker.py / DependencyChecker）之上，进一步校验 7 个关键
文件之间的**内容一致性**。文件都在但彼此矛盾，FLASH 仍会编译/运行失败。

内置 14 条规则（分类见 GEN_CHECKER_GUIDE「检查项的内在关联」）：

  A. 文件级引用（rules_reference）
      1  .par 引用的 .cn4 必须存在于磁盘
      2  .par 引用的 .cn4 必须在 Config 的 DATAFILES 声明
      3  Config 需定义 .par 用到的表绑定 PARAMETER
  B. 参数级一致性（rules_parameter）
      4  .par 的 sim_* 参数需在 Config 有 PARAMETER 定义
      5  Simulation_data.F90 变量与 Simulation_init.F90 读取对应
      6  .par 的 sim_* 键与 Simulation_init.F90 读取键一致
  C. 维度/光束/脉冲（rules_dimension）
      7  维度一致性（.par 网格参数 vs setup flag）
      8  光束数目一致性（ed_numberOfBeams vs ed_lensX_*/ed_targetX_*）
      9  脉冲-光束绑定（ed_pulseNumber_i 在 ed_numberOfPulses 内）
     10  脉冲组数上限（ed_numberOfSections_* 超 20 → setup 需 ed_maxPulseSections）
     11  靶/透镜位置在仿真域内
  D. 脚本级装配（rules_script）
     12  run_flash.sh 的 PAR_FILE 与磁盘 .par 文件名一致
     13  setup 的 species= 与 Config 的 SPECIES 一致
     14  Makefile 引用的 .o 与存在的 Simulation_*.F90 对应

CLI 用法:
  python check_relations.py <仿真目录> [--verbose] [--rule 规则id] [--summary-only]
  python check_relations.py <目录> --rules            # 列出所有规则

Python API:
  from flash.input_gen.gen_checker import RelationChecker
  rc = RelationChecker("/path/to/sim_dir")
  results = rc.run_all()          # List[RelationResult]
  print(rc.summary())             # 文本报告
  ok = rc.all_passed()            # bool，是否有失败项

──────────────────────────────────────────────────────
可扩展性
──────────────────────────────────────────────────────
采用注册式规则引擎：
  - 每条规则是一个 @relation_rule(id, name) 装饰的函数，注册进 relations.REGISTRY；
  - 新增规则 → 在 relations/ 下加一个模块（或往现有模块加函数）并在
    relations/__init__.py 末尾 import 即可，**无需修改本主脚本**；
  - 规则共享的解析结果缓存在 RelationContext（relations/_core.py），避免重复解析。

详见 GEN_CHECKER_GUIDE「如何扩展自定义关联」。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional

# 支持两种导入方式：
#   1) 作为包的一部分：`from flash.input_gen.gen_checker import RelationChecker`
#   2) 直接运行脚本：  `python check_relations.py <dir>`（__package__ 为空）
if __package__ in (None, ""):
    # 向上找到 flash 包根（含 pyproject.toml 的目录），插入 sys.path
    _root = Path(__file__).resolve()
    for _ in range(12):
        if (_root / "pyproject.toml").exists():
            break
        _root = _root.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from flash.input_gen.gen_checker.relations import REGISTRY, RelationContext, RelationResult
else:
    from .relations import REGISTRY, RelationContext, RelationResult

__all__ = ["RelationChecker", "RelationResult", "RelationContext", "REGISTRY"]


class RelationChecker:
    """FLASH 文件内在关联检查器。

    Args:
        sim_dir: 仿真目录（含 .par / Config / Makefile / Simulation_*.F90 / *.cn4 / 脚本）
        verbose: 是否在 summary 里输出 details

    Example:
        >>> rc = RelationChecker("flash/scenarios/.../flash_input")
        >>> results = rc.run_all()
        >>> print(rc.summary())
    """

    def __init__(self, sim_dir, verbose: bool = False):
        self.sim_dir = Path(sim_dir)
        self.verbose = verbose
        self._results: List[RelationResult] = []

    # ── 规则执行 ────────────────────────────────────
    def run_all(self, rule_ids: Optional[List[str]] = None) -> List[RelationResult]:
        """执行全部（或指定）规则。

        Args:
            rule_ids: 若给则只跑这些规则 id；None 跑全部。

        Returns:
            按 REGISTRY 顺序排列的 RelationResult 列表。
        """
        ctx = RelationContext(self.sim_dir, verbose=self.verbose)
        self._results = []
        for rid, fn in REGISTRY.items():
            if rule_ids and rid not in rule_ids:
                continue
            try:
                self._results.append(fn(ctx))
            except Exception as exc:  # 规则内部异常不阻断整体
                self._results.append(RelationResult(
                    rule_id=rid,
                    name=getattr(fn, "rule_name", rid),
                    status=False,
                    message=f"规则执行异常: {exc!r}",
                    details={"error": str(exc)},
                ))
        return self._results

    def results(self) -> List[RelationResult]:
        return self._results

    # ── 汇总判定 ────────────────────────────────────
    def failed(self) -> List[RelationResult]:
        """返回所有 status is False 的结果。"""
        return [r for r in self._results if r.status is False]

    def all_passed(self) -> bool:
        """是否所有已执行规则均通过（无失败项；跳过/通过皆可）。"""
        return not self.failed()

    # ── 报告 ────────────────────────────────────────
    def summary(self) -> str:
        """生成文本报告（含每项状态与失败明细）。"""
        lines: List[str] = []
        lines.append("=" * 62)
        lines.append("FLASH 文件内在关联检查报告 (check_relations)")
        lines.append(f"  目录: {self.sim_dir}")
        lines.append("=" * 62)
        if not self._results:
            lines.append("  (尚未执行规则，请先调用 run_all())")
            return "\n".join(lines)

        n_pass = n_fail = n_skip = 0
        for r in self._results:
            if r.status is True:
                flag, n_pass = "OK", n_pass + 1
            elif r.status is None:
                flag, n_skip = "--", n_skip + 1
            else:
                flag, n_fail = "FAIL", n_fail + 1
            lines.append(f"  [{flag}] {r.rule_id}: {r.message}")
            if self.verbose and r.details:
                lines.append(f"         details: {r.details}")
        lines.append("-" * 62)
        lines.append(f"  通过 {n_pass} / 失败 {n_fail} / 跳过 {n_skip} / 共 {len(self._results)}")
        lines.append("=" * 62)
        return "\n".join(lines)


def _list_rules() -> str:
    """列出所有已注册规则。"""
    lines = ["已注册的关联检查规则:"]
    for rid, fn in REGISTRY.items():
        lines.append(f"  - {rid}: {getattr(fn, 'rule_name', rid)}")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI 入口。

    Returns:
        0=全部通过/有跳过; 1=存在失败项。
    """
    ap = argparse.ArgumentParser(
        prog="check_relations",
        description="FLASH 文件内在关联检查器",
    )
    ap.add_argument("sim_dir", nargs="?", help="仿真目录路径")
    ap.add_argument("--verbose", action="store_true", help="输出 details")
    ap.add_argument("--rule", action="append", help="只跑指定规则 id（可多次）")
    ap.add_argument("--rules", action="store_true", help="仅列出所有规则")
    ap.add_argument("--summary-only", action="store_true",
                    help="只打印结论行，不打印逐项")
    args = ap.parse_args(argv)

    if args.rules:
        print(_list_rules())
        return 0
    if not args.sim_dir:
        ap.error("需要提供仿真目录路径，或用 --rules 查看规则列表")
        return 2

    rc = RelationChecker(args.sim_dir, verbose=args.verbose)
    rc.run_all(rule_ids=args.rule)
    report = rc.summary()
    if args.summary_only:
        # 只打印总结行
        for ln in report.splitlines():
            if ln.startswith("  通过"):
                print(ln)
    else:
        print(report)

    if not rc.all_passed():
        print("\n存在失败项，请检查上方 FAIL 规则。")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
