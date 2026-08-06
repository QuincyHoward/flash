"""
测试 flash_hdf5.py 的 3D 数据提取功能
逐点对比 flash_hdf5.py 与 yt 的处理结果
"""

import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path

# 添加项目根目录到路径

# Bootstrap: find flash project root by searching upward for marker
_ROOT = Path(__file__).resolve().parent
for _ in range(12):
    if (_ROOT / "pyproject.toml").exists():
        break
    _ROOT = _ROOT.parent
else:
    _ROOT = None  # 已安装环境 (site-packages): 静默跳过
_PARENT = _ROOT
if _PARENT is not None and str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))


# 尝试导入 yt（用于基准数据生成）
try:
    import yt
    HAS_YT = True
except ImportError:
    HAS_YT = False
    print("⚠️ yt 未安装，将使用预处理数据")

# 导入 flash_hdf5
from flash.output_processors.hdf5processor.flash_hdf5 import FlashHDF5File


def extract_with_yt_3d(hdf5_file, var_name='dens'):
    """使用 yt 提取 3D 数据"""
    if not HAS_YT:
        raise ImportError("yt 未安装，无法提取基准数据")

    ds = yt.load(hdf5_file)

    # 获取所有数据
    ad = ds.all_data()

    # 提取坐标和变量（FLASH 3D 使用笛卡尔坐标）
    x_coords = ad[('flash', 'x')].to_value()
    y_coords = ad[('flash', 'y')].to_value()
    z_coords = ad[('flash', 'z')].to_value()
    var_data = ad[('flash', var_name)].to_value()

    # 去除重复的坐标点（AMR 覆盖关系已由 yt 处理）
    df = pd.DataFrame({
        'x': x_coords,
        'y': y_coords,
        'z': z_coords,
        var_name: var_data
    })

    # 排序并去重（保留第一个出现的）
    df = df.sort_values(['x', 'y', 'z']).drop_duplicates(subset=['x', 'y', 'z'], keep='first')

    return df['x'].values, df['y'].values, df['z'].values, df[var_name].values


def extract_with_flash_hdf5_3d(hdf5_file, var_name='dens'):
    """使用 flash_hdf5.py 提取 3D 数据（yt 风格）"""
    with FlashHDF5File(hdf5_file) as f:
        result = f.extract_var_yt_style(var_name, use_cell_centers=True)
        if f.ndim == 3:
            x, y, z, dens = result
            return x, y, z, dens
        else:
            raise ValueError(f"期望 3D 文件，但得到 {f.ndim}D")


def save_yt_baseline_3d(hdf5_file, output_dir):
    """使用 yt 提取数据并保存为基准"""
    if not HAS_YT:
        print("❌ yt 未安装，无法生成基准数据")
        return None

    print(f"\n📊 使用 yt 提取基准数据...")
    print(f"   文件: {hdf5_file}")

    x_yt, y_yt, z_yt, dens_yt = extract_with_yt_3d(hdf5_file, 'dens')

    # 保存到 CSV
    basename = os.path.splitext(os.path.basename(hdf5_file))[0]
    output_file = os.path.join(output_dir, f"{basename}_yt_baseline.csv")

    df = pd.DataFrame({
        'x': x_yt,
        'y': y_yt,
        'z': z_yt,
        'dens': dens_yt
    })
    df.to_csv(output_file, index=False)

    print(f"✅ 基准数据已保存: {output_file}")
    print(f"   数据点数量: {len(dens_yt):,}")
    print(f"   x 范围: [{x_yt.min():.6e}, {x_yt.max():.6e}]")
    print(f"   y 范围: [{y_yt.min():.6e}, {y_yt.max():.6e}]")
    print(f"   z 范围: [{z_yt.min():.6e}, {z_yt.max():.6e}]")
    print(f"   dens 范围: [{dens_yt.min():.6e}, {dens_yt.max():.6e}]")

    return output_file


