"""
超算链接诊断工具
═══════════════════════════════════════════════════════════

全面诊断超算连接链路，快速定位问题。

检查项目:
  1. 凭据完整性     — password / route_key / connection_mode
  2. 所有路由 TCP    — 测试每一条预定义路由
  3. SSH 实际登录    — 使用真实凭据尝试连接
  4. 远程环境        — FLASH 目录、模块、磁盘
  5. SCP 文件传输    — 上传 + 下载测试
  6. SLURM 可用性    — sbatch/sacct/squeue 检查

用法:
    python -m flash.test.remote_connect         # 全量诊断
    python -m flash.test.remote_connect --quick  # 快速模式
    python -m flash.test.remote_connect --cred   # 仅凭据
    python -m flash.test.remote_connect --route  # 仅路由
    python -m flash.test.remote_connect --ssh    # 仅 SSH
    python -m flash.test.remote_connect --env    # 仅远程环境
    python -m flash.test.remote_connect --scp    # 仅文件传输
    python -m flash.test.remote_connect --slurm  # 仅 SLURM
"""

import sys
import os
import time
import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple


# ── 路径设置 ──────────────────────────────────────

# flash 独立包模式: 将 flash/ 的父目录加入 sys.path

# Bootstrap: find flash project root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "__init__.py").exists() and (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))


# ══════════════════════════════════════════════════
# 诊断报告数据结构
# ══════════════════════════════════════════════════

class DiagReport:
    """诊断报告。"""

    def __init__(self):
        self.timestamp = datetime.now().isoformat()
        self.checks: Dict[str, Dict[str, Any]] = {}

    def add(self, category: str, item: str, status: str, detail: str = ""):
        """添加一条检查结果。

        Args:
            category: 分类名 (如 "credential", "route", "ssh")
            item: 检查项名
            status: "PASS" | "FAIL" | "WARN" | "INFO"
            detail: 详情或错误信息
        """
        if category not in self.checks:
            self.checks[category] = {}
        self.checks[category][item] = {"status": status, "detail": str(detail)[:500]}

    def summary(self) -> str:
        """生成格式化的诊断报告摘要。"""
        lines = [
            "=" * 60,
            "  超算连接诊断报告",
            f"  {self.timestamp}",
            "=" * 60,
        ]

        total = 0
        passed = 0
        failed = 0
        warned = 0

        for cat, items in self.checks.items():
            lines.append(f"\n  [{cat.upper()}]")
            for item, result in items.items():
                s = result["status"]
                d = result["detail"]
                total += 1
                if s == "PASS": passed += 1
                elif s == "FAIL": failed += 1
                elif s == "WARN": warned += 1

                lines.append(f"    [{s:4s}] {item}")
                if s in ("FAIL", "WARN") and d:
                    lines.append(f"          {d[:200]}")

        lines.extend([
            "",
            "-" * 60,
            f"  总计: {total}  |  PASS: {passed}  |  FAIL: {failed}  |  WARN: {warned}",
            "=" * 60,
        ])

        if failed > 0:
            lines.append("  ❌ 存在失败项，请检查上面的 FAIL 条目")
        elif warned > 0:
            lines.append("  ⚠️ 存在警告项，建议检查 WARN 条目")
        else:
            lines.append("  ✅ 全部通过！")
        lines.append("=" * 60)

        return "\n".join(lines)

    def json_report(self) -> str:
        """生成 JSON 格式报告。"""
        return json.dumps({
            "timestamp": self.timestamp,
            "checks": self.checks,
            "summary": {
                "total": sum(len(v) for v in self.checks.values()),
                "passed": sum(1 for v in self.checks.values()
                              for r in v.values() if r["status"] == "PASS"),
                "failed": sum(1 for v in self.checks.values()
                              for r in v.values() if r["status"] == "FAIL"),
                "warned": sum(1 for v in self.checks.values()
                              for r in v.values() if r["status"] == "WARN"),
            }
        }, indent=2, ensure_ascii=False)


# ══════════════════════════════════════════════════
# 诊断函数
# ══════════════════════════════════════════════════

# ── 1. 凭据检查 ──────────────────────────────────

def _print_section(title: str):
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")


