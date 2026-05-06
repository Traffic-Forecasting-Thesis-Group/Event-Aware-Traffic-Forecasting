# Taglish-to-English Translation Module

## Overview

The `TaglishTranslator` module provides robust translation of Filipino/Taglish text to English using:

1. **MarianMT Seq2Seq Model** (`Helsinki-NLP/opus-mt-tl-en`) for core translation
2. **Entity Masking** (NER + Gazetteer) to preserve place names and proper nouns
3. **Pre-translation Regex Cleaning** to remove URLs, mentions, and noise

## Problem Statement

Pre-trained neural translation models like MarianMT often mistranslate **local place names and proper nouns** that are context-dependent:

- **"España"** (a boulevard in Manila) → ❌ "Spain" (without masking)
- **"EDSA"** (major road in Metro Manila) → ❌ "EDSA" (sometimes garbled)
- **"Makati"** (city in NCR) → ❌ "Natti" (corrupted without masking)

## Solution: Entity Masking Strategy

### How It Works

1. **Identify Entities**: Detect place names and proper nouns before translation
2. **Mask Entities**: Replace them with placeholders like `<LOC_0>`, `<ORG_1>`
3. **Translate**: Translate the masked text (skips protected entities)
4. **Unmask**: Restore original entity names in the final translation

### Example

```
Input:  "Grabe baha sa España ngayon, ingat sa mga pauwi sa Makati!"

Step 1 (Mask):     "Grabe baha sa <LOC_0> ngayon, ingat sa mga pauwi sa <LOC_1>!"
                   Mapping: {<LOC_0>: "España", <LOC_1>: "Makati"}

Step 2 (Translate): "Serious flood at <LOC_0> today, be careful going home in <LOC_1>!"

Step 3 (Unmask):   "Serious flood at España today, be careful going home in Makati!"

Output: ✓ Place names preserved!
```

## Implementation Approaches

### 1. **Gazetteer-Based Masking (PRIMARY - RECOMMENDED)**

Uses a maintained list of place names and proper nouns specific to Manila/NCR.

**Advantages:**
- Fast (no model download)
- Highly accurate for known locations
- Works offline
- No GPU/memory overhead
- Easy to customize and extend

**Disadvantages:**
- Requires manual maintenance of place-name list
- Cannot handle completely unknown entities
- Limited to pre-defined gazetteer

**Current Gazetteer Coverage:**
- Manila streets: España, Recto, Mandaluyong, Sta. Mesa, Quiapo, Tondo, Binondo, etc.
- Major roads: EDSA, C5, Ortigas Avenue, etc.
- Cities: Quezon City, Makati, Pasig, Marikina, Paranaque, Muntinlupa, etc.
- Landmarks/Orgs: BGC, SM, Robinsons, MOA, MMDA, LGU, etc.

### 2. **NER-Based Masking (OPTIONAL - SECONDARY)**

Uses multilingual Named Entity Recognition (NER) to detect entities.

**Advantages:**
- Can detect unknown entities
- Language-agnostic
- Robust across diverse text

**Disadvantages:**
- Requires downloading ~500MB NER model
- Slower (10-20% latency added)
- Needs GPU for optimal performance
- NER models sometimes misclassify place names

**Note:** NER automatically falls back to gazetteer if model load fails.

## Usage

### Basic Translation

```python
from app.preprocessing.taglish_translator import TaglishTranslator

# Initialize (first run downloads ~300MB models)
translator = TaglishTranslator()

# Translate list of texts (with entity masking enabled by default)
texts = [
    "Malakas na ulan sa EDSA, traffic suspended ngayon.",
    "Flooding sa España area, ingat mga residents ng Makati!",
]

results = translator.translate_texts(texts)
# ['Heavy rain on EDSA, traffic suspended now.',
#  'Flooding on España area, be careful residents of Makati!']
```

### Disable Entity Masking (Baseline)

```python
# For comparison or if masking causes issues:
results = translator.translate_texts(texts, use_ner=False)
```

### Translate DataFrame

```python
import pandas as pd

df = pd.DataFrame({
    'social_post': [
        'Signal #3 sa NCR, suspended classes ngayon.',
        'Grabe traffic sa C5, 2 hours na ako dito!',
    ]
})

# Adds 'social_post_en' column with translations
translator.translate_dataframe(df, 'social_post', batch_size=32)
```

## Customizing the Gazetteer

To add more place names:

**File:** `backend/app/preprocessing/taglish_translator.py`

Find the `MANILA_GAZETTEER` class variable and add new locations:

```python
MANILA_GAZETTEER = {
    "espana", "edsa", "c5", "quezon city", "ortigas",
    # ... add your locations in lowercase
    "my_new_place", "another_street",
}
```

### Recommended Additions

- Street names in your AOR (area of responsibility)
- Barangay names
- Building names (offices, malls, hospitals)
- Schools
- Government agencies

