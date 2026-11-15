#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将提取的PDF文本转换为Markdown格式
"""

import re
from pathlib import Path

def convert_text_to_markdown(input_file, output_file):
    """
    将PDF提取的文本转换为Markdown格式
    """
    
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    print(f"读取文件: {input_file}")
    print(f"文件大小: {len(content)} 字符")
    
    # 按行分割
    lines = content.split('\n')
    
    md_lines = []
    md_lines.append("# FLASH User's Guide")
    md_lines.append("")
    md_lines.append("**Version:** 4.8")
    md_lines.append("")
    md_lines.append("**Date:** May 2024 (last updated May 6, 2024)")
    md_lines.append("")
    md_lines.append("**Source:** Flash Center for Computational Science, University of Rochester")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    
    current_section = ""
    in_toc = False
    page_num = 0
    
    for i, line in enumerate(lines):
        # 跳过空行
        if not line.strip():
            md_lines.append("")
            continue
        
        # 检测页码 (单独的罗马数字或阿拉伯数字)
        if re.match(r'^\s*[ivxlcIVXLC\d]+\s*$', line.strip()):
            page_num += 1
            continue
        
        # 检测章节标题 (大写字母开头的短行可能是标题)
        stripped = line.strip()
        
        # 检测主要章节 (全部大写，较短)
        if stripped.isupper() and len(stripped) < 50 and len(stripped) > 3:
            # 可能是章节标题
            if not stripped.startswith('FLASH') and 'USER' not in stripped:
                md_lines.append(f"## {stripped}")
                md_lines.append("")
                current_section = stripped
                continue
        
        # 检测子章节 (数字编号如 "1.1 Introduction")
        if re.match(r'^\d+(\.\d+)*\s+[A-Z]', stripped):
            md_lines.append(f"### {stripped}")
            md_lines.append("")
            continue
        
        # 普通文本
        # 检测是否是粗体 (ALL CAPS 的短句)
        words = stripped.split()
        if (len(words) <= 10 and 
            all(w.isupper() or not w.isalpha() for w in words) and 
            len(stripped) < 60):
            md_lines.append(f"**{stripped}**")
        else:
            md_lines.append(stripped)
    
    # 写入输出文件
    md_content = '\n'.join(md_lines)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"✓ Markdown文件已保存: {output_file}")
    print(f"  输出大小: {len(md_content)} 字符")
    
    return True

if __name__ == "__main__":
    input_file = Path("docs/flash4_ug_4p8_temp.txt")
    output_file = Path("docs/flash4_ug_4p8.md")
    
    if not input_file.exists():
        print(f"错误: 输入文件不存在: {input_file}")
        exit(1)
    
    print("=" * 60)
    print("PDF文本到Markdown转换")
    print("=" * 60)
    
    convert_text_to_markdown(input_file, output_file)
