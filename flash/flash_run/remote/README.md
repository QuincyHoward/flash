# FLASH 远程超算部署模块

通过 SSH 在远程超算上部署、运行、管理 FLASH 仿真。

## 功能

- **多超算账户支持**: 自动加载所有 `flash_ssh*` 凭据
- **SSH 多路由自动选择**: TCP 延迟测试，选择最佳线路
- **FLASH 远程安装**: 一键安装 (结合 FirstRun)
- **SBATCH 作业管理**: 提交、监控、取消、等待
- **文件传输**: 上传/下载仿真文件
- **结果分析**: 下载并分析 HDF5 输出

## 主要类

### RouteTester

SSH 多路由延迟测试器。

**功能**:
- 测试所有路由的 TCP 连接延迟 (SYN-ACK)
- 自动选择延迟最低的线路
- 缓存最佳路由结果
- 支持 `scfa2696` 和 `sch0348` 两个账号

**预定义路由**:

`ROUTES_SCFA2696` (9 条):
1. `ssh.cn-zhongwei-1.paracloud.com:8443`
2. `ssh.cn-hongkong-1.paracloud.com:22`
3. `ssh.cn-zhongwei-1.paracloud.com:22`
4. `ssh.cn-zhongwei-1-v6.paracloud.com:22`
5. `ssh.cn-zhongwei-1.paracloud.com:2222`
6. `ssh.cn-zhongwei-1-v6.paracloud.com:2222`
7. `ssh.cn-zhongwei-cstnet.paracloud.com:22`
8. `ssh.cn-zhongwei-cstnet-v6.paracloud.com:22`
9. `ssh.paracloud.com:2222`

`ROUTES_SCH0348` (9 条): 同上，用户名为 `sch0348@BSCC-T6`

**方法**:
- `test_route(route)`: 测试单条路由
- `test_all_routes(routes, verify_ssh)`: 测试所有路由
- `routes_for_account(cred_name, cred_data)`: 获取账号对应路由
- `account_label(cred_name, cred_data)`: 获取账号标签
- `_verify_ssh_banner(host, port)`: 验证 SSH 服务

**数据结构**:
- `RouteResult`: 单条路由测试结果 (host, port, tcp_ms, ping_ms, success)
- `RouteTestReport`: 测试报告 (results, best, timestamp)

### FlashRemoteDeploy

FLASH 超算远程部署管理器。

**功能**:
- 自动路由选择 (每次连接时测试)
- SSH 连接管理 (支持重试)
- 远程命令执行
- 文件上传/下载 (SFTP)
- FLASH 远程安装 (占位符)
- SBATCH 作业提交/监控/取消
- 结果下载与分析

**方法**:
- `connect(retry, retry_interval)`: 建立 SSH 连接
- `disconnect()`: 断开连接
- `execute(command, work_dir, timeout)`: 执行远程命令
- `upload(local_path, remote_path)`: 上传文件
- `download(remote_path, local_path)`: 下载文件
- `file_exists(remote_path)`: 检查远程文件是否存在
- `install_flash(flash_version, install_dir, with_setup)`: 安装 FLASH
- `submit_job(par_file, flash_exe, nprocs, wall_time, job_name)`: 提交作业
- `check_job(job_id)`: 检查作业状态
- `cancel_job(job_id)`: 取消作业
- `wait_for_job(job_id, poll_interval, timeout)`: 等待作业完成
- `download_results(remote_output_dir, local_output_dir, pattern)`: 下载结果

## 用法

### 测试 SSH 路由

```python
from flash.flash_run.remote.route_tester import (
    RouteTester, ROUTES_SCFA2696, ROUTES_SCH0348,
    test_and_select_best_route,
)

# 方法 1: 使用测试器类
tester = RouteTester()
report = tester.test_all_routes(ROUTES_SCFA2696, verify_ssh=True)
print(report.summary())

if report.best:
    print(f"最佳路由: {report.best.label()} ({report.best.tcp_ms:.0f}ms)")

# 方法 2: 使用便捷函数
best = test_and_select_best_route(
    username="scfa2696@NC-E",
    routes=ROUTES_SCFA2696,
    verbose=True,
)
```

### 提交超算作业

```python
from flash.flash_run.remote.remote_deploy import FlashRemoteDeploy

# 使用 with 语句自动管理连接
with FlashRemoteDeploy(credential_name="flash_ssh") as deploy:
    # 提交作业
    job_id = deploy.submit_job(
        par_file="laser_slab_2d.par",
        flash_exe="flash4",
        nprocs=90,
        wall_time="02:00:00",
        job_name="LaserSlab2D",
    )
    print(f"作业已提交: JobID={job_id}")

    # 等待作业完成
    final_state = deploy.wait_for_job(job_id, timeout=3600)
    print(f"作业结束: {final_state}")

    # 下载结果
    if final_state == "COMPLETED":
        downloaded = deploy.download_results(
            remote_output_dir="~/<user_name>/FLASH/FLASH4.8/object",
            local_output_dir="./outputs",
            pattern="*.h5",
        )
        print(f"下载了 {len(downloaded)} 个文件")
```

### 手动连接与命令执行

