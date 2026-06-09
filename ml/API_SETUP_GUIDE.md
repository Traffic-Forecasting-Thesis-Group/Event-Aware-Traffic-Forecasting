# API Setup Guide

To fetch real data from News API and GDELT, you need to set up credentials.

## News API

**What you get:** Articles from major Philippine news sources including ABS-CBN News, TV5, Manila Bulletin, The Philippine Star, ONE News, GMA News, and more.

### Step 1: Get Free API Key

1. Visit: https://newsapi.org/
2. Click "Get API Key"
3. Sign up with your email (free account)
4. Copy your API key

### Step 2: Set Environment Variable

**Option A: Windows (PowerShell)**
```powershell
$env:NEWS_API_KEY = "your_api_key_here"
```

**Option B: Windows (Command Prompt)**
```cmd
set NEWS_API_KEY=your_api_key_here
```

**Option C: Add to `.env` file** (create if doesn't exist)
```bash
echo "NEWS_API_KEY=your_api_key_here" > .env
```

### Step 3: Run Script with API Key

```bash
python ml/scripts/fetch_multi_source_training_data.py \
    --api-key "your_api_key_here" \
    --sources social_media news_api gdelt \
    --output ml/data/x_multi_source_training.csv \
    --limit 50
```

Or use environment variable:
```bash
$env:NEWS_API_KEY = "your_api_key_here"
python ml/scripts/fetch_multi_source_training_data.py
```

## GDELT

**What you get:** Global event data that can be filtered for Metro Manila traffic events.

### Note on GDELT

The script currently uses the **GDELT REST API** (free, no key required for search). For more powerful data access (BigQuery integration), you would need:

- Google Cloud account
- BigQuery access
- Service account credentials

For now, the REST API works fine for fetching recent events.

## Fallback Behavior

If API keys are not provided or APIs are unreachable:
- **News API** → Uses stub data with sample articles
- **GDELT** → Uses stub data with sample events
- **Social Media** → Loads from `ml/outputs/x_fetch/x_recent_posts_translated.csv`

This ensures the script always produces output for annotation.

## Supported Philippine News Sources

These sources are automatically searched in News API:

| Source ID | Name |
|-----------|------|
| `abs-cbn-news` | ABS-CBN News |
| `tv5` | TV5 (News5) |
| `manila-bulletin` | Manila Bulletin |
| `the-philippine-star` | The Philippine Star |
| `gma-news` | GMA News |
| `abs-cbn-news-online` | ABS-CBN News Online |
| `inquirer` | Inquirer.net |
| `rappler` | Rappler |

## Testing Your Setup

To verify your News API key works:

```bash
$env:NEWS_API_KEY = "your_api_key_here"
python -c "
import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as client:
        params = {
            'q': 'traffic',
            'sources': 'abs-cbn-news,manila-bulletin',
            'language': 'en',
            'pageSize': '5',
            'apiKey': 'your_api_key_here'
        }
        response = await client.get('https://newsapi.org/v2/everything', params=params)
        print('Status:', response.status_code)
        print('Articles:', len(response.json().get('articles', [])))

asyncio.run(test())
"
```

Expected output:
```
Status: 200
Articles: 5
```

## Quick Start

### Without API Key (Uses Stubs)
```bash
python ml/scripts/fetch_multi_source_training_data.py
```

### With News API Key
```bash
python ml/scripts/fetch_multi_source_training_data.py --api-key "your_key_here"
```

### All Sources with Full Limits
```bash
python ml/scripts/fetch_multi_source_training_data.py \
    --api-key "your_key_here" \
    --sources social_media news_api gdelt \
    --output ml/data/x_multi_source_training.csv \
    --limit 100
```

---

**Next Step:** After setting up API key and running the fetch script, load the resulting CSV in `interactive_labeling.ipynb` to begin annotation.