def compare_point_by_point_3d(hdf5_file, yt_baseline_file=None):
    """逐点对比 flash_hdf5.py 与 yt 的结果"""

    print(f"\n{'='*60}")
    print(f"逐点对比测试（3D）")
    print(f"{'='*60}")
    print(f"文件: {hdf5_file}")

    # 1. 使用 flash_hdf5.py 提取数据
    print(f"\n1️⃣ 使用 flash_hdf5.py 提取数据...")
    x_hdf5, y_hdf5, z_hdf5, dens_hdf5 = extract_with_flash_hdf5_3d(hdf5_file, 'dens')

    print(f"   数据点数量: {len(dens_hdf5):,}")
    print(f"   x 范围: [{x_hdf5.min():.6e}, {x_hdf5.max():.6e}]")
    print(f"   y 范围: [{y_hdf5.min():.6e}, {y_hdf5.max():.6e}]")
    print(f"   z 范围: [{z_hdf5.min():.6e}, {z_hdf5.max():.6e}]")
    print(f"   dens 范围: [{dens_hdf5.min():.6e}, {dens_hdf5.max():.6e}]")

    # 2. 获取 yt 基准数据
    if yt_baseline_file and os.path.exists(yt_baseline_file):
        print(f"\n2️⃣ 读取 yt 基准数据: {yt_baseline_file}")
        df_yt = pd.read_csv(yt_baseline_file)
        x_yt = df_yt['x'].values
        y_yt = df_yt['y'].values
        z_yt = df_yt['z'].values
        dens_yt = df_yt['dens'].values
    elif HAS_YT:
        print(f"\n2️⃣ 使用 yt 提取基准数据...")
        x_yt, y_yt, z_yt, dens_yt = extract_with_yt_3d(hdf5_file, 'dens')
    else:
        print(f"\n❌ 无法获取 yt 基准数据")
        print(f"   请提供 yt 基准数据文件，或安装 yt")
        return None

    print(f"   数据点数量: {len(dens_yt):,}")
    print(f"   x 范围: [{x_yt.min():.6e}, {x_yt.max():.6e}]")
    print(f"   y 范围: [{y_yt.min():.6e}, {y_yt.max():.6e}]")
    print(f"   z 范围: [{z_yt.min():.6e}, {z_yt.max():.6e}]")
    print(f"   dens 范围: [{dens_yt.min():.6e}, {dens_yt.max():.6e}]")

    # 3. 检查数据点数量是否一致
    print(f"\n3️⃣ 数据点数量检查...")
    if len(dens_hdf5) != len(dens_yt):
        print(f"   ❌ 数据点数量不一致!")
        print(f"      flash_hdf5: {len(dens_hdf5):,}")
        print(f"      yt:          {len(dens_yt):,}")
        print(f"   无法进行逐点对比")
        return None
    else:
        print(f"   ✅ 数据点数量一致: {len(dens_hdf5):,}")

    # 4. 排序（按 x, y, z 坐标）
    print(f"\n4️⃣ 排序数据（按 x, y, z 坐标）...")
    sort_idx_hdf5 = np.lexsort((z_hdf5, y_hdf5, x_hdf5))
    sort_idx_yt = np.lexsort((z_yt, y_yt, x_yt))

    x_hdf5_sorted = x_hdf5[sort_idx_hdf5]
    y_hdf5_sorted = y_hdf5[sort_idx_hdf5]
    z_hdf5_sorted = z_hdf5[sort_idx_hdf5]
    dens_hdf5_sorted = dens_hdf5[sort_idx_hdf5]
    x_yt_sorted = x_yt[sort_idx_yt]
    y_yt_sorted = y_yt[sort_idx_yt]
    z_yt_sorted = z_yt[sort_idx_yt]
    dens_yt_sorted = dens_yt[sort_idx_yt]

    # 5. 逐点对比坐标
    print(f"\n5️⃣ 逐点对比坐标...")
    coord_diff_x = np.abs(x_hdf5_sorted - x_yt_sorted)
    coord_diff_y = np.abs(y_hdf5_sorted - y_yt_sorted)
    coord_diff_z = np.abs(z_hdf5_sorted - z_yt_sorted)
    max_coord_diff_x = coord_diff_x.max()
    max_coord_diff_y = coord_diff_y.max()
    max_coord_diff_z = coord_diff_z.max()
    mean_coord_diff_x = coord_diff_x.mean()
    mean_coord_diff_y = coord_diff_y.mean()
    mean_coord_diff_z = coord_diff_z.mean()
    coord_match = np.allclose(x_hdf5_sorted, x_yt_sorted, rtol=1e-8, atol=1e-10) and \
                  np.allclose(y_hdf5_sorted, y_yt_sorted, rtol=1e-8, atol=1e-10) and \
                  np.allclose(z_hdf5_sorted, z_yt_sorted, rtol=1e-8, atol=1e-10)

    print(f"   x 最大坐标差异: {max_coord_diff_x:.6e}")
    print(f"   x 平均坐标差异: {mean_coord_diff_x:.6e}")
    print(f"   y 最大坐标差异: {max_coord_diff_y:.6e}")
    print(f"   y 平均坐标差异: {mean_coord_diff_y:.6e}")
    print(f"   z 最大坐标差异: {max_coord_diff_z:.6e}")
    print(f"   z 平均坐标差异: {mean_coord_diff_z:.6e}")
    # 判断坐标一致性（分档）
    max_coord_diff = max(max_coord_diff_x, max_coord_diff_y, max_coord_diff_z)
    if coord_match:
        coord_status = "✅ 完全一致"
    elif max_coord_diff < 1e-8:
        coord_status = f"⚠️ 基本一致（差异 < 1e-8，机器精度范围内）"
    else:
        coord_status = "❌ 不一致"
    print(f"   坐标一致性: {coord_status}")

    if not coord_match:
        # 找出不一致的点
        coord_mismatch_mask = ~(np.isclose(x_hdf5_sorted, x_yt_sorted, rtol=1e-8, atol=1e-10) &
                              np.isclose(y_hdf5_sorted, y_yt_sorted, rtol=1e-8, atol=1e-10) &
                              np.isclose(z_hdf5_sorted, z_yt_sorted, rtol=1e-8, atol=1e-10))
        mismatch_indices = np.where(coord_mismatch_mask)[0]
        print(f"   不一致的点数: {len(mismatch_indices)}")
        if len(mismatch_indices) > 0:
            print(f"   前 10 个不一致的点:")
            for i in mismatch_indices[:10]:
                print(f"     索引 {i}: flash_hdf5=({x_hdf5_sorted[i]:.10e}, {y_hdf5_sorted[i]:.10e}, {z_hdf5_sorted[i]:.10e}), "
                      f"yt=({x_yt_sorted[i]:.10e}, {y_yt_sorted[i]:.10e}, {z_yt_sorted[i]:.10e}), "
                      f"差异=({coord_diff_x[i]:.6e}, {coord_diff_y[i]:.6e}, {coord_diff_z[i]:.6e})")

    # 6. 逐点对比密度值
    print(f"\n6️⃣ 逐点对比密度值...")
    dens_diff = dens_hdf5_sorted - dens_yt_sorted
    max_dens_diff = dens_diff.max()
    min_dens_diff = dens_diff.min()
    mean_abs_dens_diff = np.abs(dens_diff).mean()
    dens_match = np.allclose(dens_hdf5_sorted, dens_yt_sorted, rtol=1e-10, atol=1e-14)

    print(f"   最大正差异: {max_dens_diff:.6e}")
    print(f"   最大负差异: {min_dens_diff:.6e}")
    print(f"   平均绝对差异: {mean_abs_dens_diff:.6e}")
    print(f"   密度完全一致: {'✅ 是' if dens_match else '❌ 否'}")

    if not dens_match:
        # 找出不一致的点
        dens_mismatch_mask = ~np.isclose(dens_hdf5_sorted, dens_yt_sorted, rtol=1e-10, atol=1e-14)
        mismatch_indices = np.where(dens_mismatch_mask)[0]
        print(f"   不一致的点数: {len(mismatch_indices)}")
        if len(mismatch_indices) > 0:
            print(f"   前 10 个不一致的点:")
            for i in mismatch_indices[:10]:
                print(f"     索引 {i}: x={x_hdf5_sorted[i]:.10e}, y={y_hdf5_sorted[i]:.10e}, z={z_hdf5_sorted[i]:.10e}, "
                      f"flash_hdf5={dens_hdf5_sorted[i]:.10e}, yt={dens_yt_sorted[i]:.10e}, "
                      f"差异={dens_diff[i]:.6e}")

    # 7. 生成对比报告
    print(f"\n{'='*60}")
    print(f"对比报告（3D）")
    print(f"{'='*60}")
    print(f"文件: {os.path.basename(hdf5_file)}")
    print(f"\n数据点数量:")
    print(f"  flash_hdf5: {len(dens_hdf5):,}")
    print(f"  yt:          {len(dens_yt):,}")
    print(f"  一致: {'✅' if len(dens_hdf5) == len(dens_yt) else '❌'}")
    print(f"\n坐标一致性（逐点）:")
    print(f"  x 最大差异: {max_coord_diff_x:.6e}")
    print(f"  x 平均差异: {mean_coord_diff_x:.6e}")
    print(f"  y 最大差异: {max_coord_diff_y:.6e}")
    print(f"  y 平均差异: {mean_coord_diff_y:.6e}")
    print(f"  z 最大差异: {max_coord_diff_z:.6e}")
    print(f"  z 平均差异: {mean_coord_diff_z:.6e}")
    print(f"  完全一致: {'✅' if coord_match else '❌'}")
    print(f"\n密度值一致性（逐点）:")
    print(f"  最大正差异: {max_dens_diff:.6e}")
    print(f"  最大负差异: {min_dens_diff:.6e}")
    print(f"  平均绝对差异: {mean_abs_dens_diff:.6e}")
    print(f"  完全一致: {'✅' if dens_match else '❌'}")
    print(f"{'='*60}")

    # 8. 保存详细对比数据
    output_dir = os.path.dirname(os.path.abspath(__file__))
    basename = os.path.splitext(os.path.basename(hdf5_file))[0]
    comparison_file = os.path.join(output_dir, f"{basename}_point_by_point_comparison.csv")

    df_comparison = pd.DataFrame({
        'x_hdf5': x_hdf5_sorted,
        'y_hdf5': y_hdf5_sorted,
        'z_hdf5': z_hdf5_sorted,
        'x_yt': x_yt_sorted,
        'y_yt': y_yt_sorted,
        'z_yt': z_yt_sorted,
        'x_diff': x_hdf5_sorted - x_yt_sorted,
        'y_diff': y_hdf5_sorted - y_yt_sorted,
        'z_diff': z_hdf5_sorted - z_yt_sorted,
        'dens_hdf5': dens_hdf5_sorted,
        'dens_yt': dens_yt_sorted,
        'dens_diff': dens_diff
    })
    df_comparison.to_csv(comparison_file, index=False)

    print(f"\n✅ 详细对比数据已保存: {comparison_file}")

    return {
        'file': hdf5_file,
        'npoints_hdf5': len(dens_hdf5),
        'npoints_yt': len(dens_yt),
        'npoints_match': len(dens_hdf5) == len(dens_yt),
        'coord_max_diff_x': max_coord_diff_x,
        'coord_mean_diff_x': mean_coord_diff_x,
        'coord_max_diff_y': max_coord_diff_y,
        'coord_mean_diff_y': mean_coord_diff_y,
        'coord_max_diff_z': max_coord_diff_z,
        'coord_mean_diff_z': mean_coord_diff_z,
        'coord_match': coord_match,
        'dens_max_diff': max_dens_diff,
        'dens_min_diff': min_dens_diff,
        'dens_mean_abs_diff': mean_abs_dens_diff,
        'dens_match': dens_match
    }


