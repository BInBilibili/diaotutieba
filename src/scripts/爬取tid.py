import asyncio
import json
import os
import sys
import subprocess
import time
from datetime import datetime

# 强制 stdout/stderr 使用 utf-8，避免 Windows 默认 gbk 编码遇到 emoji 报错
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import aiotieba as tb

# 配置参数
DEBUG_MODE = False  # 调试模式开关，True显示详细调试信息，False正常模式
UPLOAD_TO_GITHUB = True  # 是否上传到GitHub，True上传，False不上传

# 压缩配置
COMPRESS_ENABLED = False  # 是否启用压缩
COMPRESS_THRESHOLD_MB = 50  # 压缩阈值（MB），超过此大小的文件会被压缩
COMPRESS_DELETE_ORIGINAL = False  # 压缩后是否删除原文件

# 要爬取的贴吧列表
# 可以配置多个贴吧，每个贴吧可以单独设置爬取范围
# 格式: [(贴吧名, 起始帖子序号, 结束帖子序号), ...]
# 注意：置顶帖不算在内，序号从1开始
# 例如：(2, 4) 表示爬取第2、3、4个非置顶帖子
FORUMS = [
    ("steam", 5, 6),
    ("b站", 6, 6),
    ("V", 6, 6),
]

# 添加src目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 导入爬取模块
from modules.scrape_module import scrape
from scrape_config import ScrapeConfig, DownloadUserAvatarMode


def save_tids_to_file(tids, filename="tid.json"):
    """保存tid到本地文件，只保存本次爬取的tid，不累计"""
    # 创建保存目录
    save_dir = os.path.join(os.getcwd(), "tieba_data")
    os.makedirs(save_dir, exist_ok=True)
    
    # 生成文件路径
    filepath = os.path.join(save_dir, filename)
    
    # 只保存本次爬取的tid，不累计
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(tids, f, ensure_ascii=False, indent=2)
    
    print(f"数据已保存到: {filepath}")
    print(f"本次保存 {len(tids)} 个tid")


def run_git_command(args, cwd=None, timeout=60):
    """
    运行Git命令并处理编码问题
    """
    cmd_str = ' '.join(['git'] + args)
    
    if DEBUG_MODE:
        safe_print(f"\n[DEBUG] 开始执行命令: {cmd_str}")
        safe_print(f"[DEBUG] 工作目录: {cwd if cwd else os.getcwd()}")
        safe_print(f"[DEBUG] 超时时间: {timeout}秒")
    
    try:
        start_time = time.time()
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            cwd=cwd,
            encoding='utf-8',
            errors='replace',
            timeout=timeout
        )
        end_time = time.time()
        elapsed = end_time - start_time
        
        if DEBUG_MODE:
            safe_print(f"[DEBUG] 命令执行完成，耗时: {elapsed:.2f}秒")
            safe_print(f"[DEBUG] 返回码: {result.returncode}")
            if result.stdout:
                safe_print(f"[DEBUG] 标准输出: {result.stdout[:500]}..." if len(result.stdout) > 500 else f"[DEBUG] 标准输出: {result.stdout}")
            if result.stderr:
                safe_print(f"[DEBUG] 标准错误: {result.stderr[:500]}..." if len(result.stderr) > 500 else f"[DEBUG] 标准错误: {result.stderr}")
        
        return result
    except subprocess.TimeoutExpired:
        safe_print(f"[ERROR] 命令执行超时: {cmd_str}")
        return None
    except Exception as e:
        safe_print(f"[ERROR] 命令执行失败: {e}")
        return None


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


