# SNB / FLASH 工程参考（细节层）

> 从 `MEMORY.md` 下沉而来的**详细版**。`MEMORY.md` 只留高频规则与指针（注入体积上限）；
> 需要数值、源码行号、完整表格时读本文件。
> 建立于 2026-09-12。

---

## 1. SNB 失真/崩塌的权威根因（四版才定案）

| 版本 | 假说 | 结论 |
|---|---|---|
| v1 | 各向同性分支限流器被注释 | ❌ 推翻（t004/t005/t006 该文件逐字节相同，解释不了差异） |
| v2 | radON 驱动导致崩塌 | ❌ 推翻（t004 用的就是 radON） |
| v3 | `dtmax` 用成 2e-12 | ❌ 不充分（t006 dtmax=2e-14 仍崩） |
| **v4** | **`gr_hypreUseFloor` 退回默认 `.true.`** | ✅ **根因**（单键 A/B 与基线逐位相同） |

**三条并列前提（缺一不可）**

1. **`gr_hypreUseFloor = .false.`** — 真正主因。HYPRE 隐式扩散 floor 开 → SNB 多群解失真
   → 过度压缩 → ρmax 冲高后崩塌（12.1 → 0.26）。
   ★★ 作者示例 par **本来就写了该键**（`SNB_1D_laser/flash.par:464`）——
   是我们从零生成 par 时**丢了它**。
2. **`dtmax = 2.0e-14`** — 必要条件，非充分条件（作者原值 `2e-12` 配 AMR lrefine6 才够）。
3. **SNB 腿 `driver-variant = radon`** — 作者原版把 `call RadTrans` 注释了，辐射永不推进。

**两条判据铁律**

- ① `dtmax` 是否生效**看 chk 的 `real scalars` 里 `dt` 实测值，不看 par 文本**；
- ② **`dt` 钳位正确 ≠ 结果正确**，还须查 ρmax 走势与守恒。
- 最强溯源手段 = **参数回显差分**（~1231 键）。

**路径相关性**：`gr_hypreUseFloor` 在 SNB 侧造成 **1.6× 物理级差异**；在 FL-SH 侧单变量 A/B
实测最大相对差仅 **≤9.0e-4** → 现有 FL-SH 结论可用（引用时注明 ≤0.1%）。
**不能因 SH 侧小就认为它普遍无害。**

---

## 2. `diff_eleFlMode` 在 SNB 电子路径上是 no-op（实测）

改 `"fl_none"` 后六物理量（dens/tele/tion/trad/pele/pres）逐帧最大绝对差
**全为 `0.000000e+00`**（短时 11 帧 + 全长 17 帧两尺度一致）。

**原因**：`source/snb_package/diff_advanceTherm.F90` 各向同性电子分支的限流器调用（`:839`）
与 SH 传导解（`:847`）**都被注释**；场景 `diff_anisoCondForEle=.false.` → 不进入各向异性
分支（`:818` 也不进入）→ **无存活消费者**。

```
838|     else   ! Do isotropic conduction/diffusion
839|!        call Diffuse_fluxLimiter(COND_VAR, Temptodiffuse, FLLM_VAR, ...)
847|!        call Diffuse_solveScalar(Temptodiffuse, COND_VAR, DFCF_VAR, ...)
```

**推论**：`fl_none` **不会**破坏 SNB 守恒；保护 SNB 的是 **SNB 多群非局域公式本身**
（以无界 Spitzer 电导 `:364` 为基准 + `mgd_qesh` 能量分数 + 群 mfp 做非局域修正）。
`docs/05` 的 **P1 已更正**。`fl_harmonic` 从"保护措施"降为**声明意图**（对离子腿 `:991`
与 `FLLM_VAR` 诊断量仍有作用）；现默认 `fl_none`。

---

## 3. SNB 模块细节

### 3.1 原始参考实现 `SNB_1D_laser`

- AMR **lrefine 6**、`dtmax=2e-12`、`plot_var` **15 项**（>12 → 13+ 静默忽略）、
  **chk 未开启**、**无 `useRadTrans`**。
- 示例 setup 就是 **`species=cham,targ`**。
- **18 个 SNB 诊断 `VARIABLE`** 与 `REQUESTS Conductivity/SpitzerHighZ` 是覆盖件能编译的**前提**。
- 几何 = 体靶 `x∈(-50,0)` µm + 2 个 0.1 µm 表面标记层 + `(-2.2,-2.1)` 埋入标记层。
- 详见 `SNB/SNB/docs/09_原始参考实现与当前设置.md`（原版全设置表 + 改动对照表）。

### 3.2 模块默认值（2026-09-12 起）

`diff_eleFlMode = "fl_none"`、辐射默认**开**、`--driver-variant` 默认 `radon`；
`gen_scene.py` 新增 `--ele-fl-mode`；`run_scene.py` 新增 `--tables` / `--pulse-sections`。

### 3.3 构建指纹 → 首次使用场景强制重编译

objdir 名由 `LEG_SPECS` 固定（`SNB_SCENE_obj`）→ **不同场景复用同一 objdir**；沿用旧
`flash4` 会把别的场景的二进制当成当前结果（**静默错误**）。现以 `flash_input/` 全文件内容
+ setup 参数的 **SHA256** 记入 objdir；不一致或缺 `flash4` → **无视 `--skip-setup/--skip-make`
强制 setup+make**。

### 3.4 用 input_gen 生成 SNB 场景的 Config：**以 SNB 包 Config 为基座**

`ConfigGenerator` 只产物种参数，**缺** SNB 包的 `REQUESTS` 与 18 个诊断 `VARIABLE`
→ 编译期报一串 `Symbol 'qesh_var' at (1) has no IMPLICIT type`。
正解：以 `source/snb_package/Config` 为基座 → 替换 `DATAFILES` → **追加**未声明的物种参数。
另须给 Makefile 补 `mgd_qesh.o`。★ `ZMin` 的 par 键是 **`sim_zmin<Cap>`**，不是 `ms_*ZMin`。

### 3.5 分享与保密

**分享红线**：不分享 F90 源码；可分享 py，但**不可分享会生成/复制 F90 的 py**；
不分享逐字引用算法片段的文档。可分享：par 配置 / 驱动·分析·绘图 py / 说明·流程文档。

**★ gitignore 反模式**：白名单绝不能放行"源码类型"。`**/*.F90`、`**/*.f90` **一律全忽略**；
另加 `**/Test/t00*/variants/`。验证：`git add -n --all | grep -icE '\.f90'` 必须 = 0。
检查器三闸门（类型/目录/内容）缺一不可；须先剔除 F90 **文件名**再扫内容，否则误报。

**检查器两个历史漏洞（已修）**：① 扩展名漏项（`.f95/.f03/.f08/.fpp`）→ 类型闸门补齐
+ 内容闸门改**二进制黑名单**（消除"未知即放行"）；② **已暂存内容不可见（致命 fail-open）**
→ 待提交集合改为 `git diff --cached` ∪ `git ls-files --others` ∪ `--modified` 三路并集；
git 查询失败改 **fail-closed**（返回 2）。详见 `docs/06` §8。

---

## 4. 场景与参考结果

### 4.1 `tracer/SNB/SNBOneCH`

OneCH_ml 几何/材料 + SNB，**cham+targ 两标记**，`+ug` iProcs16×nxb128（2048 格，
dx=0.244 µm），域 `[-0.04,0.01] cm`，固体靶 `0→56.1 µm` CH 1.0，He 1e-6，82 段激光，
表 `He-BADGER + CH-QC-1-001`。

- smoke（tmax=1e-11）11 帧 / **14.2 s**；
- **full（1.6 ns）81 帧 / 3608 s**，`dt` 全程钳位 2e-14，总质量漂移 1.82e-11，
  ρmax 1.0→峰 6.57→末 1.97（平滑衰减，非崩塌）。
- FL-SH 侧用 `OneCH_ml/.../run_000001`（317 帧 chk，t→1.6001 ns，含 pele）→ 两腿数据源
  统一为 **chk float64**。
- 1.6 ns 对比：nele_max 1.4568e23 vs 1.4941e23（+2.6%）、tele_max 1534.63 vs 1510.96 eV（−1.5%）、
  pele_max 11.085 vs 11.040 Mbar（−0.4%）→ **全域极值 ≤3%**，剖面 ≤3.2%。
- 对比图 `plot_compare_onech.py`（x-t 每列共享色标）。

### 4.2 t006 五腿（tmax=0.8 ns，`+ug` 1024 格，dtmax=2e-14，chk 源）

| 腿 | x_a[µm] | Ṁ[g/cm²/s] | ρmax | Te_max[eV] | Trad_max[eV] |
|---|---|---|---|---|---|
| SNB radON (fl_harmonic / fl_none **两者逐位相同**) | −31.69 | 5.3393e5 | 12.111 | 1513.1 | 68.538 |
| SNB radOFF | −34.03 | 6.3882e5 | 12.231 | 1522.1 | 0.047 |
| FL-SH radON | −31.10 | 5.0346e5 | 6.739 | 1649.7 | 63.110 |
| FL-SH radOFF | −31.69 | 4.8139e5 | 6.731 | 1655.2 | 0.132 |

- **辐射开关效应方向相反**：FL-SH 关辐射 **0.956×**（减速）；SNB **1.196×**（加速）。
- **模型效应**：辐射开 SNB/FL-SH = **1.061×**；关辐射 = **1.327×**。
- ⚠ **未解**：SNB `ρmax ≈ 12.1` vs FL-SH `≈ 6.7`（**1.8×**），开/关辐射都成立 → 与辐射无关，
  **成因未定位**。（完整表/图见 `t006/docs/对比_SNB3_SH2.md`）

### 4.3 辐射开关

- **权威机制**（`tracer/VCH_ml_F/VCH_ml_F.py:300-303`）：**纯运行时 par 三开关**
  `rt_useMGD`/`useOpacity`/`useRadTrans`，源码/setup/编译**逐字节不变**。
- ★ **SNB 侧陷阱**：作者 `Driver_evolveFlash.F90:301,325` 的 `call RadTrans` **被注释**
  → 辐射永不推进、三开关形同虚设 → **必须用 radON 驱动变体**。

### 4.4 SNB 实现包缺陷清单（源码级）

限流器调用被注释（`:839/:847`，**非**崩塌根因，使 `diff_eleFlMode` 成 no-op）· 辐射被关闭
（`Driver_evolveFlash.F90:301,325`）· D1 λ_g 旁路（`:456-458` 算出不用；⚠ **恢复反而更不稳**）·
`:253` 先用后赋 · **启动失稳真因 = `dtmax` 过大**（与 λ_g 无关）· 打包未打补丁
（QENL 缺续行符 / `hy_uhd_*` 旧模块名 / `mgd_qesh.F90` 原缺失）·
★ `variants/..._limiterON.F90` **名不副实**（六个调用点与 `snb_package` 完全相同）。
详见 `docs/05` / `docs/09`。

---

## 5. FLASHSNB 构建基线

- SNB 尝试**必须在 FLASHSNB**（`/root/QC/FLASH/FLASHSNB/FLASH4.8`，objdir `SNB_SCENE_obj`）；
  FL-SH 腿用标准树 `/root/QC/FLASH/FLASH4.8`（objdir `FLSH_SCENE_obj`）。
- **6 补丁**（新 SNB 场景报错按序查）：① `diff_advanceTherm.F90` QENL 续行符；
  ② 场景 Makefile 补 `mgd_qesh.F90`；③ `Diffuse_computeDt`；④ `hy_uhd_getFaceFlux`
  的 Conductivity 按 aniso 分流；⑤ `hy_uhd` 用 `hy_slopeLimiters`；⑥ par `iProcs`。
- 接口：FLASHSNB = 增强泛型（6 参数旧版 + 标量 fullState + anisoFullState），泛型不匹配
  **修调用方勿改接口**。`-j4` 竞态：先单独 make 模块 `.o`；旧 `.mod` 需 rm 强重编。
- **铁律**：改 Fortran 源**用 Python 二进制模式**（perl `s/\s*$/…/` 会损坏文件）。
- ★ 覆盖文件权威来源 = WSL FLASHSNB 工作副本（含 6 补丁）；原始包源未打补丁。
- FLASH 输出（plt/chk/dat/log）**用后即转** `flash_output/`。

---

## 6. `+ug` 均匀网格铁律

- ★★ SNB 非局域热流跨平均自由程积分，**AMR 粗细界面是破缺点** → 必须 `+ug`
  （"要分辨率就 AMR"的旧结论作废）。
- `+ug` 下 par 的 `nblockx`/`lrefine` 被**无视**，UG 一块一进程 → `mpiexec -n` **必须 == iProcs**。
  分辨率三路径：① `-nxb=N` → 总格数 = iProcs×NXB；② 显式 `-nofbs` + par `iGridSize=M`
  → 与核数解耦；③ `iProcs`。
  ★ **坑**：只"不给 `-nxb`"进不了非固定块模式（默认仍 `FIXEDBLOCKSIZE` NXB=8，
  `iGridSize` 被静默忽略）。`-nofbs` 强制并行 HDF5 IO，与 `+serialIO` 冲突（SETUPERROR）。
- 实测：分辨率 ×2 价格 ≈ **4.2×**；2048 格（iProcs16×nxb128）跑 1.6 ns ≈ **3600 s**。
- 启动瞬态稳定化：AMR 细网格 `tstep=1.05`+`dtmax=2e-14`；`+ug` 场景 `tstep=1.10`。

---

## 7. 数据提取与绘图

### 7.1 一律走 `flash/output_processors`

```python
FlashDataLoader(path).load(compute_derived=False, extraction_mode="h5py")
    → 只取 node_type==1 叶子块（★ AMR 必需；默认 load() 会混入父块陈旧数据且坐标错位）
DataCalculator(container.data).compute("nele") / ("nion")   # 项目 DATA_CONFIG 权威公式
```

**权威派生量**（`hdf5processor/flash_hdf5.py`）：`nele = ye*dens*NA`、
`nion = sumy*dens*NA`、`zbar = ye/sumy`；`NA = 6.02214076e23`。
**禁止自己手写这些公式** —— 统一后新旧结果仅差 ~0.04%（NA 常数精度）。

### 7.2 `nele` 与 `dens` 形态差很多是**物理**，不是提取错误

`ye` 是**电离态相关**的电子丰度（mol e⁻/g，由 EOS 给出），不是常数：
室温冷 CH `zbar≈0.001`（几乎中性）→ `nele≈1e14`；加热到 `zbar≈3.5` 才到 `1e23`。
⇒ `nele` 比 `dens` 多数个十进跨度。**用固定"完全电离"Z/A 会差 2 个量级以上。**

★ **显示坑**：固定色标（如 `value_lim=[1e18,1e24]`）会把 t=0 冷态（~1e14）
压成同一个最暗色 → 早期结构看不见；宜放宽下限或用自动范围。

### 7.3 chk vs plt

**定量分析/绘图一律用 chk**（71 键 / **float64** / 无变量上限）；plt 仅作健全性检查
（~25 键 / float32 / `plot_var` 白名单**硬上限 12**，第 13 项起静默忽略）。

- ★ **chk 与 plt 布局相同**；`+ug` 下**所有块都是叶子块**（`node type` 每块标量恒=1）
  → **无需 leaf 过滤**（与 AMR 根本不同）。`coordinates (nb,3)`＝**块中心**；变量
  `(nb,1,1,nxb)`；重建节点坐标 `linspace(bbox_lo,bbox_hi,nxb+1)`，每块**左闭右开**。
- ★ `unknown names` 是变量清单权威来源，但其元素是 repr 定宽字符串 → **存在性用 `key in f`**。
- ★ `real scalars` 是**复合 Dataset**（非 Group）→ 需 `dtype.names` + 属性兜底。
- ★ `plot_var` 是纯运行时参数（`IO_init.F90:240`）→ 改白名单**无需重编**。
- ★ `plotFileIntervalStep` 与 `plotFileIntervalTime` 是 **OR 双触发**（`IO_output.F90:367`）；
  chk 间隔可直接当时间分辨率旋钮（<1 s/帧）。
