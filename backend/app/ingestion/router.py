from celery.result import AsyncResult
from fastapi import APIRouter, Query

from app.ingestion.service import IngestionService
from app.schemas.ingestion import (
    IngestionPipelineRequest,
    IngestionTaskResponse,
    IngestionTaskStatusResponse,
    CSVIngestionRequest,
    CSVIngestionResponse,
    CleanedTextItem,
    RawTextItem,
    SpatialGraphBuildRequest,
    SpatialGraphBuildResponse,
    UnstructuredCollectionResponse,
)
from app.workers.celery_app import celery_app
from app.workers.tasks import (
    build_spatial_graph_task,
    collect_structured_traffic_task,
    collect_unstructured_task,
    run_pipeline_task,
)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])
service = IngestionService()


@router.post("/preprocess", response_model=list[CleanedTextItem])
async def preprocess_texts(items: list[RawTextItem]) -> list[CleanedTextItem]:
    return await service.preprocess_texts(items)


@router.get("/collect/unstructured", response_model=UnstructuredCollectionResponse)
async def collect_unstructured(limit_per_source: int = Query(10, ge=1, le=100)) -> UnstructuredCollectionResponse:
    return await service.collect_unstructured(limit_per_source)


@router.post("/collect/traffic", response_model=CSVIngestionResponse)
async def collect_structured_traffic(request: CSVIngestionRequest) -> CSVIngestionResponse:
    return await service.collect_structured_traffic(request.file_path)


@router.post("/spatial/build", response_model=SpatialGraphBuildResponse)
async def build_spatial_graph(request: SpatialGraphBuildRequest) -> SpatialGraphBuildResponse:
    return await service.build_spatial_graph(request)


@router.post("/collect/unstructured/async", response_model=IngestionTaskResponse)
async def collect_unstructured_async(
    limit_per_source: int = Query(10, ge=1, le=100),
) -> IngestionTaskResponse:
    task = collect_unstructured_task.delay(limit_per_source=limit_per_source)
    return IngestionTaskResponse(task_id=task.id, task_name="ingestion.collect_unstructured", status="queued")


@router.post("/collect/traffic/async", response_model=IngestionTaskResponse)
async def collect_structured_traffic_async(request: CSVIngestionRequest) -> IngestionTaskResponse:
    task = collect_structured_traffic_task.delay(file_path=request.file_path)
    return IngestionTaskResponse(task_id=task.id, task_name="ingestion.collect_structured_traffic", status="queued")


@router.post("/spatial/build/async", response_model=IngestionTaskResponse)
async def build_spatial_graph_async(request: SpatialGraphBuildRequest) -> IngestionTaskResponse:
    task = build_spatial_graph_task.delay(place_name=request.place_name, output_path=request.output_path)
    return IngestionTaskResponse(task_id=task.id, task_name="ingestion.build_spatial_graph", status="queued")


@router.post("/pipeline/async", response_model=IngestionTaskResponse)
async def run_ingestion_pipeline_async(request: IngestionPipelineRequest) -> IngestionTaskResponse:
    task = run_pipeline_task.delay(
        limit_per_source=request.limit_per_source,
        traffic_csv_path=request.traffic_csv_path,
        place_name=request.place_name,
        output_path=request.output_path,
    )
    return IngestionTaskResponse(task_id=task.id, task_name="ingestion.run_pipeline", status="queued")


@router.get("/tasks/{task_id}", response_model=IngestionTaskStatusResponse)
async def get_ingestion_task_status(task_id: str) -> IngestionTaskStatusResponse:
    task = AsyncResult(task_id, app=celery_app)
    if task.failed():
        return IngestionTaskStatusResponse(task_id=task_id, status=task.status, result=None, error=str(task.result))

    result_payload = task.result if isinstance(task.result, dict) else None
    return IngestionTaskStatusResponse(task_id=task_id, status=task.status, result=result_payload, error=None)
