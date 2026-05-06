from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import logging
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

# Optional import for GDELT BigQuery Adapter
try:
    from google.cloud import bigquery
    from google.api_core.exceptions import GoogleAPICallError

    # This assumes ml/src is in the path. A better long-term solution is packaging the ml module.
    # The router at `app/spatial/router.py` modifies sys.path, which is one way to achieve this.
    from event_aware_traffic.bigquery import build_gdelt_query
except ImportError:
    bigquery = None  # type: ignore
    GoogleAPICallError = None  # type: ignore
    build_gdelt_query = None  # type: ignore

from app.schemas.ingestion import RawTextItem

logger = logging.getLogger(__name__)

def parse_timestamp(value: str | None) -> datetime:

def parse_timestamp(value: str | int | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)

    str_value = str(value)

    try:
        dt = parsedate_to_datetime(value)
        dt = parsedate_to_datetime(str_value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"]:
    # Add GDELT DATEADDED format
    for fmt in ["%Y%m%d%H%M%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"]:
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            return datetime.strptime(str_value, fmt).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue

    return datetime.now(timezone.utc)


def strip_html(text: str) -> str:
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()


def location_hint_from_text(text: str) -> str | None:
    corridors = [
        "edsa",
        "c5",
        "ayala",
        "ortigas",
        "quezon avenue",
        "commonwealth",
        "roxas boulevard",
        "katipunan",
        "manila",
        "makati",
        "pasig",
        "taguig",
    ]
    lowered = text.lower()
    for corridor in corridors:
        if corridor in lowered:
            return corridor.title()
    return None


@dataclass(slots=True)
class SourceContext:
    timeout_seconds: float
    user_agent: str


class SourceAdapter:
    source_name: str

    def __init__(self, source_name: str) -> None:
        self.source_name = source_name

    async def fetch(self, client: httpx.AsyncClient, limit: int) -> list[RawTextItem]:
        raise NotImplementedError


class RSSSourceAdapter(SourceAdapter):
    def __init__(self, source_name: str, url: str, auth_header: str | None = None) -> None:
        super().__init__(source_name)
        self.url = url
        self.auth_header = auth_header

    async def fetch(self, client: httpx.AsyncClient, limit: int) -> list[RawTextItem]:
        headers: dict[str, str] = {}
        if self.auth_header:
            headers["Authorization"] = self.auth_header

        response = await client.get(self.url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "xml")
        items = soup.find_all("item")[:limit]

        parsed: list[RawTextItem] = []
        for item in items:
            title = strip_html(item.title.text if item.find("title") else "")
            description = strip_html(item.description.text if item.find("description") else "")
            text = " ".join(part for part in [title, description] if part)
            if not text:
                continue

            date_text = ""
            for candidate in ["pubDate", "dc:date", "published"]:
                node = item.find(candidate)
                if node and node.text:
                    date_text = node.text
                    break

            parsed.append(
                RawTextItem(
                    source=self.source_name,
                    text=text,
                    location_hint=location_hint_from_text(text),
                    timestamp=parse_timestamp(date_text),
                )
            )
        return parsed


class MMDAAdapter(SourceAdapter):
    def __init__(
        self,
        feed_url: str,
        twitter_api_url: str | None = None,
        bearer_token: str | None = None,
        twitter_user_id: str | None = None,
    ) -> None:
        super().__init__("mmda_twitter")
        self.feed_url = feed_url
        self.twitter_api_url = twitter_api_url
        self.bearer_token = bearer_token
        self.twitter_user_id = twitter_user_id

    async def fetch(self, client: httpx.AsyncClient, limit: int) -> list[RawTextItem]:
        if self.twitter_api_url and self.bearer_token and self.twitter_user_id:
            headers = {"Authorization": f"Bearer {self.bearer_token}"}
            params = {"max_results": min(limit, 100), "tweet.fields": "created_at,text"}
            url = self.twitter_api_url.format(user_id=self.twitter_user_id)
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            payload = response.json()
            tweets = payload.get("data", [])

            items: list[RawTextItem] = []
            for tweet in tweets[:limit]:
                text = strip_html(str(tweet.get("text", "")))
                if not text:
                    continue
                items.append(
                    RawTextItem(
                        source=self.source_name,
                        text=text,
                        location_hint=location_hint_from_text(text),
                        timestamp=parse_timestamp(str(tweet.get("created_at", ""))),
                    )
                )
            return items

        fallback = RSSSourceAdapter(self.source_name, self.feed_url)
        return await fallback.fetch(client, limit)


class GDELTAdapter(SourceAdapter):
    def __init__(self, api_url: str, api_key: str | None = None) -> None:
        super().__init__("gdelt")
        self.api_url = api_url
        self.api_key = api_key

    async def fetch(self, client: httpx.AsyncClient, limit: int) -> list[RawTextItem]:
        params: dict[str, Any] = {
            "query": "traffic AND (Manila OR Metro Manila)",
            "mode": "ArtList",
            "maxrecords": str(limit),
            "format": "json",
        }
        if self.api_key:
            params["key"] = self.api_key

        response = await client.get(self.api_url, params=params)
        response.raise_for_status()
        payload = response.json()
        articles = payload.get("articles", [])

        items: list[RawTextItem] = []
        for article in articles[:limit]:
            title = strip_html(str(article.get("title", "")))
            body = strip_html(str(article.get("socialimage", "")))
            text = " ".join(part for part in [title, body] if part).strip()
            if not text:
                continue

            items.append(
                RawTextItem(
                    source=self.source_name,
                    text=text,
                    location_hint=location_hint_from_text(text),
                    timestamp=parse_timestamp(str(article.get("seendate", ""))),  # GDELT v1 date format
                )
            )
        return items


class GDELTBigQueryAdapter(SourceAdapter):
    """
    Fetches GDELT events from Google BigQuery.
    This is more powerful than the DOC API for country-wide event monitoring.
    """

    def __init__(self, project_id: str | None, country_code: str = "RP") -> None:
        super().__init__("gdelt_bigquery")
        self.project_id = project_id
        self.country_code = country_code
        if not bigquery or not build_gdelt_query:
            logger.warning("google-cloud-bigquery is not installed. GDELTBigQueryAdapter will be disabled.")

    async def fetch(self, client: httpx.AsyncClient, limit: int) -> list[RawTextItem]:
        if not self.project_id or not bigquery or not build_gdelt_query:
            return []

        try:
            # This assumes the environment is authenticated for Google Cloud (e.g., GOOGLE_APPLICATION_CREDENTIALS)
            bq_client = bigquery.Client(project=self.project_id)
            # GDELT updates every 15 mins, so a 30-min lookback is safe.
            query = build_gdelt_query(lookback_minutes=30, country_code=self.country_code)

            # BigQuery jobs are blocking, so run in a thread pool to avoid blocking the event loop.
            job = await asyncio.to_thread(bq_client.query, query)
            df = await asyncio.to_thread(job.to_dataframe)

        except (GoogleAPICallError, Exception) as e:
            logger.error(f"GDELT BigQuery query failed: {e}")
            return []

        if df.empty:
            return []

        items: list[RawTextItem] = []
        # Limit to the most mentioned events
        for row in df.sort_values("NumMentions", ascending=False).head(limit).itertuples(index=False):
            # The 'events' table gives us the source URL, but not the article text.
            # We'll create a summary text from the available event metadata.
            text = f"GDELT Event Code: {getattr(row, 'EventRootCode', 'N/A')}; Mentions: {getattr(row, 'NumMentions', 0)}; Source: {getattr(row, 'SOURCEURL', '')}"
            lat = getattr(row, "ActionGeo_Lat", None)
            lon = getattr(row, "ActionGeo_Long", None)
            location_hint = f"{lat},{lon}" if lat and lon else None

            items.append(
                RawTextItem(
                    source=self.source_name,
                    text=text,
                    location_hint=location_hint,
                    timestamp=parse_timestamp(getattr(row, "DATEADDED", None)),
                )
            )
        return items


class NewsAPIAdapter(SourceAdapter):
    def __init__(self, api_url: str, api_key: str | None = None, query: str = "traffic OR accident OR flood OR road closure OR MMDA") -> None:
        super().__init__("news_api")
        self.api_url = api_url
        self.api_key = api_key
        self.query = query

    async def fetch(self, client: httpx.AsyncClient, limit: int) -> list[RawTextItem]:
        if not self.api_key:
            return []

        params: dict[str, Any] = {
            "q": self.query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": str(limit),
            "apiKey": self.api_key,
        }

        response = await client.get(self.api_url, params=params)
        response.raise_for_status()
        payload = response.json()
        articles = payload.get("articles", [])

        items: list[RawTextItem] = []
        for article in articles[:limit]:
            title = strip_html(str(article.get("title", "")))
            description = strip_html(str(article.get("description", "")))
            content = strip_html(str(article.get("content", "")))
            text = " ".join(part for part in [title, description, content] if part).strip()
            if not text:
                continue

            items.append(
                RawTextItem(
                    source=self.source_name,
                    text=text,
                    location_hint=location_hint_from_text(text),
                    timestamp=parse_timestamp(str(article.get("publishedAt", ""))),
                )
            )
        return items


class OpenWeatherAdapter(SourceAdapter):
    def __init__(self, api_url: str, api_key: str | None, lat: float, lon: float) -> None:
        super().__init__("openweather")
        self.api_url = api_url
        self.api_key = api_key
        self.lat = lat
        self.lon = lon

    async def fetch(self, client: httpx.AsyncClient, limit: int) -> list[RawTextItem]:
        if not self.api_key:
            return []

        params: dict[str, Any] = {
            "lat": str(self.lat),
            "lon": str(self.lon),
            "appid": self.api_key,
            "units": "metric",
        }

        response = await client.get(self.api_url, params=params)
        response.raise_for_status()
        payload = response.json()

        location = payload.get("name") or "Metro Manila"
        weather_items = payload.get("weather", [])
        description = weather_items[0].get("description") if weather_items else ""
        temperature = payload.get("main", {}).get("temp")
        wind_speed = payload.get("wind", {}).get("speed")
        humidity = payload.get("main", {}).get("humidity")

        summary_parts = [
            f"Location: {location}",
            f"Weather: {description}" if description else "",
            f"Temp C: {temperature}" if temperature is not None else "",
            f"Wind m/s: {wind_speed}" if wind_speed is not None else "",
            f"Humidity: {humidity}%" if humidity is not None else "",
        ]
        text = "; ".join(part for part in summary_parts if part)
        if not text:
            return []

        return [
            RawTextItem(
                source=self.source_name,
                text=text,
                location_hint=location_hint_from_text(text),
                timestamp=datetime.now(timezone.utc),
            )
        ]


class WeatherStackAdapter(SourceAdapter):
    def __init__(self, api_url: str, api_key: str | None, lat: float, lon: float) -> None:
        super().__init__("weatherstack")
        self.api_url = api_url
        self.api_key = api_key
        self.lat = lat
        self.lon = lon

    async def fetch(self, client: httpx.AsyncClient, limit: int) -> list[RawTextItem]:
        if not self.api_key:
            return []

        params: dict[str, Any] = {
            "access_key": self.api_key,
            "query": f"{self.lat},{self.lon}",
            "units": "m",
        }

        response = await client.get(self.api_url, params=params)
        response.raise_for_status()
        payload = response.json()

        current = payload.get("current", {})
        location = payload.get("location", {}).get("name") or "Metro Manila"
        description = ""
        if isinstance(current.get("weather_descriptions"), list) and current.get("weather_descriptions"):
            description = current.get("weather_descriptions")[0]

        temperature = current.get("temperature")
        wind_speed = current.get("wind_speed")
        humidity = current.get("humidity")

        summary_parts = [
            f"Location: {location}",
            f"Weather: {description}" if description else "",
            f"Temp C: {temperature}" if temperature is not None else "",
            f"Wind kph: {wind_speed}" if wind_speed is not None else "",
            f"Humidity: {humidity}%" if humidity is not None else "",
        ]
        text = "; ".join(part for part in summary_parts if part)
        if not text:
            return []

        return [
            RawTextItem(
                source=self.source_name,
                text=text,
                location_hint=location_hint_from_text(text),
                timestamp=datetime.now(timezone.utc),
            )
        ]


class XSearchAdapter(SourceAdapter):
    """
    Fetches recent posts from X (Twitter) matching a search query.
    Useful for capturing user-generated event reports, traffic disruptions, accidents, floods, concerts, etc.
    """

    def __init__(
        self,
        api_url: str = "https://api.twitter.com/v2/tweets/search/recent",
        bearer_token: str | None = None,
        query: str = "(traffic OR accident OR flood OR concert OR event) (Manila OR \"Metro Manila\") lang:en",
    ) -> None:
        super().__init__("x_search")
        self.api_url = api_url
        self.bearer_token = bearer_token
        self.query = query

    async def fetch(self, client: httpx.AsyncClient, limit: int) -> list[RawTextItem]:
        """Fetch recent tweets matching the search query."""
        if not self.bearer_token:
            # Silently skip if no bearer token configured
            return []

        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        params: dict[str, Any] = {
            "query": self.query,
            "max_results": min(limit, 100),
            "tweet.fields": "created_at,public_metrics,author_id",
            "expansions": "author_id",
            "user.fields": "username,verified",
        }

        try:
            response = await client.get(self.api_url, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
        except Exception as exc:
            # Log and continue; X search is optional
            return []

        try:
            payload = response.json()
        except Exception:
            return []

        tweets = payload.get("data", [])
        if not tweets:
            return []

        # Build a simple user map from includes if available (for author info)
        users_map = {}
        includes = payload.get("includes", {})
        for user in includes.get("users", []):
            users_map[user.get("id")] = user.get("username", "unknown")

        items: list[RawTextItem] = []
        for tweet in tweets[:limit]:
            text = str(tweet.get("text", "")).strip()
            if not text:
                continue

            created_at = str(tweet.get("created_at", "")).strip()
            author_id = str(tweet.get("author_id", ""))
            username = users_map.get(author_id, "user")

            # Preserve author in text for provenance
            full_text = f"[{username}] {text}"

            items.append(
                RawTextItem(
                    source=self.source_name,
                    text=full_text,
                    location_hint=location_hint_from_text(text),
                    timestamp=parse_timestamp(created_at),
                )
            )
        return items