def check_credential(report: DiagReport, cred_name: Optional[str] = None):
    """检查凭据完整性。"""
    _print_section("1. 凭据检查")

    try:
        from flash._core.credentials import (
            load_ssh_credentials, load_all_ssh_credentials,
            get_credential_manager, get_primary_ssh, get_user_name,
        )
    except ImportError as e:
        report.add("credential", "import", "FAIL", str(e))
        print("  [FAIL] 无法导入 credentials 模块")
        return

    # 列出所有 SSH 凭据
    all_creds = load_all_ssh_credentials()
    report.add("credential", "accounts", "INFO", f"共 {len(all_creds)} 个: {list(all_creds.keys())}")
    print(f"  [INFO] SSH 账户数: {len(all_creds)}")
    for name in all_creds:
        print(f"    - {name}")

    cm = get_credential_manager()
    primary = get_primary_ssh(cm)
    print(f"  [INFO] 主账户: {primary}")
    print(f"  [INFO] 用户名(路径): {get_user_name()}")

    # 检查主凭据
    cred = load_ssh_credentials(cred_name)
    if cred is None:
        report.add("credential", "primary_account", "FAIL", "凭据未找到")
        print("  [FAIL] 主凭据不存在")
        return

    # 检查各字段
    pw = cred.get("password", "")
    mode = cred.get("connection_mode", "auto")
    rk = cred.get("route_key", "")
    has_host = bool(cred.get("host"))
    has_port = bool(cred.get("port"))
    has_user = bool(cred.get("username"))

    report.add("credential", "password_exists", "PASS" if pw else "FAIL",
               f"长度={len(pw)}" if pw else "密码为空")
    print(f"  [{'OK' if pw else 'FAIL'}] 密码长度: {len(pw)}")

    report.add("credential", "connection_mode", "INFO", f"当前模式: {mode}")
    print(f"  [INFO] 连接模式: {mode}")

    if mode == "manual":
        if has_host and has_user:
            report.add("credential", "manual_fields", "PASS",
                       f"{cred['username']}@{cred['host']}:{cred.get('port','?')}")
            print(f"  [OK] 手动指定: {cred['username']}@{cred['host']}:{cred.get('port','?')}")
        else:
            report.add("credential", "manual_fields", "FAIL",
                       "manual 模式但 host/port/username 不完整")
            print(f"  [FAIL] manual 模式但 host/port/username 缺失")
    else:
        report.add("credential", "route_key", "INFO", f"route_key={rk}")
        print(f"  [INFO] 路由 key: {rk}")

    # 检查最佳路由缓存
    try:
        from flash._core.credentials import get_best_route
        best = get_best_route(cred_name or primary)
        if best:
            report.add("credential", "cached_route", "INFO",
                       f"{best.get('host','?')}:{best.get('port','?')} ({best.get('latency_ms',0):.0f}ms)")
            print(f"  [INFO] 上次最佳路由: {best.get('host','?')}:{best.get('port','?')} ({best.get('latency_ms',0):.0f}ms)")
    except ImportError:
        pass

    return cred


# ── 2. 路由检查 ──────────────────────────────────

def check_routes(report: DiagReport, cred: Optional[Dict] = None):
    """测试所有 SSH 路由的 TCP 可达性。"""
    _print_section("2. 路由检查")

    try:
        from flash.flash_run.remote.route_tester import (
            RouteTester, ROUTES_SCFA2696, ROUTES_SCH0348,
        )
    except ImportError as e:
        report.add("route", "import", "FAIL", str(e))
        print("  [FAIL] 无法导入 route_tester")
        return

    # 确定用哪组路由
    rk = (cred or {}).get("route_key", "")
    if rk == "scfa2696":
        routes = ROUTES_SCFA2696
        label = "scfa2696@NC-E"
    else:
        routes = ROUTES_SCH0348
        label = "sch0348@BSCC-T6"

    print(f"  [INFO] 路由组: {label} ({len(routes)} 条)")

    tester = RouteTester()
    test_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
    test_file.write("PhySimX connectivity test\n")
    test_file.close()

    reachable = 0
    unreachable = 0

    for route in routes:
        host = route["host"]
        port = int(route["port"])
        try:
            tcp_ms, tcp_err = tester._tcp_connect_ms(host, port, 3)
            if tcp_ms >= 0:
                reachable += 1
                status = "PASS"
                detail = f"{tcp_ms:.0f}ms"
            else:
                unreachable += 1
                status = "FAIL"
                detail = tcp_err[:80] if tcp_err else "TCP 超时/拒绝"
        except Exception as e:
            unreachable += 1
            status = "FAIL"
            detail = str(e)[:80]

        item_name = f"{host}:{port}"
        report.add("route", item_name, status, detail)
        tag = "[OK]" if status == "PASS" else "[ x]"
        print(f"  {tag} {host:45s}:{port:<5d} {detail[:20]}")

    os.unlink(test_file.name)

    if reachable > 0:
        report.add("route", "summary", "PASS",
                   f"{reachable}/{len(routes)} 可达")
    else:
        report.add("route", "summary", "FAIL",
                   f"0/{len(routes)} 可达 - 请检查网络或防火墙")


