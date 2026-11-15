# -*- coding: utf-8 -*-
"""batch.control — 批量提交/轮询/收集与排序榜持久化（场景无关）
════════════════════════════════════════════════════════════════════════════

收编自 SandwichTxN/scripts/hpc_pf_batch.py（upload/submit/poll/collect，
2026-11-07/08 实测验证版）。全部基于 flash_run.remote 既有原语
（slurm_control / session / executors），零场景知识。

哨兵行兼容：新前缀 BATCH_ELAPSED/BATCH_STEPS 与旧前缀 PF_ELAPSED/PF_STEPS
均可解析（历史批次 collect 不回归）。
"""
from __future__ import annotations

import json
import re
import statistics
import time
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from flash.flash_run.remote.slurm_control import (
    job_state, latest_job_by_name, submit,
)

# 哨兵前缀：新旧双兼容
_ELAPSED_RES = (re.compile(r"BATCH_ELAPSED\s+(\S+)\s+(\d+)\s+rc=(\d+)"),
                re.compile(r"PF_ELAPSED\s+(\S+)\s+(\d+)\s+rc=(\d+)"))
_STEPS_RES = (re.compile(r"BATCH_STEPS\s+(\S+)\s+(\d+)"),
              re.compile(r"PF_STEPS\s+(\S+)\s+(\d+)"))


# ────────────────────────────────────────────────────────────────────
# JSON / 时间解析
# ────────────────────────────────────────────────────────────────────

def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8")


