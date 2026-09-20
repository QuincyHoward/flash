# -*- coding: utf-8 -*-
import base64
import io
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_INNER = os.path.join(_HERE, "flash")
sys.path.insert(0, os.path.join(_INNER, "scenarios", "flash_demo", "demo_hpc"))
sys.path.insert(0, _INNER)

from remote_ssh_helper import quick_run  # noqa: E402

SH = os.path.join(_HERE, "_nce_postmortem.sh")
OUT = os.path.join(_HERE, "_nce_postmortem.txt")

body = io.open(SH, "r", encoding="utf-8").read().replace("\r\n", "\n")
b64 = base64.b64encode(body.encode("utf-8")).decode("ascii")
cmd = ("mkdir -p $HOME/_diag && "
       f"printf '%s' '{b64}' | base64 -d > $HOME/_diag/pm.sh && "
       "bash $HOME/_diag/pm.sh")

for attempt in range(1, 6):
    try:
        out, err, rc = quick_run(cmd, credential_name="flash_ssh", timeout=300)
        txt = (out or "")
        if err:
            txt += "\n[stderr]\n" + err[-1200:]
        io.open(OUT, "w", encoding="utf-8").write(txt)
        print(txt)
        print(f"\n[rc={rc}]")
        break
    except Exception as exc:
        print(f"[attempt {attempt}] EXC {type(exc).__name__}: {exc}")
        time.sleep(60)
else:
    print("[FATAL] 5 次失败")
