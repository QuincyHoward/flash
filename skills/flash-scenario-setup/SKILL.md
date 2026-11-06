---
name: flash-scenario-setup
description: SNB（多群非局域热传导）与 FL-SH 场景的全流程设置：setup 标志、par 参数清单（gr_hypreUseFloor/dtmax/限流器）、+ug 均匀网格与核数、辐射开关（radON 驱动）、dtmax 稳定性判据（读 chk 实测）、A/B 对比护栏、x-t 图 pcolormesh 纪律、SNB 分享红线。触发词：SNB 场景、SNB par、非局域热传导、gr_hypreUseFloor、dtmax、限流器、fl_harmonic、关辐射、radON、x-t 图、SNB 分享、SNB 崩塌。
---

> 最后核对：2026-11-06 · commit 72f6428

# SNB / FL-SH 场景设置（速查与操作指南）

详细长文见本目录 `references/`：
- `SNB_FLASH_reference.md` — SNB 工程参考全文（105KB）
- `flashsnb-build-and-deploy.md` — FLASHSNB 树级 6 补丁、编译报错速修、WSL/NC-E/BSCC 三机部署
- `end-to-end-workflow.md` — 端到端流程明细
- 仓库内可分享文档集：`flash/scenarios/private/SNB/SNB/`（README + docs/01..08 + scripts/）

## 1. 五条铁律（先记住，能省几小时）

| # | 铁律 | 违反后果 |
|---|---|---|
| ★0 | **`gr_hypreUseFloor = .false.`**（显式写入 par） | ★★★ SNB 崩塌真正主因。FLASH 默认 .true. → HYPRE 隐式扩散失真 → ρmax 崩塌、质量守恒破裂；dtmax 正确也照样崩 |
| ★1 | **`dtmax = 2.0e-14`** | dt 增长到 4.6e-14 越稳定阈值。**必要条件，非充分** |
| ★2 | **`diff_eleFlMode = "fl_harmonic"`** 仅声明意图 | SNB 路径上实测 **no-op**（各向同性分支限流调用被注释）；`fl_none` 逐位相同、不破坏守恒 |
| ★3 | **必须 `+ug` 均匀网格**，`mpiexec -n` **严格等于** `iProcs` | AMR 粗细界面破缺；核数不符挂死 |
| ★4 | **辐射：par 三开关 + SNB 腿必须用 radON 驱动** | 部分覆盖 F90 注释了辐射调用 → 设 .true. 也不涨（trad 差 1700×） |

**配套判据**（缺一不可）：
- 判据 A：dtmax 是否生效 → **读 chk 的 `real scalars` 里 `dt`**，不看 par 文本（par 会被 sed 覆写）。
- 判据 B：结果健康 → ρmax 走势 + 质量守恒。**dt 钳位正确 ≠ 结果正确**。
- 判据 C：配置溯源最强手段 → FLASH 启动日志参数回显差分（~前 1400 行，可解析 1200+ 键）。
- 判据 D：差异出现在第 1 帧 → 查初始/求解器配置，不往数值累积想。

## 2. Setup 与依赖

```bash
./setup -auto <SimName> -1d +cartesian +ug -nxb=128 +hdf5typeio \
        species=cham,tar1,tar2,tar3 +mtmmmt +laser +uhd3t +mgd \
        mgd_meshgroups=10 -objdir=<SimName>_obj
```

- `+uhd3t`（3T）—— SNB 作用在 tele 方程上；`+mgd` 的 `mgd_meshgroups=N` **必须 == par 的 `rt_mgdNumGroups=N`**；`rt_mgdBounds` 需 N+1 个边界。
- 全体物种 cn4 表**群数一致**；表温度下限须覆盖初值温度。
- 场景覆盖 F90 放 `<TREE>/source/Simulation/SimulationMain/<SimName>/`（放错位置**静默不生效**，看 objdir 软链接指向）。
- SNB 场景 9 个覆盖 F90 清单与自包含验收（部署单元 17 文件 + sha256 指纹）见 `references/SNB_FLASH_reference.md`。

## 3. par 参数速查

```par
# 热传导（核心）
useDiffuse = .true.   useConductivity = .true.
diff_useEleCond      = .true.
diff_eleFlMode       = "fl_harmonic"   # 声明意图（SNB 路径 no-op，见 ★2）
diff_eleFlCoef       = 0.06
diff_thetaImplct     = 1.0
diff_anisoCondForEle = .false.
dt_diff_factor       = 1.0e100         # 关扩散步长限制
useHeatexchange = .true.   hx_dtFactor = 1.0e100   rt_dtFactor = 1.0e100

# 时间积分
tstep_change_factor = 1.10
cfl = 0.2
dtinit = 1.0e-15   dtmin = 1.0e-16
dtmax  = 2.0e-14   # ★ 关键
tmax   = 0.8e-9

# 输出（以 chk 为主）
basenm = "<唯一前缀>_"   log_file = "<唯一>.log"
checkpointFileIntervalTime = 5.0e-11
plotFileIntervalTime       = 4.0e-10
# ★ 不要写 *IntervalStep —— 与 Time 是 OR 双触发，导致额外输出
# ★ plot_var 白名单 ≤ 12 项且从 1 连续编号；第 13 项起静默忽略

# 网格（+ug）
iProcs = 131          # 必须 == mpiexec -n
lrefine_max = lrefine_min = lrefine_min_init = 1
```