# ── 3. SSH 登录检查 ──────────────────────────────

def check_ssh_login(report: DiagReport, cred_name: Optional[str] = None):
    """使用真实凭据尝试 SSH 登录。"""
    _print_section("3. SSH 登录检查")

    try:
        from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import (
            _resolve_route_and_credential, ssh_cmd,
        )
    except ImportError as e:
        report.add("ssh", "import", "FAIL", str(e))
        print("  [FAIL] 无法导入 remote_ssh_helper")
        return

    try:
        route = _resolve_route_and_credential(cred_name)
    except Exception as e:
        report.add("ssh", "route_resolve", "FAIL", str(e))
        print(f"  [FAIL] 路由解析失败: {e}")
        return

    report.add("ssh", "selected_route", "INFO",
               f"{route['username']}@{route['host']}:{route['port']}")
    print(f"  [INFO] 尝试连接: {route['username']}@{route['host']}:{route['port']}")

    # SSH 连接测试
    start = time.time()
    # 第一次用较短的超时快速检查
    out, err, code = ssh_cmd(route, "echo SSH_OK", timeout=30)
    elapsed = time.time() - start

    if code == 0 and "SSH_OK" in out:
        hostname_out, _, _ = ssh_cmd(route, "hostname", timeout=10)
        hostname = hostname_out.strip()
        report.add("ssh", "login", "PASS",
                   f"已连接 {hostname}, 延迟={elapsed*1000:.0f}ms")
        print(f"  [OK] SSH 登录成功!")
        print(f"        主机: {hostname}")
        print(f"        延迟: {elapsed*1000:.0f}ms")
        return route
    else:
        err_short = err[:300].replace("\n", " | ")
        # 尝试获取更多错误信息
        try:
            # 不加 PreferredAuthentications 再试
            import tempfile, subprocess
            askpass = tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False, newline="")
            askpass.write("#!/bin/sh\n")
            askpass.write(f'echo "{route["password"]}"\n')
            askpass.close()
            os.chmod(askpass.name, 0o755)
            env = os.environ.copy()
            env["SSH_ASKPASS"] = askpass.name
            env["DISPLAY"] = ":0"

            r2 = subprocess.run([
                "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10",
                "-o", "BatchMode=no", "-o", "NumberOfPasswordPrompts=1",
                "-p", str(route["port"]),
                f'{route["username"]}@{route["host"]}', "echo SSH_OK",
            ], capture_output=True, text=True, timeout=15, env=env)
            if r2.returncode == 0:
                report.add("ssh", "login_retry", "PASS", "二次尝试成功")
                print(f"  [OK] 二次尝试登录成功!")
                return route
            err_extra = r2.stderr[:300].replace("\n", " | ")
            err_short += f" | 再试: {err_extra}"
            os.unlink(askpass.name)
        except Exception:
            pass

        report.add("ssh", "login", "FAIL", err_short)
        print(f"  [FAIL] SSH 登录失败")
        print(f"        耗时: {elapsed*1000:.0f}ms")
        print(f"        错误: {err_short[:200]}")
        print(f"        退出码: {code}")
        return None


# ── 4. 远程环境检查 ──────────────────────────────

