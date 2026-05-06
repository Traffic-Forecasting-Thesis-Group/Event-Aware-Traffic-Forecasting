import re
import asyncio
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

from app.core.config import get_settings
from app.ingestion.adapters import (
    GDELTBigQueryAdapter,
    GDELTAdapter,
    MMDAAdapter,
    NewsAPIAdapter,
    OpenWeatherAdapter,
    RSSSourceAdapter,
    SourceAdapter,
    WeatherStackAdapter,
    XSearchAdapter,
)
from app.ingestion.interfaces import DataIngestor
from app.preprocessing.taglish_translator import TaglishTranslator
from app.schemas.ingestion import (
    CSVIngestionResponse,
    CleanedTextItem,
    RawTextItem,
    SpatialGraphBuildRequest,
    SpatialGraphBuildResponse,
    StructuredTrafficRecord,
    UnstructuredCollectionResponse,
)

logger = logging.getLogger(__name__)


class IngestionService(DataIngestor):
    """Foundational ingestion service with text pre-cleaning and Taglish→English translation."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.adapters = self._build_adapters()
        
        # Initialize Taglish translator for auto-translation before NLP classification
        try:
            self.translator = TaglishTranslator()
            logger.info("TaglishTranslator initialized for ingestion pipeline")
        except Exception as e:
            logger.warning(f"Failed to initialize TaglishTranslator: {e}. Translation will be skipped.")
            self.translator = None

    async def collect_unstructured(self, limit_per_source: int | None = None) -> UnstructuredCollectionResponse:
        limit = limit_per_source or self.settings.source_max_items_per_source

        async with httpx.AsyncClient(
            timeout=self.settings.source_timeout_seconds,
            headers={"User-Agent": self.settings.source_user_agent},
        ) as client:
            gathered = await self._gather_sources(client, limit)

        by_source = Counter(item.source for item in gathered)
        return UnstructuredCollectionResponse(total_items=len(gathered), by_source=dict(by_source), items=gathered)

    async def preprocess_texts(self, items: list[RawTextItem]) -> list[CleanedTextItem]:
        """Clean and translate raw texts to English.
        
        Pipeline:
        1. Clean: remove URLs, mentions, whitespace
        2. Translate: convert Taglish to English using MarianMT + gazetteer masking
        3. Return: cleaned + translated text for downstream NLP classification
        """
        cleaned_items = []
        
        for item in items:
            cleaned = self._clean_text(item.text)
            
            # Translate using TaglishTranslator if available
            translated = None
            if self.translator:
                try:
                    translated = self.translator.translate_texts([cleaned], use_ner=True)[0]
                except Exception as e:
                    logger.warning(f"Translation failed for text from {item.source}: {e}. Skipping translation.")
            
            cleaned_items.append(
                CleanedTextItem(
                    source=item.source,
                    original_text=item.text,
                    cleaned_text=cleaned,
                    translated_text=translated,  # English translation (or None if failed)
                    location_hint=item.location_hint,
                    language_hint="taglish",
                    timestamp=item.timestamp,
                )
            )
        
        return cleaned_items

    async def collect_structured_traffic(self, file_path: str) -> CSVIngestionResponse:
        frame = pd.read_csv(file_path)
        required_columns = {"Timestamp", "Node", "Speed", "Flow"}
        missing = required_columns.difference(frame.columns)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        frame = frame[["Timestamp", "Node", "Speed", "Flow"]].copy()
        frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], errors="coerce", utc=True)
        frame["Speed"] = pd.to_numeric(frame["Speed"], errors="coerce")
        frame["Flow"] = pd.to_numeric(frame["Flow"], errors="coerce")

        invalid_mask = frame[["Timestamp", "Node", "Speed", "Flow"]].isnull().any(axis=1)
        invalid_rows = int(invalid_mask.sum())
        cleaned = frame[~invalid_mask].copy()

        before_dedupe = len(cleaned)
        cleaned.drop_duplicates(subset=["Timestamp", "Node"], keep="last", inplace=True)
        deduplicated = before_dedupe - len(cleaned)

        preview_records = [
            StructuredTrafficRecord(
                timestamp=row.Timestamp.to_pydatetime(),
                node=str(row.Node),
                speed=float(row.Speed),
                flow=float(row.Flow),
            )
            for row in cleaned.head(25).itertuples(index=False)
        ]

        return CSVIngestionResponse(
            loaded=len(cleaned),
            deduplicated=deduplicated,
            invalid_rows=invalid_rows,
            preview=preview_records,
        )

    async def build_spatial_graph(self, request: SpatialGraphBuildRequest) -> SpatialGraphBuildResponse:
        try:
            import networkx as nx
            import osmnx as ox

            graph = ox.graph_from_place(request.place_name, network_type="drive")
            output = Path(request.output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            nx.write_graphml(graph, output)

            return SpatialGraphBuildResponse(
                status="built",
                artifact=str(output),
                nodes=int(graph.number_of_nodes()),
                edges=int(graph.number_of_edges()),
                updated_at=datetime.now(timezone.utc),
            )
        except Exception:
            return SpatialGraphBuildResponse(
                status="pending",
                artifact=request.output_path,
                nodes=0,
                edges=0,
                updated_at=datetime.now(timezone.utc),
            )

    async def run_end_to_end_pipeline(
        self,
        limit_per_source: int | None = None,
        traffic_csv_path: str | None = None,
        spatial_request: SpatialGraphBuildRequest | None = None,
    ) -> dict[str, object]:
        unstructured = await self.collect_unstructured(limit_per_source=limit_per_source)
        cleaned = await self.preprocess_texts(unstructured.items)

        traffic_result: CSVIngestionResponse | None = None
        if traffic_csv_path:
            traffic_result = await self.collect_structured_traffic(traffic_csv_path)

        graph_result: SpatialGraphBuildResponse | None = None
        if spatial_request:
            graph_result = await self.build_spatial_graph(spatial_request)

        return {
            "unstructured_total": unstructured.total_items,
            "preprocessed_total": len(cleaned),
            "sources": unstructured.by_source,
            "traffic": traffic_result.model_dump() if traffic_result else None,
            "spatial": graph_result.model_dump() if graph_result else None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _clean_text(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"https?://\\S+", "", text)
        text = re.sub(r"[@#][\\w_]+", "", text)
        text = re.sub(r"\\s+", " ", text)
        return text.strip()

    async def _gather_sources(self, client: httpx.AsyncClient, limit: int) -> list[RawTextItem]:
        source_jobs = [adapter.fetch(client, limit) for adapter in self.adapters]

        results = await asyncio.gather(*source_jobs, return_exceptions=True)

        merged: list[RawTextItem] = []
        for result in results:
            if isinstance(result, Exception):
                continue
            merged.extend(result)
        return merged

    def _build_adapters(self) -> list[SourceAdapter]:
        rappler_auth = f"Bearer {self.settings.rappler_api_key}" if self.settings.rappler_api_key else None
        inquirer_auth = f"Bearer {self.settings.inquirer_api_key}" if self.settings.inquirer_api_key else None
        gma_auth = f"Bearer {self.settings.gma_api_key}" if self.settings.gma_api_key else None
        pagasa_auth = f"Bearer {self.settings.pagasa_api_key}" if self.settings.pagasa_api_key else None

        adapters = [
            RSSSourceAdapter("rappler", self.settings.rappler_feed_url, rappler_auth),
            RSSSourceAdapter("inquirer", self.settings.inquirer_feed_url, inquirer_auth),
            RSSSourceAdapter("gma_news", self.settings.gma_feed_url, gma_auth),
            NewsAPIAdapter(self.settings.news_api_url, self.settings.news_api_key or None, self.settings.news_api_query),
            MMDAAdapter(
                feed_url=self.settings.mmda_feed_url,
                twitter_api_url=self.settings.mmda_twitter_api_url,
                bearer_token=self.settings.mmda_twitter_bearer_token or None,
                twitter_user_id=self.settings.mmda_twitter_user_id or None,
            ),
            RSSSourceAdapter("pagasa", self.settings.pagasa_feed_url, pagasa_auth),
            OpenWeatherAdapter(
                self.settings.openweather_url,
                self.settings.openweather_api_key or None,
                self.settings.openweather_lat,
                self.settings.openweather_lon,
            ),
            WeatherStackAdapter(
                self.settings.weatherstack_url,
                self.settings.weatherstack_api_key or None,
                self.settings.openweather_lat,
                self.settings.openweather_lon,
            ),
            GDELTAdapter(self.settings.gdelt_api_url, self.settings.gdelt_api_key or None),
            XSearchAdapter(
                api_url=self.settings.x_search_api_url,
                bearer_token=self.settings.x_bearer_token or None,
                query=self.settings.x_search_query,
            ),
        ]

        if self.settings.google_cloud_project:
            adapters.append(GDELTBigQueryAdapter(project_id=self.settings.google_cloud_project))

        return adapters
