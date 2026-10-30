#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hpc_plasmapy_install.py — 超算 NC-E PlasmaPy 2024.10.0 离线安装测试（编排器）

背景（2026-10-30 探测结论）:
  - NC-E: CentOS 7 / glibc 2.17 / module python 最高 3.10.8 / **完全离线**;
  - PlasmaPy 2026.2.0 requires-python>=3.12 → 不可安装（版本闸门拦截）;
  - 改测 PlasmaPy 2024.10.0（最后支持 py3.10 的版本）;
  - 路线: 本机 pip download 交叉下载 cp310 manylinux2014 wheel → SFTP 上传 →
    `pip install --no-index --target=<隔离目录>`（零污染正式 venv .venv-hpc-nce）→ 冒烟。

用法:
  python flash/output_pro/test/hpc_plasmapy_install.py flash_ssh
"""
import gzip
import io
import os
import sys
import tarfile
import time
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
LOCAL_WHL_DIR = _ROOT / "artifacts" / "hpc-plasmapy-wheels"
REMOTE_BASE = "~/PhySimX/PhySimX/simulation/flash/flash_sim_pkg"
REMOTE_WHL_DIR = f"{REMOTE_BASE}/hpc-plasmapy-wheels"
REMOTE_FLASH_SIM = "~/PhySimX/PhySimX/simulation/flash/flash_sim"
REMOTE_VENV = f"{REMOTE_FLASH_SIM}/.venv-hpc-nce"
REMOTE_TARGET = f"{REMOTE_FLASH_SIM}/plasmapy_site_test"
# ⚠ 远端命令内必须用 $HOME (bash 不展开参数中 `=` 后的 ~; SFTP 不经 shell)
REMOTE_TARGET_SH = "$HOME/PhySimX/PhySimX/simulation/flash/flash_sim/plasmapy_site_test"
PP_VERSION = "2026.2.0"
# 2026-10-30 用户实测: module miniforge/24.11 → Python 3.12.8, 解除
# PlasmaPy 2026.2.0 的 requires-python>=3.12 闸门 (原 py3.10.8 路线降级为备选)
MF_ENV = "bash -lc 'module load miniforge/24.11 && cd ~ && ' "  # 前缀模板(占位)

cred = load_all_ssh_credentials()[CRED_NAME]


def make_client():
    cl = paramiko.SSHClient()
    cl.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cl.connect(hostname=cred["host"], port=22, username=cred["username"],
               password=cred["password"], timeout=30, allow_agent=False,
               look_for_keys=False, banner_timeout=15)
    return cl


def run(cl, label, cmd, t=300):
    _i, o, e = cl.exec_command(cmd, timeout=t)
    rc = o.channel.recv_exit_status() if False else None
    out = o.read().decode(errors="replace").strip()
    err = e.read().decode(errors="replace").strip()
    print(f"\n===== {label} =====")
    if out:
        print(out[-2500:])
    if err:
        print("[stderr]", err[-600:])
    return out, err


def step_upload(cl, home):
    """打包 wheel 目录并 SFTP 上传（gzip tar 单流, 客户端内存打包）。"""
    wheels = sorted(LOCAL_WHL_DIR.glob("*.whl"))
    if not wheels:
        print(f"[X] 本地无 wheel: {LOCAL_WHL_DIR}");  sys.exit(1)
    total_mb = sum(w.stat().st_size for w in wheels) / 1e6
    print(f"[1] 本地 wheel: {len(wheels)} 个, 共 {total_mb:.1f} MB, 打包上传中...")
    t0 = time.time()
    sftp = cl.open_sftp()
    try:
        # SFTP 不经 shell, '~' 不展开 → 必须用 $HOME 绝对路径
        base = f"{home}/PhySimX/PhySimX/simulation/flash/flash_sim_pkg"
        run(cl, "远端中转目录", f"mkdir -p {base}")
        remote_tgz = f"{base}/hpc-plasmapy-wheels.tar.gz"
        with sftp.open(remote_tgz, "wb") as rf:
            with tarfile.open(fileobj=rf, mode="w:gz") as tf:
                for w in wheels:
                    tf.add(str(w), arcname=w.name)
        dur = time.time() - t0
        print(f"[1] 上传完成: {dur:.0f}s")
        # 校验数量: "ls *.whl | wc -l && du -sh" → 首行为数量
        out, _ = run(cl, "远端解包 (先清空防新旧混装)",
                     f"rm -rf {REMOTE_WHL_DIR} && mkdir -p {REMOTE_WHL_DIR} && "
                     f"tar -xzf {REMOTE_BASE}/hpc-plasmapy-wheels.tar.gz -C {REMOTE_WHL_DIR} && "
                     f"ls {REMOTE_WHL_DIR}/*.whl | wc -l && du -sh {REMOTE_WHL_DIR}")
        try:
            return int(out.splitlines()[0].strip())
        except (ValueError, IndexError):
            return 0
    finally:
        sftp.close()


def step_install(cl):
    # miniforge/24.11 (py3.12.8) + --no-deps --target 隔离安装:
    # 重依赖 (numpy 2.1.3/scipy 1.14.1/pandas 2.2.3/matplotlib/h5py) 由
    # miniforge 基础环境提供; 本 bundle 只装 17 个缺失包。
    # (不带 --no-deps 时 pip --target 要求全部依赖都在 find-links 内,
    #  含 ~90MB 科学计算栈 — 无必要; 也避免 pip 解析器 jupyter 链回退死循环)
    out, err = run(cl, "隔离安装 (miniforge py3.12, --no-index --no-deps --target)",
                   f"rm -rf \"$HOME/~\" {REMOTE_TARGET} {REMOTE_TARGET_SH}; "
                   f"bash -lc 'module load miniforge/24.11 && "
                   f"python -m pip install --no-index --no-deps "
                   f"--target={REMOTE_TARGET_SH} {REMOTE_WHL_DIR}/*.whl' 2>&1 | tail -5", t=600)
    return out


SMOKE = r'''
import sys, time
t0 = time.time()
import plasmapy
print("[smoke] plasmapy", plasmapy.__version__, "@", plasmapy.__file__)
assert plasmapy.__version__ == "2026.2.0", f"版本非 2026.2.0: {plasmapy.__version__}"
import astropy.units as u
from plasmapy.formulary import thermal_speed, Debye_length, Coulomb_logarithm
v = thermal_speed(1 * u.keV, "e-")
print("[smoke] thermal_speed(1keV,'e-') =", f"{v.si.value:.4e}", "m/s  (理论 1.876e7)")
assert abs(v.si.value - 1.876e7) / 1.876e7 < 0.01
lD = Debye_length(1e6 * u.K, 1e20 * u.m**-3)
print("[smoke] Debye_length(1e6K, 1e20/m3) =", f"{lD.si.value:.4e}", "m  (理论 6.90e-6)")
assert abs(lD.si.value - 6.90e-6) / 6.90e-6 < 0.01
lnL = Coulomb_logarithm(1e7 * u.K, 1e27 * u.m**-3, ("e-", "p+"))
print("[smoke] Coulomb_logarithm =", f"{float(lnL):.3f}")
try:
    from plasmapy.formulary.laser import em_angular_frequency
    from plasmapy.formulary.densities import critical_density
    nc = critical_density(em_angular_frequency(0.351 * u.um))
    print("[smoke] n_c(0.351um) =", f"{nc.to(1/u.cm**3).value:.4e}", "cm^-3  (理论 9.05e21)")
except Exception as exc:
    print("[smoke] laser/critical_density 在 2024.10.0 不可用:", type(exc).__name__)
try:
    from plasmapy.formulary.ionization import ionization_balance
    print("[smoke] ionization_balance 可用")
except Exception as exc:
    print("[smoke] ionization_balance 在 2024.10.0 不可用:", type(exc).__name__)
try:
    from plasmapy.formulary.braginskii import ClassicalTransport
    tr = ClassicalTransport(T_e=1e6*u.K, n_e=1e26*u.m**-3, T_i=1e6*u.K, n_i=1e26*u.m**-3,
                            ion="p+", Z=1, model="Braginskii", field_orientation="parallel")
    print("[smoke] kappa_e(Braginskii) =", f"{tr.electron_thermal_conductivity.value:.4e}", "W/(m K)")
except Exception as exc:
    print("[smoke] ClassicalTransport 异常:", type(exc).__name__, str(exc)[:120])
print(f"[smoke] 总耗时 {time.time()-t0:.1f}s")
print("[smoke] ALL CORE OK")
'''


def step_smoke(cl, home):
    # 冒烟脚本经 SFTP 上传为文件再执行 (单引号嵌套在 bash -lc 内不可靠)
    base = f"{home}/PhySimX/PhySimX/simulation/flash/flash_sim_pkg"
    remote_py = f"{base}/hpc_plasmapy_smoke.py"
    sftp = cl.open_sftp()
    try:
        with sftp.open(remote_py, "wb") as f:
            f.write(SMOKE.encode("utf-8"))
    finally:
        sftp.close()
    out, err = run(cl, "冒烟测试 (miniforge py3.12 + PYTHONPATH 隔离)",
                   f"bash -lc 'module load miniforge/24.11 && "
                   f"PYTHONPATH={REMOTE_TARGET_SH} python {remote_py}' 2>&1",
                   t=300)
    return out


def _q(s):
    """单引号安全包裹 (heredoc 替代, 避免远端引号地狱)。"""
    return "'" + s.replace("'", "'\\''") + "'"


def main():
    cl = make_client()
    print(f"[connected] {CRED_NAME}: {cred['host']}")
    try:
        out, _ = run(cl, "远端 $HOME", "echo $HOME")
        home = out.strip().splitlines()[-1]
        run(cl, "远端前置检查 (venv + miniforge py3.12)",
            f"ls -d {REMOTE_VENV} 2>/dev/null && {REMOTE_VENV}/bin/python --version 2>&1; "
            f"bash -lc 'module load miniforge/24.11 && python --version' 2>&1 | tail -1")
        n = step_upload(cl, home)
        step_install(cl)
        out = step_smoke(cl, home)
        ok = "ALL CORE OK" in out
        print("\n" + "=" * 60)
        print("[RESULT]", "✅ HPC PlasmaPy 安装+冒烟通过" if ok else "❌ 冒烟未全部通过 (见上方输出)")
        print("=" * 60)
    finally:
        cl.close()


if __name__ == "__main__":
    main()
