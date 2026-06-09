#!/usr/bin/env python3
"""
Test X (Twitter) API integration - Fetch MMDA posts

This script:
1. Calls X API to search for MMDA traffic posts
2. Ingests them through the pipeline (clean + translate)
3. Shows results side-by-side

Usage:
    python ml/scripts/test_x_api_integration.py
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timezone

backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import httpx
from app.core.config import get_settings
from app.ingestion.adapters import XSearchAdapter
from app.ingestion.service import IngestionService


async def test_x_api():
    """Test X API integration with MMDA traffic posts."""
    
    print("=" * 100)
    print("X API INTEGRATION TEST - MMDA Traffic Posts")
    print("=" * 100)
    print()

    settings = get_settings()
    
    # Check credentials
    if not settings.x_bearer_token:
        print("ERROR: X_BEARER_TOKEN not set in .env")
        return
    
    print(f"✓ X Bearer Token found: {settings.x_bearer_token[:50]}...")
    print(f"✓ Search query: {settings.x_search_query[:80]}...")
    print()

    # Step 1: Fetch from X API using XSearchAdapter
    print("STEP 1: Fetching posts from X API...")
    print("-" * 100)
    
    adapter = XSearchAdapter(
        api_url=settings.x_search_api_url,
        bearer_token=settings.x_bearer_token,
        query=settings.x_search_query,
    )
    
    async with httpx.AsyncClient(timeout=settings.source_timeout_seconds) as client:
        try:
            raw_items = await adapter.fetch(client, limit=5)
            print(f"✓ Fetched {len(raw_items)} posts from X API")
            print()
        except Exception as e:
            print(f"ERROR: Failed to fetch from X API: {e}")
            return

    if not raw_items:
        print("No posts found matching the query")
        return

    # Step 2: Show raw posts
    print("STEP 2: Raw Posts from X")
    print("-" * 100)
    for i, item in enumerate(raw_items, 1):
        print(f"\n{i}. @{item.source}")
        print(f"   Text: {item.text[:100]}..." if len(item.text) > 100 else f"   Text: {item.text}")
        print(f"   Time: {item.timestamp}")
        print(f"   Hint: {item.location_hint}")

    # Step 3: Process through ingestion pipeline (clean + translate)
    print()
    print()
    print("STEP 3: Processing through Ingestion Pipeline")
    print("-" * 100)
    
    service = IngestionService()
    
    try:
        cleaned_items = await service.preprocess_texts(raw_items)
        print(f"✓ Pipeline processed {len(cleaned_items)} items")
        print()
    except Exception as e:
        print(f"ERROR: Pipeline processing failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 4: Show results
    print("STEP 4: Final Results (Cleaned + Translated)")
    print("-" * 100)
    
    for i, item in enumerate(cleaned_items, 1):
        print(f"\n{i}. Source: {item.source}")
        print(f"   Raw Text:      {item.original_text[:90]}...")
        print(f"   Cleaned:       {item.cleaned_text[:90]}...")
        if item.translated_text:
            print(f"   Translated:    {item.translated_text[:90]}...")
        else:
            print(f"   Translated:    (skipped)")
        print(f"   Location Hint: {item.location_hint}")

    # Step 5: Summary
    print()
    print()
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    
    successful = sum(1 for item in cleaned_items if item.translated_text)
    print(f"✓ Fetched from X API: {len(raw_items)} posts")
    print(f"✓ Successfully cleaned: {len(cleaned_items)} items")
    print(f"✓ Successfully translated: {successful}/{len(cleaned_items)} items")
    print()
    print("✓ X API integration is working!")
    print()


if __name__ == "__main__":
    asyncio.run(test_x_api())
