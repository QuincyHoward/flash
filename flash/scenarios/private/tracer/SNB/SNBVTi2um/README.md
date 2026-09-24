# SNBVTi2um — V+Ti 多层示踪 + SNB（0.02µm 精确网格 + ★辐射开启）

## 定位

由 **SNBVTi2**（0.02µm 精确网格版）派生（2026-09-24）。
**几何/材料/激光/网格/SNB 参数与 SNBVTi2 完全一致**，唯一差异：

| 项 | SNBVTi2 | 本场景 SNBVTi2um |
|---|---|---|
| 网格 | iProcs=125 × nxb=200，dx=0.02µm 精确（0.1µm 薄层=5 整格） | 同 |
| 材料 | shld=V 6.11，tar2=Ti 4.54，其余 tar*=CH 1.0；cham=He 1e-6 | 同 |
| Driver | 作者原版（`call RadTrans` 被注释 → 辐射永不推进） | **radON 变体**（活 call RadTrans ×2） |
| par 三开关 | rt_useMGD=.true.（useOpacity 靠基线；**useRadTrans 缺失**） | **三开关全 .true.（显式）** |
| 辐射实际状态 | ❌ 实际关（trad 冻结在初值 290K） | ✅ 真正开启 |

依据：`SNB/SNB/docs/04_辐射开关.md` §2（三开关形同虚设陷阱 + radON 判据）；
2026-09-24 四场景核查结论（SNBOneCH_ml/SNBVTi2/SNBVTi2_ml 辐射实际未推进）。

## 与核心模块的联动（2026-09-24 起）

核心模块 `SNB/SNB` 已把"辐射开 ↔ radON 驱动"固化为默认行为：
- `snb_params.py`：`RADIATION` 三开关默认全 `.true.`；新增 `RADIATION_SWITCHES`。
- `gen_scene.py`：默认 `--driver-variant radon` + `--radiation on`；
  生成时断言 Driver 活 `call RadTrans`，拒绝"辐射开+作者原版驱动"组合。
- `run_scene.py`：运行前 `radiation_linkage_check()` 闸门（par 开关 ↔ Driver 变体）。

本场景自包含脚本沿用同一联动逻辑（`_deploy_snb_overrides` 强制 radON +
静态核验断言），与核心模块护栏互为冗余。

## 用法

```bash
cd <flash 包根目录>
PY=C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe

# ① 只生成输入文件（含辐射三开关 + radON 驱动静态断言）
$PY flash/scenarios/private/tracer/SNB/SNBVTi2um/SNBVTi2um.py --generate-only

# ② 本地 WSL 极短冒烟（tmax=1e-13；首次完整 setup+make）
cd flash/scenarios/private/tracer/SNB/SNBVTi2um/flash_input
TMAX=1.0e-13 bash run_flash.sh

# ③ 超算 NC-E 正式（极短验证 1e-11 / 全长 1.6ns 用 --tmax 覆写）
$PY flash/scenarios/private/tracer/SNB/SNBVTi2um/SNBVTi2um.py \
    --tmax 1.0e-11 --nproc 125 --account flash_ssh
```

## 辐射生效判据（跑完必查）

1. par 三开关：`grep -E "^(rt_useMGD|useOpacity|useRadTrans)" flash_input/snbvti2um.par`
   → 三行全 `.true.`；
2. Driver：`grep -c "call RadTrans(" flash_input/Driver_evolveFlash.F90` 且行首无 `!`；
3. **chk 实测**：`trad` 末帧明显高于初值 0.025 eV（辐射 ON 的铁判据，docs/04 §5）；
   SNBVTi2 同窗口对照 trad 应仍 ≈ 初值（两场景辐射差异的直接证据）。

## 文件

- `SNBVTi2um.py` — 自包含场景脚本（生成/静态核验/WSL 流水线/HPC 委托）
- `flash_input/` — 生成产物（Config/Makefile/Simulation_*/9 F90/cn4/par/run_flash.sh）
- `flash_output/` — 运行输出（按 tag 分目录）