def load_json(path: Path, default=None):
    if not Path(path).is_file():
        return default
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def parse_slurm_time(s: str) -> int:
    """'02:14:33' / '1-02:14:33' / '...:45.175'（小数秒）→ 秒。"""
    if not s or s in ("N/A", "Unknown"):
        return 0
    days = 0
    if "-" in s:
        days, s = s.split("-", 1)
        try:
            days = int(days)
        except ValueError:
            days = 0
    parts = [int(float(x)) for x in s.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, sec = parts
    return days * 86400 + h * 3600 + m * 60 + sec


# ────────────────────────────────────────────────────────────────────
# 哨兵行解析（纯函数）
# ────────────────────────────────────────────────────────────────────

def parse_sentinels(out_text: str) -> tuple[Dict[str, dict], Dict[str, int]]:
    """作业 .out 文本 → (elapsed_map{tag:{elapsed_s,rc}}, steps_map{tag:int})。"""
    elapsed: Dict[str, dict] = {}
    steps: Dict[str, int] = {}
    for ln in out_text.splitlines():
        ln = ln.strip()
        for res in _ELAPSED_RES:
            m = res.match(ln)
            if m:
                elapsed[m.group(1)] = {"elapsed_s": int(m.group(2)),
                                       "rc": int(m.group(3))}
                break
        for res in _STEPS_RES:
            m = res.match(ln)
            if m:
                steps[m.group(1)] = int(m.group(2))
                break
    return elapsed, steps


def parse_batch_stats(out_text: str, logs: Mapping[str, str],
                      instances: Iterable[dict],
                      sacct_rows: Sequence[str] = (),
                      job_id: str = "", cores_per_node: int = 48) -> dict:
    """纯函数：哨兵行 + 每实例日志 → stats dict（与 leaderboard schema 对齐）。

    logs: {tag: flash_run.log 全文}（缺日志的实例跳过日志项）
    instances: [{tag, par_name, ntasks, ...}]（state.json 的 instances）
    """
    elapsed_map, steps_map = parse_sentinels(out_text)
    results: Dict[str, dict] = {}
    for inst in instances:
        tag = inst["tag"]
        rec = {"tag": tag, "ntasks": int(inst.get("ntasks", 1)),
               **{k: v for k, v in inst.items() if k not in ("tag", "ntasks")},
               **elapsed_map.get(tag, {})}
        rec["steps"] = steps_map.get(tag, 0)
        txt = logs.get(tag)
        if txt:
            steps = [int(m.group(1)) for m in
                     re.finditer(r"^\s*(\d+)\s+\d\.\d+E", txt, re.M)]
            if steps:
                rec["steps"] = max(steps)
            rec["finished"] = "reached max SimTime" in txt
            rec["abort"] = ("abort" in txt.lower() or
                            "Negative" in txt or "SIGSEGV" in txt)
        el = rec.get("elapsed_s")
        if el and rec["steps"]:
            rec["steps_per_s"] = round(rec["steps"] / el, 1)
        results[tag] = rec

    ok = [r for r in results.values()
          if r.get("steps") and r.get("steps_per_s") and r.get("rc") == 0]
    rates = [r["steps_per_s"] for r in ok]
    summary = {
        "n_ok": len(ok), "n_total": len(results),
        "per_instance_best": max(rates) if rates else None,
        "per_instance_median": round(statistics.median(rates), 1) if rates else None,
        "per_instance_worst": min(rates) if rates else None,
        "aggregate_steps_per_s": round(sum(rates), 1) if rates else None,
    }
    # sacct 主作业行 CPU 利用率
    util = None
    for row in sacct_rows:
        cols = row.split("|")
        if cols and cols[0] == str(job_id) and len(cols) > 5:
            el = parse_slurm_time(cols[3])
            tc = parse_slurm_time(cols[4])
            alloc = int(cols[5]) if cols[5].isdigit() else 0
            if el and alloc:
                util = round(100.0 * tc / (alloc * el), 1)
            break
    summary["cpu_utilization_pct"] = util
    if cores_per_node and rates:
        summary["occupancy_pct"] = round(
            100.0 * sum(r["ntasks"] for r in results.values()) / cores_per_node, 1)
    el_list = [r.get("elapsed_s") for r in results.values() if r.get("elapsed_s")]
    return {
        "results": results,
        "summary": summary,
        "sacct": list(sacct_rows),
        "job_elapsed_hint": max(el_list) if el_list else None,
    }


# ────────────────────────────────────────────────────────────────────
# 远程操作（upload / submit / poll / probe / cancel / collect）
# ────────────────────────────────────────────────────────────────────

def upload_batch_inputs(session, local_dir: Path, remote_input: str) -> int:
    """上传批次输入目录全部文件 → 远端。"""
    session.run(f"mkdir -p {remote_input}", timeout=60)
    n = 0
    for f in sorted(p for p in Path(local_dir).iterdir() if p.is_file()):
        if not session.upload(str(f), f"{remote_input}/{f.name}"):
            raise RuntimeError(f"上传失败: {f.name}")
        n += 1
    return n


def submit_batch(exe, script_remote: str, job_name: str,
                 workdir: str = "") -> str:
    """sbatch 提交 + 按作业名回查兜底（提交超时但已入队）。"""
    wd = workdir or script_remote.rsplit("/", 1)[0]
    out, err, _rc = exe.run(f"cd {wd} && sbatch {script_remote} 2>&1",
                            timeout=300)
    blob = (out or "") + (err or "")
    m = re.search(r"Submitted batch job (\d+)", blob)
    job_id = m.group(1) if m else latest_job_by_name(exe, job_name)
    if not job_id:
        raise RuntimeError(f"提交失败（未解析出 JobID）: {blob.strip()[-400:]}")
    return job_id


def poll_batch(exe, job_id: str) -> str:
    return job_state(exe, job_id) or "(无记录)"


def cancel_batch(exe, job_id: str) -> None:
    exe.run(f"scancel {job_id} 2>&1", timeout=60)


def probe_batch(exe, out_glob: str, elapsed_marker: str = "BATCH_ELAPSED",
                legacy_marker: str = "PF_ELAPSED",
                steps_marker: str = "BATCH_STEPS",
                legacy_steps: str = "PF_STEPS") -> dict:
    """中途探针：远端抓作业 .out 哨兵行 → 完成数/部分聚合吞吐。

    早停钩子用；PENDING/零进度返回 n_done=0。
    partial_aggregate = Σ(steps_i/elapsed_i)（已完成实例）——与 collect 的
    聚合吞吐同口径，供"显著低于当前最优即终止"判据。
    """
    cmd = (f'O=$(ls {out_glob} 2>/dev/null | head -1); '
           f'[ -n "$O" ] && grep -hE "({elapsed_marker}|{legacy_marker}|'
           f'{steps_marker}|{legacy_steps})" $O || echo NOFILE')
    out, _e, _rc = exe.run(cmd, timeout=60)
    elapsed: dict[str, int] = {}
    steps: dict[str, int] = {}
    for ln in (out or "").splitlines():
        ln = ln.strip()
        m = re.match(rf"(?:{elapsed_marker}|{legacy_marker})\s+(\S+)\s+(\d+)\s+rc=(\d+)", ln)
        if m:
            elapsed[m.group(1)] = int(m.group(2))
            continue
        m = re.match(rf"(?:{steps_marker}|{legacy_steps})\s+(\S+)\s+(\d+)", ln)
        if m:
            steps[m.group(1)] = int(m.group(2))
    partial = 0.0
    for tag, el in elapsed.items():
        if tag in steps and el > 0:
            partial += steps[tag] / el
    return {"n_done": len(elapsed), "elapsed": elapsed, "steps": steps,
            "partial_aggregate": round(partial, 1) if elapsed else 0.0}


def collect_batch(exe, session, state: Mapping,
                  local_dir: Path) -> dict:
    """下载作业 .out 与每实例日志 → 解析 → stats dict（含 sacct）。

    state 需含: batch_id/job_id/shared{out,log}/instances/mode/markers(可选)/cores_per_node
    """
    bid = state["batch_id"]
    job_id = str(state["job_id"])
    shared = state["shared"]
    instances = state["instances"]
    markers = state.get("markers", {})
    elapsed_marker = markers.get("elapsed", "BATCH_ELAPSED")
    steps_marker = markers.get("steps", "BATCH_STEPS")

    dl = Path(local_dir)
    dl.mkdir(parents=True, exist_ok=True)
    job_name = state.get("job_name", f"batch_{bid}")

    sacct_fmt = ("JobID,JobName,State,Elapsed,TotalCPU,AllocCPUS,"
                 "MaxRSS,NodeList")
    out, _e, _rc = exe.run(f"sacct -j {job_id} --format={sacct_fmt} "
                           f"--noheader -P 2>/dev/null", timeout=60)
    sacct_rows = [r for r in (out or "").strip().splitlines() if r.strip()]

    # 1) 下载作业 .out
    out_blob, _e, _rc = session.run(
        f"ls -1 {shared['log']}/{job_name}*_{job_id}.out 2>/dev/null",
        timeout=30)
    out_text = ""
    for rpath in [l.strip() for l in (out_blob or "").splitlines() if l.strip()]:
        fname = rpath.rsplit("/", 1)[-1]
        if session.download(rpath, str(dl / fname)):
            out_text = (dl / fname).read_text(encoding="utf-8",
                                              errors="replace")
            print(f"  [collect] {fname}")

    # 2) 下载每实例日志
    logs: Dict[str, str] = {}
    log_name = state.get("log_name", "flash_run.log")
    for inst in instances:
        tag = inst["tag"]
        rp = f"{shared['out']}/{tag}/{log_name}"
        lp = dl / f"{log_name.rsplit('.', 1)[0]}_{tag}.log"
        if session.download(rp, str(lp)):
            logs[tag] = lp.read_text(encoding="utf-8", errors="replace")
            print(f"  [collect] {lp.name}")

    stats = parse_batch_stats(out_text, logs, instances, sacct_rows,
                              job_id=job_id,
                              cores_per_node=int(state.get("cores_per_node", 48)))
    stats.update({"batch_id": bid, "job_id": job_id,
                  "mode": state.get("mode", "conc"),
                  "instances": list(instances)})
    stats_path = dl.parent / "stats.json"
    save_json(stats_path, stats)
    print(f"[collect] 聚合吞吐={stats['summary']['aggregate_steps_per_s']} 步/s  "
          f"per-instance best/median/worst = "
          f"{stats['summary']['per_instance_best']}/"
          f"{stats['summary']['per_instance_median']}/"
          f"{stats['summary']['per_instance_worst']}  "
          f"完成={stats['summary']['n_ok']}/{stats['summary']['n_total']}")
    print(f"[collect] stats.json -> {stats_path}")
    return stats


# ────────────────────────────────────────────────────────────────────
# 排序榜（追加式；node_value 主排序）
# ────────────────────────────────────────────────────────────────────

def merge_leaderboard(path: Path, entry: dict) -> dict:
    """追加 entry → 按 node_value 排序 → 维护 best_* 汇总。只追加不改写历史。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lb = load_json(path, default={"entries": []}) or {"entries": []}
    lb.setdefault("entries", []).append(entry)
    lb["entries"].sort(key=lambda e: -(e.get("node_value") or 0))
    lb["best_node_value"] = lb["entries"][0] if lb["entries"] else None
    by_inst = sorted(lb["entries"],
                     key=lambda e: -(e.get("per_instance_best") or 0))
    lb["best_per_instance"] = by_inst[0] if by_inst else None
    save_json(path, lb)
    print(f"[leaderboard] 已更新 -> {path}")
    for e in lb["entries"][:3]:
        tag = "实测" if e.get("aggregate_steps_per_s") else "估值"
        print(f"    {e.get('node_value')} 步/s [{tag}]  "
              f"{e.get('batch_id')}: {e.get('config')}")
    pi = lb["best_per_instance"]
    if pi:
        print(f"[leaderboard] per-instance 最佳: "
              f"{pi.get('per_instance_best')} 步/s ({pi.get('batch_id')})")
    return lb


def stats_to_leaderboard_entry(stats: dict, *, plan: str = "",
                               cores_per_node: int = 48) -> dict:
    """stats dict → leaderboard entry（node_value 主排序字段齐备）。"""
    s = stats["summary"]
    nts_set = sorted({r["ntasks"] for r in stats["results"].values()})
    if len(nts_set) == 1:
        fit = max(cores_per_node // nts_set[0], 1)
        node_value_est = round((s["per_instance_best"] or 0) * fit, 1)
        cfg = (f"{s['n_total']} inst × {nts_set[0]} rank (可容 {fit} 个), "
               f"mode={stats.get('mode', 'conc')}")
    else:
        node_value_est = None
        cfg = (f"{s['n_total']} inst × {nts_set} rank, "
               f"mode={stats.get('mode', 'conc')}")
    return {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "batch_id": stats.get("batch_id"),
        "job_id": stats.get("job_id"),
        "plan": plan or None,
        "config": cfg,
        "per_instance_best": s["per_instance_best"],
        "per_instance_median": s["per_instance_median"],
        "per_instance_worst": s["per_instance_worst"],
        "aggregate_steps_per_s": s["aggregate_steps_per_s"],
        "node_value_est": node_value_est,
        "node_value": s["aggregate_steps_per_s"] or node_value_est,
        "cpu_utilization_pct": s.get("cpu_utilization_pct"),
    }
