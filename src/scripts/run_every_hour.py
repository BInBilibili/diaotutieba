#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每小时自动运行爬取脚本
"""

import os
import time
import schedule
import subprocess
import sys


# 配置参数
CLEAN_ON_FIRST_RUN = True  # 首次运行时是否清空GitHub仓库中的scraped_data目录

# 爬取脚本的路径
SCRAPE_SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "爬取tid.py"
)

# 清理脚本的路径
CLEAN_SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "clean_scraped_data.py"
)


def run_clean_script():
    """运行清理脚本（清空scraped_data目录）"""
    print("=" * 60)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始运行清理脚本")
    print("=" * 60)
    
    try:
        # 运行清理脚本，使用--no-confirm参数跳过确认
        result = subprocess.run(
            [sys.executable, CLEAN_SCRIPT_PATH, "--no-confirm"],
            capture_output=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # 输出结果
        if result.stdout:
            print("清理脚本输出:")
            print(result.stdout)
        
        if result.stderr:
            print("清理脚本错误:")
            print(result.stderr)
        
        print(f"清理脚本返回码: {result.returncode}")
        
    except Exception as e:
        print(f"运行清理脚本时出错: {e}")
    
    print("=" * 60)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 清理脚本运行完成")
    print("=" * 60)
    print()


def run_scrape_script():
    """运行爬取脚本"""
    print("=" * 60)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始运行爬取脚本")
    print("=" * 60)
    
    try:
        # 运行爬取脚本，直接设置编码为utf-8，处理所有字符
        result = subprocess.run(
            [sys.executable, SCRAPE_SCRIPT_PATH],
            capture_output=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # 输出结果
        if result.stdout:
            print("脚本输出:")
            print(result.stdout)
        
        if result.stderr:
            print("脚本错误:")
            print(result.stderr)
        
        print(f"脚本返回码: {result.returncode}")
        
    except Exception as e:
        print(f"运行脚本时出错: {e}")
    
    print("=" * 60)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 爬取脚本运行完成")
    print("=" * 60)
    print()


def main():
    """主函数"""
    print("开始每小时自动运行爬取脚本")
    print(f"爬取脚本路径: {SCRAPE_SCRIPT_PATH}")
    print(f"清理脚本路径: {CLEAN_SCRIPT_PATH}")
    print(f"首次运行时清空scraped_data目录: {CLEAN_ON_FIRST_RUN}")
    print("按 Ctrl+C 退出")
    print()
    
    # 首次运行时清空scraped_data目录（如果配置开启）
    if CLEAN_ON_FIRST_RUN:
        print("[首次运行] 开始清空GitHub仓库中的scraped_data目录...")
        run_clean_script()
        print("[首次运行] scraped_data目录清空完成")
        print()
    
    # 立即运行一次爬取
    run_scrape_script()
    
    # 每小时运行一次
    schedule.every().hour.do(run_scrape_script)
    
    # 持续运行
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次


if __name__ == "__main__":
    main()