## Performance Characteristics

### Translation Speed

| Scenario | Batch Size | Time per 100 texts |
|----------|------------|-------------------|
| Without masking | 32 | ~15s |
| Gazetteer masking | 32 | ~16s (+6% overhead) |
| NER + masking | 32 | ~20s (+33% overhead, first run slower) |

### Memory Usage

| Approach | GPU Memory | CPU Memory |
|----------|-----------|-----------|
| Marian only | ~2GB | ~1GB |
| + Gazetteer | ~2GB | ~1GB |
| + NER model | ~4-6GB | ~2GB |

### First Run

- **Without NER:** ~10 seconds (model caching)
- **With NER:** ~2-3 minutes (downloading 300MB+ NER model)

## Testing & Validation

### Run Test Suite

```bash
python ml/scripts/test_ner_translation.py
```

This compares translations WITH and WITHOUT entity masking on a set of real Taglish examples.

### Expected Output (WITH masking enabled)

```
SRC: Grabe baha sa España ngayon, ingat sa mga pauwi!
EN : Severe flood on España today, be careful going home!  ✓ PRESERVE España

SRC: Traffic sa EDSA northbound dahil sa banggaan ng 3 sasakyan.
EN : Traffic on EDSA northbsound because of 3 - vehicle crash  ✓ PRESERVE EDSA
```

### Expected Output (WITHOUT masking)

```
SRC: Grabe baha sa España ngayon, ingat sa mga pauwi!
EN : Serious Floods in Spain today, beware of those returning home!  ✗ WRONG: España→Spain

SRC: Traffic sa EDSA northbound dahil sa banggaan ng 3 sasakyan.
EN : EDSA northbsound Traffic due to acident  ✗ DEGRADED: garbled output
```

## Architecture Decisions

### Why Gazetteer + NER?

1. **Gazetteer First**: Fast, reliable for known locations in your domain
2. **NER Fallback**: Catches unknown entities that gazetteer misses
3. **Hybrid Approach**: Best of both worlds—speed + robustness

### Why Not Just Fine-tune MarianMT?

Fine-tuning on a small in-domain corpus is possible but:
- Requires labeled training data (500+ parallel sentences)
- Takes time to collect and annotate
- Needs retraining as new place names emerge
- Gazetteer is faster to maintain

**Recommendation:** Start with gazetteer. If accuracy plateaus, consider fine-tuning.

## Troubleshooting

### "España" still translates to "Spain"

**Cause:** Place name not in gazetteer or NER/masking disabled.

**Solution:** 
```python
# Add to MANILA_GAZETTEER
translator.MANILA_GAZETTEER.add("espana")
```

Or ensure `use_ner=True` (default).

### Masking breaks translation quality

**Cause:** Placeholder tokens confuse the model or critical context is masked.

**Solution:**
```python
# Disable masking for that text
result = translator.translate_texts([problematic_text], use_ner=False)
```

### Out of Memory (OOM)

**Cause:** NER model or batch size too large.

**Solution:**
```python
# Reduce batch size
translator.translate_texts(texts, batch_size=8, use_ner=True)

# Or disable NER
translator.translate_texts(texts, batch_size=32, use_ner=False)
```

## Dependencies

```
transformers>=4.30.0
torch>=2.0.0
sentencepiece>=0.1.99
```

Optional (for NER):
```
accelerate>=0.20.0  # Faster inference on GPU
```

Install:
```bash
pip install transformers torch sentencepiece
```

## Integration with Ingestion Pipeline

Wire into your ingestion workflow before NLP classification:

```python
from app.preprocessing.taglish_translator import TaglishTranslator
from app.nlp.verify import verify_text_quality

translator = TaglishTranslator()

# In your ingestion handler:
def preprocess_social_post(raw_text):
    # 1. Translate Taglish to English
    english_text = translator.translate_texts([raw_text])[0]
    
    # 2. Verify quality (now safe for English-only models)
    is_valid = verify_text_quality(english_text)
    
    # 3. Return for further processing
    return english_text if is_valid else None
```

## Future Improvements

1. **Expand Gazetteer**: Automate extraction from OSM or city databases
2. **Context-Aware Masking**: Use sentence context to detect homonyms
3. **Fine-tuning**: Collect parallel Taglish↔English corpus, fine-tune MarianMT
4. **Active Learning**: Log mistranslations, use feedback to improve gazetteer
5. **Evaluation Metrics**: Add BLEU/METEOR scoring for translation quality tracking

## References

- [Helsinki-NLP opus-mt-tl-en Model](https://huggingface.co/Helsinki-NLP/opus-mt-tl-en)
- [Taglish Processing Literature](https://aclanthology.org/)
- [Named Entity Recognition with Transformers](https://huggingface.co/tasks/token-classification)
