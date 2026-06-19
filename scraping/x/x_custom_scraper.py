import os
import asyncio
import aiohttp
import traceback
import datetime as dt
import bittensor as bt
import re
from typing import List, Optional, Tuple
from dotenv import load_dotenv
from urllib.parse import urlencode

from common.data import DataEntity, DataLabel, DataSource
from scraping.scraper import ScrapeConfig, Scraper, ValidationResult
from scraping.x.model import XContent
from scraping.x import utils
from common.protocol import KeywordMode
from common.date_range import DateRange


load_dotenv()


class XCustomScraper(Scraper):
    """
    Scrapes X/Twitter data using the Twitter API v2.
    
    This scraper requires the following environment variables:
    - X_BEARER_TOKEN: Bearer token for Twitter API v2 authentication
    """

    # Twitter API v2 endpoints
    TWEETS_ENDPOINT = "https://api.twitter.com/2/tweets/search/recent"
    TWEET_LOOKUP_ENDPOINT = "https://api.twitter.com/2/tweets"
    USERS_ENDPOINT = "https://api.twitter.com/2/users/by/username"
    USER_TWEETS_ENDPOINT = "https://api.twitter.com/2/users/{user_id}/tweets"

    # Default headers for API calls
    HEADERS = {
        "User-Agent": "XCustomScraper/1.0"
    }

    REQUEST_TIMEOUT = 30

    def __init__(self):
        """Initialize the scraper with API credentials."""
        self.bearer_token = os.getenv("X_BEARER_TOKEN")
        if not self.bearer_token:
            bt.logging.warning(
                "X_BEARER_TOKEN not found in environment variables. "
                "X.custom scraper will not be able to authenticate with Twitter API v2."
            )

    def _get_auth_headers(self) -> dict:
        """Get authorization headers for API requests."""
        headers = self.HEADERS.copy()
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers

    async def validate(self, entities: List[DataEntity]) -> List[ValidationResult]:
        """
        Validate a list of DataEntity objects by fetching from Twitter API.
        """
        if not entities:
            return []

        if not self.bearer_token:
            return [
                ValidationResult(
                    is_valid=False,
                    reason="X_BEARER_TOKEN not configured",
                    content_size_bytes_validated=entity.content_size_bytes,
                )
                for entity in entities
            ]

        results: List[ValidationResult] = []

        async with aiohttp.ClientSession() as session:
            for entity in entities:
                # 1) Basic URI sanity check
                if not utils.is_valid_twitter_url(entity.uri):
                    results.append(
                        ValidationResult(
                            is_valid=False,
                            reason="Invalid URI.",
                            content_size_bytes_validated=entity.content_size_bytes,
                        )
                    )
                    continue

                # 2) Decode XContent blob
                try:
                    ent_content = XContent.from_data_entity(entity)
                except Exception:
                    results.append(
                        ValidationResult(
                            is_valid=False,
                            reason="Failed to decode data entity.",
                            content_size_bytes_validated=entity.content_size_bytes,
                        )
                    )
                    continue

                # 3) Fetch live data from Twitter API
                try:
                    tweet_id = self._extract_tweet_id_from_url(entity.uri)
                    if not tweet_id:
                        results.append(
                            ValidationResult(
                                is_valid=False,
                                reason="Could not extract tweet ID from URI.",
                                content_size_bytes_validated=entity.content_size_bytes,
                            )
                        )
                        continue

                    live_content = await self._fetch_tweet(session, tweet_id)

                except Exception as e:
                    bt.logging.error(f"Failed to retrieve content for {entity.uri}: {e}")
                    results.append(
                        ValidationResult(
                            is_valid=False,
                            reason="Failed to retrieve tweet from Twitter API.",
                            content_size_bytes_validated=entity.content_size_bytes,
                        )
                    )
                    continue

                # 4) Live content object exists?
                if not live_content:
                    results.append(
                        ValidationResult(
                            is_valid=False,
                            reason="Tweet not found or invalid.",
                            content_size_bytes_validated=entity.content_size_bytes,
                        )
                    )
                    continue

                # 5) Field-by-field validation
                validation_result = utils.validate_tweet_content(
                    actual_tweet=live_content,
                    entity=entity,
                )

                results.append(validation_result)

        return results

    async def scrape(self, scrape_config: ScrapeConfig) -> List[DataEntity]:
        """Scrapes tweets according to the scrape config."""
        if not self.bearer_token:
            bt.logging.error("X_BEARER_TOKEN not configured. Cannot scrape.")
            return []

        bt.logging.trace(
            f"X custom scraper performing scrape with config: {scrape_config}."
        )

        # Construct search query
        search_query = self._build_search_query(scrape_config)

        bt.logging.trace(f"Running custom X scraper with search: {search_query}.")

        contents = []
        try:
            async with aiohttp.ClientSession() as session:
                tweets = await self._search_tweets(
                    session,
                    search_query,
                    max_results=scrape_config.entity_limit or 100,
                    start_time=scrape_config.date_range.start,
                    end_time=scrape_config.date_range.end,
                )
                
                for tweet_data in tweets:
                    content = self._parse_tweet(tweet_data)
                    if content:
                        contents.append(content)

        except Exception:
            bt.logging.error(
                f"Failed to scrape X using query {search_query}: {traceback.format_exc()}."
            )
            return []

        # Return the parsed results
        parsed_contents = [content for content in contents if content is not None]

        bt.logging.success(
            f"Completed scrape for query {search_query}. Scraped {len(parsed_contents)} items."
        )

        data_entities = []
        for content in parsed_contents:
            data_entities.append(XContent.to_data_entity(content=content))

        return data_entities

    async def on_demand_scrape(
        self,
        usernames: List[str] = None,
        keywords: List[str] = None,
        url: str = None,
        keyword_mode: KeywordMode = "all",
        start_datetime: dt.datetime = None,
        end_datetime: dt.datetime = None,
        limit: int = 100
    ) -> List[DataEntity]:
        """
        Scrapes X data based on specific search criteria.

        Args:
            usernames: List of target usernames (without @, OR logic between them)
            keywords: List of keywords to search for
            url: Single tweet URL for direct tweet lookup
            keyword_mode: "any" (OR logic) or "all" (AND logic) for keyword matching
            start_datetime: Earliest datetime for content (UTC)
            end_datetime: Latest datetime for content (UTC)
            limit: Maximum number of items to return

        Returns:
            List of DataEntity objects matching the criteria
        """
        if not self.bearer_token:
            bt.logging.error("X_BEARER_TOKEN not configured. Cannot scrape.")
            return []

        # Handle URL-based search (single tweet lookup)
        if url:
            bt.logging.trace(f"On-demand X scrape for URL: {url}")

            if not utils.is_valid_twitter_url(url):
                bt.logging.error(f"Invalid Twitter URL: {url}")
                return []

            try:
                async with aiohttp.ClientSession() as session:
                    tweet_id = self._extract_tweet_id_from_url(url)
                    if not tweet_id:
                        return []

                    tweet_data = await self._fetch_tweet(session, tweet_id)
                    if not tweet_data:
                        return []

                    content = self._parse_tweet(tweet_data)
                    if content:
                        return [XContent.to_data_entity(content=content)]

            except Exception as e:
                bt.logging.exception(f"Failed to scrape tweet from URL {url}: {str(e)}")
                return []

        # Return empty list if all key search parameters are None
        if all(param is None for param in [usernames, keywords, start_datetime, end_datetime]):
            bt.logging.trace("All search parameters are None, returning empty list")
            return []

        bt.logging.trace(
            f"On-demand X scrape with usernames={usernames}, keywords={keywords}, "
            f"keyword_mode={keyword_mode}, start={start_datetime}, end={end_datetime}"
        )

        # Build search query
        query_parts = []

        if usernames:
            username_queries = [f"from:{username.removeprefix('@')}" for username in usernames]
            query_parts.append(f"({' OR '.join(username_queries)})")

        if keywords:
            quoted_keywords = [f'"{keyword}"' for keyword in keywords]
            if keyword_mode == "all":
                query_parts.append(f"({' AND '.join(quoted_keywords)})")
            else:  # keyword_mode == "any"
                query_parts.append(f"({' OR '.join(quoted_keywords)})")

        if not query_parts:
            query_parts.append("e")  # Default fallback

        search_query = " ".join(query_parts)

        contents = []
        try:
            async with aiohttp.ClientSession() as session:
                tweets = await self._search_tweets(
                    session,
                    search_query,
                    max_results=limit,
                    start_time=start_datetime,
                    end_time=end_datetime,
                )

                for tweet_data in tweets:
                    content = self._parse_tweet(tweet_data)
                    if content:
                        contents.append(content)

        except Exception as e:
            bt.logging.exception(f"Failed to scrape tweets using query {search_query}: {str(e)}")
            return []

        bt.logging.success(
            f"Completed on-demand scrape for {search_query}. Scraped {len(contents)} items."
        )

        data_entities = []
        for content in contents:
            data_entities.append(XContent.to_data_entity(content=content))

        return data_entities

    def _build_search_query(self, scrape_config: ScrapeConfig) -> str:
        """Build a Twitter search query from scrape config."""
        query_parts = []

        # Add labels as search terms
        if scrape_config.labels:
            label_queries = []
            for label in scrape_config.labels:
                value = label.value
                if value.startswith("@"):
                    label_queries.append(f"from:{value[1:]}")
                else:
                    label_queries.append(f'"{value}"')
            if label_queries:
                query_parts.append(f"({' OR '.join(label_queries)})")

        if not query_parts:
            # Fallback if no labels provided
            query_parts.append("e")

        return " ".join(query_parts)

    async def _search_tweets(
        self,
        session: aiohttp.ClientSession,
        query: str,
        max_results: int = 100,
        start_time: Optional[dt.datetime] = None,
        end_time: Optional[dt.datetime] = None,
    ) -> List[dict]:
        """Search for tweets using the Twitter API v2."""
        params = {
            "query": query,
            "max_results": min(max_results, 100),  # API limit is 100
            "tweet.fields": "created_at,author_id,public_metrics,lang",
            "user.fields": "username,verified,followers_count,following_count",
            "expansions": "author_id",
        }

        if start_time:
            params["start_time"] = start_time.isoformat()
        if end_time:
            params["end_time"] = end_time.isoformat()

        try:
            async with session.get(
                self.TWEETS_ENDPOINT,
                params=params,
                headers=self._get_auth_headers(),
                timeout=aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    tweets = data.get("data", [])
                    includes = data.get("includes", {})
                    users_data = {u["id"]: u for u in includes.get("users", [])}

                    # Enrich tweets with user data
                    for tweet in tweets:
                        if "author_id" in tweet and tweet["author_id"] in users_data:
                            tweet["author"] = users_data[tweet["author_id"]]

                    return tweets
                else:
                    error_msg = await response.text()
                    bt.logging.error(
                        f"Twitter API error {response.status}: {error_msg}"
                    )
                    return []

        except asyncio.TimeoutError:
            bt.logging.error("Twitter API request timed out")
            return []
        except Exception as e:
            bt.logging.error(f"Error searching tweets: {e}")
            return []

    async def _fetch_tweet(
        self, session: aiohttp.ClientSession, tweet_id: str
    ) -> Optional[dict]:
        """Fetch a single tweet by ID."""
        params = {
            "tweet.fields": "created_at,author_id,public_metrics,lang",
            "user.fields": "username,verified,followers_count,following_count",
            "expansions": "author_id",
        }

        try:
            async with session.get(
                f"{self.TWEET_LOOKUP_ENDPOINT}/{tweet_id}",
                params=params,
                headers=self._get_auth_headers(),
                timeout=aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    tweet = data.get("data")
                    includes = data.get("includes", {})
                    users_data = {u["id"]: u for u in includes.get("users", [])}

                    if tweet and "author_id" in tweet and tweet["author_id"] in users_data:
                        tweet["author"] = users_data[tweet["author_id"]]

                    return tweet
                else:
                    return None

        except Exception as e:
            bt.logging.error(f"Error fetching tweet {tweet_id}: {e}")
            return None

    def _parse_tweet(self, tweet_data: dict) -> Optional[XContent]:
        """Parse raw tweet data into XContent object."""
        try:
            if not tweet_data or "text" not in tweet_data:
                return None

            author = tweet_data.get("author", {})
            metrics = tweet_data.get("public_metrics", {})

            # Extract hashtags from text
            hashtags = self._extract_hashtags(tweet_data["text"])

            # Create URL
            author_username = author.get("username", "unknown")
            tweet_id = tweet_data.get("id", "")
            url = f"https://x.com/{author_username}/status/{tweet_id}"

            content = XContent(
                username=author_username,
                text=tweet_data["text"],
                url=url,
                timestamp=self._parse_datetime(tweet_data.get("created_at")),
                tweet_hashtags=hashtags,
                # Additional fields if available
                user_id=author.get("id"),
                user_display_name=author.get("name"),
                user_verified=author.get("verified", False),
                tweet_id=tweet_id,
                language=tweet_data.get("lang"),
                like_count=metrics.get("like_count"),
                retweet_count=metrics.get("retweet_count"),
                reply_count=metrics.get("reply_count"),
                quote_count=metrics.get("quote_count"),
                user_followers_count=author.get("followers_count"),
                user_following_count=author.get("following_count"),
                scraped_at=dt.datetime.now(dt.timezone.utc),
            )

            return content

        except Exception:
            bt.logging.warning(
                f"Failed to parse tweet data: {traceback.format_exc()}"
            )
            return None

    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from tweet text."""
        # Match hashtags in order of appearance
        hashtag_pattern = r"#\w+"
        matches = re.finditer(hashtag_pattern, text)
        hashtags = [match.group() for match in matches]
        return hashtags

    def _parse_datetime(self, datetime_str: Optional[str]) -> dt.datetime:
        """Parse datetime string from Twitter API."""
        if not datetime_str:
            return dt.datetime.now(dt.timezone.utc)
        try:
            # Twitter API returns ISO 8601 format
            return dt.datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        except Exception:
            return dt.datetime.now(dt.timezone.utc)

    def _extract_tweet_id_from_url(self, url: str) -> Optional[str]:
        """Extract tweet ID from Twitter URL."""
        # Match pattern like /status/1234567890
        match = re.search(r"/status/(\d+)", url)
        return match.group(1) if match else None
