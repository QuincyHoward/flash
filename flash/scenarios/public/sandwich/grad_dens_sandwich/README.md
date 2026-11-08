# grad_dens_sandwich — 渐变密度 CH 靶

> 最后核对：2026-11-08 · commit c77b564

**一句话职责**：HE-CH-Si-CH-HE 渐变密度 CH 靶（超高斯脉冲；1D；auto = 平台自适应）

## 物理构型

- 1D 多层渐变靶：HE（低密度填充）— CH — **Si 芯** — CH — HE，密度沿层渐变（区别于 thin_layer 的阶跃分层）
- 驱动：超高斯脉冲激光（单束）
- 网格/EOS 与 sandwich 族同规范（nblockx=8 · nxb=16；Si/CH/He 三套 cn4 表）

## 目录结构（与 thin_layer_sandwich 同构）

| 文件/目录 | 说明 |
|---|---|
| `defaults.py` | 物理默认参数（域/层厚/密度/激光/时间控制） |
| `par_builder.py` | par 生成器（defaults → FLASH par） |
| `gen_flash_inputs.py` | sim_input 生成器（Config/F90/cn4/par/预诊断图；幂等，`--force` 重生成） |
| `sim_input/` | 生成的输入文件（非 py 不入库） |
| `run.py` | 薄启动器（去注册化三件套） |

## 运行

```bash
python run.py --tmax 1e-11      # 极短验证（dtinit/dtmax 随 tmax 自动收缩）
python run.py                   # 全程
python -m flash.scenarios.core.entry.cli run grad_dens_sandwich   # 统一 CLI
```

**上级导航**：[../README.md](../../../README.md)
