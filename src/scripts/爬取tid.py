import asyncio
import json
import os
import sys
import subprocess
from datetime import datetime

import aiotieba as tb

# 添加src目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 导入爬取模块
from modules.scrape_module import scrape
from scrape_config import ScrapeConfig, DownloadUserAvatarMode


def save_tids_to_file(tids, filename="tid.json"):
    """保存tid到本地文件，如果文件已存在则合并数据"""
    # 创建保存目录
    save_dir = os.path.join(os.getcwd(), "tieba_data")
    os.makedirs(save_dir, exist_ok=True)
    
    # 生成文件路径
    filepath = os.path.join(save_dir, filename)
    
    # 如果文件已存在，读取现有的tid
    existing_tids = []
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                existing_tids = json.load(f)
                if not isinstance(existing_tids, list):
                    existing_tids = []
        except (json.JSONDecodeError, IOError):
            existing_tids = []
    
    # 计算实际新增的tid（去重）
    new_tids = [tid for tid in tids if tid not in existing_tids]
    
    # 合并新旧tid
    all_tids = existing_tids + new_tids
    
    # 保存数据
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(all_tids, f, ensure_ascii=False, indent=2)
    
    print(f"数据已保存到: {filepath}")
    print(f"本次新增 {len(new_tids)} 个tid，文件中共 {len(all_tids)} 个tid")


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


def upload_to_github():
    """
    将爬取的帖子数据上传到GitHub仓库
    """
    # GitHub配置
    GITHUB_TOKEN = "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"
    REPO_URL = f"https://{GITHUB_TOKEN}@github.com/BInBilibili/diaotutieba.git"
    REPO_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 项目根目录
    
    print("\n===== 开始上传到GitHub仓库 =====")
    print(f"仓库路径: {REPO_PATH}")
    
    try:
        # 切换到仓库目录
        os.chdir(REPO_PATH)
        print(f"已切换到目录: {os.getcwd()}")
        
        # 检查是否为Git仓库
        is_new_repo = False
        if not os.path.exists(".git"):
            is_new_repo = True
            print("初始化Git仓库...")
            result = run_git_command(["init"])
            if result and result.returncode == 0:
                print("✓ Git仓库初始化成功")
            else:
                print("✗ Git仓库初始化失败")
                return
            
            # 配置用户信息
            result = run_git_command(["config", "user.name", "BInBilibili"])
            if result and result.returncode == 0:
                print("✓ Git用户名配置完成")
            
            result = run_git_command(["config", "user.email", "your.email@example.com"])
            if result and result.returncode == 0:
                print("✓ Git邮箱配置完成")
            
            # 添加远程仓库
            print("添加远程仓库...")
            result = run_git_command(["remote", "add", "origin", REPO_URL])
            if result and result.returncode == 0:
                print("✓ 远程仓库添加成功")
            else:
                print("✗ 远程仓库添加失败")
                return
        else:
            print("✓ Git仓库已存在")
        
        # 检查远程仓库
        print("\n检查远程仓库...")
        result = run_git_command(["remote", "-v"])
        if result and result.returncode == 0:
            print("远程仓库信息:")
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    print(f"  {line}")
        
        # 添加所有文件
        print("\n添加文件到暂存区...")
        result = run_git_command(["add", "."])
        if result and result.returncode == 0:
            print("✓ 文件添加成功")
        
        # 检查状态
        result = run_git_command(["status"])
        if result and result.returncode == 0:
            print("\nGit状态:")
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    print(f"  {line}")
        
        # 提交更改
        commit_message = f"更新爬取的帖子数据 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        print(f"\n提交更改: {commit_message}")
        result = run_git_command(["commit", "-m", commit_message])
        if result and result.returncode == 0:
            print("✓ 提交成功")
        else:
            print("✗ 提交失败（可能没有更改需要提交）")
            if result and result.stderr:
                print(f"  错误: {result.stderr}")
        
        # 检查当前分支
        result = run_git_command(["branch"])
        if result and result.returncode == 0:
            current_branch = result.stdout.strip()
            print(f"\n当前分支: {current_branch if current_branch else '无分支'}")
            
            # 如果没有分支，创建main分支
            if not current_branch:
                print("创建main分支...")
                result = run_git_command(["checkout", "-b", "main"])
                if result and result.returncode == 0:
                    print("✓ main分支创建成功")
                else:
                    print("✗ main分支创建失败")
                    if result and result.stderr:
                        print(f"  错误: {result.stderr}")
        
        # 推送到远程仓库
        print("\n推送到远程仓库...")
        
        # 先尝试获取远程分支信息
        result = run_git_command(["fetch", "origin"])
        
        # 检查远程是否有main分支
        result = run_git_command(["ls-remote", "--heads", "origin", "main"])
        has_remote_main = result and result.returncode == 0 and result.stdout.strip()
        
        if has_remote_main:
            # 远程有main分支，先合并
            print("远程存在main分支，尝试合并...")
            result = run_git_command(["pull", "origin", "main", "--allow-unrelated-histories"])
            if result and result.returncode == 0:
                print("✓ 合并成功")
            else:
                print("⚠ 合并可能有冲突，继续推送...")
        
        # 推送
        result = run_git_command(["push", "-u", "origin", "main"])
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
            
            # 如果推送失败，尝试强制推送（仅用于新仓库）
            if is_new_repo:
                print("\n尝试强制推送...")
                result = run_git_command(["push", "-f", "-u", "origin", "main"])
                if result and result.returncode == 0:
                    print("✓ 强制推送成功！")
                else:
                    print("✗ 强制推送也失败")
                    if result and result.stderr:
                        print(f"  错误: {result.stderr}")
        
        print("\n===== 上传到GitHub仓库完成 =====")
        
    except Exception as e:
        print(f"上传失败: {e}")


