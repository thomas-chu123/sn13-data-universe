"""
Playwright 認證助手 - 處理 Twitter 和 Reddit 登入
"""

import os
import asyncio
import logging
from typing import Optional, Tuple
from playwright.async_api import async_playwright, Page, Browser

logger = logging.getLogger(__name__)


class PlaywrightAuthHelper:
    """Playwright 認證助手類"""
    
    TWITTER_LOGIN_URL = "https://twitter.com/i/flow/login"
    REDDIT_LOGIN_URL = "https://www.reddit.com/login"
    
    @staticmethod
    async def login_twitter(
        page: Page,
        username: str,
        password: str,
        timeout: int = 30000
    ) -> bool:
        """
        使用 Playwright 登入 Twitter
        
        Args:
            page: Playwright Page 對象
            username: Twitter 用戶名或電子郵件
            password: Twitter 密碼
            timeout: 超時時間（毫秒）
        
        Returns:
            是否登入成功
        """
        try:
            logger.info("開始 Twitter 登入...")
            
            # 導航到登入頁面
            await page.goto(PlaywrightAuthHelper.TWITTER_LOGIN_URL, wait_until='networkidle', timeout=timeout)
            
            # 等待用戶名輸入框
            await page.wait_for_selector('input[autocomplete="username"]', timeout=10000)
            
            # 輸入用戶名
            await page.fill('input[autocomplete="username"]', username)
            
            # 點擊下一步按鈕
            next_button = await page.query_selector('button:has-text("下一步")')
            if not next_button:
                next_button = await page.query_selector('button:has-text("Next")')
            
            if next_button:
                await next_button.click()
                await asyncio.sleep(2)
            
            # 輸入密碼
            await page.wait_for_selector('input[autocomplete="current-password"]', timeout=10000)
            await page.fill('input[autocomplete="current-password"]', password)
            
            # 點擊登入按鈕
            login_button = await page.query_selector('button:has-text("登入")')
            if not login_button:
                login_button = await page.query_selector('button:has-text("Log in")')
            
            if login_button:
                await login_button.click()
                
                # 等待頁面加載完成
                await page.wait_for_url("https://twitter.com/home", timeout=30000)
                logger.info("✅ Twitter 登入成功")
                return True
            else:
                logger.warning("找不到登入按鈕")
                return False
                
        except Exception as e:
            logger.error(f"Twitter 登入失敗: {e}")
            return False
    
    @staticmethod
    async def login_reddit(
        page: Page,
        username: str,
        password: str,
        timeout: int = 30000
    ) -> bool:
        """
        使用 Playwright 登入 Reddit
        
        Args:
            page: Playwright Page 對象
            username: Reddit 用戶名
            password: Reddit 密碼
            timeout: 超時時間（毫秒）
        
        Returns:
            是否登入成功
        """
        try:
            logger.info("開始 Reddit 登入...")
            
            # 導航到登入頁面
            await page.goto(PlaywrightAuthHelper.REDDIT_LOGIN_URL, wait_until='networkidle', timeout=timeout)
            
            # 等待用戶名輸入框
            await page.wait_for_selector('input[name="username"]', timeout=10000)
            
            # 輸入用戶名
            await page.fill('input[name="username"]', username)
            
            # 輸入密碼
            await page.fill('input[name="password"]', password)
            
            # 點擊登入按鈕
            login_button = await page.query_selector('button:has-text("Log in")')
            if not login_button:
                login_button = await page.query_selector('button[type="submit"]')
            
            if login_button:
                await login_button.click()
                
                # 等待登入完成（檢查 URL 變化或元素出現）
                await page.wait_for_url("https://www.reddit.com/", timeout=30000)
                logger.info("✅ Reddit 登入成功")
                return True
            else:
                logger.warning("找不到登入按鈕")
                return False
                
        except Exception as e:
            logger.error(f"Reddit 登入失敗: {e}")
            return False
    
    @staticmethod
    async def get_cookies(page: Page) -> list:
        """獲取頁面 cookies，用於後續請求"""
        return await page.context.cookies()
    
    @staticmethod
    async def set_cookies(page: Page, cookies: list) -> None:
        """設置 cookies 到頁面"""
        await page.context.add_cookies(cookies)
    
    @staticmethod
    def get_credentials_from_env() -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        從環境變量讀取認證信息
        
        Returns:
            (twitter_username, twitter_password, reddit_username, reddit_password)
        """
        twitter_username = os.getenv('TWITTER_USERNAME')
        twitter_password = os.getenv('TWITTER_PASSWORD')
        reddit_username = os.getenv('REDDIT_USERNAME')
        reddit_password = os.getenv('REDDIT_PASSWORD')
        
        return twitter_username, twitter_password, reddit_username, reddit_password
