#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""insitu_runner.py — hpc-insitu 模式编排（三模式统一，2026-10-22）
════════════════════════════════════════════════════════════════════════════

适用前提：场景驱动脚本**已经在超算上**（登录节点，用 .venv-hpc-nce/bin/python）。
与 hpc-remote 的本质区别：**绝不 SSH 自连**——所有 slurm 操作经 LocalExecutor
直接 subprocess 执行；所有重活（FLASH 运行、分析绘图）一律 sbatch 作业提交
到计算节点，登录节点只做轻量编排（脚本渲染 / 提交 / 轮询 / 文件移动）。

目录契约（与 runner.py runs_root 一致）：
  运行输出写 <FLASH_RUNS_DIR 或 包根兄弟目录>/flash_sim_runs/<scenario>/run_NNNNNN/
  （input/ 输入快照, output/ 回收产物, plots/ 分析图, logs/, state.json）
  flash_sim 包目录保持 git status 干净。

来源与复用:
  * 作业控制 → flash_run.remote.slurm_control（wait_for_job/run_job_chain 与
    hpc-remote 完全同一实现）
  * 回收策略 → flash_run.remote.fetch_policy（chk-only 单一来源；insitu 下
    "下载"退化为同文件系统 shutil 移动）
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from flash.flash_run.remote.slurm_control import (
    LocalExecutor,
    SlurmJobSpec,
    log,
    run_job_chain,
    sbatch_available,
)
# ★ 2026-10-24（B1）：原为 `from flash.scenarios.runner import ...`（经兼容壳
#   回到本包，形成 modes → scenarios → modes 环）。迁入执行层后改为**同包**导入，
#   环消失；`flash.scenarios.insitu_runner` 现仅为指向本模块的转发壳。
from .runner import allocate_run_id, detect_native_linux, run_id_name

# ── 超算登录节点探测与 python 解析 ───────────────────────

def is_hpc_login_node() -> bool:
    """保守判定当前是否 slurm 登录节点（仅供 --check-env 报告/告警）。

    ★ 模式切换必须显式 ``--mode hpc-insitu``，本函数不做隐式自动跳转。"""
    return detect_native_linux() and all(
        shutil.which(x) for x in ("sbatch", "sacct", "sinfo"))


def resolve_hpc_python() -> str:
    """insitu 场景的 python 解析: 项目 venv 优先（唯一事实源 env/venv_paths）。

    ★ 2026-10-24 修复：旧实现 ``parents[2]/.venv-hpc-nce`` 指向包目录
      （``.../flash/flash``），恒不存在；今天在超算能跑只是因为部署脚本
      注入了 ``FLASH_VENV_DIR``。一旦绕过安装脚本，旧逻辑会静默回落
      ``sys.executable`` → 登录节点 python3.6.8 → 报 ``ModuleNotFoundError: h5py``，
      **被误判为"没装包"而非"venv 找错"**。
      ⇒ 现在：找不到就 WARN 并校验解释器 ≥3.10，低于则明确拒绝。
    """
    from flash.flash_run.env.venv_paths import repo_root, venv_python

    py = venv_python(repo_root(), kind="hpc")
    if py is not None:
        return str(py)

    # 兜底：沿用当前解释器，但必须显式告警 + 版本闸门（不得静默）
    if sys.version_info < (3, 10):
        raise RuntimeError(
            f"未找到超算 venv（.venv-hpc-nce / FLASH_VENV_DIR），且当前解释器 "
            f"{sys.version.split()[0]} < 3.10，缺少 h5py/yt 依赖。\n"
            f"  修复：在 <TARGET>/.venv-hpc-nce 创建环境，或设置 FLASH_VENV_DIR。"
        )
    log(f"未找到超算 venv，回退当前解释器 {sys.executable}（版本 "
        f"{sys.version.split()[0]} ≥3.10）", "WARN")
    return sys.executable


# ── 规格 ─────────────────────────────────────────────────

@dataclass
class InsituSpec:
    """hpc-insitu 运行规格。"""
    name: str                       # 场景名（runs 子目录名）
    input_dir: Path                 # 输入文件目录（快照进 run_N/input）
    runs_dir: Path                  # 本场景 runs 目录（一般 = runs_root()/name）
    flash_home: str                 # FLASH 树（$HOME 绝对路径形式）
    objdir: str                     # FLASH 树内 obj 目录名
    basenm: str                     # 输出前缀（chk/plt 归属过滤用）
    jobs: List[SlurmJobSpec]        # 作业链（build/run/...，slurm_control 渲染）
    gates: Optional[Dict[str, Callable[[Any], bool]]] = None
    skip_first_if: Optional[Callable[[Any], bool]] = None
    analysis_cmd: str = ""          # 分析作业体（空 = 无分析作业）；重活必须走作业
    analysis_ntasks: int = 1
    with_plt: bool = False          # False = chk-only（fetch_policy 默认）
    log_names: Tuple[str, ...] = () # 额外回收的日志文件名（精确匹配）
    partition: str = ""
    nproc: int = 1


# ── 就地收集 ─────────────────────────────────────────────

