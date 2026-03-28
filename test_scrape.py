# 直接爬取指定帖子的脚本
import asyncio
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from modules.scrape_module import scrape

async def main():
    # 要爬取的帖子tid
    tid = 10580861955
    print(f"开始爬取帖子: {tid}")
    await scrape(tid)
    print("爬取完成！")

if __name__ == "__main__":
    asyncio.run(main())