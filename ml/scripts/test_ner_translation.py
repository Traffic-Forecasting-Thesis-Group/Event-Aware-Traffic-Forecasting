#!/usr/bin/env python3
"""Test NER-based masking for Taglish translation.

Demonstrates how entity masking preserves place names, organization names,
and person names during translation, avoiding incorrect translations like
"España" (boulevard in Manila) -> "Spain".

Usage:
    python ml/scripts/test_ner_translation.py
"""
import sys
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.preprocessing.taglish_translator import TaglishTranslator


def main():
    print("=" * 80)
    print("NER-Based Taglish Translation Test")
    print("=" * 80)
    print()

    # Test samples with place names, org names, and regular text
    test_samples = [
        "Grabe baha sa España ngayon, ingat sa mga pauwi!",
        "Traffic update: Bumagal ang daloy sa EDSA northbound dahil sa accident.",
        "Breaking: Mayor Binay announced funding para sa C5 extension ngayong linggo.",
        "Sobrang traffic sa Ortigas Avenue, iniwasan ko ng Metro Manila.",
        "Ang LGU ay nag-suspend ng classes dahil sa Signal #3.",
        "Malakas na ulan, ingat sa Recto hanggang Mandaluyong area ngayon.",
    ]

    print("Initializing translator with NER masking...")
    translator = TaglishTranslator()
    print("✓ Translator initialized\n")

    print("-" * 80)
    print("TRANSLATION WITH NER MASKING (Default)")
    print("-" * 80)
    print()

    translations_with_ner = translator.translate_texts(test_samples, batch_size=3, use_ner=True)

    for src, tgt in zip(test_samples, translations_with_ner):
        print(f"SRC: {src}")
        print(f"EN : {tgt}")
        print()

    print()
    print("-" * 80)
    print("TRANSLATION WITHOUT NER MASKING (For Comparison)")
    print("-" * 80)
    print()

    translations_without_ner = translator.translate_texts(
        test_samples, batch_size=3, use_ner=False
    )

    for src, tgt in zip(test_samples, translations_without_ner):
        print(f"SRC: {src}")
        print(f"EN : {tgt}")
        print()

    print()
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print()

    # Highlight key differences
    critical_tokens = ["España", "EDSA", "C5", "Ortigas", "Recto", "Mandaluyong"]

    print("Checking if critical place names were preserved:\n")
    for src, with_ner, without_ner in zip(test_samples, translations_with_ner, translations_without_ner):
        # Check for place-name preservation
        for place in critical_tokens:
            if place.lower() in src.lower():
                with_preserved = place in with_ner or place.upper() in with_ner
                without_preserved = place in without_ner or place.upper() in without_ner

                status_with = "✓ PRESERVED" if with_preserved else "✗ TRANSLATED"
                status_without = "✓ PRESERVED" if without_preserved else "✗ TRANSLATED"

                if with_preserved != without_preserved:
                    print(f"  Place: {place}")
                    print(f"    With NER:    {status_with}")
                    print(f"    Without NER: {status_without}")
                    print()


if __name__ == "__main__":
    main()
