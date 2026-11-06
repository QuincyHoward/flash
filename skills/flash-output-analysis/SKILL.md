---
name: flash-output-analysis
description: FLASH HDF5 输出（chk/plt）分析：FlashDataLoader/FlashPlotter 用法、+ug chk 布局与逐格 x 重建、质量守恒积分、x-t 时空图 pcolormesh 纪律、chk 健康检查四判据、边界热伪迹判据。触发词：HDF5 分析、chk 读取、plt 读取、x-t 图、时空图、pcolormesh、质量守恒、逐格坐标、bounding box、健康检查、边界伪迹、FlashDataLoader、FlashPlotter。
---

> 最后核对：2026-11-06 · commit 14e320f（skill 巡检：分工声明补齐）
> 分工：本 skill 管**分析与绘图纪律**；无 yt 环境的底层提取/批读提速用 `flash-data-extract`。

> API 逐方法速查：`references/output-api.md`（三层架构 FlashHDF5File/DataCalculator/FlashDataLoader/FlashPlotter 全签名，2026-11-06 自旧 output_processors 技能校正迁入）

# FLASH 输出分析与绘图纪律

代码锚点：`flash/output_pro/`（hdf5pro → loader → plotter）、`extraction_modes.py`、`parallel.py`。
物理量字典：`flash/output_pro/FLASH物理量说明.md`。

## 1. 标准入口

```python
from flash.output_pro.loader import FlashDataLoader
from flash.output_pro.plotter import FlashPlotter

loader = FlashDataLoader("sim_output/chk_0039")
data = loader.load("dens", compute_derived=True)   # 结构化容器（含单位/派生量）

plotter = FlashPlotter()
plotter.plot(data)                                 # 自适应 1/2/3D
```

- 提取模式注册表：`extraction_modes.get/set/resolve_extraction_mode`（yt-style 等）。
  场景快检脚本用 `extraction_mode="yt"`，**禁裸 load()**。
- 批量读取用 `parallel.ParallelProcessor`（按内存/文件大小自适应 worker 数）。
- 单位换算：`plasmapy_bridge.to_quantity`（vendored PlasmaPy 2026.2.0，未安装自动降级）。
- 测试基线：`python -m pytest flash/output_pro -q --ignore=flash/output_pro/PlasmaPy`（57 passed）。

## 2. ★ x-t 时空图必须 pcolormesh（不可 imshow）

FLASH chk 帧由 `checkpointFileIntervalTime/Step` 触发，**Δt 高度不均**
（实测 AMR 腿 1.36e-12…7.19e-11，**52.7×**；+ug 腿恒定）。
`imshow` 假设等时间间隔 → 时间轴局部拉偏最多 **~3500%** →
"两腿前沿速度不同"假象。**必须**：

```python
X, T = np.meshgrid(xg, ts * 1e9)
plt.pcolormesh(X, T, field)          # 真实逐帧时间坐标
```

定位手段：打印各腿 Δt 的 max/min。彩图冷区"一片平"→ 检查固定色标下限（如 `value_lim=[1e18,1e24]`），
`nele` 冷区可低至 ~1e14，宜放宽下限或自动范围。

## 3. ★★ +ug chk HDF5 布局（权威，实测）

```python
"real scalars"     (11,)  结构化 [('name','S80'),('value','<f8')]   # name 空格填充 bytes，须 .strip()
"integer scalars"  (15,)  结构化 [('name','S80'),('value','<i4')]   # 含 nxb/nstep/globalnumblocks
"coordinates"      (nb,3) float64  # ★ 块中心 x (cm)，非逐格
"block size"       (nb,3) float64  # 块宽 (cm)
"bounding box"     (nb,3,2) float64  # ★ 逐块真实 [x_lo, x_hi]
"refine level"     (nb,)  int32     # +ug 下全为 1
变量 (dens/tele/tion/trad/eint/ye/...)  (nb,1,1,nxb)   # 须展平
```

