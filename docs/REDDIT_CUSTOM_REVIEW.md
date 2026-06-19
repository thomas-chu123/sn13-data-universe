# Reddit.custom 爬蟲功能審查報告

## 1. 總體評估
✅ **Reddit.custom 功能完整，能充分滿足當前的 Reddit 爬取需求**

---

## 2. 核心功能分析

### 2.1 基本爬取功能 (Scrape)
**功能**: `scrape(scrape_config: ScrapeConfig) -> List[DataEntity]`

#### 支持特性
- ✅ 按子版塊(subreddit)爬取
- ✅ 支持"新"、"熱"、"熱門"三種排序
- ✅ 支持時間範圍過濾
- ✅ 隨機選擇帖子或評論（降低 API 調用）
- ✅ NSFW+媒體內容過濾
- ✅ 錯誤恢復和詳細日誌記錄

#### 排序模式
```python
case "new":      # 最新
case "top":      # 熱門 (支持時間濾波: 小時/天/週/月/年)
case "hot":      # 熱 (即時排序)
```

#### 限制
- ⚠️ 一次只能爬取 1 個子版塊（需要在labels中指定）
- ⚠️ 隨機帖子/評論切換（不可控）

---

### 2.2 按需爬取功能 (On-Demand Scrape)
**功能**: `on_demand_scrape(usernames, subreddit, keywords, ...) -> List[DataEntity]`

#### 支持的查詢條件
- ✅ **按用戶**: `usernames=['user1', 'user2']` - 爬取多個用戶內容 (OR邏輯)
- ✅ **按子版塊**: `subreddit='python'` - 指定具體子版塊
- ✅ **按關鍵字**: `keywords=['async', 'await']` - 支持AND/OR邏輯
- ✅ **時間範圍**: `start_datetime`, `end_datetime` - 完全支持
- ✅ **結果限制**: `limit` - 可控制返回數量

#### 關鍵字模式
```python
keyword_mode="all"   # AND邏輯: 所有關鍵字都必須出現
keyword_mode="any"   # OR邏輯: 任意關鍵字出現即可
```

#### 用途示例
```python
# 爬取特定用戶的內容
await scraper.on_demand_scrape(
    usernames=['gvanrossum', 'guido'],
    limit=100
)

# 爬取特定話題
await scraper.on_demand_scrape(
    subreddit='python',
    keywords=['asyncio', 'concurrent'],
    keyword_mode='any',
    start_datetime=datetime(...),
    end_datetime=datetime(...)
)

# 綜合搜索
await scraper.on_demand_scrape(
    usernames=['techuser'],
    keywords=['python', 'rust'],
    keyword_mode='all'
)
```

---

### 2.3 驗證功能 (Validate)
**功能**: `validate(entities: List[DataEntity]) -> List[ValidationResult]`

#### 驗證層次
1. **URI 驗證**: 確保是有效的 Reddit URL
2. **內容解碼**: 從 DataEntity 恢復 RedditContent
3. **即時獲取**: 從 Reddit 獲取最新數據進行對比
4. **字段驗證**: 逐字段比對
   - ID、URL、用戶名、社區、內容、時間戳
   - 帖子專用: 標題
   - 評論專用: 父ID
5. **媒體驗證**: 嚴格檢查媒體 URL 有效性
6. **NSFW 驗證**: NSFW 內容處理
7. **時間戳驗證**: 確保按分鐘混淆

#### 驗證規則
```
✅ 基本檢查:
  - 檢查 Reddit ID 是否匹配
  - 檢查 URL 是否匹配
  - 檢查用戶名是否匹配
  - 檢查社區是否匹配
  - 檢查內容是否匹配

⏱️  時間戳檢查:
  - 必須按分鐘混淆 (秒和微秒 = 0)
  - 必須 >= 創建時間
  - 必須 <= 當前時間

🔒 NSFW+媒體檢查:
  - NSFW 內容 + 媒體 = 拒絕

🔍 媒體驗證:
  - 防止虛假媒體 URL
```

---

## 3. 內容提取能力

### 3.1 提取的字段
```
帖子 (Submission):
  - id, url, username, community
  - body (自文本)
  - created_at, data_type
  - title (帖子標題)
  - media (媒體 URL 列表)
  - is_nsfw
  - score (投票數)
  - upvote_ratio (讚比)
  - num_comments (評論數)
  - scraped_at (爬取時間)

評論 (Comment):
  - id, url, username, community
  - body (評論內容)
  - created_at, data_type
  - parent_id (父評論/帖子 ID)
  - is_nsfw (繼承自帖子或子版塊)
  - score (評論投票)
  - scraped_at
```

