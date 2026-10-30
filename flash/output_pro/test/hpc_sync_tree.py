#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hpc_sync_tree.py — 本地仓库 → HPC flash_sim 树的代码同步（旧版清点 + 更新 + 回归）

背景: 远端 flash_sim 树是历史部署副本, flash_run/deploy/scenarios/docs 等落后于本地,
且本地已完成 output_processors→output_pro 全仓迁移 (2026-10-30)。本脚本:
  1. 生成本地文本代码清单 (路径+md5) → 上传 manifest
  2. 远端 md5sum 比对 → 打印 [stale/missing/extra] 三类清单 (回答"有哪些仍是旧版")
  3. 打包同步集 tar.gz → SFTP 上传 → 远端解包覆盖 (只覆盖代码文件, 不碰运行数据)
  4. 复验比对 → 应为 0 差异
  5. 远端 output_pro pytest 全套件回归

同步范围 (文本代码): flash/ + start_flash.py Makefile pyproject.toml mcp_server.py
  DEPENDENCIES.md README.md + deploy/ scripts/ docs/ test/
排除: output_processors(旧目录本体)/output_pro/PlasmaPy 克隆/__pycache__/测试数据/artifacts

用法: python hpc_sync_tree.py flash_ssh [--dry-run]
  --dry-run: 只出清单比对, 不上传不覆盖
