from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Event-Aware Traffic Forecasting API"
    api_prefix: str = "/api"

    database_url: str = "postgresql+asyncpg://user:password@localhost:5433/traffic_db"
    redis_url: str = "redis://localhost:6380/0"

    celery_broker_url: str = "redis://localhost:6380/1"
    celery_result_backend: str = "redis://localhost:6380/2"

    source_timeout_seconds: float = 20.0
    source_max_items_per_source: int = 10
    source_user_agent: str = "EventAwareTrafficBot/1.0"

    rappler_feed_url: str = "https://www.rappler.com/rss/"
    rappler_api_key: str = ""
    inquirer_feed_url: str = "https://newsinfo.inquirer.net/feed"
    inquirer_api_key: str = ""
    gma_feed_url: str = "https://www.gmanetwork.com/news/rss/news/nation/feed.xml"
    gma_api_key: str = ""
    mmda_feed_url: str = "https://mmda.gov.ph/feed"
    mmda_twitter_api_url: str = "https://api.twitter.com/2/users/{user_id}/tweets"
    mmda_twitter_user_id: str = ""
    mmda_twitter_bearer_token: str = ""
    x_search_api_url: str = "https://api.twitter.com/v2/tweets/search/recent"
    x_bearer_token: str = ""
    x_search_query: str = "((from:DOTrPH OR from:DPWHph OR from:PNP_HPG OR from:PIOCaloocan OR from:CaloocanCityLGU OR from:Malabon_City OR from:Navotas_City OR from:valenzuelacity OR from:QCGov OR from:sanjuancityncr OR from:officialmunti OR from:ILoveParanaque OR from:PasayPIO OR #MMDAtraffic OR #MMDAAlert OR #TrafficAdvisory) lang:en -is:retweet)"
    pagasa_feed_url: str = "https://bagong.pagasa.dost.gov.ph/rss"
    pagasa_api_key: str = ""
    gdelt_api_url: str = "https://api.gdeltproject.org/api/v2/doc/doc"
    gdelt_api_key: str = ""
    google_cloud_project: str = ""

    news_api_url: str = "https://newsapi.org/v2/everything"
    news_api_key: str = Field(default="", validation_alias=AliasChoices("NEWS_API_KEY", "NEWS_API"))
    news_api_query: str = "(\"Metro Manila\" OR Manila OR NCR OR EDSA OR \"Quezon City\" OR Makati OR Pasig OR Taguig OR Caloocan OR Valenzuela OR Navotas OR Malabon OR Muntinlupa OR Parañaque OR Pasay OR San Juan) AND (traffic OR accident OR collision OR crash OR flood OR \"road closure\" OR roadwork OR construction OR reroute OR congestion OR advisory OR rally OR protest OR concert OR sale OR political OR holiday)"

    openweather_api_key: str = ""
    openweather_lat: float = 14.5995
    openweather_lon: float = 120.9842
    openweather_url: str = "https://api.openweathermap.org/data/2.5/weather"
    weatherstack_api_key: str = ""
    weatherstack_url: str = "http://api.weatherstack.com/current"

    distilbert_model_name: str = "distilbert-base-uncased-finetuned-sst-2-english"
    roberta_model_name: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    distilbert_model_path: str | None = None
    roberta_model_path: str | None = None
    strict_nlp_mode: bool = False
    model_artifact_dir: str = "artifacts/model_registry"
    model_registry_version: str = "v0"
    nlp_evaluation_dataset_path: str = "data/nlp_evaluation.csv"

    distilbert_threshold: float = 0.80
    roberta_threshold: float = 0.70


@lru_cache
def get_settings() -> Settings:
    return Settings()
