#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清空GitHub仓库中的scraped_data目录
"""

import os
import subprocess
import sys


def safe_print(s):
    """
    安全打印函数，处理编码问题
    """
    try:
        print(s)
    except UnicodeEncodeError:
        # 尝试用gbk编码打印，失败则用utf-8
        if isinstance(s, str):
            try:
                # 尝试用gbk编码，替换无法编码的字符
                print(s.encode('gbk', errors='replace').decode('gbk'))
            except:
                #  fallback到utf-8
                print(s.encode('utf-8', errors='replace').decode('utf-8'))
        else:
            try:
                print(str(s))
            except UnicodeEncodeError:
                # 处理非字符串对象的编码问题
                print(repr(s))


def run_git_command(args, cwd=None):
    """
    运行Git命令并处理编码问题
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            cwd=cwd,
            encoding='utf-8',
            errors='replace'
        )
        return result
    except Exception as e:
        safe_print(f"命令执行失败: {e}")
        return None


def clean_scraped_data(confirm_required=True):
    """
    清空GitHub仓库中的scraped_data目录
    
    Args:
        confirm_required: 是否需要用户确认，默认为True
    """
    # 仓库路径（项目根目录）
    REPO_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    safe_print("=" * 60)
    safe_print("开始清空GitHub仓库中的scraped_data目录")
    safe_print("=" * 60)
    safe_print(f"仓库路径: {REPO_PATH}")
    
    try:
        # 切换到仓库目录
        os.chdir(REPO_PATH)
        safe_print(f"已切换到目录: {os.getcwd()}")
        
        # 检查是否为Git仓库
        if not os.path.exists(".git"):
            safe_print("[X] 当前目录不是Git仓库")
            return
        
        safe_print("[OK] Git仓库已存在")
        
        # 检查当前分支
        safe_print("\n检查当前分支...")
        result = run_git_command(["branch"])
        current_branch = ""
        if result and result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.startswith('* '):
                    current_branch = line[2:].strip()
                    break
            safe_print(f"当前分支: {current_branch if current_branch else '无分支'}")
        
        if not current_branch:
            safe_print("[X] 没有活动的分支，无法继续")
            return
        
        # 检查scraped_data目录是否存在
        scraped_data_path = os.path.join(REPO_PATH, "scraped_data")
        if not os.path.exists(scraped_data_path):
            safe_print("\n[OK] scraped_data目录不存在，无需清理")
            return
        
        # 查看当前scraped_data目录内容
        safe_print("\n当前scraped_data目录内容:")
        items = os.listdir(scraped_data_path)
        safe_print(f"  包含 {len(items)} 个项目:")
        for item in items:
            safe_print(f"    - {item}")
        
        # 确认操作（如果需要）
        if confirm_required:
            confirm = input("\n确认清空scraped_data目录？(y/n): ")
            if confirm.lower() != 'y':
                safe_print("取消操作")
                return
        else:
            safe_print("\n[自动模式] 跳过确认，直接清空scraped_data目录")
        
        # 删除scraped_data目录中的所有内容
        safe_print("\n开始删除scraped_data目录中的内容...")
        import shutil
        deleted_count = 0
        
        for item in os.listdir(scraped_data_path):
            item_path = os.path.join(scraped_data_path, item)
            try:
                if os.path.isdir(item_path):
                    # 删除目录
                    shutil.rmtree(item_path)
                    safe_print(f"  [OK] 删除目录: {item}")
                else:
                    # 删除文件
                    os.remove(item_path)
                    safe_print(f"  [OK] 删除文件: {item}")
                deleted_count += 1
            except Exception as e:
                safe_print(f"  [X] 删除失败: {item} - {e}")
        
        if deleted_count == 0:
            safe_print("  没有需要删除的内容")
        else:
            safe_print(f"\n[OK] 共删除 {deleted_count} 个项目")
        
        # 添加更改到Git
        safe_print("\n添加更改到Git...")
        result = run_git_command(["add", "-A"])
        if result and result.returncode == 0:
            safe_print("[OK] 添加成功")
        else:
            safe_print("[X] 添加失败")
            if result and result.stderr:
                safe_print(f"  错误: {result.stderr}")
        
        # 检查Git状态
        result = run_git_command(["status"])
        if result and result.returncode == 0:
            safe_print("\nGit状态:")
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    safe_print(f"  {line}")
        
        # 提交更改
        safe_print("\n提交更改...")
        result = run_git_command(["commit", "-m", "清空scraped_data目录"])
        if result and result.returncode == 0:
            safe_print("[OK] 提交成功")
        else:
            safe_print("[X] 提交失败")
            if result and result.stderr:
                safe_print(f"  错误: {result.stderr}")
            return
        
        # 推送到远程仓库
        safe_print("\n推送到远程仓库...")
        result = run_git_command(["push", "origin", current_branch])
        if result and result.returncode == 0:
            safe_print("[OK] 推送成功！")
            safe_print("\n推送结果:")
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    safe_print(f"  {line}")
        else:
            safe_print("[X] 推送失败")
            if result and result.stderr:
                safe_print(f"  错误: {result.stderr}")
            safe_print("\n尝试强制推送...")
            result = run_git_command(["push", "-f", "origin", current_branch])
            if result and result.returncode == 0:
                safe_print("[OK] 强制推送成功！")
            else:
                safe_print("[X] 强制推送也失败")
                safe_print("\n请手动运行以下命令推送:")
                safe_print(f"  cd {REPO_PATH}")
                safe_print(f"  git push origin {current_branch}")
        
        safe_print("\n" + "=" * 60)
        safe_print("scraped_data目录清空完成！")
        safe_print("=" * 60)
        
    except Exception as e:
        safe_print(f"\n[X] 操作失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 检查命令行参数
    confirm_required = True
    if len(sys.argv) > 1 and sys.argv[1] == "--no-confirm":
        confirm_required = False
    
    clean_scraped_data(confirm_required=confirm_required)