def compress_large_files(directory, threshold_mb=50, delete_original=False):
    """
    压缩目录中的大文件
    
    Args:
        directory: 要扫描的目录
        threshold_mb: 压缩阈值（MB），超过此大小的文件会被压缩
        delete_original: 压缩后是否删除原文件
    
    Returns:
        int: 压缩的文件数量
    """
    import zipfile
    
    compressed_count = 0
    total_saved_mb = 0
    
    if not COMPRESS_ENABLED:
        safe_print("[压缩] 压缩功能已禁用")
        return compressed_count
    
    safe_print(f"\n[压缩] 开始扫描大文件...")
    safe_print(f"[压缩] 扫描目录: {directory}")
    safe_print(f"[压缩] 压缩阈值: {threshold_mb}MB")
    
    for root, dirs, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            
            try:
                file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
                
                if file_size_mb > threshold_mb:
                    safe_print(f"[压缩] 发现大文件 ({file_size_mb:.2f}MB): {filename}")
                    
                    zip_path = filepath + '.zip'
                    
                    safe_print(f"[压缩] 正在压缩: {filename} -> {filename}.zip")
                    
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        zipf.write(filepath, arcname=filename)
                    
                    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
                    saved_mb = file_size_mb - zip_size_mb
                    
                    safe_print(f"[压缩] 压缩完成，原文件 {file_size_mb:.2f}MB -> 压缩后 {zip_size_mb:.2f}MB (节省 {saved_mb/file_size_mb*100:.1f}%)")
                    
                    if delete_original:
                        os.remove(filepath)
                        safe_print(f"[压缩] 已删除原文件")
                    
                    compressed_count += 1
                    total_saved_mb += saved_mb
                    
            except Exception as e:
                safe_print(f"[压缩] 压缩文件 {filename} 时出错: {e}")
    
    if compressed_count > 0:
        safe_print(f"\n[压缩] 共处理 {compressed_count} 个大文件，节省空间 {total_saved_mb:.2f}MB")
    else:
        safe_print("[压缩] 未发现需要压缩的大文件")
    
    return compressed_count


