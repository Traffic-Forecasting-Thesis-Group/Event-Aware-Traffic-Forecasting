#!/usr/bin/env python3
"""
Fetch data from multiple sources (Social Media, News API, GDELT) and combine into a single training CSV.

This script:
1. Fetches recent posts from configured data sources
2. Cleans and translates text to English
3. Combines all sources into a single CSV for annotation

Usage:
    python fetch_multi_source_training_data.py \
        --sources social_media news_api gdelt \
        --output ml/data/x_multi_source_training.csv \
        --limit 50 \
        --api-key YOUR_NEWS_API_KEY

Supported News Sources:
    - ABS-CBN News
    - TV5 (News5)
    - Manila Bulletin
    - The Philippine Star
    - ONE News
    - GMA News
    - ABS-CBN News Online
    - Inquirer.net
    - Rappler
"""

import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import logging

import pandas as pd
import httpx

BASE_DIR = Path(__file__).resolve().parents[2]


def load_env_file(env_path: Path) -> None:
    """Load simple KEY=VALUE pairs from a .env file into the current process."""
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file(BASE_DIR / "backend" / ".env")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Philippine news sources to track
PHILIPPINE_NEWS_SOURCES = {
    "abs-cbn-news": "ABS-CBN News",
    "tv5-news5": "TV5 (News5)",
    "manila-bulletin": "Manila Bulletin",
    "the-philippine-star": "The Philippine Star",
    "one-news": "ONE News",
    "gma-news": "GMA News",
    "abs-cbn-news-online": "ABS-CBN News Online",
    "inquirer": "Inquirer.net",
    "rappler": "Rappler",
}

PHILIPPINE_NEWS_DOMAINS = [
    "abs-cbn.com",
    "news.abs-cbn.com",
    "tv5.com.ph",
    "news.tv5.com.ph",
    "mb.com.ph",
    "philstar.com",
    "onenews.ph",
    "gmanetwork.com",
    "inquirer.net",
    "rappler.com",
]

GDELT_TRAFFIC_QUERY = (
    '(traffic OR accident OR flood OR congestion OR "road closed" OR collision) '
    '("Metro Manila" OR EDSA OR SLEX OR NLEX OR Skyway OR Makati OR "Quezon City") '
    'sourcelang:English'
)

METRO_MANILA_TERMS = [
    "metro manila", "manila", "ncr", "edsa", "c5", "c-5", "slex", "nlex", "skyway",
    "quezon city", "makati", "pasig", "taguig", "pasay", "paranaque", "parañaque",
    "mandaluyong", "marikina", "caloocan", "muntinlupa", "navotas", "malabon",
    "san juan", "valenzuela", "pateros", "ortigas", "bgc", "bonifacio global city",
]

DISRUPTION_EVENT_TERMS = [
    "traffic", "accident", "collision", "crash", "stalled", "breakdown", "gridlock", "congestion",
    "flood", "baha", "road closed", "road closure", "lane closure", "reroute", "advisory",
    "rally", "protest", "strike", "parade", "procession", "motorcade", "public event", "festival",
    "holiday", "long weekend", "holiday rush", "commuters", "transport disruption",
]


def is_metro_manila_event_relevant(text: str) -> bool:
    t = str(text).lower()
    has_location = any(term in t for term in METRO_MANILA_TERMS)
    has_event = any(term in t for term in DISRUPTION_EVENT_TERMS)
    return has_location and has_event


def has_event_signal(text: str) -> bool:
    t = str(text).lower()
    return any(term in t for term in DISRUPTION_EVENT_TERMS)