"""
import sys
import time
import tarfile
import hashlib
import io
from pathlib import Path

import paramiko

_ROOT = Path(__file__).resolve().parents[3]
CRED_NAME = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "flash_ssh"
DRY = "--dry-run" in sys.argv

SYNC_TOP = ["flash", "deploy", "scripts", "docs", "test"]
SYNC_ROOT_FILES = ["start_flash.py", "Makefile", "pyproject.toml", "mcp_server.py",
                   "DEPENDENCIES.md", "README.md"]
TEXT_EXT = {".py", ".md", ".sh", ".bat", ".json", ".toml", ".rst", ".tsv", ".txt",
            ".cfg", ".ini", ".par"}
EXCL_PARTS = {"__pycache__", ".pytest_cache", ".git", "artifacts", "PlasmaPy",
              "flash_src", "node_modules"}
EXCL_PREFIX = ("flash/output_processors/", "flash/output_pro/inputfiles/")
REMOTE_BASE_SH = "$HOME/PhySimX/PhySimX/simulation/flash/flash_sim"


def local_manifest():
    entries = {}
    def add(p: Path):
        rel = p.relative_to(_ROOT).as_posix()
        data = p.read_bytes()
        entries[rel] = hashlib.md5(data).hexdigest()
    for top in SYNC_TOP:
        for p in (_ROOT / top).rglob("*"):
            if not p.is_file():
                continue
            s = p.relative_to(_ROOT).as_posix()
            if p.suffix.lower() not in TEXT_EXT:
                continue
            if any(part in EXCL_PARTS for part in p.parts):
                continue
            if any(s.startswith(x) for x in EXCL_PREFIX):
                continue
            add(p)
    for f in SYNC_ROOT_FILES:
        p = _ROOT / f
        if p.exists():
            add(p)
    return entries


_MD5_SCRIPT = r'''
import hashlib, os
BASE = os.path.expanduser("~/PhySimX/PhySimX/simulation/flash/flash_sim")
LIST = os.path.expanduser("~/PhySimX/PhySimX/simulation/flash/flash_sim/plasmapy_bundle/sync_list.txt")
for line in open(LIST, encoding="utf-8"):
    rel = line.strip()
    if not rel:
        continue
    fp = os.path.join(BASE, rel)
    if os.path.isfile(fp):
        h = hashlib.md5()
        with open(fp, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        print(rel, h.hexdigest())
'''


def remote_md5(cl, rel_paths, home):
    """上传清单 → 远端 python3 逐文件 md5 → {rel: md5|缺失}"""
    bundle = f"{home}/PhySimX/PhySimX/simulation/flash/flash_sim/plasmapy_bundle"
    sftp = cl.open_sftp()
    try:
        with sftp.open(f"{bundle}/sync_list.txt", "wb") as f:
            f.write("\n".join(rel_paths).encode("utf-8"))
        with sftp.open(f"{bundle}/remote_md5.py", "wb") as f:
            f.write(_MD5_SCRIPT.encode("utf-8"))
    finally:
        sftp.close()
    _i, o, e = cl.exec_command(
        f"python3 {bundle}/remote_md5.py 2>/dev/null", timeout=600)
    result = {}
    for line in o.read().decode(errors="replace").splitlines():
        parts = line.strip().rsplit(None, 1)
        if len(parts) == 2:
            result[parts[0]] = parts[1]
    return result


def main():
    sys.path.insert(0, str(_ROOT))
    from flash._core.credentials import load_all_ssh_credentials
    cred = load_all_ssh_credentials()[CRED_NAME]
    cl = paramiko.SSHClient()
    cl.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cl.connect(hostname=cred["host"], port=22, username=cred["username"],
               password=cred["password"], timeout=30, allow_agent=False,
               look_for_keys=False, banner_timeout=15)
    print(f"[connected] {CRED_NAME}: {cred['host']}")
    try:
        _i, o, _e = cl.exec_command("echo $HOME", timeout=30)
        home = o.read().decode().strip()
        manifest = local_manifest()
        print(f"[manifest] 本地同步集: {len(manifest)} 个文件")
        rmd5 = remote_md5(cl, list(manifest), home)
        stale = [p for p, h in manifest.items() if rmd5.get(p) not in (h,)]
        missing_remote = [p for p in manifest if p not in rmd5]
        print(f"\n===== 比对结果 =====")
        print(f"本地独有 (远端缺失): {len(missing_remote)}")
        print(f"内容不同或远端缺失 (待更新): {len(stale)}")
        print(f"\n-- 远端缺失文件 (前 30) --")
        for p in sorted(missing_remote)[:30]:
            print("  +", p)
        print(f"\n-- 内容不同 (前 60) --")
        for p in sorted(set(stale) - set(missing_remote))[:60]:
            print("  ~", p)
        if DRY:
            print("\n[dry-run] 不执行同步。")
            return
        if not stale:
            print("\n[sync] 远端已全部同步, 无需更新。")
        else:
            buf = io.BytesIO()
            n = 0
            with tarfile.open(fileobj=buf, mode="w:gz") as tf:
                for p in sorted(stale):
                    tf.add(str(_ROOT / p), arcname=p)
                    n += 1
            data = buf.getvalue()
            print(f"\n[sync] 打包 {n} 个文件 → {len(data)/1e6:.1f} MB, 上传中...")
            sftp = cl.open_sftp()
            t0 = time.time()
            base = REMOTE_BASE_SH.replace("$HOME/", "")
            _i, o, _e = cl.exec_command("echo $HOME", timeout=30)
            home = o.read().decode().strip()
            with sftp.open(f"{home}/{base}/sync_tree.tar.gz", "wb") as fobj:
                fobj.write(data)
            print(f"[sync] 上传完成 {time.time()-t0:.0f}s")
            _i, o, _e = cl.exec_command(
                f"cd {REMOTE_BASE_SH} && tar -xzf sync_tree.tar.gz && echo EXTRACT-OK", timeout=300)
            print(o.read().decode(errors="replace").strip())
            sftp.close()
            # 复验
            rmd5b = remote_md5(cl, list(manifest), home)
            remaining = [p for p, h in manifest.items() if rmd5b.get(p) not in (h,)]
            print(f"[verify] 复验: 剩余差异 {len(remaining)}")
            for p in remaining[:10]:
                print("  !", p)
        # 远端回归
        print("\n[pytest] 远端 output_pro 全套件回归...")
        _i, o, _e = cl.exec_command(
            f"cd {REMOTE_BASE_SH}/flash/output_pro && "
            f"{REMOTE_BASE_SH}/.venv-hpc-nce/bin/python -m pytest test/ -q --tb=line 2>&1 | tail -3",
            timeout=900)
        print(o.read().decode(errors="replace").strip())
    finally:
        cl.close()


if __name__ == "__main__":
    main()
