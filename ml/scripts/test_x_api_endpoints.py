#!/usr/bin/env python3
"""
X API Test - Try Alternative Endpoints

Try different X/Twitter API endpoints to find what's accessible
"""
import sys
import asyncio
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import httpx
from app.core.config import get_settings


async def test_x_api_endpoints():
    """Test different X API endpoints."""
    
    settings = get_settings()
    
    if not settings.x_bearer_token:
        print("❌ No bearer token")
        return
    
    print("=" * 100)
    print("X API ENDPOINT TEST - Finding accessible endpoints")
    print("=" * 100)
    print()
    
    headers = {"Authorization": f"Bearer {settings.x_bearer_token}"}
    
    endpoints = [
        {
            "name": "v2 Search Recent (current)",
            "url": "https://api.twitter.com/v2/tweets/search/recent",
            "params": {"query": "MMDA", "max_results": 10}
        },
        {
            "name": "v2 Search Recent (with tweet.fields)",
            "url": "https://api.twitter.com/v2/tweets/search/recent",
            "params": {
                "query": "MMDA traffic",
                "max_results": 10,
                "tweet.fields": "created_at,public_metrics"
            }
        },
        {
            "name": "v1.1 Search (tweets)",
            "url": "https://api.twitter.com/1.1/search/tweets.json",
            "params": {"q": "MMDA", "count": 10}
        },
        {
            "name": "v2 Tweets by ID",
            "url": "https://api.twitter.com/v2/tweets/1776041407",
            "params": {}
        },
        {
            "name": "v2 Users Me",
            "url": "https://api.twitter.com/2/users/me",
            "params": {}
        },
    ]
    
    async with httpx.AsyncClient(timeout=15) as client:
        for endpoint in endpoints:
            print(f"Testing: {endpoint['name']}")
            print(f"  URL: {endpoint['url']}")
            
            try:
                response = await client.get(
                    endpoint['url'],
                    headers=headers,
                    params=endpoint['params'] if endpoint['params'] else None
                )
                
                status = response.status_code
                
                if status == 200:
                    print(f"  ✓ Status: 200 (SUCCESS!)")
                    data = response.json()
                    if "data" in data:
                        tweets = data.get("data", [])
                        if isinstance(tweets, list):
                            print(f"  ✓ Found: {len(tweets)} tweets")
                            if tweets and len(tweets) > 0:
                                first = tweets[0]
                                text = first.get("text", first.get("full_text", ""))
                                print(f"  ✓ Sample: {text[:60]}...")
                        else:
                            print(f"  ✓ Response: {str(data)[:80]}...")
                    else:
                        print(f"  ✓ Response keys: {list(data.keys())}")
                        
                elif status == 401:
                    print(f"  ✗ Status: 401 Unauthorized")
                elif status == 403:
                    print(f"  ✗ Status: 403 Forbidden")
                elif status == 404:
                    print(f"  ✗ Status: 404 Not Found")
                else:
                    print(f"  ✗ Status: {status}")
                    
            except Exception as e:
                print(f"  ✗ Exception: {str(e)[:60]}")
            
            print()


if __name__ == "__main__":
    asyncio.run(test_x_api_endpoints())
