# +ug 均匀网格分辨率机制 —— 实测矩阵

生成时间: 2026-09-10 22:46:23    运行环境: WSL Ubuntu-22.04, 24 核 / 11 GB
场景: t002 FL-SH 腿      tmax = 2.0e-10 s

## 源码机制 (Grid/GridMain/UG/Grid_init.F90:186-194)

```fortran
#ifdef FIXEDBLOCKSIZE        ! setup 给了 -nxb=N
   gr_gIndexSize(IAXIS) = gr_axisNumProcs(IAXIS) * NXB
#else                        ! 不给 -nxb
   RuntimeParameters_get("iGridSize", gr_gIndexSize(IAXIS))
#endif
```

UG/Config 明文: `D nblockx number of blocks along X - ignored by UG Grid`;
`D iGridSize ... ONLY needed when running in NON_FIXED_BLOCKSIZE mode`。

### ★ 关键前提: 非固定块模式必须显式 `-nofbs`

首次尝试只"去掉 `-nxb`" 并在 par 里写 `iGridSize=1024`，实测**无效**：
`iProcs=8 → 64 格`、`iProcs=16 → 128 格`（即 `iProcs×8`，NXB 取了默认值 8），
说明 FLASH 默认仍定义 `FIXEDBLOCKSIZE`，`iGridSize` 被完全忽略。
正确开关是 `-nofbs`（`bin/parseCmd.py:282` → `fixedBlockSize=False`；
`bin/Readme.SetupVars:97`；快捷方式 `nofbs:-nofbs:+ug:parallelIO=True:`）。
注意副作用：`not fixedBlockSize` 会让 `IO/IOMain/hdf5/Config` 强制
`DEFAULT parallel`，且 `parallelIO=False` 直接 SETUPERROR —— 即 `-nofbs`
与串行 HDF5 不兼容。

## 实测结果

| 用例 | 模式 | nxb | iProcs | iGridSize | 预期格数 | 实测格数 | dx 预期 [µm] | dx 实测 [µm] | 墙钟 |
|---|---|---|---|---|---|---|---|---|---|
| A1 | 固定块 | 64 | 8 | - | 512 | 512 | 0.9766 | 0.9766 | 12.47 s |
| A2 | 固定块 | 128 | 8 | - | 1024 | 1024 | 0.4883 | 0.4883 | 54.05 s |
| A3 | 固定块 | 128 | 16 | - | 2048 | 2048 | 0.2441 | 0.2441 | 164.46 s |
| A4 | 非固定块 | - | 8 | 1024 | 1024 | 1024 | 0.4883 | 0.4883 | 56.14 s |
| A5 | 非固定块 | - | 16 | 1024 | 1024 | 1024 | 0.4883 | 0.4883 | 46.56 s |

## 结论

- **A1** (固定块基线 (与生产配置相同)): 固定块 nxb=64 × iProcs=8 → 实测 512 格, dx≈0.9766 µm, 墙钟 12.47 s
- **A2** (同 8 核, nxb×2 → 分辨率×2 (关键对照)): 固定块 nxb=128 × iProcs=8 → 实测 1024 格, dx≈0.4883 µm, 墙钟 54.05 s
- **A3** (同 nxb, iprocs×2 (复用 A2 二进制)): 固定块 nxb=128 × iProcs=16 → 实测 2048 格, dx≈0.2441 µm, 墙钟 164.46 s
- **A4** (非固定块 (-nofbs) iGridSize=1024, 8 核): 非固定块 iGridSize=1024 × iProcs=8 → 实测 1024 格, dx≈0.4883 µm, 墙钟 56.14 s
- **A5** (非固定块 (-nofbs) iGridSize=1024, 16 核 (复用 A4 二进制)): 非固定块 iGridSize=1024 × iProcs=16 → 实测 1024 格, dx≈0.4883 µm, 墙钟 46.56 s

### 判读

1. **核数不变、只把 `-nxb` 从 64 提到 128**：格数 512 → 1024 (×2.00), dx 0.9766 → 0.4883 µm → 分辨率**与核数无关**，`-nxb` 是独立旋钮。
2. **非固定块模式 `iGridSize=1024`**：8 核 → 1024 格, 16 核 → 1024 格 (分辨率不变) → 总格数由 iGridSize 直接给定，与核数完全解耦。
3. 因此旧结论「SNB 分辨率只能靠 iProcs 提升 / 不存在固定分辨率扫核数」**只在固定块模式且不动 `-nxb` 时成立**：固定块模式下 `-nxb` 本身就是独立分辨率旋钮；改用 `-nofbs` 并给 `iGridSize` 后，分辨率与核数完全解耦。

> 注意 1: UG 是「一块一进程」，因此 `nproc` 必须严格等于 `iProcs`；这与「分辨率是否可自由设定」是两个独立约束。
> 注意 2: `-nofbs` 会强制并行 HDF5 IO，与 `+serialIO`/`parallelIO=False` 冲突（setup 直接报错）。

