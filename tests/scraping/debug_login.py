import asyncio
import os
import sys
import logging
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("debug_login")

async def debug_x():
    logger.info("=" * 60)
    logger.info("调试 X / Twitter 登入")
    logger.info("=" * 60)
    
    username = os.getenv('TWITTER_USERNAME')
    password = os.getenv('TWITTER_PASSWORD')
    
    if not username or not password:
        logger.error("缺少 TWITTER_USERNAME 或 TWITTER_PASSWORD")
        return
        
    async with async_playwright() as p:
        # 使用 firefox
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
        )
        page = await context.new_page()
        
        try:
            logger.info("导航到 X login url...")
            await page.goto("https://x.com/i/flow/login", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(5000)
            
            # 保存第一步截图
            logger.info("保存加载页面后的截图...")
            await page.screenshot(path="x_step1_loaded.png")
            logger.info("当前 URL: %s", page.url)
            
            # 打印所有 input
            inputs = await page.query_selector_all("input")
            logger.info("找到 %d 个 input:", len(inputs))
            for i, inp in enumerate(inputs):
                name = await inp.get_attribute("name")
                placeholder = await inp.get_attribute("placeholder")
                autocomplete = await inp.get_attribute("autocomplete")
                type_attr = await inp.get_attribute("type")
                logger.info("  Input %d: name=%s, placeholder=%s, autocomplete=%s, type=%s", i, name, placeholder, autocomplete, type_attr)
                
            # 寻找用户名输入框
            # 常见选择器: input[autocomplete="username"], input[name="text"]
            username_input = await page.query_selector('input[autocomplete="username"]')
            if not username_input:
                username_input = await page.query_selector('input[name="text"]')
            if not username_input:
                username_input = await page.query_selector('input[type="text"]')
                
            if username_input:
                logger.info("输入用户名...")
                await username_input.fill(username)
                await page.screenshot(path="x_step2_username_filled.png")
                
                next_btn = None
                buttons = await page.query_selector_all("button")
                logger.info("找到 %d 个 button:", len(buttons))
                for btn in buttons:
                    text = await btn.inner_text()
                    text_strip = text.strip()
                    logger.info("  Button text: %s", text_strip)
                    if text_strip in ["Next", "下一步", "Continue"]:
                        next_btn = btn
                        break
                        
                if next_btn:
                    logger.info("点击 Next/Continue 按钮...")
                    await next_btn.click()
                    await page.wait_for_timeout(5000)
                    await page.screenshot(path="x_step3_after_next.png")
                    logger.info("点击 Next 后的 URL: %s", page.url)
                    
                    # 检查是否要求输入密码，或者有其它 verification
                    # 密码框选择器: input[name="password"]
                    password_input = await page.query_selector('input[name="password"]')
                    if password_input:
                        logger.info("找到密码输入框，输入密码...")
                        await password_input.fill(password)
                        await page.screenshot(path="x_step4_password_filled.png")
                        
                        # 寻找登录按钮 "Log in"
                        login_btn = None
                        buttons = await page.query_selector_all("button")
                        for btn in buttons:
                            text = await btn.inner_text()
                            if any(t in text for t in ["Log in", "登入", "登录"]):
                                login_btn = btn
                                break
                        if not login_btn:
                            # 备用
                            login_btn = await page.query_selector('button[data-testid="LoginForm_Login_Button"]')
                            
                        if login_btn:
                            logger.info("点击登录按钮...")
                            await login_btn.click()
                            await page.wait_for_timeout(10000)
                            await page.screenshot(path="x_step5_after_login.png")
                            logger.info("登录后的 URL: %s", page.url)
                        else:
                            logger.error("找不到登录按钮！")
                    else:
                        logger.warning("未找到密码输入框。可能需要输入手机号/邮箱验证 (Suspicious login challenge)？")
                        # 检查是否有其它输入框
                        inputs = await page.query_selector_all("input")
                        for i, inp in enumerate(inputs):
                            name = await inp.get_attribute("name")
                            placeholder = await inp.get_attribute("placeholder")
                            logger.info("  验证步骤 Input %d: name=%s, placeholder=%s", i, name, placeholder)
                else:
                    logger.error("找不到 Next 按钮！")
            else:
                logger.error("找不到用户名输入框！")
                
        except Exception as e:
            logger.exception("调试 X 出错: %s", e)
        finally:
            await browser.close()

async def debug_reddit():
    logger.info("=" * 60)
    logger.info("调试 Reddit 登入")
    logger.info("=" * 60)
    
    username = os.getenv('REDDIT_USERNAME')
    password = os.getenv('REDDIT_PASSWORD')
    
    if not username or not password:
        logger.error("缺少 REDDIT_USERNAME 或 REDDIT_PASSWORD")
        return
        
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
        )
        page = await context.new_page()
        
        try:
            logger.info("导航到 Reddit login url...")
            await page.goto("https://www.reddit.com/login", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(5000)
            
            # 保存第一步截图
            logger.info("保存加载页面后的截图...")
            await page.screenshot(path="reddit_step1_loaded.png")
            logger.info("当前 URL: %s", page.url)
            
            # 打印所有 input
            inputs = await page.query_selector_all("input")
            logger.info("找到 %d 个 input:", len(inputs))
            for i, inp in enumerate(inputs):
                name = await inp.get_attribute("name")
                placeholder = await inp.get_attribute("placeholder")
                type_attr = await inp.get_attribute("type")
                logger.info("  Input %d: name=%s, placeholder=%s, type=%s", i, name, placeholder, type_attr)
                
            username_input = await page.query_selector('input[name="username"]')
            password_input = await page.query_selector('input[name="password"]')
            
            if username_input and password_input:
                logger.info("输入用户名和密码...")
                await username_input.fill(username)
                await password_input.fill(password)
                await page.screenshot(path="reddit_step2_filled.png")
                
                # 寻找登录按钮
                login_btn = None
                buttons = await page.query_selector_all("button")
                logger.info("找到 %d 个 button:", len(buttons))
                for btn in buttons:
                    text = await btn.inner_text()
                    logger.info("  Button text: %s", text.strip())
                    if any(t in text for t in ["Log in", "Log In", "登入", "登录"]):
                        login_btn = btn
                        
                if not login_btn:
                    login_btn = await page.query_selector('button[type="submit"]')
                    
                if login_btn:
                    logger.info("点击登录按钮...")
                    await login_btn.click()
                    await page.wait_for_timeout(10000)
                    await page.screenshot(path="reddit_step3_after_login.png")
                    logger.info("登录后的 URL: %s", page.url)
                    
                    # 检查是否有错误提示
                    error_div = await page.query_selector('[class*="error"]')
                    if error_div:
                        logger.warning("发现可能有错误提示: %s", await error_div.inner_text())
                else:
                    logger.error("找不到登录按钮！")
            else:
                logger.error("找不到用户名或密码输入框！")
                
        except Exception as e:
            logger.exception("调试 Reddit 出错: %s", e)
        finally:
            await browser.close()

async def main():
    await debug_x()
    await debug_reddit()

if __name__ == "__main__":
    asyncio.run(main())
