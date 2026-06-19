#!/usr/bin/env python3
"""
快速測試 Playwright Scraper 登入和數據獲取
使用: python test_playwright_quick.py [x|reddit|all]
"""

import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 設置路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraping.x.x_playwright_scraper import XPlaywrightScraper
from scraping.reddit.reddit_playwright_scraper import RedditPlaywrightScraper


async def test_x_scraper():
    """測試 X Scraper"""
    logger.info("=" * 60)
    logger.info("🔍 開始測試 X (Twitter) Playwright Scraper")
    logger.info("=" * 60)
    
    scraper = XPlaywrightScraper()
    
    try:
        # 1. 測試頁面建立和登入
        logger.info("\n📝 [1/3] 測試頁面建立和自動登入...")
        page = await scraper._get_page()
        assert page is not None
        logger.info("✅ 頁面建立成功")
        
        username = os.getenv('TWITTER_USERNAME')
        password = os.getenv('TWITTER_PASSWORD')
        if username and password:
            logger.info(f"🔐 嘗試登入 ({username})...")
            await scraper._auto_login()
            if scraper.is_logged_in:
                logger.info("✅ 自動登入成功！")
            else:
                logger.warning("⚠️ 自動登入失敗，將使用未登入模式")
        else:
            logger.warning("⚠️ 未設置認證資訊，使用未登入模式")
        
        # 2. 測試搜尋功能
        logger.info("\n📝 [2/3] 測試搜尋推文功能...")
        logger.info("🔍 搜尋關鍵字: 'bitcoin'...")
        tweets = await scraper._search_tweets(
            query="bitcoin lang:en -is:retweet",
            max_results=3
        )
        logger.info(f"✅ 搜尋成功，獲得 {len(tweets)} 條推文")
        
        if tweets:
            for i, tweet in enumerate(tweets[:3], 1):
                logger.info(f"\n   推文 {i}:")
                logger.info(f"   👤 用戶: @{tweet.username}")
                logger.info(f"   📝 內容: {tweet.text[:100]}...")
                logger.info(f"   🔗 URL: {tweet.url}")
        
        # 3. 測試 on_demand_scrape 功能
        logger.info("\n📝 [3/3] 測試 on_demand_scrape 功能...")
        logger.info("🔍 執行 on_demand_scrape (keywords=['crypto'], limit=3)...")
        result = await scraper.on_demand_scrape(
            keywords=["crypto"],
            keyword_mode="all",
            limit=3
        )
        logger.info(f"✅ on_demand_scrape 成功，獲得 {len(result)} 條推文")
        
        if result:
            for i, tweet in enumerate(result[:2], 1):
                logger.info(f"\n   推文 {i}:")
                logger.info(f"   👤 用戶: @{tweet.username}")
                logger.info(f"   📝 內容: {tweet.text[:100]}...")
        
        # 驗證資料
        logger.info("\n📝 驗證數據完整性...")
        if result:
            validation_results = await scraper.validate(result)
            valid_count = sum(1 for v in validation_results if v.are_valid)
            logger.info(f"✅ 驗證完成: {valid_count}/{len(validation_results)} 個有效資料")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ X Scraper 測試完成！")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ X Scraper 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            await scraper._close_browser()
        except Exception as e:
            logger.warning(f"清理失敗: {e}")


