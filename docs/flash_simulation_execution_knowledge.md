# FLASH仿真执行知识库
**来源:** FLASH4.8 User's Guide
**提取时间:** 2026-06-16

---

## 1. FLASH仿真执行基本流程

### 1.1 配置 (Setup)

```bash
# 基本语法
./setup <SimulationName> [options]

# 示例: LaserSlab 1D仿真
./setup -auto LaserSlab -1d +cartesian -nxb=16 +hdf5typeio species=cham,targ +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10
```

### 1.2 编译 (Build)

```bash
cd object/
make
```

### 1.3 运行 (Run)

```bash
# 并行运行 (N个进程)
mpirun -np N ./flash4

# 单机运行
./flash4
```

## 2. LaserSlab仿真配置

### 2.1 Setup快捷键

| 快捷键 | 说明 |
|--------|------|
| `+laser` | 启用激光射线追踪包 |
| `+laserCubicInterpolation` | 启用立方插值射线追踪 |
| `+asyncLaser` | 启用异步射线追踪通信 |
| `+mtmmmt` | 启用多物种多温度 |
| `+uhd3t` | 启用3T非分裂流体力学 |
| `+mgd` | 启用多群辐射扩散 |

### 2.2 激光参数配置 (Runtime Parameters)

#### 2.2.1 激光脉冲参数

```
# 脉冲数量
ed_numberofPulses = 1

# 脉冲功率和时间点对 (ed_power_n_i, ed_time_n_i)
ed_power_1_1 = 1.0e12  # 第一个脉冲的第一个功率点 (瓦特)
ed_time_1_1 = 0.0      # 对应的时间 (秒)
```

#### 2.2.2 激光光束参数

```
# 光束数量
ed_numberOfBeams = 1

# 激光波长 (米)
ed_wavelength_1 = 3.5e-7

# 光束透镜坐标 (激光起源点)
ed_lens_1_x = 0.0
ed_lens_1_y = 0.0
ed_lens_1_z = -0.01

# 光束目标坐标 (激光照射点)
ed_target_1_x = 0.0
ed_target_1_y = 0.0
ed_target_1_z = 0.0
```

#### 2.2.3 通用激光参数

```
# 最大脉冲数 (setup时需要)
ed_maxPulses = 5

# 最大光束数 (setup时需要)
ed_maxBeams = 6

# 每个时间步的能量沉积基于cell时间
ed_cellTimeEnergyDeposition = .true.

# 3D圆柱对称激光射线追踪
ed_laser3Din2D = .false.
```

## 3. 输出文件分析

### 3.1 检查点文件 (Checkpoint Files)

- 命名: `*_hdf5_chk_*`
- 用途: 重启仿真

### 3.2 绘图文件 (Plot Files)

- 命名: `*_hdf5_plo_*`
- 用途: 可视化和后处理

### 3.3 激光IO输出

```
# 启用激光IO
ed_useLaserIO = .true.

# 最大射线数
ed_laserIOMaxNumberOfRays = 1000

# 每个射线的最大位置记录数
ed_laserIOMaxNumberOfPositions = 100
```

## 4. 激光光束参数详解

### 4.1 ed_lens vs ed_target 位置说明 (重要!)

| 参数系列 | 含义 | 位置特征 | 说明 |
|---------|------|---------|------|
| `ed_lensX/Y/Z_N` | 激光透镜（射线起源点） | **在仿真区域外** | 定义射线方向，值通常为 ±1（cm），远超出仿真域 [-0.016, 0.016] cm |
| `ed_targetX/Y/Z_N` | 激光目标（射线入射目标点） | **在仿真区域内** | 如 targetX=0.0 或 =0.014（靶前表面），在仿真域内 |

> **关键理解:** 在 1D 仿真中，激光从 lens（域外）向 target（域内）传播。lens 位置仅定义方向，实际物理（能量沉积、吸收）发生在射线穿过仿真域时。lens 的 ±1 等大值确保射线以近垂直/水平方向进入域内。

### 4.2 1D仿真激光几何

在 1D 仿真中：
- `ed_lensX = -1` → 激光从左侧入射（射线向右传播）
- `ed_lensX = 1` → 激光从右侧入射（射线向左传播）
- `ed_targetX` → 激光瞄准的域内位置

## 5. LaserSlab变体

### 5.1 全物理激光驱动仿真 (Section 35.7.5)

- **几何:** 2D圆柱
- **物理:** 3T流体力学 + 表格EOS和不透明度 + MGD + 电子热传导 + 激光射线追踪
- **物种:** cham (腔), targ (靶)
- **EOS:** IONMIX4格式表格

### 5.2 带Thomson散射诊断的激光仿真 (Section 35.7.6)

- **附加功能:** ThomsonScattering诊断
- **Setup快捷键:** `+thsc`

### 5.3 Z-pinch仿真 (Section 35.7.7)

- **物理:** Z-pinch等离子体压缩

### 5.4 项目自定义变体对比

