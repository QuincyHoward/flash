# FLASH 仿真运行流程文档

本文档描述使用 `flash_run` 模块运行 FLASH 仿真的完整流程。

## 流程概览

```
1. 配置环境 → 2. 测试路由 → 3. 生成输入文件 → 4. 提交作业 → 5. 监控作业 → 6. 下载结果 → 7. 后处理
```

---

## 1. 配置环境

### 1.1 首次使用：初始化环境

```python
from physimx_sim.flash.flash_run.env import get_env_manager

# 获取环境管理器 (自动创建默认环境)
mgr = get_env_manager()

# 查看所有环境
print(mgr.summary())
```

输出示例：
```
FLASH 仿真环境管理
==================================================
  [local_wsl] LOCAL(WSL) <-- 当前
    描述: 本地 WSL Ubuntu (FLASH 4.8)
    FLASH: ~/hello/FLASH/FLASH4.8

  [supercomputer_nc_e] SSH(flash_ssh)
    描述: ParaCloud 并行云 NC-E (中卫)
    远程 FLASH: ~/scfa2696/FLASH/FLASH4.8
    工作目录: ~/scfa2696/FLASH/run

  [supercomputer_bscc_t6] SSH(flash_ssh_2)
    描述: ParaCloud 并行云 BSCC-T6 (中卫)
    远程 FLASH: ~/sch0348/FLASH/FLASH4.8
    工作目录: ~/sch0348/FLASH/run
```

### 1.2 从凭据自动创建环境

```python
# 如果添加了新的 SSH 凭据，可以自动创建对应的环境
created = mgr.auto_create_from_credentials()
if created:
    print(f"自动创建了环境: {created}")
```

### 1.3 修改资源配置

```python
from physimx_sim.flash.flash_run.env.resource_config import get_resource_config

rc = get_resource_config()

# 查看当前配置
print(rc.summary())

# 修改本地 1D 配置
rc.set_local_config(
    dimension=1,
    max_cpu_percent=90,  # 使用 90% CPU
    max_parallel=2,        # 最多 2 个并行
)

# 修改超算 2D 配置
rc.set_hpc_config(
    dimension=2,
    max_cpu_percent=100,  # 使用 100% CPU
    max_parallel=3,         # 最多 3 个并行
)
```

---

## 2. 测试 SSH 路由

在连接超算之前，先测试所有 SSH 路由的延迟，选择最佳线路。

```python
from physimx_sim.flash.flash_run.remote.route_tester import main

# 命令行方式
# python -m physimx_sim.flash.flash_run.remote.route_tester

# 或在 Python 中调用
from physimx_sim.flash.flash_run.remote.route_tester import (
    RouteTester, ROUTES_SCFA2696, test_and_select_best_route,
)

# 测试所有路由
tester = RouteTester()
report = tester.test_all_routes(ROUTES_SCFA2696, verify_ssh=True)
print(report.summary())

# 使用便捷函数
best = test_and_select_best_route(
    username="scfa2696@NC-E",
    routes=ROUTES_SCFA2696,
    verbose=True,
)
```

输出示例：
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

---

## 3. 生成输入文件

使用 `flash_input_gen` 模块生成 FLASH 输入文件（.par 文件）。

> **注意**: 此步骤需要使用 `flash_input_gen` 模块，详见该模块的文档。

```python
# 示例：生成 1D LaserSlab 仿真输入文件
from physimx_sim.flash.input_gen import ParGeneratorExtended

gen = ParGeneratorExtended()
par_content = gen.generate(
    dimension=1,
    sim_name="laser_slab_1d",
    # ... 其他参数
)

# 保存到文件
with open("./run/flash_1d.par", "w") as f:
    f.write(par_content)
```

---

## 4. 提交作业

### 4.1 本地 WSL 运行

```python
import subprocess
from physimx_sim.flash.flash_run.env import get_env_manager

# 切换 to 本地环境
mgr = get_env_manager()
mgr.set_active("local_wsl")

env = mgr.get_active()
cmd = env.build_run_command(
    par_file="./run/flash_1d.par",
    nproc=4,
)

# 执行命令
result = subprocess.run(
    cmd,
    shell=True,
    capture_output=True,
    text=True,
)
print(result.stdout)
```

