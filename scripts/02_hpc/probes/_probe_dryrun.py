"""_probe_dryrun.py — 远端复现 engine dry-run + 检查 flash_input 现状。"""
import sys, tempfile, traceback
from pathlib import Path

sys.path.insert(0, str(Path.home() / "PhySimX/PhySimX/simulation/flash/flash_sim"))

from flash.scenarios.core.registry import get_scenario, list_scenarios
from flash.scenarios.core.simulator import FlashSimulatorEngine

import flash
print("flash pkg:", flash.__file__)

sc = get_scenario("ch_center")
print("sim_input_dir:", sc.sim_input_dir, "exists:", sc.sim_input_dir.exists())
if sc.sim_input_dir.exists():
    print("flash_input 内容数:", len(list(Path(sc.sim_input_dir).iterdir())))

available = [s[0] for s in list_scenarios()]
print("registered:", available[:8])

try:
    engine = FlashSimulatorEngine(sc, verbose=True)
    with tempfile.TemporaryDirectory() as td:
        out = engine.run(runs_dir=td, run_flash=False, run_id="000999")
        run_dir = Path(out.run_dir)
        si = run_dir / "sim_input"
        names = sorted(p.name for p in si.iterdir()) if si.exists() else "DIR MISSING"
        print("run_dir sim_input 内容:", names if isinstance(names, str) else names[:8])
        print("DRYRUN_OK" if (si.exists() and list(si.glob("*.F90"))) else "DRYRUN_STILL_EMPTY")
except BaseException:
    traceback.print_exc()