| 参数 | LaserSlab1d_new (1beam) | LaserSlab1d_2beams | LaserSlab1d_3beams |
|------|------------------------|-------------------|-------------------|
| **靶材** | Al (铝, ρ=2.7) | Polystyrene (聚苯乙烯, ρ=1.1) | Al (铝, ρ=2.7) |
| **腔材** | He (氦) | He (氦) | He (氦) |
| **光束数** | 1 (左侧入射) | 2 (左右对射) | 3 (左2 + 右1) |
| **脉冲数** | 1 (4段梯形) | 2 (5段+6段) | 1 (4段梯形) |
| **脉冲形状** | 高斯→梯形 | 双平台矩形 | 梯形 (100ps ramp) |
| **峰值功率** | 1e14 W/cm² | 1e11 W (pulse2) | 1e12 W |
| **波长** | 1.053 μm | 1.053 μm | 1.053 μm |
| **光束位置** | X=-1→0.0 | X=-1→0.0, X=1→0.0 | X=-1→0.0, X=1→0.0, X=-1→0.014 |
| **网格块** | nblockx=6 | nblockx=4 | nblockx=6 |
| **tmax** | 5.5e-9 s | 1.0e-9 s | 1.2e-9 s |
| **特点** | 单侧烧蚀压缩 | 对称双面驱动 | 非对称3束：2束腔面+1束靶面 |

| **new_struture_custom** | **2 (相向)** | **CH/Polystyrene (ρ=1.0)** | **1 梯形** | **1.19e-9** | **对称域, 351nm, 40ps边沿** |

### 5.5 自定义对称域仿真 (new_struture, 2026-06-23)

| 参数 | 值 | 说明 |
|------|-----|------|
| 域 | [-100, 100] μm | 对称域, L0=100μm (可配置) |
| 靶 | [-30, 30] μm | CH/Polystyrene半宽 (可配置) |
| 光束 | 2束相向, ±1cm | 0.351μm, 5e14 W/cm² |
| 脉冲 | 梯形, 1ns平顶, 40ps边沿 | 0→40ps→1.04ns→1.08ns |
| 模块 | `scenarios/flash_demo/new_struture/` | `laserslab1d_local_custom.py` |
| 凭据 | `RemoteSession` + `~/.physimx/physimx_sim/flash/` | Flash 独立存储, SSH_ASKPASS 密码自动注入 |
| 超算分析 | `module load python/3.9.6` | h5py 3.3.0 + numpy 1.26.4 |

**物理结果** (2026-06-23, 超算运行, CH中心 [-5,5] μm):
- 激光加热: ~3.2e-10s 开始 → ~4.5e-10s 峰值 (⟨tele⟩~2.4e6 K)
- 冷却: ~1.07e-9s 降至 ⟨tele⟩~9.5e5 K
- ⟨nele⟩ 峰值 ~6.3e23 cm⁻³

## 6. 真实测试结果

### 6.1 LaserSlab1D 本地 Demo 测试 (2026-06-22, v2.1)

| 项目 | 值 |
|------|-----|
| 测试环境 | WSL Ubuntu-22.04, mpirun -np 1 |
| 运行文件夹 | `scenarios/flash_demo/demo_task/laserslab1d_local_demo/run/` (11 文件自包含) |
| SETUP_CMD | `./setup -auto hello/LaserSlab_local -1d ... -objdir=hello/LaserSlab_local -par_file=laserslab1d_demo.par` |
| FLASH 二进制 | `~/hello/FLASH/FLASH4.8/hello/LaserSlab_local/flash4` |
| 输出 | 41 checkpoint + 80 plot 文件 |
| 成功标志 | `exiting: reached max SimTime` |
| 一键执行 | `cd run/ && bash run_flash.sh` |

### 6.2 LaserSlab1D 超算 Demo 测试 (2026-06-18)

| 项目 | 值 |
|------|-----|
| 测试环境 | ParaCloud NC-E (SSH1: scfa2696) |
| 作业系统 | SLURM, partition=v5_192, 4 cores, 1 node |
| 文件模式 (v2.1) | `demo_task/laserslab1d_supercomputer_demo/run/` 独立运行文件夹 |
| SETUP_CMD (v2.1) | `./setup -auto hello/LaserSlab_hpc -1d ... -objdir=hello/LaserSlab_hpc -par_file=laserslab1d_sc_demo.par` |
| 模块 | `mpich/3.2-gcc9.3`, `hdf5/1.8.18` |
| 编译耗时 | ~2 分钟 (make -j4) |
| 仿真耗时 | ~30 秒 (mpirun -np 4) |
| 输出 | 41 checkpoint + 80 plot 文件 |
| 成功标志 | `exiting: reached max SimTime` |

## 7. 批量仿真工作流 (HPC Batch)

### 7.1 概述

`laserslab1d_hpc_demo_batch.py` 实现了多功率批量仿真与对比分析工作流。通过修改 `ed_power*` 参数值，在相同物理配置下运行不同激光功率的仿真，对比密度/温度/峰值等物理量。

