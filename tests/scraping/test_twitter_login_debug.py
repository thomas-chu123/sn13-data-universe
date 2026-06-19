#!/usr/bin/env python3
"""
Twitter/X 登入診斷工具 - 非 headless 模式用於可視化調試
使用: python test_twitter_login_debug.py
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


async def test_twitter_login_visual():
    """非 headless 模式的 Twitter 登入測試"""
    logger.info("=" * 80)
    logger.info("🔍 Twitter/X 登入可視化診斷")
    logger.info("=" * 80)
    
    twitter_username = os.getenv('TWITTER_USERNAME')
    twitter_password = os.getenv('TWITTER_PASSWORD')
    
    if not twitter_username or not twitter_password:
        logger.error("❌ 環境變數未設置: TWITTER_USERNAME 或 TWITTER_PASSWORD")
        return
    
    logger.info(f"使用帳號: {twitter_username}")
    logger.info("瀏覽器將在非 headless 模式下開啟，以便觀察登入過程")
    logger.info("按 Enter 繼續...")
    input()
    
    async with async_playwright() as p:
        try:
            # 使用 Firefox，非 headless 模式
            logger.info("🚀 啟動 Firefox...")
            browser = await p.firefox.launch(headless=False)
            context = await browser.new_context(viewport={'width': 1400, 'height': 900})
            page = await context.new_page()
            
            # 設置超時
            page.set_default_timeout(30000)
            page.set_default_navigation_timeout(30000)
            
            logger.info("📍 導航到 Twitter 登入頁面...")
            await page.goto("https://twitter.com/i/flow/login", wait_until='networkidle')
            logger.info("✅ 登入頁面已加載")
            await asyncio.sleep(2)
            
            # 檢查頁面上的輸入框
            logger.info("\n" + "=" * 80)
            logger.info("🔍 檢查頁面上的所有輸入框:")
            logger.info("=" * 80)
            
            inputs = await page.query_selector_all('input')
            logger.info(f"找到 {len(inputs)} 個輸入框:")
            
            for i, inp in enumerate(inputs):
                # 獲取各種屬性
                input_type = await inp.get_attribute('type')
                placeholder = await inp.get_attribute('placeholder')
                name = await inp.get_attribute('name')
                autocomplete = await inp.get_attribute('autocomplete')
                aria_label = await inp.get_attribute('aria-label')
                
                logger.info(f"\n  輸入框 {i+1}:")
                logger.info(f"    type: {input_type}")
                logger.info(f"    name: {name}")
                logger.info(f"    autocomplete: {autocomplete}")
                logger.info(f"    placeholder: {placeholder}")
                logger.info(f"    aria-label: {aria_label}")
            
            # 嘗試不同的選擇器
            logger.info("\n" + "=" * 80)
            logger.info("🔍 嘗試不同的選擇器:")
            logger.info("=" * 80)
            
            selectors_to_try = [
                'input[autocomplete="username"]',
                'input[name="text"]',
                'input[type="text"]',
                'input[type="email"]',
                'input[aria-label*="Phone"]',
                'input[aria-label*="email"]',
                'input[aria-label*="username"]',
                'input[autocomplete="email"]',
                'input[placeholder*="Phone"]',
            ]
            
            for selector in selectors_to_try:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        logger.info(f"✅ 找到: {selector}")
                    else:
                        logger.warning(f"❌ 未找到: {selector}")
                except Exception as e:
                    logger.warning(f"❌ 錯誤查詢 {selector}: {e}")
            
            # 檢查頁面上的按鈕
            logger.info("\n" + "=" * 80)
            logger.info("🔍 檢查頁面上的按鈕:")
            logger.info("=" * 80)
            
            buttons = await page.query_selector_all('button')
            logger.info(f"找到 {len(buttons)} 個按鈕:")
            
            for i, btn in enumerate(buttons[:5]):  # 只顯示前 5 個
                btn_text = await btn.text_content()
                btn_type = await btn.get_attribute('type')
                aria_label = await btn.get_attribute('aria-label')
                
                logger.info(f"\n  按鈕 {i+1}:")
                logger.info(f"    text: {btn_text[:50] if btn_text else 'N/A'}")
                logger.info(f"    type: {btn_type}")
                logger.info(f"    aria-label: {aria_label}")
            
            # 檢查表單
            logger.info("\n" + "=" * 80)
            logger.info("🔍 檢查頁面上的表單:")
            logger.info("=" * 80)
            
            forms = await page.query_selector_all('form')
            logger.info(f"找到 {len(forms)} 個表單")
            
            # 獲取完整頁面內容（部分）
            logger.info("\n" + "=" * 80)
            logger.info("📄 頁面標題和基本信息:")
            logger.info("=" * 80)
            logger.info(f"標題: {page.title()}")
            logger.info(f"URL: {page.url}")
            
            # 等待用戶觀察
            logger.info("\n" + "=" * 80)
            logger.info("✅ 診斷完成")
            logger.info("=" * 80)
            logger.info("瀏覽器窗口仍保持開啟中...")
            logger.info("您可以在瀏覽器中手動輸入並觀察 HTML 結構")
            logger.info("按 Enter 關閉瀏覽器...")
            input()
            
            await browser.close()
            
        except Exception as e:
            logger.error(f"❌ 異常: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_twitter_login_visual())
