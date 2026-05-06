import asyncio
import sys

import httpx

sys.path.append("C:/Users/Japoy/OneDrive/Documents/Desktop/Github/Event-Aware-Traffic-Forecasting/backend")

from app.core.config import get_settings
from app.ingestion.adapters import NewsAPIAdapter, OpenWeatherAdapter, WeatherStackAdapter


def main() -> None:
    settings = get_settings()

    async def run() -> None:
        async with httpx.AsyncClient(timeout=20.0) as client:
            news = NewsAPIAdapter(
                settings.news_api_url,
                settings.news_api_key or None,
                settings.news_api_query,
            )
            openweather = OpenWeatherAdapter(
                settings.openweather_url,
                settings.openweather_api_key or None,
                settings.openweather_lat,
                settings.openweather_lon,
            )
            weatherstack = WeatherStackAdapter(
                settings.weatherstack_url,
                settings.weatherstack_api_key or None,
                settings.openweather_lat,
                settings.openweather_lon,
            )

            news_items = await news.fetch(client, 3)
            openweather_items = await openweather.fetch(client, 1)
            weatherstack_items = await weatherstack.fetch(client, 1)

            print(f"NewsAPI items: {len(news_items)}")
            print(f"OpenWeather items: {len(openweather_items)}")
            print(f"Weatherstack items: {len(weatherstack_items)}")

            if news_items:
                print("NewsAPI sample:", news_items[0].text[:180])
            if openweather_items:
                print("OpenWeather sample:", openweather_items[0].text)
            if weatherstack_items:
                print("Weatherstack sample:", weatherstack_items[0].text)

    asyncio.run(run())


if __name__ == "__main__":
    main()
