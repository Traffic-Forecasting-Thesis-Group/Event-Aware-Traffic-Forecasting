import asyncio

from app.ingestion.service import IngestionService
from app.schemas.ingestion import SpatialGraphBuildRequest
from app.workers.celery_app import celery_app


def _runner(coro):
    return asyncio.run(coro)


@celery_app.task(name="ingestion.collect_unstructured")
def collect_unstructured_task(limit_per_source: int | None = None) -> dict[str, object]:
    service = IngestionService()
    result = _runner(service.collect_unstructured(limit_per_source=limit_per_source))
    return result.model_dump(mode="json")


@celery_app.task(name="ingestion.collect_structured_traffic")
def collect_structured_traffic_task(file_path: str) -> dict[str, object]:
    service = IngestionService()
    result = _runner(service.collect_structured_traffic(file_path=file_path))
    return result.model_dump(mode="json")


@celery_app.task(name="ingestion.build_spatial_graph")
def build_spatial_graph_task(place_name: str, output_path: str) -> dict[str, object]:
    service = IngestionService()
    request = SpatialGraphBuildRequest(place_name=place_name, output_path=output_path)
    result = _runner(service.build_spatial_graph(request=request))
    return result.model_dump(mode="json")


@celery_app.task(name="ingestion.run_pipeline")
def run_pipeline_task(
    limit_per_source: int | None = None,
    traffic_csv_path: str | None = None,
    place_name: str | None = None,
    output_path: str | None = None,
) -> dict[str, object]:
    service = IngestionService()
    spatial_request = None
    if place_name or output_path:
        spatial_request = SpatialGraphBuildRequest(
            place_name=place_name or "Metro Manila, Philippines",
            output_path=output_path or "artifacts/metro_manila_graph.graphml",
        )
    return _runner(
        service.run_end_to_end_pipeline(
            limit_per_source=limit_per_source,
            traffic_csv_path=traffic_csv_path,
            spatial_request=spatial_request,
        )
    )
