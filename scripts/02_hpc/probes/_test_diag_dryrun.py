"""_test_diag_dryrun.py — pytest 上下文诊断（临时文件，跑完即删）。"""
import sys, tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
sys.path.insert(0, str(_ROOT))

import flash
print("flash pkg:", flash.__file__)
print("cwd:", Path.cwd())


def test_diag_dryrun():
    from flash.scenarios.core.registry import get_scenario
    from flash.scenarios.core.simulator import FlashSimulatorEngine

    sc = get_scenario("ch_center")
    print("sim_input_dir:", sc.sim_input_dir)
    print("exists:", sc.sim_input_dir.exists())
    if sc.sim_input_dir.exists():
        print("源目录内容:", sorted(p.name for p in Path(sc.sim_input_dir).iterdir())[:14])

    engine = FlashSimulatorEngine(sc, verbose=True)
    with tempfile.TemporaryDirectory() as td:
        out = engine.run(runs_dir=td, run_flash=False, run_id="000999")
        si = Path(out.run_dir) / "sim_input"
        names = sorted(p.name for p in si.iterdir()) if si.exists() else "MISSING"
        print("run_dir sim_input:", names if isinstance(names, str) else names[:10])
