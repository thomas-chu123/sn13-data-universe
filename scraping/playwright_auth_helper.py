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
            logger.info(f"🔐 [Twitter] 開始登入 ({username})...")
            
            # 導航到登入頁面
            logger.debug(f"🌐 [Twitter] 導航到登入頁面...")
            await page.goto(PlaywrightAuthHelper.TWITTER_LOGIN_URL, wait_until='networkidle', timeout=timeout)
            logger.debug(f"✅ [Twitter] 登入頁面已加載")
            
            # 關閉 Google 登入彈出窗口（如果存在）
            logger.debug(f"🔍 [Twitter] 檢查是否有 Google 登入彈出窗口...")
            try:
                # 嘗試找到並關閉彈出窗口的關閉按鈕
                close_buttons = await page.query_selector_all('button[aria-label*="Close"], button[aria-label*="關閉"], div[role="dialog"] button[type="button"]')
                if close_buttons:
                    # 嘗試按 Escape 鍵先
                    logger.debug(f"⌨️ [Twitter] 按 Escape 鍵關閉彈出窗口...")
                    await page.press('body', 'Escape')
                    await asyncio.sleep(1)
                    logger.debug(f"✅ [Twitter] Escape 鍵已按下")
                
                # 如果還有 Google 登入相關的 iframe，嘗試隱藏它
                google_frames = await page.query_selector_all('iframe[title*="Google"]')
                for frame in google_frames:
                    logger.debug(f"🔍 [Twitter] 找到 Google iframe，嘗試隱藏...")
                    await page.evaluate(f"() => {{ const elem = document.querySelector('iframe[title*=\"Google\"]'); if (elem) elem.style.display = 'none'; }}")
                    logger.debug(f"✅ [Twitter] Google iframe 已隱藏")
            except Exception as e:
                logger.debug(f"ℹ️ [Twitter] 關閉彈出窗口失敗（可能不存在）: {e}")
            
            await asyncio.sleep(1)
            
            # 等待用戶名輸入框（增加超時時間）
            logger.debug(f"⏳ [Twitter] 等待用戶名輸入框...")
            try:
                await page.wait_for_selector('input[autocomplete="username"]', timeout=20000)
                logger.debug(f"✅ [Twitter] 用戶名輸入框已就緒")
            except Exception as e:
                logger.warning(f"⚠️ [Twitter] 用戶名輸入框未找到: {e}，嘗試其他選擇器...")
                await asyncio.sleep(2)
            
            # 輸入用戶名
            logger.debug(f"📝 [Twitter] 輸入用戶名...")
            await page.fill('input[autocomplete="username"]', username)
            logger.debug(f"✅ [Twitter] 用戶名已輸入")
            
            # 點擊下一步按鈕
            logger.debug(f"🔘 [Twitter] 查找下一步按鈕...")
            next_button = await page.query_selector('button:has-text("下一步")')
            if not next_button:
                next_button = await page.query_selector('button:has-text("Next")')
            
            if next_button:
                logger.debug(f"✅ [Twitter] 點擊下一步")
                await next_button.click()
                await asyncio.sleep(3)  # 增加等待時間
                logger.debug(f"✅ [Twitter] 下一步完成")
            else:
                logger.warning(f"⚠️ [Twitter] 找不到下一步按鈕，繼續...")
            
            # 輸入密碼（增加超時時間）
            logger.debug(f"⏳ [Twitter] 等待密碼輸入框...")
            try:
                await page.wait_for_selector('input[autocomplete="current-password"]', timeout=20000)
                logger.debug(f"✅ [Twitter] 密碼輸入框已就緒")
            except Exception as e:
                logger.warning(f"⚠️ [Twitter] 密碼輸入框未找到: {e}，嘗試其他選擇器...")
                await asyncio.sleep(2)
            
            logger.debug(f"📝 [Twitter] 輸入密碼...")
            await page.fill('input[autocomplete="current-password"]', password)
            logger.debug(f"✅ [Twitter] 密碼已輸入")
            
            # 點擊登入按鈕
            logger.debug(f"🔘 [Twitter] 查找登入按鈕...")
            login_button = await page.query_selector('button:has-text("登入")')
            if not login_button:
                login_button = await page.query_selector('button:has-text("Log in")')
            
            if login_button:
                logger.debug(f"✅ [Twitter] 點擊登入按鈕")
                await login_button.click()
                
                # 等待頁面加載完成（增加超時時間）
                logger.debug(f"⏳ [Twitter] 等待登入完成...")
                try:
                    # 等待頁面穩定而不是等待特定 URL
                    await page.wait_for_load_state('networkidle', timeout=60000)
                    logger.debug("✅ [Twitter] 網路已穩定")
                    
                    current_url = page.url
                    logger.debug(f"📍 [Twitter] 當前 URL: {current_url}")
                    
                    # 檢查是否已登出登入頁面
                    if "twitter.com" in current_url and ("login" not in current_url and "i/flow" not in current_url):
                        logger.info(f"✅ [Twitter] 登入成功 - 已離開登入流程 (URL: {current_url})")
                        
                        # 等待一下，讓頁面完全加載
                        await asyncio.sleep(2)
                        
                        return True
                    else:
                        logger.warning(f"⚠️ [Twitter] 可能仍在登入流程: {current_url}")
                        # 等待更久看看是否會導航
                        await asyncio.sleep(5)
                        current_url = page.url
                        logger.debug(f"📍 [Twitter] 等待後 URL: {current_url}")
                        
                        if "twitter.com" in current_url and ("login" not in current_url and "i/flow" not in current_url):
                            logger.info(f"✅ [Twitter] 登入成功 - URL: {current_url}")
                            return True
                        else:
                            logger.warning(f"❌ [Twitter] 仍在登入頁面: {current_url}")
                            return False
                        
                except asyncio.TimeoutError as e:
                    logger.warning(f"⚠️ [Twitter] 頁面加載超時: {e}")
                    current_url = page.url
                    logger.info(f"📍 [Twitter] 當前 URL: {current_url}")
                    
                    # 即使超時，也檢查是否已離開登入頁面
                    if "twitter.com" in current_url and ("login" not in current_url and "i/flow" not in current_url):
                        logger.info(f"✅ [Twitter] 可能登入成功 - URL: {current_url}")
                        return True
                    else:
                        logger.warning(f"❌ [Twitter] 仍在登入頁面")
                        return False
                        
                except Exception as e:
                    logger.warning(f"⚠️ [Twitter] 等待過程出錯: {e}")
                    current_url = page.url
                    logger.info(f"📍 [Twitter] 當前 URL: {current_url}")
                    
                    # 檢查是否已離開登入頁面
                    if "twitter.com" in current_url and ("login" not in current_url and "i/flow" not in current_url):
                        logger.info(f"✅ [Twitter] 可能登入成功 - URL: {current_url}")
                        return True
                    else:
                        logger.warning(f"❌ [Twitter] 仍在登入頁面")
                        return False
            else:
                logger.warning("⚠️ [Twitter] 找不到登入按鈕")
                return False
                
        except Exception as e:
            logger.error(f"❌ [Twitter] 登入異常: {e}")
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
            logger.info(f"🔐 [Reddit] 開始登入 ({username})...")
            
            # 導航到登入頁面
            logger.debug(f"🌐 [Reddit] 導航到登入頁面...")
            await page.goto(PlaywrightAuthHelper.REDDIT_LOGIN_URL, wait_until='networkidle', timeout=timeout)
            logger.debug(f"✅ [Reddit] 登入頁面已加載")
            
            # 等待用戶名輸入框（增加超時時間）
            logger.debug(f"⏳ [Reddit] 等待用戶名輸入框...")
            try:
                await page.wait_for_selector('input[name="username"]', timeout=20000)
                logger.debug(f"✅ [Reddit] 用戶名輸入框已就緒")
            except Exception as e:
                logger.warning(f"⚠️ [Reddit] 用戶名輸入框未找到: {e}，嘗試其他選擇器...")
                await asyncio.sleep(2)
            
            # 輸入用戶名
            logger.debug(f"📝 [Reddit] 輸入用戶名...")
            await page.fill('input[name="username"]', username)
            logger.debug(f"✅ [Reddit] 用戶名已輸入")
            
            # 輸入密碼
            logger.debug(f"📝 [Reddit] 輸入密碼...")
            await page.fill('input[name="password"]', password)
            logger.debug(f"✅ [Reddit] 密碼已輸入")
            
            # 點擊登入按鈕
            logger.debug(f"🔘 [Reddit] 查找登入按鈕...")
            login_button = await page.query_selector('button:has-text("Log in")')
            if not login_button:
                login_button = await page.query_selector('button[type="submit"]')
            
            if login_button:
                logger.debug(f"✅ [Reddit] 點擊登入按鈕")
                await login_button.click()
                
                # 等待登入完成
                logger.debug(f"⏳ [Reddit] 等待登入完成...")
                try:
                    # 先等待一下，讓 JavaScript 挑戰（js_challenge）可以執行
                    await asyncio.sleep(3)
                    logger.debug("✅ [Reddit] 已等待 JavaScript 挑戰時間")
                    
                    # 等待導航或頁面穩定（嘗試多個條件）
                    # Reddit 可能會在 js_challenge 之後導航，或者頁面會更新
                    try:
                        await page.wait_for_load_state('networkidle', timeout=60000)
                        logger.debug("✅ [Reddit] 網路已穩定")
                    except:
                        logger.warning("⚠️ [Reddit] 網路穩定超時，繼續檢查...")
                        await asyncio.sleep(5)
                    
                    current_url = page.url
                    logger.debug(f"📍 [Reddit] 當前 URL: {current_url}")
                    
                    # 檢查是否已登出登入頁面
                    # 排除 js_challenge 和 solution 參數
                    is_login_page = ("login" in current_url or "password" in current_url) and \
                                   ("js_challenge" in current_url or not any(x in current_url for x in ["/?", "reddit.com/r/"]))
                    
                    if not is_login_page or "reddit.com/r/" in current_url or "/user/" in current_url:
                        logger.info(f"✅ [Reddit] 登入成功 - 已離開登入流程 (URL: {current_url})")
                        
                        # 等待一下，讓頁面完全加載
                        await asyncio.sleep(2)
                        
                        return True
                    else:
                        logger.warning(f"❌ [Reddit] 仍在登入頁面: {current_url}")
                        # 嘗試檢查是否有其他元素表明登入成功
                        try:
                            # 查找用戶菜單或首頁指示
                            user_menu = await page.query_selector('[data-test-id="post-container"], .ProfileDropdown__Button')
                            if user_menu:
                                logger.info("✅ [Reddit] 檢測到登入成功（找到用戶菜單）")
                                return True
                        except:
                            pass
                        return False
                        
                except asyncio.TimeoutError as e:
                    logger.warning(f"⚠️ [Reddit] 頁面加載超時: {e}")
                    current_url = page.url
                    logger.info(f"📍 [Reddit] 當前 URL: {current_url}")
                    
                    # 即使超時，也檢查是否已離開登入頁面
                    if "login" not in current_url and "password" not in current_url:
                        logger.info(f"✅ [Reddit] 可能登入成功 - URL: {current_url}")
                        return True
                    else:
                        logger.warning(f"❌ [Reddit] 仍在登入頁面")
                        return False
                        
                except Exception as e:
                    logger.warning(f"⚠️ [Reddit] 等待過程出錯: {e}")
                    current_url = page.url
                    logger.info(f"📍 [Reddit] 當前 URL: {current_url}")
                    
                    # 檢查是否已離開登入頁面
                    if "login" not in current_url and "password" not in current_url:
                        logger.info(f"✅ [Reddit] 可能登入成功 - URL: {current_url}")
                        return True
                    else:
                        logger.warning(f"❌ [Reddit] 仍在登入頁面")
                        return False
            else:
                logger.warning("⚠️ [Reddit] 找不到登入按鈕")
                return False
                
        except Exception as e:
            logger.error(f"❌ [Reddit] 登入異常: {e}")
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