def main():
    """主函数"""
    print(f"{'#'*60}")
    print(f"# 测试 flash_hdf5.py 的 3D 数据提取功能")
    print(f"# 逐点对比 flash_hdf5.py 与 yt 的处理结果")
    print(f"{'#'*60}")

    # 获取输入文件目录
    input_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'inputfiles', 'hdf5files_3d')
    input_dir = os.path.abspath(input_dir)
    print(f"\n输入文件目录: {input_dir}")

    # 设置输出目录（当前脚本所在目录）
    output_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(output_dir, exist_ok=True)
    print(f"输出目录: {output_dir}")

    # 确定要处理的文件
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        if not os.path.isabs(input_file):
            input_file = os.path.join(input_dir, input_file)
    else:
        # 使用第一个 plt_cnt 文件
        hdf5_files = sorted([
            f for f in os.listdir(input_dir)
            if f.startswith('lasslab_hdf5_plt_cnt') and os.path.isfile(os.path.join(input_dir, f))
        ])
        if len(hdf5_files) == 0:
            print(f"\n❌ 错误: 在 {input_dir} 中未找到任何 HDF5 文件!")
            return
        input_file = os.path.join(input_dir, hdf5_files[-1])  # 最晚时间
        print(f"\n使用最新 plt_cnt 文件: {hdf5_files[-1]}")

    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"\n❌ 错误: 输入文件不存在: {input_file}")
        return

    # 生成 yt 基准数据（如果 yt 可用）
    yt_baseline_file = None
    if HAS_YT:
        yt_baseline_file = save_yt_baseline_3d(input_file, output_dir)
    else:
        # 尝试读取已有的基准数据
        basename = os.path.splitext(os.path.basename(input_file))[0]
        yt_baseline_file = os.path.join(output_dir, f"{basename}_yt_baseline.csv")
        if not os.path.exists(yt_baseline_file):
            print(f"\n⚠️ yt 未安装，且未找到基准数据: {yt_baseline_file}")
            print(f"   请在有 yt 的环境中运行一次，生成基准数据")
            return

    # 逐点对比
    result = compare_point_by_point_3d(input_file, yt_baseline_file)

    if result:
        print(f"\n✅ 测试完成!")
    else:
        print(f"\n❌ 测试失败!")


