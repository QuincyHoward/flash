# -*- coding: utf-8 -*-
"""把 _wsl_fix_cn4.sh 拷进 WSL 并执行 (避免跨 WSL 边界的引号/变量展开问题)。"""
import subprocess, io, os, time

WS = r"E:\PhySimX\PhySimX\simulation\flash_test\layer3\flash"
OUT = WS + r"\_wsl_fix_cn4.txt"
SRC = WS + r"\_wsl_fix_cn4.sh"

# 转 WSL 内路径: E:\a\b -> /mnt/e/a/b
def to_wsl(p):
    d, rest = os.path.splitdrive(p)
    return "/mnt/" + d[0].lower() + rest.replace("\\", "/")

wsl_src = to_wsl(SRC)
wsl_dst = "/tmp/_wsl_fix_cn4.sh"

def sh(c, tmo=300):
    r = subprocess.run(["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-lc", c],
                       capture_output=True, timeout=tmo)
    return (r.stdout.decode("utf-8", "replace") +
            r.stderr.decode("utf-8", "replace")).strip()

lines = []
o = sh(f"cp -f '{wsl_src}' {wsl_dst} && sed -i 's/\\r$//' {wsl_dst} && bash {wsl_dst}")
lines.append(f"===== FIX_CN4 =====\n{o}\n")

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("WROTE", OUT)