- **绘图坑**：`plt.get_cmap`（`cm.get_cmap` 已移除）；`np.trapezoid`（`np.trapz` 已移除）；
  `imshow` 的 `extent` 显式给时刻 + `origin="lower"`；**横向对比必须每列共享色标**，
  逐腿定标时**文件名必须区分**（否则静默覆盖）。

### 7.4 ★★★ x-t 图不能用 `imshow` —— FLASH chk 帧间隔不均

chk 由 `checkpointFileIntervalStep` 触发 → Δt 随 dt 变化。实测：
`+ug` 腿 81 帧 Δt 恒定 2e-11（1.00×）；**AMR 腿 317 帧 Δt 1.36e-12…7.19e-11（52.7×）**。
`imshow` 假定各行在 extent 内等间距 → 时间轴局部拉偏最多 **~3576%**，
使**同一物理运动在两腿上"显得前沿速度不同"**。

⇒ **必须 `pcolormesh` + 真实逐帧时间坐标** `np.meshgrid(xg, ts*1e9)`。
已统一修正：`output_processors/plotter/plot_generator.py`（新增 `plot_xt_map` / `collect_xt` /
`time_uniformity`，并自动警告非均匀 Δt）、`SNB/scripts/analysis/compare_4way.py`、
`t006/flnone_test/plot_5leg.py`、`SNBOneCH/plot_compare_onech.py`、`Test/t00{2,3,4}/…`。
定量验证：阈值法 `x_c(t)` 三方速度 +0.0803 / +0.0796 / +0.0853 µm/ps（差 ≤7%）。

---

## 8. 场景快速验证规范

- 首跑 `tmax=1.0e-11`；通过后恢复规范 tmax。
- tracer 家族：`tracer/private/` OneCH_ml / VCH_ml / CHTi(_F) / VCH_ml_F / OneSi_ml(_F) /
  OneC_ml(_F) / TiTi(_n)；派生用 `build_*_family.py`；par 数值注入用 `repr()`。

## 9. HPC

- sbatch `--output=~/{dir}/x` **不展开波浪号** → 用相对路径。
- `route_key` 是 `"nc_e"`/`"bscc_t6"`（**非**账号名）。
- BSCC v6_384 需补 `LD_LIBRARY_PATH=/public1/soft/miniforge/24.11/lib`。


---

# 附录（2026-09-12 从 MEMORY.md 下沉，保持 MEMORY.md 在体积预算内）

## §A. Windows SSH 传输必须走 paramiko

**事故（2026-09-12）**：`RemoteSession.__enter__` 在 Windows 上 3 次重试全 `Timeout`，
但同刻 paramiko 直连 **2.7 s 成功**。

| 测试 | 结果 |
|---|---|
| `ssh` CLI + `SSH_ASKPASS`（.bat 注入密码） | **TIMEOUT 40 s** ❌ |
| `ssh` CLI + BatchMode（无 askpass） | rc=255, `Permission denied` |
| **paramiko 直连（进程内密码认证）** | **rc=0, 2.7 s** ✅ |

**根因**：Windows 下 `SSH_ASKPASS` 不被触发（无 tty 判定 + `DISPLAY` 无效）→ 密码提示被
跳过 → 会话挂起至超时。TCP 握手正常（~70–110 ms），所以**路由测试报 OK 但命令必超时**——
这是最容易误判为"网络抖动"的假象。

**修复**：`flash/scenarios/flash_demo/demo_hpc/remote_ssh_helper.py` 加 **paramiko 后端**，
`_use_paramiko()` = Windows 默认 True（`FLASH_SSH_BACKEND=cli` 可强制回退 CLI）。
三个传输点已分流：`ssh_cmd` / `scp_upload`（→`_paramiko_put`）/ `scp_download`（→`_paramiko_get`），
SFTP 自动建远端父目录。实测：连接尝试 1 成功、SFTP 上传/下载往返一致。
★ 备份留存 `remote_ssh_helper.py.bak_<ts>`。

**排查口诀**：HPC 报 SSH 超时 → 先看 TCP 是否 OK；**TCP OK 而命令超时 = askpass 失效**，
不要归因于网络。

---

## §B. 工程坑（通用）

1. ★★★ **含 `$`/反引号的文本一律 Write 落盘，不经 shell**：① `wsl bash -lc '…$VAR…'` 里
   shell 变量**展开为空**（曾把文件写到 E: 盘根目录）；② `bash -c "python -c '…'"` 里
   **反引号被命令替换吞掉**（实测整段被抹）。`wsl` 里 `grep/tail/head/ls/rm` 常不可用 → 用 Python。
2. **日志名带 tag 前缀**（否则 smoke/full 同名 → 误读旧 `RUN_EXIT=0`）；**收集先校验后删**
   （本地 chk>0）；**`run_leg` 一律关键字传参**；`rm -rf` 被沙箱 `[safe-delete]` 拦截
   → 改**不删除、幂等重跑**。
3. ★★ **A/B 比对两条护栏（缺一不可）**：帧**按时间戳配对**（按序号曾把 t=1e-12 与 1e-11 比，
   得出 tele 相对差 0.97 的**虚假差异**）；比对前做 **par 键级差分**（曾拿缺 `gr_hypreUseFloor`
   的 smoke 当基线 → 一次改两个变量）。
4. ★ **已废弃数据**：`sim_snb/smoke_*` 与 t006 早先的 `*_smoke.png`、`summary_4way_smoke.md`
   产于 `gr_hypreUseFloor` 修正**之前**，**勿再作基线**。
5. ★★ **"看起来像崩塌"必须先与对照腿同窗口比对**：ρmax 6.57→1.97 曾被判"崩塌"，实为
   **物理稀疏化**（`dt` 全程钳位、单帧最大跌幅仅 5.9%，且 FL-SH 同窗口跌得更多）。
   ⇒ 判据 = **单帧相对跌幅 > 30%**。
6. ★★ **不要凭共享色标的 x-t 图目视判断前沿位置**（曾据色图判"SNB 前沿更深 −58 vs −38 µm"，
   阈值法实测两模型末帧都已到域边界 −400 µm、差 0.37 µm → 该时刻已饱和、无判别力）。
7. ★★ **"两边图不像"按序查三项，别先怀疑提取代码**：① **数据源**（清单 + md5）；
   ② **数值**（读对方中间文件取同 (t,x) 切片）；③ **显示约定**（**固定色标范围**最常见）。

---

8. ★★★ **判 HPC 作业"是否真在算"必须看三处, 只看 `run_%j_out.txt` 会误判**:
   ① `squeue`/`sacct` 状态; ② **作业目录内 chk/plt 的 mtime 是否在增长**;
   ③ ★ **objdir 内 FLASH 日志的步进轨迹**。本仓库 `run.sh` 把 stdout
   `> wsl_run_snbonech.log` 重定向进 objdir, 所以 SLURM 的 `--output` 文件
   **永远是 0 字节**。2026-09-12 曾据此误判"空转", 实际作业已正常跑完
   (9073 步 / 58.1 min / RUN_EXIT=0 / 23 chk + 5 plt)。
   同理 `hydra_bstrap_proxy FAILED` 常是**作业被 kill 后的伴随现象**, 非根因。
9. ★★★ **`+ug` 网格必须按 nproc 反推 nxb, 否则 0.1 µm 薄层物种从不被写入**:
   `Simulation_initBlock.F90` 按单元中心判据选物种, 若 `dx > 薄层厚度` 则
   **没有任何单元中心落进薄层** → 该物种质量分数恒为 `sim_smallX=1e-99` →
   相邻层直接接触 (ρ 差 6 量级) → 一步即爆。
   铁律: `nxb = 2**ceil(log2(max(8, dom/(3e-6 * nproc))))` (3e-6 cm = 0.03 µm),
   且 `dx > 0.03 µm` 时**硬中止**。验收判据 = **chk_0000 里 8 个物种全部 nonzero**,
   每个薄层 6-7 格 (门槛 3 格)。见 `SNBOneCH_ml.py:build_setup_flags_ug()`。
10. ★ **`pres` 跨 6-9 个量级不一定是故障**: `P = rho*kT/(mu*m_p)`, 冷区 ρ=1e-6
   与密区 ρ=1.0 的 6 量级 ρ 差会**原样传递**到 pres。判据 = **dens 跳变处数**
   (`|d log10 rho| > 0.5`), 本场景**只有 2 处** (cham|shld 与 samp|cham),
   层间无跳变 (层间 ρ 全 = 1.0, 靠 spec_* 质量分数区分)。
11. ★ **WSL `bash -lc` 会吞 shell 变量与反引号**: 内联 `$OBJ` 展开为**空**
   (导致 `ls /` 而非目标目录), 反引号内容被命令替换吞掉。
   ★ 唯一可靠: **Windows 侧 Write `.sh` → `cp -f` 进 WSL → `sed -i 's/\r$//'` → `bash`**。
   远端同理: **base64 编码后 `printf | base64 -d > f.sh && bash f.sh`** (规避引号/换行)。
   ★ 另: h5py **无法从 `\\wsl$\` UNC 路径读** (Win32 文件锁 errno 1)
   → 必须先 `cp` 到 `/mnt/e/...` 再读。

---

12. ★★★ **禁止整目录删除 `flash_output/`** —— 它是 **WSL 与 HPC 共用父目录**
    (`hpc_<account>/` 子目录存超算结果)。收集 WSL 结果时只删本次产物模式:
    `rm -f {out}/{BASENM}* {out}/wsl_run_snbonech.log`, **保留子目录**。
    2026-09-12 曾用 `rm -rf` 误清 `hpc_flash_ssh/`。
13. ★★★ **chk/plt 收集后必须校验"是否陈旧"**: 文件名**不含 tag 前缀**,
    而 `flash_output/` 会跨运行累积 → 旧 chk 残留且**数量占优抢占下标**,
    使"按文件名读第 N 帧"**静默拿到旧运行数据** (曾据此得出"网格塌缩 +
    全域均匀化"的完全错误结论)。
    ★ 权威判据 = **`sim info` 的 `setup call` (含 `-nxb`) + 文件 mtime**,
    **绝不能用文件名字典序**。快速粗筛: 尺寸档位 (32768 格 ≈ 19.3 MB;
    512 格 ≈ 0.73 MB; ~589 B/格)。

---


---


---

## §C `+ug` 场景族三大铁律（2026-09-13 实测定案）

### C1 叶块步长 = `W/(iProcs*nxb)`，与 `lrefine_max` 无关

实测（SNBVTi, `xmin=-0.039990234375, xmax=0.010009765625, nblockx=8, nxb=128, iProcs=131`）：

| 来源 | dx [cm] | dx [µm] |
|---|---|---|
| par 注释公式 `W/(nblockx*nxb*2^(lrefine_max-1))` | 1.525879e-06 | 0.015259 |
| **实测** `W/(iProcs*nxb)` | **2.981870e-06** | **0.029819** |

比值 **15.63×**。日志证据：

```
RuntimeParameters_read:  ignoring unknown parameter "lrefine_max"...
RuntimeParameters_read:  ignoring unknown parameter "lrefine_min"...
RuntimeParameters_read:  ignoring unknown parameter "lrefine_min_init"...
RuntimeParameters_read:  ignoring unknown parameter "refine_var_1"...
RuntimeParameters_read:  ignoring unknown parameter "refine_var_2"...
RuntimeParameters_read:  ignoring unknown parameter "refine_var_3"...
RuntimeParameters_read:  ignoring unknown parameter "refine_cutoff_1"...
RuntimeParameters_read:  ignoring unknown parameter "derefine_cutoff_1"...
RuntimeParameters_read:  ignoring unknown parameter "refine_cutoff_2"...
RuntimeParameters_read:  ignoring unknown parameter "derefine_cutoff_2"...
```

⇒ `+ug` 下**全部 AMR 键被忽略**。另：`nblockx` 也被无视，叶块数 = `iProcs`（131），
每块 128 cell，共 16768 cell。`lrefine` 恒为 1（全部叶子块）。

★ **反面教训**：par 里 `lrefine_max` 行的注释
`# res = dir_delta/(nxb*nblock*2^(lrefine_max-1)) = 1.525879e-06 cm` 是**误导性注释**，
在 `+ug` 下不可用于估算 dx。

### C2 `chk c[0,0] == par_xmin + 64*dx`（64 = nxb/2）

| 场景 | par `xmin` | `chk c[0,0]` | `c[0,0] - xmin` [cells] |
|---|---|---|---|
| SNBVTi | -0.039990234375 | -0.03979939468034351 | **64.000000** |
| SNBOneCH_ml | -0.040000000000 | -0.03980916030534351 | **64.000000** |

两场景**精确** 64 cell（误差为 0）。域宽不变（0.05 cm），**整体平移 +1.9084 µm**。
⇒ **`+ug` 场景族固有行为**，非个别场景 bug。

物理后果：`Simulation_initBlock.F90` 用绝对 `xcent` 与 `sim_*Radius` 比较，
但 `xcent` 的 cell 0 对应 `par_xmin + 64*dx` ⇒ **所有层界右移 64 cell**。

实测层位（SNBVTi, 4 物种）：
```
设计   shld [0, 0.1]    samp [0.1, 2.0]  tar2 [2.0, 2.1]  samp [2.1, 52.1]   um
实测   shld [1.6065, 2.0239]  samp [2.0239, 3.8727]  tar2 [3.8727, 4.0516]  samp [4.0516, 54.1172]
```

★ 用户 2026-09-13 明示"不用在意那一点点位置偏差" → **当前搁置**。
若未来需绝对坐标对齐：在 `Simulation_initBlock.F90` 新增 par 参数 `sim_xmin`，
判据改 `xcent(i) - sim_xmin`，使 `sim_*Radius` 表示"距域左边界"。

### C3 `NSPECIES` 是编译期常量 → `--skip-build` 会静默复用旧二进制

事故：8→4 物种重构（`py_compile` 通过、26 处替换验证）后，chk 仍含
`tar1/tar3/tar4/tar6`。

根因：`NSPECIES` 由 setup 的 `species=` 标志**编译期**确定；
`--skip-build` 只做 `ls flash4` 检查 + `tar xzf unit.tar.gz` 刷新 par/F90，**不重编二进制**。

**护栏（已落地）**：`_longrun_lib.py` 增构建指纹机制：

| 函数 | 作用 |
|---|---|
| `fingerprint_files()` | 返回 Config + `Simulation_initBlock.F90` + Makefile + 各 `*.F90` |
| `compute_build_fingerprint()` | 上述文件 name+bytes 的 sha256（含 NUL 分隔） |
| `remote_fingerprint(remote, objdir)` | 读远端 `_BUILD_STAMP.json` |
| `needs_rebuild(remote, objdir)` | 无 `flash4` / 无戳 / 戳不符 → True |
| `write_remote_fingerprint(...)` | 仿真成功后 base64 写戳 |

`03_run_16ns_pipeline.py` 增 `--force-build`（无视指纹强制全量构建）。
★ 指纹**故意不含 par** —— par 是运行时参数，`--skip-build` 会重新解压刷新。

首次运行输出：
```
★ 需全量构建: 无构建戳 (旧二进制, 无法证明与当前输入一致)
SETUP_OK → MAKE_OK → flash4 10,502,392 B → BUILD_OK (1335 个 .o)
构建戳写入: ✓ (744511c55595…)
```
重建后 chk 物种标记恰为 `['cham','samp','shld','tar2']`。

★ **判据不能只看 `flash4` 是否存在** —— 这正是缺陷得以潜伏的原因。

---

## §D `par_gen.set()` 必须显式覆写域值（2026-09-13 事故）

`SNBVTi.py::generate_input_files()` 里 **`par_gen.set("xmin"/"xmax", ...)` 从未被调用**，
导致 `align_domain()` 的吸附结果根本没进 par；par 值一直来自
`tracer/_par_layers.py` 第 335–338 行 `CH_FLASH_PAR` 模板硬编码：

```python
'xmin': -0.04, 'xmax': 0.01, 'nblockx': 8, 'lrefine_max': 9,
```

