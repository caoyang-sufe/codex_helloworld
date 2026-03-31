#!/usr/bin/env python
"""
Django Game Migration Verification Script
验证 Django 应用迁移是否成功
"""

import os
import sys
from pathlib import Path

def check_file_exists(path, description):
    """检查文件是否存在"""
    exists = os.path.exists(path)
    status = "✓ PASS" if exists else "✗ FAIL"
    print(f"{status}: {description}")
    print(f"  Path: {path}")
    return exists

def check_directory_exists(path, description):
    """检查目录是否存在"""
    exists = os.path.isdir(path)
    status = "✓ PASS" if exists else "✗ FAIL"
    print(f"{status}: {description}")
    print(f"  Path: {path}")
    return exists

def check_files_in_directory(path, pattern, min_count):
    """检查目录中是否存在指定数量的文件"""
    try:
        files = list(Path(path).glob(pattern))
        count = len(files)
        passed = count >= min_count
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {path} 中存在至少 {min_count} 个 {pattern} 文件 (实际: {count})")
        return passed
    except Exception as e:
        print(f"✗ FAIL: 无法检查 {path}: {e}")
        return False

def main():
    print("=" * 60)
    print("Django Game Migration 验证清单")
    print("=" * 60)
    print()
    
    base_dir = Path(__file__).parent
    checks = []
    
    # 检查模板文件
    print("【1】模板文件检查")
    print("-" * 60)
    checks.append(check_file_exists(
        base_dir / "templates" / "gameapp" / "game.html",
        "游戏模板文件"
    ))
    print()
    
    # 检查 Django 配置文件
    print("【2】Django 配置文件检查")
    print("-" * 60)
    checks.append(check_file_exists(
        base_dir / "webapp" / "settings.py",
        "settings.py 配置文件"
    ))
    checks.append(check_file_exists(
        base_dir / "webapp" / "urls.py",
        "urls.py 路由文件"
    ))
    checks.append(check_file_exists(
        base_dir / "gameapp" / "views.py",
        "gameapp/views.py 视图文件"
    ))
    print()
    
    # 检查可执行文件
    print("【3】可执行文件检查")
    print("-" * 60)
    checks.append(check_file_exists(
        base_dir / "manage.py",
        "manage.py (Django 管理脚本)"
    ))
    print()
    
    # 检查静态资源目录
    print("【4】静态资源目录检查")
    print("-" * 60)
    checks.append(check_directory_exists(
        base_dir / "assets" / "card",
        "assets/card 卡牌图片目录"
    ))
    checks.append(check_files_in_directory(
        base_dir / "assets" / "card",
        "*.png",
        100
    ))
    print()
    
    # 检查其他重要目录
    print("【5】目录结构检查")
    print("-" * 60)
    checks.append(check_directory_exists(
        base_dir / "templates",
        "templates 模板目录"
    ))
    checks.append(check_directory_exists(
        base_dir / "gameapp",
        "gameapp 应用目录"
    ))
    checks.append(check_directory_exists(
        base_dir / "webapp",
        "webapp 项目目录"
    ))
    print()
    
    # 总结
    print("=" * 60)
    print("验证结果总结")
    print("=" * 60)
    passed = sum(checks)
    total = len(checks)
    print(f"通过: {passed}/{total}")
    print()
    
    if passed == total:
        print("✓ 所有检查都已通过！")
        print()
        print("下一步：启动 Django 服务器")
        print("  python manage.py runserver 0.0.0.0:8080")
        print()
        print("然后访问:")
        print("  游戏: http://localhost:8080/game")
        print("  API:  http://localhost:8080/api/cards")
        return 0
    else:
        print("✗ 有些检查失败，请检查上面的错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main())
