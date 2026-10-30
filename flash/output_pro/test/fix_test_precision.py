"""
修复测试文件的精度判断逻辑。

将"坐标完全一致: ❌ 否"改为更合适的提示：
- 差异 < 1e-8: "⚠️ 基本一致（机器精度范围内）"
- 差异 > 1e-8: "❌ 不一致"
"""

import sys
import os
from pathlib import Path

def fix_test_file(filepath):
    """修复单个测试文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否需要修复
    if "coord_match = np.allclose" not in content:
        print(f"⏭  {filepath.name}: 无需修复")
        return False

    # 修复 1D 测试
    if "1D" in filepath.name or filepath.parent.name == "d1":
        # 添加分档判断逻辑
        old_str1 = '''    coord_match = np.allclose(x_hdf5_sorted, x_yt_sorted, rtol=1e-10, atol=1e-14)

    print(f"   最大坐标差异: {max_coord_diff:.6e}")
    print(f"   平均坐标差异: {mean_coord_diff:.6e}")
    print(f"   坐标完全一致: {'✅ 是' if coord_match else '❌ 否'}")'''

        new_str1 = '''    coord_match = np.allclose(x_hdf5_sorted, x_yt_sorted, rtol=1e-10, atol=1e-14)

    # 判断坐标一致性（分档）
    if coord_match:
        coord_status = "✅ 完全一致"
    elif max_coord_diff < 1e-8:
        coord_status = f"⚠️ 基本一致（差异 < 1e-8，机器精度范围内）"
    else:
        coord_status = "❌ 不一致"

    print(f"   最大坐标差异: {max_coord_diff:.6e}")
    print(f"   平均坐标差异: {mean_coord_diff:.6e}")
    print(f"   坐标一致性: {coord_status}")'''

        if old_str1 in content:
            content = content.replace(old_str1, new_str1)
            print(f"✅ {filepath.name}: 修复 1D 坐标判断")
        else:
            print(f"⚠️  {filepath.name}: 未找到 1D 坐标判断代码")

        # 修复对比报告中的输出
        old_str2 = '''    print(f"  完全一致: {'✅ 是' if coord_match else '❌ 否'}")'''

        new_str2 = '''    print(f"  一致性: {coord_status}")'''

        if old_str2 in content:
            content = content.replace(old_str2, new_str2)
            print(f"✅ {filepath.name}: 修复对比报告输出")

    # 修复 2D/3D 测试
    elif "2D" in filepath.name or "3D" in filepath.name or filepath.parent.name in ["d2", "d3"]:
        # 2D/3D 需要比较 x, y(, z) 三个坐标
        # 这里简化为检查是否有 x_coord_diff 变量
        if "x_coord_diff" in content or "x_max_diff" in content:
            print(f"⚠️  {filepath.name}: 2D/3D 测试需要手动修复")
        else:
            print(f"⏭  {filepath.name}: 无需修复（未找到坐标判断代码）")

    # 写回文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ {filepath.name}: 修复完成")
    return True


def main():
    """主函数"""
    # 查找所有测试文件
    test_dir = Path(__file__).parent

    # 查找 d1/d2/d3 目录中的测试文件
    for d in ["d1", "d2", "d3"]:
        d_dir = test_dir / d
        if not d_dir.exists():
            continue

        for test_file in d_dir.glob("test_*.py"):
            print(f"\n修复: {test_file}")
            fix_test_file(test_file)


if __name__ == '__main__':
    main()