**修复**（附条件判断 + 日志）：
```python
if abs(cfg["xmin"] - float(CH_FLASH_PAR["xmin"])) > 1e-15 or \
   abs(cfg["xmax"] - float(CH_FLASH_PAR["xmax"])) > 1e-15:
    par_gen.set("xmin", cfg["xmin"])
    par_gen.set("xmax", cfg["xmax"])
    log(f"    域覆写: xmin={cfg['xmin']:.10f}, xmax={cfg['xmax']:.10f} ✓")
```
验证：`par:402| xmin = -0.039990234375` ✓（远端 deploy + objdir 双确认）。

另新增 `align_domain(xmin, xmax, nblockx, nxb)`：把域边界吸附到 root 网格整数倍
（`rootdx = (xmax-xmin)/(nblockx*nxb)`；`xmin' = round(xmin/rootdx)*rootdx`；
`xmax' = xmin' + nblockx*nxb*rootdx`），`config_constants` 增 `"align_domain": True`。
实测：`xmin -0.04 → -0.03999023 cm`（位移 +0.0977 µm），`xmax → 0.01000977`。

★ 教训：**改了 cfg 不等于改了 par** —— 凡 cfg→par 的传递点必须显式验证产物文本。

---

## §E chk 结构速查（h5py 直读，2026-09-13）

| 路径 | 结构 | 读法 |
|---|---|---|
| `coordinates` | shape `(nblocks, 3)`，**块首坐标**（非逐 cell） | `dx = (c[1,0]-c[0,0])/nxb` |
| `block size` | shape `(nblocks, 3)` | 每块物理尺寸 |
| `real scalars` | compound `[('name','S80'),('value','<f8')]` | `{r['name'].decode().strip(): r['value'] for r in d}` |
| `integer scalars` | compound `[('name','S80'),('value','<i4')]` | 同上（含 `nxb`/`iprocs`/`globalnumblocks`/`nstep`）|
| `unknown names` | S80 数组 | `n.tobytes().decode('utf-8','replace').strip()` |

★ `integer scalars` 仅有 15 键：`checkpointfilenumber, dimensionality, forcedplotfilenumber,
globalnumblocks, iprocs, jprocs, kprocs, nbegin, nstep, nxb, nyb, nzb, plotfilenumber,
splitnumblocks, splitnumparticles` —— **无 `nblockx`/`lrefine_max`/`iguard`**
（那些须从 `real scalars` 或 par 取）。

★ 错误示范：`for row in d: k = row[0]` → `TypeError: Cannot compare structured or void
to non-void arrays`。

★ 物种标记定位：`f[s][:,:,0,:].reshape(-1)` → `np.nonzero(a>0.5)` → 连通区间。
**注意 shape `(131,1,1,128)`，必须 reshape(-1) 再找 run**；只取 `f[s][:,:,:,0]` 会
误报"全为 1"（那只是每块首 cell）。

---

---

## §F 密度跃变 ≠ 数值发散：四项并联判据（2026-09-12）

2026-09-12 曾把 `chk_0003->0004` 的 `rho_max +86.1%` 误判为异常，实为**中心撞击压缩**。

**四项判据（缺一不可）**：
1. `argmax(dens)` 是否始终在对称轴 x=0（压缩必在中心；边界/局域尖峰才可疑）
2. `dt` 在跃变时刻是否下降（发散必砍 dt；SNBOneCH_ml 主链是 hydro，`dtmax=2e-14`，
   **密度不进 CFL** → 密度跃变本身不会缩 dt）
3. 内能密度增长是否平滑（压缩 = 绝热做功，平滑增长；激波加热会在跃变帧出现尖峰）
4. 体面质量是否守恒（`\int rho dx` 逐步对比 —— 本次 `m_all` 逐位相同）

★ `dtmax` 可比 `dt` 实测值大 1–2 个量级（SNBOneCH_ml 实测 1.36e-13），因为 `dtmax`
只在 `Simulation_init` 读一次、`dt` 由进化器动态给出。
★ 起始 `dt` 较大（1.36e-13 @ 8.4e-11 s）是**激光沉积初期启动暂态**，不是不稳定。

---

## §G HPC 结果收集与下载

**结果不在 objdir，在部署脚本的 `_out/` 收集目录。**
`run.sh` 开头 `rm -f snbonechug_*` 清空 objdir，结尾把 chk/plt/profile/log 移入
`<HOME>/QC/<scene>_deploy/_out/`。直接去 objdir 拉会得到"输出消失了"的假象。
真实样本：NC-E 4864358 → `_out/` 共 31 文件（23 chk + 6 plt + LaserEnergyProfile.dat + log）。
★ chk 序号可能真缺号（0000–0023 缺 0005 = 23 个），**不是下载漏了**。

**超算批量下载必须用 venv 解释器 + 每文件独立连接。**
基础托管解释器缺 `cryptography` → 凭据解密抛错、脚本**静默退出且日志 0 字节**。
排查第一步 = **`--dry-run`**。
★ DETACHED/nohup 起的长任务在沙箱里立即被回收 → 用**宿主后台任务机制**。
★ paramiko 不展开 `~` → 先 `printf '%s' "$HOME"`。
详见技能 `hpc-sftp-parallel-fetch`。

---

## §H SNBVTi 极短测试基线（2026-09-13，tmax=1e-11，4 物种）

工况：NC-E `flash_ssh`，131 tasks，`RUN_EXIT=0`，`WALL_SECONDS=36.83`，nstep=87。

| 量 | 值 |
|---|---|
| t_end | 1.0148e-11 s（`exiting: reached max SimTime`）|
| dt 实测 | 1.0e-15 → 1.5533e-13 s（峰值 4.6206e-13 @ step 65），**从未触及 dtmax=2e-12** |
| 质量守恒 | 窗内 Σρ 两帧**完全一致** 2.398886e-03 g/cm²（相对差 0）|
| 内能 | ΣρTₑ 1.1149e-12 → 1.3384e-12 erg/cm²（+20.0%，单调）|
| tele max | 1.1736e+05 eV @ x=+1.8301 µm |
| tion max | 88186 eV @ x=+1.8003 µm（比 tele 峰滞后 0.03 µm）|
| dens max | 4.9206 g/cm³ @ x=+1.9494 µm |
| trad | 131.89 – 280.94 eV |
| 未扰区 | x>5 µm 仍为初值 `dens=1.0, tele=290.11 eV` |

**物种标记实测**：`['cham','samp','shld','tar2']`（4 种，无 `tar1/3/4/6`）✅

⚠ **两项未决**：
1. **Hypre 非收敛**：5 次 `ierr=256` Nonconv（`component=2`，iter 1–9，res 1.03–3.03），
   短测未致崩溃；按 §11 结论其在长跑中是**主导成本**，须监控频次。
2. **`LaserEnergyProfile.dat` 列语义**：`col3(7.14e6) > col4(3.41e6)` 疑违能量守恒
   → 列义待核实（须查写出源码），**不作定量结论**。

**产出**：`scripts/analysis/plot_shorttest.py`（4 图，全英文，字号 ≥19pt，DPI=500）
+ `SHORTTEST_RESULT.md`。

---

---

## §I 凭据与 Git 认证（2026-09-12 定案）

**只有一套机制**：`scripts/03_git_publish/_git_auth.py`（`auth_prefix()`）+
`_git_credential_helper.py`（git credential helper 协议，只服务 gitee.com）；
4 个入口共用：`git_push.py` / `git_pull.py` / `git_size_report.py` / `private/git_push_private.py`。

| 做法 | token 落 `.git/config` | token 进 `argv` |
|---|:---:|:---:|
| 认证 URL 写进 remote | ❌ 明文落盘 | — |
| 认证 URL / base64 头当参数 | ✅ | ❌ `ps` 可见 |
| **credential helper（现用）** | ✅ | ✅ |

- ★ `auth_prefix()` **先写空的 `credential.helper=` 清空列表**（否则系统 GCM 抢答/弹窗），
  再挂自己的。
- ★ **Gitee API 鉴权用请求头** `Authorization: token <t>`，**不用** `?access_token=`
  （后者把 token 留在 URL → 日志/异常/代理记录）；实测 v5 两种均 200。
- ★ **`cryptography` 是惰性导入** → 各入口须显式 `import cryptography` 探测，再给友好提示。
- ★ **Windows 禁 `shell=True` 拼 git 命令**（cmd.exe 不认 shlex 单引号）→ `shell=False` + 参数列表。
- ★★ **提交消息一律「写文件 + `git commit -F <file>`」**。两次踩坑：
  ① 经 bash 内联时**反引号被命令替换吞掉**（消息残缺）；
  ② `-m-file` 被 argparse 当 `-m` 的值 → 消息变 `-file`。
- ★ 强推用 `--force-with-lease=refs/heads/master:<已知远端SHA>` —— 本机 tracking ref
  **不落盘**，裸 `--force-with-lease` 会报 `stale info`。

---

## §J E: 盘文件「间歇性不可见」→ `git add -A` 会静默提交大规模删除

**事故**：2026-09-12 一次推送把 `tracer/SNB/SNBOneCH_ml/`（10 文件 / 2835 行）提交为删除 ——
磁盘上目录仍在、内容为空，而我**没执行过删除**。同源现象早已见于 `.git/refs/remotes/**`
数秒内被清除、`update-ref` rc=0 却不落盘。

**护栏（已落地）**：`git_push.py` 在 commit 前查 `git diff --cached --diff-filter=D`，
有条目且未给 `--allow-deletes` → `git reset` 撤回暂存 + 列文件 +
给 `git checkout HEAD -- <paths>` 恢复命令 + **rc=2 中止**。

**恢复路径**：`git checkout <上一提交> -- <path>` → `commit --amend` → **断言**"相对该提交
只剩预期差异、零删除" → 显式 lease 强推。**先断言再推**。

★ 排查"文件是否真的缺了"必须用 **`git ls-files -z`**：默认 `core.quotepath` 会把**含中文的路径
转义成八进制**，直接喂 `os.path.isfile` 会**误报缺失**（本次曾误报 21 个）。

---


## §K HYPRE：**不是错误，但是最大性能瓶颈**（2026-09-14 定案，推翻 09-13 版）

### K1 结论（两条，互不矛盾）
1. **告警本身是常态噪声** —— 不阻断推进、不影响守恒，**不需处理**。
2. **但它吞掉 77% 墙钟时间** —— 是**首要优化对象**。

### K2 告警统计（日志行级：仅反映“打印出来的部分调用”，≠ 调用总数。勿用 grep）

| 指标 | SNBVTi 极短 (tmax=1e-11) | SNBOneCH_ml 1.6 ns |
|---|---|---|
| step 数 | 87 | 306,779 |
| 日志中 `[gr_hypreSolve]` 行数 | 5 | 11,805 |
| 其中 Nonconv | 5 (100%) | 11,805 (100%) |
| `iter=500` 烧满 | 0 | 11,430 (96.82%) |
| res_norm | 3.03e-05 ~ 1.91e-03 | 1.09e-08 ~ 1.0006e+04（中位 9.34e-04）|
| 退出 | `exiting: reached max SimTime` | 同左（t=1.6e-09 正常到达）|

### K3 三条硬结论
1. **`final_res_norm` 远小于 1**（中位 9.34e-04），是“接近收敛但未达
   `gr_hypreRelTol=1e-8`”，**不是“残差爆炸”**。
2. **`component=2` 是系统编号，不是辐射群。** 源码 `gr_uhypreSolve.F90`：
   `if (component==3) then strings='group no' else strings='component'`。
3. ★★ **日志行数 ≠ 调用次数。** 日志只打印**部分**调用
   （受 `gr_hyprePrintSolveInfo` 门控）。**判性能必读 perf_summary 的 num calls 列。**

### K4 ★★★ 性能实测（perf_summary，SNBVTi 1.6 ns，权威）

| 项 | 秒 (avg/proc) | 占比 |
|---|---|---|
| 总 monitoring period | 51,215 | 100% |
| `Diffuse` → `diff_advanceTherm` | 41,036 | **80.3%** |
| 　`Grid_advanceDiffusion` | 40,203 | 78.5% |
| 　　**`gr_hypreSolve`** | **39,321** | **76.8%** |
| 　　　`HYPRE_ParCSRPCGSetup` | **30,604** | **59.8%** ← 预条件重建 |
| 　　　`HYPRE_ParCSRPCGSolve` | 8,378 | 16.4% |
| `Hydro` | 1,251 | 2.4% |
| `sourceTerms` (含激光) | 3,968 | 7.8% |
| `IO_output` | 3,704 | 7.2% |

**`gr_hypreSolve` 调用 = 5,692,647 = 每步 19.0 次**（MGD 10 群 + 电子/离子等）。
⇒ **PCG 预条件器每次 solve 都重建**（~5.4 ms/次），这是主成本。

★ ★ **2026-09-13 我据“日志 Nonconv 行数”得出的“每步仅 0.038 次 solve、
非性能主宰”结论是错的** —— 它把日志行数当了调用数。
（同时，历史上的“每步 3.4 次”也偏低；真值 19.0。）

### K5 参数全清单（源码 `gr_hypreInit.F90`，默认值）
`gr_hypreSolverType="HYPRE_PCG"` / `gr_hyprePcType="HYPRE_AMG"` / `gr_hypreRelTol=1.0e-8` /
`gr_hypreAbsTol=0.0` / `gr_hypreCfTol=0.0` / **`gr_hypreMaxIter=500`**（正是烧满值）/ `gr_hypreMinIter` /
`gr_hypreFloor=1.0e-12` / **`gr_hypreUseFloor=.TRUE.`**（SNB 必须 `.false.`）/ `gr_hypreRelChange` /
`gr_hypreRecomputeResidual` / `gr_hypreRecomputeResidualP=-1` / `gr_hypreUse2Norm` /
`gr_hypreSlopeLimType` / `gr_hyprePrintSolveInfo` / `gr_hypreInfoLevel` / `gr_hypreSolverAutoAbsTolFact`。
另有 MagZ/Mag/Viscosity 三套子参数（`Config` 中默认 `HYPRE_GMRES` + `RelTol=1.e-10`）。

### K6 作者原版态度（★ 决定性）
`SNB_1D_laser_obj/flash.par:460-464`：

```
#gr_hypreSolverType = "HYPRE_PCG"    ← 注释掉
#gr_hyprePcType     = "HYPRE_ILU"    ← 注释掉
#gr_hypreMaxIter    = 5000           ← 注释掉
#gr_hypreRelTol     = 1.0e-8         ← 注释掉
 gr_hypreUseFloor   = .false.        ← 唯一启用
```

⇒ **作者本人不调任何 HYPRE 收敛参数**。

### K7 处置决策（未变）
**不改任何 `gr_hypre*` 参数。** 仅需静音日志可用 `gr_hyprePrintSolveInfo=.FALSE.`。
优化方向（**尚未实施，属代码级改动，需先获批**）：
① 复用预条件器（避免每次 `HYPRE_ParCSRPCGSetup`）；
② 换 `gr_hyprePcType`（如 `HYPRE_ILU`）；③ 减少 MGD 群求解次数。

### K8 复现
统计器 `flash/temp_delete/hypre_stat.py`（逐行流式）：

```bash
PY=$FLASH_MANAGED_PYTHON  # 管理型解释器，运行期经 flash/_core/paths.py 解析
$PY flash/temp_delete/hypre_stat.py <logfile>
```

★ `[gr_hypreSolve]` 每次调用**跨 5~6 行**写出，**必须按键名正则逐行抓**。
★ 性能数字只能从运行末尾的 **perf_summary** 取（`grep` 不可用时用
`tail -120 <objdir>/snbvti.log`）。

---

## §L 重复提交事故：同名作业并发写同一 objdir（2026-09-14）

### L1 事故
`--stage submit`（内部阻塞轮询）的**父进程**因网络中断死亡，但**远端 SLURM
作业并不随之结束**。重跑 submit 又提交了第二个作业。

| JobID | 启动 | 时长 | 结束 |
|---|---|---|---|
| **4865100** | 09-13 18:46:23 | 14:14:16 | 09-14 09:00:14 |
| **4865102** | 09-13 18:57:01 | 14:15:41 | 09-14 09:12:42 |

两者同名 `SNB1CH_r_nce`，共用同一 objdir / `snbvti.log` / `snbvtiug_*` chk 编号 ⇒ **交错覆盖**。

