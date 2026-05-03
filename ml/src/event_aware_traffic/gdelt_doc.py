from __future__ import annotations
from json import JSONDecodeError
from typing import Any
from urllib.parse import urlparse

import requests

DEFAULT_GDELT_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

class GDELTDocFetchError(RuntimeError):
    pass

def _domain_from_url(url: str) -> str:
    parsed_url = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

def _extract_gdelt_articles(payload: dict[str, Any]) -> list[dict[str, Any]]:
    articles = payload.get("articles")
    if isinstance(articles, list):
        return articles
    result = payload.get("result")
    if isinstance(result, list):
        nested = result.get("articles")
        if isinstance(nested, list):
            return nested
    return []

def fetch_new_articles(
    query: str = "location:Philippines (flood OR baha OR traffic OR accident OR road closure OR roadwork OR construction OR reblocking OR strike OR tigil-pasada OR rally OR concert OR event OR disaster OR emergency OR typhoon OR bagyo OR heavy rain OR breakdown OR aberya OR procession motorcade OR fiesta OR payday OR carmageddon)",
    api_endpoint: str = DEFAULT_GDELT_API_URL,
    timespan: str = "15m",
    output_format: str = "json",
    max_records: int = 50,
    timeout_seconds: int = 30,
    mode: str = "artlist",
) -> list[dict[str, Any]]:
    params = {
        "query": query,
        "timespan": timespan,
        "format": output_format,
        "maxrecords": max_records,
        "mode": mode,
    }
    
    try:
        response = requests.get(api_endpoint, params=params, timeout=timeout_seconds)
        response.raise_for_status()
    except requests.RequestException as exception:
        raise GDELTDocFetchError("DOC API request failed") from exception   
    
    try:
        payload = response.json()
    except JSONDecodeError as exception:
        raise GDELTDocFetchError("Failed to decode DOC API response as JSON") from exception
    
    parsed_articles: list[dict[str, Any]] = []
    for article in _extract_gdelt_articles(payload):
        url = str(article.get("url") or article.get("sourceurl") or "").strip()
        if not url:
            continue
        
        title = str(article.get("title") or "").strip()
        published_at = str(
            article.get("seendate") 
            or article.get("datetime")
            or article.get("publishedAt")
            or "" 
        ).strip()
        domain = str(article.get("domain") or _domain_from_url(url)).strip()
        text_snippet = " | ".join(part for part in [title, published_at] if part)

        parsed_articles.append(
            {
                "url": url,
                "domain": domain,
                "title": title,
                "published_at": published_at,
                "text_snippet": text_snippet,
                "source": "gdelt_doc",
            }
        )

    return parsed_articles