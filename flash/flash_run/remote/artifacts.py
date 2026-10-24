"""产物回收 —— `fetch_policy` 的唯一执行器
═════════════════════════════════════════════════════════════════════

★ 2026-10-24（解耦计划 B1）：`fetch_policy` 是「该拿哪些文件」的唯一策略源，
但它此前**没有任何统一执行点** —— `HpcRunner.download()` 手写 3 个固定
文件、`insitu_runner.collect_local()` 另一套、引擎又一套 glob。结果
hpc-remote 模式下 chk 全部留在超算（G4）。

本模块把「策略」与「传输」拼起来：策略仍只来自 `fetch_policy`，
传输交给 `CommandExecutor`（本地 copy2 / wsl cp / sftp），
四个 target 共用同一条路径。
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from .fetch_policy import select_fetch_files

__all__ = ["fetch_artifacts"]


def fetch_artifacts(
    exe,
    remote_dir: str,
    local_dir: Path,
    *,
    basenm: str,
    with_plt: bool = False,
    frames: int = 0,
    log_names: Sequence[str] = (),
    move: bool = False,
) -> Tuple[List[str], Dict[str, int]]:
    """按 `fetch_policy` 选择并回收产物。

    Args:
        exe: ``CommandExecutor``（提供 listdir / copy_from / run）。
        remote_dir: 产物所在目录（本地 target 即本地路径）。
        local_dir: 落地目录。
        basenm: 输出前缀（chk/plt 归属过滤）。
        with_plt: False=chk-only（fetch_policy 默认）。
        frames: chk 抽帧数，0=全量。
        log_names: 额外精确匹配的日志名。
        move: True 时回收后删除远端（insitu 就地收集语义）。

    Returns:
        (collected_names, stats)。stats 额外含 `n_collected` / `n_failed`。
    """
    local_dir = Path(local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)

    names = exe.listdir(remote_dir)
    if not names:
        return [], {"n_chk": 0, "n_picked": 0, "n_plt": 0, "n_fixed": 0,
                    "plt_skipped": 0, "n_collected": 0, "n_failed": 0,
                    "reason": "remote_dir_empty"}

    picked, stats = select_fetch_files(
        names, basenm=basenm, log_names=tuple(log_names),
        with_plt=with_plt, frames=frames,
    )

    collected: List[str] = []
    failed: List[str] = []
    base = remote_dir.rstrip("/")
    for name in picked:
        remote_path = f"{base}/{name}"
        if exe.copy_from(remote_path, local_dir / name):
            collected.append(name)
            if move:
                exe.run(f"rm -f '{remote_path}'", timeout=60)
        else:
            failed.append(name)

    stats = dict(stats)
    stats["n_collected"] = len(collected)
    stats["n_failed"] = len(failed)
    return collected, stats