### L2 证据
- `snbvti.log` = 55.9 MB，含 **599,131** 行 `step: n=`（≈ 2 × 299,613）
- **5 个 `LOGFILE_END`**：17:44:16 / 17:58:53 / 18:11:56（三个极短测试）+ **09:00:14 / 09:12:42**
- `chk_0751` mtime = 09:00:12（属 A），`chk_0750` mtime = 09:12:39（属 B）
- 时间线中部可见**两条 step 序列相邻交错**（如 01:37:31 n=120,285 与 n=115,894）
- `squeue -u $USER` 当时应有两行，但 **`_track.py` 只取首行** ⇒ 完全掩盖

### L3 ★ 数据未受损（逐位校验已证）
两者输入完全相同（`tmax=1.6e-9` / `xmin=-0.04` / `xmax=0.01` / `iProcs=131` /
`nblockx=8`）、均 **299,613 步**，且是同一二进制确定性复现：

```
逐 n 比对（取前两次出现）: 299,259 个 n
t 与 dt 完全一致（逐字符）: 299,259  (100.0000%)
1..299613 缺失的 n: 0
```

⇒ **两 run 逐位相同 ⇒ 交错覆盖的 chk 可互换，数据自洽。**
（浪费 = 131 核 × 14.2 h 机时，但**无数据损失**。）

### L4 护栏（已落地）
1. **`03_run_16ns_pipeline.py`**：`stage_submit` 提交前查 `squeue -u $USER -h -o '%i|%j|%T|%M|%N'`，
   若存在同名 `SNB1CH_r_{tag}` 作业 → 打印全部命中行 + **`return 2` 中止**；
   逃逸门 `--allow-duplicate`。判定不受其他名字作业影响。
2. **`_track.py`**：收**全部** squeue 行，输出 `TRACK_NJOBS`；当 `njobs>1` 额外打印
   `TRACK_WARN` + 逐作业 `TRACK_JOB=`。优先选与本场景同名的 run 作业。

### L5 教训
**阻塞式父进程的生命周期 ≠ 远端作业的生命周期。**
任何重提前必先确认远端无残留作业；
且**不得假设“父进程死了作业就死了”**。

---
## §M 超算连接信息唯一来源 = `hpc_accounts.json`（2026-09-14 重构定案）

### M1 规则
**包内禁止硬编码 host / port / SSH 用户名 / 线路。**
唯一来源 = `~/.physimx/flash/hpc_accounts.json`（明文，用户可编辑，**不在包内**）。
密码仍 Fernet 加密存于同目录 `credentials.enc`。

### M2 删除的硬编码（清单）
| 位置 | 内容 |
|---|---|
| `_core/credentials/_config.py` | `LEGACY_PACKAGE_ROUTES`（9 条中卫/香港线路 host:port）整块删除 |
| `_core/credentials_legacy.py` `MANUAL_FIELDS` | `host="ssh.cn-zhongwei-1.paracloud.com"` / `username="hello@NC-E"` → 置空 |
| `scenarios/runner.py` `Remote.__init__` | 3 条硬编码线路 → `load_hpc_routes(credential)`（新函数） |
| `SNBOneCH_ml` / `SNBVTi` `03_run_16ns_pipeline.py` `_probe_route()` | 硬编码 3 条 → `get_hpc_routes(account)` |
| `ch_center/laserslab1d_local_custom.py` | 提示串 `scp ... <ACCOUNT>@ssh.cn-zhongwei-1...` → 从 JSON 拼 |
| `flash/config/__init__.py`、`hello_flash/deploy_flash.py` | docstring/描述里的 `paracloud` 举例 → 通用化 |

### M3 语义收紧
* `_config.get_ssh_username()`：**未配置返回 `""`**。原实现回退为 `name` 本身，而
  `flash_ssh.py` 曾用 `get_ssh_username(name) == name` 作"未配置"哨兵 —— **哨兵已删**，
  `_get_field()` 随之成为死代码被删除。
* `_config.get_ssh_routes()`：删掉"从 `ENTRIES.manual_fields` 拼单条线路"的回退
  ⇒ **JSON 是唯一来源**。
* 调用点全部核查：`_core.load_ssh_credentials`（`raw["host"]/["username"]` 短路分支保留
  但**注释为旧数据兼容**）、`route_tester.account_label`（`or cred_name` 兜底）等均 tolerant。

### M4 `hpc_config.py` = 格式权威
* 模块 docstring 内含完整格式规范（字段表 + JSON 示例 + 读写 API + 生命周期 + CLI）。
* `_HEADER_COMMENT` 即"格式速查"，新生成的 JSON 自解释。
* 新增 `HPC_ACCOUNTS_TEMPLATE` / `write_example_file()` / `list_hpc_accounts()` / `all_routes()`；
  CLI 新增 `example` 子命令。
* `extract_accounts_from_storage()` **不再注入 LEGACY 线路**：只提取加密库 `ssh_username` +
  旧条目 title/route_key；**已有 routes 原样保留**，缺失时告警"请手工补全 routes"。
* ★ `get_hpc_routes()` 增加**归一化**：`port` 必为 1..65535 的 int（缺省 22）、`host` 必非空、
  `label` 缺省补 `host:port`；非法条目**静默丢弃**。
  **（修掉一个真实崩溃：`port="bad"` 曾使 `all_routes()` 抛 `ValueError`）**

### M5 消除第二真相源
`manage.py` manual 模式原把 host/port/username 写进 **`credentials.enc`** → 改为新增
`_collect_manual_basics()` / `_persist_manual_basics()` 写 **JSON**（加密库只留密码）。

### M6 新增交付物
* `flash/_core/credentials/README.md` — 格式规范 + 读取 API + CLI + 模块职责表
* `flash/_core/credentials/hpc_accounts.example.json` — 静态模板（已加入 `pyproject.toml`
  的 sdist `include`，否则 `**/*.py|md` 白名单会漏掉它）
* `flash/_core/credentials/examples/hpc_accounts_demo.py` — 示例脚本：
  打印 / 结构校验 / `--probe` TCP 测速 / `--json` / `--init` / `--example`

### M7 验证
* `py_compile` 12 文件全过；**ruff `--select=E9,F` 逐文件对比 HEAD 基线，issues 数完全一致**
* pytest `test_gitee / test_flash_remote_deploy / test_interface / test_flash_simulator /
  test_flash_env_manager` = **60 passed**
* 真实配置读取：2 账户 / 各 9 线路；`ROUTES_NC_E=9`、`ROUTES_BSCC_T6=9`、
  `runner.load_hpc_routes=9`
* 隔离 HOME 边界：文件缺失→空、JSON 损坏→空、非法 port/host→过滤不崩、`extract` 保留既有 routes

### M8 遗留（未动，待用户决策）
`hello_flash/deploy_flash.py` 的 `MACHINES[].label` 仍含账号名（`<ACCOUNT>@NC-E` 等）——
纯 UI 文本，**连接仍走凭据**；该 dict 还含 `slurm_partition`/`module_load` 等场景级配置，
按"用户未提及参数不得改"原则未动。`private/SNB/SNBtest/.../run_snb_hpc.py` docstring、
`test/remote_connect/diagnostics.py` 标签同理。

---


## §N chk 温度单位 = **K**；绘图/能量核算两处 bug（2026-09-14）

### N1 结论
chk 中 `tele` / `tion` / `trad` / `temp` 的单位是 **开尔文 (K)**，**不是 eV**。
显示为 eV 需 `/11604.51812`。

⇒ `SNBVTi` 末帧 `Te_max = 1.8490897e7 K = 1593.4 eV`（1.6 keV）—— **完全物理**。
此前读作 “18.5 MeV” 是单位误判。

### N2 三条独立证据
1. **par 自带注释**：
   `sim_teleCham = 290.11375   # cham initial electron temperature [K]`
   （四个物种全同；参考场景 `SNBOneCH_ml` 亦同）。
2. **压力**：`p = (n_i + n_e) k T`。取 T=290.1137 **K** ⇒ `p_est = 5.991e3` vs chk `pres`
   `6.072e3`（**偏差 1.4%**）；取 eV 则差 **1e4 倍** ⇒ 矛盾。
3. **内能**：`eint = (3/2)·p/ρ`（单原子理想气体，与成分无关）。
   290 K → `9.109e9` vs chk `eint` `9.1038e9`（**偏差 0.06%**）。

★ 另：`Simulation_initBlock.F90:141,145` 把**同一个 `tele`** 同时写入
`TEMP_VAR` 与 `TELE_VAR` ⇒ 实测 `temp == tele` 逐位相等，进一步锁定同单位。

### N3 bug①：`_longrun_lib.K_BOLTZ_EV_PER_K` 大了 1000 倍
```python
K_BOLTZ_EV_PER_K = 1.16045e7   # 旧：名为 K/eV，实为 K/keV（正确值 11604.51812）
```
⇒ `tele / K_EV` 实际得 **keV** 却标“(eV)”。
修正：`1.160451812e4`（`SNBVTi` 与 `SNBOneCH_ml` 两份 `_longrun_lib.py` 均改）。

### N4 bug②：`04_analyze_plots.py` 单位转换不一致 + 能量积分漏 ρ
- 仅 `plot_profile` 第 206 行做了 `/K_EV`；`tele_xt` / `boundary_diag` /
  `scalars_history` / `health.json` **四处未转换**却标 eV。
  且第 426 行注释错写 “FLASH 的 `tele` 已是 eV，不得再除 K_B”。
- `plot_boundary_diag` 能量积分 `Σ ei·dx` **漏乘 ρ**（`eint` 是**比**内能 [erg/g]）
  ⇒ 虚报 `6.0e13 erg/cm²`（真值 `9.08e11`）、左半域占比误报 72.6%（真值 **46.6%**）。

**修正后**（`--stage plot` rc=0，6 s）：
```
末帧: ρmax=2.337 g/cc   Te_max=1593 eV
boundary_diag: Te_edge 1.59e+03 eV, ∫ρe_int dx 6.01e+07→9.08e+11 erg/cm2, 左半域占比 46.6%
health.json: tele_max_K=1.8490897e7  tele_max_eV=1593.4222  （双键）
```

### N5 物理合理性（修正后）
- 激光累计吸收 `Energy in = 3.060e12 erg/cm²`；
  `LaserEnergyProfile.dat` 列义（表头）：
  `#Step  Time(s)  dt(s)  Energy in(erg)  Energy out(erg)  dE in(erg)  dE out(erg)`。
- 材料内能 `∫ρe_int dx: 6.01e7 → 9.08e11 erg/cm²` = 激光输入的 **29.7%** ⇒ **无能量超支**。
  质量经边界流出 22.6%（左边界 `vacuum`，与抽空一致）。
- **与参考场景一致**：`Te_max 1.849e7 vs 1.820e7 K`；沿 x 剖面逐点吻合
  （-398 µm: 1.85e7 vs 1.82e7；+30 µm: 8.27e6 vs 8.17e6）⇒ **场景族基线特性**。
- 物种真实身份（par `ms_*A/Z`）：`cham`=**He**(4.00/2)，`shld`=**V**(50.94/23)，
  `samp`=**CH**(6.51/3.5)，`tar2`=**Ti**(47.87/22)。

### N6 遺留
- 激光脉冲 **t=1.063 ns 达峰、延至 2.209 ns**，而 `tmax = 1.6 ns` ⇒ 仅覆盖前 72%。
- `boundary_heating_artifact_suspected` 仍为 `true`（阈值 1e6 K ≈ 86 eV 偏松），
  该电平待复核。

---
## §O 发布流程：定向提交 + 凭据推送 + 打标签（2026-09-16，tag 0.1.8）

### O1 ★ `git_push.py` 的 `git add -A` 是发布陷阱
`scripts/03_git_publish/git_push.py` 在 `has_changes()` 为真时会先 `git add -A` **再**提交。
工作区存在在制变更时，它会把**无关改动一起提交**，且因 `_hpc_build_bscc_test.sh` 处于
`D`（未暂存删除）状态而触发删除护栏 → `rc=2` 中止（护栏本身是对的，但它使脚本无法用于
"只推已完成的提交"）。
⇒ **发布标准流程**（本次实践）：
1. `git add -- <显式路径>`（**禁止 `git add -A`**）
2. `git diff --cached --name-status` + `git diff --cached --diff-filter=D` 双确认
3. `git commit -F <utf8-message-file>`（中文消息走文件，避免 argv 编码问题）
4. 推送用 `.workbuddy/tmp/push_only.py`（复用 `_git_auth.auth_prefix()`，只 push 不提交）
5. `git tag -a <ver> -F <msgfile>` → 同一脚本推标签（`push_only.py <tag>`）

### O2 裸 `env/` 会吞掉源码包 —— 仓库级 .gitignore 同步的必查项
把子树 `.gitignore` 提升到仓库根时，**必须逐条检查是否会命中已跟踪路径**：
- 本例 `flash/flash_run/env/` 是**已跟踪源码包**（`env_manager.py` 等），
  上游裸 `env/` 会让该包**新增文件被静默忽略** ⇒ 锚定为 `/env/`、`/ENV/`。
- 其余同步项无需锚定（`venv/`、`env.bak/`、`venv.bak/`）。

### O3 ★ 同步验证法（可复用）
不要只看"规则写进去了"，要**实测忽略集合等价**：
```bash
git ls-files --others --ignored --exclude-standard -z -- <subtree> | tr '\0' '\n' | sort > A
mv <subtree>/.gitignore /tmp/bak        # 临时移走嵌套 .gitignore
git ls-files --others --ignored --exclude-standard -z -- <subtree> | tr '\0' '\n' | sort > B
mv /tmp/bak <subtree>/.gitignore        # 立刻复原
diff A B      # 空 ⇒ 根规则可完全替代嵌套规则
git hash-object <subtree>/.gitignore    # 复原后 sha 必须与移走前一致
```
本次结果：**4556 项，diff 为空**（`gen_eos_op` 子树）。

### O4 Gitee 远端跟踪引用会被 E: 盘过滤驱动"卡住"（§J 同源）
`git fetch` 报 `8a6aba2..2a35357 master -> origin/master` 成功，但 `git rev-parse
origin/master` 仍返回旧值，且 `.git/refs/remotes/origin/` **目录不存在**（`show-ref` 回落到
`.git/packed-refs` 的旧条目）。修复：
```bash
mkdir -p .git/refs/remotes/origin
printf '%s\n' <new-sha> > .git/refs/remotes/origin/master
```
修复后 `git rev-list --left-right --count origin/master...HEAD` → `0  0`。
★ 判断"推送是否真的成功"**必须**用 `git ls-remote origin refs/heads/master`（网络权威），
不能信本地 `origin/master`。

### O5 本次发布事实（0.1.8）
- 提交 `2a35357` "新增eosop_pro多类型文件处理模块"（**仅 `.gitignore`，+139 行，0 删除**）
- push：`aa8fb81..2a35357` → Gitee `physimx/flash`；`ls-remote` 复核 master = `2a35357`
- 注释标签 `0.1.8` = `7750cde`，已推远端；`0.1.4` 历史上不存在（跳过）
- **未提交**：工作区 41 项在制变更（credentials 重构 / SNB 场景族 / pyproject）刻意保留
- ⚠ `pyproject.toml` 版本仍为 `0.1.7`，与 tag `0.1.8` **不一致**（历史 0.1.3/0.1.5 亦如此）

---

---

# §P 离线安装（start_flash.py 双模式）+ wheel 体积（2026-10-09）

## P1. 双模式设计

唯一入口 `start_flash.py`，唯一分叉点 = `run_pip()`；健康检查 / 自愈重建 / 三套测试 /
`INSTALL_TEST_REPORT.txt` **两模式完全共用**。

| |在线（默认） | 离线 |
|---|---|---|
| pip | `install -e ".[full,dev]" scipy paramiko` | `install --no-index --find-links=<wh> "flash_sim[full,dev]" scipy paramiko` |
| 开关 | — | `--offline` / `FLASH_OFFLINE=1` / 自动探测 |
| 其他 | — | `--wheelhouse <dir>` / `FLASH_WHEELHOUSE` / `--profile full\|runtime\|lite` / `FLASH_PROFILE` / `FLASH_SKIP_TESTS=1` / `FLASH_FORCE_ONLINE=1` |

