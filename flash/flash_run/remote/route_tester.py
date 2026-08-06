"""
SSH 多路由延迟测试与自动选择最佳线路
═══════════════════════════════════════════════════════════

核心设计:
  **TCP 连接时间** 作为主要延迟指标。
  不需要 SSH 认证 (密码/密钥)，只测网络可达性和连接延迟。
  路由测试在凭据设置之后进行，但 TCP 探测本身不需要凭据。

功能:
  1. 测试所有路由的 TCP 连接延迟 (SYN-ACK)
  2. 自动选择延迟最低的线路
  3. 缓存最佳路由结果
  4. 支持 scfa2696 和 sch0348 两个账号的多路由列表

用法:
    from flash.flash_run.remote.route_tester import (
        RouteTester, ROUTES_SCFA2696, ROUTES_SCH0348
    )

    tester = RouteTester()
    results = tester.test_all_routes(ROUTES_SCFA2696)
    best = tester.get_best_route(ROUTES_SCFA2696)
"""

import subprocess
import time
import json
import socket
import platform
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


# ══════════════════════════════════════════════════════
# 预定义路由 (从 credentials _config 动态构建, 无硬编码用户名)
# ══════════════════════════════════════════════════════
def _build_routes(ssh_name: str) -> List[Dict[str, Any]]:
    """从 credentials 配置动态构建路由表 (含用户名)."""
    try:
        from flash._core.credentials._config import (
            get_ssh_username, get_ssh_routes,
        )
        username = get_ssh_username(ssh_name)
        routes = get_ssh_routes(ssh_name)
        return [{**r, "username": username} for r in routes]
    except Exception:
        return []


ROUTES_SCFA2696: List[Dict[str, Any]] = _build_routes("flash_ssh")
ROUTES_SCH0348: List[Dict[str, Any]] = _build_routes("flash_ssh_2")


@dataclass
class RouteResult:
    """单条路由的测试结果。

    success=True 表示 TCP 端口可达 (host:port 可以建立 TCP 连接)。
    SSH 认证不在测试范围内 — 仅在连接时通过真实凭据认证。
    """
    host: str
    port: int
    username: str
    tcp_ms: float          # TCP SYN-ACK 连接延迟 (ms), -1 = 端口不可达
    ping_ms: float         # ICMP ping 延迟 (ms), -1 = 不可 ping
    success: bool = False  # TCP 端口是否可达
    error: str = ""        # 错误信息

    def label(self) -> str:
        return f"{self.username}@{self.host}:{self.port}"

    def summary(self) -> str:
        status = "OK" if self.success else "REFUSED"
        tcp_s = f"{self.tcp_ms:.0f}ms" if self.tcp_ms >= 0 else "N/A"
        ping_s = f"{self.ping_ms:.0f}ms" if self.ping_ms >= 0 else "N/A"
        return f"  [{status:7s}] {self.label():55s} tcp={tcp_s:>6s}  ping={ping_s:>6s}"


@dataclass
class RouteTestReport:
    """路由测试报告。"""
    results: List[RouteResult] = field(default_factory=list)
    best: Optional[RouteResult] = None
    timestamp: str = ""

    def sorted_by_latency(self) -> List[RouteResult]:
        """按延迟排序: 可达 > 不可达, 可达内按 TCP 延迟升序。"""
        def sort_key(r: RouteResult) -> tuple:
            return (
                0 if r.success else 1,
                r.tcp_ms if r.tcp_ms >= 0 else float("inf"),
            )
        return sorted(self.results, key=sort_key)

    def summary(self) -> str:
        lines = [
            "=" * 60,
            "SSH 路由延迟测试报告 (TCP 连接延迟)",
            "=" * 60,
        ]
        for r in self.sorted_by_latency():
            lines.append(r.summary())
        lines.append("-" * 60)
        if self.best:
            lines.append(
                f"  最佳路由: {self.best.label()}  "
                f"(TCP={self.best.tcp_ms:.0f}ms, Ping={self.best.ping_ms:.0f}ms)"
            )
        else:
            lines.append("  所有路由端口均不可达!")
        return "\n".join(lines)


