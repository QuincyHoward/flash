# -*- coding: utf-8 -*-
"""所有场景本地 WSL 极短时间验证 + output_pro 模块顺带测试（2026-10-30）
═══════════════════════════════════════════════════════════════════════════

目的（背景：output_processors→output_pro 全仓改名迁移后）：
  1. 对 35 个注册场景逐一做本地验证 —— 端到端确认改名迁移无破坏；
  2. 顺带用 output_pro (FlashDataLoader) 逐场景加载运行产物，验证模块功能。

执行策略（分级，绝不触碰超算）：
  · WSL 场景 (24): CLI `run <scene> --mode wsl --tmax 1e-11 --json`
      —— 极短物理运行（编译缓存命中时约 20-60s/个）
  · hpc-only 场景 (11): 场景脚本直调本地生成档
      —— SNBOneCH → --stage generate；其余 → --generate-only
      （只生成输入 + 静态核验，不部署不提交，超算零接触）
  · 每个成功的 WSL 运行后: output_pro 加载最新 chk → dens/tele/nele 范围

产物:
  artifacts/scene-verify-20261030/results.json   （增量落盘）
  test/reports/scene_verify_20261030.md          （最终报告）

用法:
  python scripts/07_private_keep/scene_verify_all_20261030.py [--only name1,name2]
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
OUT_DIR = ROOT / "artifacts" / "scene-verify-20261030"
REPORT = ROOT / "test" / "reports" / "scene_verify_20261030.md"
OUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT.parent.mkdir(parents=True, exist_ok=True)

# hpc-only 场景 → 本地生成命令（脚本相对 ROOT）
HPC_LOCAL_GEN = {
    "SNBOneCH":   (["flash/scenarios/private/tracer/SNB/SNBOneCH/SNBOneCH.py"], ["--stage", "generate"]),
    "SNBOneCH_m": (["flash/scenarios/private/tracer/SNB/SNBOneCH_m/SNBOneCH_m.py"], ["--generate-only"]),
    "SNBOneCH_ml": (["flash/scenarios/private/tracer/SNB/SNBOneCH_ml/SNBOneCH_ml.py"], ["--generate-only"]),
    "SNBVTi1um":  (["flash/scenarios/private/tracer/SNB/SNBVTi1um/SNBVTi1um.py"], ["--generate-only"]),
    "SNBVTi1umx": (["flash/scenarios/private/tracer/SNB/SNBVTi1umx/SNBVTi1umx.py"], ["--generate-only"]),
    "SNBVTi2":    (["flash/scenarios/private/tracer/SNB/SNBVTi2/SNBVTi2.py"], ["--generate-only"]),
    "SNBVTi2_ml": (["flash/scenarios/private/tracer/SNB/SNBVTi2_ml/SNBVTi2_ml.py"], ["--generate-only"]),
    "SNBVTi2um":  (["flash/scenarios/private/tracer/SNB/SNBVTi2um/SNBVTi2um.py"], ["--generate-only"]),
    "SNBVTi2umx": (["flash/scenarios/private/tracer/SNB/SNBVTi2umx/SNBVTi2umx.py"], ["--generate-only"]),
    "SNBVTi3um":  (["flash/scenarios/private/tracer/SNB/SNBVTi3um/SNBVTi3um.py"], ["--generate-only"]),
    "SNBVTi3umx": (["flash/scenarios/private/tracer/SNB/SNBVTi3umx/SNBVTi3umx.py"], ["--generate-only"]),
}

# 全局锁文件防止并行误启
LOCK = OUT_DIR / ".running"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def parse_last_json(text: str) -> dict | None:
    """从 CLI 输出中提取最后一个完整 JSON 对象（场景会先打印日志再输出 JSON）。"""
    idx = text.rfind("\n{\n")
    if idx == -1:
        # JSON 可能顶行开始
        idx = text.rfind("\n{")
        if idx == -1:
            return None
    try:
        return json.loads(text[idx:].strip())
    except json.JSONDecodeError:
        pass
    # 兜底: 逐个 '{' 尝试
    for m in re.finditer(r"\{", text):
        try:
            return json.loads(text[m.start():])
        except json.JSONDecodeError:
            continue
    return None


def win_path_from_wsl(p: str) -> str:
    m = re.match(r"/mnt/([a-z])(/.*)", p)
    if m:
        return f"{m.group(1).upper()}:{m.group(2)}"
    return p


def find_output_dir(stdout: str, scene_name: str) -> Path | None:
    """从场景 stdout 提取输出目录 (多语言/多格式兼容)。"""
    pats = [
        r"Output files:\s+(\S+)",            # 引擎英文行 (WSL 路径)
        r"输出结果目录:\s*(.+)",               # 引擎中文行 (Windows 路径)
        r"输出文件目录:\s*(.+)",
        r"outputfiles[=:\s]+(\S+)",
    ]
    for pat in pats:
        m = re.findall(pat, stdout)
        if m:
            p = m[-1].strip().strip('"')
            p = win_path_from_wsl(p)
            if p.startswith("E:"):
                return Path(p)
    return None


def newest_hdf5(out_dir: Path, max_age_s: int = 3600):
    """取 out_dir 内最新 FLASH HDF5 文件 (chk 优先; 带不带 .h5 后缀均可)。"""
    import time as _t
    now = _t.time()
    cands = []

    def _add(f: Path):
        cands.append((f.stat().st_mtime, f))

    if out_dir and out_dir.exists():
        chk = sorted(out_dir.rglob("*hdf5_chk_*"))
        if not chk:
            chk = sorted(out_dir.rglob("*_hdf5_*"))
        if not chk:
            chk = sorted(out_dir.rglob("*.h5"))
        for f in chk:
            if f.is_file():
                _add(f)
    cands = [c for c in cands if now - c[0] < max_age_s]
    if not cands:
        return None
    cands.sort(key=lambda x: (x[1].name, x[0]))  # 取序号最大的 chk
    return cands[-1][1]


def test_output_pro(chk: Path) -> dict:
    """output_pro 模块实测: FlashDataLoader 加载 + 变量提取。"""
    sys.path.insert(0, str(ROOT))
    from flash.output_pro.loader import FlashDataLoader  # noqa: E402

    t0 = time.time()
    c = FlashDataLoader(chk).load(compute_derived=True)
    info: dict = {"file": str(chk), "load_s": round(time.time() - t0, 2)}
    for var in ("dens", "tele", "nele"):
        try:
            v = c.get(var)
            import numpy as np
            a = __import__("numpy").asarray(v, dtype=float)
            fin = a[__import__("numpy").isfinite(a)]
            info[var] = {
                "shape": list(a.shape),
                "min": float(fin.min()) if fin.size else None,
                "max": float(fin.max()) if fin.size else None,
            }
        except Exception as exc:  # noqa: BLE001
            info[var] = {"error": f"{type(exc).__name__}: {exc}"}
    return info


def run_cmd(cmd: list, timeout_s: int, log_path: Path) -> tuple[int, str]:
    with open(log_path, "w", encoding="utf-8", errors="replace") as rf:
        p = subprocess.run(cmd, cwd=ROOT, stdout=rf, stderr=subprocess.STDOUT,
                           encoding="utf-8", errors="replace", timeout=timeout_s)
        rc = p.returncode
    text = log_path.read_text(encoding="utf-8", errors="replace")
    return rc, text


def main() -> int:
    if LOCK.exists():
        print("[X] 已有实例在运行 (artifacts/scene-verify-20261030/.running)")
        return 2
    LOCK.write_text(str(time.time()))
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))

    results: dict = {}
    results_path = OUT_DIR / "results.json"
    try:
        # ── 场景清单 ──
        sys.path.insert(0, str(ROOT))
        from flash.scenarios.core.catalog import list_scenes
        scenes = list_scenes()
        log(f"共 {len(scenes)} 个注册场景")

        for name, desc, allowed in scenes:
            if only and name not in only:
                continue
            rec: dict = {"desc": desc, "allowed": list(allowed)}
            t0 = time.time()
            if "wsl" in allowed:
                # ── WSL 极短物理运行 ──
                cmd = [PY, "-m", "flash.scenarios", "run", name,
                       "--mode", "wsl", "--tmax", "1e-11", "--json"]
                lp = OUT_DIR / f"run_{name}.log"
                log(f"▶ WSL 运行 {name} ...")
                try:
                    rc, text = run_cmd(cmd, timeout_s=900, log_path=lp)
                except subprocess.TimeoutExpired:
                    rec.update(ok=False, reason="TIMEOUT(900s)", dur_s=round(time.time()-t0, 1))
                    results[name] = rec
                    _flush(results, results_path)
                    log(f"✗ {name} 超时")
                    continue
                j = parse_last_json(text) or {}
                rec["cli_ok"] = j.get("ok")
                rec["reason"] = str(j.get("reason") or "")[:200]
                rec["exit"] = rc
                # 输出目录: 优先 stats.run_dir (声明式场景), 再 stdout 正则
                out_dir = None
                stats = j.get("stats") or {}
                if stats.get("run_dir"):
                    out_dir = Path(stats["run_dir"])
                if out_dir is None or not out_dir.exists():
                    out_dir = find_output_dir(text, name) or out_dir
                rec["out_dir"] = str(out_dir) if out_dir else None
                # ── output_pro 顺带测试 ──
                if j.get("ok") or rc == 0:
                    chk = newest_hdf5(out_dir) if out_dir else None
                    if chk:
                        try:
                            rec["output_pro"] = test_output_pro(chk)
                        except Exception as exc:  # noqa: BLE001
                            rec["output_pro"] = {"error": f"{type(exc).__name__}: {exc}"}
                    else:
                        rec["output_pro"] = {"error": "未找到产物 HDF5"}
                rec["ok"] = bool(j.get("ok") or rc == 0)
            elif name in HPC_LOCAL_GEN:
                # ── hpc-only: 本地输入生成 + 静态核验 (不部署不提交) ──
                script, sargs = HPC_LOCAL_GEN[name]
                cmd = [PY, *script, *sargs]
                lp = OUT_DIR / f"gen_{name}.log"
                log(f"▶ 本地生成 {name} (hpc-only, --generate-only) ...")
                try:
                    rc, text = run_cmd(cmd, timeout_s=480, log_path=lp)
                except subprocess.TimeoutExpired:
                    rec.update(ok=False, reason="TIMEOUT(480s)", dur_s=round(time.time()-t0, 1))
                    results[name] = rec
                    _flush(results, results_path)
                    log(f"✗ {name} 超时")
                    continue
                ok = (rc == 0)
                reason = "" if ok else text[-300:]
                if not ok and "缺 SNB 覆盖 F90" in text:
                    # 本地保留层 (source/snb_package, 设计上不入库) 缺失 ——
                    # 预存在环境缺口, 非改名迁移回归; 生成链本身已跑到核验步
                    ok = None
                    reason = "ENV-GAP: SNB F90 本地保留层缺失 (source/snb_package, 见 README §本地保留)"
                rec.update(ok=ok, exit=rc, reason=reason)
            else:
                rec.update(ok=None, reason="无本地验证路径 (跳过)")
            rec["dur_s"] = round(time.time() - t0, 1)
            results[name] = rec
            _flush(results, results_path)
            mark = "✓" if rec.get("ok") else ("△" if rec.get("ok") is None else "✗")
            op = "output_pro✓" if isinstance(rec.get("output_pro"), dict) and "error" not in rec["output_pro"] else ""
            log(f"{mark} {name} ({rec['dur_s']}s) {op} {rec.get('reason','')[:60]}")
    finally:
        LOCK.unlink(missing_ok=True)

    write_report(results)
    n_ok = sum(1 for r in results.values() if r.get("ok"))
    n_skip = sum(1 for r in results.values() if r.get("ok") is None)
    n_fail = len(results) - n_ok - n_skip
    log(f"=== 完成: {n_ok} 成功 / {n_fail} 失败 / {n_skip} 跳过 ===")
    return 0 if n_fail == 0 else 1


def _flush(results: dict, path: Path) -> None:
    path.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")


def write_report(results: dict) -> None:
    lines = [
        "# 全场景本地 WSL 极短验证 + output_pro 测试报告",
        "",
        f"- 日期: 2026-10-30 21:0x–（增量写入）",
        "- 背景: output_processors → output_pro 全仓改名迁移后的端到端验证",
        "- WSL 场景: `--mode wsl --tmax 1e-11`（极短物理运行）；hpc-only: 本地 `--generate-only`/`--stage generate`（超算零接触）",
        "- output_pro 测试: FlashDataLoader 加载最新 chk → dens/tele/nele 提取",
        "",
        "| 场景 | 类型 | 结果 | 耗时(s) | output_pro | 备注 |",
        "|---|---|---|---|---|---|",
    ]
    for name, r in results.items():
        kind = "WSL" if "wsl" in r.get("allowed", []) else "hpc-gen"
        mark = "✓" if r.get("ok") else ("△ 跳过" if r.get("ok") is None else "✗")
        op = r.get("output_pro")
        if isinstance(op, dict) and "error" not in op:
            op_s = "✓"
        elif isinstance(op, dict):
            op_s = f"✗ {op['error'][:40]}"
        else:
            op_s = "—"
        lines.append(f"| {name} | {kind} | {mark} | {r.get('dur_s','?')} | {op_s} | {(r.get('reason') or '')[:50]} |")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
