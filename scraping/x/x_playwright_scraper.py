"""
X/Twitter Scraper using Playwright (Browser Automation)
不需要 API 密鑰，通過瀏覽器自動化獲取推文
支持自動登入以獲取更多內容
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
from scraping.x.model import XContent

logger = logging.getLogger(__name__)
    

class XPlaywrightScraper(Scraper):
    """使用 Playwright 的 X/Twitter Scraper - 完全免費，無需 API 密鑰"""
    
    TWITTER_URL = "https://twitter.com"
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
            logger.debug("🚀 [X] 初始化瀏覽器...")
            self.playwright = await async_playwright().start()
            logger.debug("🚀 [X] Playwright 已啟動")
            # 使用 chromium，設置 headless 模式
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',  # 減少內存使用
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
        """自動登入 Twitter"""
        try:
            twitter_username = os.getenv('TWITTER_USERNAME')
            twitter_password = os.getenv('TWITTER_PASSWORD')
            
            if not twitter_username or not twitter_password:
                logger.warning("⚠️ [X] 未設置 TWITTER_USERNAME 或 TWITTER_PASSWORD，使用未登入模式")
                return
            
            logger.info(f"🔐 [X] 嘗試自動登入 Twitter ({twitter_username})...")
            # 使用更長的超時時間以應對網路延遲
            success = await PlaywrightAuthHelper.login_twitter(
                self.page,
                twitter_username,
                twitter_password,
                timeout=120000  # 增加到 2 分鐘
            )
            
            if success:
                self.is_logged_in = True
                logger.info("✅ [X] Twitter 自動登入成功 - 將使用已登入身份爬取")
            else:
                logger.warning("⚠️ [X] Twitter 自動登入失敗，將繼續使用未登入模式")
                
        except asyncio.TimeoutError as e:
            logger.warning(f"⚠️ [X] Twitter 登入超時 (超過 120 秒): {e}")
            logger.warning("⚠️ [X] 將繼續使用未登入模式")
        except Exception as e:
            logger.error(f"❌ [X] 自動登入異常: {e}")
            logger.warning("⚠️ [X] 將繼續使用未登入模式")
    
    async def _search_tweets(
        self,
        query: str,
        max_results: int = 20,
        days_back: int = 7
    ) -> List[XContent]:
        """搜尋推文"""
        try:
            logger.debug(f"🔍 [X] 搜尋推文: query='{query}', max_results={max_results}")
            page = await self._get_page()
            
            # 構建搜尋 URL
            search_query = f"{query} lang:en -is:retweet -is:reply"
            search_url = f"{self.TWITTER_URL}/search?q={quote(search_query)}&f=live"
            
            logger.debug(f"🔍 [X] 搜尋 URL: {search_url}")
            logger.info(f"🔍 [X] 搜尋查詢: {search_query}")
            await page.goto(search_url, wait_until='networkidle', timeout=self.TIMEOUT)
            logger.debug("✅ [X] 頁面已加載")
            
            # 等待推文加載
            logger.debug("⏳ [X] 等待推文元素加載...")
            await page.wait_for_selector('article', timeout=10000)
            logger.debug("✅ [X] 推文元素已加載")
            
            tweets = []
            
            # 滾動頁面以加載更多推文
            logger.debug(f"📜 [X] 開始提取推文 (目標: {max_results})...")
            for scroll_idx in range(max_results // 5):
                # 提取當前可見的推文
                logger.debug(f"📜 [X] 滾動 #{scroll_idx}: 提取推文元素...")
                tweet_elements = await page.query_selector_all('article')
                logger.debug(f"📜 [X] 找到 {len(tweet_elements)} 個推文元素")
                
                for elem_idx, element in enumerate(tweet_elements):
                    if len(tweets) >= max_results:
                        logger.debug(f"🛑 [X] 達到最大數量 ({max_results})")
                        break
                    
                    try:
                        logger.debug(f"📄 [X] 提取推文 #{elem_idx}...")
                        tweet_data = await self._extract_tweet_data(element)
                        if tweet_data:
                            tweets.append(tweet_data)
                            logger.debug(f"✅ [X] 推文已提取: @{tweet_data.username} - {tweet_data.text[:50]}...")
                        else:
                            logger.debug(f"⏭️  [X] 推文為空，跳過")
                    except Exception as e:
                        logger.debug(f"⚠️  [X] 提取推文失敗 #{elem_idx}: {e}")
                        continue
                
                if len(tweets) >= max_results:
                    break
                
                # 滾動以加載更多
                logger.debug(f"📜 [X] 滾動頁面加載更多推文...")
                await page.evaluate('window.scrollBy(0, window.innerHeight)')
                await asyncio.sleep(1)
            
            logger.info(f"✅ [X] 找到 {len(tweets)} 條推文 (目標: {max_results})")
            return tweets[:max_results]
            
        except Exception as e:
            logger.error(f"搜尋失敗: {e}")
            return []
    
    async def _extract_tweet_data(self, element) -> Optional[XContent]:
        """從元素提取推文數據"""
        try:
            logger.debug("📄 [X] 提取推文數據...")
            # 提取推文文本
            text_elem = await element.query_selector('[data-testid="tweet"]')
            text = await text_elem.inner_text() if text_elem else ""
            logger.debug(f"📝 [X] 推文文本長度: {len(text)}")
            
            if not text:
                logger.debug("❌ [X] 推文文本為空，跳過")
                return None
            
            # 提取用戶名和 URL
            username_elem = await element.query_selector('a[href*="/"]')
            username = ""
            url = ""
            if username_elem:
                href = await username_elem.get_attribute('href')
                if href:
                    username = href.split('/')[-1] if href else ""
                    url = f"https://twitter.com{href}"
                    logger.debug(f"👤 [X] 用戶名: {username}")
            
            if not username:
                logger.debug("❌ [X] 未找到用戶名，跳過")
                return None
            
            # 提取推文 ID
            article_elem = element
            article_id = await article_elem.get_attribute('data-testid')
            tweet_id = article_id.split('-')[-1] if article_id else ""
            logger.debug(f"🆔 [X] 推文 ID: {tweet_id}")
            
            # 提取主題標籤
            hashtags = self._extract_hashtags(text)
            logger.debug(f"#️⃣ [X] 主題標籤: {hashtags}")
            
            # 創建 XContent - 使用標準欄位名
            result = XContent(
                username=username,
                text=text,
                url=url or f"https://twitter.com/{username}/status/{tweet_id}",
                timestamp=dt.datetime.utcnow(),
                tweet_hashtags=hashtags,
                media=None,
                tweet_id=tweet_id,
            )
            logger.debug(f"✅ [X] 推文提取成功 (@{username}, {len(text)} 字符)")
            return result
            
        except Exception as e:
            logger.debug(f"⚠️ [X] 提取推文數據異常: {e}")
            return None
    
    async def _get_stat_count(self, element, stat_type: str) -> int:
        """取得推文的統計數據"""
        try:
            stat_elem = await element.query_selector(f'[aria-label*="{stat_type}"]')
            if stat_elem:
                label = await stat_elem.get_attribute('aria-label')
                # 從標籤中提取數字 例如: "123 Likes"
                parts = label.split()
                if parts and parts[0].isdigit():
                    return int(parts[0])
        except:
            pass
        return 0
    
    def _extract_hashtags(self, text: str) -> List[str]:
        """從文本提取主題標籤"""
        import re
        pattern = r'#\w+'
        return re.findall(pattern, text)
    
    def _extract_urls(self, text: str) -> List[str]:
        """從文本提取 URL"""
        import re
        pattern = r'https?://[^\s]+'
        return re.findall(pattern, text)
    
    async def validate(
        self,
        entities: List[DataEntityBucket],
    ) -> List[ValidationResult]:
        """驗證實體"""
        results = []
        
        try:
            for entity in entities:
                if not isinstance(entity, XContent):
                    results.append(ValidationResult(
                        is_valid=False,
                        reason=f"Invalid entity type: {type(entity)}",
                        content_size_bytes_validated=0,
                    ))
                    continue
                
                # 驗證必要字段
                if not entity.tweet_id or not entity.username or not entity.text:
                    results.append(ValidationResult(
                        is_valid=False,
                        reason="Missing required fields (id, username, or text)",
                        content_size_bytes_validated=0,
                    ))
                    continue
                
                # 驗證推文是否存在（通過 Playwright 檢查）
                is_valid = await self._verify_tweet_exists(entity)
                
                if is_valid:
                    # 計算驗證的內容大小
                    content_size = len(entity.text.encode('utf-8'))
                    content_size += len(entity.username.encode('utf-8'))
                    content_size += sum(len(h.encode('utf-8')) for h in entity.tweet_hashtags)
                    
                    results.append(ValidationResult(
                        is_valid=True,
                        reason="Tweet verified successfully",
                        content_size_bytes_validated=content_size,
                    ))
                else:
                    results.append(ValidationResult(
                        is_valid=False,
                        reason="Tweet not found or inaccessible",
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
            # 清理資源
            await self._close_browser()
        
        return results
    
    async def _verify_tweet_exists(self, entity: XContent) -> bool:
        """驗證推文是否存在"""
        try:
            page = await self._get_page()
            
            # 訪問推文
            tweet_url = f"{self.TWITTER_URL}/{entity.username}/status/{entity.tweet_id}"
            await page.goto(tweet_url, wait_until='networkidle', timeout=self.TIMEOUT)
            
            # 檢查推文文本是否存在
            text_elements = await page.query_selector_all('[data-testid="tweet"]')
            
            for elem in text_elements:
                text = await elem.inner_text()
                if entity.text[:50] in text:  # 部分匹配前 50 個字符
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"驗證推文失敗: {e}")
            return False
    
    async def scrape(
        self,
        labels_to_scrape: List[dict],
        max_data_entities: int = 100,
    ) -> List[XContent]:
        """爬取推文"""
        try:
            all_tweets = []
            
            for label_config in labels_to_scrape:
                labels = label_config.get('label_choices', [])
                
                for label in labels:
                    tweets = await self._search_tweets(
                        query=label,
                        max_results=max_data_entities // len(labels),
                    )
                    all_tweets.extend(tweets)
            
            return all_tweets[:max_data_entities]
            
        except Exception as e:
            logger.error(f"爬取失敗: {e}")
            return []
        
        finally:
            await self._close_browser()
    
    async def on_demand_scrape(
        self,
        usernames: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        url: Optional[str] = None,
        keyword_mode: KeywordMode = "all",
        start_datetime: dt.datetime = None,
        end_datetime: dt.datetime = None,
        limit: int = 100,
    ) -> List[XContent]:
        """按需爬取
        
        Args:
            usernames: List of target usernames
            keywords: List of keywords to search for
            url: Single tweet URL for direct tweet lookup
            keyword_mode: "any" (OR logic) or "all" (AND logic) for keyword matching
            start_datetime: Earliest datetime for content (UTC)
            end_datetime: Latest datetime for content (UTC)
            limit: Maximum number of items to return
        """
        try:
            logger.info(f"🚀 [X] on_demand_scrape 啟動: usernames={usernames}, keywords={keywords}, url={url}, limit={limit}")
            all_tweets = []
            
            # 爬取指定用戶的推文
            if usernames:
                logger.debug(f"👤 [X] 爬取指定用戶推文: {usernames}")
                batch_size = limit // len(usernames) if usernames else limit
                for username in usernames:
                    logger.debug(f"👤 [X] 搜尋用戶: {username}")
                    tweets = await self._search_tweets(
                        query=f"from:{username}",
                        max_results=batch_size,
                    )
                    logger.debug(f"✅ [X] 用戶 {username} 獲得 {len(tweets)} 條推文")
                    all_tweets.extend(tweets)
            
            # 爬取單個 URL 的推文
            if url:
                logger.debug(f"🔗 [X] 爬取 URL 推文: {url}")
                tweets = await self._search_tweets(
                    query=f"url:{url}",
                    max_results=limit // 2 if keywords else limit,
                )
                logger.debug(f"✅ [X] URL 查詢獲得 {len(tweets)} 條推文")
                all_tweets.extend(tweets)
            
            # 爬取包含關鍵字的推文
            if keywords:
                logger.debug(f"🔑 [X] 爬取關鍵字推文: {keywords}, mode={keyword_mode}")
                batch_size = limit // len(keywords) if keywords else limit
                if keyword_mode == "all":
                    # AND logic - search for all keywords together
                    query = " ".join(keywords)
                    logger.debug(f"🔑 [X] AND 模式查詢: {query}")
                    tweets = await self._search_tweets(
                        query=query,
                        max_results=batch_size,
                    )
                    logger.debug(f"✅ [X] AND 查詢獲得 {len(tweets)} 條推文")
                    all_tweets.extend(tweets)
                else:
                    # OR logic - search for each keyword separately
                    for keyword in keywords:
                        logger.debug(f"🔑 [X] OR 模式搜尋關鍵字: {keyword}")
                        tweets = await self._search_tweets(
                            query=keyword,
                            max_results=batch_size,
                        )
                        logger.debug(f"✅ [X] 關鍵字 {keyword} 獲得 {len(tweets)} 條推文")
                        all_tweets.extend(tweets)
            
            logger.debug(f"📊 [X] 全部推文: {len(all_tweets)}，開始過濾...")
            
            # Filter by date range if provided
            if start_datetime or end_datetime:
                logger.debug(f"📅 [X] 過濾日期範圍: {start_datetime} - {end_datetime}")
                filtered_tweets = []
                for tweet in all_tweets:
                    tweet_time = tweet.timestamp  # 使用 timestamp 而不是 created_at
                    if start_datetime and tweet_time < start_datetime:
                        continue
                    if end_datetime and tweet_time > end_datetime:
                        continue
                    filtered_tweets.append(tweet)
                logger.debug(f"✅ [X] 日期過濾後: {len(filtered_tweets)} 條推文")
                all_tweets = filtered_tweets
            
            result = all_tweets[:limit]
            logger.info(f"✅ [X] on_demand_scrape 完成: {len(result)} 條推文返回")
            return result
            
        except Exception as e:
            logger.error(f"❌ [X] on_demand_scrape 失敗: {e}")
            return []
        
        finally:
            await self._close_browser()
