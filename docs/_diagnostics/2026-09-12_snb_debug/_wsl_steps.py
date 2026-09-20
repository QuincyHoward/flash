# -*- coding: utf-8 -*-
import subprocess, io, os

WS = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
OUT = WS + r"\_wsl_steps.txt"
SRC = WS + r"\_wsl_steps.sh"

def to_wsl(p):
    d, rest = os.path.splitdrive(p)
    return "/mnt/" + d[0].lower() + rest.replace("\\", "/")

r = subprocess.run(["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-lc",
                    f"cp -f '{to_wsl(SRC)}' /tmp/_ws.sh && sed -i 's/\\r$//' /tmp/_ws.sh && bash /tmp/_ws.sh"],
                   capture_output=True, timeout=300)
o = (r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace"))
io.open(OUT, "w", encoding="utf-8").write(o)
print("WROTE", OUT)
