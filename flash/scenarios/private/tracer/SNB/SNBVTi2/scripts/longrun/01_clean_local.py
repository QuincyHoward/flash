# -*- coding: utf-8 -*-
"""01_clean_local.py — 清空本地 FLASH 输入/输出（默认 dry-run）。

★★ 安全设计（必读）
====================
本脚本**只删"可再生/产物"**，绝不删"源头资产"：

| 目标 | 处理 | 理由 |
|---|---|---|
| `flash_output/**` | **删** | 仿真产物, 全部可再生 |
| `flash_input/` 内的 cn4 表 / *.F90 / Config / Makefile / par 模板 | **保护** | ★ 场景源头资产, 删了要重建整个场景 |
| `flash_input/pre_diag_*.png` | **删** | 预诊断图, 可重生成 |
| `flash_input/run_flash.sh` | **保护** | 运行脚本 |
| `__pycache__/` | **删** | 纯缓存 |
| `coretest_*.sh`（远端产物残留） | **删** | 产物 |
| `*.py` / `*.md` / `scripts/` / `tools_local/` / `docs/` | **保护** | 代码与文档 |

用法：
    python 01_clean_local.py                 # 只列清单（dry-run，默认）
    python 01_clean_local.py --apply         # 真正执行（送回收站）
    python 01_clean_local.py --apply --include-analysis
                                             # 连同绘图产物一起清
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _longrun_lib import (  # noqa: E402
    FLASH_IN, FLASH_OUT, SCEN_DIR, SafeDeleteError,
    human, log, print_inventory, safe_remove, save_state, step,
)

# ── 待删：再生型产物 ──
OUT_PATTERNS = ["*"]                     # flash_output/ 下全部

# flash_input 中可删的产物（白名单式，绝不整目录删）
IN_PRODUCT_PATTERNS = [
    "pre_diag_*.png",
    "_hpc_run_*.sh",
    "_hpc_build_*.sh",
]

# flash_input 中必须保护（用于最终断言）
IN_PROTECTED = [
    "snbvti2.par", "Config", "Makefile", "run_flash.sh",
    "Simulation_data.F90", "Simulation_init.F90", "Simulation_initBlock.F90",
    "mgd_qesh.F90", "Conductivity.F90", "diff_advanceTherm.F90",
    "Driver_evolveFlash.F90", "Grid_advanceDiffusion.F90",
    "hy_uhd_ragelike.F90", "hy_uhd_getRiemannState.F90",
    "hy_uhd_DataReconstructNormalDir_PPM.F90",
    "hy_uhd_dataReconstOneStep.F90",
    "SNB_F90_PROVENANCE.md", "_deploy_cn4.sh",
    "CH-QC-1-001.cn4", "He-BADGER-TOPS-Final.cn4",
    "Ti-BADGER-TOPS.cn4", "V-BADGER-TOPS.cn4",
]


def main() -> int:
    ap = argparse.ArgumentParser(description="清空本地 FLASH 输入/输出（默认 dry-run）")
    ap.add_argument("--apply", action="store_true",
                    help="真正执行删除（送回收站）。不给出则只列清单。")
    ap.add_argument("--include-analysis", action="store_true",
                    help="连同 flash_output 下的绘图产物一并清（本就在 flash_output 内）")
    ap.add_argument("--keep-logs", action="store_true",
                    help="保留 *.log（便于排查）")
    args = ap.parse_args()

    dry = not args.apply
    step(f"清空本地 FLASH 输入/输出  ({'DRY-RUN' if dry else '★ 实际执行'}）")

    log(f"场景目录: {SCEN_DIR}")
    if dry:
        log("★ 当前为 DRY-RUN，只列清单不动文件。加 --apply 才真正执行。", "WARN")

    total_n = total_b = 0
    victims: list[Path] = []

    # ── 1. flash_output/ ──
    if FLASH_OUT.exists():
        n, b = print_inventory("【将清空】flash_output/", FLASH_OUT, ["*"])
        total_n += n
        total_b += b
        for p in sorted(FLASH_OUT.iterdir()):
            if args.keep_logs and p.suffix == ".log":
                log(f"    (保留日志: {p.name})")
                continue
            victims.append(p)
    else:
        log("flash_output/ 不存在，跳过")

    # ── 2. flash_input/ 产物 ──
    if FLASH_IN.exists():
        n, b = print_inventory("【将清空】flash_input/ 产物（白名单）",
                               FLASH_IN, IN_PRODUCT_PATTERNS)
        total_n += n
        total_b += b
        for pat in IN_PRODUCT_PATTERNS:
            victims.extend(sorted(FLASH_IN.glob(pat)))

    # ── 3. __pycache__ ──
    for pc in SCEN_DIR.rglob("__pycache__"):
        victims.append(pc)
        n = sum(1 for _ in pc.rglob("*") if _.is_file())
        b = sum(x.stat().st_size for x in pc.rglob("*") if x.is_file())
        log(f"【将清空】{pc.relative_to(SCEN_DIR)}: {n} 文件 / {human(b)}")
        total_n += n
        total_b += b

    log(f"\n合计: {len(victims)} 个待删项 / {total_n} 文件 / {human(total_b)}")

    # ── 4. 执行 ──
    if dry:
        log("\n[DRY-RUN] 未执行任何删除。", "WARN")
    else:
        ok = fail = 0
        for p in victims:
            try:
                _, note = safe_remove(p, dry_run=False)
                ok += 1
                log(f"    ✓ {p.name}  ({note})")
            except SafeDeleteError as e:
                fail += 1
                log(f"    ✗ {p.name}: {e}", "ERROR")
        log(f"\n删除完成: 成功 {ok}, 失败 {fail}")
        if fail:
            log("★ 有项目未能送入回收站，请手动处理后再重跑。", "WARN")

    # ── 5. 断言：源头资产完好 ──
    step("断言：flash_input 源头资产完好")
    missing = []
    for k in IN_PROTECTED:
        if not (FLASH_IN / k).exists():
            missing.append(k)
    if missing:
        log(f"★ 警告: 以下受保护资产缺失 → {missing}", "ERROR")
        log("  → 若确认是误删，请用 git 恢复: git checkout HEAD -- "
            f"{FLASH_IN.relative_to(SCEN_DIR)}/", "ERROR")
    else:
        log(f"✓ {len(IN_PROTECTED)} 项受保护资产全部在位")

    # ── 6. 落盘状态 ──
    save_state(local_cleaned_at=None if dry else "done",
               local_clean_dryrun=dry,
               local_freed_bytes=0 if dry else total_b)
    log(f"状态已写: pipeline_state.json")

    if not dry:
        log("\n本地清空完成。下一步: python 02_clean_remote.py --apply", "OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