def check_remote_env(report: DiagReport, route, cred_name: Optional[str] = None):
    """检查远程超算环境。"""
    _print_section("4. 远程环境检查")

    from flash._core.credentials import get_user_name

    from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import ssh_cmd
    user_dir = get_user_name()
    flash_home = f"~/{user_dir}/FLASH/FLASH4.8"

    checks = [
        ("HOME 目录", "echo $HOME", None),
        ("FLASH_HOME", f"test -d {flash_home} && echo EXISTS || echo MISSING", None),
        ("FLASH binary", f"ls {flash_home}/object/flash4 2>/dev/null || echo MISSING", None),
        ("磁盘空间", "df -h /public1 2>/dev/null | tail -1 || df -h ~ 2>/dev/null | tail -1", None),
        ("主机名", "hostname", None),
        ("CPU 核心", "nproc", None),
        ("总内存", "free -g | grep Mem | awk '{print $2}'", "GB"),
        ("Python", "which python3 && python3 --version 2>&1 || echo NO_PYTHON", None),
        ("mpirun", "which mpirun && mpirun --version 2>&1 | head -1 || echo NO_MPI", None),
        ("sbatch 可用", "which sbatch && sbatch --version 2>&1 || echo NO_SBATCH", None),
        ("sacct 可用", "which sacct && sacct --version 2>&1 || echo NO_SACCT", None),
        ("squeue 可用", "which squeue && squeue --version 2>&1 || echo NO_SQUEUE", None),
        ("当前用户作业", "squeue -u $USER 2>/dev/null | head -5 || echo NO_JOBS", None),
        ("可用分区", "sinfo -o '%P' 2>/dev/null | head -10 || echo NO_SINFO", None),
        ("FLASH 模块可用", "module avail 2>&1 | grep -i mpich | head -3 || echo NO_MODULE", None),
    ]

    for item, command, unit in checks:
        if route is None:
            report.add("remote_env", item, "WARN", "无有效路由，跳过")
            print(f"  [WARN] {item}: 跳过 (路由不可用)")
            continue

        try:
            out, err, code = ssh_cmd(route, command, timeout=10)
            result = out.strip()[:120] if out.strip() else (err.strip()[:120] if err.strip() else "OK")
            if unit:
                result += f" {unit}"
            status = "PASS" if code == 0 else "WARN"
            report.add("remote_env", item, status, result)
            print(f"  [{'OK' if status=='PASS' else '??'}] {item:15s}: {result}")
        except Exception as e:
            report.add("remote_env", item, "FAIL", str(e)[:120])
            print(f"  [FAIL] {item}: {e}")

    # FLASH 安装路径详情 (如果存在)
    if route:
        try:
            out, _, _ = ssh_cmd(route, f"ls -la {flash_home}/ 2>/dev/null | head -10", timeout=10)
            if out.strip():
                print(f"\n  [INFO] FLASH_HOME 内容:")
                for line in out.strip().splitlines()[:8]:
                    print(f"    {line}")
                report.add("remote_env", "flash_home_contents", "INFO", f"{len(out.splitlines())} 行")
        except Exception:
            pass


# ── 5. SCP 传输检查 ──────────────────────────────

def check_scp(report: DiagReport, route, cred_name: Optional[str] = None):
    """测试文件上传和下载。"""
    _print_section("5. SCP 文件传输检查")

    if route is None:
        report.add("scp", "skip", "WARN", "无有效路由，跳过 SCP 测试")
        print("  [WARN] 跳过 (路由不可用)")
        return

    from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import (
        scp_upload, scp_download, ssh_cmd,
    )

    # 创建测试文件
    test_file = tempfile.NamedTemporaryFile(mode="w", suffix=".test", delete=False)
    test_file.write("PhySimX Remote Connectivity Test\n")
    test_file.write(f"Timestamp: {datetime.now().isoformat()}\n")
    test_file.write("X" * 1024 + "\n")  # 1KB payload
    test_file.close()
    test_path = test_file.name
    test_name = os.path.basename(test_path)

    remote_test_path = f"~/connect_test_{test_name}"
    local_dl_path = test_path + ".downloaded"

    try:
        # 上传
        start = time.time()
        ok = scp_upload(route, test_path, remote_test_path, verbose=True)
        up_time = time.time() - start

        if ok:
            report.add("scp", "upload", "PASS", f"{up_time*1000:.0f}ms")
            print(f"  [OK] 上传成功: {test_name} -> {remote_test_path} ({up_time*1000:.0f}ms)")

            # 检查远程文件是否存在
            out, _, _ = ssh_cmd(route, f"ls -la {remote_test_path}", timeout=10)
            print(f"  [INFO] 远程文件: {out.strip()[:100]}")

            # 下载
            start = time.time()
            ok = scp_download(route, remote_test_path, local_dl_path, verbose=True)
            dl_time = time.time() - start

            if ok and os.path.exists(local_dl_path):
                report.add("scp", "download", "PASS", f"{dl_time*1000:.0f}ms")
                print(f"  [OK] 下载成功 ({dl_time*1000:.0f}ms)")
                # 验证内容
                content = open(local_dl_path).read()
                if "PhySimX Remote Connectivity Test" in content:
                    report.add("scp", "content_verify", "PASS", "文件内容一致")
                    print(f"  [OK] 文件内容验证通过")
                else:
                    report.add("scp", "content_verify", "FAIL", "文件内容不匹配")
                    print(f"  [FAIL] 文件内容不匹配")
            else:
                report.add("scp", "download", "FAIL", f"下载失败, 本地文件不存在")
                print(f"  [FAIL] 下载失败")
        else:
            report.add("scp", "upload", "FAIL", f"上传失败 ({up_time*1000:.0f}ms)")
            print(f"  [FAIL] 上传失败")

        # 清理远程
        ssh_cmd(route, f"rm -f {remote_test_path}", timeout=5)

    except Exception as e:
        report.add("scp", "exception", "FAIL", str(e)[:200])
        print(f"  [FAIL] SCP 异常: {e}")
    finally:
        try:
            os.unlink(test_path)
        except OSError:
            pass
        try:
            os.unlink(local_dl_path)
        except OSError:
            pass


