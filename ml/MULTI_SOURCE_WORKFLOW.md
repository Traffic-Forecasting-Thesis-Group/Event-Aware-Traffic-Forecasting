# Multi-Source Training Data Pipeline

This guide explains how to fetch and label data from **Social Media**, **News API**, and **GDELT** for training DistilBERT and RoBERTa.

## Architecture

Your backend ingestion system supports multiple sources:

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Sources                              │
├──────────────────┬─────────────────────┬────────────────────┤
│ Social Media     │ News API            │ GDELT              │
│ • X/Twitter      │ • Inquirer          │ • REST API         │
│ • MMDA RSS       │ • GMA News          │ • BigQuery         │
│                  │ • Rappler           │ • 15-min updates   │
│                  │ • PAGASA            │                    │
└──────────────────┴─────────────────────┴────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   Backend Adapter Pattern             │
        │  (backend/app/ingestion/adapters.py)  │
        │                                       │
        │  - RSSSourceAdapter                   │
        │  - NewsAPIAdapter                     │
        │  - GDELTAdapter / GDELTBigQueryAdapter│
        │  - XSearchAdapter                     │
        │  - MMDAAdapter                        │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │  Unified RawTextItem Schema           │
        │  {                                    │
        │    source: str,                       │
        │    text: str,                         │
        │    location_hint: str | None,        │
        │    timestamp: datetime                │
        │  }                                    │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │  Text Preprocessing Pipeline          │
        │  1. Clean URLs, mentions, whitespace │
        │  2. Translate Taglish → English      │
        │  3. Return CleanedTextItem           │
        └───────────────────────────────────────┘
                            │
                            ▼
    ┌─────────────────────────────────────────────────┐
    │  x_multi_source_training.csv                    │
    │  (Combined data ready for annotation)           │
    │                                                  │
    │  post_id | created_at | raw_text | source_type │
    │  ________|___________|__________|________________│
    │  social_001 | ... | MMDA ALERT | social_media  │
    │  news_001   | ... | [News API] | news_api      │
    │  gdelt_001  | ... | [GDELT]    | gdelt         │
    └─────────────────────────────────────────────────┘
                            │
                            ▼
    ┌─────────────────────────────────────────────────┐
    │  interactive_labeling.ipynb                     │
    │  → Annotate with binary rubric                  │
    │  → Score: 1=Reliable, 0=Unreliable             │
    └─────────────────────────────────────────────────┘
                            │
                            ▼
    ┌─────────────────────────────────────────────────┐
    │  x_labeled_batch_<timestamp>_<annotator>.csv    │
    │  x_labeled_master.csv (merged)                  │
    └─────────────────────────────────────────────────┘
                            │
                            ▼
    ┌─────────────────────────────────────────────────┐
    │  fuse_traffic_training.ipynb                    │
    │  → Train DistilBERT (event detection)          │
    │  → Train RoBERTa (reliability scoring)         │
    │  → Export model artifacts                       │
    └─────────────────────────────────────────────────┘
```

## Workflow

### Step 1: Fetch Multi-Source Data

Run the fetch script to combine Social Media, News API, and GDELT data:

```bash
cd c:\Users\Japoy\OneDrive\Documents\Desktop\Github\Event-Aware-Traffic-Forecasting

python ml/scripts/fetch_multi_source_training_data.py \
    --sources social_media news_api gdelt \
    --output ml/data/x_multi_source_training.csv \
    --limit 50