def upload_to_github(post_dirs):
    """
    将爬取的帖子数据上传到GitHub仓库
    只上传新爬取的帖子目录
    """
    # 注意：不要在代码中硬编码GitHub令牌
    # 令牌已从代码中移除，避免被GitHub安全扫描检测到
    
    REPO_URL = "https://github.com/BInBilibili/diaotutieba.git"
    REPO_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 项目根目录
    
    safe_print("\n===== 开始上传到GitHub仓库 =====")
    safe_print(f"仓库路径: {REPO_PATH}")
    
    try:
        # 切换到仓库目录
        os.chdir(REPO_PATH)
        safe_print(f"已切换到目录: {os.getcwd()}")
        
        # 检查是否为Git仓库
        is_new_repo = False
        if not os.path.exists(".git"):
            is_new_repo = True
            safe_print("初始化Git仓库...")
            result = run_git_command(["init"], cwd=REPO_PATH)
            if result and result.returncode == 0:
                safe_print("OK Git仓库初始化成功")
            else:
                safe_print("ERROR Git仓库初始化失败")
                return
            
            # 配置用户信息
            result = run_git_command(["config", "user.name", "BInBilibili"], cwd=REPO_PATH)
            if result and result.returncode == 0:
                safe_print("OK Git用户名配置完成")
            
            result = run_git_command(["config", "user.email", "your.email@example.com"], cwd=REPO_PATH)
            if result and result.returncode == 0:
                safe_print("OK Git邮箱配置完成")
            
            # 添加远程仓库
            safe_print("添加远程仓库...")
            result = run_git_command(["remote", "add", "origin", REPO_URL], cwd=REPO_PATH)
            if result and result.returncode == 0:
                safe_print("OK 远程仓库添加成功")
            else:
                safe_print("ERROR 远程仓库添加失败")
                return
        else:
            safe_print("OK Git仓库已存在")
        
        # 检查远程仓库
        safe_print("\n检查远程仓库...")
        result = run_git_command(["remote", "-v"], cwd=REPO_PATH)
        if result and result.returncode == 0:
            safe_print("远程仓库信息:")
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    safe_print(f"  {line}")
        
        # 检查当前分支
        safe_print("\n检查当前分支...")
        result = run_git_command(["branch"], cwd=REPO_PATH)
        current_branch = ""
        if result and result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.startswith('* '):
                    current_branch = line[2:].strip()
                    break
            safe_print(f"当前分支: {current_branch if current_branch else '无分支'}")
        
        # 处理分支
        target_branch = "main"
        if not current_branch:
            # 没有分支，创建main分支
            safe_print(f"创建{target_branch}分支...")
            result = run_git_command(["checkout", "-b", target_branch], cwd=REPO_PATH)
            if result and result.returncode == 0:
                safe_print(f"OK {target_branch}分支创建成功")
                current_branch = target_branch
            else:
                safe_print(f"ERROR {target_branch}分支创建失败")
                if result and result.stderr:
                    safe_print(f"  错误: {result.stderr}")
        elif current_branch != target_branch:
            # 分支不匹配，切换到main分支
            safe_print(f"切换到{target_branch}分支...")
            # 先尝试创建main分支
            result = run_git_command(["checkout", "-b", target_branch], cwd=REPO_PATH)
            if result and result.returncode != 0:
                # 如果已存在，直接切换
                result = run_git_command(["checkout", target_branch], cwd=REPO_PATH)
            if result and result.returncode == 0:
                safe_print(f"OK 切换到{target_branch}分支成功")
                current_branch = target_branch
            else:
                safe_print(f"ERROR 切换分支失败")
                if result and result.stderr:
                    safe_print(f"  错误: {result.stderr}")
        
        # 确保仓库只包含必要文件
        safe_print("\n检查仓库文件...")
        
        # 确保README.md存在
        readme_path = os.path.join(REPO_PATH, "README.md")
        if not os.path.exists(readme_path):
            readme_content = "# 吊图吧爬虫数据\n\n本仓库用于存储从吊图吧爬取的帖子数据。\n\n## 项目说明\n- 使用 TiebaScraper 爬取贴吧内容\n- 只存储爬取的帖子数据\n- 定期更新最新内容\n"
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(readme_content)
            safe_print("OK 创建README.md文件")
        
        # 复制帖子到仓库根目录的scraped_data目录
        safe_print("\n复制帖子到仓库目录...")
        import shutil
        
        # 确保仓库根目录有scraped_data目录
        repo_scraped_dir = os.path.join(REPO_PATH, "scraped_data")
        safe_print(f"仓库scraped_data目录: {repo_scraped_dir}")
        os.makedirs(repo_scraped_dir, exist_ok=True)
        
        # 检查源帖子目录
        safe_print(f"要复制的帖子目录数量: {len(post_dirs)}")
        for post_dir in post_dirs:
            safe_print(f"  源目录: {post_dir}")
            safe_print(f"  是否存在: {os.path.exists(post_dir)}")
        
        # 复制帖子目录
        for post_dir in post_dirs:
            # 获取帖子目录名称
            post_dir_name = os.path.basename(post_dir)
            # 目标路径
            target_path = os.path.join(repo_scraped_dir, post_dir_name)
            
            safe_print(f"复制: {post_dir} -> {target_path}")

            # Windows 文件系统不区分大小写，需用 normcase+realpath 判断源和目标是否同一目录
            if os.path.normcase(os.path.realpath(post_dir)) == os.path.normcase(os.path.realpath(target_path)):
                safe_print(f"  跳过: 源与目标为同一目录 (Windows 路径大小写差异)")
                continue

            # 如果目标存在，先删除
            if os.path.exists(target_path):
                safe_print(f"  目标已存在，删除旧目录")
                shutil.rmtree(target_path, ignore_errors=True)

            # 复制帖子目录
            if os.path.exists(post_dir):
                shutil.copytree(post_dir, target_path)
                safe_print(f"OK 复制帖子成功: {post_dir_name}")
            else:
                safe_print(f"ERROR 源目录不存在: {post_dir}")
        
        # 验证复制结果
        safe_print(f"\n验证仓库scraped_data目录内容:")
        if os.path.exists(repo_scraped_dir):
            items = os.listdir(repo_scraped_dir)
            safe_print(f"  目录存在，包含 {len(items)} 个项目")
            for item in items:
                safe_print(f"    - {item}")
        else:
            safe_print(f"  目录不存在: {repo_scraped_dir}")
        
        # 压缩大文件
        compress_large_files(repo_scraped_dir, COMPRESS_THRESHOLD_MB, COMPRESS_DELETE_ORIGINAL)
        
        # 只添加scraped_data目录和README.md
        safe_print("\n添加文件到暂存区...")
        
        # 添加README.md
        result = run_git_command(["add", "README.md"], cwd=REPO_PATH)
        if result and result.returncode == 0:
            safe_print("OK 添加README.md成功")
        
        # 添加scraped_data目录（使用-f强制添加，即使被.gitignore忽略）
        result = run_git_command(["add", "-f", "scraped_data"], cwd=REPO_PATH)
        if result and result.returncode == 0:
            safe_print("OK 添加scraped_data目录成功")
        else:
            safe_print("ERROR 添加scraped_data目录失败")
            if result and result.stderr:
                safe_print(f"  错误: {result.stderr}")
        
        # 检查状态
        result = run_git_command(["status"], cwd=REPO_PATH)
        if result and result.returncode == 0:
            safe_print("\nGit状态:")
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    safe_print(f"  {line}")
        
        # 提交更改
        commit_message = f"更新爬取的帖子数据 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        safe_print(f"\n提交更改: {commit_message}")
        result = run_git_command(["commit", "-m", commit_message], cwd=REPO_PATH)
        if result and result.returncode == 0:
            safe_print("OK 提交成功")
        else:
            safe_print("ERROR 提交失败（可能没有更改需要提交）")
            if result and result.stderr:
                safe_print(f"  错误: {result.stderr}")
        
        # 推送到远程仓库
        safe_print("\n推送到远程仓库...")
        
        # 先尝试获取远程分支信息
        result = run_git_command(["fetch", "origin"], cwd=REPO_PATH)
        
        # 检查远程是否有main分支
        result = run_git_command(["ls-remote", "--heads", "origin", target_branch], cwd=REPO_PATH)
        has_remote_main = result and result.returncode == 0 and result.stdout.strip()
        
        if has_remote_main:
            # 远程有main分支，先合并
            safe_print(f"远程存在{target_branch}分支，尝试合并...")
            result = run_git_command(["pull", "origin", target_branch, "--allow-unrelated-histories"], cwd=REPO_PATH)
            if result and result.returncode == 0:
                safe_print("OK 合并成功")
            else:
                safe_print("⚠ 合并可能有冲突，继续推送...")
        
        # 推送（设置5分钟超时，处理大文件上传）
        result = run_git_command(["push", "-u", "origin", current_branch], cwd=REPO_PATH, timeout=300)
        if result and result.returncode == 0:
            safe_print("✓ 推送成功！")
            safe_print("\n推送结果:")
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    safe_print(f"  {line}")
        else:
            safe_print("✗ 推送失败")
            if result and result.stderr:
                safe_print(f"  错误: {result.stderr}")
            
            # 显示手动推送说明
            safe_print("\n=== 手动推送说明 ===")
            safe_print("由于安全原因，GitHub阻止了包含令牌的推送")
            safe_print("请按照以下步骤手动推送：")
            safe_print("1. 打开命令提示符或Git Bash")
            safe_print(f"2. 切换到目录: {REPO_PATH}")
            safe_print("3. 运行命令: git push -u origin main")
            safe_print("4. 按照GitHub提示输入用户名和密码（密码使用个人访问令牌）")
        
        safe_print("\n===== 上传到GitHub仓库完成 =====")
        
    except Exception as e:
        safe_print(f"上传失败: {e}")


