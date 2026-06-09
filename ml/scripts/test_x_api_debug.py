#!/usr/bin/env python3
"""
X API Debug Test - See actual API response

This shows what the X API is returning (errors, rate limits, etc)
"""
import sys
import asyncio
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import httpx
from app.core.config import get_settings


async def test_x_api_debug():
    """Debug X API response."""
    
    settings = get_settings()
    
    if not settings.x_bearer_token:
        print("❌ No bearer token")
        return
    
    print("=" * 100)
    print("X API DEBUG TEST")
    print("=" * 100)
    print()
    
    api_url = "https://api.twitter.com/v2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {settings.x_bearer_token}"}
    
    # Simple query
    params = {
        "query": "MMDA",
        "max_results": 10,
    }
    
    print(f"API URL: {api_url}")
    print(f"Query: {params['query']}")
    print(f"Max Results: {params['max_results']}")
    print()
    print("Sending request...")
    print("-" * 100)
    print()
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(api_url, headers=headers, params=params)
            
            print(f"Status Code: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            print()
            print("Response Body:")
            print(response.text[:500])
            print()
            
            if response.status_code == 200:
                data = response.json()
                tweets = data.get("data", [])
                meta = data.get("meta", {})
                
                print(f"✓ Tweets found: {len(tweets)}")
                print(f"✓ Meta: {meta}")
                print()
                
                if tweets:
                    print("Sample tweets:")
                    for i, tweet in enumerate(tweets[:3], 1):
                        print(f"  {i}. {tweet.get('text', '')}")
            
        except Exception as e:
            print(f"❌ Exception: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_x_api_debug())