```

**Output:**
- `ml/data/x_multi_source_training.csv` - Combined data from all sources, ready for annotation

**What this does:**
1. Fetches social media posts from **most recent** timestamped CSV (e.g., `x_recent_posts_translated_20260506_1618.csv`)
2. Prepares News API data (currently using stub; can connect to real API if configured)
3. Prepares GDELT data (currently using stub; can connect to REST API if configured)
4. Combines all into one CSV with columns: `post_id, created_at, raw_text, translated_text, source_type, reliability_label, annotator_name, ...`

### Continuous Data Collection

To continuously fetch new X posts and create timestamped outputs:

```bash
# Fetches new posts and saves as: x_recent_posts_translated_20260507_0930.csv
python ml/scripts/test_x_fetch_posts.py
```

Each run creates a new timestamped file without overwriting previous data, supporting hourly/daily collection cycles.

### Step 2: Annotate with Binary Rubric

Open `ml/notebooks/interactive_labeling.ipynb` and:

1. **Cell 1:** Load the multi-source CSV
   ```python
   CSV_PATH = './ml/data/x_multi_source_training.csv'  # Update to multi-source file
   ```

2. **Cell 2:** Review the rubric and source-specific rules

3. **Cell 3:** Annotate each post as **1 (Reliable) or 0 (Unreliable)**
   - Apply the 4 annotation rules based on source type
   - Institutional sources (News API, GDELT verified): provisional 1 if specific event
   - Commuter posts (Social Media): 1 ONLY if objective + specific location
   - Taglish not auto-unreliable if semantic content is specific

4. **Cell 4:** Save batch → `x_labeled_batch_<timestamp>_<annotator>.csv`

5. **Cell 5:** Merge batches → `x_labeled_master.csv`

6. **Cell 6:** Inspect results

### Step 3: Train Models

Open `ml/notebooks/fuse_traffic_training.ipynb` and:

1. Update CSV path to the labeled master file:
   ```python
   LABELED_PATH = Path('./ml/data/x_labeled_master.csv')
   ```

2. Run all cells to train DistilBERT and RoBERTa

3. Models are saved to:
   - `distilbert_event/` (event detection model)
   - `roberta_reliability/` (reliability scoring model)

## Connecting Real APIs (Optional)

To use real data instead of stubs, configure these environment variables:

### News API
```bash
export NEWS_API_KEY="your_newsapi_org_key"
export NEWS_API_URL="https://newsapi.org/v2/everything"
```

### GDELT (BigQuery)
```bash
# Requires Google Cloud credentials
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
```

### X/Twitter
```bash
export X_BEARER_TOKEN="your_x_api_bearer_token"
```

## Data Format Reference

All sources are standardized to this CSV format:

| Column | Type | Example |
|--------|------|---------|
| `post_id` | str | `social_001`, `news_api_001`, `gdelt_001` |
| `created_at` | ISO datetime | `2026-05-06T16:18:26Z` |
| `raw_text` | str | Original text from source |
| `translated_text` | str | English translation (Taglish→English) |
| `lang` | str | `en`, `tl`, `unknown` |
| `source_type` | str | `social_media`, `news_api`, `gdelt` |
| `reliability_label` | int | `1` (Reliable), `0` (Unreliable), `NA` (not yet annotated) |
| `annotator_name` | str | Your name |
| `annotation_time` | ISO datetime | When you labeled it |
| `notes` | str | Optional reasoning |

## Output Filenames (With Timestamps)

Social media posts now save with timestamps to support continuous data collection:

**Format:** `x_recent_posts_translated_YYYYMMDD_HHMM.csv`

**Examples:**
- `x_recent_posts_translated_20260506_1618.csv` (May 6, 2026 at 4:18 PM)
- `x_recent_posts_translated_20260507_0930.csv` (May 7, 2026 at 9:30 AM)

**Why timestamped?**
- Track when data was fetched
- Support hourly/daily collection cycles without overwriting
- Multi-source fetch automatically finds the **most recent** timestamped file

## Key Differences by Source

### Social Media (X/Twitter, MMDA)
- **Source type**: `social_media`
- **Characteristics**: Real-time, user-generated, mixed quality
- **Annotation rule**: Reliable (1) ONLY if objective report with specific location + incident type
- **Common issue**: Vague complaints ("traffic is bad") = Unreliable (0)

### News API (Inquirer, GMA, Rappler, PAGASA)
- **Source type**: `news_api`
- **Characteristics**: Professional journalists, vetted information
- **Annotation rule**: Provisionally Reliable (1) if event is specific and traffic-relevant
- **Common issue**: Non-traffic news (e.g., "MMDA appoints new director") = Unreliable (0)

### GDELT (Automated global event scraping)
- **Source type**: `gdelt`
- **Characteristics**: Automated, can have errors or metaphorical language, 15-minute updates
- **Annotation rule**: DO NOT auto-score as reliable; evaluate for accuracy
- **Common issue**: "Web traffic jams" (metaphorical) = Unreliable (0)

## Progress Tracking

| Phase | Status | Output |
|-------|--------|--------|
| 1. Fetch multi-source | In progress | `x_multi_source_training.csv` |
| 2. Annotate | Waiting for you | `x_labeled_batch_*.csv` |
| 3. Merge | After annotation | `x_labeled_master.csv` |
| 4. Train | After merge | `distilbert_event/`, `roberta_reliability/` |

## Troubleshooting

**Q: How do I load multi-source data in interactive_labeling.ipynb?**

A: In Cell 1, update the CSV path:
```python
CSV_PATH = Path('./ml/data/x_multi_source_training.csv')
```

**Q: What if News API / GDELT adapters are not configured?**

A: The script currently uses **stub data** for testing. To enable real fetching:
1. Install required dependencies: `pip install google-cloud-bigquery newsapi`
2. Set environment variables (see "Connecting Real APIs")
3. Uncomment the httpx code in `fetch_multi_source_training_data.py`

**Q: How many posts should I annotate?**

A: Target 200-300 labeled posts for robust training (currently have ~122 from social media). Multi-source combination should reach this faster.

**Q: Can I run the fetch script multiple times?**

A: Yes. Each run appends new posts (duplicates are removed by `post_id` during merging).

---

**Next step:** Run the fetch script and begin annotation!
