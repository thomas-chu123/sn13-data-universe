# GitHub Copilot Instructions for sn13-data-universe

## Git Workflow Rules

### ⛔ DO NOT automatically push to Git

**IMPORTANT**: After completing work, do NOT automatically execute `git push` commands.

**Expected workflow**:
1. ✅ Make code changes
2. ✅ Run `git add` and `git commit` with descriptive messages
3. ✅ Show commit details in the chat
4. ⛔ **STOP** - Do not push to remote repository
5. ✅ Wait for user confirmation before pushing

**Why**: 
- Users need to review commits locally
- Some work may be in progress and shouldn't be pushed yet
- Users may want to squash, rebase, or amend commits
- CI/CD pipeline should be under user control

### When to Commit

- ✅ After implementing a feature or fix
- ✅ After all tests pass locally
- ✅ After resolving an issue
- ✅ Include detailed commit messages explaining the changes

### When NOT to Push

- ⛔ Do not push without explicit user request
- ⛔ Do not push after every commit
- ⛔ Do not push if user asks to "save" or "commit" work
- ⛔ Only push if user explicitly says "push to git/GitHub/origin"

### Example Correct Workflow

**Instead of**:
```bash
git add -A
git commit -m "..."
git push origin main  # ❌ WRONG - Do this automatically
```

**Do this**:
```bash
git add -A
git commit -m "..."
# ✅ STOP HERE - Wait for user to request push
```

Then inform the user:
```
✅ Changes committed successfully:
- Commit: abc1234
- Message: "feat: Add new feature..."
- Files changed: 3

Ready to push when you are. Run: git push origin main
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
