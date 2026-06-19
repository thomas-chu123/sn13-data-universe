#!/usr/bin/env python3
"""
Playwright Scrapers 測試指南
=============================

本目錄包含用於測試 X (Twitter) 和 Reddit Playwright Scrapers 的測試套件。
"""

# TEST_README

## 快速開始

### 1. 設置環境變量

首先，確保在 `.env` 文件中設置了認證資訊：

```bash
# .env 文件
export TWITTER_USERNAME="your_twitter_username"
export TWITTER_PASSWORD="your_twitter_password"
export REDDIT_USERNAME="your_reddit_username"
export REDDIT_PASSWORD="your_reddit_password"
```

加載環境變量：
```bash
source .env
```

### 2. 快速測試（推薦）

**測試 X Scraper：**
```bash
python tests/scraping/test_playwright_quick.py x
```

**測試 Reddit Scraper：**
```bash
python tests/scraping/test_playwright_quick.py reddit
```

**同時測試兩者：**
```bash
python tests/scraping/test_playwright_quick.py all
```

或简单地：
```bash
python tests/scraping/test_playwright_quick.py
```

### 3. Pytest 測試

安裝依賴：
```bash
pip install pytest pytest-asyncio
```

運行 pytest 測試：
```bash
# 測試 X Scraper
pytest tests/scraping/x/test_playwright.py -v

# 測試 Reddit Scraper
pytest tests/scraping/reddit/test_playwright.py -v

# 運行所有 Playwright 測試
pytest tests/scraping/x/test_playwright.py tests/scraping/reddit/test_playwright.py -v
```

### 4. 診斷 Reddit 登入問題

如果 Reddit 登入超時，可以使用診斷腳本：

```bash
python tests/scraping/test_reddit_login_diagnose.py
```

這個腳本會以非無頭模式運行瀏覽器，這樣你可以看到實際的登入過程。

## 測試文件說明

### test_playwright_quick.py
- **用途**: 快速測試登入和數據獲取功能
- **特點**: 簡單、易於理解、快速反饋
- **測試內容**:
  - 頁面建立
  - 自動登入（如果提供認證資訊）
  - 搜尋功能
  - on_demand_scrape 功能
  - 數據驗證

**運行時間**: ~30-60 秒（取決於網路速度和登入時間）

### test_playwright.py (在 x/ 和 reddit/ 子目錄中)
- **用途**: 綜合測試 Scraper 的所有功能
- **測試類型**:
  - 單元測試：測試個別功能
  - 整合測試：測試完整流程

**特點**:
- 使用 pytest + pytest-asyncio
- 可跳過（使用 `--skipif` 標誌）
- 支持 CI/CD 集成

### test_reddit_login_diagnose.py
- **用途**: 診斷 Reddit 登入問題
- **特點**:
  - 非無頭模式（可以看到瀏覽器）
  - 詳細的日誌輸出
  - 持續 30 秒讓你檢查頁面狀態

## 預期結果

### 成功的登入
```
🔐 [Twitter] 開始登入 (thomas2chu)...
🌐 [Twitter] 導航到登入頁面...
✅ [Twitter] 登入頁面已加載
...
✅ [Twitter] 登入成功 - 已離開登入流程 (URL: https://twitter.com/home)
```

### 登入失敗或超時（但仍然繼續）
```
🔐 [Twitter] 開始登入 (thomas2chu)...
...
⚠️ [Twitter] 頁面加載超時
📍 [Twitter] 當前 URL: https://twitter.com/i/flow/login
⚠️ [Twitter] 仍在登入頁面
⚠️ [Twitter] Twitter 自動登入失敗，將繼續使用未登入模式
```

### 未登入模式（成功）
```
⚠️ [X] 未設置 TWITTER_USERNAME 或 TWITTER_PASSWORD，使用未登入模式
🔍 [X] 搜尋推文: query='bitcoin', max_results=3
✅ [X] 頁面已加載
✅ [X] 推文元素已加載
✅ [X] 找到 3 條推文
```

## 常見問題

### 1. 登入超時

**症狀**:
```
Twitter 登入失敗: Timeout 60000ms exceeded.
```

**解決方案**:
- 檢查網路連接
- 確認 TWITTER_USERNAME/PASSWORD 正確
- 嘗試手動登入檢查認證資訊是否有效
- 使用診斷腳本確認登入流程

### 2. 元素未找到

**症狀**:
```
❌ [X] 用戶名輸入框未找到
```

**原因**: Twitter/Reddit 頁面結構可能已更改

**解決方案**:
- 檢查 PlaywrightAuthHelper 中的選擇器是否仍然有效
- 使用診斷腳本查看實際的頁面結構

### 3. 搜尋結果為空

**症狀**:
```
✅ 搜尋成功，獲得 0 條推文
```

**原因**: 
- 搜尋查詢無匹配結果
- 頁面未完全加載
- 需要登入才能看到結果

**解決方案**:
- 嘗試不同的搜尋關鍵字
- 確保登入功能正常工作

## 改進建議

1. **登入增強**:
   - 實現驗證碼識別
   - 支持 2FA（雙因子認證）
   - 保存 cookies 以加快後續登入

2. **穩定性改進**:
   - 添加重試邏輯
   - 實現指數退避
   - 添加更詳細的錯誤日誌

3. **性能優化**:
   - 使用瀏覽器連接池
   - 並行測試多個 Scraper
   - 緩存登入狀態

## 支持

如有問題，請查看：
- X Scraper: `scraping/x/x_playwright_scraper.py`
- Reddit Scraper: `scraping/reddit/reddit_playwright_scraper.py`
- Auth Helper: `scraping/playwright_auth_helper.py`
