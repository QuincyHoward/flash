#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将FLASH用户指南PDF转换为Markdown格式
支持多种PDF处理库
"""

import sys
from pathlib import Path

def convert_with_pdfplumber(pdf_path, output_path):
    """使用pdfplumber提取PDF文本并转换为Markdown"""
    try:
        import pdfplumber
    except ImportError:
        return False, "pdfplumber未安装"
    
    print(f"使用pdfplumber转换: {pdf_path}")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as outf:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    outf.write(f"\n\n## 第 {i+1} 页\n\n")
                    text = page.extract_text()
                    if text:
                        # 简单的文本到markdown转换
                        lines = text.split('\n')
                        for line in lines:
                            line = line.strip()
                            if line:
                                outf.write(line + '  \n')
        
        return True, f"转换完成: {output_path}"
        
    except Exception as e:
        return False, str(e)

def convert_with_pypdf2(pdf_path, output_path):
    """使用PyPDF2提取PDF文本"""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        return False, "PyPDF2未安装"
    
    print(f"使用PyPDF2转换: {pdf_path}")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as outf:
            reader = PdfReader(pdf_path)
            for i, page in enumerate(reader.pages):
                outf.write(f"\n\n## 第 {i+1} 页\n\n")
                text = page.extract_text()
                if text:
                    outf.write(text + '\n')
        
        return True, f"转换完成: {output_path}"
        
    except Exception as e:
        return False, str(e)

def convert_with_markitdown(pdf_path, output_path):
    """使用markitdown转换PDF到Markdown"""
    try:
        from markitdown import MarkItDown
    except ImportError:
        return False, "markitdown未安装"
    
    print(f"使用markitdown转换: {pdf_path}")
    
    try:
        converter = MarkItDown()
        result = converter.convert(str(pdf_path))
        md_content = result.text_content
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        return True, f"转换完成: {output_path}"
        
    except Exception as e:
        return False, str(e)

def convert_pdf_to_markdown(pdf_path, output_path):
    """尝试使用多种方法转换PDF"""
    
    # 方法1: markitdown (最好的格式保留)
    print("尝试使用 markitdown...")
    success, msg = convert_with_markitdown(pdf_path, output_path)
    if success:
        print(f"✓ {msg}")
        return True
    else:
        print(f"  {msg}")
    
    # 方法2: pdfplumber
    print("尝试使用 pdfplumber...")
    success, msg = convert_with_pdfplumber(pdf_path, output_path)
    if success:
        print(f"✓ {msg}")
        return True
    else:
        print(f"  {msg}")
    
    # 方法3: PyPDF2
    print("尝试使用 PyPDF2...")
    success, msg = convert_with_pypdf2(pdf_path, output_path)
    if success:
        print(f"✓ {msg}")
        return True
    else:
        print(f"  {msg}")
    
    print("\n错误: 没有可用的PDF处理库")
    print("请安装以下任一库:")
    print("  pip install markitdown")
    print("  pip install pdfplumber")
    print("  pip install PyPDF2")
    return False

if __name__ == "__main__":
    pdf_file = Path("docs/flash4_ug_4p8.pdf")
    output_file = Path("docs/flash4_ug_4p8.md")
    
    if not pdf_file.exists():
        print(f"错误: PDF文件不存在: {pdf_file}")
        sys.exit(1)
    
    print(f"输入: {pdf_file}")
    print(f"输出: {output_file}")
    print("=" * 60)
    
    success = convert_pdf_to_markdown(pdf_file, output_file)
    sys.exit(0 if success else 1)