# ── 6. SLURM 检查 ────────────────────────────────

def check_slurm(report: DiagReport, route, cred_name: Optional[str] = None):
    """检查 SLURM 作业系统。"""
    _print_section("6. SLURM 作业系统检查")

    if route is None:
        report.add("slurm", "skip", "WARN", "无有效路由，跳过")
        print("  [WARN] 跳过 (路由不可用)")
        return

    from flash.scenarios.flash_demo.demo_hpc.remote_ssh_helper import ssh_cmd, scp_upload

    checks = [
        ("sbatch 版本", "sbatch --version 2>&1 | head -1", None),
        ("可用分区", r"sinfo -o '%P|%D|%t' 2>/dev/null | head -15", None),
        ("当前作业", "squeue -u $USER --format='%.18i|%.10P|%.12j|%.8T' 2>/dev/null | head -10", None),
        ("账户配额", "sacctmgr show user $USER format=Account,MaxJobs 2>/dev/null | head -5 || echo NO_ACCTMGR", None),
        ("默认分区详情", r"scontrol show partition cpu 2>/dev/null | head -15 || echo NO_CPU_PART", None),
    ]

    for item, command, unit in checks:
        try:
            out, _, _ = ssh_cmd(route, command, timeout=10)
            result = out.strip()[:150]
            status = "PASS" if out.strip() and "NO_" not in out else "WARN"
            report.add("slurm", item, status, result)
            print(f"  [{'OK' if status=='PASS' else '??'}] {item:15s}: {result[:80]}")
        except Exception as e:
            report.add("slurm", item, "FAIL", str(e)[:120])
            print(f"  [FAIL] {item}: {e}")

    # 测试提交一个最小 sbatch 作业
    print(f"\n  [TEST] 提交最小 sbatch 测试作业...")

    # 创建测试脚本
    test_script = tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False, newline="\n")
    test_script.write("#!/bin/bash\n")
    test_script.write("#SBATCH -J diag_test\n")
    test_script.write("#SBATCH -p cpu\n")
    test_script.write("#SBATCH -N 1\n")
    test_script.write("#SBATCH --ntasks=1\n")
    test_script.write("#SBATCH -t 00:01:00\n")
    test_script.write("echo DIAG_JOB_OK && sleep 5 && echo DIAG_JOB_DONE\n")
    test_script.close()

    remote_test_script = f"~/diag_test_{os.path.basename(test_script.name)}"

    try:
        # 上传测试脚本
        scp_upload(route, test_script.name, remote_test_script, verbose=False)

        # 转 Unix 换行符
        ssh_cmd(route, f"sed -i 's/\\r$//' {remote_test_script}", timeout=5)

        # 提交
        out, _, _ = ssh_cmd(route, f"sbatch {remote_test_script} 2>&1", timeout=15)
        print(f"  sbatch 返回: {out.strip()[:150]}")

        import re
        match = re.search(r"Submitted batch job (\d+)", out)
        if match:
            jid = match.group(1)
            report.add("slurm", "test_submit", "PASS", f"JobID={jid}")
            print(f"  [OK] 测试作业提交成功: JobID={jid}")

            # 等待完成
            for _ in range(20):  # 最多等 60s
                out, _, _ = ssh_cmd(route, f"sacct -j {jid} --format=State --noheader 2>/dev/null | head -1", timeout=5)
                state = out.strip()
                if state in ("COMPLETED", "COMPLETING"):
                    report.add("slurm", "test_complete", "PASS", f"状态: {state}")
                    print(f"  [OK] 测试作业完成: {state}")
                    break
                elif state in ("FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL"):
                    report.add("slurm", "test_complete", "FAIL", f"状态: {state}")
                    print(f"  [FAIL] 测试作业失败: {state}")
                    break
                time.sleep(3)
            else:
                report.add("slurm", "test_complete", "WARN", "等待超时 (60s)")
                print(f"  [WARN] 测试作业超时")
        else:
            report.add("slurm", "test_submit", "FAIL", out.strip()[:200])
            print(f"  [FAIL] 测试作业提交失败: {out.strip()[:200]}")

        # 清理
        ssh_cmd(route, f"rm -f {remote_test_script}", timeout=5)

    except Exception as e:
        report.add("slurm", "test_exception", "FAIL", str(e)[:200])
        print(f"  [FAIL] SLURM 测试异常: {e}")
    finally:
        try:
            os.unlink(test_script.name)
        except OSError:
            pass


