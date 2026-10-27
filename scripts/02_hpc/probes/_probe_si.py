"""_probe_si.py — thin_layer_sandwich_si 的 ensure_sim_input 远端探针。"""
import traceback
from pathlib import Path

from flash.scenarios.core.registry import get_scenario

sc = get_scenario("thin_layer_sandwich_si")
print("name:", sc.name)
print("sim_input_dir:", sc.sim_input_dir, "exists:", sc.sim_input_dir.exists())
try:
    sc.ensure_sim_input()
    d = Path(sc.sim_input_dir)
    names = sorted(p.name for p in d.iterdir()) if d.exists() else "DIR-MISSING"
    print("AFTER_ENSURE:", names if isinstance(names, str) else names[:12])
except BaseException:
    traceback.print_exc()
