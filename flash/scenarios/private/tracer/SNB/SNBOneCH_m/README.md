# SNBOneCH_m — SNBOneCH_ml + 辐射开启

**派生**: 2026-09-24, 自 `SNBOneCH_ml`（纯 CH 8 物种基线, 131 核 +ug dx=0.0298 µm）。

**唯一差异 = 辐射真正开启**（SNBOneCH_ml 的 Driver 是作者原版，`call RadTrans`
被注释 → trad 冻结，辐射从未推进）：

1. **Driver = radON 变体**: `flash_input/Driver_evolveFlash.F90` 为核心模块
   `SNB/SNB/variants/Driver_evolveFlash_radON.F90`（301/325 行 `call RadTrans`
   活调用），自包含归档，`run_hpc` 打包本地优先全量入单元包；
2. **par 三开关全开**: `rt_useMGD=.true.` + `useOpacity=.true.` +
   `useRadTrans=.true.`（ml 缺 `useRadTrans` 键）。

其余物理（几何/物种/材料/激光/EOS 表/网格 131×128）与 SNBOneCH_ml 逐项一致。

## 场景对照矩阵（辐射判据 = `SNB/SNB/docs/04_辐射开关.md`）

| 场景 | 材料 | 核数/dx | 辐射 |
|---|---|---|---|
| SNBOneCH_ml | 纯 CH | 131 核, dx=0.0298 µm | **关**（作者原版 Driver） |
| **SNBOneCH_m** | 纯 CH | 131 核, dx=0.0298 µm | **开**（radON + 三开关）← 本场景 |
| SNBVTi2um | V+Ti 示踪 | 125 核, dx=0.02 µm | 开（同法, 2026-09-24 已验证） |

- SNBOneCH_m vs SNBOneCH_ml = **辐射开/关对照**
- SNBVTi2um vs SNBOneCH_m = **材料对照**

## 内置护栏

`_radiation_ready()`（main 生成后强制执行，--generate-only 亦检查）：
① par 三开关全 `.true.`；② flash_input Driver 与 radON 变体 sha256 一致
（变体缺失时兜底：活 `call RadTrans` ≥ 2）。任一失败即中止——
**只改 par 不换 Driver，辐射求解器根本不会被调用**。

## 用法

```bash
cd <flash 包目录>
# 生成 + 静态核验
python flash/scenarios/private/tracer/SNB/SNBOneCH_m/SNBOneCH_m.py --generate-only
# 超算 NC-E 极短验证（首次必须完整编译, 勿加 --skip-build）
python flash/scenarios/private/tracer/SNB/SNBOneCH_m/SNBOneCH_m.py \
    --mode hpc --account flash_ssh --nproc 131 --tmax 1.0e-13
# 1.6 ns 完整仿真（NC-E 131 核, 轮询上限 12h）
python flash/scenarios/private/tracer/SNB/SNBOneCH_m/SNBOneCH_m.py \
    --mode hpc --account flash_ssh --nproc 131 --tmax 1.6e-9 --poll-timeout 43200
```

**辐射生效判据**（极短验证后）: chk trad 末帧明显高于初值 231.3 K（≈0.02 eV）
——对照 SNBOneCH_ml 同窗口 trad 应冻结在初值。

## F90 归档说明

`flash_input/` 9 个 F90 中 8 个与上游 SNB_1D_laser 逐字节一致（License §3
不入 git 库）；`Driver_evolveFlash.F90` 例外 = radON 变体。详见
`flash_input/SNB_F90_PROVENANCE.md`（含 2026-09-24 差异段）。
