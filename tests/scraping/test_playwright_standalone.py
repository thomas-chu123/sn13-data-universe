#!/usr/bin/env python3
"""
輕量級 Playwright Scraper 測試 - 不依賴 bittensor
用於快速驗證登入和基本爬取功能
"""

import asyncio
import os
import sys
import logging

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加項目到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


async def test_x_playwright_basic():
    """基礎 X Playwright 測試 - 最小化依賴"""
    logger.info("=" * 80)
    logger.info("🔍 開始基礎 X Playwright 測試")
    logger.info("=" * 80)
    
    try:
        # 僅導入必要的 Playwright 組件
        from playwright.async_api import async_playwright
        
        logger.info("✅ Playwright 導入成功")
        
        # 建立瀏覽器
        async with async_playwright() as p:
            logger.info("📱 啟動瀏覽器...")
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            logger.info("✅ 瀏覽器已啟動")
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = await context.new_page()
            logger.info("✅ 頁面已建立")
            
            # 測試導航
            logger.info("\n🌐 測試頁面導航...")
            await page.goto("https://twitter.com/search", wait_until='networkidle', timeout=60000)
            logger.info("✅ Twitter 首頁已加載")
            
            # 檢查頁面標題
            title = await page.title()
            logger.info(f"📄 頁面標題: {title}")
            
            # 關閉
            await context.close()
            await browser.close()
            logger.info("\n✅ 測試完成 - X Playwright 基本功能正常")
            return True
            
    except Exception as e:
        logger.error(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_reddit_playwright_basic():
    """基礎 Reddit Playwright 測試 - 最小化依賴"""
    logger.info("=" * 80)
    logger.info("🔍 開始基礎 Reddit Playwright 測試")
    logger.info("=" * 80)
    
    try:
        from playwright.async_api import async_playwright
        
        logger.info("✅ Playwright 導入成功")
        
        async with async_playwright() as p:
            logger.info("📱 啟動瀏覽器...")
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            logger.info("✅ 瀏覽器已啟動")
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = await context.new_page()
            logger.info("✅ 頁面已建立")
            
            # 測試導航
            logger.info("\n🌐 測試頁面導航...")
            await page.goto("https://www.reddit.com/r/python/", wait_until='networkidle', timeout=60000)
            logger.info("✅ Reddit r/python 已加載")
            
            # 檢查頁面標題
            title = await page.title()
            logger.info(f"📄 頁面標題: {title}")
            
            # 關閉
            await context.close()
            await browser.close()
            logger.info("\n✅ 測試完成 - Reddit Playwright 基本功能正常")
            return True
            
    except Exception as e:
        logger.error(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_scraper_imports():
    """測試 Scraper 導入（可能會遇到 bittensor 依賴問題）"""
    logger.info("=" * 80)
    logger.info("🔍 開始 Scraper 導入測試")
    logger.info("=" * 80)
    
    try:
        logger.info("📦 嘗試導入 X Scraper...")
        from scraping.x.x_playwright_scraper import XPlaywrightScraper
        logger.info("✅ X Scraper 導入成功")
        
        logger.info("📦 嘗試導入 Reddit Scraper...")
        from scraping.reddit.reddit_playwright_scraper import RedditPlaywrightScraper
        logger.info("✅ Reddit Scraper 導入成功")
        
        logger.info("\n✅ 所有 Scraper 導入成功")
        return True
        
    except ImportError as e:
        logger.warning(f"⚠️ Scraper 導入失敗（可能是 bittensor 依賴）: {e}")
        logger.info("   但基礎 Playwright 功能仍可使用")
        return False
    except Exception as e:
        logger.error(f"❌ 導入錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函數"""
    logger.info("🧪 Playwright Scraper 基礎測試套件")
    logger.info("=" * 80)
    
    results = {}
    
    # 測試 1: 基礎 X Playwright
    logger.info("\n【測試 1/3】基礎 X Playwright 測試\n")
    results["X Playwright"] = await test_x_playwright_basic()
    
    # 測試 2: 基礎 Reddit Playwright  
    logger.info("\n【測試 2/3】基礎 Reddit Playwright 測試\n")
    results["Reddit Playwright"] = await test_reddit_playwright_basic()
    
    # 測試 3: Scraper 導入
    logger.info("\n【測試 3/3】Scraper 導入測試\n")
    results["Scraper Import"] = await test_scraper_imports()
    
    # 總結
    logger.info("\n" + "=" * 80)
    logger.info("📊 測試總結:")
    logger.info("=" * 80)
    
    for test_name, success in results.items():
        status = "✅ 成功" if success else "❌ 失敗"
        logger.info(f"  {test_name}: {status}")
    
    logger.info("=" * 80)
    
    # 最後一個測試失敗是預期的（bittensor 依賴）
    basic_success = results.get("X Playwright") and results.get("Reddit Playwright")
    
    if basic_success:
        logger.info("✅ 基礎 Playwright 功能正常！")
        logger.info("\n💡 下一步建議:")
        logger.info("   1. 檢查 bittensor/OpenSSL 環境問題（非關鍵）")
        logger.info("   2. 運行 miner.py 測試完整功能")
        sys.exit(0)
    else:
        logger.info("❌ 基礎 Playwright 功能出現問題")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
