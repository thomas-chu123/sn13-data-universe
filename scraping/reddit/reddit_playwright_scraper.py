"""
Reddit Scraper using Playwright (Browser Automation)
不需要 OAuth 認證，通過瀏覽器自動化獲取內容
支持自動登入以獲取更多功能
"""

import asyncio
import datetime as dt
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import quote

from playwright.async_api import async_playwright, Page

from common.data import DataEntity, DataSource, DataEntityBucket
from common.protocol import KeywordMode
from scraping.scraper import Scraper, ScraperId, ValidationResult
from scraping.playwright_auth_helper import PlaywrightAuthHelper
from scraping.reddit.model import RedditContent, RedditDataType, DELETED_USER

logger = logging.getLogger(__name__)
    

class RedditPlaywrightScraper(Scraper):
    """使用 Playwright 的 Reddit Scraper - 完全免費，無需 OAuth"""
    
    REDDIT_URL = "https://www.reddit.com"
    TIMEOUT = 30000  # 毫秒
    
    def __init__(self, auto_login: bool = True):
        self.playwright = None
        self.browser = None
        self.page: Optional[Page] = None
        self.auto_login = auto_login
        self.is_logged_in = False
        
    async def _initialize_browser(self):
        """初始化 Playwright 瀏覽器"""
        if self.browser is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                ]
            )
    
    async def _close_browser(self):
        """關閉瀏覽器"""
        if self.page:
            await self.page.close()
            self.page = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
    
    async def _get_page(self) -> Page:
        """取得或創建頁面"""
        if self.page is None:
            await self._initialize_browser()
            # 使用 new_context 設置 user-agent（正確的 Playwright API）
            context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            self.page = await context.new_page()
            
            # 自動登入
            if self.auto_login and not self.is_logged_in:
                await self._auto_login()
        
        return self.page
    
    async def _auto_login(self):
        """自動登入 Reddit"""
        try:
            reddit_username = os.getenv('REDDIT_USERNAME')
            reddit_password = os.getenv('REDDIT_PASSWORD')
            
            if not reddit_username or not reddit_password:
                logger.warning("未設置 REDDIT_USERNAME 或 REDDIT_PASSWORD，使用未登入模式")
                return
            
            logger.info("嘗試自動登入 Reddit...")
            success = await PlaywrightAuthHelper.login_reddit(
                self.page,
                reddit_username,
                reddit_password,
                timeout=self.TIMEOUT
            )
            
            if success:
                self.is_logged_in = True
                logger.info("✅ Reddit 自動登入成功")
            else:
                logger.warning("⚠️ Reddit 自動登入失敗，繼續使用未登入模式")
                
        except Exception as e:
            logger.error(f"自動登入異常: {e}")
            logger.warning("⚠️ 繼續使用未登入模式")
    
    async def _search_subreddit_posts(
        self,
        subreddit: str,
        max_results: int = 20,
        sort: str = "hot"
    ) -> List[RedditContent]:
        """搜尋 Subreddit 中的帖子"""
        try:
            page = await self._get_page()
            
            # 構建 subreddit URL
            subreddit_url = f"{self.REDDIT_URL}/r/{subreddit}/{sort}"
            
            logger.info(f"搜尋 r/{subreddit} ({sort})")
            await page.goto(subreddit_url, wait_until='networkidle', timeout=self.TIMEOUT)
            
            # 等待帖子加載
            await page.wait_for_selector('[data-testid="post-container"]', timeout=10000)
            
            posts = []
            
            # 滾動頁面以加載更多帖子
            for _ in range(max_results // 10 + 1):
                # 提取當前可見的帖子
                post_elements = await page.query_selector_all('[data-testid="post-container"]')
                
                for element in post_elements:
                    if len(posts) >= max_results:
                        break
                    
                    try:
                        post_data = await self._extract_post_data(element, subreddit)
                        if post_data:
                            posts.append(post_data)
                    except Exception as e:
                        logger.warning(f"提取帖子失敗: {e}")
                        continue
                
                if len(posts) >= max_results:
                    break
                
                # 滾動以加載更多
                await page.evaluate('window.scrollBy(0, window.innerHeight)')
                await asyncio.sleep(1)
            
            logger.info(f"找到 {len(posts)} 個帖子")
            return posts[:max_results]
            
        except Exception as e:
            logger.error(f"搜尋失敗: {e}")
            return []
    
    async def _extract_post_data(self, element, subreddit: str) -> Optional[RedditContent]:
        """從元素提取帖子數據"""
        try:
            # 提取帖子標題
            title_elem = await element.query_selector('h3')
            title = await title_elem.inner_text() if title_elem else ""
            
            if not title:
                return None
            
            # 提取帖子 ID 和 URL
            post_link = await element.query_selector('a[slot="full-post-link"]')
            post_url = await post_link.get_attribute('href') if post_link else ""
            post_id = post_url.split('/')[4] if post_url else ""
            
            if not post_id:
                return None
            
            # 提取用戶名
            author_elem = await element.query_selector('a[data-testid="post-author-link"]')
            username = await author_elem.inner_text() if author_elem else DELETED_USER
            
            # 提取帖子文本
            content_elem = await element.query_selector('[data-testid="post-content-root"]')
            body = await content_elem.inner_text() if content_elem else ""
            
            # 構造完整 URL
            if not post_url.startswith('http'):
                post_url = f"https://reddit.com{post_url}"
            
            # 確保 subreddit 有 r/ 前綴
            community = f"r/{subreddit}" if not subreddit.startswith('r/') else subreddit
            
            # 創建 RedditContent - 使用標準欄位名
            return RedditContent(
                id=post_id,
                url=post_url,
                username=username,
                communityName=community,
                body=body,
                createdAt=dt.datetime.utcnow(),
                dataType=RedditDataType.POST,
                title=title,
            )
            
        except Exception as e:
            logger.warning(f"提取帖子數據失敗: {e}")
            return None
            
        except Exception as e:
            logger.warning(f"提取帖子數據失敗: {e}")
            return None
    
    async def validate(
        self,
        entities: List[DataEntityBucket],
    ) -> List[ValidationResult]:
        """驗證實體"""
        results = []
        
        try:
            for entity in entities:
                if not isinstance(entity, RedditContent):
                    results.append(ValidationResult(
                        is_valid=False,
                        reason=f"Invalid entity type: {type(entity)}",
                        content_size_bytes_validated=0,
                    ))
                    continue
                
                # 驗證必要字段
                if not entity.id or not entity.username or not entity.title:
                    results.append(ValidationResult(
                        is_valid=False,
                        reason="Missing required fields (id, username, or title)",
                        content_size_bytes_validated=0,
                    ))
                    continue
                
                # 驗證帖子是否存在
                is_valid = await self._verify_post_exists(entity)
                
                if is_valid:
                    # 計算驗證的內容大小
                    content_size = len(entity.title.encode('utf-8'))
                    content_size += len(entity.body.encode('utf-8'))
                    content_size += len(entity.username.encode('utf-8'))
                    
                    results.append(ValidationResult(
                        is_valid=True,
                        reason="Post verified successfully",
                        content_size_bytes_validated=content_size,
                    ))
                else:
                    results.append(ValidationResult(
                        is_valid=False,
                        reason="Post not found or inaccessible",
                        content_size_bytes_validated=0,
                    ))
                    
        except Exception as e:
            logger.error(f"驗證失敗: {e}")
            results.append(ValidationResult(
                is_valid=False,
                reason=f"Validation error: {str(e)}",
                content_size_bytes_validated=0,
            ))
        
        finally:
            await self._close_browser()
        
        return results
    
    async def _verify_post_exists(self, entity: RedditContent) -> bool:
        """驗證帖子是否存在"""
        try:
            page = await self._get_page()
            
            # 訪問帖子
            post_url = f"{self.REDDIT_URL}/r/{entity.subreddit}/comments/{entity.post_id}"
            await page.goto(post_url, wait_until='networkidle', timeout=self.TIMEOUT)
            
            # 檢查帖子標題是否存在
            title_elem = await page.query_selector('h1')
            if title_elem:
                title = await title_elem.inner_text()
                if entity.title[:50] in title:
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"驗證帖子失敗: {e}")
            return False
    
    async def scrape(
        self,
        labels_to_scrape: List[dict],
        max_data_entities: int = 100,
    ) -> List[RedditContent]:
        """爬取 Reddit 帖子"""
        try:
            all_posts = []
            
            for label_config in labels_to_scrape:
                labels = label_config.get('label_choices', [])
                
                for label in labels:
                    # 移除 "r/" 前綴
                    subreddit = label.replace('r/', '')
                    
                    posts = await self._search_subreddit_posts(
                        subreddit=subreddit,
                        max_results=max_data_entities // len(labels),
                    )
                    all_posts.extend(posts)
            
            return all_posts[:max_data_entities]
            
        except Exception as e:
            logger.error(f"爬取失敗: {e}")
            return []
        
        finally:
            await self._close_browser()
    
    async def on_demand_scrape(
        self,
        usernames: Optional[List[str]] = None,
        subreddit: Optional[str] = "all",
        keywords: Optional[List[str]] = None,
        keyword_mode: KeywordMode = "all",
        start_datetime: dt.datetime = None,
        end_datetime: dt.datetime = None,
        limit: int = 100,
    ) -> List[RedditContent]:
        """按需爬取
        
        Args:
            usernames: List of target usernames - content from any of these users will be included (OR logic)
            subreddit: Target specific subreddit (without r/ prefix)
            keywords: List of keywords to search for
            keyword_mode: "any" (OR logic) or "all" (AND logic) for keyword matching
            start_datetime: Earliest datetime for content (UTC)
            end_datetime: Latest datetime for content (UTC)
            limit: Maximum number of items to return
        """
        try:
            all_posts = []
            
            # 爬取指定 subreddit
            if subreddit and subreddit != "all":
                posts = await self._search_subreddit_posts(
                    subreddit=subreddit.replace('r/', ''),
                    max_results=limit,
                )
                all_posts.extend(posts)
            
            # Filter by date range if provided
            if start_datetime or end_datetime:
                filtered_posts = []
                for post in all_posts:
                    post_time = dt.datetime.fromisoformat(post.created_at.replace('Z', '+00:00'))
                    if start_datetime and post_time < start_datetime:
                        continue
                    if end_datetime and post_time > end_datetime:
                        continue
                    filtered_posts.append(post)
                all_posts = filtered_posts
            
            # Filter by username if provided
            if usernames:
                filtered_posts = [
                    post for post in all_posts
                    if post.username in usernames
                ]
                all_posts = filtered_posts
            
            # Filter by keywords if provided
            if keywords:
                filtered_posts = []
                for post in all_posts:
                    post_text = (post.title + " " + (post.text or "")).lower()
                    if keyword_mode == "all":
                        # AND logic - all keywords must be present
                        if all(kw.lower() in post_text for kw in keywords):
                            filtered_posts.append(post)
                    else:
                        # OR logic - at least one keyword must be present
                        if any(kw.lower() in post_text for kw in keywords):
                            filtered_posts.append(post)
                all_posts = filtered_posts
            
            return all_posts[:limit]
            
        except Exception as e:
            logger.error(f"按需爬取失敗: {e}")
            return []
        
        finally:
            await self._close_browser()