class MultiSourceFetcher:
    """Fetch and combine data from multiple sources."""

    def __init__(self, output_dir: Path = None, news_api_key: str = None, gdelt_api_key: str = None):
        self.output_dir = output_dir or Path("./ml/data")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.news_api_key = news_api_key or os.getenv("NEWS_API_KEY")
        self.gdelt_api_key = gdelt_api_key or os.getenv("GDELT_API_KEY")
        self.news_api_url = "https://newsapi.org/v2/everything"
        self.news_api_top_url = "https://newsapi.org/v2/top-headlines"
        self.gdelt_api_url = os.getenv("GDELT_API_URL", "https://api.gdeltproject.org/api/v2/doc/doc")

    def _load_existing_social_media_csv(self, csv_dir: str = "./ml/outputs/x_fetch") -> pd.DataFrame:
        """Load and combine all timestamped social media CSVs for annotation."""
        csv_dir_path = Path(csv_dir)
        
        # Look for timestamped CSV files: x_recent_posts_translated_YYYYMMDD_HHMM.csv
        if csv_dir_path.exists():
            timestamped_files = sorted(csv_dir_path.glob("x_recent_posts_translated_*.csv"))

            if timestamped_files:
                frames: list[pd.DataFrame] = []
                for csv_path in timestamped_files:
                    try:
                        df = pd.read_csv(csv_path)
                        df["source_type"] = "social_media"
                        df["source_file"] = csv_path.name
                        # Rename columns to standard format
                        if "x_post_id" in df.columns:
                            df.rename(columns={"x_post_id": "post_id"}, inplace=True)
                        if "raw_text" not in df.columns and "text" in df.columns:
                            df["raw_text"] = df["text"]
                        frames.append(df)
                        logger.info(f"Loaded {len(df)} social media posts from {csv_path}")
                    except Exception as e:
                        logger.error(f"Failed to read {csv_path}: {e}")

                if frames:
                    combined = pd.concat(frames, ignore_index=True)
                    combined = combined.drop_duplicates(subset=["post_id", "raw_text"], keep="first")
                    combined = combined.sort_values("created_at", ascending=False).reset_index(drop=True)
                    logger.info(
                        f"Combined {len(frames)} X exports into {len(combined)} social media rows"
                    )
                    return combined
        
        # Fallback: try old naming convention
        legacy_path = csv_dir_path / "x_recent_posts_translated.csv"
        if legacy_path.exists():
            try:
                df = pd.read_csv(legacy_path)
                df["source_type"] = "social_media"
                df["source_file"] = legacy_path.name
                if "x_post_id" in df.columns:
                    df.rename(columns={"x_post_id": "post_id"}, inplace=True)
                if "raw_text" not in df.columns and "text" in df.columns:
                    df["raw_text"] = df["text"]
                logger.info(f"Loaded {len(df)} social media posts from {legacy_path} (legacy naming)")
                return df
            except Exception as e:
                logger.error(f"Failed to read {legacy_path}: {e}")
        
        logger.warning(f"No social media CSV found in {csv_dir_path}")
        return pd.DataFrame()

    async def _fetch_news_api(self, client: httpx.AsyncClient, limit: int) -> pd.DataFrame:
        """Fetch from News API (Philippine news sources)."""
        if not self.news_api_key:
            logger.warning("NEWS_API_KEY not set. Using stub data for News API.")
            return self._create_stub_news_api_data()

        try:
            # Search for Metro Manila traffic disruptions, accidents, rallies, public events, and holidays.
            # News API pageSize maxes out at 100 per request.
            queries = [
                '(("Metro Manila" OR Manila OR NCR OR EDSA OR "Quezon City" OR Makati OR Pasig OR Taguig) '
                'AND (traffic OR accident OR collision OR flood OR congestion OR "road closure" OR reroute OR advisory))',
                '(("Metro Manila" OR Manila OR NCR OR "Quezon City" OR Makati) '
                'AND (rally OR protest OR strike OR parade OR procession OR "public event" OR holiday))',
            ]
            domains = ",".join(PHILIPPINE_NEWS_DOMAINS)

            all_articles = []
            
            for query in queries:
                params = {
                    "q": query,
                    "sortBy": "publishedAt",
                    "pageSize": str(min(limit, 100)),
                    "apiKey": self.news_api_key,
                    "language": "en",
                    "searchIn": "title,description,content",
                }

                # Prefer domain-based filtering, but keep a fallback without domains if the API rejects it.
                domain_params = {**params, "domains": domains}

                logger.info(f"Fetching News API: query='{query}'")
                response = await client.get(self.news_api_url, params=domain_params, timeout=30.0)
                
                if response.status_code == 401:
                    logger.error("News API Key is invalid. Using stub data.")
                    return self._create_stub_news_api_data()
                if response.status_code == 429:
                    logger.warning("News API rate-limited. Waiting 10s and retrying once.")
                    await asyncio.sleep(10)
                    response = await client.get(self.news_api_url, params=domain_params, timeout=30.0)
                if response.status_code == 400:
                    logger.warning("News API rejected domain filtering; retrying without domains.")
                    response = await client.get(self.news_api_url, params=params, timeout=30.0)
                
                response.raise_for_status()
                payload = response.json()
                articles = payload.get("articles", [])
                all_articles.extend(articles)
                logger.info(f"  Found {len(articles)} articles for query '{query}'")

            # If domain-filtered queries return nothing, retry once with no domain restriction.
            if not all_articles:
                logger.warning("No News API results with domain filter; retrying top-headlines country=ph.")
                top_queries = [
                    "traffic OR accident OR collision OR road closure",
                    "flood OR rally OR protest OR public event OR holiday",
                    "MMDA OR EDSA OR Metro Manila",
                ]
                for query in top_queries:
                    top_params = {
                        "country": "ph",
                        "q": query,
                        "pageSize": str(min(limit, 100)),
                        "apiKey": self.news_api_key,
                    }
                    response = await client.get(self.news_api_top_url, params=top_params, timeout=30.0)
                    if response.status_code == 429:
                        logger.warning("News API rate-limited on top-headlines retry. Waiting 10s.")
                        await asyncio.sleep(10)
                        response = await client.get(self.news_api_top_url, params=top_params, timeout=30.0)
                    response.raise_for_status()
                    payload = response.json()
                    articles = payload.get("articles", [])
                    all_articles.extend(articles)
                    logger.info(f"  Found {len(articles)} top-headlines for query '{query}'")

            # Deduplicate by URL
            seen_urls = set()
            unique_articles = []
            for article in all_articles:
                url = article.get("url", "")
                if url not in seen_urls:
                    seen_urls.add(url)
                    text_blob = " ".join(
                        [
                            str(article.get("title", "")),
                            str(article.get("description", "")),
                            str(article.get("content", "")),
                            str(article.get("source", {}).get("name", "")),
                        ]
                    )
                    article_url = str(article.get("url", "")).lower()
                    is_ph_domain = any(domain in article_url for domain in PHILIPPINE_NEWS_DOMAINS)
                    if is_metro_manila_event_relevant(text_blob) or (is_ph_domain and has_event_signal(text_blob)):
                        unique_articles.append(article)

            logger.info(f"  Relevant News API articles after filtering: {len(unique_articles)}")

            # Convert to DataFrame
            data = {
                "post_id": [f"news_api_{i}" for i in range(len(unique_articles))],
                "created_at": [],
                "raw_text": [],
                "translated_text": [],
                "source_type": ["news_api"] * len(unique_articles),
                "lang": ["en"] * len(unique_articles),
            }

            for article in unique_articles[:limit]:
                title = article.get("title", "").strip()
                description = article.get("description", "").strip()
                content = article.get("content", "").strip()
                source_name = article.get("source", {}).get("name", "Unknown Source")
                
                # Combine title, description, content
                text = f"[{source_name}] {title}"
                if description:
                    text += f" {description}"
                if content and len(content) < 500:  # Avoid overly long texts
                    text += f" {content}"
                
                data["raw_text"].append(text)
                data["translated_text"].append(text)  # Already in English
                data["created_at"].append(article.get("publishedAt", datetime.now().isoformat()))

            df = pd.DataFrame(data)
            logger.info(f"Fetched {len(df)} articles from News API")
            return df

        except Exception as e:
            logger.error(f"News API fetch failed: {e}. Using stub data.")
            return self._create_stub_news_api_data()

    async def _fetch_gdelt(self, client: httpx.AsyncClient, limit: int) -> pd.DataFrame:
        """Fetch from GDELT API (global events)."""
        try:
            # Mirror the working backend/test_gdelt.py logic.
            # GDELT needs a short, focused query and a time window.
            params = {
                "query": GDELT_TRAFFIC_QUERY,
                "mode": "artlist",
                "format": "json",
                "maxrecords": str(min(limit, 250)),
                "sort": "DateDesc",
                "timespan": os.getenv("GDELT_TIMESPAN", "3d"),
            }
            if self.gdelt_api_key:
                params["key"] = self.gdelt_api_key

            logger.info("Fetching GDELT data using test_gdelt.py logic")

            response = None
            for attempt in range(1, 4):
                response = await client.get(self.gdelt_api_url, params=params, timeout=30.0)
                if response.status_code == 429 and attempt < 3:
                    logger.warning(f"GDELT rate-limited (attempt {attempt}/3). Waiting 6s.")
                    await asyncio.sleep(6)
                    continue
                break

            if response is None:
                raise RuntimeError("GDELT request did not return a response")

            response.raise_for_status()
            payload = response.json()

            articles = payload.get("articles", [])
            all_articles = list(articles)
            logger.info(f"  Found {len(articles)} articles for the GDELT traffic query")

            # If the first query is sparse, broaden with a second pass after a short pause.
            if len(all_articles) < limit:
                await asyncio.sleep(6)
                fallback_params = {
                    "query": '(traffic OR accident OR flood OR congestion OR collision OR rally OR protest OR holiday) '
                             '("Metro Manila" OR Manila OR NCR OR EDSA OR "Quezon City") sourcelang:English',
                    "mode": "artlist",
                    "format": "json",
                    "maxrecords": str(min(limit, 25)),
                    "sort": "DateDesc",
                    "timespan": os.getenv("GDELT_TIMESPAN", "7d"),
                }
                if self.gdelt_api_key:
                    fallback_params["key"] = self.gdelt_api_key

                logger.info("Fetching GDELT fallback query")
                fallback_response = await client.get(self.gdelt_api_url, params=fallback_params, timeout=30.0)
                if fallback_response.status_code == 429:
                    logger.warning("GDELT fallback query rate-limited. Keeping first-pass results.")
                else:
                    fallback_response.raise_for_status()
                    fallback_payload = fallback_response.json()
                    fallback_articles = fallback_payload.get("articles", [])
                    all_articles.extend(fallback_articles)
                    logger.info(f"  Found {len(fallback_articles)} fallback articles")

            # Deduplicate by URL/title pair
            seen_keys = set()
            unique_articles = []
            for article in all_articles:
                key = (article.get("url", ""), article.get("title", ""))
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                title = str(article.get("title", "")).strip()
                if not title:
                    continue
                # Keep all deduplicated rows from the targeted Metro Manila query.
                unique_articles.append(article)

            logger.info(f"  Unique GDELT articles after deduplication: {len(unique_articles)}")

            # Convert to DataFrame
            data = {
                "post_id": [f"gdelt_{i}" for i in range(len(unique_articles))],
                "created_at": [],
                "raw_text": [],
                "translated_text": [],
                "source_type": ["gdelt"] * len(unique_articles),
                "lang": ["en"] * len(unique_articles),
            }

            for article in unique_articles[:limit]:
                title = article.get("title", "").strip()
                url = article.get("url", "")
                
                text = f"[GDELT] {title}"
                if url:
                    text += f" (Source: {url})"
                
                data["raw_text"].append(text)
                data["translated_text"].append(text)  # Assume English
                # GDELT uses timestamps; default to now if not available
                data["created_at"].append(
                    article.get("seendate")
                    or article.get("pubdate")
                    or article.get("datetime")
                    or datetime.now().isoformat()
                )

            df = pd.DataFrame(data)
            logger.info(f"Fetched {len(df)} events from GDELT")
            return df

        except Exception as e:
            logger.error(f"GDELT fetch failed: {e}. Returning empty result (no stub rows).")
            return pd.DataFrame()

    async def fetch_from_backend(self, sources: list[str] = None, limit_per_source: int = 30):
        """
        Fetch from multiple sources (Social Media, News API, GDELT).
        
        Uses real APIs if credentials are available, otherwise falls back to stubs.
        """
        sources = sources or ["social_media", "news_api", "gdelt"]
        
        all_data = []

        # Load social media posts from existing CSV
        if "social_media" in sources:
            sm_df = self._load_existing_social_media_csv()
            if not sm_df.empty:
                all_data.append(sm_df)
                logger.info(f"Loaded {len(sm_df)} social media posts")

        # Fetch News API data (real or stub)
        if "news_api" in sources:
            async with httpx.AsyncClient() as client:
                news_df = await self._fetch_news_api(client, limit_per_source)
                if not news_df.empty:
                    all_data.append(news_df)
                    logger.info(f"Loaded {len(news_df)} News API posts")

        # Fetch GDELT data (real or stub)
        if "gdelt" in sources:
            async with httpx.AsyncClient() as client:
                gdelt_df = await self._fetch_gdelt(client, limit_per_source)
                if not gdelt_df.empty:
                    all_data.append(gdelt_df)
                    logger.info(f"Loaded {len(gdelt_df)} GDELT posts")

        return all_data

    def _create_stub_news_api_data(self) -> pd.DataFrame:
        """Fallback stub data for News API."""
        stub_data = {
            "post_id": ["news_api_001", "news_api_002", "news_api_003"],
            "created_at": [
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
            ],
            "raw_text": [
                "[ABS-CBN News] Heavy traffic on C5 due to accident involving 3 vehicles, MMDA on scene responding to the incident",
                "[Manila Bulletin] MMDA urges motorists to avoid EDSA northbound due to road closure from construction",
                "[TV5 News5] Flooding reported in Marikina following heavy downpour, affecting traffic flow towards Metro Manila",
            ],
            "translated_text": [
                "[ABS-CBN News] Heavy traffic on C5 due to accident involving 3 vehicles, MMDA on scene responding to the incident",
                "[Manila Bulletin] MMDA urges motorists to avoid EDSA northbound due to road closure from construction",
                "[TV5 News5] Flooding reported in Marikina following heavy downpour, affecting traffic flow towards Metro Manila",
            ],
            "lang": ["en", "en", "en"],
            "source_type": ["news_api", "news_api", "news_api"],
        }
        return pd.DataFrame(stub_data)

    def _create_stub_gdelt_data(self) -> pd.DataFrame:
        """Fallback stub data for GDELT."""
        stub_data = {
            "post_id": ["gdelt_001", "gdelt_002", "gdelt_003"],
            "created_at": [
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
            ],
            "raw_text": [
                "[GDELT] Transport disruption reported in Quezon City: vehicle breakdown blocking main road at Commonwealth Avenue, causing heavy congestion",
                "[GDELT] Weather event affecting Metro Manila: Heavy downpour creates flooding in low-lying areas, impacts EDSA traffic significantly",
                "[GDELT] Road incident in Makati: Multiple vehicle collision on Ayala Avenue, one lane closed, traffic rerouted to alternative routes",
            ],
            "translated_text": [
                "[GDELT] Transport disruption reported in Quezon City: vehicle breakdown blocking main road at Commonwealth Avenue, causing heavy congestion",
                "[GDELT] Weather event affecting Metro Manila: Heavy downpour creates flooding in low-lying areas, impacts EDSA traffic significantly",
                "[GDELT] Road incident in Makati: Multiple vehicle collision on Ayala Avenue, one lane closed, traffic rerouted to alternative routes",
            ],
            "lang": ["en", "en", "en"],
            "source_type": ["gdelt", "gdelt", "gdelt"],
        }
        return pd.DataFrame(stub_data)

    def combine_sources(self, dataframes: list[pd.DataFrame]) -> pd.DataFrame:
        """Combine data from multiple sources into a single DataFrame."""
        if not dataframes:
            return pd.DataFrame()

        combined = pd.concat(dataframes, ignore_index=True)
        
        # Ensure required columns exist
        required_cols = ["post_id", "created_at", "raw_text", "translated_text", "source_type"]
        for col in required_cols:
            if col not in combined.columns:
                if col == "source_type":
                    combined[col] = "unknown"
                else:
                    combined[col] = None

        # Add label columns (empty, to be filled by annotators)
        combined["reliability_label"] = pd.NA
        combined["annotator_name"] = ""
        combined["annotation_time"] = pd.NA
        combined["notes"] = ""

        # Sort by timestamp
        combined = combined.sort_values("created_at", ascending=False).reset_index(drop=True)

        return combined

    def save_combined_csv(self, combined_df: pd.DataFrame, output_path: str) -> Path:
        """Save combined data to CSV."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        combined_df.to_csv(output_path, index=False)
        logger.info(f"Saved {len(combined_df)} combined posts to {output_path}")
        return output_path

    async def run(
        self,
        sources: list[str] = None,
        output_path: str = None,
        limit_per_source: int = 30,
    ) -> Path:
        """Orchestrate the full fetch-combine-save workflow."""
        sources = sources or ["social_media", "news_api", "gdelt"]
        output_path = output_path or str(self.output_dir / "x_multi_source_training.csv")

        logger.info(f"Starting multi-source fetch for: {sources}")
        
        # Fetch from all sources
        dataframes = await self.fetch_from_backend(sources=sources, limit_per_source=limit_per_source)
        
        # Combine
        combined = self.combine_sources(dataframes)
        
        # Save
        saved_path = self.save_combined_csv(combined, output_path)
        
        # Print summary
        print("\n" + "=" * 80)
        print("MULTI-SOURCE DATA FETCH COMPLETE")
        print("=" * 80)
        print(f"Total posts: {len(combined)}")
        print(f"\nBreakdown by source:")
        source_counts = combined["source_type"].value_counts()
        for source, count in source_counts.items():
            print(f"  {source}: {count}")
        print(f"\nSaved to: {saved_path}")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Load this CSV in interactive_labeling.ipynb")
        print("2. Annotate posts using the binary rubric (1=Reliable, 0=Unreliable)")
        print("3. Save labeled batch and merge into master training file")
        print("4. Train DistilBERT and RoBERTa in fuse_traffic_training.ipynb")
        print("=" * 80 + "\n")
        
        return saved_path


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch multi-source training data (Social Media, News API, GDELT)"
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["social_media", "news_api", "gdelt"],
        help="Data sources to fetch from",
    )
    parser.add_argument(
        "--output",
        default="./ml/data/x_multi_source_training.csv",
        help="Output CSV path",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Limit per source",
    )
    parser.add_argument(
        "--api-key",
        help="News API key (newsapi.org). Also checks NEWS_API_KEY env var.",
    )
    parser.add_argument(
        "--gdelt-key",
        help="GDELT API key. Also checks GDELT_API_KEY env var.",
    )

    args = parser.parse_args()

    fetcher = MultiSourceFetcher(news_api_key=args.api_key, gdelt_api_key=args.gdelt_key)
    await fetcher.run(sources=args.sources, output_path=args.output, limit_per_source=args.limit)


if __name__ == "__main__":
    asyncio.run(main())