class RouteTester:
    """SSH 路由延迟测试器。

    核心逻辑:
      - 使用 TCP socket connect() 测量网络延迟 (不需要 SSH 认证)
      - 成功 = TCP 端口可达 (对方有进程监听该端口)
      - 延迟 = TCP SYN-ACK 往返时间
      - 不测试 SSH 登录 — 那是凭据系统的工作
    """

    CACHE_DIR = Path.home() / ".physimx" / "route_cache"
    CACHE_FILE = CACHE_DIR / "best_routes.json"

    def __init__(self, tcp_timeout: int = 5):
        self.tcp_timeout = tcp_timeout

    # ── 核心测试方法 ──────────────────────────────

    def _ping_ms(self, host: str, timeout: int = 3) -> float:
        """测量 ICMP ping 延迟 (纯参考, 不作为选路依据)。"""
        try:
            param = "-n" if platform.system().lower() == "windows" else "-c"
            start = time.time()
            r = subprocess.run(
                ["ping", param, "1", "-W", str(timeout), host],
                capture_output=True, text=True, timeout=timeout + 1,
            )
            elapsed = (time.time() - start) * 1000
            return elapsed if r.returncode == 0 else -1.0
        except (subprocess.TimeoutExpired, Exception):
            return -1.0

    def _tcp_connect_ms(self, host: str, port: int, timeout: int = 5) -> Tuple[float, str]:
        """测量 TCP 连接延迟 (核心指标)。

        使用 Raw TCP socket connect() 测量 SYN-ACK 时间。
        不需要 SSH 认证, 也不需要任何凭据。
        只需要目标端口开放即可。

        Returns:
            (latency_ms, error_or_empty)
        """
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            elapsed = (time.time() - start) * 1000
            sock.close()
            return (elapsed, "")
        except socket.timeout:
            return (-1.0, "Timeout")
        except ConnectionRefusedError:
            return (-1.0, "Connection refused")
        except socket.gaierror:
            return (-1.0, "DNS resolution failed")
        except OSError as e:
            return (-1.0, str(e))
        except Exception as e:
            return (-1.0, str(e))

    def test_route(self, route: Dict[str, Any]) -> RouteResult:
        """测试单条路由: 仅测 TCP 连通性和延迟。

        注意: 不执行 SSH 认证。TCP connect() 成功即可标记为
        可用路由 — 后续连接超算时会用实际凭据做 SSH 认证。
        """
        host = route["host"]
        port = int(route.get("port", 22))
        username = route.get("username", "")

        # 主指标: TCP 连接延迟
        tcp_ms, error = self._tcp_connect_ms(host, port, self.tcp_timeout)

        # 辅指标: ICMP ping (纯参考)
        ping_ms = self._ping_ms(host) if tcp_ms >= 0 else -1.0

        return RouteResult(
            host=host,
            port=port,
            username=username,
            tcp_ms=tcp_ms,
            ping_ms=ping_ms,
            success=(tcp_ms >= 0),
            error=error,
        )

    def test_all_routes(self, routes: List[Dict[str, Any]], verify_ssh: bool = False) -> RouteTestReport:
        """测试所有路由并生成报告。

        Args:
            routes: 路由列表
            verify_ssh: 是否对 TCP 可达的路由做 SSH 连接验证
                (排除 TCP 端口开放但实际非 SSH 服务的情况)

        Returns:
            RouteTestReport
        """
        results = []
        best = None
        best_latency = float("inf")

        # 第一轮: 所有路由 TCP 测试
        for route in routes:
            result = self.test_route(route)
            results.append(result)

            if result.success and result.tcp_ms >= 0 and result.tcp_ms < best_latency:
                best_latency = result.tcp_ms
                best = result

        # 第二轮 (可选): 对最快的路由做 SSH 认证验证
        if verify_ssh and results:
            # 取 TCP 最快的前 N 条
            tcp_ok = [r for r in results if r.success]
            tcp_ok.sort(key=lambda r: r.tcp_ms)

            for candidate in tcp_ok[:3]:  # 最多验证前 3 条
                if self._verify_ssh_banner(candidate.host, candidate.port):
                    best = candidate
                    best_latency = candidate.tcp_ms
                    break
            else:
                # 所有候选都无法 SSH 连接
                best = None

        import datetime as _dt
        report = RouteTestReport(
            results=results,
            best=best,
            timestamp=_dt.datetime.now().isoformat(),
        )

        if best:
            self._cache_best_route(best)

        return report

    def _verify_ssh_banner(self, host: str, port: int, timeout: int = 5) -> bool:
        """验证端口是否真的是 SSH 服务 (检查 SSH banner)。

        发送 SSH 协议标识符并等待服务器的 SSH 版本横幅。
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))

            # 发送 SSH 协议版本
            sock.sendall(b"SSH-2.0-PhySimXRouteTester\r\n")

            # 读取服务器 banner
            banner = sock.recv(256)
            sock.close()

            # SSH banner 以 "SSH-" 开头
            return banner.startswith(b"SSH-")
        except Exception:
            return False

    # ── 缓存管理 ──────────────────────────────────

    def _cache_best_route(self, route: RouteResult) -> None:
        """缓存最佳路由。"""
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "host": route.host,
            "port": route.port,
            "username": route.username,
            "tcp_ms": route.tcp_ms,
            "ping_ms": route.ping_ms,
        }
        cached = {}
        if self.CACHE_FILE.exists():
            try:
                cached = json.loads(self.CACHE_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                cached = {}

        key = f"{route.username}@{route.host}:{route.port}"
        cached[key] = data
        self.CACHE_FILE.write_text(
            json.dumps(cached, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get_cached_best_route(self, username: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取缓存的最佳路由。"""
        if not self.CACHE_FILE.exists():
            return None

        try:
            cached = json.loads(self.CACHE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        if username:
            user_routes = {k: v for k, v in cached.items() if username in k}
            if not user_routes:
                return None
            best = min(user_routes.values(), key=lambda x: x.get("tcp_ms", float("inf")))
            return best

        if not cached:
            return None
        return min(cached.values(), key=lambda x: x.get("tcp_ms", float("inf")))

    @staticmethod
    def routes_for_account(cred_name: str, cred_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """根据凭据名称和凭据数据返回对应的预定义路由列表。

        优先级:
          1. 凭据数据中的 route_key (由 _config.py 元数据设定)
          2. 凭据名称中的关键字匹配
        """
        # 1. 优先使用凭据中存储的 route_key
        if cred_data:
            rk = cred_data.get("route_key", "")
            if rk == "scfa2696":
                return ROUTES_SCFA2696
            elif rk == "sch0348":
                return ROUTES_SCH0348

        # 2. 按名称模式匹配
        name_lower = cred_name.lower()
        if "scfa2696" in name_lower or "nc-e" in name_lower:
            return ROUTES_SCFA2696
        # flash_ssh (第一个账户) → NC-E
        if cred_name == "flash_ssh":
            return ROUTES_SCFA2696
        # flash_ssh_N → BSCC-T6
        return ROUTES_SCH0348

    @staticmethod
    def resolve_route_key(cred_name: str, cred_data: Optional[Dict[str, Any]] = None) -> str:
        """解析凭据对应的路由 key。

        Returns:
            "scfa2696" 或 "sch0348"
        """
        if cred_data:
            rk = cred_data.get("route_key", "")
            if rk in ("scfa2696", "sch0348"):
                return rk
        if cred_name == "flash_ssh" or "scfa2696" in cred_name.lower() or "nc-e" in cred_name.lower():
            return "scfa2696"
        return "sch0348"

    @staticmethod
    def account_label(cred_name: str, cred_data: Optional[Dict[str, Any]] = None) -> str:
        """返回账户的人类可读标签。"""
        rk = RouteTester.resolve_route_key(cred_name, cred_data)
        if rk == "scfa2696":
            return "scfa2696@NC-E"
        return "sch0348@BSCC-T6"

    @staticmethod
    def routes_for_username(username: str) -> List[Dict[str, Any]]:
        """根据用户名返回对应的预定义路由列表。"""
        if "scfa2696" in username:
            return ROUTES_SCFA2696
        elif "sch0348" in username:
            return ROUTES_SCH0348
        return []


# ── 便捷函数 ──────────────────────────────────────

def test_and_select_best_route(
    username: str,
    routes: Optional[List[Dict[str, Any]]] = None,
    verbose: bool = True,
) -> Optional[Dict[str, Any]]:
    """测试所有路由并选择最佳线路。

    Args:
        username: SSH 用户名 (用于查找预定义路由)
        routes: 自定义路由列表 (None = 使用预定义)
        verbose: 是否打印详细信息

    Returns:
        最佳路由字典 {"host": ..., "port": ..., "username": ..., "latency_ms": ...}
        全部 TCP 不可达返回 None
    """
    if routes is None:
        routes = RouteTester.routes_for_username(username)

    if not routes:
        if verbose:
            print(f"  [WARN] 未找到 {username} 的路由定义")
        return None

    tester = RouteTester()
    report = tester.test_all_routes(routes, verify_ssh=True)

    if verbose:
        print(report.summary())

    if report.best:
        return {
            "host": report.best.host,
            "port": report.best.port,
            "username": report.best.username,
            "latency_ms": report.best.tcp_ms,
        }
    return None


# ── CLI 入口 ──────────────────────────────────────

def main():
    """命令行入口。"""
    import sys as _sys

    if len(_sys.argv) > 1:
        target = _sys.argv[1].lower()
        if "sch0348" in target or "bscc" in target:
            routes = ROUTES_SCH0348
            label = "sch0348@BSCC-T6"
        else:
            routes = ROUTES_SCFA2696
            label = "scfa2696@NC-E"

        print(f"测试 {label} 的路由...")
        best = test_and_select_best_route(target if "@" in target else label, routes)
        if best:
            print(f"\n  推荐路由: {best['username']}@{best['host']}:{best['port']}")
            print(f"  TCP 延迟: {best['latency_ms']:.0f}ms")
        else:
            print("\n  所有路由端口均不可达!")
    else:
        print("=" * 60)
        print("测试所有 SSH 路由 (TCP 连接延迟)...")
        print("=" * 60)

        print("\n[账号 1: scfa2696@NC-E]")
        best1 = test_and_select_best_route("scfa2696@NC-E", ROUTES_SCFA2696)

        print("\n[账号 2: sch0348@BSCC-T6]")
        best2 = test_and_select_best_route("sch0348@BSCC-T6", ROUTES_SCH0348)

        print("\n" + "=" * 60)
        if best1:
            print(f"  scfa2696 最佳: {best1['username']}@{best1['host']}:{best1['port']}  ({best1['latency_ms']:.0f}ms TCP)")
        if best2:
            print(f"  sch0348 最佳: {best2['username']}@{best2['host']}:{best2['port']}  ({best2['latency_ms']:.0f}ms TCP)")


if __name__ == "__main__":
    main()
