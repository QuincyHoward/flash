# -*- coding: utf-8 -*-
import subprocess, io, os
WS = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
OUT = WS + r"\_hypre.txt"; SRC = WS + r"\_hypre.sh"
def to_wsl(p):
    d, rest = os.path.splitdrive(p)
    return "/mnt/" + d[0].lower() + rest.replace("\\", "/")
r = subprocess.run(["wsl","-d","Ubuntu-22.04","--","bash","-lc",
    f"cp -f '{to_wsl(SRC)}' /tmp/_hy.sh && sed -i 's/\\r$//' /tmp/_hy.sh && bash /tmp/_hy.sh"],
    capture_output=True, timeout=300)
io.open(OUT,"w",encoding="utf-8").write(
    r.stdout.decode("utf-8","replace")+r.stderr.decode("utf-8","replace"))
print("OK")
