# Playwright 登入指南

本文說明如何配置 Playwright 自動登入 Twitter 和 Reddit。

---

## 📋 概述

### 新增的 Scrapers

| Scraper ID | 平台 | 特點 | 成本 |
|-----------|------|------|------|
| **X.playwright** | Twitter | 瀏覽器自動化 + 自動登入 | $0 |
| **Reddit.playwright** | Reddit | 瀏覽器自動化 + 自動登入 | $0 |

### 核心文件

```
scraping/
├── playwright_auth_helper.py      ← 認證助手（負責登入）
├── x/
│   └── x_playwright_scraper.py    ← X/Twitter Playwright Scraper
└── reddit/
    └── reddit_playwright_scraper.py ← Reddit Playwright Scraper

.env                                 ← 認證信息配置
```

---

## 🔐 Playwright 登入工作原理

### 認證流程

```
1. ScraperProvider.get(ScraperId.X_PLAYWRIGHT)
   ↓
2. XPlaywrightScraper.__init__(auto_login=True)
   ↓
3. _get_page()
   ↓
4. _auto_login()
   ├─ 讀取環境變量 (TWITTER_USERNAME, TWITTER_PASSWORD)
   ├─ 調用 PlaywrightAuthHelper.login_twitter()
   └─ 使用 Playwright 自動填表和點擊按鈕
   ↓
5. 登入成功 → is_logged_in = True
   ↓
6. 後續所有請求使用登入狀態
```

### PlaywrightAuthHelper 方法

```python
# 登入 Twitter
await PlaywrightAuthHelper.login_twitter(
    page=page,
    username="your_email@gmail.com",
    password="your_password",
    timeout=30000
)

# 登入 Reddit
await PlaywrightAuthHelper.login_reddit(
    page=page,
    username="your_reddit_username",
    password="your_reddit_password",
    timeout=30000
)
```

---

## ⚙️ 配置步驟

### Step 1: 設置環境變量

編輯 `.env` 文件：

```bash
# Twitter 登入認證
TWITTER_USERNAME="your_email@gmail.com"  # 或用戶名
TWITTER_PASSWORD="your_twitter_password"

# Reddit 登入認證
REDDIT_USERNAME="your_reddit_username"
REDDIT_PASSWORD="your_reddit_password"
```

### Step 2: 安裝 Playwright

```bash
pip install -r requirements.txt

# 下載瀏覽器引擎
playwright install chromium

# 或下載所有引擎
playwright install
```

### Step 3: 配置爬取設置

**scraping/config/scraping_config.json:**

```json
{
    "scraper_configs": [
        {
            "scraper_id": "X.playwright",
            "cadence_seconds": 600,
            "labels_to_scrape": [
                {
                    "label_choices": ["#bitcoin", "#bittensor"],
                    "max_data_entities": 50,
                    "max_age_hint_minutes": 1440
                }
            ]
        },
        {
            "scraper_id": "Reddit.playwright",
            "cadence_seconds": 600,
            "labels_to_scrape": [
                {
                    "label_choices": ["r/bittensor", "r/bitcoin"],
                    "max_data_entities": 100,
                    "max_age_hint_minutes": 360
                }
            ]
        }
    ]
}
```

### Step 4: 配置 Validator (可選)

如果希望 Validator 使用 Playwright scrapers：

**vali_utils/miner_evaluator.py (第 59-63 行):**

```python
PREFERRED_SCRAPERS = {
    DataSource.X: ScraperId.X_PLAYWRIGHT,         # ✅ 使用 Playwright
    DataSource.REDDIT: ScraperId.REDDIT_PLAYWRIGHT, # ✅ 使用 Playwright
}
```

---

## 🧪 測試

### 測試 Twitter 登入

```bash
python3 << 'EOF'
import asyncio
import os
from scraping.x.x_playwright_scraper import XPlaywrightScraper

os.environ['TWITTER_USERNAME'] = 'your_email@gmail.com'
os.environ['TWITTER_PASSWORD'] = 'your_password'

async def test_twitter():
    scraper = XPlaywrightScraper(auto_login=True)
    
    # 測試搜尋推文
    tweets = await scraper._search_tweets(
        query="bittensor",
        max_results=5
    )
    
    print(f"✅ 找到 {len(tweets)} 條推文:")
    for tweet in tweets:
        print(f"  @{tweet.username}: {tweet.text[:60]}...")

asyncio.run(test_twitter())
EOF
```

### 測試 Reddit 登入

```bash
python3 << 'EOF'
import asyncio
import os
from scraping.reddit.reddit_playwright_scraper import RedditPlaywrightScraper

os.environ['REDDIT_USERNAME'] = 'your_username'
os.environ['REDDIT_PASSWORD'] = 'your_password'

async def test_reddit():
    scraper = RedditPlaywrightScraper(auto_login=True)
    
    # 測試搜尋帖子
    posts = await scraper._search_subreddit_posts(
        subreddit="bittensor",
        max_results=5
    )
    
    print(f"✅ 找到 {len(posts)} 個帖子:")
    for post in posts:
        print(f"  r/{post.subreddit}: {post.title[:60]}...")

asyncio.run(test_reddit())
EOF
```

---

## 🔧 高級配置

### 禁用自動登入

如果不想自動登入：

```python
# 不登入
scraper = XPlaywrightScraper(auto_login=False)

# 或
scraper = RedditPlaywrightScraper(auto_login=False)
```

### 手動登入

