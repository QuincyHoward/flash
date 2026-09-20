"""对比核查: OneCH_ml (基线) 的 par 是否有同样的 tele 初值 & 是否有 gr_hypreUseFloor。
目的: 判定 dt_Diff=2.8e86 是 SNB 特有还是共享的初态问题。
"""
import sys
from pathlib import Path

FLASH_ROOT = Path(r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
S = FLASH_ROOT / "flash" / "scenarios" / "private" / "tracer"

lines = []
for name, p in [
    ("SNBOneCH_ml", S / "SNB" / "SNBOneCH_ml" / "flash_input" / "snbonech_ml.par"),
    ("SNBOneCH", S / "SNB" / "SNBOneCH" / "flash_input"),
    ("OneCH_ml", S / "OneCH_ml"),
]:
    lines.append(f"══ {name}: {p} ══")
    if p.is_file():
        txt = p.read_text(encoding="utf-8", errors="replace")
        for k in ["gr_hypreUseFloor", "sim_teleCham", "dtmax", "cfl",
                  "eos_chamTableFile", "tstep_change_factor", "useDiffuse"]:
            for ln in txt.splitlines():
                if ln.strip().startswith(k):
                    lines.append("   " + ln.strip()[:110])
                    break
            else:
                lines.append(f"   {k}: <ABSENT>")
    elif p.is_dir():
        pars = list(p.glob("*.par"))
        lines.append(f"   dir, pars={[q.name for q in pars]}")
        for q in pars:
            txt = q.read_text(encoding="utf-8", errors="replace")
            lines.append(f"   -- {q.name} --")
            for k in ["gr_hypreUseFloor", "sim_teleCham", "dtmax"]:
                for ln in txt.splitlines():
                    if ln.strip().startswith(k):
                        lines.append("      " + ln.strip()[:110])
                        break
                else:
                    lines.append(f"      {k}: <ABSENT>")
    else:
        lines.append("   <path not found>")
    lines.append("")

(FLASH_ROOT / "_compare_baseline.txt").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