**`--no-index` 是硬闸门**：pip 物理上无法访问 PyPI，缺包立即报"No matching
distribution found"并指名缺哪个，**不会**静默联网补装 —— 离线部署最常见的翻车点
就是"装到一半才发现漏包，venv 半残，必须从头再来"。故离线另设**安装前**三道闸门：

1. wheelhouse 目录存在（含 `MANIFEST.json`）
2. `MANIFEST.json` 校验：每个归档的存在性 + 大小 + **SHA256**（U 盘拷贝最易静默损坏）
3. 依赖覆盖度预检：`pyproject` 依赖闭包 ⊆ wheelhouse 实际文件，缺则报**全清单**

三档 profile：`full`(base+full+dev, 71 包/126MB, 可跑三套测试) /
`runtime`(base+full, 保留 yt 出图) / `lite`(无 yt/matplotlib/pandas)。
**造包与安装两端档位必须一致**，否则闸门 3拦下。

### 实测（联网机真造包 + 离线安装，非静态检查）
- `build_wheelhouse.py --profile full`：71 包 / 126 MB / 140 s
- `install_offline.py`：rc=0 / 121 s；三套测试 **framework 132 + input_gen 83 +
  output_processors 45 = 260 全绿，0 失败**
- `flash` 以真 wheel 装入 site-packages（**非 editable**），`flash.__file__` 在 venv 内
- `test_offline_install.py`：**64/64 通过**（含 12 项负例）

## P2. ★ wheel 体积铁律

**每次 build 后核对 wheel 是 MB 级；GB 级 = exclude 漏了。**
根因：`.gitignore` **只管 git，不管 wheel/sdist 构建** —— 两者须**成对维护**。

09-09 实测：pyproject 的 hatch `wheel`/`sdist` exclude 漏了 .gitignore 已有的规则：
Multi1D++ 便携包（~1.5 GB，含 `gen_eos_op - 副本/` 重复一份）、
`scenarios/**/flash_input|flash_output/`、`_flash_output_contaminated_*/` 诊断污染快照
（~354 MB）、`*.tar/rar/tgz` ⇒ wheel **1.43 GB**、build **20 min 未完成**（被迫 kill）。
补齐后：**100 MB / 17.5 s**（构建提速约 70×）。

> ★ `dist/` 里旧 wheel 体积正常**不能当证据** —— 它可能早于新场景目录生成。

## P3. 造包/API坑

- **`pip download` 不支持 `--upgrade`**（那是 `install` 专有），传入直接
  rc=2 "no such option"。删掉即可（`download` 本就按索引取最新，不像 install
  受本机已装版本约束）。
- **造wheelhouse 必须把「项目本体 + pyproject 全量」作为 `pip download` 目标**，
  并配 `--find-links <wh_dir>` 让 pip 从**本地刚构建的 wheel** 解析本体，从而顺带解出
  base/extras 的传递闭包。若只传 scipy/paramiko 等少数几项，h5py/matplotlib/yt/
  pandas/pytest 会**整批缺失**。直接依赖 18 个 → 实际闭包 **71** 个，手写清单必漏。
- ★ **`.bat` 行尾由 `.gitattributes` 统一为 LF**（`.gitattributes:42` 明确
  `*.bat text eol=lf`）⇒ 校验器**只查「纯 ASCII + 无 BOM」**，行尾仅提示**不得强制
  CRLF**（否则任何新 clone 都会校验失败）。
- ★ `pip download` 默认按当前平台/解释器取包；离线机须**同版本 Python**。

## P4. 开发期踩坑（全部由实测暴露，静态检查/dry-run 无法发现）

1. **依赖解析器字符/行切片混淆** → base/full/dev 三档全解析为空 ⇒预检**假通过**。
   `text[start_line:]` 是**字符**切片，而索引是**行**号 ⇒ 必须迭代 `lines[start_line:]`。
   另需在 `depth<=0` 时先截断 `"]"`，否则 `"]"` 被当成 requirement 收进来（幽灵包名）。
2. **自动探测判据误伤所有在线用户**：曾用"`scripts/08_offline_install/` 目录存在"
   当离线判据，但该目录随仓库分发、联网机上永远存在 ⇒ 所有在线用户被误切离线。
   正确判据只能是 `wheelhouse/MANIFEST.json` **本身**。
   > 推论：探测判据必须是**运行产物**，绝不能用**随仓库分发的脚本目录**。
3. **`preflight()` 传 `str` 抛 AttributeError**（内部需 `.read_text()`）⇒ 须传 `Path`。
4. **自动定位漏 `offline_pkg/wheelhouse`**：造包默认输出在 `offline_pkg/` 下，
   定位只试 `<root>/wheelhouse` ⇒ 不传参数必然"找不到目录"。
5. **离线不能用 `-e .`**：editable 往 .venv 写**指向源码树的绝对路径**，U盘换机即失效；
   且需源码树含依赖声明（sdist 不含 tests/docs）。
6. **脚本不会自动执行 Python 安装程序** —— 装解释器属系统级变更，必须用户亲自确认。

> **教训**：判断"跨机器脚本能否在离线机工作"，唯一可靠办法是**真造包 + 真装一次**；
> 每个判定分支都该配负例断言（本次 64 项中 12 项为负例）。

## P5. ★★★ 第三轮（09-10 晚）：三个真事故 + 护栏自身失效

### ① ★★★ wheelhouse 实际装的是 **PyPI 上的过期公开包**（最严重）

`flash-sim 0.1.7` 已发布在 PyPI（1.53 MB / 224 条目）。造包时
`pip download flash_sim[full,dev] --find-links <本地目录>` 中，
**`--find-links` 不保证本地优先** —— pip 以
`WARNING: Previously-downloaded file ... has bad hash. Re-downloading.`
为由下载公开旧包，**覆盖**刚构建的本地 wheel：

```
覆盖前: 4.76 MB  sha256=dc3f3746b8d35909  entries=902
覆盖后: 1.53 MB  sha256=857941f55cf557a8  entries=224   ← 712 个文件消失
```

日志仍打印 `[ok]`，肉眼极难发现；`hpc_config.py` 等模块离线机装上后直接
`ModuleNotFoundError`。

- **根因修复**：`build_pip_freeze_list()` 把 pyproject 的 base + extras
  **全量展开后逐项列出**，跳过项目本体 ⇒ 本体 wheel 由 Step 1 直接放进
  wheelhouse，根本不经pip。
  ★ 与 P3 的旧结论**冲突但更优**：旧做法「本体 + find-links」正是本事故根因；
  全量展开后逐项传即可拿全 71 包闭包（`required_packages()` 的 human 列表
  已含 base+extras），**不再需要借助本体解析**。
- **防御**：Step 1 记SHA256 指纹，Step 2 后 `_ensure_local_wheel_intact()` 比对。
  ★ 必须用 **SHA256** 而非体积 —— 同名同版本的覆盖包体积可能接近。

### ② ★★ wheel 100.5 MB → **5.5 MB**（且修复我自己的误排除）

**深层根因**：hatchling 的 VCS 排除安全阀

```python
exclude_spec = pathspec.GitIgnoreSpec.from_lines(patterns)
if exclude_spec.match_file(self.root):
    return []      # ← 静默丢弃**全部** VCS 规则
```

根 `.gitignore:11` 的裸 `*` 匹配到项目根自身 ⇒ 命中安全阀 ⇒
**536 条 .gitignore 规则全部失效** ⇒ git 忽略的 336.8 MB 测试产物 +
FLASH 引擎源码（License §3 违规）被打进 wheel（占 **94.5%**）。
⇒ **本仓库 `.gitignore` 无法充当 wheel 排除规则**，两者必须成对手写。

修完 100.5 MB 后**又引入新回归**：为挡 62 GB 产物写的
`flash/scenarios/private/tracer/**` **误伤 116 个 git 已跟踪源码**
（151 .py / 33 .md / 9 .sh，含 `SNBOneCH_ml.py`、`run_cores_parallel.py`
等自研 SNB 场景主线）。实测 `flash_output/**`、`flash_input/**` 早已被
通用规则覆盖，真正漏网的仅 ~13.9 MB ⇒ 改为逐条精确排除
（`docs_diag/`、`plots/`、`temp_delete/`、`__pycache__/`）。
**最终：5.5 MB / 1028 条目 / 4 s**（vs 100.5 MB / 2873 条目 / 21×提速）。

> ★★ **铁律：凡新增 `private/` 排除，必须先核对
> `git ls-files flash/scenarios/private` 的已跟踪清单，禁止整目录排除。**

### ③ ★★ 护栏自己骗了我两次（**报喜不报忧的护栏比没有护栏更危险**）

1. **自建泄漏审计漏报 94.5%**：批量 `git check-ignore` 用
   `subprocess.run(text=True)`，Windows 走 ANSI 代码页（GBK/cp1252），
   CJK 路径被弄坏 ⇒ 同一输入报 1733 条 vs 正确 1855 条，实际泄漏
   336.8 MB 却报「0.4 MB」。⇒ 必须喂 **bytes** + 自行 UTF-8 解码；
   并用 `-z` 分隔（路径含空格/CJK 安全）。
2. **§3 判据用子串匹配误报**：`"MultiEOS" in name` 命中自研文档
   `MultiEOSOP格式说明.md`（git 已跟踪）。⇒ 改按**路径分量**精确匹配。
   另 `*.dist-info/` 由 hatchling 构建时生成、天然不在 git 里，
   须先剔除，否则每次审计 2 条假阳性。

> ⇒ 审计器已固化为 `scripts/08_offline_install/wheel_leak_audit.py`，
> `build_wheelhouse.py` 写完 MANIFEST 后**自动跑**，不过即中止
> （`--no-audit` 可逃逸）。判据按**体积**（容差 2 MB）而非文件数 ——
> 残余 50 个 `results/*.json` 共 384 KB 是科研快照，对使用者有价值。
> **未证明会失败的护栏不算护栏** ⇒ 回归里配了负向样本（rc=1 断言）。

### ④ 其他

- **陈旧 wheel 静默回退**：造包前先 `_quarantine_previous_wheels()` 把上一轮
  产物挪进 `.stale/`（★ 必须在**构建前**，否则会把自己刚建的 wheel 挪走——
  我第一次就写反了，静态检查看不出）；`dist/` 退路须显式 `--allow-legacy-dist`。
- **假阴性护栏**：`test_offline_install.py` 只把脚本目录加 `sys.path`，而
  `start_flash.py` 在**项目根** ⇒ `test_switch_matrix` 整节静默跳过，
  报「导入失败」但手动导入完全正常。补 `PROJECT_ROOT` 后该项真实执行。
  ⇒ 断言 `entries < 100` 判残包时须写成 `0 <= n < 100`（`-1` 表示读失败）。
- **实测数据（09-10 第三轮）**：本体 wheel 5.5 MB/1028 条目；full wheelhouse
  **130 MB / 71 包 / 119 s**；离线 `--no-index` 装 **67 包**，装完 `.venv`
  **647 MB**；离线 venv 跑测试 **framework 132 passed + input_gen 577 +
  flychk_his 223 + output_processors 45**；`test_offline_install.py`
  **124/124 通过**（含负例）。
- **仓库轻量化实测**：`flash/` 磁盘 **71 GB**，但 git 跟踪仅 **17.2 MB /
  1391 文件** ⇒ `usb_backup.py --mode gitee` 导出即 17.2 MB（文件列表来自
  `git ls-files --cached --others --exclude-standard`）。
  历史 pack 37 MB，最大 blob 是**已从 HEAD 移除**的
  `ionmix/.../test/report.html`（36 MB），当前 HEAD 最大文件仅 0.8 MB。
- **既有失败（非本轮引入）**：`test_declared_types.py` 硬编码 `expect_eq(len(dts),
  1214)`，而 `e825275` 删了 `sv_physics.py`/`sv_plots.py` 两个文件 ⇒ 实际 1213，
  **两个 venv 均复现**。修法：把期望值改为 1213 或改为动态断言。

## P6. 仓库轻量化 / U 盘迁移（2026-10-09 实测）

| 对象 | 磁盘实测 | git 跟踪 | U 盘要拷 |
|---|---|---|---|
| `flash/` 全目录 | **71 GB** | — | ✗ 禁止整目录拷 |
| git 跟踪内容（HEAD） | — | **17.2 MB / 1391 文件** | ✓ 17.2 MB |
| `full` wheelhouse | 130 MB / 71 包 | — | ✓ 130 MB |
| 装完 `.venv` | 647 MB | — | ✗ 离线机自建 |

⇒ **U 盘净荷 ≈ 147 MB**（wheelhouse 130 + 源码 17.2）。

导出源码**必须**用现成脚本（文件列表来自
`git ls-files --cached --others --exclude-standard` ⇒ git 忽略的一律不拷）：

```bash
python scripts/04_backup/usb_backup.py --mode gitee E:/usb_target
```

- `usb_backup.py --mode full` 是「几乎全量」，**不用于 U 盘迁移**（会带 71 GB）。
- `.gitignore` 对以下全部有效（09-10 逐条 `git check-ignore` 验证）：
  `flash_output/`、`flash_input/`、`SNBtest/src/`、`_out/`、`Multi1D++Portable*`、
  `Others_data/*.cn4`、`.venv/`、`.workbuddy/`、`env/`、`dist_new2/`。
- git 历史 pack **37 MB**，最大 blob 是**已从 HEAD 移除**的
  `ionmix/ionmix/eosop_pro/test/report.html`（**36 MB**，单文件超限）。
  当前 HEAD 最大文件仅 **0.8 MB**（`MultiEOSOP格式说明.md`）。
  ★ 若要进一步瘦身，需 `git filter-repo` 重写历史 —— 会改写所有 SHA，
  **须与远端协调**，本轮未做。

# §Q fresh-clone 端到端验证（2026-10-10）

## Q1. 分步验证矩阵（Gitee → tempt，全实测）

| 步骤 | 结果 |
|---|---|
| Gitee 拉取 | tempt HEAD == 远端 `1a63348`，1391 文件 / 26 MB |
| wheelhouse | 71 包 / 131 MB / MANIFEST SHA256 深校验 **0 问题** |
| 闸门③ 依赖预检 | full 18 / runtime 12 / lite 8，全部 **0 缺失** |
| 离线安装 | `--no-index` + 代理 `127.0.0.1:9`（不可达）⇒ 66 包全本地，118 s |
| 三套测试 | framework **132 PASS** / output_processors **45 PASS** / input_gen 82+1 |
| 官方一键 1D 仿真 | **FLASH_EXIT_CODE=0** / 342 chk / 1707 输出 / 3 张 PNG |

## Q2. ★★ gen_checker 未剥离 .par 行尾注释（fresh-clone 才暴露）

**现象**：干净克隆后跑 `laserslab1d_local_custom.py`（零修改），[步骤 1/5] 硬失败：

```
[X] [FAIL] par_cn4_on_disk: 缺失 4 个被 .par 引用的表文件:
[X]   ['"Z02_1.00-20260708_0851.cn4"       # cham opacity opacity table file', ...]
[X] [FAIL] par_cn4_in_config_datafiles / config_table_parameter / dimension_grid_vs_setup
```

★ 报错里的「文件名」**带着尾随注释** ⇒ cn4 其实在磁盘上。

**根因**：`relations/_core.py: par_params()`

```python
m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
out[m.group(1)] = m.group(2).strip()      # ← 值里含 `"xxx.cn4"  # 注释`
```

只 `strip()`、**从不剥注释**；而 input_gen 生成的 .par 大量用**对齐行尾注释**
⇒ 3 条「文件存在性」规则同时误报 ⇒ 阻断官方一键仿真。

**为何主仓库测不出**：`flash_input/` 被 `.gitignore:403` 排除（生成目录），
主仓库的旧产物恰好与 clone 产物一致 ⇒ **掩盖了缺陷**。

**修法**：新增 `relations/_parsers.strip_par_comment()`，`par_params()` 改用它。
★ 只切**引号之外**的第一个 `#`（扫描时维护引号状态）⇒ 含 `#` 的合法路径不被截断。
提交 `5f62d5a`（2 文件 +45/-2）。

⇒ **铁律：凡改「生成器 / 解析器 / 检查器」，必须在 fresh clone 上验证。**
   主仓库本地能过 ≠ 干净克隆能过。

