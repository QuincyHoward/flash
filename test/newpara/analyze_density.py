"""
FLASH NewPara — 密度网格分析脚本
═══════════════════════════════════
读取 plt_cnt_0000 (初始密度) 和 plt_cnt_0308 (最终密度)，
绘制密度分布图验证三区结构。

预期初始密度:
  [0, 0.014) cm  → cham: rho ≈ 1e-6
  [0.014, 0.016) → targ: rho ≈ 2.7
  [0.016, 0.018] → poly: rho ≈ 1.0
"""

import sys
from pathlib import Path

# Bootstrap: find flash project root
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "__init__.py").exists() and (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    raise RuntimeError("Cannot locate flash package root")
_PARENT = _ROOT.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

# 路径设置
TEST_DIR = Path(__file__).parent
OUTPUT_DIR = TEST_DIR / "output"
PLOTS_DIR = OUTPUT_DIR / "plots"

PLOTS_DIR.mkdir(parents=True, exist_ok=True)

# 找 HDF5 文件
plt_initial = sorted(OUTPUT_DIR.glob("lasslab_hdf5_plt_cnt_0000*"))
plt_final = sorted(OUTPUT_DIR.glob("lasslab_hdf5_plt_cnt_0308*"))
chk_initial = sorted(OUTPUT_DIR.glob("lasslab_hdf5_chk_0000*"))

print("=" * 65)
print(" FLASH NewPara — 密度网格分析")
print("=" * 65)

try:
    from flash.output_processors.loader import FlashDataLoader
    from flash.output_processors.plotter import FlashPlotter
    from flash.output_processors.calculator import FlashCalculator

    # ── 1. 初始密度分布 (plt_cnt_0000) ──
    if plt_initial:
        print(f"\n[1/2] 分析初始密度: {plt_initial[0].name}")
        container0 = FlashDataLoader(str(plt_initial[0])).load()
        calc0 = FlashCalculator(container0)

        dens0 = container0.get_data("dens")
        print(f"  密度范围: [{dens0.min():.4e}, {dens0.max():.4f}] g/cm³")
        print(f"  密度均值: {dens0.mean():.4f}")

        # 绘制初始密度分布
        p0 = str(PLOTS_DIR / "dens_initial_profile.png")
        FlashPlotter(container0).plot(
            "dens", save_path=p0,
            title="Initial Density – NewPara Multi-Zone (t=0)",
        )
        print(f"  ✓ 初始密度图: {p0}")

        # 如果 species 在数据集中
        data_names = container0.get_data_names()
        print(f"  数据变量: {data_names[:15]}...")
        for sp in ["cham", "targ", "poly"]:
            if sp in data_names:
                sp_data = container0.get_data(sp)
                print(f"  {sp}: max={sp_data.max():.2e}")

    # ── 2. 最终密度分布 (plt_cnt_0308) ──
    if plt_final:
        print(f"\n[2/2] 分析最终密度: {plt_final[0].name}")
        container1 = FlashDataLoader(str(plt_final[0])).load()

        dens1 = container1.get_data("dens")
        print(f"  密度范围: [{dens1.min():.4e}, {dens1.max():.4f}] g/cm³")

        p1 = str(PLOTS_DIR / "dens_final_profile.png")
        FlashPlotter(container1).plot(
            "dens", save_path=p1,
            title="Final Density – NewPara Multi-Zone (t=2ns)",
        )
        print(f"  ✓ 最终密度图: {p1}")

        # 检查 species mass fraction
        data_names1 = container1.get_data_names()
        for sp in ["cham", "targ", "poly"]:
            if sp in data_names1:
                sp_data = container1.get_data(sp)
                print(f"  {sp}: min={sp_data.min():.2e}, max={sp_data.max():.2e}")

    print("\n✅ 分析完成!")
    print(f"  图像目录: {PLOTS_DIR}")

except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("   需要 output_processors 包")
except Exception as e:
    print(f"❌ 分析失败: {e}")
    import traceback
    traceback.print_exc()