if __name__ == '__main__':
    main()


# ==================== pytest 兼容测试函数 ====================

def test_3d_extraction():
    """pytest 测试：验证 3D 数据提取与 yt 一致（需要 HDF5 输入文件）"""
    import pytest
    import os
    
    # 查找测试文件（与 main() 函数保持一致）
    input_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'inputfiles', 'hdf5files_3d')
    input_dir = os.path.abspath(input_dir)

    if not os.path.isdir(input_dir):
        pytest.skip(f"input_files dir not found: {input_dir}")
    
    hdf5_files = sorted([
        f for f in os.listdir(input_dir)
        if f.startswith('lasslab_hdf5_plt_cnt') and os.path.isfile(os.path.join(input_dir, f))
    ])

    if len(hdf5_files) == 0:
        pytest.skip(f"No HDF5 test files in {input_dir}")

    if not HAS_YT:
        pytest.skip("yt not installed — cannot run yt comparison test")

    input_file = os.path.join(input_dir, hdf5_files[-1])  # 最晚时间
    
    # 运行对比测试
    result = compare_point_by_point_3d(input_file, yt_baseline_file=None)
    
    assert result is not None, "测试失败（返回 None）"
    assert result['npoints_match'], f"数据点数量不一致: hdf5={result['npoints_hdf5']}, yt={result['npoints_yt']}"
    
    # 放宽精度要求：坐标差异 < 1e-8 视为一致（机器精度范围内）
    assert result['coord_max_diff_x'] < 1e-8, f"x 坐标差异过大: max_diff={result['coord_max_diff_x']:.6e}"
    assert result['coord_max_diff_y'] < 1e-8, f"y 坐标差异过大: max_diff={result['coord_max_diff_y']:.6e}"
    assert result['coord_max_diff_z'] < 1e-8, f"z 坐标差异过大: max_diff={result['coord_max_diff_z']:.6e}"
    
    # 密度差异 < 1e-10 视为一致
    assert result['dens_max_diff'] < 1e-10, f"密度值不一致: max_diff={result['dens_max_diff']:.6e}"
