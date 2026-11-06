---
name: flash-hpc-fetch
description: 从超算批量下载 FLASH 结果文件（chk/plt/日志）的稳健 SFTP 模式：会话策略按批量规模二选、连接级重试、多线程并行、逐文件字节数校验、原子改名、收敛遍，以及凭据解析、远端路径定位、解释器选择三个前置坑与 T1-T6 传输层缺陷。触发词：超算下载、SFTP 下载、下载卡住、.part 残留、socket is closed、批量拉取 chk、paramiko 下载、hpc_download_results、结果回收。
---

> 最后核对：2026-11-06 · commit 72f6428

# HPC/SFTP 批量下载 —— 并行 + 容错 + 校验

## 1. 适用场景与落地实现

从超算拉取大量大文件（FLASH `chk` 单个 ~10 MB、`plt` ~2 MB、日志 ~1.8 MB），链路 RTT 高（~120 ms）、单连接吞吐低（实测 ~17 KB/s）。

仓内落地实现（复用而非重写）：
- `scripts/02_hpc/hpc_download_results.py` — 结果批量下载主脚本
- `scripts/02_hpc/hpc_laserslab_test.py` — 超算端到端提交/测试
- `scripts/02_hpc/hpc_run_uploader.py` — 输入包上传

实测战绩：10 文件 / 101.1 MB / 10/10 成功零重试；大批量 618 文件 / 5.1 GB 失败率 37.7% → 0.6%。

## 2. ★★★ 会话策略二选（批量规模决定，选错代价很大）

| 批量规模 | 策略 | 实测 |
|---|---|---|
| ~10–50 文件 | 每文件独立建连（开→传→关） | 10/10 成功，零重试 |
| **≥100 文件** | **每 worker 线程一个复用会话**（`threading.local`）+ 单文件 3 次重试 | 618 文件 0.6% 失败，4.81 MB/s |

**根因**：大批量逐文件建连 = 数百次 SSH 握手，叠加服务端限流反而更慢。但**绝不能跨线程共享一个会话**（paramiko 非线程安全，曾致 `as_completed` 永不返回的静默挂死）。正确折中 = **线程内复用、线程间隔离；失败即丢弃重建**。

## 3. ★ 三个前置坑（不解决则脚本静默失败）

1. **解释器缺 `cryptography` → 脚本无输出直接退出**：凭据解密链（`flash/_core/credentials/`）惰性导入 Fernet，基础托管解释器不含该包。**必须用工作区 `.venv` 解释器**（已含 numpy/h5py/paramiko/cryptography）。排查手段：先跑 `--dry-run`，秒级暴露环境问题。
2. **分离进程（nohup/DETACHED）在沙箱里启动即被杀**：返回 PID 但进程随即消失、stdout 0 字节。**用宿主自带的后台任务机制**，不用 nohup/Start-Process/DETACHED。
3. **paramiko 不展开 `~`**：`sftp.listdir_attr('~/...')` → No such file。必须先解析绝对路径：

```python
_, out, _ = run_ssh("printf '%s' \"$HOME\"")
remote_dir = f"{out.strip()}/<deploy>/_out"
```

## 4. T1–T6 传输层缺陷清单

| # | 缺陷 | 规避 |
|---|---|---|
| T1 | SFTP 不展开 `~` | 用 `printf '%s' "$HOME"` 解析绝对路径（见上） |
| T2 | 传输截断**仍返回 True** | 不信任返回值，**逐文件字节数校验**（远端 `listdir_attr` 为准） |
| T3 | `RemoteSession` 无 `sftp` 属性 | 会话对象上取不到 sftp 句柄，须自建 `open_sftp()` 或用脚本内已封装通道 |
| T4 | 单流吞吐 ~17 KB/s | 4–6 线程并行：4 连接提至 ~130 KB/s（7.7×），6 线程大批量 4.81 MB/s |
| T5 | h5py 打开失败 ≠ 文件损坏 | 先对字节数/传输完成性排查（半截文件/`.part` 残留最常见），再谈格式问题 |
| T6 | `os.replace` 被沙箱/回收站型安全策略阻断 | 原子改名失败时改用 Python `shutil.move` 或在非沙箱环境执行；勿静默吞异常 |