```python
from flash.flash_run.remote.remote_deploy import FlashRemoteDeploy

deploy = FlashRemoteDeploy(credential_name="flash_ssh_2")
deploy.connect()

# 执行远程命令
stdout, stderr, exit_code = deploy.execute(
    command="ls -la ~/<user_name>/FLASH/FLASH4.8/object/",
    work_dir=None,
    timeout=60,
)
print(stdout)

# 上传文件
deploy.upload(
    local_path="./flash_2d.par",
    remote_path="~/<user_name>/FLASH/FLASH4.8/object/flash_2d.par",
)

# 下载文件
deploy.download(
    remote_path="~/<user_name>/FLASH/FLASH4.8/object/flash.log",
    local_path="./outputs/flash.log",
)

deploy.disconnect()
```

### 多超算并行调度

```python
from flash.flash_run.remote.remote_deploy import deploy_to_all_accounts

# 定义任务函数
def my_task(deploy, **kwargs):
    """在所有超算账户上执行的任务。"""
    deploy.connect()
    # 执行一些操作
    stdout, stderr, exit_code = deploy.execute("echo Hello from $(hostname)")
    return {"stdout": stdout, "exit_code": exit_code}

# 并行部署到所有账户
results = deploy_to_all_accounts(my_task)

for account, result in results.items():
    print(f"{account}: {result}")
```

## 命令行用法

### 测试所有 SSH 路由

```bash
python -m physimx_sim.flash.flash_run.remote.route_tester
```

输出示例:
```
============================================================
SSH 路由延迟测试报告 (TCP 连接延迟)
============================================================
  [OK    ] scfa2696@NC-E@ssh.cn-zhongwei-1.paracloud.com:8443       tcp= 45ms  ping= 48ms
  [OK    ] scfa2696@NC-E@ssh.cn-hongkong-1.paracloud.com:22          tcp= 78ms  ping= 82ms
  [REFUSED] scfa2696@NC-E@ssh.cn-zhongwei-1.paracloud.com:22        tcp= N/A   ping= N/A
...
------------------------------------------------------------
  最佳路由: scfa2696@NC-E@ssh.cn-zhongwei-1.paracloud.com:8443  (TCP=45ms, Ping=48ms)
```

### 指定账号测试

```bash
python -m physimx_sim.flash.flash_run.remote.route_tester sch0348
```

## 配置存储

路由缓存: `~/.physimx/route_cache/best_routes.json`

```json
{
  "scfa2696@NC-E@ssh.cn-zhongwei-1.paracloud.com:8443": {
    "host": "ssh.cn-zhongwei-1.paracloud.com",
    "port": 8443,
    "username": "scfa2696@NC-E",
    "tcp_ms": 45.2,
    "ping_ms": 48.5
  }
}
```

## 作业提交流程

1. **连接超算**: `FlashRemoteDeploy.connect()` 自动选择最佳路由
2. **上传 .par 文件**: `FlashRemoteDeploy.upload()`
3. **生成 SBATCH 脚本**: 自动生成并提交
4. **提交作业**: `sbatch <script>`
5. **解析 Job ID**: 从 sbatch 输出中提取
6. **监控作业**: `sacct -j <job_id>`
7. **等待完成**: 轮询作业状态
8. **下载结果**: 下载 HDF5 文件

## SBATCH 脚本模板

```bash
#!/bin/bash
#SBATCH --job-name=FLASH_LaserSlab
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=90
#SBATCH --time=02:00:00
#SBATCH --output=flash_%j.out
#SBATCH --error=flash_%j.err

# 加载模块
source /public1/soft/modules/module.sh
module load hdf5/1.8.18
module load mpich/3.2-gcc9.3

# 设置环境变量
export HYPRE_HOME=~/<user_name>/FLASH/local/hypre
export LD_LIBRARY_PATH=$HYPRE_HOME/lib:$LD_LIBRARY_PATH

# 运行 FLASH
cd ~/<user_name>/FLASH/FLASH4.8/object
mpirun -np 90 ./flash4 -par_file laser_slab_2d.par
```

## 注意事项

1. **路由自动选择**: 每次调用 `connect()` 时都会重新测试所有路由，确保使用当前网络条件下最快的线路。

2. **SSH 认证**: TCP 连接成功不代表 SSH 认证成功，需要在连接时使用正确的密码/密钥。

3. **FLASH 安装**: `install_flash()` 目前是占位符实现，真实部署需要手动上传 FLASH 源码并编译。

4. **作业监控**: `check_job()` 使用 `sacct` 命令，确保超算上已安装 SLURM。

5. **文件权限**: 上传/下载文件时，确保有相应的读写权限。

## 依赖

- `paramiko`: SSH/SFTP 客户端
- `flash._core.credentials`: 密码管理
- `physimx_sim.flash.input_gen`: 输入文件生成 (可选)

## 调试

### 启用详细日志

```python
deploy = FlashRemoteDeploy(
    credential_name="flash_ssh",
    verbose=True,  # 打印详细日志
)
```

### 检查 SSH 连接

```python
from flash._core.credentials import load_ssh_credentials
cred = load_ssh_credentials("flash_ssh")
print(cred)
```

### 手动测试 TCP 连接

```python
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(5)
sock.connect(("ssh.cn-zhongwei-1.paracloud.com", 8443))
print("TCP 连接成功")
sock.close()
```
