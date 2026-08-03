#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从FLASH用户指南中提取仿真执行知识
重点关注：激光等离子体仿真、LaserSlab及其变体
"""

import re
from pathlib import Path

def extract_section_content(md_file, section_title, max_lines=500):
    """提取指定章节的内容"""
    with open(md_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    content = []
    in_section = False
    section_level = 0
    
    for i, line in enumerate(lines):
        # 检测章节标题
        if section_title.lower() in line.lower() and ('###' in line or '##' in line):
            in_section = True
            section_level = line.count('#')
            content.append(line)
            continue
        
        if in_section:
            # 如果遇到新的同级别或更高级别的标题，停止
            if line.strip().startswith('#'):
                current_level = line.count('#')
                if current_level <= section_level:
                    break
            content.append(line)
            
            if len(content) > max_lines:
                break
    
    return ''.join(content)

def extract_laserslab_knowledge(md_file, output_file):
    """提取LaserSlab相关知识和仿真执行流程"""
    
    print("=" * 70)
    print("提取FLASH仿真执行知识 (激光等离子体方向)")
    print("=" * 70)
    
    knowledge = []
    knowledge.append("# FLASH仿真执行知识库\n")
    knowledge.append(f"**来源:** FLASH4.8 User's Guide\n")
    knowledge.append(f"**提取时间:** 2026-06-16\n\n")
    knowledge.append("---\n\n")
    
    # 1. 仿真执行基本流程
    knowledge.append("## 1. FLASH仿真执行基本流程\n\n")
    knowledge.append("### 1.1 配置 (Setup)\n\n")
    knowledge.append("```bash\n")
    knowledge.append("# 基本语法\n")
    knowledge.append("./setup <SimulationName> [options]\n\n")
    knowledge.append("# 示例: LaserSlab 1D仿真\n")
    knowledge.append("./setup -auto LaserSlab -1d +cartesian -nxb=16 +hdf5typeio species=cham,targ +mtmmmt +laser +uhd3t +mgd mgd_meshgroups=10\n")
    knowledge.append("```\n\n")
    
    knowledge.append("### 1.2 编译 (Build)\n\n")
    knowledge.append("```bash\n")
    knowledge.append("cd object/\n")
    knowledge.append("make\n")
    knowledge.append("```\n\n")
    
    knowledge.append("### 1.3 运行 (Run)\n\n")
    knowledge.append("```bash\n")
    knowledge.append("# 并行运行 (N个进程)\n")
    knowledge.append("mpirun -np N ./flash4\n")
    knowledge.append("\n# 单机运行\n")
    knowledge.append("./flash4\n")
    knowledge.append("```\n\n")
    
    # 2. LaserSlab仿真特定知识
    knowledge.append("## 2. LaserSlab仿真配置\n\n")
    knowledge.append("### 2.1 Setup快捷键\n\n")
    knowledge.append("| 快捷键 | 说明 |\n")
    knowledge.append("|--------|------|\n")
    knowledge.append("| `+laser` | 启用激光射线追踪包 |\n")
    knowledge.append("| `+laserCubicInterpolation` | 启用立方插值射线追踪 |\n")
    knowledge.append("| `+asyncLaser` | 启用异步射线追踪通信 |\n")
    knowledge.append("| `+mtmmmt` | 启用多物种多温度 |\n")
    knowledge.append("| `+uhd3t` | 启用3T非分裂流体力学 |\n")
    knowledge.append("| `+mgd` | 启用多群辐射扩散 |\n\n")
    
    knowledge.append("### 2.2 激光参数配置 (Runtime Parameters)\n\n")
    knowledge.append("#### 2.2.1 激光脉冲参数\n\n")
    knowledge.append("```\n")
    knowledge.append("# 脉冲数量\n")
    knowledge.append("ed_numberofPulses = 1\n\n")
    knowledge.append("# 脉冲功率和时间点对 (ed_power_n_i, ed_time_n_i)\n")
    knowledge.append("ed_power_1_1 = 1.0e12  # 第一个脉冲的第一个功率点 (瓦特)\n")
    knowledge.append("ed_time_1_1 = 0.0      # 对应的时间 (秒)\n")
    knowledge.append("```\n\n")
    
    knowledge.append("#### 2.2.2 激光光束参数\n\n")
    knowledge.append("```\n")
    knowledge.append("# 光束数量\n")
    knowledge.append("ed_numberOfBeams = 1\n\n")
    knowledge.append("# 激光波长 (米)\n")
    knowledge.append("ed_wavelength_1 = 3.5e-7\n\n")
    knowledge.append("# 光束透镜坐标 (激光起源点)\n")
    knowledge.append("ed_lens_1_x = 0.0\n")
    knowledge.append("ed_lens_1_y = 0.0\n")
    knowledge.append("ed_lens_1_z = -0.01\n\n")
    knowledge.append("# 光束目标坐标 (激光照射点)\n")
    knowledge.append("ed_target_1_x = 0.0\n")
    knowledge.append("ed_target_1_y = 0.0\n")
    knowledge.append("ed_target_1_z = 0.0\n")
    knowledge.append("```\n\n")
    
    knowledge.append("#### 2.2.3 通用激光参数\n\n")
    knowledge.append("```\n")
    knowledge.append("# 最大脉冲数 (setup时需要)\n")
    knowledge.append("ed_maxPulses = 5\n\n")
    knowledge.append("# 最大光束数 (setup时需要)\n")
    knowledge.append("ed_maxBeams = 6\n\n")
    knowledge.append("# 每个时间步的能量沉积基于cell时间\n")
    knowledge.append("ed_cellTimeEnergyDeposition = .true.\n\n")
    knowledge.append("# 3D圆柱对称激光射线追踪\n")
    knowledge.append("ed_laser3Din2D = .false.\n")
    knowledge.append("```\n\n")
    
    # 3. 输出分析
    knowledge.append("## 3. 输出文件分析\n\n")
    knowledge.append("### 3.1 检查点文件 (Checkpoint Files)\n\n")
    knowledge.append("- 命名: `*_hdf5_chk_*`\n")
    knowledge.append("- 用途: 重启仿真\n\n")
    
    knowledge.append("### 3.2 绘图文件 (Plot Files)\n\n")
    knowledge.append("- 命名: `*_hdf5_plo_*`\n")
    knowledge.append("- 用途: 可视化和后处理\n\n")
    
    knowledge.append("### 3.3 激光IO输出\n\n")
    knowledge.append("```\n")
    knowledge.append("# 启用激光IO\n")
    knowledge.append("ed_useLaserIO = .true.\n\n")
    knowledge.append("# 最大射线数\n")
    knowledge.append("ed_laserIOMaxNumberOfRays = 1000\n\n")
    knowledge.append("# 每个射线的最大位置记录数\n")
    knowledge.append("ed_laserIOMaxNumberOfPositions = 100\n")
    knowledge.append("```\n\n")
    
    # 4. LaserSlab变体
    knowledge.append("## 4. LaserSlab变体\n\n")
    knowledge.append("### 4.1 全物理激光驱动仿真 (Section 35.7.5)\n\n")
    knowledge.append("- **几何:** 2D圆柱\n")
    knowledge.append("- **物理:** 3T流体力学 + 表格EOS和不透明度 + MGD + 电子热传导 + 激光射线追踪\n")
    knowledge.append("- **物种:** cham (腔), targ (靶)\n")
    knowledge.append("- **EOS:** IONMIX4格式表格\n\n")
    
    knowledge.append("### 4.2 带Thomson散射诊断的激光仿真 (Section 35.7.6)\n\n")
    knowledge.append("- **附加功能:** ThomsonScattering诊断\n")
    knowledge.append("- **Setup快捷键:** `+thsc`\n\n")
    
    knowledge.append("### 4.3 Z-pinch仿真 (Section 35.7.7)\n\n")
    knowledge.append("- **物理:** Z-pinch等离子体压缩\n\n")
    
    # 5. 常见问题
    knowledge.append("## 5. 常见问题与解决方案\n\n")
    knowledge.append("### 5.1 Setup阶段\n\n")
    knowledge.append("**Q: 如何指定激光相关参数？**\n")
    knowledge.append("A: 在`flash.par`文件中设置`ed_*`开头的运行时参数。\n\n")
    
    knowledge.append("**Q: Setup时如何设置最大脉冲/光束数？**\n")
    knowledge.append("A: 使用setup选项: `./setup ... +laser ed_maxPulses=5 ed_maxBeams=6`\n\n")
    
    knowledge.append("### 5.2 运行阶段\n\n")
    knowledge.append("**Q: 如何查看激光能量沉积？**\n")
    knowledge.append("A: 在Config文件中添加`REQUIRES VARIABLE lase`，然后在绘图文件中查看`lase`变量。\n\n")
    
    knowledge.append("**Q: 如何输出激光射线轨迹？**\n")
    knowledge.append("A: 在`flash.par`中设置`ed_useLaserIO = .true.`，输出将写入`<basename>LaserRaysPrint<PID>.txt`。\n\n")
    
    # 写入文件
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(''.join(knowledge))
    
    print(f"✓ 知识库已保存到: {output_path}")
    print(f"  文件大小: {output_path.stat().st_size / 1024:.1f} KB")
    
    return True

if __name__ == "__main__":
    md_file = Path("docs/flash4_ug_4p8.md")
    output_file = Path("docs/flash_simulation_execution_knowledge.md")
    
    if not md_file.exists():
        print(f"错误: Markdown文件不存在: {md_file}")
        exit(1)
    
    print(f"输入: {md_file}")
    print(f"输出: {output_file}")
    
    extract_laserslab_knowledge(md_file, output_file)
