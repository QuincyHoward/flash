#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hpc_plasmapy_merge.py — 把 plasmapy_site_test 并入 .venv-hpc-nce 正式环境（py3.12 基座切换）

背景（2026-10-30）:
  - .venv-hpc-nce 原为 module python/3.10.8 基座，无法承载 plasmapy 2026.2.0
    (requires-python>=3.12)。
  - 用户决策: venv 基座整体切换到 miniforge/24.11 (py3.12.8)，一次性消除
    双 Python 冲突（而非维持 PYTHONPATH --target 旁路）。
  - miniforge base 已带 numpy/scipy/pandas/matplotlib/h5py → 新 venv 用
    --system-site-packages 继承，bundle 只补 yt/pytest/plasmapy 链 (32 whl)。

阶段:
  默认    : 上传 wheel bundle + output_pro 源码 → 建 .venv-hpc-nce-py312
            (旧 venv 不动) → editable 安装 flash-sim → 冒烟 → pytest 全套件
  --swap  : 验证通过后执行——旧 venv 改名 .venv-hpc-nce-py310.bak (可回滚),
            新 venv 换名为 .venv-hpc-nce, 删除 plasmapy_site_test (193M),
            快速复验。

用法: python hpc_plasmapy_merge.py [flash_ssh] [--swap]
"""
import sys
import time
import tarfile
import fnmatch
import io
from pathlib import Path

import paramiko

_ROOT = Path(__file__).resolve().parents[3]          # 仓库根 flash/
_WHL_DIR = _ROOT / "artifacts" / "hpc-plasmapy-wheels"
_OUTPUT_PRO_SRC = _ROOT / "flash" / "output_pro"
_FLASH_SIM_WHL = _ROOT / "artifacts" / "flash_sim-0.1.11-py3-none-any.whl"

CRED_NAME = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "flash_ssh"
DO_SWAP = "--swap" in sys.argv

REMOTE_FLASH_SIM = "~/PhySimX/PhySimX/simulation/flash/flash_sim"
REMOTE_FLASH_SIM_SH = "$HOME/PhySimX/PhySimX/simulation/flash/flash_sim"   # shell 命令内用 $HOME
REMOTE_WHL_DIR = f"{REMOTE_FLASH_SIM}/plasmapy_bundle"          # ⚠ 远端字面量路径只能经 mkdir 用 ~
REMOTE_WHL_DIR_SH = f"{REMOTE_FLASH_SIM_SH}/plasmapy_bundle"
VENV_NEW = f"{REMOTE_FLASH_SIM}/.venv-hpc-nce-py312"
VENV_NEW_SH = f"{REMOTE_FLASH_SIM_SH}/.venv-hpc-nce-py312"
VENV_OLD = f"{REMOTE_FLASH_SIM}/.venv-hpc-nce"
VENV_OLD_SH = f"{REMOTE_FLASH_SIM_SH}/.venv-hpc-nce"
SITE_TEST_DIR_SH = f"{REMOTE_FLASH_SIM_SH}/plasmapy_site_test"
MF = "bash -lc 'module load miniforge/24.11"

# wheel bundle 中 base 已提供的重复项（--system-site-packages 继承, 免传 14MB）
SKIP_WHEELS = {"h5py"}


def run(cl, label, cmd, t=300, show=True):
    _i, o, e = cl.exec_command(cmd, timeout=t)
    out = o.read().decode(errors="replace").strip()
    err = e.read().decode(errors="replace").strip()
    if show:
        print(f"\n===== {label} =====")
        if out:
            print(out[:2500])
        if err:
            print("[stderr]", err[:400])
    return out, err


def _tar_filter(name):
    base = name.replace("\\", "/")
    for pat in ("*/__pycache__/*", "*/.pytest_cache/*", "*/PlasmaPy/*",
                "*/inputfiles/*", "*/artifacts/*", "*.pyc"):
        if fnmatch.fnmatch(base, pat):
            return False
    return True


def pack_output_pro() -> bytes:
    """打包 output_pro 源码 (排除 PlasmaPy 克隆/缓存/测试数据) → 内存 tar.gz。"""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for p in sorted(_OUTPUT_PRO_SRC.rglob("*")):
            if not _tar_filter(str(p)):
                continue
            arc = "output_pro/" + str(p.relative_to(_OUTPUT_PRO_SRC)).replace("\\", "/")
            tf.add(str(p), arcname=arc, recursive=False)
    data = buf.getvalue()
    print(f"[pack] output_pro 源码: {len(data)/1e6:.1f} MB")
    return data


def pack_wheels() -> bytes:
    wheels = sorted(w for w in _WHL_DIR.glob("*.whl")
                    if not any(w.name.startswith(s) for s in SKIP_WHEELS))
    if not wheels:
        print(f"[X] 无 wheel: {_WHL_DIR}"); sys.exit(1)
    # flash-sim wheel 一起带上 (editable 失败时的回退)
    if _FLASH_SIM_WHL.exists():
        wheels.append(_FLASH_SIM_WHL)
    total = sum(w.stat().st_size for w in wheels)
    print(f"[pack] wheel bundle: {len(wheels)} 个, 共 {total/1e6:.1f} MB")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for w in wheels:
            tf.add(str(w), arcname=w.name)
    data = buf.getvalue()
    print(f"[pack] tar.gz: {len(data)/1e6:.1f} MB")
    return data


def step_upload(cl, payloads):
    """payloads: [(remote_path, bytes)] — SFTP 不经 shell, 路径必须绝对 (先取 $HOME)。"""
    out, _ = run(cl, "取 $HOME", "echo $HOME", show=False)
    home = out.strip()
    sftp = cl.open_sftp()
    t0 = time.time()
    try:
        run(cl, "建远端中转目录", f"mkdir -p {REMOTE_FLASH_SIM}/plasmapy_bundle", show=False)
        for rel, data in payloads:
            rp = f"{home}/{rel}"
            with sftp.open(rp, "wb") as f:
                f.write(data)
            print(f"[upload] {rel}: {len(data)/1e6:.1f} MB")
    finally:
        sftp.close()
    print(f"[upload] 完成: {time.time()-t0:.0f}s")
    return home


def step_venv(cl):
    run(cl, "建 venv (miniforge py3.12.8, --system-site-packages)",
        f"rm -rf {VENV_NEW} && "
        f"{MF} && python -m venv --system-site-packages "
        f"{REMOTE_FLASH_SIM_SH}/.venv-hpc-nce-py312 && echo VENV-CREATED' 2>&1", t=180)
    out, _ = run(cl, "venv 版本确认",
                 f"{VENV_NEW_SH}/bin/python --version && {VENV_NEW_SH}/bin/python -m pip --version", t=60)
    if "3.12" not in out:
        print("[X] venv 非 py3.12，中止"); sys.exit(1)


def step_install(cl):
    # 1) hatchling (editable 构建后端)
    run(cl, "安装 hatchling",
        f"{VENV_NEW_SH}/bin/python -m pip install --no-index --no-deps "
        f"{REMOTE_WHL_DIR_SH}/hatchling-*.whl 2>&1 | tail -2", t=120)
    # 2) flash-sim editable (源码树 = flash_sim, 与旧部署一致); 失败回退 wheel
    out, _ = run(cl, "flash-sim editable 安装",
                 f"{VENV_NEW_SH}/bin/python -m pip install --no-index --no-deps "
                 f"--no-build-isolation -e {REMOTE_FLASH_SIM_SH} 2>&1 | tail -4", t=300)
    if "Successfully installed" not in out and "Would install" not in out:
        run(cl, "editable 失败 → 回退 wheel 安装",
            f"{VENV_NEW_SH}/bin/python -m pip install --no-index --no-deps "
            f"{REMOTE_WHL_DIR_SH}/flash_sim-0.1.11-py3-none-any.whl 2>&1 | tail -3", t=180)
    # 3) 其余全部 wheel (yt/pytest/plasmapy 链)
    run(cl, "安装 wheel bundle (--no-index --no-deps)",
        f"{VENV_NEW_SH}/bin/python -m pip install --no-index --no-deps "
        f"{REMOTE_WHL_DIR_SH}/*.whl 2>&1 | tail -4", t=420)


SMOKE = r'''
import sys
import numpy, scipy, pandas, matplotlib, h5py, yt, pytest, astropy
import plasmapy
from plasmapy.formulary.speeds import thermal_speed
import astropy.units as u

print("python", sys.version.split()[0])
print("numpy", numpy.__version__, "| yt", yt.__version__, "| pytest", pytest.__version__)
assert plasmapy.__version__ == "2026.2.0", plasmapy.__version__
v = thermal_speed(1 * u.keV, "e-")
assert abs(v.si.value - 1.876e7) / 1.876e7 < 0.01

import flash
from flash.output_pro import plasmapy_bridge as pb
print("flash:", flash.__file__)
print("plasmapy", plasmapy.__version__, "@", plasmapy.__file__)
print("HAS_PLASMAPY:", pb.HAS_PLASMAPY)
print("[merge-smoke] ALL CORE OK")
'''


def step_smoke(cl):
    out, _ = run(cl, "取 $HOME (smoke)", "echo $HOME", show=False)
    home = out.strip()
    sftp = cl.open_sftp()
    rp = f"{home}/PhySimX/PhySimX/simulation/flash/flash_sim/plasmapy_bundle/merge_smoke.py"
    try:
        with sftp.open(rp, "wb") as f:
            f.write(SMOKE.encode("utf-8"))
    finally:
        sftp.close()
    run(cl, "venv 冒烟 (plasmapy/yt/pytest/bridge)",
        f"{VENV_NEW_SH}/bin/python {rp} 2>&1", t=300)


def step_test(cl):
    run(cl, "output_pro pytest 全套件",
        f"cd {REMOTE_FLASH_SIM_SH}/flash/output_pro && "
        f"{VENV_NEW_SH}/bin/python -m pytest test/ -v --tb=short 2>&1 | tail -70", t=900)


def step_unpack_source(cl):
    run(cl, "解包 output_pro 源码到 flash_sim/flash/",
        f"cd {REMOTE_FLASH_SIM_SH}/flash && tar -xzf {REMOTE_WHL_DIR_SH}/output_pro_src.tar.gz && "
        f"ls output_pro/ | head -12 && echo SRC-OK", t=120)


def do_swap(cl):
    print("\n" + "#" * 20 + " SWAP 阶段 " + "#" * 20)
    run(cl, "旧 venv → .venv-hpc-nce-py310.bak (可回滚)",
        f"mv {VENV_OLD_SH} {VENV_OLD_SH}-py310.bak 2>&1 && echo MOVED-OLD", t=60)
    run(cl, "新 venv → .venv-hpc-nce (正式)",
        f"mv {VENV_NEW_SH} {VENV_OLD_SH} 2>&1 && echo MOVED-NEW", t=60)
    run(cl, "删除 plasmapy_site_test (193M, 已并入 venv)",
        f"rm -rf {SITE_TEST_DIR_SH} && echo CLEANED-SITE-TEST", t=120)
    run(cl, "复验正式 venv",
        f"{VENV_OLD_SH}/bin/python --version && "
        f"{VENV_OLD_SH}/bin/python -c \"import plasmapy,yt,pytest,flash; "
        f"from flash.output_pro import plasmapy_bridge as pb; "
        f"print('plasmapy', plasmapy.__version__, '| bridge', pb.HAS_PLASMAPY)\" 2>&1", t=120)


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
        if DO_SWAP:
            do_swap(cl)
            return
        run(cl, "远端前置检查 (旧 venv + miniforge)",
            f"ls -d {VENV_OLD_SH} 2>/dev/null && "
            f"{MF} && python --version && python -c \"import numpy,scipy,pandas,matplotlib,h5py; "
            f"print('base stack OK')\"' 2>&1", t=120)
        whl = pack_wheels()
        src = pack_output_pro()
        step_upload(cl, [("PhySimX/PhySimX/simulation/flash/flash_sim/plasmapy_bundle/wheels.tar.gz", whl),
                         ("PhySimX/PhySimX/simulation/flash/flash_sim/plasmapy_bundle/output_pro_src.tar.gz", src)])
        run(cl, "远端解包 wheels",
            f"cd {REMOTE_WHL_DIR_SH} && rm -f *.whl && tar -xzf wheels.tar.gz && ls *.whl | wc -l", t=180)
        step_venv(cl)
        step_install(cl)
        step_unpack_source(cl)
        step_smoke(cl)
        step_test(cl)
        print("\n[merge] 阶段一完成 — 测试全绿后执行: python hpc_plasmapy_merge.py flash_ssh --swap")
    finally:
        cl.close()


if __name__ == "__main__":
    main()