## Q3. 官方 1D LaserSlab 实测物理（离线 venv 读回 chk）

CH 靶 1 g/cm^3 居中 ±30 µm、两侧真空、5e14 W/cm^2 × 2 束 351 nm、1 ns 平顶。

| chk | Tmax (K) | Tmax (eV) | dens max (g/cm^3) |
|-----|---------|-----------|------------------|
| 0000 | 2.9e2 | 0.03 | 1.00 |
| 0068 | 2.1e7 | 1849 | 4.72 |
| 0171 | 2.7e7 | 2360 | 10.04 |
| 0341 | 8.8e6 | 758 | 2.17 |

⇒ 完整呈现「升温→峰值→冷却」激光烧蚀演化；温度量级与固体靶一致。
§J 复核：chk 温度是 K，换 eV 须 `/11604.518`。

## Q4. 我走的弯路（★别重犯）

1. **手改 par 造 Sedov 测试** —— 用户明确「仅用真实 1D LaserSlab 配置」。
2. **绕开官方脚本手工部署 WSL** —— 根 `README.md`「②」已给出入口，
   且 `RUN_MODE = "wsl"` **默认就是本地 WSL，零修改**。
3. **误判 editable 误用** —— `flash.__file__` 指向源码树是因 `cd` 到项目根
   使 `sys.path[0]=''`；判据应看 `pip show flash_sim` 的 `Location`。

## Q5. WSL 跑 FLASH 的坑

- **venv 路径环境变量 = `FLASH_VENV_DIR`**（我先用 `FLASH_OFFLINE_VENV` 无效，
  脚本静默回落到默认 `.venv`）。
- **FLASH 4.8 只读默认名 `flash.par`**：`-p xxx.par` 与位置参数都无效，
  报 `unable to open parameter file "flash.par"` ⇒ 直接 `cp` 成 `flash.par`。
- 可用二进制：`/home/LaserSlab_local/flash4`（编译好的 ELF 64-bit）；
  `/flash4` 不是可执行文件；`/home/flash_1782991316/flash4` 需配
  `polystyrene-imx-008.cn4`（该二进制的默认第三材料）。
- chk 是 **type1_hdf5 块结构**：dataset 形如 `(nblocks,1,1,ncell)`，1D 时中间两维
  恒 1；坐标取自 `bounding box` (nb,3,2)；**不可当规则数组直接用**。
- bash 里嵌 heredoc 写 par 会被外层引号吃掉（`syntax error near unexpected token '('`）
  ⇒ 改用 Python 脚本在 WSL 内直接写文件。
- Windows 侧 `cp` 到 WSL 会把 CRLF 转成 LF（Git Bash 行为）——
  这与「`.gitattributes` 统一 LF」一致，**不是** bug。

## Q6. 既有小缺陷（未修）

`*_wsl.png` 三张图取**首个**输出文件（290 K 初始态）而非终态（chk_0341 已 8.8e6 K）
⇒ 图上看不到烧蚀，属出图取样问题，不影响仿真数据本身。

## P7. ★ 跨平台：venv 布局（09-10 WSL 实测暴露，提交 f5429ee）

**现象**：Linux/WSL 上离线安装**必然失败**，且报错无任何线索：
`[FATAL] 创建 venv 失败:` 后 **stderr 全空**；健康检查恒判失败 → 反复清零重建。

**根因**：venv 内可执行文件路径**硬编码 Windows 布局**（三处）：

| 位置 | 旧值 |
|---|---|
| `_wh_common.py: VENV_SUBPATH` | `("Scripts", "python.exe")` |
| `start_flash.py: run_pip()` | `os.path.join(VENV_DIR, "Scripts", "pip.exe")` |
| `start_flash.py: main()` | `os.path.join(VENV_DIR, "Scripts", "python.exe")` |

Linux 上 `python -m venv` 生成 **`bin/python`**（无 `Scripts/`、无 `.exe`）⇒
`create_venv()` 里 `not os.path.isfile(VENV_PY)` **恒为真** ⇒ venv 明明创建成功
也判 FATAL（`rc == 0` 但报错，stderr 空）。

**修法**：`VENV_SUBPATH` 随 `os.name` 取值；`start_flash.py` 统一由
`_wh_common.venv_python()` 给出（保留本地兜底 —— sdist 里`scripts/` 可能缺失）；
`run_pip()` 的 pip 路径同样分支；`create_venv()` 报错**区分两种失败**
（命令失败 → stderr+rc；命令成功但路径不存在 → 提示布局不匹配 + `os.name`）。

验证：Windows `venv_python(.venv)` = `.venv\Scripts\python.exe`；
Linux = `.venv/bin/python`；`test_offline_install.py` 124/124 无回归。

## P8. ★★ 真实断网测试：Linux `unshare -n`（比设代理更硬）

```bash
unshare -n -- python3 scripts/08_offline_install/install_offline.py
```

`unshare -n` 起独立 network namespace，**TCP 与 DNS 同时不可达**。
断网自检（务必先做，否则「断网测试」可能没真断）：

```bash
unshare -n -- curl -s -m5 https://pypi.org            # 应失败
unshare -n -- python3 -c "import socket;socket.setdefaulttimeout(4);\
  socket.create_connection(('pypi.org',443))"
#   → socket.gaierror: [Errno -3] Temporary failure in name resolution
```

对比：Windows 上只能用 `HTTP_PROXY=127.0.0.1:9`（可被 pip 的
direct/PROXY 绕过，强度较低）。

**实测结果**（WSL Ubuntu-22.04 / Python 3.10.12）：78 包 / 165.4 MB；
framework 132 / input_gen 83 / output_processors 45 全PASS；369 s；
`pip show flash_sim` 的 Location 在 `.venv/lib/python3.10/site-packages`
⇒ 真 wheel 非 editable。

## P9. ★ 造包必须同平台 + 同 Python 版本

| 平台 | full 档 |
|---|---|
| Windows (Python 3.13) | **71 包 / 130 MB** |
| Linux (Python 3.10) | **78 包 / 165.4 MB** |

wheel 文件名带 `cp3XX-` **ABI 标签**（如 `numpy-2.5.3-cp313-cp313-win_amd64.whl`
vs `cp310-cp310-manylinux`）⇒ **联网机与离线机必须同平台同Python 版本**，
否则 `--no-index` 下直接缺包，且报错只说"No matching distribution found"，
不会提示「平台不匹配」。

## P10. 环境前置依赖（Linux/WSL）

**Ubuntu-22.04 默认未装 `python3.10-venv`** ⇒ `python3 -m venv` 报
`No module named 'ensurepip'`。需：

```bash
sudo apt install -y python3.10-venv
```

★ 这也是「报错须能区分失败原因」的典型：修好路径 bug 后此环境问题才暴露；
若报错仍只印空 stderr，用户就得自己猜。

---

## R. ★★★ Gitee 推送：403 的隐蔽真因与正确通道（2026-10-21）

### R1. 症状与误判
`git push origin master` →
`remote: The token is not authorized to access this project` + HTTP 403。

**误判**：看到 `git ls-remote origin master` 成功，就推断"token 只有读权限"。
**为什么错**：`physimx/flash` 是**公开仓库**（匿名 `curl` 返回 200），匿名即可 ls-remote。
`ls-remote` 成功只能证明"仓库可读"，**完全不能**证明 token 有效或具备写权限。

### R2. 真因
`~/.gitconfig` 中：
```
credential.https://gitee.com.helper =        ← 空值（等号后什么都没有）
```
git 的语义：`credential.<url>.helper=`（**空值**）不是"未设置"，而是把该 URL 的
helper 链**重置为空**，即**禁用 gitee.com 的全部凭据助手**。
没有 helper ⇒ 不提供任何凭据 ⇒ git 以匿名身份推送 ⇒ 403。
即使同时存在 `credential.helperselector.selected=manager` 与
`credential.https://gitee.com.provider=generic`，仍被这个空值覆盖。

排查命令（按信息量排序）：
```bash
git config --list --show-origin | grep -i credential   # 找空值/坏路径
git config --get-all credential.helper                 # 看生效的 helper 链
```

### R3. 验证 token 是否真的有效（必须走需鉴权的 API，不能靠 ls-remote）
```python
# 从加密库取 token，走 HTTP 头鉴权，不落 argv
from flash._core.credentials import get_credential_manager
t = get_credential_manager().get("gitee")["token"]
# GET https://gitee.com/api/v5/user              → 200 + login
# GET https://gitee.com/api/v5/repos/physimx/flash → permission{pull,push,admin}
```
本次实测：`/user` → `quincyhoward`；仓库 `permission={"pull":true,"push":true,"admin":true}`，
owner 即 quincyhoward ⇒ **token 完全有效**，问题纯在 git 配置层。
（`/user/keys` 返回 401 只说明 token scope 不含该端点，与 push 无关。）

### R4. 正确通道：项目脚本
```bash
.venv\Scripts\python.exe scripts/03_git_publish/git_push.py
```
它绕开 `.gitconfig` 的全部坑：
`flash._core.credentials`（Fernet 加密库）读 token →
`_git_auth.auth_prefix()` 注入
`-c credential.helper=`（**先清空**）+ `-c credential.helper=!"<py>" "<helper.py>"`，
凭据经**管道**交给 git ⇒ 不进 `.git/config`、不进 `argv`（`ps` 看不到）。

参数：`-m` 提交信息、`-b` 分支、`-f` 强推、`-n` dry-run、`--status` 查状态、
`--setup` 改凭据、`--allow-deletes` 放行删除。
★ 它内含 `git add -A`，**有在制变更时禁用**（E: 盘间歇不可见会误提交删除）；
   工作区干净时才可直接用。

### R5. 修复与验收
```bash
cp ~/.gitconfig ~/.gitconfig.bak_$(date +%Y%m%d_%H%M%S)
git config --global --unset-all credential.https://gitee.com.helper
```
随后脚本推送成功，并用 hash 对账（判成败的唯一标准）：
```
local  HEAD = 39128c1...
remote master = 39128c1...   → MATCH
```

### R6. 其它踩过的环境坑
- 全局 `credential.helper` 曾指向 `PortableGit/versions/**1.2.0**/...git-credential-manager.exe`，
  该版本已不存在（现为 `1.3.0`）⇒ `could not read Username`。用绝对路径指向现存版本。
- 凭据库里 `gitee` 条目应为：`username`/`login`=Gitee **登录名**（显示名会 403）、
  `token`=32 位私人令牌、`repo_url`=不含凭据的 https 地址。

---

## §T flash-sim 超算离线部署链（2026-10-22 建成，NC-E <ACCOUNT>）— 全文

- 部署目录 `~/PhySimX/PhySimX/simulation/flash/flash_sim`（=Gitee 同步目录，HEAD 随 bundle 走）；
  命名环境 **`.venv-hpc-nce`**（module python/3.10.8，离线 --no-index），三套测试 132/83/45 全绿。
- 脚本在 **`deploy/hpc_deploy/`**（run_all.py 编排 00–08 + 05b）；文档=《flash-sim的超算部署与测试.md》
  （flash/flash_run/remote/test/，含 §9 实测结果、§4 问题库）。
