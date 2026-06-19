# GitHub Copilot Instructions for sn13-data-universe

## Git Workflow Rules

### ⛔ DO NOT commit or push changes automatically

**IMPORTANT**: After completing work, do NOT automatically execute `git commit` or `git push` commands.

**Expected workflow**:
1. ✅ Make code changes only
2. ⛔ **STOP** - Do not commit
3. ⛔ **STOP** - Do not push
4. ✅ Wait for user confirmation before any git operations

**Why**: 
- Users need to review changes first
- Users decide when and what to commit
- Users control the commit process and messages
- CI/CD pipeline should be under user control

### When to Make Changes

- ✅ Implement features or fixes
- ✅ Update documentation
- ✅ Modify configuration
- ✅ Show changes in the chat

### When NOT to Use Git

- ⛔ Do not run `git add`
- ⛔ Do not run `git commit`
- ⛔ Do not run `git push`
- ⛔ Do not automatically perform any git operations

### Example Correct Workflow

**Instead of**:
```bash
# Make changes
# Then automatically:
git add -A
git commit -m "..."
git push origin main  # ❌ WRONG
```

**Do this**:
```bash
# Make changes only
# ✅ STOP HERE
# User decides what to do with git
```

Then inform the user:
```
✅ Changes made successfully:
- Modified: src/file.ts
- Created: src/new-file.ts
- Updated: config.json

When ready, you can:
  git add -A
  git commit -m "description"
  git push origin main
```

---

## Project-Specific Guidelines

### Environment Setup
- `.env` file contains credentials and should NOT be committed
- Use `export` prefix for all environment variables
- Test with `source .env` before running tests

### Testing Before Changes
- Run `python tests/scraping/test_simple_playwright.py` to validate basic setup
- Use diagnostic tools (`test_twitter_login_debug.py`, `test_reddit_login_debug.py`) for login issues
- Always check `.env` is properly sourced before running tests

### Browser Automation (Playwright)
- Default browser engine is **Firefox** (not Chromium)
- All scrapers use Firefox: `await self.playwright.firefox.launch()`
- Use `headless=True` for production, `headless=False` for debugging
- Login helpers are in `scraping/playwright_auth_helper.py`

### Field References
- **X/Twitter**: `tweet_hashtags`, `timestamp`, `tweet_id` (not `hashtags`, `created_at`)
- **Reddit**: `id`, `body`, `communityName` (with "r/" prefix), `createdAt`

### On-Demand Requests
- Maximum 20 keywords in `OnDemandRequest.keywords` field
- Miner automatically truncates if > 20 and logs warning
- Scraper selection based on `scraping_config.json`

---

## Commit Message Format

Follow conventional commits:
```
type(scope): description

Optional body with more details
Optional footer with issue references
```

**Types**: feat, fix, docs, test, refactor, chore, perf

**Examples**:
- `feat(scraper): Add X Playwright scraper`
- `fix(login): Improve Reddit js_challenge handling`
- `test: Add Twitter login diagnostic tool`
- `docs: Update README with setup instructions`

---

## Common Tasks

### Running Tests
```bash
source .env
python tests/scraping/test_simple_playwright.py
```

### Debugging Login Issues
```bash
python tests/scraping/test_twitter_login_debug.py   # Twitter/X
python tests/scraping/test_reddit_login_debug.py    # Reddit
```

### Checking Syntax
- Python: Run code through pylance syntax checker
- Review before committing

### Database/Storage
- Miner uses SQLite: `storage/miner/sqlite_miner_storage.py`
- Validator uses S3: `storage/validator/s3_validator_storage.py`

---

## Important Files

| File | Purpose |
|------|---------|
| `scraping/playwright_auth_helper.py` | Login automation for Twitter/Reddit |
| `scraping/x/x_playwright_scraper.py` | Twitter/X free scraper |
| `scraping/reddit/reddit_playwright_scraper.py` | Reddit free scraper |
| `neurons/miner.py` | Miner node with on-demand job handling |
| `common/protocol.py` | Bittensor protocol definitions |
| `scraping_config.json` | Scraper configuration |
| `.env` | Credentials (not committed) |

---

## Last Updated
- 2026-06-19
- Established: Do NOT auto-push to Git
- Firefox as default browser engine
- Reddit js_challenge handling improvements
