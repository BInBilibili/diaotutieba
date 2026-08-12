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

# 强制 stdout/stderr 使用 utf-8，避免 Windows 默认 gbk 编码遇到 emoji/中文报错
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# 子进程环境变量，强制子进程也用 utf-8 IO 编码
CHILD_ENV = os.environ.copy()
CHILD_ENV['PYTHONIOENCODING'] = 'utf-8'

# 阻止电脑休眠的功能
try:
    import ctypes
    # 定义Windows API常量
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002
    
    def prevent_sleep():
        """阻止电脑休眠（允许屏幕关闭）"""
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        )
        return True
    
    def allow_sleep():
        """允许电脑休眠"""
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        return True
    
    CAN_PREVENT_SLEEP = True
except Exception:
    # 如果在非Windows系统或无法导入ctypes，设置为False
    CAN_PREVENT_SLEEP = False
    def prevent_sleep():
        """非Windows系统，无法阻止休眠"""
        return False
    
    def allow_sleep():
        """非Windows系统，无法允许休眠"""
        return False


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
            errors='replace',
            env=CHILD_ENV
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
            errors='replace',
            env=CHILD_ENV
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
    print(f"阻止电脑休眠: {CAN_PREVENT_SLEEP}")
    print("按 Ctrl+C 退出")
    print()
    
    # 阻止电脑休眠
    if CAN_PREVENT_SLEEP:
        if prevent_sleep():
            print("[系统] 已阻止电脑休眠")
        else:
            print("[系统] 无法阻止电脑休眠")
    else:
        print("[系统] 不支持阻止电脑休眠（非Windows系统）")
    
    try:
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
            # 定期调用prevent_sleep()以保持阻止状态
            if CAN_PREVENT_SLEEP:
                prevent_sleep()
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    
    except KeyboardInterrupt:
        print("\n[系统] 收到退出信号，正在清理...")
    finally:
        # 恢复电脑休眠功能
        if CAN_PREVENT_SLEEP:
            if allow_sleep():
                print("[系统] 已恢复电脑休眠功能")
            else:
                print("[系统] 无法恢复电脑休眠功能")
        print("脚本已退出")


if __name__ == "__main__":
    main()
