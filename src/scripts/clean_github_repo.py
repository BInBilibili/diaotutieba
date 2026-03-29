#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清空GitHub仓库，只保留README.md文件
"""

import os
import subprocess
import sys


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
        print(f"命令执行失败: {e}")
        return None


def clean_github_repo():
    """
    清空GitHub仓库，只保留README.md文件
    """
    # 仓库路径（项目根目录）
    REPO_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print("=" * 60)
    print("开始清空GitHub仓库")
    print("=" * 60)
    print(f"仓库路径: {REPO_PATH}")
    
    try:
        # 切换到仓库目录
        os.chdir(REPO_PATH)
        print(f"已切换到目录: {os.getcwd()}")
        
        # 检查是否为Git仓库
        if not os.path.exists(".git"):
            print("✗ 当前目录不是Git仓库")
            return
        
        print("✓ Git仓库已存在")
        
        # 检查当前分支
        print("\n检查当前分支...")
        result = run_git_command(["branch"])
        current_branch = ""
        if result and result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.startswith('* '):
                    current_branch = line[2:].strip()
                    break
            print(f"当前分支: {current_branch if current_branch else '无分支'}")
        
        if not current_branch:
            print("✗ 没有活动的分支，无法继续")
            return
        
        # 查看当前文件
        print("\n当前仓库文件:")
        for item in os.listdir(REPO_PATH):
            if item not in [".git"]:
                print(f"  - {item}")
        
        # 确认操作
        confirm = input("\n确认清空仓库，只保留README.md？(y/n): ")
        if confirm.lower() != 'y':
            print("取消操作")
            return
        
        # 删除所有文件和目录，保留.git和README.md
        print("\n开始删除文件...")
        deleted_items = []
        for item in os.listdir(REPO_PATH):
            if item not in [".git", "README.md"]:
                item_path = os.path.join(REPO_PATH, item)
                try:
                    if os.path.isdir(item_path):
                        # 删除目录
                        import shutil
                        shutil.rmtree(item_path)
                        print(f"  ✓ 删除目录: {item}")
                    else:
                        # 删除文件
                        os.remove(item_path)
                        print(f"  ✓ 删除文件: {item}")
                    deleted_items.append(item)
                except Exception as e:
                    print(f"  ✗ 删除失败: {item} - {e}")
        
        if not deleted_items:
            print("  没有需要删除的文件")
        
        # 确保README.md存在
        if not os.path.exists("README.md"):
            readme_content = """# 吊图吧爬虫数据

本仓库用于存储从吊图吧爬取的帖子数据。

## 项目说明
- 使用 TiebaScraper 爬取贴吧内容
- 只存储爬取的帖子数据
- 定期更新最新内容
"""
            with open("README.md", "w", encoding="utf-8") as f:
                f.write(readme_content)
            print("\n✓ 创建README.md文件")
        else:
            print("\n✓ README.md文件已存在")
        
        # 添加所有更改到Git
        print("\n添加更改到Git...")
        result = run_git_command(["add", "-A"])
        if result and result.returncode == 0:
            print("✓ 添加成功")
        else:
            print("✗ 添加失败")
            if result and result.stderr:
                print(f"  错误: {result.stderr}")
        
        # 检查Git状态
        result = run_git_command(["status"])
        if result and result.returncode == 0:
            print("\nGit状态:")
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    print(f"  {line}")
        
        # 提交更改
        print("\n提交更改...")
        result = run_git_command(["commit", "-m", "清空仓库，只保留README.md"])
        if result and result.returncode == 0:
            print("✓ 提交成功")
        else:
            print("✗ 提交失败")
            if result and result.stderr:
                print(f"  错误: {result.stderr}")
            return
        
        # 推送到远程仓库
        print("\n推送到远程仓库...")
        result = run_git_command(["push", "origin", current_branch])
        if result and result.returncode == 0:
            print("✓ 推送成功！")
            print("\n推送结果:")
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    print(f"  {line}")
        else:
            print("✗ 推送失败")
            if result and result.stderr:
                print(f"  错误: {result.stderr}")
            print("\n请手动运行以下命令推送:")
            print(f"  cd {REPO_PATH}")
            print(f"  git push origin {current_branch}")
        
        print("\n" + "=" * 60)
        print("仓库清空完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 操作失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    clean_github_repo()
