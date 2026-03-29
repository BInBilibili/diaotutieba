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


def upload_to_github(post_dirs):
    """
    将爬取的帖子数据上传到GitHub仓库
    只上传新爬取的帖子目录
    """
    # 注意：不要在代码中硬编码GitHub令牌
    # 令牌已从代码中移除，避免被GitHub安全扫描检测到
    
    REPO_URL = "https://github.com/BInBilibili/diaotutieba.git"
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
        
        # 处理分支
        target_branch = "main"
        if not current_branch:
            # 没有分支，创建main分支
            print(f"创建{target_branch}分支...")
            result = run_git_command(["checkout", "-b", target_branch])
            if result and result.returncode == 0:
                print(f"✓ {target_branch}分支创建成功")
                current_branch = target_branch
            else:
                print(f"✗ {target_branch}分支创建失败")
                if result and result.stderr:
                    print(f"  错误: {result.stderr}")
        elif current_branch != target_branch:
            # 分支不匹配，切换到main分支
            print(f"切换到{target_branch}分支...")
            # 先尝试创建main分支
            result = run_git_command(["checkout", "-b", target_branch])
            if result and result.returncode != 0:
                # 如果已存在，直接切换
                result = run_git_command(["checkout", target_branch])
            if result and result.returncode == 0:
                print(f"✓ 切换到{target_branch}分支成功")
                current_branch = target_branch
            else:
                print(f"✗ 切换分支失败")
                if result and result.stderr:
                    print(f"  错误: {result.stderr}")
        
        # 确保仓库只包含必要文件
        print("\n检查仓库文件...")
        
        # 确保README.md存在
        if not os.path.exists("README.md"):
            readme_content = "# 吊图吧爬虫数据\n\n本仓库用于存储从吊图吧爬取的帖子数据。\n\n## 项目说明\n- 使用 TiebaScraper 爬取贴吧内容\n- 只存储爬取的帖子数据\n- 定期更新最新内容\n"
            with open("README.md", "w", encoding="utf-8") as f:
                f.write(readme_content)
            print("✓ 创建README.md文件")
        
        # 复制帖子到仓库根目录的scraped_data目录
        print("\n复制帖子到仓库目录...")
        import shutil
        
        # 确保仓库根目录有scraped_data目录
        repo_scraped_dir = os.path.join(REPO_PATH, "scraped_data")
        print(f"仓库scraped_data目录: {repo_scraped_dir}")
        os.makedirs(repo_scraped_dir, exist_ok=True)
        
        # 检查源帖子目录
        print(f"要复制的帖子目录数量: {len(post_dirs)}")
        for post_dir in post_dirs:
            print(f"  源目录: {post_dir}")
            print(f"  是否存在: {os.path.exists(post_dir)}")
        
        # 复制帖子目录
        for post_dir in post_dirs:
            # 获取帖子目录名称
            post_dir_name = os.path.basename(post_dir)
            # 目标路径
            target_path = os.path.join(repo_scraped_dir, post_dir_name)
            
            print(f"复制: {post_dir} -> {target_path}")
            
            # 如果目标存在，先删除
            if os.path.exists(target_path):
                print(f"  目标已存在，删除旧目录")
                shutil.rmtree(target_path, ignore_errors=True)
            
            # 复制帖子目录
            if os.path.exists(post_dir):
                shutil.copytree(post_dir, target_path)
                print(f"✓ 复制帖子成功: {post_dir_name}")
            else:
                print(f"✗ 源目录不存在: {post_dir}")
        
        # 验证复制结果
        print(f"\n验证仓库scraped_data目录内容:")
        if os.path.exists(repo_scraped_dir):
            items = os.listdir(repo_scraped_dir)
            print(f"  目录存在，包含 {len(items)} 个项目")
            for item in items:
                print(f"    - {item}")
        else:
            print(f"  目录不存在: {repo_scraped_dir}")
        
        # 只添加scraped_data目录和README.md
        print("\n添加文件到暂存区...")
        
        # 添加README.md
        result = run_git_command(["add", "README.md"])
        if result and result.returncode == 0:
            print("✓ 添加README.md成功")
        
        # 添加scraped_data目录（使用-f强制添加，即使被.gitignore忽略）
        result = run_git_command(["add", "-f", "scraped_data"])
        if result and result.returncode == 0:
            print("✓ 添加scraped_data目录成功")
        else:
            print("✗ 添加scraped_data目录失败")
            if result and result.stderr:
                print(f"  错误: {result.stderr}")
        
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
        
        # 推送到远程仓库
        print("\n推送到远程仓库...")
        
        # 先尝试获取远程分支信息
        result = run_git_command(["fetch", "origin"])
        
        # 检查远程是否有main分支
        result = run_git_command(["ls-remote", "--heads", "origin", target_branch])
        has_remote_main = result and result.returncode == 0 and result.stdout.strip()
        
        if has_remote_main:
            # 远程有main分支，先合并
            print(f"远程存在{target_branch}分支，尝试合并...")
            result = run_git_command(["pull", "origin", target_branch, "--allow-unrelated-histories"])
            if result and result.returncode == 0:
                print("✓ 合并成功")
            else:
                print("⚠ 合并可能有冲突，继续推送...")
        
        # 推送
        result = run_git_command(["push", "-u", "origin", current_branch])
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
            
            # 显示手动推送说明
            print("\n=== 手动推送说明 ===")
            print("由于安全原因，GitHub阻止了包含令牌的推送")
            print("请按照以下步骤手动推送：")
            print("1. 打开命令提示符或Git Bash")
            print(f"2. 切换到目录: {REPO_PATH}")
            print("3. 运行命令: git push -u origin main")
            print("4. 按照GitHub提示输入用户名和密码（密码使用个人访问令牌）")
        
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
        # 爬取前1个帖子，除了置顶
        thread_range = [1, 2]  # 爬取第2个帖子（只爬取1个）
        
        # 准备保存的帖子数据
        tids = []
        thread_info = {}
        for thread in threads[thread_range[0]:thread_range[1]]:
            tids.append(thread.tid)
            thread_info[thread.tid] = thread.title
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
    
    # 跟踪新爬取的帖子目录
    new_post_dirs = []
    
    # 依次爬取每个tid
    for i, tid in enumerate(tids, 1):
        print(f"\n===== 开始爬取第 {i} 个帖子 (tid: {tid}) =====")
        try:
            # 直接await scrape(tid)，避免事件循环嵌套
            await scrape(tid)
            print(f"第 {i} 个帖子爬取完成 (tid: {tid})")
            
            # 构建帖子目录路径
            # 帖子目录在当前目录的"帖子"文件夹中
            # 格式为：[吊图吧][tid]帖子标题_时间戳
            import glob
            
            # 检查scraped_data目录（帖子实际保存的位置）
            scraped_dir = os.path.join(os.getcwd(), "scraped_data")
            if os.path.exists(scraped_dir):
                print(f"检查scraped_data目录: {scraped_dir}")
                # 列出scraped_data目录中的所有子目录
                for item in os.listdir(scraped_dir):
                    item_path = os.path.join(scraped_dir, item)
                    if os.path.isdir(item_path) and f"[{tid}]" in item:
                        new_post_dirs.append(item_path)
                        print(f"找到帖子目录: {item_path}")
            else:
                print("scraped_data目录不存在")
        except Exception as e:
            print(f"爬取第 {i} 个帖子时出错 (tid: {tid}): {e}")
        
        # 爬取间隔，避免请求过快
        if i < len(tids):
            print("等待2秒后继续...")
            await asyncio.sleep(2)
    
    print(f"\n所有 {len(tids)} 个帖子爬取完成！")
    
    # 上传到GitHub仓库
    if new_post_dirs:
        print(f"\n准备上传 {len(new_post_dirs)} 个新爬取的帖子目录")
        upload_to_github(new_post_dirs)
    else:
        print("\n没有新爬取的帖子目录需要上传")


if __name__ == "__main__":
    asyncio.run(main())