### 7.2 功率因子变体生成

```python
# 核心方法: _modify_power_in_par
# 正则匹配 ed_power 开头的行, 将值乘以 power_factor
def _modify_power_in_par(par_path: Path, power_factor: float) -> None:
    content = par_path.read_text(encoding="utf-8")
    
    def replace_power(match):
        prefix = match.group(1)
        value_str = match.group(2)
        orig_value = float(value_str)
        new_value = orig_value * power_factor
        return f"{prefix}{new_value:.6e}"
    
    new_content = re.sub(
        r'(ed_power\w*\s*=\s*)([\d.eE+\-]+)',
        replace_power, content,
    )
    par_path.write_text(new_content, encoding="utf-8")
```

### 7.3 批量工作流 (v1.1 — 远程分析模式)

| 步骤 | 方法 | 说明 |
|------|------|------|
| 1. 生成变体 | `create_power_variants()` | 生成基准 → copytree 复制 → 修改功率 (`platform="hpc"`) |
| 2. 上传超算 | `deploy_to_supercomputer()` | SFTP 上传 + CRLF 转 Unix + 上传 `remote_analysis.py` |
| 3a. sbatch 提交 | `run_flash_remotely() 3a` | 提交到可用分区 (v5_192) |
| 3b. 直接运行 (fallback) | `run_flash_remotely() 3b` | sbatch 失败时降级 |
| 3c. 等待完成 | `run_flash_remotely() 3c` | sacct 轮询 (最长 1h) |
| 4. 远程分析 | `run_remote_analysis_and_download()` | 在超算运行 `remote_analysis.py` (module load python/3.10.8) |
| 5. 下载结果 | `run_remote_analysis_and_download()` | 仅下载 JSON + PNG, HDF5 保留在超算 |

### 7.4 对比分析图

- **batch_results_dens_comparison.png**: 密度分布对比 (超算分析生成)
- **batch_results_tele_comparison.png**: 电子温度对比
- **batch_results_peak_density_vs_power.png**: 密度峰值 vs 功率因子
- **batch_results.json**: 密度/温度摘要数据

### 7.5 SBATCH 资源配置说明

`ShellScriptGenerator` 自动从 `resource_config.json` 加载并生成 SLURM 脚本头:

```
HPC 1D: --ntasks=4,  no --mem  (48核节点, ntasks_per_job=4)
HPC 2D: --ntasks=12, no --mem  (48核节点, ntasks_per_job=12)
HPC 3D: --ntasks=22, no --mem  (48核节点, ntasks_per_job=22)
Local:  不生成 SLURM 头
```

**重要 — SelectType=select/linear 说明:**

ParaCloud NC-E (scfa2696) 使用 `SelectType=select/linear`, 这意味着:
- 每个 `sbatch` 作业必然分配 **整节点** (48核/192GB)
- `--ntasks` 仅控制 `srun -n` 的 MPI 进程数, 不影响 SLURM 分配的 CPU 数
- `--mem` 限制在此模式下同样**无效** — 无论设多少, 整节点内存都被分配
- 因此 `submit_flash.sh` **不设 `--mem`**, `--ntasks` 设为合理值仅用于 srun
- 多个独立 sbatch 作业可并行分配到不同节点, 实现并发执行

### 7.6 SLURM 注意事项

- 提交前先用 `test/remote_connect/test_sbatch.py` 检测可用分区
- `submit_flash.sh` 需要 `#SBATCH -p` 行来指定分区（模板中默认启用）
- **`--mem` 已被移除**: select/linear 下整节点分配, 内存限制无效
- **`--ntasks=N`** 仅控制 `srun -n` 的 MPI 进程数, 不影响 CPU 分配
- 直接执行 `./submit_flash.sh` 时（非 sbatch），SLURM_* 环境变量为空，已通过 `${VAR:-default}` 语法提供回退
- CRLF 换行符问题：上传后通过 `sed -i 's/\\r$//' *.sh` 修复
- 远程分析使用 `module load python/3.10.8` 加载 Python 3
- `remote_analysis.py` 兼容 Python 2.7+ (无类型注解, 无 typing 导入)

## 8. 绘图语言规范

### 5.1 Setup阶段

**Q: 如何指定激光相关参数？**
A: 在`flash.par`文件中设置`ed_*`开头的运行时参数。

**Q: Setup时如何设置最大脉冲/光束数？**
A: 使用setup选项: `./setup ... +laser ed_maxPulses=5 ed_maxBeams=6`

### 5.2 运行阶段

**Q: 如何查看激光能量沉积？**
A: 在Config文件中添加`REQUIRES VARIABLE lase`，然后在绘图文件中查看`lase`变量。

**Q: 如何输出激光射线轨迹？**
A: 在`flash.par`中设置`ed_useLaserIO = .true.`，输出将写入`<basename>LaserRaysPrint<PID>.txt`。