async def main():
    """主函数：获取tid并爬取帖子"""
    # 1. 获取tid并保存到文件
    async with tb.Client() as client:
        # 获取帖子列表
        forum_name = "吊图"
        threads = await client.get_threads(forum_name)
        
        # 配置爬取范围
        # 爬取前2个帖子，除了置顶
        thread_range = [1, 3]  # 爬取第2-3个帖子
        
        # 准备保存的帖子数据
        tids = []
        for thread in threads[thread_range[0]:thread_range[1]]:
            tids.append(thread.tid)
            print(f"已获取帖子: {thread.title} (ID: {thread.tid})")
        
        # 保存tid到文件（始终使用同一个文件tid.json）
        save_tids_to_file(tids)
        print(f"爬取完成，共获取 {len(tids)} 个帖子")
    
    # 2. 读取tid.json并爬取帖子
    # 读取tid.json文件
    save_dir = os.path.join(os.getcwd(), "tieba_data")
    filepath = os.path.join(save_dir, "tid.json")
    
    if not os.path.exists(filepath):
        print(f"错误：{filepath} 文件不存在！")
        return
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tids = json.load(f)
            if not isinstance(tids, list):
                print("错误：tid.json文件格式不正确！")
                return
    except (json.JSONDecodeError, IOError) as e:
        print(f"读取tid.json文件时出错：{e}")
        return
    
    print(f"\n从 {filepath} 中读取到 {len(tids)} 个tid")
    
    # 设置默认不爬取头像
    ScrapeConfig.DOWNLOAD_USER_AVATAR_MODE = DownloadUserAvatarMode.NONE
    print("已设置默认不爬取头像")
    
    # 依次爬取每个tid
    for i, tid in enumerate(tids, 1):
        print(f"\n===== 开始爬取第 {i} 个帖子 (tid: {tid}) =====")
        try:
            # 直接await scrape(tid)，避免事件循环嵌套
            await scrape(tid)
            print(f"第 {i} 个帖子爬取完成 (tid: {tid})")
        except Exception as e:
            print(f"爬取第 {i} 个帖子时出错 (tid: {tid}): {e}")
        
        # 爬取间隔，避免请求过快
        if i < len(tids):
            print("等待2秒后继续...")
            await asyncio.sleep(2)
    
    print(f"\n所有 {len(tids)} 个帖子爬取完成！")
    
    # 上传到GitHub仓库
    upload_to_github()


if __name__ == "__main__":
    asyncio.run(main())