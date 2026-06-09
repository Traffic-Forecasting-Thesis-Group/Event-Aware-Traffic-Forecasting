import os
import time
import requests
import json
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

GDELT_API_URL = os.getenv("GDELT_API_URL", "https://api.gdeltproject.org/api/v2/doc/doc")

# Shortened query — GDELT has a ~500 char limit on the query param
QUERY = (
    '(traffic OR accident OR flood OR congestion OR "road closed" OR collision) '
    '("Metro Manila" OR EDSA OR SLEX OR NLEX OR Skyway OR Makati OR "Quezon City") '
    'sourcelang:English'
)

TIMEOUT = int(os.getenv("SOURCE_TIMEOUT_SECONDS", 20))
USER_AGENT = os.getenv("SOURCE_USER_AGENT", "EventAwareTrafficBot/1.0")
DELAY = 6  # seconds between requests — GDELT requires >5s
ARTLIST_RETRIES = 3


def gdelt_get(params, label):
    """Make a single GDELT request with error handling."""
    try:
        resp = requests.get(
            GDELT_API_URL,
            params=params,
            timeout=TIMEOUT,
            headers={"User-Agent": USER_AGENT}
        )
    except requests.exceptions.Timeout:
        print(f"  ✗ TIMEOUT on {label}")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"  ✗ CONNECTION ERROR on {label}: {e}")
        return None

    print(f"  Status : {resp.status_code}")

    if resp.status_code == 429:
        print("  ✗ Rate limited — wait 5s+ between requests.")
        return None
    if resp.status_code != 200:
        print(f"  ✗ Bad status: {resp.text[:300]}")
        return None

    text = resp.text.strip()
    if not text.startswith("{"):
        print(f"  ✗ Not JSON. Response: {text[:200]}")
        return None

    try:
        return resp.json()
    except Exception as e:
        print(f"  ✗ JSON parse error: {e}")
        return None


def test_env():
    print("\n" + "="*60)
    print("TEST 0 — ENV CHECK")
    print("="*60)
    print(f"  GDELT_API_URL = {GDELT_API_URL}")
    print(f"  Query length  = {len(QUERY)} chars")
    assert "gdeltproject.org" in GDELT_API_URL
    print("  ✓ OK")


def test_artlist():
    print("\n" + "="*60)
    print("TEST 1 — ARTICLE LIST")
    print("="*60)

    params = {
        "query":      QUERY,
        "mode":       "artlist",
        "format":     "json",
        "maxrecords": int(os.getenv("SOURCE_MAX_ITEMS_PER_SOURCE", 10)),
        "sort":       "DateDesc",
        "timespan":   "3d",
    }

    data = None
    for attempt in range(1, ARTLIST_RETRIES + 1):
        print(f"  Attempt {attempt}/{ARTLIST_RETRIES}")
        data = gdelt_get(params, "artlist")
        if data is not None:
            break
        if attempt < ARTLIST_RETRIES:
            print(f"  Waiting {DELAY}s before retry...")
            time.sleep(DELAY)

    if data is None:
        print("  ✗ No article list retrieved after retries.")
        return

    articles = data.get("articles", [])
    print(f"  Articles returned : {len(articles)}")

    if not articles:
        print("  ⚠ No articles. Try widening timespan to 7d.")
        return

    for i, a in enumerate(articles[:5], 1):
        print(f"  [{i}] {a.get('title','(no title)')[:70]}")
        print(f"       {a.get('seendate','')} | {a.get('domain','')} | {a.get('sourcecountry','')} | {a.get('language','')}")
        print(f"       {a.get('url','')[:80]}")
        print()

    with open("gdelt_artlist_result.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Saved → gdelt_artlist_result.json ({len(articles)} articles)")


def test_timeline():
    print("\n" + "="*60)
    print("TEST 2 — TIMELINE VOLUME")
    print("="*60)
    print(f"  Waiting {DELAY}s before request...")
    time.sleep(DELAY)

    params = {
        "query":          QUERY,
        "mode":           "timelinevol",
        "format":         "json",
        "timespan":       "7d",
        "TIMELINESMOOTH": 3,
    }

    data = gdelt_get(params, "timelinevol")
    if data is None:
        return

    timeline = data.get("timeline", [])
    print(f"  Timeline series returned : {len(timeline)}")

    for series in timeline[:1]:
        points = series.get("data", [])
        print(f"\n  Series: {series.get('series','')} ({len(points)} pts)")
        for pt in points[:5]:
            print(f"    {pt.get('date','')} → {pt.get('value','')}")

    with open("gdelt_timeline_result.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Saved → gdelt_timeline_result.json")


def test_tone():
    print("\n" + "="*60)
    print("TEST 3 — TONE TIMELINE")
    print("="*60)
    print(f"  Waiting {DELAY}s before request...")
    time.sleep(DELAY)

    params = {
        "query":    QUERY,
        "mode":     "timelinetone",
        "format":   "json",
        "timespan": "7d",
    }

    data = gdelt_get(params, "timelinetone")
    if data is None:
        return

    timeline = data.get("timeline", [])
    print(f"  Timeline series: {len(timeline)}")

    for series in timeline[:2]:
        points = series.get("data", [])
        print(f"\n  [{series.get('series','')}] {len(points)} pts")
        for pt in points[:3]:
            print(f"    {pt.get('date','')} → {pt.get('value','')}")

    with open("gdelt_tone_result.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Saved → gdelt_tone_result.json")


if __name__ == "__main__":
    test_env()
    test_artlist()
    if os.path.exists("gdelt_artlist_result.json"):
        test_timeline()
        test_tone()
    print("\n" + "="*60)
    print("ALL GDELT TESTS COMPLETE")
    print("="*60)