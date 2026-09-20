"""NC-E 连通性与凭据预检 (不修改任何凭据)。"""
import subprocess, sys, os

ROOT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
OUT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\_nce_precheck.txt"

code = r'''
import sys, json
sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
lines = []
try:
    from flash._core.credentials import get_credential_manager
    cm = get_credential_manager()
    names = cm.list_names() if hasattr(cm, "list_names") else None
    lines.append(f"cred_names={names}")
except Exception as e:
    lines.append(f"cred_error={e!r}")

try:
    from flash.scenarios.runner import HpcSpec
    lines.append("runner_import=OK")
except Exception as e:
    lines.append(f"runner_import_error={e!r}")

try:
    from flash._core.credentials.hpc_config import load_hpc_config
    cfg = load_hpc_config()
    lines.append(f"hpc_config_keys={list(cfg.keys()) if isinstance(cfg, dict) else type(cfg)}")
except Exception as e:
    lines.append(f"hpc_config_error={e!r}")

print("\n".join(lines))
'''
with open(OUT, "w", encoding="utf-8") as f:
    f.write("")

r = subprocess.run([PY, "-c", code], capture_output=True, text=True,
                   errors="replace", cwd=ROOT)
with open(OUT, "w", encoding="utf-8") as f:
    f.write("STDOUT:\n" + (r.stdout or "") + "\nSTDERR:\n" + (r.stderr or "") +
            f"\nRC={r.returncode}\n")
print("done")
