"""
env_spec.py — flash-sim 三平台依赖规格（机器可读唯一事实源）
═══════════════════════════════════════════════════════════

职责:
  * 定义三平台（Windows / WSL / HPC）依赖的**基线版本**与**平台差异**；
  * 供 deps_lock/generate_locks.py 生成三份 requirements-*.txt；
  * 供 deploy/doctor.py 做安装后版本核对；
  * 根目录 DEPENDENCIES.md 的人读表格与本文件保持一致（本文件为源）。

约定:
  * 基线策略 = 三平台取交集版本（尽量同版本）；
  * 平台差异只在本文件 `PLATFORM_OVERRIDES` 中声明，并须在
    DEPENDENCIES.md「差异原因」列给出依据；
  * pyproject.toml 仍是语义化声明处（>= 约束）；本文件是**精确锁定层**。
"""

from __future__ import annotations

#: 基线锁定（三平台共同目标版本）。key = PyPI 包名。
#: 维护规则: 升级基线时同步 pyproject.toml 下限、DEPENDENCIES.md、重新生成 lock。
BASELINE: dict[str, str] = {
    # ── 运行时核心（pyproject dependencies）──
    "numpy": "1.26.4",
    "cryptography": "41.0.7",
    # ── full 附加（pyproject [full]）──
    "h5py": "3.11.0",
    "matplotlib": "3.8.4",
    "pandas": "2.2.3",
    "yt": "4.4.0",          # ★ 4.3.1 在 NC-E 全节点 SIGSEGV（2026-10 实测），基线直接抬到 4.4.0
    # ── dev / 工具（pyproject [dev] + start_flash 在线补装）──
    "scipy": "1.11.4",
    "pytest": "8.2.0",
    "pytest-cov": "5.0.0",
    "paramiko": "3.4.0",    # SSH/SFTP（超算部署与 hpc CLI 依赖）
    "pillow": "10.3.0",
}

#: 平台差异覆盖。仅列**偏离基线**的包；未列出的包三平台同用基线版本。
#: reason 字段必填 —— 对应 DEPENDENCIES.md 差异表的依据。
PLATFORM_OVERRIDES: dict[str, dict[str, str]] = {
    # ── HPC (NC-E, glibc 2.17 老 gcc/老内核，跨机构建) ──
    "hpc": {
        "pandas": "2.3.2",   # glibc2.17 交叉构建可用版本（2026-10-22 实测部署通过）
        "h5py": "3.14.0",    # 同上
        "pillow": "12.2.0",  # 同上
        # yt 不覆盖: 基线已抬至 4.4.0（NC-E 最低可用版）
    },
    # ── Windows: 无原生 FLASH，Python 侧与基线一致，无覆盖 ──
    "win": {},
    # ── WSL: 与 Windows 共用 Ubuntu 侧 wheel，与基线一致 ──
    "wsl": {},
}

#: 平台元数据（doctor 与 lock 头注释使用）
PLATFORM_NOTES: dict[str, str] = {
    "win": "Windows 本机: 无原生 FLASH；仅 Python 侧（造包/分析/paramiko 驱动）",
    "wsl": "WSL Ubuntu: FLASH 4.8 本地运行；venv 路径经 FLASH_VENV_DIR 注入；"
           "FLASH 4.8 只读默认名 flash.par",
    "hpc": "超算 NC-E (glibc 2.17): module python/3.10.8；命名环境 .venv-hpc-nce；"
           "离线 --no-index；wheelhouse 由 build_wheelhouse_linux.py 交叉构建",
}

#: 档位（与 _wh_common.PROFILES 对齐）: 每档包含的包分组
PROFILE_GROUPS: dict[str, list[str]] = {
    "lite":    ["numpy", "cryptography", "h5py", "matplotlib"],
    "runtime": ["numpy", "cryptography", "h5py", "matplotlib", "pandas", "yt", "paramiko"],
    "full":    ["numpy", "cryptography", "h5py", "matplotlib", "pandas", "yt",
                "scipy", "pytest", "pytest-cov", "paramiko", "pillow"],
}


def resolve(platform: str, profile: str = "full") -> dict[str, str]:
    """返回某平台某档位的 {包名: 精确版本}（基线 + 平台覆盖合成）。"""
    platform = platform.lower()
    if platform not in PLATFORM_NOTES:
        raise ValueError(f"未知平台: {platform}（可选: {sorted(PLATFORM_NOTES)}）")
    if profile not in PROFILE_GROUPS:
        raise ValueError(f"未知档位: {profile}（可选: {sorted(PROFILE_GROUPS)}）")
    overrides = PLATFORM_OVERRIDES.get(platform, {})
    out: dict[str, str] = {}
    for pkg in PROFILE_GROUPS[profile]:
        if pkg not in BASELINE:
            raise KeyError(f"PROFILE_GROUPS 引用了未在 BASELINE 声明的包: {pkg}")
        out[pkg] = overrides.get(pkg, BASELINE[pkg])
    return out


def diff_rows() -> list[tuple[str, str, str, str, str]]:
    """生成 DEPENDENCIES.md 差异表行: (包名, 基线, win, wsl, hpc)。"""
    rows = []
    for pkg in sorted(BASELINE):
        w = PLATFORM_OVERRIDES.get("win", {}).get(pkg, BASELINE[pkg])
        l = PLATFORM_OVERRIDES.get("wsl", {}).get(pkg, BASELINE[pkg])
        h = PLATFORM_OVERRIDES.get("hpc", {}).get(pkg, BASELINE[pkg])
        rows.append((pkg, BASELINE[pkg], w, l, h))
    return rows


if __name__ == "__main__":
    # 自检: 打印三平台 full 档差异
    for plat in ("win", "wsl", "hpc"):
        print(f"== {plat} ==")
        for k, v in resolve(plat).items():
            mark = "" if v == BASELINE[k] else "  (≠基线)"
            print(f"  {k}=={v}{mark}")
