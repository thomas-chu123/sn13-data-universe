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
from bittensor.core.metagraph import Metagraph

from common.data import DataEntity, DataSource, DataEntityBucket
from common.protocol import KeywordMode
from scraping.scraper import Scraper, ScraperId, ValidationResult
from scraping.playwright_auth_helper import PlaywrightAuthHelper

logger = logging.getLogger(__name__)


class XContent(DataEntity):
    """X/Twitter 推文內容"""
    
    tweet_id: str
    username: str
    text: str
    created_at: datetime
    likes: int
    retweets: int
    replies: int
    hashtags: List[str]
    urls: List[str]
    

class XPlaywrightScraper(Scraper):
    """使用 Playwright 的 X/Twitter Scraper - 完全免費，無需 API 密鑰"""
    
    TWITTER_URL = "https://twitter.com"
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
                logger.warning("未設置 TWITTER_USERNAME 或 TWITTER_PASSWORD，使用未登入模式")
                return
            
            logger.info("嘗試自動登入 Twitter...")
            success = await PlaywrightAuthHelper.login_twitter(
                self.page,
                twitter_username,
                twitter_password,
                timeout=self.TIMEOUT
            )
            
            if success:
                self.is_logged_in = True
                logger.info("✅ Twitter 自動登入成功")
            else:
                logger.warning("⚠️ Twitter 自動登入失敗，繼續使用未登入模式")
                
        except Exception as e:
            logger.error(f"自動登入異常: {e}")
            logger.warning("⚠️ 繼續使用未登入模式")
    
    async def _search_tweets(
        self,
        query: str,
        max_results: int = 20,
        days_back: int = 7
    ) -> List[XContent]:
        """搜尋推文"""
        try:
            page = await self._get_page()
            
            # 構建搜尋 URL
            search_query = f"{query} lang:en -is:retweet -is:reply"
            search_url = f"{self.TWITTER_URL}/search?q={quote(search_query)}&f=live"
            
            logger.info(f"搜尋: {search_query}")
            await page.goto(search_url, wait_until='networkidle', timeout=self.TIMEOUT)
            
            # 等待推文加載
            await page.wait_for_selector('article', timeout=10000)
            
            tweets = []
            
            # 滾動頁面以加載更多推文
            for _ in range(max_results // 5):
                # 提取當前可見的推文
                tweet_elements = await page.query_selector_all('article')
                
                for element in tweet_elements:
                    if len(tweets) >= max_results:
                        break
                    
                    try:
                        tweet_data = await self._extract_tweet_data(element)
                        if tweet_data:
                            tweets.append(tweet_data)
                    except Exception as e:
                        logger.warning(f"提取推文失敗: {e}")
                        continue
                
                if len(tweets) >= max_results:
                    break
                
                # 滾動以加載更多
                await page.evaluate('window.scrollBy(0, window.innerHeight)')
                await asyncio.sleep(1)
            
            logger.info(f"找到 {len(tweets)} 條推文")
            return tweets[:max_results]
            
        except Exception as e:
            logger.error(f"搜尋失敗: {e}")
            return []
    
    async def _extract_tweet_data(self, element) -> Optional[XContent]:
        """從元素提取推文數據"""
        try:
            # 提取推文文本
            text_elem = await element.query_selector('[data-testid="tweet"]')
            text = await text_elem.inner_text() if text_elem else ""
            
            if not text:
                return None
            
            # 提取用戶名
            username_elem = await element.query_selector('a[href*="/"]')
            username = ""
            if username_elem:
                href = await username_elem.get_attribute('href')
                username = href.split('/')[-1] if href else ""
            
            # 提取推文 ID
            article_elem = element
            article_id = await article_elem.get_attribute('data-testid')
            tweet_id = article_id.split('-')[-1] if article_id else ""
            
            # 提取統計數據
            likes = await self._get_stat_count(element, 'Like')
            retweets = await self._get_stat_count(element, 'Retweet')
            replies = await self._get_stat_count(element, 'Reply')
            
            # 提取主題標籤
            hashtags = self._extract_hashtags(text)
            
            # 提取 URL
            urls = self._extract_urls(text)
            
            return XContent(
                tweet_id=tweet_id,
                username=username,
                text=text,
                created_at=datetime.utcnow(),
                likes=likes,
                retweets=retweets,
                replies=replies,
                hashtags=hashtags,
                urls=urls,
                data_source=DataSource.X,
            )
            
        except Exception as e:
            logger.warning(f"提取推文數據失敗: {e}")
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
                    content_size += sum(len(h.encode('utf-8')) for h in entity.hashtags)
                    
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
            all_tweets = []
            
            # 爬取指定用戶的推文
            if usernames:
                batch_size = limit // len(usernames) if usernames else limit
                for username in usernames:
                    tweets = await self._search_tweets(
                        query=f"from:{username}",
                        max_results=batch_size,
                    )
                    all_tweets.extend(tweets)
            
            # 爬取單個 URL 的推文
            if url:
                tweets = await self._search_tweets(
                    query=f"url:{url}",
                    max_results=limit // 2 if keywords else limit,
                )
                all_tweets.extend(tweets)
            
            # 爬取包含關鍵字的推文
            if keywords:
                batch_size = limit // len(keywords) if keywords else limit
                if keyword_mode == "all":
                    # AND logic - search for all keywords together
                    query = " ".join(keywords)
                    tweets = await self._search_tweets(
                        query=query,
                        max_results=batch_size,
                    )
                    all_tweets.extend(tweets)
                else:
                    # OR logic - search for each keyword separately
                    for keyword in keywords:
                        tweets = await self._search_tweets(
                            query=keyword,
                            max_results=batch_size,
                        )
                        all_tweets.extend(tweets)
            
            # Filter by date range if provided
            if start_datetime or end_datetime:
                filtered_tweets = []
                for tweet in all_tweets:
                    tweet_time = dt.datetime.fromisoformat(tweet.created_at.replace('Z', '+00:00'))
                    if start_datetime and tweet_time < start_datetime:
                        continue
                    if end_datetime and tweet_time > end_datetime:
                        continue
                    filtered_tweets.append(tweet)
                all_tweets = filtered_tweets
            
            return all_tweets[:limit]
            
        except Exception as e:
            logger.error(f"按需爬取失敗: {e}")
            return []
        
        finally:
            await self._close_browser()
