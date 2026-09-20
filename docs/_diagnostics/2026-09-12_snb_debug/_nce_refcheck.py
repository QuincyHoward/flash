"""检查 NC-E 上参考单元 SNB_1D_laser 是否含 9 个覆盖 F90。"""
import subprocess

OUT = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash\_nce_refcheck.txt"
PY = r"C:\Users\Administrator\.workbuddy\binaries\python\envs\default\Scripts\python.exe"

code = r'''
import sys
sys.path.insert(0, r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash")
lines = []
from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import RemoteSession

FILES = ["diff_advanceTherm.F90","mgd_qesh.F90","Conductivity.F90",
         "Driver_evolveFlash.F90","Grid_advanceDiffusion.F90",
         "hy_uhd_DataReconstructNormalDir_PPM.F90","hy_uhd_dataReconstOneStep.F90",
         "hy_uhd_getRiemannState.F90","hy_uhd_ragelike.F90"]

with RemoteSession("flash_ssh", verbose=False) as s:
    home = "~/QC/FLASH/FLASHSNB/FLASH4.8"
    ref = f"{home}/source/Simulation/SimulationMain/SNB_1D_laser"
    out, err, rc = s.run(f"ls {ref} 2>/dev/null | head -40; echo '---RC='$?", timeout=60)
    lines.append("REF_DIR_LISTING:\n" + out.strip())
    for f in FILES:
        o, e, c = s.run(f"test -f {ref}/{f} && echo YES || echo NO", timeout=40)
        lines.append(f"  {f}: {o.strip()}")
    # 已有场景单元?
    o, e, c = s.run(f"ls -d {home}/source/Simulation/SimulationMain/SNBOneCH_ml 2>/dev/null || echo NONE", timeout=40)
    lines.append("scenario_unit=" + o.strip())
    o, e, c = s.run(f"ls {home}/object/SNBOneCH_ml_ug_obj/flash4 2>/dev/null || echo NO_OBJ", timeout=40)
    lines.append("remote_ug_obj_flash4=" + o.strip())
    o, e, c = s.run(f"ls -d {home}/SNBOneCH_ml_ug_obj 2>/dev/null || echo NO_LOCALOBJ", timeout=40)
    lines.append("root_ug_obj=" + o.strip())

print("\n".join(lines))
'''
r = subprocess.run([PY, "-c", code], capture_output=True, text=True,
                   errors="replace", timeout=400)
with open(OUT, "w", encoding="utf-8") as f:
    f.write("STDOUT:\n" + (r.stdout or "") + "\n\nSTDERR:\n" + (r.stderr or "") +
            f"\n\nRC={r.returncode}\n")
print("done")
