"""报告目录保留策略 —— 每类报告只留最新几批。

为什么需要它
------------
报告文件名带时间戳（``audit_all.<ts>.md``），所以**每跑一次就多一份**。
跑一遍全流程 + 几轮测试后，``outputs/reports/`` 会迅速膨胀
（实测一次测试套件就能新增十多个文件），真正想看的"最新结论"被淹没。
而 **固定名**报告（``zeff_inventory.*`` / ``type_conflict.*``）每次覆盖，
本来就不会堆积。

纪律
----
1. **只删时间戳批次里的旧文件** —— 从不删"最新一批"，也从不删固定名报告。
2. 一次运行的 ``csv`` / ``json`` / ``md`` 三份共享同一个时间戳，**同进同出**。
3. ``dry_run=True`` 只列不删（默认给批处理用 ``keep=1``）。

不做的事
--------
* 不碰 ``outputs/{h5,plots,logs}`` —— 那些是产物，不是报告。
* 不做"按大小淘汰" —— 时间戳顺序就是生成顺序，语义明确。
"""

from __future__ import annotations

import collections
from pathlib import Path

from . import config

__all__ = ["REPORT_PREFIXES", "prune_reports", "list_report_batches"]

#: 带时间戳的"批次型"报告前缀。固定名报告不参与保留策略。
REPORT_PREFIXES = ("audit_all.", "inventory.", "convert_all.", "plot_all.",
                   "identify.", "infer_unknown.")

_EXTS = (".csv", ".json", ".md")


def _batch_of(name: str, prefix: str) -> str:
    """从文件名抽出**批次 id**。

    ``audit_all.20260914T152830.md`` → ``audit_all.20260914T152830``
    固定名报告（``identify.<ts>`` 缺失时）返回前缀本身。
    """
    rest = name[len(prefix):]
    ts = rest.split(".")[0]
    return prefix + ts


def list_report_batches(outdir: str | Path | None = None) -> dict[str, list[list[Path]]]:
    """返回 ``{report_kind: [[batch_1_files], [batch_2_files], ...]}``（按时间升序）。

    ``report_kind`` 是前缀去掉末尾点（如 ``audit_all``）。
    """
    od = Path(outdir) if outdir else config.REPORTS_DIR
    if not od.is_dir():
        return {}
    groups: dict[str, dict[str, list[Path]]] = collections.defaultdict(
        lambda: collections.defaultdict(list))
    for f in sorted(od.iterdir(), key=lambda p: p.name):
        if not f.is_file() or f.suffix.lower() not in _EXTS:
            continue
        for pre in REPORT_PREFIXES:
            if f.name.startswith(pre):
                groups[pre.rstrip(".")][_batch_of(f.name, pre)].append(f)
                break
    return {kind: [groups[kind][b] for b in sorted(groups[kind])]
            for kind in sorted(groups)}


def prune_reports(*, outdir: str | Path | None = None, keep: int = 1,
                  dry_run: bool = False) -> dict:
    """每类报告只保留**最新 keep 批**；返回 ``{kind: {kept, removed}}``。"""
    od = Path(outdir) if outdir else config.REPORTS_DIR
    n_keep = max(keep, 1)
    out: dict[str, dict] = {}
    n_rm = 0
    for kind, batches in list_report_batches(od).items():
        kept = [f for b in batches[-n_keep:] for f in b]
        removed = [f for b in batches[:-n_keep] for f in b]
        if not dry_run:
            for f in removed:
                f.unlink(missing_ok=True)
        n_rm += len(removed)
        out[kind] = {"kept": sorted(f.name for f in kept),
                     "removed": sorted(f.name for f in removed)}

    tag = "(dry-run)" if dry_run else ""
    print(f"报告保留策略{tag}: 每类保留最新 {n_keep} 批，"
          f"{'将' if dry_run else ''}删除 {n_rm} 个文件")
    for k, v in out.items():
        if v["removed"]:
            print(f"  {k:14s} 删 {len(v['removed']):3d} 留 {len(v['kept']):3d}")
    if not out:
        print("  （未发现批次型报告）")
    return out
