# -*- coding: utf-8 -*-
"""chk-only 下载策略 —— 全场景唯一来源（single source of truth）。

★★★ 2026-09-16 用户定案：**所有场景**（SNB 及非 SNB 通用场景）的远端结果
下载默认 **只取 chk，不取 plt**；plt 必须显式 opt-in（--with-plt / with_plt=True）。

依据（SNBVTi2 / SNBVTi2_ml 实测，2026-09-16）：
  - 分析链 04_analyze_plots.py 只读 chk + 运行日志，plt 全程未被消费；
  - 体积：plt 单文件 ~2.7 MB vs chk ~14.2 MB —— SNBVTi2 一次 16 ns run
    228 个 plt ≈ 638 MB 纯冗余流量/磁盘；
  - chk-only + 大文件摊薄 SFTP 握手开销后，400 帧聚合下载实测 10.69 MB/s。

策略（select_fetch_files 四步）：
  1. 归属过滤：只考虑 basenm 前缀 / wsl_run_ 前缀 / log_names 精确命名的文件；
  2. 三分类：`*_hdf5_chk_*` → chk；`*_hdf5_plt_*`（含 forced_hdf5_plt_）→ plt；
     其余（运行日志 / .dat 等小文件）→ fixed，恒保留；
  3. 抽帧：frames>0 且 chk 超限时按「等间隔 + 首尾必取」抽稀（索引确定可复现）；
  4. with_plt=False（默认）⇒ plt 全部跳过并计数上报。

消费方（改策略只改本文件）：
  - SNB 长跑管线 03_run_16ns_pipeline.py（SNBOneCH_ml / SNBVTi2 / SNBVTi2_ml）
  - _fetch_incremental.py（SNBVTi2 / SNBVTi2_ml）
  - SNBOneCH_ml.py run_hpc collect；SNBtest t001 run_snb_hpc.py collect_outputs
  - ch_center download_hdf5_to_local；demo_hpc download_all_outputs
  - flash_run.remote.remote_deploy.download_results
  （独立脚本经 importlib 按文件路径加载本模块，避免 import flash 包副作用；
    包内模块用 `from flash.flash_run.remote.fetch_policy import ...`。）
"""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

# ★ 策略常量：chk-only 为全场景默认（勿在消费方另行硬编码决策）
CHK_ONLY_DEFAULT = True


def is_chk(name: str) -> bool:
    """FLASH chk 输出（<basenm>hdf5_chk_NNNN）。"""
    return "_hdf5_chk_" in name


def is_plt(name: str) -> bool:
    """FLASH plt 输出（<basenm>hdf5_plt_NNNN / forced_hdf5_plt_NNNN）。"""
    return "_hdf5_plt_" in name


def classify_names(
    names: Sequence[str],
    basenm: str = "",
    log_names: Sequence[str] = (),
    extra_prefixes: Sequence[str] = ("wsl_run_",),
) -> Tuple[List[str], List[str], List[str]]:
    """按归属过滤 + 三分类 → (chks, plts, fixed)，各自排序。

    fixed = 运行日志 / .dat 等非 HDF5 小文件：体积小、日志/定标可能要用，
    **恒保留**（与 plt 的"默认丢弃"不同）。
    """
    logs = {x for x in log_names if x}
    prefixes = tuple(extra_prefixes) + ((basenm,) if basenm else ())
    chks: List[str] = []
    plts: List[str] = []
    fixed: List[str] = []
    for n in names:
        if prefixes and not n.startswith(prefixes) and n not in logs:
            continue
        if is_chk(n):
            chks.append(n)
        elif is_plt(n):
            plts.append(n)
        else:
            fixed.append(n)
    return sorted(chks), sorted(plts), sorted(fixed)


def pick_frames(chks: Sequence[str], frames: int) -> List[str]:
    """等间隔抽帧（首尾必取）；frames<=0 或未超限时原样返回。

    抽帧索引 = round(i*(n-1)/(frames-1)) —— 确定性公式，重跑可复现。
    注意：长跑**中途**同步勿抽帧（n 增长 ⇒ 索引漂移 ⇒ 幂等失效），
    见 _fetch_incremental.py docstring。
    """
    if frames and frames > 0 and len(chks) > frames:
        idx = sorted({round(i * (len(chks) - 1) / (frames - 1))
                      for i in range(frames)})
        return [chks[i] for i in idx]
    return list(chks)


def select_fetch_files(
    names: Sequence[str],
    basenm: str,
    log_names: Sequence[str] = (),
    with_plt: bool = False,
    frames: int = 0,
) -> Tuple[List[str], Dict[str, int]]:
    """★ 唯一下载选择入口。返回 (picked_names, stats)。

    Args:
        names: 远端目录全部文件名（如 L.remote_list(rm, obj) 返回的列表）。
        basenm: 本 run 输出前缀（如 L.M.BASENM）。
        log_names: 额外精确匹配的日志名（如 wsl_run_xxx.log / L.M.LOG_FILE）。
        with_plt: False（默认）= chk-only；True = 连 plt 一起下载。
        frames: chk 抽帧数；0/负 = 全量。

    Returns:
        (picked, stats)。stats 键：n_chk / n_picked / n_plt / n_fixed /
        plt_skipped（被 chk-only 策略丢弃的 plt 数，供日志上报）。
    """
    chks, plts, fixed = classify_names(names, basenm=basenm, log_names=log_names)
    picked_chks = pick_frames(chks, frames)
    picked = list(picked_chks) + (list(plts) if with_plt else []) + list(fixed)
    stats: Dict[str, int] = {
        "n_chk": len(chks),
        "n_picked": len(picked_chks),
        "n_plt": len(plts),
        "n_fixed": len(fixed),
        "plt_skipped": 0 if with_plt else len(plts),
    }
    return picked, stats


def load_policy_module():
    """供独立脚本按文件路径加载本模块（不 import flash 包，零副作用）。

    用法（独立脚本内）：
        _fp = _load_fetch_policy()   # 本函数由消费方内联复制为 _load_fetch_policy
    说明：本函数保留在模块内仅为文档/单测用途；独立脚本请内联同款 10 行
    loader（见各消费方），因为调用本函数前必须先能找到本模块 —— 鸡生蛋。
    """
    import importlib.util
    from pathlib import Path

    for p in Path(__file__).resolve().parents:
        f = p / "flash" / "flash_run" / "remote" / "fetch_policy.py"
        if f.is_file():
            spec = importlib.util.spec_from_file_location("_fetch_policy", f)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise ImportError("fetch_policy.py 未找到")
