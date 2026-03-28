import subprocess
import os
import sys

# 设置默认编码为utf-8
sys.stdout.reconfigure(encoding='utf-8')

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

def test_git():
    """
    测试Git命令是否正常工作
    """
    print("===== 测试Git命令 ======")
    
    # 检查Git是否安装
    result = run_git_command(["--version"])
    if result and result.returncode == 0:
        print(f"✓ Git版本: {result.stdout.strip()}")
    else:
        print("✗ Git未安装或无法运行")
        return False
    
    # 测试git config
    print("\n测试Git配置...")
    result = run_git_command(["config", "--global", "user.name"])
    if result and result.returncode == 0:
        print(f"✓ Git用户名: {result.stdout.strip()}")
    else:
        print("✗ Git用户名未配置")
    
    result = run_git_command(["config", "--global", "user.email"])
    if result and result.returncode == 0:
        print(f"✓ Git邮箱: {result.stdout.strip()}")
    else:
        print("✗ Git邮箱未配置")
    
    # 测试GitHub连接
    print("\n测试GitHub连接...")
    github_url = "https://github.com/BInBilibili/diaotutieba"
    result = run_git_command(["ls-remote", github_url])
    
    if result and result.returncode == 0:
        print(f"✓ GitHub连接成功")
        print("  远程仓库引用:")
        lines = result.stdout.strip().split('\n')
        for line in lines[:3]:
            if line.strip():
                print(f"    {line}")
        if len(lines) > 3:
            print(f"    ... 共 {len(lines)} 行")
    else:
        print(f"✗ GitHub连接失败")
        if result and result.stderr:
            print(f"  错误: {result.stderr}")
    
    print("\n===== Git测试完成 ======")
    return True

if __name__ == "__main__":
    test_git()