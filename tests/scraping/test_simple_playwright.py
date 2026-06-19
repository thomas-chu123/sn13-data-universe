#!/usr/bin/env python3
"""
超級簡化的 Playwright 診斷測試
"""

import asyncio
import logging

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


async def main():
    from playwright.async_api import async_playwright
    
    logger.info("=" * 60)
    logger.info("🧪 Playwright 診斷測試")
    logger.info("=" * 60)
    
    logger.info("\n1️⃣ 創建 async_playwright 實例...")
    try:
        pw = await async_playwright().start()
        logger.info("✅ async_playwright 已啟動")
        
        logger.info("\n2️⃣ 啟動 Chromium 瀏覽器...")
        browser = await pw.chromium.launch()
        logger.info("✅ Chromium 已啟動")
        
        logger.info("\n3️⃣ 創建新標籤頁...")
        page = await browser.new_page()
        logger.info("✅ 新標籤頁已建立")
        
        logger.info("\n4️⃣ 導航到 Google...")
        await page.goto("https://www.google.com", timeout=10000)
        logger.info("✅ 已導航到 Google")
        
        logger.info("\n5️⃣ 獲取頁面標題...")
        title = await page.title()
        logger.info(f"✅ 頁面標題: {title}")
        
        logger.info("\n6️⃣ 關閉頁面...")
        await page.close()
        logger.info("✅ 頁面已關閉")
        
        logger.info("\n7️⃣ 關閉瀏覽器...")
        await browser.close()
        logger.info("✅ 瀏覽器已關閉")
        
        logger.info("\n8️⃣ 停止 async_playwright...")
        await pw.stop()
        logger.info("✅ async_playwright 已停止")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ 所有測試通過！Playwright 功能正常")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        

if __name__ == "__main__":
    asyncio.run(main())
