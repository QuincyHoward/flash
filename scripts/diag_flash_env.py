#!/usr/bin/env python3
"""诊断 WSL 中 FLASH 安装位置与检测逻辑

运行: python scripts/diag_flash_env.py
"""

import subprocess
import sys
from pathlib import Path

# Bootstrap
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
_PARENT = _ROOT
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from flash._core.credentials import get_user_name  # noqa: E402
from flash.scenarios.simulator import _flash_home_candidates, _detect_flash_home  # noqa: E402


def main():
    print("=" * 60)
    print("WSL / FLASH 环境诊断")
    print("=" * 60)

    user = get_user_name()
    print(f"\n[1] 当前用户名 (get_user_name): {user!r}")

    # 检查 wsl 是否可用
    print(f"\n[2] 检查 WSL 命令可用性...")
    try:
        r = subprocess.run(["wsl", "--status"], capture_output=True, text=True, timeout=10)
        status = (r.stdout + r.stderr).strip()
        print(f"    wsl --status 退出码: {r.returncode}")
        print(f"    输出: {status[:200]}")
    except FileNotFoundError:
        print("    ❌ 未找到 wsl 命令")
    except Exception as e:
        print(f"    ⚠️ wsl 调用异常: {e}")

    # 逐个候选路径探测
    print(f"\n[3] 探测候选 FLASH 路径 (唯一 ~/{user}/FLASH/FLASH4.8):")
    for cand in _flash_home_candidates():
        try:
            r = subprocess.run(
                ["wsl", "bash", "-lc", f"test -f {cand}/setup && echo OK || echo NO"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            ok = "OK" in r.stdout
            mark = "✅ 存在" if ok else "  缺失"
            print(f"    {mark}: {cand}  (rc={r.returncode})")
            if not ok and r.stderr.strip():
                print(f"        stderr: {r.stderr.strip()[:100]}")
        except Exception as e:
            print(f"    ⚠️ 探测失败 {cand}: {e}")

    # 额外: 用户派生路径
    print(f"\n[4] 额外探测 (用户名派生路径):")
    extra = [f"~/{user}/FLASH/FLASH4.8"]  # 项目约定路径, 不含硬编码用户名
    for cand in extra:
        try:
            r = subprocess.run(
                ["wsl", "bash", "-lc", f"test -f {cand}/setup && echo OK || echo NO"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            mark = "✅ 存在" if "OK" in r.stdout else "  缺失"
            print(f"    {mark}: {cand}")
        except Exception as e:
            print(f"    ⚠️ {cand}: {e}")

    # _detect_flash_home 实际返回
    print(f"\n[5] _detect_flash_home() 返回: {_detect_flash_home()!r}")

    # WSL 中实际 FLASH 查找
    print(f"\n[6] WSL 中 find FLASH setup (可能较慢):")
    try:
        r = subprocess.run(
            [
                "wsl",
                "bash",
                "-lc",
                "for d in ~/FLASH/FLASH4.8 /root/FLASH/FLASH4.8; do "
                '[ -f "$d/setup" ] && echo "FOUND: $d"; done; '
                'echo "HOME=$HOME USER=$USER"',
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        print(f"    {r.stdout.strip()}")
        if r.stderr.strip():
            print(f"    stderr: {r.stderr.strip()[:200]}")
    except Exception as e:
        print(f"    ⚠️ {e}")

    print("\n" + "=" * 60)
    print("诊断完成")


if __name__ == "__main__":
    main()