**逐格 x 重建（关键坑）**：`coordinates` 是块中心，块宽 `W = bbox[:,0,1]-bbox[:,0,0]`，
**W ≠ nxb·dx**。用 `x_block ± (nxb-1)/2·dx` 重建会外扩约 2% → x 序列非单调、质量积分错乱
→ 误报"质量不守恒"。正确写法：

```python
W = bbox[:, 0, 1] - bbox[:, 0, 0]                       # 逐块真实宽度
x = bbox[:, 0, 0][:, None] + W[:, None] * (np.arange(nxb) + 0.5) / nxb
mass = np.sum(dens * (W / nxb)[:, None])                # 面密度 [g/cm^2]，守恒到 1e-16
```

★ 质量积分必须 `Σρ·(W/nxb)`；误用 `W` 而非 `W/nxb` → 结果大 nxb 倍。

## 4. chk 健康检查四判据

1. `t` 不倒退（`diff >= 0`；plt 与同 t chk 并存 → 严格 `>0` 会假警报）
2. 质量漂移 < 1e-6（**开放边界语义**：不判闭箱守恒，判单调下降 + 单帧变幅 <30%；
   容差 1e-6——chk 存 float32，1e-12 会把舍入噪声误判为"质量回升"）
3. `eint_min > 0`
4. skipped == 0

★ 分析代码必做：`find_frames` **排除 `*_forced_*` / `*_rst_*` / `*_prt_*`**
（`_forced_` 是部分域 dump，混入序列会产生质量"漂移"假警报）。
★ `tele` **本就是 eV**，不要再除 K_EV（重复除会得出 Te_max=0.079 荒谬值）。

## 5. ★★★ 边界热伪迹判据（长跑定案，最高优先级）

**症状**：稀疏波前沿抵达开放边界后，被抽空区（ρ→1e-6）温度反而飙升。

**三条判据（合并使用，任一不满足即不可判伪迹）**：
1. 质量单调流出 + 内能暴涨 >100× 同现（单独质量下降可能是物理稀疏化）
2. 三站位 Te"同涨同落"：边界与中域逐帧同步，近驱动区低 4 个量级（真等离子体不可能）
3. `eint/nele` 与 `Te` 跨幅一致（不一致 → 是 ye/电离态问题）

机理：激光 + 非局域热流持续加热近真空胞，`eint/ρ` 发散；ρ→0 时 mfp > 域尺寸，**模型越出适用范围**。
⇒ **左半域触边后温度数据一律不得用于示踪反演**。候选修复：密度/能量地板、出流面外移、tmax 截到触边前。

## 6. 数据对拍纪律

与别人的图"数值对不上"时按序查：① **数据源 md5 对拍** ② **直接读对方中间产物**（预抽 H5）取同 (t,x) 切片
③ **显示约定**（色标范围/坐标限幅/插值）。**先查这三项，别先怀疑提取代码**。

## 7. 常见坑速查

| 症状 | 根因 |
|---|---|
| 找不到 HDF5 键 | chk 键**全小写**；`real scalars` 是记录数组 (name, value)；生效值在 `real runtime parameters` |
| h5py 打不开 md5 一致的 chk | FLASH chk 并非全部可被 h5py 打开 → **完整性只认 md5**，绝不用 h5py 可打开性 |
| 物种分数异常小 | `sim_smallX = 1e-99` 是默认填充值，不是物理值 |
| float32 统计溢出/NaN | np.std 等在 float32 上运行溢出 → 先 `.astype(np.float64)` |

## 关联资源

- `flash/output_pro/README.md`、`hdf5pro/README.md`、`loader/README.md`、`plotter/README.md`
- `flash/output_pro/FLASH物理量说明.md` — 物理量字典（795 行）
- skill `flash-data-extract`（无 yt 环境纯 h5py 提取）、`flash-backup-verify`
- `docs/flash_operation_standard.md` — 绘图规范（全英文、字号 ≥18pt）
