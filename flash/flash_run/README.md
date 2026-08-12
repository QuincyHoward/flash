"""
FLASH 仿真运行管理模块
═══════════════════════════════════════════════════════════

管理 FLASH 仿真在不同计算环境中的运行，包括本地 WSL 和远程超算。

模块结构:
  - env/: 环境配置管理
  - remote/: 远程超算部署与作业调度

主要功能:
  1. 多环境管理 (本地 WSL / 超算 SSH)
  2. 维度感知的资源配置 (CPU/内存/并行数)
  3. SSH 多路由自动选择最佳线路
  4. 远程部署、作业提交、结果下载
"""

# ── 快速开始 ──────────────────────────────────────

## 1. 列出所有可用环境

from flash.flash_run import FlashEnvManager

mgr = FlashEnvManager()
mgr.list_environments()

## 2. 切换环境

mgr.set_active("supercomputer_nc_e")

## 3. 生成运行命令

env = mgr.get_active()
cmd = env.build_run_command(par_file="flash.par", nproc=4)
print(cmd)

## 4. 测试 SSH 路由延迟

from flash.flash_run.remote.route_tester import main
main()  # 命令行入口

## 5. 提交超算作业

from flash.flash_run.remote.remote_deploy import FlashRemoteDeploy

deploy = FlashRemoteDeploy(credential_name="flash_ssh")
deploy.connect()
job_id = deploy.submit_job("flash_2d.par", nprocs=32)
print(f"Job submitted: {job_id}")


# ── 模块文档 ──────────────────────────────────────

## env/ - 环境管理

### FlashEnvironment
单个 FLASH 运行环境配置。

属性:
  - name: 环境名称
  - env_type: "local_wsl" | "ssh_slurm"
  - flash_home: FLASH 安装路径
  - default_nproc: 默认进程数
  - bundle_input_files: 是否打包输入文件

方法:
  - build_run_command(): 生成运行命令
  - build_sbatch_script(): 生成 SBATCH 脚本
  - get_effective_nproc(): 计算有效进程数
  - get_mem_per_job_gb(): 计算每作业内存

### FlashEnvManager
环境管理器 (单例)。

方法:
  - list_environments(): 列出所有环境
  - get_active(): 获取当前活跃环境
  - set_active(name): 切换活跃环境
  - add(env): 添加环境
  - remove(name): 删除环境
  - auto_create_from_credentials(): 从凭据自动创建环境

### FlashResourceConfig
维度感知的资源配置管理器。

配置维度:
  - 1D: 本地 80% CPU/3并行, 超算 95% CPU/4并行
  - 2D: 本地 80% CPU/2并行, 超算 95% CPU/3并行
  - 3D: 本地 80% CPU/1并行, 超算 95% CPU/2并行

方法:
  - get_local_config(dimension): 获取本地配置
  - set_local_config(dimension, ...): 修改本地配置
  - get_hpc_config(dimension): 获取超算配置
  - set_hpc_config(dimension, ...): 修改超算配置
  - get_effective_nproc(...): 计算有效进程数


## remote/ - 远程部署

### RouteTester
SSH 多路由延迟测试器。

功能:
  - TCP 连接延迟测试 (核心指标)
  - ICMP ping 延迟测试 (参考)
  - 自动选择最佳路由
  - 缓存最佳路由结果

预定义路由:
  - ROUTES_SCFA2696: scfa2696@NC-E 的 9 条路由
  - ROUTES_SCH0348: sch0348@BSCC-T6 的 9 条路由

方法:
  - test_route(route): 测试单条路由
  - test_all_routes(routes): 测试所有路由
  - routes_for_account(...): 获取账号对应路由
  - account_label(...): 获取账号标签

### FlashRemoteDeploy
超算远程部署管理器。

功能:
  - 多超算账户支持
  - 自动路由选择
  - FLASH 远程安装 (占位符)
  - SBATCH 作业提交/监控/取消
  - 文件上传/下载
  - 结果下载与分析

方法:
  - connect(): 建立 SSH 连接
  - disconnect(): 断开连接
  - execute(cmd): 执行远程命令
  - upload(local, remote): 上传文件
  - download(remote, local): 下载文件
  - submit_job(...): 提交作业
  - check_job(job_id): 检查作业状态
  - cancel_job(job_id): 取消作业
  - wait_for_job(job_id): 等待作业完成
  - download_results(...): 下载结果文件


# ── 配置存储位置 ─────────────────────────────────

环境配置: ~/.physimx/flash_envs/environments.json
资源配置: ~/.physimx/flash_resource/resource_config.json
路由缓存: ~/.physimx/route_cache/best_routes.json


# ── 依赖 ─────────────────────────────────────────

  - paramiko: SSH/SFTP 客户端
  - flash._core.credentials: 密码管理
  - physimx_sim.flash.input_gen: 输入文件生成 (可选)


# ── 命令行用法 ─────────────────────────────────

## 测试 SSH 路由
python -m physimx_sim.flash.flash_run.remote.route_tester

## 查看资源配置
python -m physimx_sim.flash.flash_run.env.resource_config


# ── 示例工作流 ─────────────────────────────────

## 本地 WSL 运行
from flash.flash_run import FlashEnvManager, get_env_manager

mgr = get_env_manager()
mgr.set_active("local_wsl")

env = mgr.get_active()
cmd = env.build_run_command(par_file="laser_slab_1d.par", nproc=4)

# 执行命令 (通过 subprocess 或 WSL)
import subprocess
subprocess.run(cmd, shell=True)

## 超算提交作业
from flash.flash_run.remote.remote_deploy import FlashRemoteDeploy

deploy = FlashRemoteDeploy(credential_name="flash_ssh")
with deploy:
    job_id = deploy.submit_job(
        par_file="laser_slab_2d.par",
        nprocs=90,
        wall_time="02:00:00",
        job_name="LaserSlab2D",
    )
    print(f"Job ID: {job_id}")

    # 等待作业完成
    final_state = deploy.wait_for_job(job_id, timeout=3600)
    print(f"Final state: {final_state}")

    # 下载结果
    if final_state == "COMPLETED":
        deploy.download_results(
            remote_output_dir="~/hello/FLASH/FLASH4.8/object",
            local_output_dir="./outputs",
            pattern="*.h5",
        )