**+ug 分辨率三条路径**：① `-nxb=N` → `iProcs×N`；② 显式 `-nofbs` + par `iGridSize=M` → M；③ `iProcs` 本身。
⚠ 只"不给 -nxb"进不了非固定块模式（默认仍 NXB=8，iGridSize 被忽略）。
⚠ **薄层 0.1 µm ⇒ dx ≤ 0.03 µm 硬下界**（`sim_smallX=1e-99` 格心判据：dx>层厚则该层物种全空，相邻层直接贴爆）。
⚠ 核数伸缩**非单调**（实测 131 核 s/step=0.288 最快，192 慢 1.63×，256 失稳 ABORT——通信主导区，MGD+HYPRE 全局归约）。生产选 **131 核 + nxb=128 → dx=0.02982 µm**。

## 4. 辐射开关

```par
# 关（三开关全 .false.，源码零改动）；开则全 .true.（显式写回，别依赖继承）
rt_useMGD   = .false.
useOpacity  = .false.
useRadTrans = .false.
```

★ SNB 侧两腿都必须用**恢复了辐射调用的驱动**（radON 变体 Driver），再用 par 三开关开/关。`trad` 末帧 ≈ 初值（如 0.04 eV）而对照腿 60+ eV 即辐射调用被注释症。
★ ml 系场景 radON 化手术与 `_radiation_ready()` 静态核验（par 三开关全 .true. + Driver sha256 == radON 变体）见 `references/SNB_FLASH_reference.md`。

## 5. 端到端流程（骨架）

1. 导入源件：`import_sources.py --from <作者包> --also-stock <参考版>`
2. 生成场景：`gen_scene.py --out <场景> --legs snb,flsh --radiation on`（受控性自检 + 键集差分）
3. **先短时验证**：`tmax=1e-11`，通过后再恢复正式 tmax
4. 正式运行：`run_scene.py --scene <场景> --side snb`（树自动探测；构建指纹不符/缺 flash4 时强制 setup+make）
5. 判健康：`chk_probe.py --expect-dtmax 2e-14`（dt 钳位 + ρmax + 守恒）
6. 分析绘图：`flash.output_pro`；**x-t 图必须 pcolormesh + 真实逐帧时间坐标（禁 imshow）**
7. 分享前自检：`check_share_safety.py` 必须 exit 0

## 6. 分享规则（SNB 专用）

**原则：分享方法，不分享实现。**

| 类别 | 处置 |
|---|---|
| F90 源码及变体（variants/） | ❌ 不分享 |
| 会写入/生成 F90 的 py 脚本 | ❌ 不分享 |
| 逐字引用 F90 算法片段的文档 | ❌ 不分享 |
| par / 驱动·分析·绘图 py / 说明文档 | ✅ 分享 |
| 凭据 / 密钥 / 账号 | ❌ 永不入库 |

提交前强制：`python flash/scenarios/private/SNB/SNB/scripts/check_share_safety.py`（类型闸门 + 目录闸门 + 内容闸门，缺一不可）。

## 7. 常见症状 → 首查

| 症状 | 首查 |
|---|---|
| `Negative 3T internal energy` | ★1 dtmax ≤ 2e-14 |
| 内能/质量异常 | 先分腿：限流 SH 腿才可能是限流器问题；SNB 腿改查 ★0 gr_hypreUseFloor |
| `trad` 冻结在初值 | ★4 辐射调用是否被注释（换 radON 驱动） |
| `Cannot open module file 'xxx.mod'` | 覆盖文件模块名与树内不一致；或该模块未先编译 |
| 分辨率改了没效果 | +ug 忽略 nblockx/lrefine；非固定块需显式 -nofbs |
| 白名单变量没输出 | plot_var 上限 12 |
| 换表后跑不动 | cn4 表温度下限未覆盖初值 |
| x-t 图两腿"前沿速度不同" | ★★ 绘制 bug：imshow 假设等间隔（实测 Δt 差 52.7×），必须 pcolormesh + 真实时间坐标 |
| 与别人的图数值对不上 | ① 数据源 md5 对拍 ② 直接读对方中间产物 ③ 显示约定。先查这三项 |

## 8. 五类结构性根因（2026-09-12 定案）

A 两层目录职责重叠（~35%）/ B 参数三副本：模板 par、部署 par、运行时 par（**FLASH 只认 objdir 内被 sed 改过的那份**）（~25%）/ C +ug 隐式约束不报错只给错果（~20%）/ D 静默失败：plot_var 上限、收集未校验即删、chk 键全小写（~15%）/ E 平台差异 WSL·NC-E·BSCC（~5%）。

**三条元纪律**：M1 穷尽哈希比对再解释（中文路径用 `git ls-files -z`）；M2 单变量 A/B（一次只改一键）；M3 读实测值（chk 的 `real runtime parameters`），不读文本。
