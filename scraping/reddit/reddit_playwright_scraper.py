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
    TIMEOUT = 60000  # 毫秒 - 增加以應對網路延遲
    
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
            self.browser = await self.playwright.firefox.launch(
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
                logger.warning("⚠️ [Reddit] 未設置 REDDIT_USERNAME 或 REDDIT_PASSWORD，使用未登入模式")
                return
            
            logger.info(f"🔐 [Reddit] 嘗試自動登入 Reddit ({reddit_username})...")
            # 使用更長的超時時間以應對網路延遲
            success = await PlaywrightAuthHelper.login_reddit(
                self.page,
                reddit_username,
                reddit_password,
                timeout=120000  # 增加到 2 分鐘
            )
            
            if success:
                self.is_logged_in = True
                logger.info("✅ [Reddit] Reddit 自動登入成功 - 將使用已登入身份爬取")
            else:
                logger.warning("⚠️ [Reddit] Reddit 自動登入失敗，將繼續使用未登入模式")
                
        except asyncio.TimeoutError as e:
            logger.warning(f"⚠️ [Reddit] Reddit 登入超時 (超過 120 秒): {e}")
            logger.warning("⚠️ [Reddit] 將繼續使用未登入模式")
        except Exception as e:
            logger.error(f"❌ [Reddit] 自動登入異常: {e}")
            logger.warning("⚠️ [Reddit] 將繼續使用未登入模式")
    
    async def _search_subreddit_posts(
        self,
        subreddit: str,
        max_results: int = 20,
        sort: str = "hot"
    ) -> List[RedditContent]:
        """搜尋 Subreddit 中的帖子"""
        try:
            logger.debug(f"🔍 [Reddit] 搜尋帖子: subreddit=r/{subreddit}, sort={sort}, max_results={max_results}")
            page = await self._get_page()
            
            # 構建 subreddit URL
            subreddit_url = f"{self.REDDIT_URL}/r/{subreddit}/{sort}"
            
            logger.debug(f"🌐 [Reddit] 導航到 URL: {subreddit_url}")
            logger.info(f"🔍 [Reddit] 搜尋 r/{subreddit} ({sort})")
            await page.goto(subreddit_url, wait_until='networkidle', timeout=self.TIMEOUT)
            logger.debug("✅ [Reddit] 頁面已加載")
            
            # 等待帖子加載
            logger.debug("⏳ [Reddit] 等待帖子元素加載...")
            await page.wait_for_selector('[data-testid="post-container"]', timeout=10000)
            logger.debug("✅ [Reddit] 帖子元素已加載")
            
            posts = []
            
            # 滾動頁面以加載更多帖子
            logger.debug(f"📄 [Reddit] 開始提取帖子 (目標: {max_results})...")
            for scroll_idx in range(max_results // 10 + 1):
                # 提取當前可見的帖子
                logger.debug(f"📄 [Reddit] 滾動 #{scroll_idx}: 查詢帖子元素...")
                post_elements = await page.query_selector_all('[data-testid="post-container"]')
                logger.debug(f"📄 [Reddit] 找到 {len(post_elements)} 個帖子元素")
                
                for elem_idx, element in enumerate(post_elements):
                    if len(posts) >= max_results:
                        logger.debug(f"🛑 [Reddit] 達到最大數量 ({max_results})")
                        break
                    
                    try:
                        logger.debug(f"📝 [Reddit] 提取帖子 #{elem_idx}...")
                        post_data = await self._extract_post_data(element, subreddit)
                        if post_data:
                            posts.append(post_data)
                            logger.debug(f"✅ [Reddit] 帖子已提取: {post_data.username} - {post_data.title[:50]}...")
                        else:
                            logger.debug(f"⏭️ [Reddit] 帖子為空，跳過")
                    except Exception as e:
                        logger.debug(f"⚠️ [Reddit] 提取帖子 #{elem_idx} 失敗: {e}")
                        continue
                
                if len(posts) >= max_results:
                    break
                
                # 滾動以加載更多
                logger.debug(f"📄 [Reddit] 滾動頁面加載更多帖子...")
                await page.evaluate('window.scrollBy(0, window.innerHeight)')
                await asyncio.sleep(1)
            
            logger.info(f"✅ [Reddit] 找到 {len(posts)} 個帖子 (目標: {max_results})")
            return posts[:max_results]
            
        except Exception as e:
            logger.error(f"搜尋失敗: {e}")
            return []
    
    async def _extract_post_data(self, element, subreddit: str) -> Optional[RedditContent]:
        """從元素提取帖子數據"""
        try:
            logger.debug("📄 [Reddit] 提取帖子數據...")
            # 提取帖子標題
            title_elem = await element.query_selector('h3')
            title = await title_elem.inner_text() if title_elem else ""
            logger.debug(f"📝 [Reddit] 帖子標題長度: {len(title)}")
            
            if not title:
                logger.debug("❌ [Reddit] 帖子標題為空，跳過")
                return None
            
            # 提取帖子 ID 和 URL
            post_link = await element.query_selector('a[slot="full-post-link"]')
            post_url = await post_link.get_attribute('href') if post_link else ""
            post_id = post_url.split('/')[4] if post_url else ""
            logger.debug(f"🆔 [Reddit] 帖子 ID: {post_id}")
            
            if not post_id:
                logger.debug("❌ [Reddit] 未找到帖子 ID，跳過")
                return None
            
            # 提取用戶名
            author_elem = await element.query_selector('a[data-testid="post-author-link"]')
            username = await author_elem.inner_text() if author_elem else DELETED_USER
            logger.debug(f"👤 [Reddit] 用戶名: {username}")
            
            # 提取帖子文本
            content_elem = await element.query_selector('[data-testid="post-content-root"]')
            body = await content_elem.inner_text() if content_elem else ""
            logger.debug(f"📝 [Reddit] 帖子內容長度: {len(body)}")
            
            # 構造完整 URL
            if not post_url.startswith('http'):
                post_url = f"https://reddit.com{post_url}"
            
            # 確保 subreddit 有 r/ 前綴
            community = f"r/{subreddit}" if not subreddit.startswith('r/') else subreddit
            logger.debug(f"✅ [Reddit] 帖子已提取: {username} in {community}")
            
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
            logger.debug(f"⚠️ [Reddit] 提取帖子數據異常: {e}")
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
            
            # 訪問帖子 - 從 entity.community 移除 r/ 前綴
            community = entity.community.replace('r/', '')
            post_url = f"{self.REDDIT_URL}/r/{community}/comments/{entity.id}"
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
            logger.info(f"🚀 [Reddit] on_demand_scrape 啟動: subreddit={subreddit}, usernames={usernames}, keywords={keywords}, limit={limit}")
            all_posts = []
            
            # 爬取指定 subreddit
            if subreddit and subreddit != "all":
                logger.debug(f"📍 [Reddit] 爬取 subreddit: r/{subreddit}")
                posts = await self._search_subreddit_posts(
                    subreddit=subreddit.replace('r/', ''),
                    max_results=limit,
                )
                logger.debug(f"✅ [Reddit] Subreddit r/{subreddit} 獲得 {len(posts)} 個帖子")
                all_posts.extend(posts)
            
            logger.debug(f"📊 [Reddit] 全部帖子: {len(all_posts)}，開始過濾...")
            
            # Filter by date range if provided
            if start_datetime or end_datetime:
                logger.debug(f"📅 [Reddit] 過濾日期範圍: {start_datetime} - {end_datetime}")
                filtered_posts = []
                for post in all_posts:
                    post_time = post.createdAt  # 使用 createdAt 而不是 created_at
                    if start_datetime and post_time < start_datetime:
                        continue
                    if end_datetime and post_time > end_datetime:
                        continue
                    filtered_posts.append(post)
                logger.debug(f"✅ [Reddit] 日期過濾後: {len(filtered_posts)} 個帖子")
                all_posts = filtered_posts
            
            # Filter by username if provided
            if usernames:
                logger.debug(f"👤 [Reddit] 過濾用戶: {usernames}")
                filtered_posts = [
                    post for post in all_posts
                    if post.username in usernames
                ]
                logger.debug(f"✅ [Reddit] 用戶過濾後: {len(filtered_posts)} 個帖子")
                all_posts = filtered_posts
            
            # Filter by keywords if provided
            if keywords:
                logger.debug(f"🔑 [Reddit] 過濾關鍵字: {keywords}, mode={keyword_mode}")
                filtered_posts = []
                for post in all_posts:
                    post_text = (post.title + " " + (post.body or "")).lower()  # 使用 body 而不是 text
                    if keyword_mode == "all":
                        # AND logic - all keywords must be present
                        if all(kw.lower() in post_text for kw in keywords):
                            filtered_posts.append(post)
                    else:
                        # OR logic - at least one keyword must be present
                        if any(kw.lower() in post_text for kw in keywords):
                            filtered_posts.append(post)
                logger.debug(f"✅ [Reddit] 關鍵字過濾後: {len(filtered_posts)} 個帖子")
                all_posts = filtered_posts
            
            result = all_posts[:limit]
            logger.info(f"✅ [Reddit] on_demand_scrape 完成: {len(result)} 個帖子返回")
            return result
            
        except Exception as e:
            logger.error(f"❌ [Reddit] on_demand_scrape 失敗: {e}")
            return []
        
        finally:
            await self._close_browser()
