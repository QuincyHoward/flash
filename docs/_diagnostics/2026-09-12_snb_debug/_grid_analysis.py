"""网格精度分析: +ug 下 dx 约束与平台核数可行域。

约束:
  dx = (xmax - xmin) / (iProcs * nxb)
  iProcs * nxb >= L_total / dx_target
  mpiexec -n == iProcs  (+ug 铁律)
平台核数上限: WSL 24, NC-E 192, BSCC 384
"""

L_TOTAL_UM = 500.0   # (xmax - xmin) = 0.01 - (-0.04) cm = 500 um

print("=" * 78)
print(" +ug 网格精度约束分析 (薄层 0.1um -> dx <= 0.03um)")
print("=" * 78)
print(f"\n  域宽 L = {L_TOTAL_UM:.0f} um")
print(f"  需要 iProcs * nxb >= {L_TOTAL_UM/0.03:,.0f}  (dx<=0.03um)")
print(f"  需要 iProcs * nxb >= {L_TOTAL_UM/0.02:,.0f}  (dx<=0.02um)")
print(f"  需要 iProcs * nxb >= {L_TOTAL_UM/0.01:,.0f}  (dx<=0.01um)")

PLATFORMS = {"WSL": 24, "NC-E": 192, "BSCC-T6": 384}

print("\n" + "-" * 78)
print(" 方案表: 给定 nxb, 求满足 dx<=0.03um 所需最小 iProcs, 与各平台可行性")
print("-" * 78)
print(f"  {'nxb':>6} {'iProcs_min':>11} {'dx(um)':>9} {'总格数':>10}  "
      f"{'WSL(24)':>9} {'NC-E(192)':>10} {'BSCC(384)':>10}")
for nxb in (16, 32, 64, 128, 256):
    import math
    ip_min = math.ceil(L_TOTAL_UM / 0.03 / nxb)
    dx = L_TOTAL_UM / (ip_min * nxb)
    cells = ip_min * nxb
    row = []
    for pname, pcap in PLATFORMS.items():
        row.append("OK" if ip_min <= pcap else f"X({ip_min})")
    print(f"  {nxb:>6} {ip_min:>11} {dx:>9.5f} {cells:>10}  "
          f"{row[0]:>9} {row[1]:>10} {row[2]:>10}")

print("\n" + "-" * 78)
print(" 当前默认配置")
print("-" * 78)
NXB, IPROCS = 128, 131
dx = L_TOTAL_UM / (NXB * IPROCS)
print(f"  nxb={NXB}, iProcs={IPROCS} -> dx = {L_TOTAL_UM}/({NXB}*{IPROCS}) = {dx:.5f} um")
print(f"  薄层 0.1um 对应格点数: {0.1/dx:.2f} 格")
print(f"  满足 dx<=0.03um: {'YES' if dx<=0.03 else 'NO'}")
print(f"  WSL(24核) 可跑: {'YES' if IPROCS<=24 else 'NO'}  (需 {IPROCS} 核)")

print("\n" + "-" * 78)
print(" WSL 本地测试可行方案 (24 核上限)")
print("-" * 78)
print("  +ug 铁律: mpiexec -n == iProcs, 无法解耦核数与分辨率。")
print("  WSL 上 iProcs<=24 -> 即使 nxb=256, dx = 500/(24*256) = %.4f um > 0.03"
      % (L_TOTAL_UM / (24 * 256)))
print("  => WSL 无法在 dx<=0.03um 下做 +ug 测试 (物理上不可能, 核数不足)。")
print("  => 0.03um 精度的冒烟测试只能上超算 (NC-E 192 核可容纳 iProcs=131)。")
