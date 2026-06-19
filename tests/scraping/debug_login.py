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
                    # 先等密码框出现
                    try:
                        await page.wait_for_selector('input[name="password"]', timeout=10000)
                    except Exception:
                        pass
                    password_input = await page.query_selector('input[name="password"]')
                    if not password_input:
                        password_input = await page.query_selector('input[type="password"]')
                    if password_input:
                        logger.info("找到密码输入框，输入密码...")
                        await password_input.click()
                        await password_input.fill(password)
                        await page.wait_for_timeout(500)
                        await page.screenshot(path="x_step4_password_filled.png")
                        
                        # 列出所有按钮以便诊断
                        login_btn = None
                        buttons = await page.query_selector_all("button")
                        logger.info("密码填写后找到 %d 个 button:", len(buttons))
                        for btn in buttons:
                            raw_text = await btn.inner_text()
                            text = raw_text.strip()
                            data_testid = await btn.get_attribute("data-testid")
                            btn_type = await btn.get_attribute("type")
                            logger.info("  Button raw=%r, testid=%s, type=%s", text, data_testid, btn_type)
                            if text in ["Log in", "Log In", "登入", "登录", "Sign in"]:
                                login_btn = btn
                                break
                        
                        if not login_btn:
                            # 备用1: data-testid
                            login_btn = await page.query_selector('[data-testid="LoginForm_Login_Button"]')
                            if login_btn:
                                logger.info("备用1: 通过 data-testid 找到登录按钮")
                        if not login_btn:
                            # 备用2: type=submit
                            login_btn = await page.query_selector('button[type="submit"]')
                            if login_btn:
                                logger.info("备用2: 通过 type=submit 找到登录按钮")
                        if not login_btn:
                            # 备用3: aria-label
                            login_btn = await page.query_selector('button[aria-label*="Log"]')
                            if login_btn:
                                logger.info("备用3: 通过 aria-label 找到登录按钮")
                            
                        if login_btn:
                            logger.info("点击登录按钮...")
                            await login_btn.click()
                            await page.wait_for_timeout(10000)
                            await page.screenshot(path="x_step5_after_login.png")
                            logger.info("登录后的 URL: %s", page.url)
                        else:
                            logger.error("找不到登录按钮！")
                            # 输出页面 HTML 片段以便诊断
                            try:
                                body_html = await page.evaluate("document.body.innerHTML")
                                logger.info("页面 HTML 片段 (前2000字): %s", body_html[:2000])
                            except Exception as html_err:
                                logger.debug("获取 HTML 失败: %s", html_err)
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
                    
                    # 检查是否有错误提示（用更精确的选择器，避免误报）
                    error_selectors = [
                        'p[class*="error"]:not([class*="-error"])',
                        'span[class*="error-message"]',
                        '[id*="error-message"]',
                        '.error-message',
                    ]
                    found_real_error = False
                    for err_sel in error_selectors:
                        error_div = await page.query_selector(err_sel)
                        if error_div:
                            err_text = (await error_div.inner_text()).strip()
                            if err_text:
                                logger.warning("发现错误提示 (%s): %s", err_sel, err_text)
                                found_real_error = True
                                break
                    if not found_real_error:
                        logger.info("未发现明确错误提示")
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
