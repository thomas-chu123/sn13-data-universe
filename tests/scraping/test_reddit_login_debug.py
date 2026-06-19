#!/usr/bin/env python3
"""
Reddit 登入診斷工具 - 非 headless 模式用於可視化調試
使用: python test_reddit_login_debug.py
"""

import asyncio
import os
import sys
import logging
from datetime import datetime

# 設置日誌
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 設置路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from playwright.async_api import async_playwright


async def test_reddit_login_visual():
    """非 headless 模式的 Reddit 登入測試"""
    logger.info("=" * 80)
    logger.info("🔍 Reddit 登入可視化診斷")
    logger.info("=" * 80)
    
    reddit_username = os.getenv('REDDIT_USERNAME')
    reddit_password = os.getenv('REDDIT_PASSWORD')
    
    if not reddit_username or not reddit_password:
        logger.error("❌ 環境變數未設置: REDDIT_USERNAME 或 REDDIT_PASSWORD")
        return
    
    logger.info(f"使用帳號: {reddit_username}")
    logger.info("瀏覽器將在非 headless 模式下開啟，以便觀察登入過程")
    logger.info("按 Enter 繼續...")
    input()
    
    async with async_playwright() as p:
        try:
            # 使用 Firefox，非 headless 模式
            logger.info("🚀 啟動 Firefox...")
            browser = await p.firefox.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            # 設置超時
            page.set_default_timeout(30000)
            page.set_default_navigation_timeout(30000)
            
            logger.info("📍 導航到 Reddit 登入頁面...")
            await page.goto("https://www.reddit.com/login", wait_until='networkidle')
            logger.info("✅ 頁面已加載")
            
            # 等待用戶名輸入框
            logger.info("⏳ 等待用戶名輸入框...")
            try:
                await page.wait_for_selector('input[name="username"]', timeout=10000)
                logger.info("✅ 用戶名輸入框已出現")
            except Exception as e:
                logger.warning(f"⚠️ 用戶名輸入框未找到: {e}")
                logger.warning("📸 頁面標題: " + page.title())
                logger.warning("📍 當前 URL: " + page.url)
                await asyncio.sleep(5)
            
            # 輸入用戶名
            logger.info("📝 輸入用戶名...")
            await page.fill('input[name="username"]', reddit_username)
            logger.info("✅ 用戶名已輸入")
            await asyncio.sleep(1)
            
            # 輸入密碼
            logger.info("📝 輸入密碼...")
            await page.fill('input[name="password"]', reddit_password)
            logger.info("✅ 密碼已輸入")
            await asyncio.sleep(1)
            
            # 點擊登入按鈕
            logger.info("🔍 查找登入按鈕...")
            login_button = await page.query_selector('button:has-text("Log in")')
            if not login_button:
                login_button = await page.query_selector('button[type="submit"]')
            
            if login_button:
                logger.info("✅ 登入按鈕已找到，點擊...")
                await login_button.click()
                logger.info("🕐 點擊後等待 5 秒... 觀察頁面變化")
                await asyncio.sleep(5)
            else:
                logger.error("❌ 找不到登入按鈕")
            
            # 檢查當前狀態
            logger.info("\n" + "=" * 80)
            logger.info("📍 登入狀態檢查:")
            logger.info("=" * 80)
            current_url = page.url
            logger.info(f"當前 URL: {current_url}")
            logger.info(f"頁面標題: {page.title()}")
            
            # 等待更多時間以觀察 js_challenge
            logger.info("\n⏳ 等待 10 秒以允許 JavaScript 挑戰完成...")
            await asyncio.sleep(10)
            
            current_url = page.url
            logger.info(f"\n10 秒後 URL: {current_url}")
            logger.info(f"10 秒後頁面標題: {page.title()}")
            
            # 檢查頁面上的元素
            logger.info("\n🔍 檢查頁面元素:")
            
            # 檢查是否有錯誤訊息
            error_msgs = await page.query_selector_all('[class*="error"], [class*="Error"]')
            if error_msgs:
                logger.warning(f"⚠️ 找到 {len(error_msgs)} 個錯誤元素")
                for i, elem in enumerate(error_msgs):
                    text = await elem.text_content()
                    logger.warning(f"  錯誤 {i+1}: {text[:100]}")
            
            # 檢查是否有驗證碼
            captcha = await page.query_selector('iframe[title*="reCAPTCHA"], [class*="captcha"]')
            if captcha:
                logger.warning("⚠️ 檢測到驗證碼 - 可能需要手動完成")
            
            # 檢查是否有登入按鈕（表示仍在登入頁面）
            login_btn_still = await page.query_selector('button:has-text("Log in")')
            if login_btn_still:
                logger.warning("⚠️ 仍然看到登入按鈕 - 登入可能未成功")
            else:
                logger.info("✅ 登入按鈕已消失 - 登入可能成功")
            
            # 保持窗口開啟，讓用戶可以觀察
            logger.info("\n" + "=" * 80)
            logger.info("✅ 診斷完成")
            logger.info("=" * 80)
            logger.info("瀏覽器窗口仍保持開啟中...")
            logger.info("按 Enter 關閉瀏覽器...")
            input()
            
            await browser.close()
            
        except Exception as e:
            logger.error(f"❌ 異常: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_reddit_login_visual())
