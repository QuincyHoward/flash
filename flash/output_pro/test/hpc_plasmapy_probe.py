#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hpc_plasmapy_probe.py — 超算 NC-E PlasmaPy 安装可行性探测（只读）

探测项:
  1. module avail python — 有无 3.11/3.12/3.13 模块
  2. 默认 python3 / module python/3.10.8 版本
  3. 外网可达性 (pypi.org, 8s 超时)
  4. glibc 版本 (ldd --version)
  5. 既有 venv (.venv-hpc-nce) 位置与 python 版本
  6. pip / setuptools 版本 (默认 venv 内)
  7. 磁盘配额
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
sys.path.insert(0, str(_ROOT))

import paramiko
from flash._core.credentials import load_all_ssh_credentials

CRED_NAME = sys.argv[1] if len(sys.argv) > 1 else "flash_ssh"
cred = load_all_ssh_credentials()[CRED_NAME]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=cred["host"], port=22,
               username=cred["username"], password=cred["password"],
               timeout=30, allow_agent=False, look_for_keys=False, banner_timeout=15)
print(f"[connected] {CRED_NAME}: {cred['host']} as {cred['username']}")


def run(label, cmd, t=60):
    _i, o, e = client.exec_command(cmd, timeout=t)
    out = o.read().decode(errors="replace").strip()
    err = e.read().decode(errors="replace").strip()
    print(f"\n===== {label} =====")
    if out:
        print(out[:2000])
    if err and not out:
        print("[stderr]", err[:500])
    return out


run("hostname/uname", "hostname; uname -m; cat /etc/os-release 2>/dev/null | head -2")
run("glibc", "ldd --version | head -1")
run("默认 python3", "python3 --version 2>&1; which python3")
run("module avail python", "bash -lc 'module avail python 2>&1' | head -40")
run("module avail anaconda/miniconda", "bash -lc 'module avail 2>&1' | grep -iE 'conda|python' | head -10")
run("外网 pypi", "curl -sS -m 8 -o /dev/null -w '%{http_code}' https://pypi.org/simple/plasmapy/ 2>&1; echo")
run("既有 venv", "ls -d ~/software*/ 2>/dev/null; ls -d ~/*/.venv* ~/.*venv* 2>/dev/null | head; "
                "for v in $(ls -d ~/*/.venv-hpc-nce ~/*/.venv* 2>/dev/null | head -3); do "
                "echo \"$v: $($v/bin/python --version 2>&1)\"; done")
run("venv pip/setuptools", "V=$(ls -d ~/*/.venv-hpc-nce 2>/dev/null | head -1); "
                           "[ -n \"$V\" ] && $V/bin/python -m pip --version 2>&1 && "
                           "$V/bin/pip list 2>/dev/null | grep -iE 'setuptools|wheel|numpy|h5py' | head -6")
run("磁盘", "df -h ~ 2>/dev/null | tail -1; quota -s 2>/dev/null | tail -2")

client.close()
print("\n[probe done]")