### 4.2 超算提交作业

```python
from physimx_sim.flash.flash_run.remote.remote_deploy import FlashRemoteDeploy

# 使用 with 语句自动管理连接
with FlashRemoteDeploy(credential_name="flash_ssh") as deploy:
    # 上传 .par 文件
    deploy.upload(
        local_path="./run/flash_2d.par",
        remote_path="~/QC/FLASH/FLASH4.8/object/flash_2d.par",
    )

    # 提交作业
    job_id = deploy.submit_job(
        par_file="flash_2d.par",
        flash_exe="flash4",
        nprocs=90,
        wall_time="02:00:00",
        job_name="LaserSlab2D",
    )
    print(f"作业已提交: JobID={job_id}")
```

---

## 5. 监控作业

### 5.1 检查作业状态

```python
with FlashRemoteDeploy(credential_name="flash_ssh") as deploy:
    status = deploy.check_job(job_id)
    print(f"作业状态: {status}")
```

可能的状态：
- `PENDING`: 排队中
- `RUNNING`: 运行中
- `COMPLETED`: 已完成
- `FAILED`: 失败
- `CANCELLED`: 已取消
- `TIMEOUT`: 超时

### 5.2 等待作业完成

```python
with FlashRemoteDeploy(credential_name="flash_ssh") as deploy:
    final_state = deploy.wait_for_job(
        job_id=job_id,
        poll_interval=30,  # 每 30 秒检查一次
        timeout=3600,      # 最多等待 1 小时
    )
    print(f"作业结束: {final_state}")
```

---

## 6. 下载结果

### 6.1 下载 HDF5 文件

```python
with FlashRemoteDeploy(credential_name="flash_ssh") as deploy:
    downloaded = deploy.download_results(
        remote_output_dir="~/QC/FLASH/FLASH4.8/object",
        local_output_dir="./outputs",
        pattern="*.h5",  # 下载所有 HDF5 文件
    )
    print(f"下载了 {len(downloaded)} 个文件")
```

### 6.2 下载作业日志

```python
result = deploy.get_job_output(
    job_id=job_id,
    local_dir="./logs",
)
print(result["stdout"])
print(result["stderr"])
```

---

## 7. 后处理

使用 `output_processors` 模块处理仿真结果。

> **注意**: 此步骤需要使用 `output_processors` 模块，详见该模块的文档。

```python
from physimx_sim.flash.output_processors import HDF5Reader

# 读取 HDF5 文件
reader = HDF5Reader("./outputs/lasslab_hdf5_chk_0000")
dens = reader.get_variable("dens")
tele = reader.get_variable("tele")

# 可视化
# ...
```

---

## 8. 批量运行

### 8.1 多参数扫描

```python
from physimx_sim.flash.flash_run.remote.remote_deploy import FlashRemoteDeploy

# 定义参数范围
powers = [0.5, 1.0, 1.5, 2.0]
job_ids = []

for power in powers:
    # 1. 生成输入文件 (假设已生成 flash_power{pr}.par)
    # 2. 提交作业
    with FlashRemoteDeploy(credential_name="flash_ssh") as deploy:
        job_id = deploy.submit_job(
            par_file=f"flash_power{power}.par",
            nprocs=90,
            job_name=f"LaserSlab_power{power}",
        )
        job_ids.append(job_id)
        print(f"提交作业: {job_id}")

# 3. 等待所有作业完成
for job_id in job_ids:
    with FlashRemoteDeploy(credential_name="flash_ssh") as deploy:
        final_state = deploy.wait_for_job(job_id, timeout=3600)
        print(f"作业 {job_id} 结束: {final_state}")
```

### 8.2 使用资源配置控制并行数