# ══════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════

def run_diagnostics(cred_name: Optional[str] = None,
                    quick: bool = False,
                    sections: Optional[List[str]] = None) -> DiagReport:
    """运行超算连接全链路诊断。

    Args:
        cred_name: 凭据名称 (None = 主账户)
        quick: 快速模式 (跳过 SCP 和 SLURM)
        sections: 只运行指定部分 ["cred", "route", "ssh", "env", "scp", "slurm"]

    Returns:
        DiagReport 诊断报告
    """
    report = DiagReport()
    run_all = sections is None

    # 1. 凭据
    cred = None
    if run_all or "cred" in (sections or []):
        cred = check_credential(report, cred_name)

    # 2. 路由
    if run_all or "route" in (sections or []):
        check_routes(report, cred)

    # 3. SSH
    route = None
    if run_all or "ssh" in (sections or []):
        route = check_ssh_login(report, cred_name)

    # 4. 远程环境
    if run_all or "env" in (sections or []):
        check_remote_env(report, route, cred_name)

    # 5. SCP
    if not quick and (run_all or "scp" in (sections or [])):
        check_scp(report, route, cred_name)

    # 6. SLURM
    if not quick and (run_all or "slurm" in (sections or [])):
        check_slurm(report, route, cred_name)

    return report


def main():
    """CLI 入口。"""

    # 解析参数
    args = sys.argv[1:]
    quick = "--quick" in args or "-q" in args
    cred_name = None

    # 提取凭据名
    for i, a in enumerate(args):
        if a == "--cred" and i + 1 < len(args):
            cred_name = args[i + 1]

    # 确定运行哪些部分
    section_map = {
        "--cred": "cred", "--route": "route",
        "--ssh": "ssh", "--env": "env",
        "--scp": "scp", "--slurm": "slurm",
    }
    sections = []
    for flag, name in section_map.items():
        if flag in args:
            sections.append(name)
    if not sections and not quick:
        sections = None  # 全部运行

    print(f"\n{'=' * 60}")
    print(f"  超算连接诊断工具 v1.0")
    print(f"  模式: {'快速' if quick else '完整'}")
    print(f"  凭据: {cred_name or '(主账户)'}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}")

    report = run_diagnostics(cred_name, quick=quick, sections=sections)

    print(f"\n{report.summary()}")

    # 保存 JSON 报告
    report_dir = Path("out_task") / "diag_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"remote_diag_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_file.write_text(report.json_report(), encoding="utf-8")
    print(f"\n  [INFO] 诊断报告已保存到: {report_file}")

    return report


if __name__ == "__main__":
    report = main()
    # 返回码: 0=全部通过, 1=有警告, 2=有失败
    has_fail = any(
        r["status"] == "FAIL"
        for cat in report.checks.values()
        for r in cat.values()
    )
    has_warn = any(
        r["status"] == "WARN"
        for cat in report.checks.values()
        for r in cat.values()
    )
    sys.exit(2 if has_fail else (1 if has_warn else 0))