async def crawl_forum(client, forum_name, start_index, end_index):
    """
    爬取单个贴吧的帖子
    
    Args:
        client: aiotieba客户端
        forum_name: 贴吧名称
        start_index: 起始帖子序号（从1开始，置顶帖不算）
        end_index: 结束帖子序号（包含）
    
    Returns:
        list: 爬取的帖子目录列表
    """
    crawl_count = end_index - start_index + 1
    print(f"\n{'='*50}")
    print(f"开始爬取贴吧: {forum_name}吧")
    print(f"计划爬取范围: 第{start_index}个 到 第{end_index}个帖子（共{crawl_count}个）")
    print(f"{'='*50}")
    
    # 获取帖子列表
    threads = await client.get_threads(forum_name)
    
    # 配置爬取范围
    # 注意：置顶帖不算在内，所以直接从0开始索引
    # start_index和end_index是从1开始的，需要转换为0开始的索引
    thread_range = [start_index - 1, end_index]  # 例如：(1, 3) -> 索引[0:3]，即第1、2、3个
    
    # 准备保存的帖子数据
    tids = []
    thread_info = {}
    for thread in threads[thread_range[0]:thread_range[1]]:
        tids.append(thread.tid)
        thread_info[thread.tid] = thread.title
        print(f"已获取帖子: {thread.title} (ID: {thread.tid})")
    
    # 保存tid到文件（使用贴吧名作为文件名）
    filename = f"tid_{forum_name}.json"
    save_tids_to_file(tids, filename)
    print(f"从 {forum_name}吧 获取 {len(tids)} 个帖子")
    
    # 跟踪新爬取的帖子目录
    new_post_dirs = []
    
    # 依次爬取每个tid
    for i, tid in enumerate(tids, 1):
        print(f"\n----- 开始爬取第 {i}/{len(tids)} 个帖子 (tid: {tid}) -----")
        try:
            # 直接await scrape(tid)，避免事件循环嵌套
            await scrape(tid)
            print(f"第 {i} 个帖子爬取完成 (tid: {tid})")
            
            # 检查scraped_data目录（帖子实际保存的位置）
            scraped_dir = os.path.join(os.getcwd(), "scraped_data")
            if os.path.exists(scraped_dir):
                # 列出scraped_data目录中的所有子目录
                for item in os.listdir(scraped_dir):
                    item_path = os.path.join(scraped_dir, item)
                    if os.path.isdir(item_path) and f"[{tid}]" in item:
                        new_post_dirs.append(item_path)
                        print(f"找到帖子目录: {item_path}")
        except Exception as e:
            print(f"爬取第 {i} 个帖子时出错 (tid: {tid}): {e}")
        
        # 爬取间隔，避免请求过快
        if i < len(tids):
            print("等待2秒后继续...")
            await asyncio.sleep(2)
    
    print(f"\n{forum_name}吧 爬取完成！共 {len(tids)} 个帖子")
    return new_post_dirs


