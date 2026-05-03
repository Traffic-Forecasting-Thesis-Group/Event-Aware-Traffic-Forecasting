from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.schemas.ingestion import RawTextItem


def parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)

    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"]:
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
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
                    timestamp=parse_timestamp(str(article.get("seendate", ""))),
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