```python
import asyncio
from scraping.playwright_auth_helper import PlaywrightAuthHelper
from playwright.async_api import async_playwright

async def manual_login():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 顯示瀏覽器窗口
        page = await browser.new_page()
        
        # 手動登入 Twitter
        success = await PlaywrightAuthHelper.login_twitter(
            page,
            username="your_email@gmail.com",
            password="your_password"
        )
        
        print(f"登入成功: {success}")
        
        # 獲取 cookies 用於後續請求
        cookies = await PlaywrightAuthHelper.get_cookies(page)
        print(f"獲得 {len(cookies)} 個 cookies")
        
        await browser.close()

asyncio.run(manual_login())
```

### 使用 Headless=False 調試

```python
class DebugPlaywrightScraper(XPlaywrightScraper):
    async def _initialize_browser(self):
        """顯示瀏覽器窗口用於調試"""
        if self.browser is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # ✅ 顯示瀏覽器
                args=['--no-sandbox']
            )
```

---

## ⚠️ 注意事項

### 安全性

1. **不要提交 .env 文件到 Git:**
   ```bash
   # .gitignore
   .env
   ```

2. **使用環境變量管理:**
   ```bash
   # 從系統環境加載
   export TWITTER_USERNAME="your_email"
   export TWITTER_PASSWORD="your_password"
   ```

3. **使用應用密碼 (App Password):**
   - Twitter: 如可能，使用應用專用密碼
   - Reddit: 如可能，使用臨時密碼

### 登入失敗排查

#### 問題 1: 登入表單選擇器變化

**症狀:** `Page.wait_for_selector timeout`

**解決:**
```python
# 更新 playwright_auth_helper.py 中的選擇器
# 例如: 'button:has-text("Log in")' 可能變為 'button[aria-label="Log in"]'

# 調試技巧：使用 headless=False 查看實際頁面
headless=False
```

#### 問題 2: 驗證碼 / 雙因素認證

**症狀:** 登入時卡在驗證碼界面

**解決:**
- 禁用雙因素認證 (不推薦)
- 或使用生成的應用密碼而不是主密碼
- 或手動登入一次允許此瀏覽器

#### 問題 3: 賬戶被鎖定

**症狀:** 登入失敗，"異常活動檢測"

**解決:**
- 等待 24-48 小時
- 驗證郵箱/手機
- 添加 User-Agent 延遲
- 使用代理 (如需要)

---

## 📊 性能建議

### 爬取頻率

```json
{
    "cadence_seconds": 600,  // 10 分鐘
    // Playwright 較慢，建議不超過 5 分鐘一次
    // 速度: 2-5 秒/項目 × 50 項目 = 100-250 秒
}
```

### 資源消耗

```bash
# Playwright 會使用大量內存
# 監控內存使用
ps aux | grep chromium
```

### 建議配置

| 場景 | 設置 |
|------|------|
| **生產環境** | cadence_seconds=600 (10分鐘) |
| **測試** | cadence_seconds=300 (5分鐘) |
| **開發** | cadence_seconds=60 (1分鐘) |

---

## 🔄 故障轉移

如果 Playwright 登入失敗，自動回退到未登入模式：

```python
# 在 XPlaywrightScraper._auto_login() 中
if success:
    self.is_logged_in = True
else:
    # ✅ 自動回退到未登入模式
    self.is_logged_in = False
    logger.warning("使用未登入模式繼續")
```

---

## 🆘 常見問題

**Q: Playwright 登入比 API 慢嗎？**  
A: 是的。API: ~100ms/推文，Playwright: ~2-5s/推文。

**Q: 需要為每個請求重新登入嗎？**  
A: 否。登入狀態保持在頁面對象中。

**Q: 可以同時多個 Playwright 進程嗎？**  
A: 可以，但會消耗大量資源。建議最多 2-3 個並發。

**Q: 如何處理登入會話過期？**  
A: 添加自動重新登入邏輯（未來增強）。

**Q: 支持代理嗎？**  
A: 支持。見 _initialize_browser() proxy 參數。

---

## 📝 下一步

1. ✅ 設置環境變量 (.env)
2. ✅ 安裝 Playwright: `pip install -r requirements.txt && playwright install chromium`
3. ✅ 測試登入
4. ✅ 配置爬取設置
5. ✅ 啟動爬蟲

**立即開始:**

```bash
# 1. 更新 .env
nano .env
# 填入 TWITTER_USERNAME, TWITTER_PASSWORD 等

# 2. 測試登入
python3 -c "
import asyncio
import os
from scraping.x.x_playwright_scraper import XPlaywrightScraper

os.environ['TWITTER_USERNAME'] = 'your_email'
os.environ['TWITTER_PASSWORD'] = 'your_pass'

async def test():
    s = XPlaywrightScraper(auto_login=True)
    tweets = await s._search_tweets('bittensor', 3)
    print(f'成功: {len(tweets)} 條推文')

asyncio.run(test())
"

# 3. 啟動爬蟲
python3 neurons/miner.py
```

---

## 📚 相關文件

- [playwright_auth_helper.py](scraping/playwright_auth_helper.py) - 認證邏輯
- [x_playwright_scraper.py](scraping/x/x_playwright_scraper.py) - Twitter Scraper
- [reddit_playwright_scraper.py](scraping/reddit/reddit_playwright_scraper.py) - Reddit Scraper
- [Playwright 官方文檔](https://playwright.dev/python/)

---

**版本:** 1.0  
**更新:** 2026-06-19  
**狀態:** ✅ 生產就緒