def collect_local(objdir_path: str, out_dir: Path, basenm: str,
                  with_plt: bool = False, move: bool = True,
                  log_names: Tuple[str, ...] = ()) -> Tuple[List[str], Dict[str, int]]:
    """obj 目录 → run 输出目录的就地收集（fetch_policy chk-only 策略）。

    与 hpc-remote 的差别仅在传输层：同文件系统，"下载"= copy2(+可选 unlink
    源文件以省超算空间，与 SNB collect 后清理语义一致)。
    Returns: (collected_names, stats)
    """
    from flash.flash_run.remote.fetch_policy import select_fetch_files

    obj = Path(objdir_path)
    if not obj.is_dir():
        log(f"obj 目录不存在，跳过收集: {obj}", "WARN")
        return [], {"n_chk": 0, "n_picked": 0, "n_plt": 0, "n_fixed": 0,
                    "plt_skipped": 0}
    names = [p.name for p in obj.iterdir() if p.is_file()]
    picked, stats = select_fetch_files(names, basenm=basenm,
                                       log_names=log_names, with_plt=with_plt)
    out_dir.mkdir(parents=True, exist_ok=True)
    collected = []
    for n in picked:
        src = obj / n
        dst = out_dir / n
        try:
            shutil.copy2(src, dst)
            if move:
                src.unlink(missing_ok=True)
            collected.append(n)
        except OSError as e:
            log(f"收集失败 {n}: {e}", "WARN")
    log(f"就地收集 {len(collected)} 文件 → {out_dir} "
        f"(chk={stats['n_picked']}, plt 跳过={stats['plt_skipped']}, "
        f"fixed={stats['n_fixed']})", "OK")
    return collected, stats


# ── 主流程 ───────────────────────────────────────────────

def run_insitu(spec: Any, cfg: Optional[Dict[str, Any]] = None) -> bool:
    """hpc-insitu 主流程：备输入 → sbatch 作业链 → 就地收集 → 可选分析作业。

    Returns: True = 作业链与收集全部成功。
    """
    cfg = cfg or {}
    exe = LocalExecutor()

    print("\n[INSITU] 超算本地编排（无 SSH 自连，重活全走 sbatch）")
    print("-" * 60)
    if not sbatch_available(exe):
        log("当前环境无 sbatch/sacct —— hpc-insitu 模式只能在超算上运行", "ERROR")
        return False

    # 1) runs 目录 + run_id
    run_id = allocate_run_id(spec.runs_dir, spec.input_dir)
    run_dir = spec.runs_dir / run_id_name(run_id)
    in_dir, out_dir = run_dir / "input", run_dir / "output"
    plots_dir, logs_dir = run_dir / "plots", run_dir / "logs"
    for d in (in_dir, out_dir, plots_dir, logs_dir):
        d.mkdir(parents=True, exist_ok=True)
    log(f"run_id = {run_id:06d} → {run_dir}", "OK")

    # 2) 输入快照
    if Path(spec.input_dir).is_dir():
        for f in sorted(Path(spec.input_dir).iterdir()):
            if f.is_file() and not f.name.startswith("wsl_"):
                shutil.copy2(f, in_dir / f.name)

    # 3) 作业链（build/run/...；脚本写 runs 目录，FLASH 操作在 objdir）
    ok = run_job_chain(exe, list(spec.jobs), str(run_dir),
                       gates=spec.gates, skip_first_if=spec.skip_first_if)
    if not ok:
        _write_state(run_dir, spec, run_id, ok, note="作业链失败")
        return False

    # 4) 就地收集（FLASH 树 objdir → run output）
    objdir_path = f"{spec.flash_home}/{spec.objdir}"
    collected, _stats = collect_local(
        objdir_path, out_dir, spec.basenm, with_plt=spec.with_plt,
        move=bool(cfg.get("collect_move", True)), log_names=spec.log_names)

    # ★ 2026-10-24 修复（解耦计划 G6）：收集 0 个文件此前仍判成功
    #   （objdir 不存在只 WARN 返回 []），等于把"没有产物"报成跑通。
    if not collected:
        log("就地收集 0 个文件（objdir 缺失或产物前缀不匹配）—— 判定失败", "ERROR")
        _write_state(run_dir, spec, run_id, False, note="收集 0 文件")
        return False

    # 5) 可选分析作业（重活走 sbatch；登录节点不跑 matplotlib/h5py 大循环）
    if spec.analysis_cmd:
        py = resolve_hpc_python()
        ana = SlurmJobSpec(
            name="analysis", ntasks=spec.analysis_ntasks,
            partition=spec.partition,
            env_block=f'export FLASH_VENV_DIR="{Path(py).parent.parent}"',
            script=(f'{py} -c {spec.analysis_cmd!r} 2>&1 | tee {logs_dir}/analysis.log\n'
                    f'echo ANALYSIS_DONE'),
            marker="ANALYSIS_DONE",
            out_glob=f"{logs_dir}/analysis.log",
            timeout=cfg.get("analysis_timeout", 3600),
            poll=cfg.get("poll", 0))
        log("提交分析作业 (venv python)...", "STEP")
        ok = run_job_chain(exe, [ana], str(run_dir))
        if ok:
            for p in run_dir.glob("analysis_*.out"):
                shutil.copy2(p, logs_dir / p.name)

    # 6) 状态落盘
    _write_state(run_dir, spec, run_id, ok, collected=collected)
    log(f"insitu 完成: {run_dir}", "OK" if ok else "WARN")
    return ok


def _write_state(run_dir: Path, spec: Any, run_id: int, ok: bool,
                 collected: Optional[List[str]] = None,
                 note: str = "") -> None:
    state = {
        "mode": "hpc-insitu",
        "scenario": spec.name,
        "run_id": run_id,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "ok": ok,
        "collected": collected or [],
        "note": note,
    }
    try:
        (run_dir / "state.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:
        log(f"state.json 写入失败: {e}", "WARN")
