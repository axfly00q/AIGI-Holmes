#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查 .gitignore 配置"""

import os

def check_gitignore():
    """检查 .gitignore 中的关键项"""
    with open('.gitignore') as f:
        content = f.read()
    
    print("=" * 60)
    print("检查 .gitignore 配置")
    print("=" * 60)
    
    if '.env' in content:
        print("✓ .gitignore 包含 .env")
    else:
        print("✗ .gitignore 未包含 .env - 需要添加！")
    
    # 检查其他关键项
    items = ['.env', '__pycache__', '*.pyc', '*.db', 'venv', '.pytest_cache', 'dist/', 'build/']
    print("\n检查项:")
    for item in items:
        mark = "✓" if item in content else "✗"
        print(f"  {mark} {item}")
    
    print("=" * 60)

def ensure_env_in_gitignore():
    """确保 .env 在 .gitignore 中"""
    with open('.gitignore') as f:
        content = f.read()
    
    if '.env' not in content:
        # 添加 .env 到 .gitignore
        with open('.gitignore', 'a', encoding='utf-8') as f:
            f.write("\n# 环境变量配置（不提交到 GitHub）\n")
            f.write(".env\n")
        print("\n✓ 已添加 .env 到 .gitignore")
    else:
        print("\n✓ .env 已在 .gitignore 中")

if __name__ == '__main__':
    check_gitignore()
    ensure_env_in_gitignore()