### 3.2 特殊處理
- ✅ 已刪除用戶檢測: `[deleted]`
- ✅ NSFW 檢查: 兼容帖子和評論級別
- ✅ 永久鏈接規范化
- ✅ 媒體 URL 提取 (包括 Reddit Gallery)

---

## 4. 性能特性

### 4.1 並發性
- ✅ 完全異步實現 (asyncpraw)
- ✅ 支持多個並發請求
- ✅ 內置 API 速率限制處理

### 4.2 效率
- ✅ 隨機帖子/評論選擇減少 API 調用
- ✅ 批量爬取支持
- ✅ NSFW+媒體過濾提早篩選

### 4.3 限制
- ℹ️ Reddit API 速率限制: 60 請求/分鐘

---

## 5. 錯誤處理

### 5.1 實現情況
- ✅ 完整的異常捕獲
- ✅ 詳細的日誌記錄 (trace/debug/warning/error)
- ✅ Best-effort 解析 (拒絕無效數據)
- ✅ 用戶連接失敗的回退處理

### 5.2 日誌示例
```
bt.logging.trace("On-demand scrape with usernames=...")
bt.logging.warning(f"Failed to scrape user '{username}': {e}")
bt.logging.success("On-demand scrape completed. Found X items...")
bt.logging.error("Failed to perform on-demand scrape: {e}")
```

---

## 6. 與其他爬蟲的比較

| 功能 | Reddit.custom | Reddit.json | Reddit.mc |
|------|---|---|---|
| 按子版塊爬取 | ✅ | ✅ | ✅ |
| 按用戶爬取 | ✅ on_demand | ❌ | ❌ |
| 按關鍵字搜尋 | ✅ on_demand | ❌ | ❌ |
| 時間範圍過濾 | ✅ | ✅ | ✅ |
| 驗證功能 | ✅ 完整 | ✅ | ✅ |
| 異步支持 | ✅ | ❌ | ❌ |
| NSFW 檢查 | ✅ | ✅ | ✅ |
| 成本 | 免費 | 免費 | 免費 |

---

## 7. 建議和改進點

### 7.1 當前狀態
✅ 生產就緒 - 已針對生產使用進行優化

### 7.2 潛在改進
1. **功能增強**
   - [ ] 支持多個子版塊的同時爬取
   - [ ] 增加排序可配置性
   - [ ] 支持評論樹爬取 (回覆鏈)

2. **性能優化**
   - [ ] 實現請求批處理
   - [ ] 添加緩存層
   - [ ] 支持增量爬取

3. **可靠性**
   - [ ] 重試邏輯改進
   - [ ] 添加熔斷器模式

### 7.3 已知限制
- Reddit 單次爬取限制: ~1000 條內容
- API 速率限制: 60 req/min
- 歷史內容可用性: 最多回溯 6 個月（某些情況下）

---

## 8. 配置需求

### 8.1 環境變量
```bash
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password
```

### 8.2 獲取憑證方式
1. 登錄 https://www.reddit.com/prefs/apps
2. 點擊"建立應用"
3. 選擇"個人使用腳本"
4. 複製 client ID 和 client secret

---

## 9. 結論

### 最終評分: 8.5/10

**優勢**:
- ✅ 功能完整且成熟
- ✅ 異步支持確保性能
- ✅ 驗證機制健全
- ✅ 成本低 (完全免費)
- ✅ 代碼質量高

**劣勢**:
- ⚠️ 一次只能爬取一個子版塊
- ⚠️ 帖子/評論爬取不可控 (隨機)

**建議**: Reddit.custom 已完全可以滿足 Reddit 爬取需求。無需額外修改，可直接用於生產環境。

---

## 10. 與 X.custom 功能對比

| 功能 | Reddit.custom | X.custom |
|------|---|---|
| API 客戶端 | PRAW (Python Reddit API Wrapper) | aiohttp + Twitter API v2 |
| 認證方式 | OAuth2 用戶認證 | Bearer Token |
| 搜索功能 | 子版塊/用戶/關鍵字 | 推文搜索 API |
| 驗證精度 | 字段級別 | 字段級別 |
| 異步支持 | ✅ (asyncpraw) | ✅ (aiohttp) |
| 成本 | 免費 | 免費 (API v2 基礎層) |
| 難度 | 低 | 中 (需配置 Bearer Token) |

---

生成時間: 2026-06-19
