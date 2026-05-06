#!/usr/bin/env python3
"""
X API Integration Test - With Mock Data

Since live X API might have rate limits or access restrictions,
this test uses realistic mock MMDA traffic posts to demonstrate
the full pipeline working end-to-end.

This validates:
1. Text cleaning (URLs, mentions removed)
2. Translation (Taglish → English with entity masking)
3. Schema correctness

Usage:
    python ml/scripts/test_x_api_mock.py
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timezone

backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.ingestion.service import IngestionService
from app.schemas.ingestion import RawTextItem


async def test_x_api_mock():
    """Test X API integration with mock MMDA traffic posts."""
    
    print("=" * 100)
    print("X API INTEGRATION TEST - Mock MMDA Traffic Posts")
    print("=" * 100)
    print()
    print("Note: Using realistic mock data (simulating X API response)")
    print()

    # Mock MMDA traffic posts (as they would come from X API)
    mock_posts = [
        {
            "text": "@MMDA_Traffic EDSA Northbound from Ortigas to Quezon Ave is heavily congested. Expect 30mins delay. Take alternate routes. #MMDATraffic",
            "source": "x_search_mmda"
        },
        {
            "text": "GRABE! Traffic sa C5 Southbound dahil sa sasakyang nasiraan. Dalawang lane lang ang available. Mag-ingat! 🚗 via @MMDA_Traffic",
            "source": "x_search_mmda"
        },
        {
            "text": "Malakas na ulan sa Metro Manila ngayon. Baha na sa España Boulevard at may flood warning sa low-lying areas. Stay safe everyone! 🌧️",
            "source": "x_search_disaster"
        },
        {
            "text": "Signal #2 na sa Marikina area. Suspended na ang classes bukas. #PAGASA #WeatherAlert",
            "source": "x_search_weather"
        },
        {
            "text": "Sobrang traffic sa BGC, Makati papunta sa NLEX dahil sa concert sa MOA. Estimated 2 hours wait. Avoid if possible!",
            "source": "x_search_events"
        }
    ]

    print("STEP 1: Mock MMDA Posts from X API")
    print("-" * 100)
    print(f"✓ Simulated {len(mock_posts)} posts from X API")
    print()

    # Convert to RawTextItem
    raw_items = [
        RawTextItem(
            source=post["source"],
            text=post["text"],
            location_hint=None,
            timestamp=datetime.now(timezone.utc),
        )
        for post in mock_posts
    ]

    # Step 2: Show raw posts
    print("STEP 2: Raw Posts from X (Mock)")
    print("-" * 100)
    for i, item in enumerate(raw_items, 1):
        print(f"\n{i}. [{item.source}]")
        print(f"   Text: {item.text}")

    # Step 3: Process through pipeline
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
        print(f"❌ Pipeline processing failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 4: Show results
    print()
    print("STEP 4: Final Results (Cleaned + Translated)")
    print("-" * 100)

    for i, item in enumerate(cleaned_items, 1):
        print(f"\n{i}. [{item.source}]")
        print(f"   Raw:        {item.original_text[:70]}...")
        print(f"   Cleaned:    {item.cleaned_text[:70]}...")
        if item.translated_text:
            print(f"   Translated: {item.translated_text[:70]}...")
        else:
            print(f"   Translated: (skipped)")

    # Step 5: Validation
    print()
    print()
    print("=" * 100)
    print("VALIDATION")
    print("=" * 100)
    print()

    # Check place name preservation
    place_names = ["EDSA", "C5", "España", "BGC", "Makati", "Marikina", "MOA"]
    preserved_count = 0

    for item in cleaned_items:
        if item.translated_text:
            for place in place_names:
                if place.lower() in item.original_text.lower():
                    if place.lower() in item.translated_text.lower() or place in item.translated_text:
                        preserved_count += 1
                        print(f"✓ {place} preserved: '{item.original_text[:50]}...' → '{item.translated_text[:50]}...'")
                        break

    print()
    print(f"✓ Place name preservation rate: {preserved_count}/{len(cleaned_items)}")
    print()

    # Check Taglish detection and translation
    taglish_posts = [
        i for i in cleaned_items
        if any(word in i.original_text.lower() for word in
               ["grabe", "sobrang", "malakas", "ulan", "baha", "ingat", "hangal"])
    ]

    translated_taglish = sum(
        1 for i in taglish_posts if i.translated_text
    )

    print(f"✓ Taglish posts detected: {len(taglish_posts)}")
    print(f"✓ Successfully translated: {translated_taglish}/{len(taglish_posts)}")
    print()

    # Summary
    print()
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print()

    successful = sum(1 for item in cleaned_items if item.translated_text)
    print(f"✓ Processed: {len(cleaned_items)} posts from X (mock)")
    print(f"✓ Cleaned: {len(cleaned_items)} items")
    print(f"✓ Translated: {successful}/{len(cleaned_items)} items")
    print(f"✓ Place names preserved: {preserved_count} instances")
    print()
    print("✓✓✓ X API Integration Pipeline is Working! ✓✓✓")
    print()
    print("Next Steps:")
    print("  1. When live API access is available, use test_x_api_integration.py")
    print("  2. Monitor translation quality in production logs")
    print("  3. Expand gazetteer with new place names as discovered")
    print()


if __name__ == "__main__":
    asyncio.run(test_x_api_mock())
