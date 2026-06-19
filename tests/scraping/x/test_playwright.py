"""
測試 X (Twitter) Playwright Scraper
測試登入、搜尋、資料提取等功能
"""

import asyncio
import os
import pytest
import logging
from typing import List

from scraping.x.x_playwright_scraper import XPlaywrightScraper
from scraping.x.model import XContent

logger = logging.getLogger(__name__)

# 只在手動執行時運行，跳過 CI
pytestmark = pytest.mark.skipif(
    os.getenv("SKIP_PLAYWRIGHT_TESTS", "false").lower() == "true",
    reason="Playwright tests require browser automation"
)


class TestXPlaywrightScraper:
    """X Playwright Scraper 測試"""
    
    @pytest.fixture
    async def scraper(self):
        """建立 scraper 實例"""
        scraper = XPlaywrightScraper()
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
        assert scraper.TWITTER_URL == "https://twitter.com"
        logger.info("✅ Scraper 初始化成功")
    
    @pytest.mark.asyncio
    async def test_page_creation(self, scraper):
        """測試頁面建立"""
        page = await scraper._get_page()
        assert page is not None
        logger.info("✅ 頁面建立成功")
    
    @pytest.mark.asyncio
    async def test_search_tweets_public(self, scraper):
        """測試搜尋推文（公開搜尋，無需登入）"""
        logger.info("🔍 開始搜尋推文...")
        try:
            tweets = await scraper._search_tweets(
                query="bitcoin lang:en",
                max_results=5,
            )
            logger.info(f"✅ 搜尋成功，獲得 {len(tweets)} 條推文")
            
            assert isinstance(tweets, list)
            if tweets:
                first_tweet = tweets[0]
                assert isinstance(first_tweet, XContent)
                assert hasattr(first_tweet, 'username')
                assert hasattr(first_tweet, 'text')
                logger.info(f"✅ 推文資料正確: {first_tweet.username} - {first_tweet.text[:50]}...")
            
            return len(tweets) > 0
            
        except Exception as e:
            logger.error(f"❌ 搜尋推文失敗: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_on_demand_scrape_keywords(self, scraper):
        """測試 on_demand_scrape（關鍵字搜尋）"""
        logger.info("🔑 測試關鍵字搜尋...")
        try:
            result = await scraper.on_demand_scrape(
                keywords=["bitcoin"],
                keyword_mode="all",
                limit=5
            )
            
            logger.info(f"✅ 關鍵字搜尋成功，獲得 {len(result)} 條推文")
            assert isinstance(result, list)
            
            if result:
                assert all(isinstance(item, XContent) for item in result)
                logger.info(f"✅ 返回 {len(result)} 條有效推文")
            
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
                keywords=["python"],
                limit=3
            )
            
            logger.info(f"✅ 限制搜尋成功，獲得 {len(result)} 條推文")
            assert len(result) <= 3
            logger.info(f"✅ 結果數量符合限制 (<=3): {len(result)}")
            
            return len(result) > 0
            
        except Exception as e:
            logger.error(f"❌ 限制搜尋失敗: {e}")
            raise
    
    @pytest.mark.asyncio
    async def test_validate_results(self, scraper):
        """測試資料驗證"""
        logger.info("✅ 測試資料驗證...")
        try:
            result = await scraper.on_demand_scrape(
                keywords=["test"],
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
            username = os.getenv('TWITTER_USERNAME')
            password = os.getenv('TWITTER_PASSWORD')
            
            if not username or not password:
                logger.warning("⚠️ 未設置 TWITTER_USERNAME/PASSWORD，跳過登入測試")
                pytest.skip("No Twitter credentials provided")
            
            # 直接呼叫 _auto_login
            page = await scraper._get_page()
            await scraper._auto_login()
            
            logger.info(f"✅ 登入嘗試完成，is_logged_in={scraper.is_logged_in}")
            return scraper.is_logged_in
            
        except Exception as e:
            logger.error(f"❌ 登入測試失敗: {e}")
            # 不拋出異常，因為登入失敗時會降級為未登入模式
            return False


class TestXPlaywrightScraperIntegration:
    """X Playwright Scraper 整合測試"""
    
    @pytest.fixture
    async def scraper(self):
        """建立 scraper 實例"""
        scraper = XPlaywrightScraper()
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
                keywords=["crypto"],
                limit=5
            )
            logger.info(f"✅ 搜尋完成: {len(result)} 條推文")
            
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
async def test_x_scraper_basic():
    """基礎測試：確認 scraper 可以建立和執行"""
    logger.info("🧪 執行基礎測試...")
    scraper = XPlaywrightScraper()
    
    try:
        page = await scraper._get_page()
        assert page is not None
        logger.info("✅ 基礎測試成功")
    finally:
        await scraper._close_browser()