async def test_reddit_scraper():
    """測試 Reddit Scraper"""
    logger.info("=" * 60)
    logger.info("🔍 開始測試 Reddit Playwright Scraper")
    logger.info("=" * 60)
    
    scraper = RedditPlaywrightScraper()
    
    try:
        # 1. 測試頁面建立和登入
        logger.info("\n📝 [1/3] 測試頁面建立和自動登入...")
        page = await scraper._get_page()
        assert page is not None
        logger.info("✅ 頁面建立成功")
        
        username = os.getenv('REDDIT_USERNAME')
        password = os.getenv('REDDIT_PASSWORD')
        if username and password:
            logger.info(f"🔐 嘗試登入 ({username})...")
            await scraper._auto_login()
            if scraper.is_logged_in:
                logger.info("✅ 自動登入成功！")
            else:
                logger.warning("⚠️ 自動登入失敗，將使用未登入模式")
        else:
            logger.warning("⚠️ 未設置認證資訊，使用未登入模式")
        
        # 2. 測試搜尋功能
        logger.info("\n📝 [2/3] 測試搜尋 Subreddit 功能...")
        logger.info("📍 搜尋 Subreddit: 'python'...")
        posts = await scraper._search_subreddit_posts(
            subreddit="python",
            max_results=3,
            sort="hot"
        )
        logger.info(f"✅ 搜尋成功，獲得 {len(posts)} 個帖子")
        
        if posts:
            for i, post in enumerate(posts[:3], 1):
                logger.info(f"\n   帖子 {i}:")
                logger.info(f"   👤 用戶: {post.username}")
                logger.info(f"   📌 標題: {post.title[:80]}...")
                logger.info(f"   📝 內容: {(post.body or '(無正文)')[:80]}...")
                logger.info(f"   🔗 URL: {post.url}")
        
        # 3. 測試 on_demand_scrape 功能
        logger.info("\n📝 [3/3] 測試 on_demand_scrape 功能...")
        logger.info("📍 執行 on_demand_scrape (subreddit='python', limit=3)...")
        result = await scraper.on_demand_scrape(
            subreddit="python",
            limit=3
        )
        logger.info(f"✅ on_demand_scrape 成功，獲得 {len(result)} 個帖子")
        
        if result:
            for i, post in enumerate(result[:2], 1):
                logger.info(f"\n   帖子 {i}:")
                logger.info(f"   👤 用戶: {post.username}")
                logger.info(f"   📌 標題: {post.title[:80]}...")
        
        # 驗證資料
        logger.info("\n📝 驗證數據完整性...")
        if result:
            validation_results = await scraper.validate(result)
            valid_count = sum(1 for v in validation_results if v.are_valid)
            logger.info(f"✅ 驗證完成: {valid_count}/{len(validation_results)} 個有效資料")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Reddit Scraper 測試完成！")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Reddit Scraper 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            await scraper._close_browser()
        except Exception as e:
            logger.warning(f"清理失敗: {e}")


async def main():
    """主函數"""
    # 讀取環境變量
    logger.info("🔧 環境設置:")
    logger.info(f"   TWITTER_USERNAME: {os.getenv('TWITTER_USERNAME') or '未設置'}")
    logger.info(f"   TWITTER_PASSWORD: {'*' * len(os.getenv('TWITTER_PASSWORD', ''))}") if os.getenv('TWITTER_PASSWORD') else logger.info("   TWITTER_PASSWORD: 未設置")
    logger.info(f"   REDDIT_USERNAME: {os.getenv('REDDIT_USERNAME') or '未設置'}")
    logger.info(f"   REDDIT_PASSWORD: {'*' * len(os.getenv('REDDIT_PASSWORD', ''))}") if os.getenv('REDDIT_PASSWORD') else logger.info("   REDDIT_PASSWORD: 未設置")
    
    # 決定測試範圍
    test_target = sys.argv[1].lower() if len(sys.argv) > 1 else "all"
    
    results = {}
    
    if test_target in ["x", "all"]:
        logger.info("\n" + "=" * 60)
        results["X"] = await test_x_scraper()
        await asyncio.sleep(2)  # 等待一下再測試下一個
    
    if test_target in ["reddit", "all"]:
        logger.info("\n" + "=" * 60)
        results["Reddit"] = await test_reddit_scraper()
    
    # 顯示總結
    logger.info("\n" + "=" * 60)
    logger.info("📊 測試總結:")
    logger.info("=" * 60)
    for scraper, success in results.items():
        status = "✅ 成功" if success else "❌ 失敗"
        logger.info(f"  {scraper}: {status}")
    
    all_success = all(results.values())
    logger.info("=" * 60)
    if all_success:
        logger.info("✅ 全部測試成功！")
        sys.exit(0)
    else:
        logger.info("❌ 部分測試失敗")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
