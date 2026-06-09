#!/usr/bin/env python3
"""
Simple X API test - Check API connectivity and response

This script:
1. Calls X API with a simple search query
2. Shows raw API response
3. Tests connection and authentication

Usage:
    $env:X_BEARER_TOKEN="YOUR_TOKEN" 
    python ml/scripts/test_x_api_simple.py
"""
import asyncio
import httpx
import json

async def test_x_api_simple():
    """Test X API connection."""
    
    # Token from environment
    import os
    bearer_token = os.getenv("X_BEARER_TOKEN")
    
    if not bearer_token:
        print("❌ X_BEARER_TOKEN not set in environment")
        return
    
    print("=" * 80)
    print("X API SIMPLE TEST")
    print("=" * 80)
    print()
    print(f"✓ Bearer Token: {bearer_token[:50]}...")
    print()
    
    api_url = "https://api.twitter.com/v2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {bearer_token}"}
    
    # Try a simple search query
    queries = [
        "MMDA traffic",
        "MMDA",
        "Manila traffic",
        "traffic",
    ]
    
    async with httpx.AsyncClient(timeout=30) as client:
        for query in queries:
            print(f"Testing query: '{query}'")
            print("-" * 80)
            
            params = {
                "query": query,
                "max_results": 10,
                "tweet.fields": "created_at",
            }
            
            try:
                response = await client.get(api_url, headers=headers, params=params)
                
                print(f"Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    tweets = data.get("data", [])
                    print(f"✓ Found {len(tweets)} tweets")
                    
                    if tweets:
                        print()
                        print("Sample tweets:")
                        for i, tweet in enumerate(tweets[:3], 1):
                            print(f"  {i}. {tweet.get('text', '')[:80]}...")
                    else:
                        print("(No tweets found - this is normal if query is too specific)")
                else:
                    print(f"❌ Error: {response.status_code}")
                    print(f"Response: {response.text[:200]}")
                    
            except Exception as e:
                print(f"❌ Exception: {e}")
            
            print()

if __name__ == "__main__":
    asyncio.run(test_x_api_simple())
