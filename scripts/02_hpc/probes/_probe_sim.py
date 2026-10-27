"""_probe_sim.py — ch_center ensure_sim_input 远端探针（由 try_yt440.py 上传执行）。"""
import traceback
from pathlib import Path

from flash.scenarios.core.registry import get_scenario

sc = get_scenario("ch_center")
print("sim_input_dir:", sc.sim_input_dir)
try:
    sc.ensure_sim_input()
    names = sorted(p.name for p in Path(sc.sim_input_dir).iterdir())
    print("GENERATED_COUNT:", len(names))
    print("GENERATED:", names[:12])
except BaseException:
    traceback.print_exc()