- 交叉造包（build_wheelhouse_linux.py）：glibc2.17 锁定 pandas2.3.2/h5py3.14.0/pillow12.2.0/
  ewah1.2.2/**yt4.4.0**（4.3.1 在 NC-E 全节点 SIGSEGV！）；--python-version 须写完整 3.10.8；
  垫片+jeepney/secretstorage/pexpect/ptyprocess 手动补。
- 超算铁律：/tmp 节点本地盘（跨会话只走 $HOME 并行盘+哨兵）；git 1.8.3 无 -C；裸 python3=3.6.8；
  Lustre 大 pip 事务会随机 ENOENT → 断点续装循环；paramiko exec nohup& 失败≠未执行（先 ps 查重）。
- **代码改动同步用 `sync_incremental.py`**（只传 42MB bundle + fetch/ff-merge，幂等）；
  仅依赖/EOS 表变化才走 package_and_upload.py（212MB 含 wheelhouse）。
- **Step 08 public 测试最终全绿（2026-10-22 20:16）**：A1/A2/B 全 rc=0，三场景 sbatch 真跑
  ch_center=37 / grad_dens=12 / thin_layer=4 个 chk（作业 4918247/4918248/4918249）。
- ★★ **远端多轮并发五坑（本地复现不出，全靠超算实测）**：
  ① sbatch 下 `dirname "$0"` → /var/spool/slurm/d/jobXXX ⇒ 输入目录必须显式锚定
  （patch_job --input-dir）；② 场景脚本 `mpi/hpcx/*`(Intel) 编译 FLASH 报 Fortran #6404
  ⇒ 归一 `mpich/3.2-gcc9.3`；③ chk 统计须覆盖 `out/<tag>_run` + `out/<tag>_outputs` + `$DST`
  三处（只查一处 ⇒ 跑成功却 n_files=0）；④ 日志/报告**必须带 run_id**（固定路径会被残留
  僵尸实例混写，本地读到的 B_RC 属于另一轮）⇒ 启动前枚举僵尸并中止/--kill-stale；
  ⑤ **禁 `pkill -f public_test_`**（匹配到执行 pkill 的 shell 自身 ⇒ SSH 自杀）⇒ 按 PID kill。
- ★ sacct State 带前导空格 ⇒ `awk 'NF{print $1;exit}'|tr -d ' \r'`；启动重试会真多起实例 ⇒ mkdir 原子锁。

## §U 发版 0.1.11「多平台适配优化」全过程（2026-10-22）

- 三项要求：① 根 README 加 GitHub 仓库信息；② 同步 Gitee + 打标签 0.1.11 标注「多平台适配优化」；
  ③ 发 PyPI 0.1.11。
- README 改动 4 处：徽章区加 GitHub 徽章；中文「仓库地址」段改双平台（Gitee 主 / GitHub 镜像）；
  表格加「HTTPS 克隆 (GitHub)」「在线浏览 (GitHub)」，问题反馈指向双 Issues；英文
  `## Repository` / `## Contact` 同步加 GitHub。
- pyproject.toml：version → **0.1.11**；`[project.urls]` 新增 GitHub / GitHub-Issues / Changelog。
- ★ `flash.__version__` 长期漂移 bug：原硬编码 `"0.1.0"`，pyproject 已 0.1.7 ⇒ pip show/bug report
  长期误导。修法见 MEMORY.md §S。
- ★ `publish_pypi.py` 用 `dist/*`，根 `dist/` 已迁 `artifacts/dist` ⇒ **静默找不到产物**；
  改 `_dist_dir()` 双路径查找（artifacts/dist 优先，回落 dist/）。
- `deploy/build_wheelhouse.py` 硬编码 `flash_sim-0.1.7-...whl` → 泛化为 `flash_sim-<version>-...`
  （`deploy/test_offline_install.py` 里的 `0.1.7` **刻意保留**，是文件名归一化测试的任意夹具）。
- `git_push.py` 新增 `--tags`：标签推送与分支推送走**同一条 credential helper 管道**
  （token 绝不进 `.git/config`、绝不进 argv）。
- 产物：`artifacts/dist/flash_sim-0.1.11-py3-none-any.whl` (5,349,624 B) + `.tar.gz` (37,547,040 B)；
  `wheel_leak_audit.py` 四闸门过（928 条目 / 5.10MB 压缩 / §3 材料 0 / 泄漏 68 文件 962.5KB
  < 2048KB 容差）；`twine check` 两项 PASSED。
- 提交链：fc5dd45(release) → d52d2c5(feat git_push --tags) → 903a913(docs readme 排版)。
  README 有一处来源不明的外部改写（拆分两行），核实为纯排版等价、已纳入提交。
- Gitee 核验（用 `git ls-remote` 而非 push 输出判成败）：remote master = 903a913 == 本地 HEAD；
  `refs/tags/0.1.11` = b23b6e0d（annotated tag），`refs/tags/0.1.11^{}` = 903a913 ⇒ 标签指向发布 commit。
- ★ PyPI 发布绕坑：`publish_pypi.py` 整脚本被 **SIGTERM**（`python -m flash._core.credentials.pypi list`
  同样 SIGTERM）⇒ 改**分步手动**：`twine check` → `twine upload artifacts/dist/flash_sim-0.1.11-*`
  （凭据在 `~/.pypirc`，upload.pypi.org/legacy + `__token__`）。页面 https://pypi.org/project/flash-sim/0.1.11/
- PyPI 核验：`https://pypi.org/pypi/flash-sim/json` ⇒ latest=**0.1.11**，releases 含 0.0.1/0.1.7/0.1.11；
  project_urls 六项齐全。
- ★ 干净 venv 真安装验证（防 `pip download` 同名覆盖老坑）：`pip install flash-sim==0.1.11` 成功；
  `flash.__version__`=0.1.11、dist version=0.1.11、Requires-Python>=3.10；
  `flash.scenarios.registry.get_scenario` / `list_scenarios()` 正常。
- ⚠ **非回归确认**：已安装包跑 `ensure_sim_input()` 报 `RuntimeError: Cannot locate flash package root`
  ⇒ **0.1.7 旧版完全相同行为**（同环境对比实测）⇒ 设计上的「源码模式」限制（场景生成需
  FLASH 源码树，Config/Makefile/Simulation_*.F90 不随包分发），**非 0.1.11 回归**。
- 临时验证环境已清理（/tmp/verify_pypi_0111、verify_pypi_017、smoke0111、smoke017）。

## §V demo_local 零输出故障全文（2026-10-23）

- 用户现象：`flash_demo/demo_local/laserslab1d_local_demo.py` 只生成 9 个输入文件，无 HDF5、
  无图像，却打印「FLASH 仿真完成 ✓」「Demo 成功!」并 exit 0。
- 根因 1（FLASH_HOME 不一致）：demo 用 `~/{SIM_USER_DIR}/FLASH/FLASH4.8` 做检查，
  但 `create_input_files` 无 `flash_home` 形参 ⇒ `run_flash.sh` 拿到默认
  `$HOME/FLASH/FLASH4.8`（不含用户名）⇒ `[1/5]` `exit 1`。实测 WSL 只有
  `/root/QC/FLASH/FLASH4.8` 有效（含 setup + SimulationMain）。
- 根因 2（管道吞 rc）：`bash run_flash.sh 2>&1 | tail -100` 的 `$?` 是 tail 的（恒 0）。
- 根因 3（漏子目录）：`run_flash.sh` 自动 run_id 把产物放进 `outputfiles/run_NNNNNN/`，
  demo 用单层 glob + 单层 cp ⇒ 即使成功也拷不回。
- 根因 4（.bat 硬编码）：`generator.py:418` 的 `set FLASH_HOME=~/FLASH/FLASH4.8` 是字面量，
  完全忽略 `cfg["flash_home"]`。**由本次新增护栏测试抓出**（我最初只修了 sh）。
- 跨层传参坑：(a) shell glob 的 `*` 经 Windows→wsl.exe→bash -c 被吃掉，**无输出也无报错**
  （heredoc 直连正常）⇒ 一律用 `find`；(b) `echo "MARK=$v"` 与 `tail` 同管道会丢行 ⇒ 写文件。
- `/root/QC/FLASH/FLASH4.8` 顶层曾是 flash-sim 仓库克隆（`.git`/`flash/`/`deploy/`），
  只有 `source/Simulation` 被当 staging ⇒ 判"引擎树"须 `setup` + `SimulationMain` 两个条件。
- `discover_flash_home()` 在 Windows 侧返回 None（扫 `$HOME` 的 POSIX 路径）
  ⇒ 本地 demo 必须在 WSL 内探测。
- 实测：rc=0、784 步、80 个 chk/plt、出图正常（Al 2.7 g/cm³ + He 腔，界面 x≈0.0142 cm）。
- 提交 b93015a；护栏 `TestFlashHomePropagation` 3 项（已负向验证）。
- 遗留：两个 demo_hpc 的 `create_input_files` 调用同样没传 `flash_home`（远端路径走法待查）。

---

## ★ 归档：MEMORY.md 精简前的全文（2026-10-24）

（这些段落在 MEMORY.md 精简时被压缩；完整原文保留在此备查。）

### [MEMORY 精简归档] wheel 体积与发布铁律（2026-10-24 精简前全文）

## ★★★ wheel 体积与发布铁律（全文见 reference §P2/§P5）

- build 后必核对 wheel 是 **MB 级**；GB 级 = exclude 漏了。★ **本仓库
  `.gitignore` 不能充当 wheel exclude**（根 `.gitignore:11` 裸 `*` 触发
  hatchling VCS 排除安全阀 ⇒ 536 条规则全失效）⇒ wheel/sdist 排除须**成对维护**。
- ★ **禁整目录排除 `private/`**（误伤 116 个 git 已跟踪源码）⇒ 新增排除前必查
  `git ls-files flash/scenarios/private`，只逐条精确排除产物目录。
- ★ `pip download` 会用 PyPI 同名包**覆盖本地 wheel**（`--find-links` 不保证
  本地优先）⇒ download 列表跳过本体；Step 1 记 SHA256、Step 2 校验（用指纹非体积）。
- 造包后自动跑 `wheel_leak_audit.py`（按**体积**判定），不过即中止。
  ★ **未证明会失败的护栏不算护栏**；★ **报喜不报忧的护栏更危险**（栽过三次：
  `text=True` 漏报 / §3 子串误报 / 只加 sys.path 让 `start_flash.py` 整节静默跳过）。
- 跨机器脚本**必须真造包+真装一次**才算验证。


### [MEMORY 精简归档] start_flash.py 双模式（精简前全文）

## ★★★ `start_flash.py` = 在线/离线**双模式**（§P1）

唯一入口，唯一分叉点 = `run_pip()`；健康检查/自愈/三套测试/报告**两模式共用**。
离线 `--offline [--wheelhouse D] [--profile full|runtime|lite]`（或 `FLASH_OFFLINE=1`）
→ `--no-index --find-links` 装真 wheel。
★ 自动探测判据**只能是 `wheelhouse/MANIFEST.json` 本身**（脚本目录随仓库分发）。
★ 离线**不用 `-e .`**（editable 写绝对路径，U 盘换机即失效）。
★ **U 盘净荷 ≈ 147 MB**；`flash/` 磁盘 71 GB ⇒ **禁整目录拷**。


### [MEMORY 精简归档] 场景 par 物性铁律（精简前全文）

## ★★★ 场景 par 物性铁律（全文见 reference §P）

- **`_par_layers.py` 已退役**（只读留存，零 import）：它是某次 CH 算例 par 的快照，
  其 `ms_*A/Z`/`sim_rho*`/`eos_*表` 会**覆盖 Config 默认值** ⇒ 换材料只改一半
  会静默错算（V 层 t=0 压强 ×15.1）。
- **物性只能由场景自声明**：`par_gen.set_species_materials()` +
  `assert_material_binding()`（不一致即 raise）。
- **物理/数值基线在通用层**：`gen_par.defaults.LAYER_TRACER_BASELINE`（277 键，
  **不含材料身份**）。范式：`ParGeneratorExtended(dim=1).reset_to(BASELINE)`。
- 护栏：gen_checker `par_material_in_config`（par **值** vs Config 默认值）；
  老规则 `par_sim_in_config` 只查键存在性 ⇒ 这就是漏网原因。
- ★ **两个真跑才暴露的坑**：① `PARAMS_1D` 是 LaserSlab demo 默认，直接当基线会改
  `diff_eleFlCoef` 0.08→0.06 / 脉冲 82→5 段 / MGD 10→6 群；② **整数参数写成浮点
  会 abort**（`plotFileNumber = 0.0`）。par 中未声明的键 FLASH 不 abort、只静默不生效。
- **验证捷径**：FLASH `chk` 里有 `real runtime parameters`（name/value 数组），
  可读**实际生效**的 `ms_*A/Z` —— 比看 par 文本可信。


### [MEMORY 精简归档] SNB 默认超算（精简前全文）

## ★★ SNB 场景默认走超算（全文见 reference §R）

- `SNBOneCH_m/_ml` 的 `--mode` 与 `FLASH_RUN_MODE` **默认已改为 hpc**；本地跑需
  显式 `--mode wsl --nproc <本机核数>`。
- 原因：nprocs 是**网格定义的一部分**（`iProcs×nxb=25000 → dx=0.02 µm`），改核数即
  SystemExit；且 131 进程在 24 核本机超订卡死（36 min 只推进 4 步）。
- ★ **超算 SSH 限并发** ⇒ 多场景同时提交会全部卡住 ⇒ **串行**。
- ★ **后台任务必须 `PYTHONUNBUFFERED=1`**，否则日志停在缓冲边界像挂死。


### [MEMORY 精简归档] 超算离线部署链（精简前全文）

## ★★ flash-sim 超算离线部署链（全文见 reference §T）

- 部署目录 `~/PhySimX/.../flash/flash_sim`；命名环境 **`.venv-hpc-nce`**
  （module python/3.10.8，离线 --no-index）；脚本在 `deploy/hpc_deploy/`。
- **代码改动同步用 `sync_incremental.py`**（42MB bundle + fetch/ff-merge，幂等）；
  仅依赖/EOS 变化才走 package_and_upload.py（212MB）。
- ★★ **远端多轮并发五坑**（本地复现不出）：① `dirname "$0"` → spool 目录；
  ② Intel MPI 编译报 #6404 ⇒ 归一 `mpich/3.2-gcc9.3`；③ chk 统计须覆盖三处；
  ④ 日志/报告**必须带 run_id** + 启动前僵尸守卫；⑤ **禁 `pkill -f`**（自杀）⇒ 按 PID kill。


### [MEMORY 精简归档] §S 发版三件套（精简前全文）

## ★★★ §S 发版三件套一致性（全文见 reference §U）

- **三件套必须同号**：`pyproject [project].version` = git tag = PyPI = `flash.__version__`。
- ★ `flash.__version__` **别硬编码**：`pyproject.toml` 优先 → importlib.metadata → "unknown"。
- ★ 根 `dist/` 已迁 `artifacts/dist` ⇒ 用 `_dist_dir()`；★ `publish_pypi.py` 整脚本
  SIGTERM ⇒ 改**分步手动**（`twine check` → `twine upload`）。
- ★ 判推送成败用 `git ls-remote`；标签走 `git_push.py --tags`（token 不进 argv）。
- ⚠ 已装包 `ensure_sim_input()` 报 `Cannot locate flash package root` 是**设计限制** ⇒ 非回归。


### [MEMORY 精简归档] §V 生成了但没跑（精简前全文）

## ★★★ §V 「生成了但没跑」/「跑失败却报成功」的防线（全文见 reference §V）

一次 demo 故障挖出 4 个**静默失败**型 bug：
① 生成期写死的路径必须与运行期同源（`run_flash.sh` 的 FLASH_HOME 是生成时写死的
⇒ 探测必须在生成脚本**之前**）；② 管道吞返回码（`| tail -N` 的 `$?` 是 tail 的
⇒ rc 写入独立文件再读回）；③ 产物常在子目录 ⇒ 收集必须 `find -type f` **递归**；
④ 成功判据须为「rc==0 且产物数>0」。
- ★★ Windows→wsl.exe→bash -c 两坑：shell glob 的 `*` 被吃掉（**无输出也无报错**）
⇒ **一律用 `find`**；混合管道里的标记行会丢 ⇒ 写文件。
- ★ 判「FLASH 引擎树」须 `setup` **且** `SimulationMain`；★ `discover_flash_home()`
  在 **Windows 侧返回 None** ⇒ 本地 demo 必须在 WSL 内探测。




## §Y 超算离线安装 + 三公开场景实测（2026-10-26）— 全文

**结果**：三个 public 场景在 NC-E 全部跑通 —— ch_center（4924413，341 chk）、
grad_dens_sandwich（4924566，629 chk，5:25）、thin_layer_sandwich_si
（4924560，34 chk，4:25）。超算三套测试 framework 221 / input_gen 86 /
output_processors 45 全绿。同步 commit 1198b9f。

### 挖出的 9 个真 bug（全部超算实跑复现）

1. **超算误走在线安装** ⇒ `probe_hpc()`（SLURM 三命令齐备 + `sinfo -s`
   返回分区行）⇒ 强制离线 + 复用命名环境 `.venv-hpc-nce` + 无外网立即
   失败（不再 60 s 无限重试）。
2. **`WHEELHOUSE` 全局为空** ⇒ 该变量**只在 `setup_offline()` 里赋值**；
   Step 0 因"venv 健康"跳过它（而它才是唯一赋值处），随后 FORCE_CLEAN
   要真装包 ⇒ pip 拿到空 `--find-links=` ⇒ "no version satisfies
   setuptools"（且提示里的路径也是空 ⇒ 极难自查）。修法：
   `_should_setup_offline()` —— 显式 `--wheelhouse` / FORCE_CLEAN /
   环境不健康，三者任一成立 ⇒ 必须走预检。
3. **wheel 曾达 280 MB** ⇒ `modes_test/results/` 未排除（1714 文件 /
   640 MB）⇒ pyproject 的 wheel+sdist 成对补排除规则。
4. **sbatch 下 `SCRIPT_DIR` 指向 spool 目录** ⇒ `dirname "$0"` 拿不到
   par ⇒ 作业立即 FAILED（"cp: cannot stat .../jobNNNN/*.par"）。
   改用 `SLURM_SUBMIT_DIR`（并用 `compgen -G` 计数校验）。
5. **`%%j` 未展开** ⇒ SBATCH 输出文件名 literally 含 `%%j` ⇒ 日志不落盘。
6. **thin_layer 的 module 不存在**（`mpi/hpcx/2.17.1`、`hdf5/1.14.3`）
   ⇒ 归一到 `mpich/3.2-gcc9.3` + `hdf5/1.8.18`。
7. **链接期 `cannot find -lmpifort/-lmpi`** ⇒ ★ **任何 `module load`
   都会污染 ifort/mpiifort 的隐式 MPI 库路径**（module 设的
   LIBRARY_PATH/CPATH 指向旧 Intel 2018，屏蔽 oneAPI 自带的 libmpifort）。
   超算对照实测：无 module ⇒ 链接 OK；load mpich ⇒ FAIL；load hdf5 ⇒
   FAIL（连显式 -L 都救不回）⇒ 编译阶段**无模块** + 显式库路径。
8. **运行期 MPI_Init SIGSEGV（forrtl 174）** ⇒ oneAPI 2022.1 的
   `lib/release` 组合在该集群会崩；改用 **Intel 2018 的
   mpi/intel64/lib**（其 mpiifort 实为 Intel MPI 2021.5.0 ⇒ 与 oneAPI
   同版本 ⇒ ABI 兼容）。运行库链：Intel MPI → SLURM PMI（srun 必需）
   → HDF5 → oneAPI runtime → GCC runtime（★ `gcc/9.3.0-new/lib64`）。
9. **cp 循环的 bash glob 陷阱** ⇒ `for f in Config Makefile *.F90 ...`
   里 glob **只展开一次且用当前 cwd**（不是脚本目录）⇒ `*.F90/*.cn4/
   *.par` 展开为空 ⇒ 源文件一个没拷 ⇒ setup 半途 ⇒ 作业挂起 7~17 分钟。
   改用 `find ... -exec cp -f {} ...`（并在循环后 echo 拷贝数量自检）。

### 两条环境铁律

- ★★ **setup 与 make 都必须在登录节点**：计算节点上 setup 永久挂起
  （实测 RUNNING 17 分钟、objdir 零文件）；`setup_depends.py`（os.walk
  扫 1500+ 源文件）在计算节点 11 分钟不出 `.o`，在登录节点秒级完成
  （Makefile.Depend 352 KB）。⇒ `deploy/hpc_deploy/submit_sandwich.py`：
  登录节点「拷源文件 → setup → make -j7」再 sbatch（作业只负责运行）。
- ★★ **产物必须落并行盘**（`$SLURM_SUBMIT_DIR`）：`/tmp` 是节点本地盘，
  跨节点不可见 ⇒ 登录节点收集到 0 个 chk（实测）。

### 架构与代码质量

- ★ 装置参数唯一事实源 = `flash/flash_run/env/devices.py`（护栏 R-SCENE-05
  要求场景层不得硬编码分区/模块/站点路径）。场景模板用 `@DEV_EXPORTS@` /
  `@RUNTIME_LIBS@` 等占位符，由生成器渲染；`render_template()` 校验
  **多行**占位符必须独占一行（曾致作业 4924488 语法错）。
- ★ 干跑用例不应依赖平台：`run_flash=False` / `dry_run=True` 不执行 FLASH
  ⇒ 远程目标校验只对 `run_flash=True and not dry_run` 生效
  （原：超算 2 failed；单跑侥幸通过 —— 因 sinfo 探测超时回落 local）。
- 新增工具：`deploy/hpc_deploy/refresh_body_wheel.py`（只换本体 wheel +
  重写 MANIFEST，依赖闭包复用）、`migrate_wheelhouse.py`（U 盘式迁移：
  tar → SFTP → 双端 SHA256 → 展开 → 离线装）、`submit_sandwich.py`。



## §W/§X 补充（2026-10-24）— 全文

### §W ch_center 五执行模式测试

## ★★★ §W ch_center 五执行模式测试（2026-10-24，commit ecf1cd9）

框架 `scenarios/public/center_evolution/ch_center/modes_test/`（**坑全在 README**）。
五模式同算例（tmax=1.188 ns）全绿：**win-wsl 与 wsl-wsl 逐位一致**；三个超算
路径彼此一致、与 WSL 参考最大偏差 5.4e-3（Intel/gcc 浮点差，集中在激波段）。

- ★★ **wsl.exe 只在顶层 `;` 处拆命令串**（`false; echo $?`→0、`X=5; echo $X`→空）；
  ★ 2026-10-24 复测：**`&&`/`||` 链本身正常**（`false && echo B || echo C` → C
  正确）——别过度禁用。⇒ 复合命令/env 前缀/行内哨兵不可信；逻辑收进脚本文件
  （`run_flash_wsl.sh`，**必须 LF**——CRLF 让 bash 解析崩），wsl 侧只发单条命令。
  旧 `; echo FLASH_EXIT_CODE=$?` 哨兵恒 0 ⇒ FLASH exit 134 崩了也报成功。
- **WSL 跑 FLASH 的 cwd 必须落原生 ext4**：HDF5 MPI-IO 写 /mnt/e（drvfs）间歇
  `No data available` → SIGABRT 134 ⇒ FLASH_RUN_WORKDIR 用 /root/...。
- 超算**已预置二进制走 module 路径**（libhdf5.so.10 只在 hdf5 模块）；Intel MPI：
  `MPII_F_TRUE` 靠 `mpi/latest/lib/release/` 的 libmpi.so.12 提供（少一层即崩）。
- paramiko SFTP：`~` **不展开**、**尾斜杠**致 `sftp.put` OSError Failure ⇒
  remote_dir 先 `printf $HOME` 转绝对路径。
- insitu 收集：`select_fetch_files(basenm="")` 滤掉**全部** chk ⇒ basenm 从 .par
  解析；`ls outputfiles_* | head -1` 取**最旧**目录 ⇒ `sort | tail -1`。

### §X 公开场景统一 auto + 极短验证

## ★★★ §X 公开场景统一 auto + 极短验证（2026-10-24，commit 32f96ca）

三公开场景（ch_center / grad_dens_sandwich / thin_layer_sandwich_si）统一走
`python -m flash.scenarios.cli run <场景>`，缺省 `--mode auto`；一键极短验证
`python flash/scenarios/public/short_validation.py`（tmax=1e-13 s，实测
21.4 / 5.1 / 3.1 s 全绿）。

- **catalog 收录**：sandwich 两场景原先只在 registry（无法用 CLI 跑）⇒ 新增
  `runner_kind="engine"`；`PUBLIC_SCENE_POLICY` 限定 local/wsl（引擎不承接
  超算 ⇒ 超算上**明确报错**不静默降级）；ch_center 走 `runner_kind="main"`。
- ★★ **"tmax 覆盖"最易被静默忽略的三处**（全靠实跑暴露）：
  ① 场景脚本：par 只在**文件缺失**时重建 ⇒ 输入已就绪时 `--tmax` 无效
  （现核对 par 的 tmax，不一致则强制重建）；② `thin_layer` build_par 恒用
  "激光末时刻+0.1ns"，忽略 `params["tmax"]`；③ 引擎侧 `build_grid` 的
  `t_max` 若不取 `params["tmax"]`，输出网格与 par 不同源。
- ★★ **短跑 dt/网格联动**（统一实现在 `scenarios/public/time_control.py`）：
  `dtmax ≤ tmax×1.05`、`dtinit ≤ tmax×0.1`、`dtmin ≤ dtinit`；输出时间
  步长 `min(step, tmax/20)`（否则 t_grid 只剩 1 点 ⇒ 插值 "division by zero"）。
- ★★ **未设 `FLASH_RUN_WORKDIR`/`FLASH_COLLECT_DIR` 时必须给默认**：
  回落到 objdir ⇒ Step 6 的 `cp *chk*` 把上一轮长跑的数百个 chk 一并收集
  （实测短跑 3 chk 却报"找到 342 个"）⇒ 默认给每轮独立的 **WSL ext4**
  工作目录 + 收集目录，且**收集前清空**旧产物。
- ★ **1D 场景 `nproc ≤ nblockx`**：资源探测给台式机十几核，而 1D 的
  nblockx 只有 4~8 ⇒ FLASH "not enough blocks" abort。
- ★ **chk 文件名无 `.h5` 后缀**（`lasslab_hdf5_chk_0002`）⇒ `ls *.h5`
  恒漏、计数恒 0（与"没产出文件"看起来一样）；引擎改按 `basenm` 收集。
- ★ **绘图"报喜不报忧"**：引擎只建目录就算完却打印"✅ (0 张)" ⇒ 现补画
  1×3 诊断图（全英文 + Times New Roman；温度按 chk 的 **K → eV** 换算）。



## §Z 目录规划与作业内全流程（2026-10-26，commit 0955312）— 全文

### 推翻的旧结论

上一轮（commit 1198b9f）写进 MEMORY 与 README 的两条「铁律」经用户质疑后复核实测，**全部证伪**：

1. 「setup 与 make 必须在登录节点（计算节点会永久挂起）」
2. 「产物必须落并行盘（/tmp 跨节点不可见）」

计算节点实测对照（NC-E，作业 4924747/4924748/4924752/4924760）：

| 观测项 | 实测 | 说明 |
|---|---|---|
| `/tmp` 挂载 | tmpfs（rootfs 94 G，节点本地内存盘） | 可写 |
| `df -T` 类型 | tmpfs | 不是共享盘 |
| GPFS 写 64 MB | 3.1 GB/s | 不慢 |
| GPFS os.walk 2811 文件 | **0.2 s** | 元数据不慢 |
| GPFS 建 500 符号链接 | **1.08 s** | 不慢 |
| `setup_depends.py` | **21.7 s** | 不是「11 分钟不出 .o」 |
| 计算节点 `setup`（GPFS objdir） | **SUCCESS** | 不是「永久挂起」 |
| 计算节点 `setup`（scratch objdir） | **SUCCESS，2 s** | — |
| 计算节点 scratch `make -j16` | **31 s**（1550 .o / 13 MB 二进制） | 完全可行 |
| scratch 上 FLASH 运行 | 299 s（623 chk） | — |
| 归档回共享盘 | **0 s** | — |

⇒ **真正的规律**：编译/运行的**中间产物放在哪**决定快慢；
  objdir 在共享并行盘 ⇒ make 漫长；objdir 在节点本地 tmpfs ⇒ 31 s。
  「不能在计算节点编译」不成立。

### 旧结论的真实来源（终于定位）

FLASH `setup` 在 objdir 里遇到**实体 .F90**（非符号链接）时会
`input()` 提问（`bin/linkFiles.py: checkSource`）：

    **********WARNING**********
    Simulation_initBlock.F90 is not a symlink and will be deleted by setup.
     Continue? [Y/n]

批处理里 stdin 为空 ⇒ `EOFError: EOF when reading a line` ⇒ setup 中止。
（实测作业 4924789 完整 traceback。）
★ 这与「登录节点 vs 计算节点」无关 —— 只是此前脚本恰好在 objdir 里
  留了实体 .F90。

### 新架构：目录拓扑抽象

`flash/flash_run/remote/job_layout.py`：

    JobLayout(scratch_root, shared_root, build_dir, run_dir,
              output_dir, log_dir, scratch_prefix)
    ResourceSpec(nodes, ntasks, cpus_per_task, time_limit,
                 mem_per_node, account, partition, qos, constraint)

职责分离：

- **scratch**（节点本地 tmpfs）= 编译 objdir + 运行工作目录 ⇒ 快，用完即弃
- **shared**（共享并行盘）= 输入源 + 最终产物 + 作业日志 ⇒ 持久、跨节点可见

`flash/flash_run/remote/job_scripts.py`：

    render_job_body(layout, build=BuildSpec(...), run=RunSpec(...),
                   input_dir=..., archive_patterns=("*chk*",))
    → stage → build → run → archive 四阶段作业体

`flash.flash_run.remote.slurm_control.SlurmJobSpec` 扩展字段：
cpus_per_task / time_limit / mem_per_node / account / qos / constraint /
chdir / out_dir ⇒ **资源与目录成为提交时的显式契约**。

★ 关键实现细节：
- scratch 探测判据 = **文件系统类型**（tmpfs/ramfs），不靠路径
  （路径因集群而异）；`FL_SCRATCH_LOCAL` 标记是否命中
- 探测**之后**才导出 BUILD/RUN 路径（否则路径指向错误的盘）
- `scratch_prefix` 含 `${SLURM_JOB_ID}` ⇒ 并发作业互不干扰
- make 并行度 = **ntasks × cpus_per_task**（不是 `nproc`：作业内 nproc
  返回节点全部核数 48 ⇒ 线程失控；也不是只算 cpus_per_task：会漏掉多 rank）
- setup **非交互**：`printf 'Y\n' | ./setup ...` + `-parfile=<name>`
- stage 只搬**运行期数据**（.cn4/.par）到 run 目录，**不搬 .F90**

### 本轮实测挖出的 3 个新 bug

1. setup 交互式提问 ⇒ EOFError（作业 4924789）
2. `find` 多 pattern 缺 `-o` ⇒ 静默拷 0 个 ⇒ "IONMIX4 file not found"
   （作业 4924811）
3. 归档 glob 被引号包住 ⇒ shell 不展开 ⇒ 循环体拿到字面量 ⇒ 仿真完成
   但归档目录为空（作业 4924826）

### 资源利用的实质改善

旧：登录节点预编译（**占用交互资源**）+ 作业只运行 4 rank ⇒ 计算资源浪费。
新：**编译与运行都在计算节点的本地 scratch**，登录节点只做提交/轮询。
单作业总时长 6:19（含编译），其中编译 ~31 s（make -j4）。


## §Y 执行层去场景化 + 统一提交入口（2026-10-26, commit 5f089e3）— 全文

### 起因（用户指出）
> "submit_sandwich.py ？？？ flash.flash_run 中专注服务运行，不要有子场景的相关信息"

三条具体病灶：
1. `deploy/hpc_deploy/submit_sandwich.py` 内含 `SCENES` 映射表
   （场景→sim_input 目录 / FLASH 单元 / par 名）+ `SETUP_EXTRA` +
   `GEN_SCRIPT` ⇒ **提交器里长出了子场景知识**。
2. `flash.flash_run/execution.py` 里 `SNB_POLICY`；
   `flash/flash_run/env/resource_config.py` 里 `SCENE_DEVICE_DEFAULTS`
   （键 = SNBOneCH / SNBVTi）⇒ **执行层里出现子场景信息**。
3. 两个 sandwich 场景的 `submit_flash.sh`（`sim_input_src.py` 内嵌模板）
   **内联整份 sbatch 作业体** ⇒ 与统一入口**两份实现**，已实际漂移：
   模板写"编译放登录节点"，统一入口写"编译放计算节点 scratch"。

### 拆分结果
| 内容 | 归属模块 | 说明 |
|---|---|---|
| 通用提交服务 | `flash.flash_run.remote.job_submit` | `JobRequest` / `render_job()` / `submit_job()`；**不认识任何场景** |
| 装置参数 | `flash.flash_run.env.devices` | 分区 / 模块 / 库路径 / `device_default()` / `credential_name()` |
| 场景族执行策略 | `flash.scenarios.policies` | `SNB_POLICY` / `PUBLIC_SCENE_POLICY` |
| 场景专属核数默认值 | `flash.scenarios.device_defaults` | `get_scene_nprocs()`（SNBOneCH→131 / SNBVTi→125） |
| 场景超算提交声明 | `flash.scenarios.hpc_job` | `SceneHpcJob`（输入目录 / 单元名 / setup 参数 / 默认 ntasks） |
| 统一提交 CLI | `flash.scenarios.submit_cli` + `cli submit` 子命令 | 场景声明 → 通用请求 → 提交 |

- **删除** `deploy/hpc_deploy/submit_sandwich.py`。
- `flash.flash_run/execution.py` 不再导出 `SNB_POLICY`；
  `resource_config.py` 不再有 `SCENE_DEVICE_DEFAULTS` / `get_scene_device_default`。
- 两个场景的 `submit_flash.sh` 改为**薄委托**（保留为"直接 sbatch 已生成
  输入"的兜底路径），作业体只有一份。
- 场景诊断探针 `flash/flash_run/remote/test/scripts/` → `scripts/02_hpc/probes/`
  （它们 `import flash.scenarios` ⇒ 属场景侧；`scripts/` 不入 wheel）。
- 超算文档 → `deploy/hpc_deploy/`。

### 新护栏 R-LAYER-03
```
Rule("R-LAYER-03", "flash_run",
     r"\b(SNBOneCH|SNBVTi|SNB_POLICY|ch_center|chcenter"
     r"|thin_layer_sandwich|grad_dens_sandwich|laserslab1d_local_custom)\w*", ...)
```
执行层出现场景名即 CI 失败（负向样本 + 正向样本各一）。

### ★★ 超算实测踩坑 1：SLURM 计费账户 ≠ SSH 凭据名
```
#SBATCH --account=flash_ssh
⇒ sbatch: error: Batch job submission failed:
   Invalid account or account/partition combination specified
```
- 凭据名 `flash_ssh` → 只用于**选 SSH 路由**。
- 计费账户 → 取 `sacct -X --format=Account` = **`nc-e`**。
- 修法：`devices.DEVICE_DEFAULTS["account"] = "nc-e"`；
  新增 `devices.credential_name()`（仅选路由，`FLASH_CREDENTIAL` 可覆盖）；
  `submit_cli` 三处硬编码 `"flash_ssh"` 改用 `credential_name()`。
- 新增测试 `test_slurm_account_is_not_credential_name` 防再次混淆。

### ★★ 超算实测踩坑 2：返回字典键集不固定 ⇒ 成功被误判为失败
`submit_job` 成功路径返回 `{ok, job_id, script_path, log_dir, output_dir, reason}`
（**缺 `job_name`**）⇒ CLI 打印日志路径时 `KeyError: 'job_name'`
⇒ 进程非零退出 ⇒ 提交**其实已成功**却报失败（作业 4925015 已 COMPLETED）。
修法：成功/失败/dry-run 三条路径统一返回
`{ok, job_id, job_name, script_path, log_dir, output_dir, reason}`；
测试断言键集固定。

### 端到端实测（新统一入口，超算 NC-E）
| 场景 | 作业 | 状态 | 耗时 | 产物 |
|---|---|---|---|---|
| grad_dens_sandwich | 4925015 | COMPLETED | 6:17 | 623 chk |
| thin_layer_sandwich_si | 4925026 | COMPLETED | 5:48 | 34 chk |

关键日志行：`[layout] scratch base=/tmp local=1 fstype=tmpfs`
⇒ 编译/运行都在节点本地 scratch；产物归档回 shared。

### 其它修复
- grad_dens 模板 par 名修正：`grid_rede.par`（非 `${SIM_NAME}_${RUN_ID}.par`）。
- 模板注释里的旧结论（"编译放登录节点"）改为"计算节点实测证伪"表述。
- 本地 270 passed / 2 skipped；护栏全绿；wheel 6.0 MB；
  `wheel_leak_audit` 四项在容差内；Gitee + 超算同步至 5f089e3。
