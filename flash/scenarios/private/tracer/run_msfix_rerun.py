"""
run_msfix_rerun — ms_shldA/Z 修复后的重算清单 (默认 dry-run, 不提交)
═══════════════════════════════════════════════════════════════════

背景 (report: temp_comp/VTi新旧差异.html):
  模板 par 字典 `tracer/_par_layers.CH_FLASH_PAR` 硬编码
  `ms_shldA=6.509 / ms_shldZ=3.5` (CH 值), 覆盖 Config 中由 species_defs
  注册的正确值 ⇒ 屏蔽层是 V/Ti 却按 CH 的 A/Z 送 EOS, t=0 屏蔽层压强 ×15
  (V: 5.92e12 vs 3.93e11 dyn/cm²), 冕区过度膨胀, 吸收高 22-89×。

本清单按"脚本是否已修 + 是否已重算"分类:
  VTi1/2/3   已修 (TiTi1.py 模板 + build_vti_family) 且 **已于 2026-10-18
             在 NC-E 重算完成** (JobID 4908405/7/9) ⇒ 不再提交
  TiTi1/2/3  已修 (模板级), 存盘 par 仍是旧的错值 ⇒ **需重算**
  VCH_ml     原脚本缺 ms_shld 覆写, 本次补上 ⇒ **需重算**
  VCH_ml_F   同上 ⇒ **需重算**
  CHTi/CHTi_F/OneCH_ml/OneC*/OneSi*  屏蔽层为 CH, A/Z=6.509/3.5 正确 ⇒ 无需重算
  Au/VAuTi   脚本本就写了 ms_shldA/Z=50.9415/23, 存盘 par 实测正确 ⇒ 无需重算
  SNB/SNBVTi* 走另一条 SNB 模板, 存盘 par 实测 50.9415/23 正确 ⇒ 无需重算

流程: 每场景 `upload` → `submit` (子进程, 与手工执行完全一致)。
TiTi1/2/3 共用 TiTi/flash_input, **必须串行**; VCH_ml / VCH_ml_F 各自独立目录。

用法:
  # 1) 先看计划 (默认, 不做任何远端操作)
  .venv/Scripts/python.exe flash/scenarios/private/tracer/run_msfix_rerun.py
  # 2) 确认后真正上传+提交
  ... run_msfix_rerun.py --submit
  # 3) 只做部分
  ... run_msfix_rerun.py --submit --only TiTi1,VCH_ml
"""

import argparse
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
TMAX = 1.6e-9

# (显示名, 主脚本, 是否串行组 — TiTi 三脚本共享 flash_input)
SCENARIOS = [
    ("TiTi1", HERE / "TiTi" / "TiTi1.py"),
    ("TiTi2", HERE / "TiTi" / "TiTi2.py"),
    ("TiTi3", HERE / "TiTi" / "TiTi3.py"),
    ("VCH_ml", HERE / "VCH_ml" / "VCH_ml.py"),
    ("VCH_ml_F", HERE / "VCH_ml_F" / "VCH_ml_F.py"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="ms_shld 修复后重算 (默认 dry-run)")
    ap.add_argument("--submit", action="store_true",
                    help="真正执行 upload+submit (缺省只打印计划)")
    ap.add_argument("--only", default=None, help="逗号分隔场景名, 如 TiTi1,VCH_ml")
    ap.add_argument("--tmax", type=float, default=TMAX)
    args = ap.parse_args()

    sel = SCENARIOS
    if args.only:
        want = {s.strip() for s in args.only.split(",") if s.strip()}
        sel = [(n, p) for n, p in SCENARIOS if n in want]
        unknown = want - {n for n, _ in SCENARIOS}
        if unknown:
            print(f"[!] 未知场景 (忽略): {sorted(unknown)}")

    print("=" * 69)
    print(f" ms_shldA/Z 修复后重算清单 — {len(sel)} 个场景, tmax={args.tmax:.2e} s")
    print(f" 模式: {'★ 实际提交' if args.submit else 'dry-run (不提交)'}")
    print("=" * 69)
    for name, script in sel:
        if not script.is_file():
            print(f"[X] 缺脚本: {script}")
            return 1

    ok = 0
    for name, script in sel:
        for action in ("upload", "submit"):
            cmd = [sys.executable, str(script), action, "--tmax", repr(args.tmax)]
            print(f"\n[{name}] {action}")
            print("   " + " ".join(cmd))
            if not args.submit:
                continue
            _root = HERE
            while _root != _root.parent and not (_root / "pyproject.toml").exists():
                _root = _root.parent
            rc = subprocess.run(cmd, cwd=str(_root)).returncode
            if rc != 0:
                print(f"[X] {name} {action} 失败 (rc={rc}), 中止后续")
                return rc
        ok += 1

    if args.submit:
        print(f"\n[OK] {ok} 个场景已提交 (各场景状态见 flash_output/hpc_task_*.json)")
    else:
        print("\n[i] dry-run 结束。确认无误后加 --submit 执行。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
