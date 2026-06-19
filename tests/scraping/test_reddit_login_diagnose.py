#!/usr/bin/env python3
"""
診斷 Reddit 登入超時問題
"""

import asyncio
import os
import sys
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scraping.playwright_auth_helper import PlaywrightAuthHelper
from playwright.async_api import async_playwright


async def diagnose_reddit_login():
    """診斷 Reddit 登入"""
    logger.info("=" * 80)
    logger.info("🔐 Reddit 登入診斷開始")
    logger.info("=" * 80)
    
    username = os.getenv('REDDIT_USERNAME')
    password = os.getenv('REDDIT_PASSWORD')
    
    if not username or not password:
        logger.error("❌ 缺少 REDDIT_USERNAME 或 REDDIT_PASSWORD")
        return False
    
    logger.info(f"📝 準備登入: {username}")
    
    async with async_playwright() as p:
        try:
            # 建立瀏覽器
            logger.info("📱 啟動瀏覽器...")
            browser = await p.firefox.launch(
                headless=False,  # 不使用無頭模式，這樣可以看到登入過程
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            logger.info("✅ 瀏覽器已啟動")
            
            # 建立上下文和頁面
            logger.info("📄 建立瀏覽器上下文和頁面...")
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = await context.new_page()
            logger.info("✅ 頁面建立完成")
            
            # 啟用詳細日誌
            page.on("console", lambda msg: logger.info(f"🌐 [Console] {msg.text}"))
            page.on("request", lambda req: logger.debug(f"📤 [Request] {req.method} {req.url}"))
            page.on("response", lambda resp: logger.debug(f"📥 [Response] {resp.status} {resp.url}"))
            
            # 嘗試登入
            logger.info("\n🔐 開始登入過程...")
            logger.info("=" * 80)
            
            # 方案 1: 使用 PlaywrightAuthHelper
            logger.info("🔑 方案 1: 使用 PlaywrightAuthHelper.login_reddit()...")
            success = await PlaywrightAuthHelper.login_reddit(
                page,
                username,
                password,
                timeout=120000  # 2 分鐘
            )
            
            logger.info(f"✅ 登入結果: {success}")
            
            if success:
                logger.info("✅ 登入成功！")
                logger.info(f"📍 當前 URL: {page.url}")
            else:
                logger.warning("⚠️ 登入失敗")
                logger.info(f"📍 當前 URL: {page.url}")
                
                # 嘗試檢查是否已登入
                try:
                    logger.info("\n🔍 檢查頁面狀態...")
                    
                    # 檢查是否在首頁
                    if "reddit.com" in page.url:
                        logger.info("✅ URL 包含 reddit.com")
                        
                        # 檢查是否有登入按鈕
                        login_btn = await page.query_selector('button:has-text("Log in")')
                        if login_btn:
                            logger.warning("⚠️ 仍然看到登入按鈕，可能未登入")
                        else:
                            logger.info("✅ 未看到登入按鈕，可能已登入")
                        
                        # 檢查是否有用戶菜單
                        user_menu = await page.query_selector('[data-testid="user_dropdown_menu"]')
                        if user_menu:
                            logger.info("✅ 發現用戶菜單，已登入！")
                        else:
                            logger.warning("⚠️ 未發現用戶菜單")
                    
                    # 保存頁面 HTML 用於檢查
                    logger.info("\n📄 頁面內容（前 500 字符）:")
                    content = await page.content()
                    logger.info(content[:500] + "...")
                    
                except Exception as e:
                    logger.error(f"❌ 檢查頁面狀態失敗: {e}")
            
            # 保留頁面打開 30 秒
            logger.info("\n⏳ 保持頁面打開 30 秒用於檢查...")
            await asyncio.sleep(30)
            
            # 清理
            await context.close()
            await browser.close()
            logger.info("✅ 清理完成")
            
            return success
            
        except asyncio.TimeoutError as e:
            logger.error(f"❌ 超時: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ 錯誤: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    asyncio.run(diagnose_reddit_login())
