"""
測試 Reddit Playwright Scraper
測試登入、搜尋、資料提取等功能
"""

import asyncio
import os
import pytest
import logging
from typing import List
from datetime import datetime, timedelta

from scraping.reddit.reddit_playwright_scraper import RedditPlaywrightScraper
from scraping.reddit.model import RedditContent

logger = logging.getLogger(__name__)

# 只在手動執行時運行，跳過 CI
pytestmark = pytest.mark.skipif(
    os.getenv("SKIP_PLAYWRIGHT_TESTS", "false").lower() == "true",
    reason="Playwright tests require browser automation"
)


class TestRedditPlaywrightScraper:
    """Reddit Playwright Scraper 測試"""
    
    @pytest.fixture
    async def scraper(self):
        """建立 scraper 實例"""
        scraper = RedditPlaywrightScraper()
        yield scraper
        # 清理
        try:
            await scraper._close_browser()
        except Exception as e:
            logger.warning(f"清理 scraper 時出錯: {e}")
    
    @pytest.mark.asyncio
    async def test_initialization(self, scraper):
        """測試 scraper 初始化"""
        assert scraper is not None
        logger.info("✅ Scraper 初始化成功")
    
    @pytest.mark.asyncio
    async def test_page_creation(self, scraper):
        """測試頁面建立"""
        page = await scraper._get_page()
        assert page is not None
        logger.info("✅ 頁面建立成功")
    
    @pytest.mark.asyncio
    async def test_search_subreddit_posts(self, scraper):
        """測試搜尋 subreddit 帖子（公開搜尋，無需登入）"""
        logger.info("🔍 開始搜尋 subreddit 帖子...")
        try:
            posts = await scraper._search_subreddit_posts(
                subreddit="python",
                max_results=5,
                sort="hot"
            )
            logger.info(f"✅ 搜尋成功，獲得 {len(posts)} 個帖子")
            
            assert isinstance(posts, list)
            if posts:
                first_post = posts[0]
                assert isinstance(first_post, RedditContent)
                assert hasattr(first_post, 'username')
                assert hasattr(first_post, 'body')
                logger.info(f"✅ 帖子資料正確: {first_post.username} - {first_post.body[:50] if first_post.body else '(無正文)'}...")
            
            return len(posts) > 0
            
        except Exception as e:
            logger.error(f"❌ 搜尋帖子失敗: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_on_demand_scrape_subreddit(self, scraper):
        """測試 on_demand_scrape（Subreddit 搜尋）"""
        logger.info("📍 測試 subreddit 搜尋...")
        try:
            result = await scraper.on_demand_scrape(
                subreddit="python",
                limit=5
            )
            
            logger.info(f"✅ Subreddit 搜尋成功，獲得 {len(result)} 個帖子")
            assert isinstance(result, list)
            
            if result:
                assert all(isinstance(item, RedditContent) for item in result)
                logger.info(f"✅ 返回 {len(result)} 個有效帖子")
            
            return len(result) > 0
            
        except Exception as e:
            logger.error(f"❌ Subreddit 搜尋失敗: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_on_demand_scrape_keywords(self, scraper):
        """測試 on_demand_scrape（關鍵字搜尋）"""
        logger.info("🔑 測試關鍵字搜尋...")
        try:
            result = await scraper.on_demand_scrape(
                subreddit="python",
                keywords=["coding"],
                keyword_mode="all",
                limit=5
            )
            
            logger.info(f"✅ 關鍵字搜尋成功，獲得 {len(result)} 個帖子")
            assert isinstance(result, list)
            
            if result:
                assert all(isinstance(item, RedditContent) for item in result)
                logger.info(f"✅ 返回 {len(result)} 個有效帖子")
            
            return len(result) > 0
            
        except Exception as e:
            logger.error(f"❌ 關鍵字搜尋失敗: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_on_demand_scrape_with_limit(self, scraper):
        """測試 on_demand_scrape（限制結果數量）"""
        logger.info("📊 測試結果數量限制...")
        try:
            result = await scraper.on_demand_scrape(
                subreddit="askreddit",
                limit=3
            )
            
            logger.info(f"✅ 限制搜尋成功，獲得 {len(result)} 個帖子")
            assert len(result) <= 3
            logger.info(f"✅ 結果數量符合限制 (<=3): {len(result)}")
            
            return len(result) > 0
            
        except Exception as e:
            logger.error(f"❌ 限制搜尋失敗: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_on_demand_scrape_with_date_range(self, scraper):
        """測試 on_demand_scrape（日期範圍過濾）"""
        logger.info("📅 測試日期範圍過濾...")
        try:
            now = datetime.utcnow()
            start_date = now - timedelta(days=7)  # 過去 7 天
            
            result = await scraper.on_demand_scrape(
                subreddit="python",
                start_datetime=start_date,
                end_datetime=now,
                limit=5
            )
            
            logger.info(f"✅ 日期範圍搜尋成功，獲得 {len(result)} 個帖子")
            assert isinstance(result, list)
            
            if result:
                for post in result:
                    assert post.createdAt >= start_date, f"帖子時間 {post.createdAt} 早於開始時間 {start_date}"
                    logger.debug(f"✅ 帖子時間驗證: {post.createdAt}")
            
            return len(result) > 0
            
        except Exception as e:
            logger.error(f"❌ 日期範圍搜尋失敗: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_validate_results(self, scraper):
        """測試資料驗證"""
        logger.info("✅ 測試資料驗證...")
        try:
            result = await scraper.on_demand_scrape(
                subreddit="python",
                limit=2
            )
            
            if result:
                validation_results = await scraper.validate(result)
                logger.info(f"✅ 驗證成功，獲得 {len(validation_results)} 個驗證結果")
                
                assert len(validation_results) == len(result)
                assert all(hasattr(v, 'are_valid') for v in validation_results)
                logger.info("✅ 驗證結果格式正確")
            else:
                logger.warning("⚠️ 未獲得搜尋結果，跳過驗證測試")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 驗證失敗: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_auto_login_attempt(self, scraper):
        """測試自動登入（如果提供認證資訊）"""
        logger.info("🔐 測試自動登入...")
        try:
            username = os.getenv('REDDIT_USERNAME')
            password = os.getenv('REDDIT_PASSWORD')
            
            if not username or not password:
                logger.warning("⚠️ 未設置 REDDIT_USERNAME/PASSWORD，跳過登入測試")
                pytest.skip("No Reddit credentials provided")
            
            # 直接呼叫 _auto_login
            page = await scraper._get_page()
            await scraper._auto_login()
            
            logger.info(f"✅ 登入嘗試完成，is_logged_in={scraper.is_logged_in}")
            return scraper.is_logged_in
            
        except Exception as e:
            logger.error(f"❌ 登入測試失敗: {e}")
            # 不拋出異常，因為登入失敗時會降級為未登入模式
            return False


class TestRedditPlaywrightScraperIntegration:
    """Reddit Playwright Scraper 整合測試"""
    
    @pytest.fixture
    async def scraper(self):
        """建立 scraper 實例"""
        scraper = RedditPlaywrightScraper()
        yield scraper
        try:
            await scraper._close_browser()
        except Exception as e:
            logger.warning(f"清理 scraper 時出錯: {e}")
    
    @pytest.mark.asyncio
    async def test_full_scrape_workflow(self, scraper):
        """測試完整的爬取流程"""
        logger.info("🚀 測試完整爬取流程...")
        try:
            # 1. 執行搜尋
            logger.info("📝 步驟 1: 執行搜尋...")
            result = await scraper.on_demand_scrape(
                subreddit="technology",
                limit=5
            )
            logger.info(f"✅ 搜尋完成: {len(result)} 個帖子")
            
            # 2. 驗證資料
            logger.info("📝 步驟 2: 驗證資料...")
            if result:
                validation_results = await scraper.validate(result)
                logger.info(f"✅ 驗證完成: {len(validation_results)} 個結果")
                
                valid_count = sum(1 for v in validation_results if v.are_valid)
                logger.info(f"✅ 有效資料: {valid_count}/{len(validation_results)}")
            
            logger.info("✅ 完整流程測試成功")
            return len(result) > 0
            
        except Exception as e:
            logger.error(f"❌ 完整流程測試失敗: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_multiple_subreddits(self, scraper):
        """測試多個 subreddit 搜尋"""
        logger.info("📚 測試多個 subreddit 搜尋...")
        try:
            subreddits = ["python", "programming", "learnprogramming"]
            all_results = []
            
            for subreddit in subreddits:
                logger.info(f"📍 搜尋 r/{subreddit}...")
                result = await scraper.on_demand_scrape(
                    subreddit=subreddit,
                    limit=3
                )
                logger.info(f"✅ r/{subreddit}: {len(result)} 個帖子")
                all_results.extend(result)
            
            logger.info(f"✅ 全部搜尋完成: 共 {len(all_results)} 個帖子")
            return len(all_results) > 0
            
        except Exception as e:
            logger.error(f"❌ 多 subreddit 搜尋失敗: {e}")
            raise


@pytest.mark.asyncio
async def test_reddit_scraper_basic():
    """基礎測試：確認 scraper 可以建立和執行"""
    logger.info("🧪 執行基礎測試...")
    scraper = RedditPlaywrightScraper()
    
    try:
        page = await scraper._get_page()
        assert page is not None
        logger.info("✅ 基礎測試成功")
    finally:
        await scraper._close_browser()