## 5. 正确实现（五条要点）

```python
SOCK_TIMEOUT = 1800      # 单文件 socket 超时，远大于最坏传输时间
ROUNDS       = 4         # 整体重试轮数，失败集前向喂给下一轮
workers      = 4~6

def _connect(route):
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(host, port=port, username=user, password=pwd, timeout=CONN_TIMEOUT)
    cli.get_transport().set_keepalive(20)
    sftp = cli.open_sftp()
    sftp.get_channel().settimeout(SOCK_TIMEOUT)   # ★ 关键：给 sftp channel 设超时
    return cli, sftp

def get_one(route, rdir, name, expect, lpath):
    cli, sftp = _connect(route)
    try:
        tmp = lpath + ".part"
        sftp.get(f"{rdir}/{name}", tmp)
        got = os.path.getsize(tmp)
        if got != expect:                      # ★ 逐文件字节数校验（T2）
            return (name, False, f"size {got}!={expect}")
        os.replace(tmp, lpath)                 # ★ 一致才原子改名（T6 备选 shutil.move）
        return (name, True, f"{got}B")
    finally:
        sftp.close(); cli.close()              # ★ 每个文件后必关
```

1. **会话策略匹配批量规模**（见 §2）；两者都不跨线程共享会话。
2. **连接级重试**：失败集进入下一轮，每轮重新建连。
3. **多线程并行** `ThreadPoolExecutor(max_workers=4~6)`。
4. **逐文件字节数校验 + `.part` → 正式文件原子改名**，杜绝半截文件冒充成品。幂等判定用文件大小而非 md5（chk 每帧大小恒定；md5 留作收敛遍可选加强）。
5. **以远端 `listdir_attr` 为准重新取尺寸**，不信任本地缓存或硬编码。

## 6. ★ 收敛遍（大批量必备）

并行阶段难免零星失败。**并行结束后必须顺序重下"尺寸不符/缺失"者**：
- 顺序执行，不依赖线程池 ⇒ 必然可收敛（并行池出问题会挂死）；
- 每轮重跑脚本即自动补齐（幂等跳过已完整文件）。

## 7. 历史事故与特殊文件

- **事故 A（静默 120 s 超时）**：`download()` 未透传 timeout，永远用默认 120 s；10 MB chk 按 17 KB/s 需 ~580 s。症状：小文件全成功、大文件全失败，误报"0 字节文件已存在"（实为 `.part` 残留）。
- **事故 B（复用已死连接）**：第 1 个文件成功后 `Server connection dropped`，之后全部 `Socket is closed`——跨文件无重试地复用已死连接所致。与"线程内复用"不矛盾：必须失败即丢弃重建。
- **事故 C（运行中日志永远"尺寸不符"）**：`wsl_run_*.log` 仿真进行中持续增长，远端尺寸与下载瞬间不符是**正常现象** ⇒ 运行中跳过日志，作业结束后再取。
- **远端结果目录**：FLASH 部署脚本常把结果移入 `_out/`，**不在 objdir**。

## 8. 通用检查清单

- [ ] 用 `.venv` 解释器；先 `--dry-run` 验证凭据 + 远端路径
- [ ] 远端根用 `printf '%s' "$HOME"` 解析（T1）
- [ ] 单文件 `settimeout` ≥ 1800 s
- [ ] 会话策略匹配批量规模；不跨线程共享会话
- [ ] 字节数校验 + `.part` 原子改名（T2/T6）
- [ ] 并行后跑收敛遍；收尾断言 `part == 0` 且尺寸 == 远端尺寸
- [ ] 运行中的日志跳过；后台任务用宿主机制（不用 nohup/DETACHED）
- [ ] 凭据一律走 credentials 体系动态解析，**不在脚本/日志中出现明文账号**

## 关联资源

- `scripts/02_hpc/hpc_download_results.py`、`hpc_laserslab_test.py`、`hpc_run_uploader.py`
- skill `flash-backup-verify`（凭据持久化与用户名体系）
