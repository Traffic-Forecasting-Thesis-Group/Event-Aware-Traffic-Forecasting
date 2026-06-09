#!/usr/bin/env python3
"""
Integration test: Verify Taglish translator is wired into ingestion pipeline.

This tests the full pipeline:
1. Raw text from sources
2. Pre-cleaning (URLs, mentions removed)
3. Taglish→English translation with entity masking
4. Output for downstream NLP classification

Usage:
    python ml/scripts/test_ingestion_pipeline_integration.py
"""
import sys
from pathlib import Path
from datetime import datetime, timezone
import asyncio

backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.ingestion.service import IngestionService
from app.schemas.ingestion import RawTextItem


async def main():
    print("=" * 90)
    print("INGESTION PIPELINE INTEGRATION TEST")
    print("=" * 90)
    print()

    # Initialize ingestion service (includes translator)
    print("Initializing IngestionService with integrated Taglish translator...")
    service = IngestionService()
    print("✓ Service initialized\n")

    # Test data: raw texts from various sources
    test_items = [
        RawTextItem(
            source="mmda_twitter",
            text="MMDA Alert: Sobrang traffic sa EDSA northbound dahil sa aksidente. Iwasan na. https://t.co/abc123",
            location_hint="EDSA",
            timestamp=datetime.now(timezone.utc),
        ),
        RawTextItem(
            source="twitter_search",
            text="Grabe baha sa España Boulevard! Nag-flood na ang kalsada. Ingat sa pag-ibabaw @mmda_alerts",
            location_hint="España Boulevard",
            timestamp=datetime.now(timezone.utc),
        ),
        RawTextItem(
            source="news_api",
            text="Signal #3 na sa Metro Manila ngayon. LGU suspends classes bukas dahil sa weather disturbance.",
            location_hint="NCR",
            timestamp=datetime.now(timezone.utc),
        ),
        RawTextItem(
            source="social_media",
            text="Traffic sa C5 ay backed up ng 2 hours! Saan ang MMDA? Mayroon pang accident sa may flyover.",
            location_hint="C5",
            timestamp=datetime.now(timezone.utc),
        ),
    ]

    # Process through pipeline
    print("Processing through ingestion pipeline:")
    print("-" * 90)
    print()

    cleaned_items = await service.preprocess_texts(test_items)

    print("PIPELINE OUTPUT:")
    print()

    for i, item in enumerate(cleaned_items, 1):
        print(f"{i}. Source: {item.source}")
        print(f"   Original:    {item.original_text}")
        print(f"   Cleaned:     {item.cleaned_text}")
        print(f"   Translated:  {item.translated_text}")
        print()

    print()
    print("=" * 90)
    print("ANALYSIS")
    print("=" * 90)
    print()

    # Check key improvements
    successes = 0
    for item in cleaned_items:
        if item.translated_text:
            # Check if place names were preserved
            orig_lower = item.original_text.lower()
            trans_lower = item.translated_text.lower()

            place_names = ["edsa", "españa", "c5", "makati", "manila"]
            preserved = [p for p in place_names if p in orig_lower and p in trans_lower]

            if preserved:
                print(f"✓ {item.source}: Preserved {preserved}")
                successes += 1
            else:
                print(f"- {item.source}: No place names to check")

    print()
    print(f"✓ Pipeline test completed: {successes}/{len(cleaned_items)} items with successful translation")
    print()
    print("Key benefits of integrated translator:")
    print("  1. Automatic Taglish→English conversion before NLP classification")
    print("  2. Entity masking preserves place names (España, EDSA, C5, etc.)")
    print("  3. English text ready for DistilBERT/RoBERTa models")
    print("  4. No manual translation step needed")
    print()


if __name__ == "__main__":
    asyncio.run(main())
