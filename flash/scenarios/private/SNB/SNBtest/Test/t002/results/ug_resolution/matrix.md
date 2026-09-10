# +ug 均匀网格分辨率机制 —— 实测矩阵

生成时间: 2026-09-10 22:24:57    运行环境: WSL Ubuntu-22.04, 24 核 / 11 GB
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

## 实测结果

| 用例 | 模式 | nxb | iProcs | iGridSize | 预期格数 | 实测格数 | dx 预期 [µm] | dx 实测 [µm] | 墙钟 |
|---|---|---|---|---|---|---|---|---|---|
| A4 | 非固定块 | - | 8 | 1024 | 1024 | 1024 | 0.4883 | 0.4883 | 50.30 s |
| A5 | 非固定块 | - | 16 | 1024 | 1024 | 1024 | 0.4883 | 0.4883 | 44.86 s |

## 结论

- **A4** (非固定块 (-nofbs) iGridSize=1024, 8 核): 非固定块 iGridSize=1024 × iProcs=8 → 实测 1024 格, dx≈0.4883 µm, 墙钟 50.30 s
- **A5** (非固定块 (-nofbs) iGridSize=1024, 16 核 (复用 A4 二进制)): 非固定块 iGridSize=1024 × iProcs=16 → 实测 1024 格, dx≈0.4883 µm, 墙钟 44.86 s

### 判读

2. **非固定块模式 `iGridSize=1024`**：8 核 → 1024 格, 16 核 → 1024 格 (分辨率不变) → 总格数由 iGridSize 直接给定，与核数完全解耦。
3. 因此旧结论「SNB 分辨率只能靠 iProcs 提升 / 不存在固定分辨率扫核数」**只在固定块模式且不动 `-nxb` 时成立**；加大 `-nxb` 或在非固定块模式下给 `iGridSize`，都可在核数不变时提高（或锁定）分辨率。

> 注意: UG 是「一块一进程」，因此 `nproc` 必须严格等于 `iProcs`；这与「分辨率是否可自由设定」是两个独立约束。