async def main():
    """主函数：获取tid并爬取帖子"""
    
    # 设置默认不爬取头像
    ScrapeConfig.DOWNLOAD_USER_AVATAR_MODE = DownloadUserAvatarMode.NONE
    print("已设置默认不爬取头像")
    
    # 跟踪所有新爬取的帖子目录
    all_post_dirs = []
    
    async with tb.Client() as client:
        # 遍历所有配置的贴吧
        for forum_index, forum_config in enumerate(FORUMS, 1):
            # 解析配置：支持 (贴吧名, 起始序号, 结束序号) 格式
            if len(forum_config) == 3:
                forum_name, start_index, end_index = forum_config
            else:
                # 兼容旧格式：(贴吧名, 数量) -> 转换为 (贴吧名, 1, 数量)
                forum_name, crawl_count = forum_config
                start_index, end_index = 1, crawl_count
            
            print(f"\n\n[进度 {forum_index}/{len(FORUMS)}] 正在处理第 {forum_index} 个贴吧")
            
            try:
                # 爬取当前贴吧
                post_dirs = await crawl_forum(client, forum_name, start_index, end_index)
                all_post_dirs.extend(post_dirs)
                
                # 贴吧之间的间隔
                if forum_index < len(FORUMS):
                    print(f"\n等待5秒后处理下一个贴吧...")
                    await asyncio.sleep(5)
                    
            except Exception as e:
                print(f"爬取 {forum_name}吧 时出错: {e}")
                continue
    
    print(f"\n\n{'='*50}")
    print(f"所有贴吧爬取完成！")
    print(f"总共爬取了 {len(all_post_dirs)} 个帖子")
    print(f"{'='*50}")
    
    # 根据配置决定是否上传到GitHub仓库
    if UPLOAD_TO_GITHUB:
        if all_post_dirs:
            print(f"\n准备上传 {len(all_post_dirs)} 个新爬取的帖子目录")
            upload_to_github(all_post_dirs)
        else:
            print("\n没有新爬取的帖子目录需要上传")
    else:
        print("\n[配置] 已跳过GitHub上传（UPLOAD_TO_GITHUB = False）")


if __name__ == "__main__":
    asyncio.run(main())