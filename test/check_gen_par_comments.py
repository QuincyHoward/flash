# -*- coding: utf-8 -*-
"""临时校验: gen_par 对用户指定 hydro 参数的行尾注释是否齐全且正确。"""
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from flash.input_gen.gen_par.generator import ParGeneratorExtended, PARAM_COMMENTS
from flash.scenarios.private.tracer._par_layers import CH_FLASH_PAR

# 用户要求的注释 (期望值)
EXPECTED = {
    "order":            "Interpolation order (first/second/third/fifth order)",
    "slopeLimiter":     "Slope limiters (minmod, mc, vanLeer, hybrid, limited)",
    "LimitedSlopeBeta": 'Slope parameter for the "limited" slope by Toro',
    "charLimiting":     "Characteristic limiting vs. Primitive limiting",
    "use_avisc":        "use artificial viscosity (originally for PPM)",
    "cvisc":            "coefficient for artificial viscosity",
    "use_flattening":   "use flattening (dissipative) (originally for PPM)",
    "use_steepening":   "use contact steepening (originally for PPM)",
    "use_upwindTVD":    "use upwind biased TVD slope for PPM (need nguard=6)",
    "RiemannSolver":    "Riemann solver (Roe, HLL, HLLC, LLF, Marquina, hybrid)",
    "entropy":          "Entropy fix for the Roe solver",
    "shockDetect":      "shock detection sensor (used by use_hybridOrder)",
    "use_hybridOrder":  "Enforce Riemann density jump",
}

print("== 1) PARAM_COMMENTS 静态表核对 ==")
ok = True
for k, v in EXPECTED.items():
    got = PARAM_COMMENTS.get(k)
    status = "OK " if got == v else "DIFF"
    if got != v:
        ok = False
    print(f"  [{status}] {k:18s} -> {got!r}")

print("\n== 2) 按场景真实参数链生成 par 并检查行尾注释 ==")
tmp = dict(CH_FLASH_PAR)
gen = ParGeneratorExtended(simulation_name="LaserSlab_CHml", dimension=1)
gen._params.clear()
for k, v in tmp.items():
    gen.set(k, v)
content = gen.generate()

lines = content.splitlines()
parsed = {}
for ln in lines:
    m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*(?:#\s*(.*))?$", ln)
    if m and m.group(1) in EXPECTED:
        parsed[m.group(1)] = (m.group(2), m.group(3))

missing = [k for k in EXPECTED if k not in parsed]
no_comment = [k for k, (val, c) in parsed.items() if not c]
print(f"  出现在 par 中的目标参数: {len(parsed)}/13")
if missing:
    print(f"  [X] 未出现在 par: {missing}")
if no_comment:
    print(f"  [X] 缺行尾注释: {no_comment}")
    ok = False
for k, (val, c) in parsed.items():
    print(f"  {k:18s} = {val:8s} # {c}")

out = _ROOT / "test" / "gen_par_comment_check.par"
with open(out, "w", encoding="utf-8") as f:
    f.write(content)
print(f"\n样例 par 已写入: {out}")
print("RESULT:", "PASS" if ok and not missing and not no_comment else "FAIL")