```python
from physimx_sim.flash.flash_run.env.resource_config import get_resource_config

rc = get_resource_config()

# 获取当前维度的并行配置
hpc_1d = rc.get_hpc_config(dimension=1)
print(f"最多并行 {hpc_1d.max_parallel} 个作业")

# 根据配置控制并行数
import concurrent.futures

def run_job(pr):
    with FlashRemoteDeploy(credential_name="flash_ssh") as deploy:
        return deploy.submit_job(f"flash_power{pr}.par")

with concurrent.futures.ThreadPoolExecutor(max_workers=hpc_1d.max_parallel) as executor:
    futures = {executor.submit(run_job, pr): pr for pr in powers}
    for future in concurrent.futures.as_completed(futures):
        pr = futures[future]
        job_id = future.result()
        print(f"功率 {pr}: JobID={job_id}")
```

---

## 9. 常见问题

### 9.1 SSH 连接失败

**问题描述**: `SSHConnectionError: 所有 SSH 路由均不可达`

**解决方法**:
1. 检查网络连接
2. 手动测试路由:
   ```bash
   python -m physimx_sim.flash.flash_run.remote.route_tester
   ```
3. 检查凭据是否正确:
   ```python
   from physimx_sim.flash._core.credentials import load_ssh_credentials
   cred = load_ssh_credentials("flash_ssh")
   print(cred)
   ```

### 9.2 作业提交失败

**问题描述**: `JobSubmissionError: sbatch 失败`

**解决方法**:
1. 检查 .par 文件是否存在
2. 检查 SBATCH 分区是否存在
3. 查看详细错误:
   ```python
   stdout, stderr, exit_code = deploy.execute(f"sbatch {sbatch_path}")
   print(stderr)
   ```

### 9.3 下载结果失败

**问题描述**: `FileNotFoundError: 远程文件不存在`

**解决方法**:
1. 检查作业是否已完成
2. 检查远程输出目录是否正确
3. 手动列出远程文件:
   ```python
   stdout, stderr, exit_code = deploy.execute("ls -la ~/QC/FLASH/FLASH4.8/object/*.h5")
   print(stdout)
   ```

---

## 10. 最佳实践

1. **始终使用单例**: 使用 `get_env_manager()` 和 `get_resource_config()` 获取单例，避免配置不一致。

2. **自动选择路由**: `FlashRemoteDeploy` 会自动选择最佳路由，无需手动指定。

3. **使用 with 语句**: 自动管理 SSH 连接，避免连接泄漏。

4. **配置维度感知**: 根据仿真维度 (1D/2D/3D) 设置不同的资源配置。

5. **批量运行时控制并行数**: 使用 `FlashResourceConfig.get_hpc_config(dimension).max_parallel` 获取最大并行数。

6. **定期检查环境**: 运行 `print(mgr.summary())` 确认当前环境配置。

---

## 附录：API 快速参考

```python
# 环境管理
from physimx_sim.flash.flash_run.env import FlashEnvManager, get_env_manager
from physimx_sim.flash.flash_run.env.resource_config import FlashResourceConfig, get_resource_config

mgr = get_env_manager()                     # 获取环境管理器
env = mgr.get_active()                      # 获取当前环境
mgr.set_active("supercomputer_nc_e")        # 切换环境

rc = get_resource_config()                  # 获取资源配置
rc.set_local_config(1, 80, 3)           # 修改本地 1D 配置
rc.set_hpc_config(2, 95, 3)             # 修改超算 2D 配置

# 远程部署
from physimx_sim.flash.flash_run.remote.remote_deploy import FlashRemoteDeploy

with FlashRemoteDeploy(credential_name="flash_ssh") as deploy:
    deploy.upload(local, remote)             # 上传文件
    job_id = deploy.submit_job(...)         # 提交作业
    status = deploy.check_job(job_id)        # 检查状态
    deploy.cancel_job(job_id)               # 取消作业
    deploy.wait_for_job(job_id)             # 等待完成
    deploy.download_results(...)            # 下载结果

# 路由测试
from physimx_sim.flash.flash_run.remote.route_tester import RouteTester, test_and_select_best_route

tester = RouteTester()
report = tester.test_all_routes(ROUTES_SCFA2696)
best = test_and_select_best_route("scfa2696@NC-E", ROUTES_SCFA2696)
```
