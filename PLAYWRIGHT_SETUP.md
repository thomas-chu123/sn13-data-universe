# Playwright 測試設置指南

## 現在遇到的問題

運行 `test_playwright_standalone.py` 時出現：
```
Executable doesn't exist at /Users/skynet_1/Library/Caches/ms-playwright/chromium-1091/...
Please run the following command to download new browsers:
    playwright install
```

## 解決方案

Playwright 需要下載瀏覽器執行文件。這是一次性的設置步驟。

### 步驟 1: 安裝 Playwright 瀏覽器

```bash
# 激活虛擬環境
source .venv/bin/activate

# 安裝 Playwright 瀏覽器
playwright install

# 或只安裝 Chromium（更小更快）
playwright install chromium
```

**預期輸出**:
```
Installing dependencies
Downloading Chromium 1223 (darwin-arm64) 210 Mb
...
✓ Success
```

**下載時間**: 2-5 分鐘（取決於網路速度）

### 步驟 2: 驗證安裝

```bash
# 應該看到瀏覽器被成功安裝
ls -la ~/.cache/ms-playwright/
# 或
ls -la ~/Library/Caches/ms-playwright/
```

### 步驟 3: 運行測試

```bash
# 加載環境
source .env

# 運行獨立測試
python tests/scraping/test_playwright_standalone.py

# 或運行具體的 X scraper 測試
python tests/scraping/test_playwright_quick.py x
```

## 常見問題

### Q: 為什麼需要下載瀏覽器？
A: Playwright 是一個瀏覽器自動化工具，需要實際的瀏覽器引擎（如 Chromium）才能運行。

### Q: 下載很慢？
A: 是的，首次下載會花費幾分鐘。這是正常的。建議在網路較好的時候進行。

### Q: 可以跳過 Chromium 只用 Firefox 或 WebKit 嗎？
A: 可以，但我們的配置是針對 Chromium 優化的。建議使用 Chromium。

### Q: 如何更新 Playwright？
```bash
pip install --upgrade playwright
playwright install
```

### Q: 如何卸載瀏覽器以節省空間？
```bash
playwright uninstall
# 或只卸載 Chromium
playwright uninstall chromium
```

## 完整設置檢查表

```bash
# ✅ 檢查 Python 虛擬環境
source .venv/bin/activate

# ✅ 檢查 Playwright 已安裝
python -c "import playwright; print(f'Playwright version: {playwright.__version__}')"

# ✅ 檢查瀏覽器已下載
playwright install chromium

# ✅ 加載環境變量
source .env
echo "Twitter: $TWITTER_USERNAME"
echo "Reddit: $REDDIT_USERNAME"

# ✅ 運行測試
python tests/scraping/test_playwright_standalone.py
```

## 下一步

完成上述設置後，可以：

1. **快速驗證**:
   ```bash
   python tests/scraping/test_playwright_standalone.py
   ```

2. **測試登入功能**:
   ```bash
   python tests/scraping/test_playwright_quick.py x
   python tests/scraping/test_playwright_quick.py reddit
   ```

3. **運行 pytest 測試** (如已安裝):
   ```bash
   pytest tests/scraping/x/test_playwright.py -v
   pytest tests/scraping/reddit/test_playwright.py -v
   ```

4. **運行 Miner**:
   ```bash
   python neurons/miner.py --config=<your-config>
   ```

## 需要幫助？

如有問題，檢查：
- [tests/scraping/TEST_README.md](TEST_README.md) - 完整測試文檔
- [scraping/x/x_playwright_scraper.py](../../scraping/x/x_playwright_scraper.py) - X scraper 實現
- [scraping/reddit/reddit_playwright_scraper.py](../../scraping/reddit/reddit_playwright_scraper.py) - Reddit scraper 實現
