#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查和修复 md 文件编码"""

import os

def detect_encoding(filepath):
    """简单的编码检测"""
    with open(filepath, 'rb') as f:
        raw = f.read()
    
    # 检查 BOM
    if raw.startswith(b'\xef\xbb\xbf'):
        return 'utf-8-sig', True
    elif raw.startswith(b'\xff\xfe'):
        return 'utf-16-le', False
    elif raw.startswith(b'\xfe\xff'):
        return 'utf-16-be', False
    
    # 尝试 UTF-8
    try:
        raw.decode('utf-8')
        return 'utf-8', False
    except:
        pass
    
    # 尝试 GB2312/GBK
    try:
        raw.decode('gb2312')
        return 'gb2312', False
    except:
        pass
    
    return 'unknown', False

def check_files():
    """检查主要 md 文件的编码"""
    files = [
        'QUICK_START.md',
        'INSTALLATION_GUIDE.md',
        'USAGE.md',
        'DESIGN_PLAN.md',
        'FIX_REPORT.md',
        'README.md',
        'docs/packaging.md',
        'docs/desktop-windows.md'
    ]
    
    print("=" * 60)
    print("检查 MD 文件编码")
    print("=" * 60)
    
    for f in files:
        if os.path.exists(f):
            enc, has_bom = detect_encoding(f)
            if enc == 'utf-8' and not has_bom:
                print(f"✓ {f}: UTF-8 (correct)")
            else:
                status = "has BOM" if has_bom else f"encoding: {enc}"
                print(f"✗ {f}: UTF-8 {status}")
        else:
            print(f"- {f}: NOT FOUND")
    print("=" * 60)

def fix_encoding(filename, target_encoding='utf-8'):
    """转换文件编码到目标编码（去除 BOM）"""
    try:
        # 尝试读取文件
        with open(filename, 'rb') as f:
            raw = f.read()
        
        # 检测当前编码
        enc, has_bom = detect_encoding(filename)
        
        # 解码
        if has_bom and enc == 'utf-8-sig':
            content = raw[3:].decode('utf-8')
        elif enc in ['utf-8', 'utf-8-sig']:
            content = raw.decode('utf-8', errors='replace')
        else:
            content = raw.decode(enc, errors='replace')
        
        # 写回为纯 UTF-8（无 BOM）
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
    except Exception as e:
        print(f"错误处理 {filename}: {e}")
        return False

if __name__ == '__main__':
    check_files()
