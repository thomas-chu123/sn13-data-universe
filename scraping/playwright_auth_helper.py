"""
Playwright 認證助手 - 處理 Twitter 和 Reddit 登入
"""

import os
import asyncio
import logging
from typing import Optional, Tuple
from playwright.async_api import Page

logger = logging.getLogger(__name__)


class PlaywrightAuthHelper:
    """Playwright 認證助手類"""
    
    TWITTER_LOGIN_URL = "https://x.com/i/flow/login"
    REDDIT_LOGIN_URL = "https://www.reddit.com/login"

    @staticmethod
    async def _first_visible_element(page: Page, selector: str, timeout: int = 10000):
        """
        Return the first visible element matching selector.
        X often keeps duplicate hidden inputs in the DOM; query_selector can pick
        one that exists but can never receive pointer events.
        """
        await page.wait_for_selector(selector, state="visible", timeout=timeout)
        elements = await page.query_selector_all(selector)
        first_visible = None
        for element in elements:
            try:
                if not await element.is_visible():
                    continue
                if first_visible is None:
                    first_visible = element
                receives_pointer = await element.evaluate("""(el) => {
                    const rect = el.getBoundingClientRect();
                    const x = rect.left + rect.width / 2;
                    const y = rect.top + rect.height / 2;
                    const hit = document.elementFromPoint(x, y);
                    return hit === el || el.contains(hit) || (hit && hit.contains(el));
                }""")
                if receives_pointer:
                    return element
            except Exception:
                continue
        return first_visible

    @staticmethod
    async def _fill_input(element, value: str, timeout: int = 5000):
        try:
            await element.fill(value, timeout=timeout)
            return
        except Exception as e:
            logger.debug(f"ℹ️ Playwright fill failed, using DOM fallback: {e}")

        await element.evaluate("""(el, value) => {
            const proto = el instanceof HTMLTextAreaElement
                ? HTMLTextAreaElement.prototype
                : HTMLInputElement.prototype;
            const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
            el.focus();
            setter.call(el, value);
            el.dispatchEvent(new Event("input", { bubbles: true }));
            el.dispatchEvent(new Event("change", { bubbles: true }));
        }""", value)

    @staticmethod
    async def _click_element(element, timeout: int = 5000):
        try:
            await element.click(timeout=timeout)
            return
        except Exception as e:
            logger.debug(f"ℹ️ Playwright click failed, using DOM fallback: {e}")
        await element.evaluate("""(el) => el.click()""")
    
    @staticmethod
    async def _click_exact_button(page: Page, target_texts: list) -> bool:
        """
        精確匹配按鈕文字並點擊（完全匹配，避免 :has-text 的前綴匹配問題）
        
        Args:
            page: Playwright Page 對象
            target_texts: 目標按鈕文字列表（完全匹配）
        
        Returns:
            是否成功找到並點擊
        """
        try:
            buttons = await page.query_selector_all("button")
            for btn in buttons:
                try:
                    if not await btn.is_visible():
                        continue
                    text = (await btn.inner_text()).strip()
                    if text in target_texts:
                        logger.debug(f"✅ 找到按鈕: '{text}'，點擊...")
                        await PlaywrightAuthHelper._click_element(btn)
                        return True
                except Exception:
                    continue
            logger.debug(f"❌ 找不到按鈕: {target_texts}")
            return False
        except Exception as e:
            logger.debug(f"❌ 查找按鈕時出錯: {e}")
            return False

    @staticmethod
    async def login_twitter(
        page: Page,
        username: str,
        password: str,
        timeout: int = 30000
    ) -> bool:
        """
        使用 Playwright 登入 Twitter/X
        
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
            logger.debug("🌐 [Twitter] 導航到登入頁面...")
            await page.goto(PlaywrightAuthHelper.TWITTER_LOGIN_URL, wait_until='networkidle', timeout=timeout)
            await asyncio.sleep(3)
            logger.debug(f"✅ [Twitter] 登入頁面已加載，URL: {page.url}")
            
            # 關閉 Google 登入彈出窗口（如果存在）
            logger.debug("🔍 [Twitter] 檢查是否有 Google 登入彈出窗口...")
            try:
                close_button = await page.query_selector('div[role="dialog"] button[aria-label*="Close"]')
                if close_button:
                    await close_button.click()
                    await asyncio.sleep(1)
                    logger.debug("✅ [Twitter] Google 彈出窗口已關閉")
                else:
                    await page.press('body', 'Escape')
                    await asyncio.sleep(0.5)
                
                # 隱藏 Google 相關元素
                try:
                    await page.evaluate("""() => {
                        const googleFrames = document.querySelectorAll('iframe[src*="google"], iframe[title*="Google"]');
                        googleFrames.forEach(frame => { frame.style.display = 'none'; frame.remove(); });
                        const dialogs = document.querySelectorAll('div[role="dialog"]');
                        dialogs.forEach(dialog => {
                            const hasGoogle = dialog.textContent.includes('Google') || dialog.innerHTML.includes('Google');
                            if (hasGoogle) { dialog.style.display = 'none'; dialog.remove(); }
                        });
                    }""")
                except Exception as e:
                    logger.debug(f"ℹ️ [Twitter] JavaScript 清理失敗（可能不需要）: {e}")
            except Exception as e:
                logger.debug(f"ℹ️ [Twitter] 關閉 Google 彈出窗口失敗（可能不存在）: {e}")
            
            # 等待用戶名輸入框
            logger.debug("⏳ [Twitter] 等待用戶名輸入框...")
            username_input = None
            for selector in [
                'input[name="username_or_email"]',
                'input[autocomplete="username"]',
                'input[name="text"]',
            ]:
                try:
                    username_input = await PlaywrightAuthHelper._first_visible_element(
                        page, selector, timeout=10000
                    )
                    if username_input:
                        logger.debug(f"✅ [Twitter] 找到用戶名輸入框: {selector}")
                        break
                except Exception:
                    continue
            
            if not username_input:
                logger.warning("⚠️ [Twitter] 找不到用戶名輸入框")
                return False
            
            # 輸入用戶名
            logger.debug("📝 [Twitter] 輸入用戶名...")
            await PlaywrightAuthHelper._fill_input(username_input, username)
            await asyncio.sleep(1)
            logger.debug("✅ [Twitter] 用戶名已輸入")
            
            # 精確點擊 Continue / Next 按鈕（避免匹配 "Continue with phone" 等）
            logger.debug("🔘 [Twitter] 查找 Continue/Next 按鈕（精確匹配）...")
            clicked = await PlaywrightAuthHelper._click_exact_button(
                page, ["Continue", "Next", "下一步", "继续"]
            )
            
            if not clicked:
                # 備用：嘗試 data-testid
                btn = None
                for selector in ['[data-testid="LoginForm_Login_Button"]', 'button[type="submit"]']:
                    try:
                        btn = await PlaywrightAuthHelper._first_visible_element(
                            page, selector, timeout=2000
                        )
                        if btn:
                            break
                    except Exception:
                        continue
                if btn:
                    logger.debug("✅ [Twitter] 備用方式找到 Continue 按鈕，點擊...")
                    await PlaywrightAuthHelper._click_element(btn)
                    clicked = True
                    
            if not clicked:
                logger.warning("⚠️ [Twitter] 找不到 Continue/Next 按鈕")
                return False
            
            await asyncio.sleep(3)
            logger.debug(f"✅ [Twitter] Continue 後的 URL: {page.url}")
            
            # 等待密碼輸入框
            logger.debug("⏳ [Twitter] 等待密碼輸入框...")
            password_input = None
            for selector in ['input[name="password"]', 'input[type="password"]']:
                try:
                    password_input = await PlaywrightAuthHelper._first_visible_element(
                        page, selector, timeout=15000
                    )
                    if password_input:
                        logger.debug(f"✅ [Twitter] 找到密碼輸入框: {selector}")
                        break
                except Exception:
                    continue
            
            if not password_input:
                logger.warning("⚠️ [Twitter] 密碼輸入框未找到，可能出現了額外的驗證步驟")
                # 列出當前頁面的 input
                inputs = await page.query_selector_all("input")
                for i, inp in enumerate(inputs):
                    name = await inp.get_attribute("name")
                    ph = await inp.get_attribute("placeholder")
                    visible = await inp.is_visible()
                    logger.debug(f"   Input {i}: name={name}, placeholder={ph}, visible={visible}")
                return False
            
            # 輸入密碼
            logger.debug("📝 [Twitter] 輸入密碼...")
            await PlaywrightAuthHelper._fill_input(password_input, password)
            await asyncio.sleep(1)
            logger.debug("✅ [Twitter] 密碼已輸入")
            
            # 精確點擊登入按鈕
            logger.debug("🔘 [Twitter] 查找登入按鈕（精確匹配）...")
            # X 的登入按鈕文字可能是 "Log in"、"Log In"、"登入"
            login_clicked = await PlaywrightAuthHelper._click_exact_button(
                page, ["Log in", "Log In", "登入", "登录", "Sign in"]
            )
            
            if not login_clicked:
                # 備用方式
                for selector in [
                    '[data-testid="LoginForm_Login_Button"]',
                    'button[type="submit"]',
                ]:
                    btn = None
                    try:
                        btn = await PlaywrightAuthHelper._first_visible_element(
                            page, selector, timeout=2000
                        )
                    except Exception:
                        continue
                    if btn:
                        logger.debug(f"✅ [Twitter] 備用方式找到登入按鈕 ({selector})，點擊...")
                        await PlaywrightAuthHelper._click_element(btn)
                        login_clicked = True
                        break
            
            if not login_clicked:
                logger.warning("⚠️ [Twitter] 找不到登入按鈕")
                return False
            
            # 等待頁面加載完成
            logger.debug("⏳ [Twitter] 等待登入完成...")
            try:
                await page.wait_for_load_state('networkidle', timeout=60000)
            except Exception as e:
                logger.debug(f"ℹ️ [Twitter] networkidle 等待結束（可能超時）: {e}")
            
            await asyncio.sleep(2)
            current_url = page.url
            logger.debug(f"📍 [Twitter] 登入後 URL: {current_url}")
            
            # 驗證登入成功：已離開 login/flow 頁面
            login_flow_paths = ["/flow/login", "/i/flow/", "/jf/onboarding", "signup_phone", "i/flow"]
            if not any(path in current_url for path in login_flow_paths):
                logger.info(f"✅ [Twitter] 登入成功 - URL: {current_url}")
                return True
            
            # 再等一下看看是否有延遲導航
            await asyncio.sleep(5)
            current_url = page.url
            logger.debug(f"📍 [Twitter] 等待後 URL: {current_url}")
            
            if not any(path in current_url for path in login_flow_paths):
                logger.info(f"✅ [Twitter] 登入成功 - URL: {current_url}")
                return True
            
            logger.warning(f"❌ [Twitter] 登入失敗，仍在登入頁面: {current_url}")
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
            logger.debug("🌐 [Reddit] 導航到登入頁面...")
            await page.goto(PlaywrightAuthHelper.REDDIT_LOGIN_URL, wait_until='networkidle', timeout=timeout)
            await asyncio.sleep(3)
            logger.debug(f"✅ [Reddit] 登入頁面已加載，URL: {page.url}")
            
            # 等待用戶名輸入框
            logger.debug("⏳ [Reddit] 等待用戶名輸入框...")
            try:
                await page.wait_for_selector('input[name="username"]', timeout=15000)
                logger.debug("✅ [Reddit] 用戶名輸入框已就緒")
            except Exception as e:
                logger.warning(f"⚠️ [Reddit] 用戶名輸入框未找到: {e}")
                return False
            
            # 輸入用戶名和密碼
            logger.debug("📝 [Reddit] 輸入用戶名...")
            await page.fill('input[name="username"]', username)
            logger.debug("✅ [Reddit] 用戶名已輸入")
            
            logger.debug("📝 [Reddit] 輸入密碼...")
            await page.fill('input[name="password"]', password)
            logger.debug("✅ [Reddit] 密碼已輸入")
            await asyncio.sleep(0.5)
            
            # 精確點擊登入按鈕（Reddit 按鈕文字為 "Log In" 或 "Log in"）
            logger.debug("🔘 [Reddit] 查找登入按鈕（精確匹配）...")
            login_clicked = await PlaywrightAuthHelper._click_exact_button(
                page, ["Log In", "Log in", "登入", "登录"]
            )
            
            if not login_clicked:
                # 備用方式
                login_btn = await page.query_selector('button[type="submit"]')
                if login_btn:
                    logger.debug("✅ [Reddit] 備用方式找到登入按鈕，點擊...")
                    await PlaywrightAuthHelper._click_element(login_btn)
                    login_clicked = True
            
            if not login_clicked:
                logger.warning("⚠️ [Reddit] 找不到登入按鈕")
                return False
            
            # 等待頁面跳轉（不強制等 networkidle，Reddit 的 js_challenge 可能導致超時）
            logger.debug("⏳ [Reddit] 等待頁面跳轉...")
            try:
                await page.wait_for_load_state('networkidle', timeout=30000)
                logger.debug("✅ [Reddit] 網路已穩定")
            except Exception:
                logger.debug("ℹ️ [Reddit] networkidle 超時，繼續檢查登入狀態...")
                await asyncio.sleep(3)
            
            current_url = page.url
            logger.debug(f"📍 [Reddit] 當前 URL: {current_url}")
            
            # 驗證登入成功：
            # 方法1 - 用戶名和密碼 input 已從頁面消失（說明已離開登入表單）
            username_input_still_visible = await page.query_selector('input[name="username"]')
            password_input_still_visible = await page.query_selector('input[name="password"]')
            
            if not username_input_still_visible and not password_input_still_visible:
                logger.info(f"✅ [Reddit] 登入成功 - 登入表單已消失 (URL: {current_url})")
                await asyncio.sleep(1)
                return True
            
            # 方法2 - URL 已不再是 /login 頁面路徑（排除 js_challenge 參數干擾）
            from urllib.parse import urlparse
            parsed = urlparse(current_url)
            # 如果 path 不再是 /login，認為登入成功
            if parsed.path not in ["/login", "/login/", "/account/login"]:
                logger.info(f"✅ [Reddit] 登入成功 - 已離開登入頁面 (URL: {current_url})")
                await asyncio.sleep(1)
                return True
            
            # 方法3 - 等待更久並再次檢查
            await asyncio.sleep(5)
            current_url = page.url
            parsed = urlparse(current_url)
            username_input_still_visible = await page.query_selector('input[name="username"]')
            
            if parsed.path not in ["/login", "/login/", "/account/login"] or not username_input_still_visible:
                logger.info(f"✅ [Reddit] 登入成功（延遲確認）- URL: {current_url}")
                return True
            
            logger.warning(f"❌ [Reddit] 登入失敗，仍在登入頁面: {current_url}")
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
