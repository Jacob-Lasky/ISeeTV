import asyncio
import json
import logging
import os
from typing import Any, Literal

import httpx
import uvicorn
from fastapi import Body, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response, StreamingResponse
from pydantic import ValidationError
from sqlalchemy import inspect, text

from common.constants import DATA_PATH
from common.db import SessionLocal, engine, init_db
from common.job_queue import (
    cancel_job,
    enqueue_download_job,
    enqueue_ingest_job,
    get_job_status,
    get_queue_status,
    initialize_job_queue,
    shutdown_job_queue,
)
from common.log_utils import get_logger
from common.rules_storage import (
    load_assignments,
    load_rules,
    save_assignments,
    save_rules,
)
from common.state import cancel_task
from common.task_manager import DownloadTaskManager, IngestTaskManager, TaskManager
from common.utils import (
    create_task_id,
    format_download_progress_response,
    format_ingest_progress_response,
    format_table_response,
    get_all_progress_response,
    get_progress_response,
    validate_table_name,
)
from download.downloader import (
    background_single_download_task,
)
from ingest.epg_loader import load_epg_file_async
from ingest.m3u_loader import load_m3u_file_async
from models.models import (
    DownloadAllTasksResponse,
    DownloadProgress,
    DownloadTaskResponse,
    GlobalSettings,
    IngestProgress,
    Message,
    Source,
    TableResponse,
)
from models.stream_models import (
    StreamProgramsResponse,
    StreamsResponse,
)
from rules.ingestion_rules import (
    INGESTION_RULES_LOGS,
    IngestionRule,
    IngestionRulesEngine,
    SourceRuleAssignment,
    get_ingestion_rules_status,
)

# Import and unapply rules
from rules.post_load_rules import post_load_engine
from scheduler.scheduler_integration import (
    get_scheduler_manager,
    initialize_scheduler,
    start_scheduler,
    stop_scheduler,
)
from utils.file_generators import (
    apply_unified_channel_filtering,
    generate_epg_content,
    generate_m3u_content,
    get_filtered_channels_and_programs,
)
from utils.filter_utils import (
    get_all_filter_values,
    get_table_filter_statistics,
    get_table_filter_statistics_by_source,
    precompute_filter_values,
    precompute_all_filter_values,
)
from utils.stream_utils import (
    get_filter_view_counts,
    get_stream_programs_query,
    get_streams_filter_values,
    get_streams_query,
)

logger = get_logger(__name__)


class SuppressIngestProgressFilter(logging.Filter):
    def filter(self, record):
        return "/api/ingest/progress" not in record.getMessage()


class SuppressDownloadProgressFilter(logging.Filter):
    def filter(self, record):
        return "/api/download/progress" not in record.getMessage()


# Apply filter to Uvicorn's access logger
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.addFilter(SuppressIngestProgressFilter())
uvicorn_access_logger.addFilter(SuppressDownloadProgressFilter())

app = FastAPI(
    title="ISeeTV API",
    description="An IPTV Pipeline Platform",
    version="0.1.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_tags=[
        {"name": "Health", "description": "Health checks"},
        {"name": "Streams", "description": "Browse and filter merged channel streams"},
        {"name": "Rules", "description": "Ingestion rules management and filtering"},
        {"name": "Database", "description": "Manage the database"},
        {"name": "Sources", "description": "Manage IPTV sources (M3U, EPG, metadata)"},
        {"name": "Download", "description": "Download the M3U and EPG files"},
        {
            "name": "Ingest",
            "description": "Parse the downloaded files and load into the database",
        },
        {"name": "Settings", "description": "Global app configuration"},
        {"name": "Scheduler", "description": "Refresh scheduling operations"},
        {"name": "Redirect", "description": "Redirect operations"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


init_db()

# Initialize scheduler
sources_file = os.path.join(DATA_PATH, "sources.json")
initialize_scheduler(sources_file)


@app.get(
    "/",
    response_model=Message,
    tags=["Redirect"],
    status_code=status.HTTP_308_PERMANENT_REDIRECT,
)
async def root() -> RedirectResponse:
    """Redirect to the Swagger docs"""
    logger.info("Redirecting to Swagger docs")
    return RedirectResponse(url="/api/docs")


@app.get(
    "/docs",
    response_model=Message,
    tags=["Redirect"],
    status_code=status.HTTP_308_PERMANENT_REDIRECT,
)
async def docs() -> RedirectResponse:
    """Redirect to the Swagger docs"""
    logger.info("Redirecting to Swagger docs")
    return RedirectResponse(url="/api/docs")


@app.get(
    "/api",
    response_model=Message,
    tags=["Redirect"],
    status_code=status.HTTP_308_PERMANENT_REDIRECT,
)
async def api() -> RedirectResponse:
    """Redirect to the Swagger docs"""
    logger.info("Redirecting to Swagger docs")
    return RedirectResponse(url="/api/docs")


@app.get(
    "/api/health",
    response_model=Message,
    tags=["Health"],
    status_code=status.HTTP_200_OK,
)
async def get_health() -> Message:
    """Return a health check."""
    logger.info("Health check")
    return Message(message="ok")


@app.get(
    "/api/settings",
    response_model=GlobalSettings,
    tags=["Settings"],
    status_code=status.HTTP_200_OK,
)
async def get_settings(
    settings_file: str = os.path.join(DATA_PATH, "settings.json"),
) -> GlobalSettings:
    """Return settings from the provided file"""
    logger.debug("Getting settings")
    try:
        with open(settings_file) as f:
            return GlobalSettings(**json.load(f))
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.post(
    "/api/settings",
    response_model=Message,
    tags=["Settings"],
    status_code=status.HTTP_201_CREATED,
)
async def set_settings(
    settings: GlobalSettings,
    settings_file: str = os.path.join(DATA_PATH, "settings.json"),
):
    """Set settings in the provided file"""
    logger.info("Setting settings")
    try:
        with open(settings_file, "w") as f:
            json.dump(settings.dict(), f, indent=4)
        return Message(message="Settings saved successfully")
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get(
    "/api/sources",
    response_model=list[Source],
    tags=["Sources"],
    status_code=status.HTTP_200_OK,
)
async def get_sources(
    sources_file: str = os.path.join(DATA_PATH, "sources.json"),
) -> list[Source]:
    """Return sources from the provided file"""
    logger.debug("Getting sources")
    try:
        with open(sources_file) as f:
            return [Source(**source) for source in json.load(f)]
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.post(
    "/api/sources",
    response_model=Message,
    tags=["Sources"],
    status_code=status.HTTP_201_CREATED,
)
async def set_sources(
    sources: list[Source], sources_file: str = os.path.join(DATA_PATH, "sources.json")
) -> Message:
    """Set sources in the provided file"""
    logger.debug("Setting sources")
    try:
        with open(sources_file, "w") as f:
            json.dump([source.dict() for source in sources], f, indent=4)
        return Message(message="Sources saved successfully")
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get(
    "/api/ingest/progress/{task_id}",
    response_model=IngestProgress,
    tags=["Ingest"],
    status_code=status.HTTP_200_OK,
)
async def get_ingest_progress_by_id(task_id: str) -> IngestProgress:
    """Get ingest progress for a specific task"""
    logger.info("Getting ingest progress for: %s", task_id)
    return IngestProgress(**get_progress_response(task_id, "ingest"))


@app.get(
    "/api/ingest/progress",
    response_model=dict[str, dict],
    tags=["Ingest"],
    status_code=status.HTTP_200_OK,
)
async def get_ingest_progress() -> dict[str, dict]:
    """Get all ingest progress"""
    logger.debug("Getting ingest progress")
    progress_data = get_all_progress_response("ingest")
    return format_ingest_progress_response(progress_data)


@app.get(
    "/api/download/progress/{task_id}",
    response_model=DownloadProgress,
    tags=["Download"],
    status_code=status.HTTP_200_OK,
)
async def get_download_progress_by_id(task_id: str) -> DownloadProgress:
    """Get download progress for a specific task"""
    logger.debug("Getting download progress for: %s", task_id)
    return DownloadProgress(**get_progress_response(task_id, "download"))


@app.get(
    "/api/download/progress",
    response_model=dict[str, DownloadProgress],
    tags=["Download"],
    status_code=status.HTTP_200_OK,
)
async def get_all_download_progress() -> dict[str, DownloadProgress]:
    """Get all download progress tasks"""
    logger.debug("Getting all download progress")
    progress_data = get_all_progress_response("download")
    return format_download_progress_response(progress_data)


@app.delete(
    "/api/download/cancel/{task_id}",
    response_model=Message,
    tags=["Download"],
    status_code=status.HTTP_200_OK,
)
async def cancel_download(task_id: str) -> Message:
    """Cancel a download task by task ID"""
    logger.info("Canceling download task %s", task_id)
    try:
        success = cancel_task(task_id, "download")
        if success:
            return Message(message=f"Download task {task_id} cancelled successfully")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found or already completed",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get(
    "/api/download/{file_type}/all",
    response_model=DownloadAllTasksResponse,
    tags=["Download"],
    status_code=status.HTTP_200_OK,
)
async def download_all_files(
    file_type: Literal["m3u", "epg"],
    sources_file: str = os.path.join(DATA_PATH, "sources.json"),
    download_dir: str = os.path.join(DATA_PATH, "sources"),
) -> DownloadAllTasksResponse:
    """Start background download of all files of a specific type - one task per source"""
    logger.info("Downloading all %s files", file_type)
    try:
        with open(sources_file) as f:
            sources = [Source(**source) for source in json.load(f)]

        # Filter sources with file_type URLs in file_metadata
        file_type_sources = [
            source
            for source in sources
            if (file_type_meta := source.get_file_metadata(file_type))
            and file_type_meta.url
        ]

        if not file_type_sources:
            return DownloadAllTasksResponse(
                message=f"No sources with {file_type} URLs found", task_ids=[]
            )

        # Create task IDs and queue downloads through job queue
        task_ids = []
        job_ids = []
        for source in file_type_sources:
            # Create unique task ID for each source
            task_id = create_task_id(source.name, file_type, "download")
            task_ids.append(task_id)

            # Create download task (1 item per task)
            DownloadTaskManager.create_download_task(task_id, 1, file_type)

            # Enqueue download job through the global job queue
            job_id = await enqueue_download_job(
                source_name=source.name,
                file_type=file_type,
                job_function=background_single_download_task,
                task_id=task_id,
                download_type=file_type,
                sources_file=sources_file,
                download_dir=download_dir,
            )
            job_ids.append(job_id)

        return DownloadAllTasksResponse(
            message=f"{file_type} downloads queued for {len(file_type_sources)} sources (jobs: {', '.join(job_ids[:3])}{'...' if len(job_ids) > 3 else ''})",
            task_ids=task_ids,
        )
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get(
    "/api/download/{file_type}/{source_name}",
    response_model=DownloadTaskResponse,
    tags=["Download"],
    status_code=status.HTTP_200_OK,
)
async def queue_file_for_download(
    file_type: Literal["m3u", "epg"],
    source_name: str,
    sources_file: str = os.path.join(DATA_PATH, "sources.json"),
    download_dir: str = os.path.join(DATA_PATH, "sources"),
) -> DownloadTaskResponse:
    """Queue file download for a specific source through the job queue"""
    logger.info("Queuing %s file download for source %s", file_type, source_name)
    try:
        # Create unique task ID for each source
        task_id = create_task_id(source_name, file_type, "download")

        # Create download task (1 item per task)
        DownloadTaskManager.create_download_task(task_id, 1, file_type)

        # Enqueue download job through the global job queue
        job_id = await enqueue_download_job(
            source_name=source_name,
            file_type=file_type,
            job_function=background_single_download_task,
            task_id=task_id,
            download_type=file_type,
            sources_file=sources_file,
            download_dir=download_dir,
        )

        return DownloadTaskResponse(
            message=f"{file_type} file for {source_name} download queued (job: {job_id})",
            task_id=task_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get(
    "/api/download/file/{source_name}/{file_type}",
    tags=["Download"],
    status_code=status.HTTP_200_OK,
)
async def download_file_stream(
    source_name: str,
    file_type: str,
    sources_file: str = os.path.join(DATA_PATH, "sources.json"),
) -> StreamingResponse:
    """Stream a file directly to the browser for download"""
    logger.info("Downloading %s file for source %s", file_type, source_name)
    try:
        # Validate file type
        if file_type not in ["m3u", "epg"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Must be 'm3u' or 'epg'",
            )

        # Load sources to get the file URL
        with open(sources_file) as f:
            sources_data = json.load(f)

        # Find the source
        source_data = None
        for source in sources_data:
            if source["name"] == source_name:
                source_data = source
                break

        if not source_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source '{source_name}' not found",
            )

        # Get file metadata
        file_metadata = source_data.get("file_metadata", {})
        file_info = file_metadata.get(file_type)

        if not file_info or not file_info.get("url"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No {file_type.upper()} URL found for source '{source_name}'",
            )

        file_url = file_info["url"]
        filename = f"{source_name}_{file_type}.{file_type}"

        # Create the streaming generator function
        async def stream_file():
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    async with client.stream("GET", file_url) as response:
                        if response.status_code != 200:
                            raise HTTPException(
                                status_code=response.status_code,
                                detail=f"Failed to fetch file from {file_url}: {response.text}",
                            )

                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            yield chunk
                except httpx.RequestError as e:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Network error while fetching file: {e!s}",
                    )
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Error streaming file: {e!s}",
                    )

        # Return streaming response with appropriate headers
        return StreamingResponse(
            stream_file(),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Cache-Control": "no-cache",
            },
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sources file not found"
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid sources file format",
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in download_file_stream: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e!s}",
        )


@app.post(
    "/api/load/{file_type}/{source_name}",
    response_model=dict[str, str],
    tags=["Database"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def load_file_to_db(
    file_type: Literal["m3u", "epg"],
    source_name: str,
    sources_file: str = os.path.join(DATA_PATH, "sources.json"),
) -> dict[str, str]:
    """Start async database loading task for parsed file data"""
    logger.info("Loading %s file to database for %s", file_type, source_name)
    try:
        # Load sources configuration
        with open(sources_file) as f:
            sources = [Source(**source) for source in json.load(f)]

        # Find the source
        source = next(
            (source for source in sources if source.name == source_name), None
        )
        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source '{source_name}' not found",
            )

        # Get file metadata
        file_metadata = source.get_file_metadata(file_type)
        if not file_metadata or not file_metadata.local_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No {file_type.upper()} file defined for source '{source_name}'",
            )

        file_path = file_metadata.local_path

        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File '{file_path}' not found for source '{source_name}'",
            )

        # Create task ID and initialize task
        task_id = create_task_id(source_name, file_type, "ingest")

        # Extract total records for progress tracking
        total_records = 0
        if file_metadata.total_records:
            if file_type == "m3u":
                total_records = file_metadata.total_records.channels or 0
                total_steps = 3  # download, parse, load
            elif file_type == "epg":
                # For EPG, use channels + programs
                channels = file_metadata.total_records.channels or 0
                programs = file_metadata.total_records.programs or 0
                total_records = channels + programs
                total_steps = 5  # download, parse channels, load channels, parse programs, load programs

        IngestTaskManager.create_ingest_task(
            task_id, file_type, source_name, total_records, total_steps
        )

        # Enqueue ingest job through the global job queue
        job_id = await enqueue_ingest_job(
            source_name=source_name,
            file_type=file_type,
            job_function=background_load_task,
            task_id=task_id,
            file_path=file_path,
        )

        return {
            "task_id": task_id,
            "job_id": job_id,
            "message": f"Queued loading {file_type.upper()} file for {source_name} (job: {job_id})",
            "status": "queued",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting load task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


async def background_load_task(
    task_id: str, file_type: str, file_path: str, source_name: str
) -> None:
    """Background task to load file data into database with multi-step progress tracking"""
    logger.debug(
        "Started background load task %s for %s file: %s", task_id, file_type, file_path
    )
    session = SessionLocal()
    try:
        # Start the task (Step 1: Download already completed)
        TaskManager.start_task(task_id, "ingest", "ingesting")

        logger.debug(
            "Started background load task %s for %s file: %s",
            task_id,
            file_type,
            file_path,
        )

        # Load data using async generators with task tracking
        if file_type == "m3u":
            async for result in load_m3u_file_async(
                session, file_path, source_name, task_id
            ):
                if result.status == "error":
                    logger.warning(f"Load error in task {task_id}: {result.message}")
        elif file_type == "epg":
            async for result in load_epg_file_async(
                session, file_path, source_name, task_id
            ):
                if result.status == "error":
                    logger.warning(f"Load error in task {task_id}: {result.message}")

        precompute_all_filter_values(session)
        logger.info("Precomputed filter values for all tables after task %s", task_id)

        # Add a small delay to ensure frontend can display progress bars
        await asyncio.sleep(2)

        # Complete the task
        TaskManager.complete_task(
            task_id,
            "ingest",
            f"Successfully loaded records from {source_name} {file_type} file",
        )
        logger.info(
            "Completed background load task %s: filter values precomputed", task_id
        )

    except Exception:
        logger.exception("Background load task %s failed", task_id)
        TaskManager.fail_task(task_id, "ingest", str(e))
        session.rollback()
    finally:
        session.close()


@app.get(
    "/api/db/{table}/head",
    response_model=TableResponse,
    tags=["Database"],
    status_code=status.HTTP_200_OK,
)
async def get_db_table_head(table: str) -> dict[str, Any]:
    """Return the first 10 rows of a table"""
    logger.info("Fetching head of table %s", table)
    try:
        with SessionLocal() as session:
            result = session.execute(text(f"SELECT * FROM {table} LIMIT 10"))
            records = [dict(row._mapping) for row in result.fetchall()]
            return format_table_response(records, table)
    except Exception as e:
        logger.error("Error fetching head of table %s: %s", table, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch head of table: {e!s}",
        )


@app.get(
    "/api/tables/{table_name}",
    response_model=TableResponse,
    tags=["Database"],
    status_code=status.HTTP_200_OK,
)
async def get_table_data(
    table_name: str,
    source: str | None = None,
) -> dict[str, Any]:
    """Return paginated table data with optional source filtering"""
    logger.info("Fetching table data for %s", table_name)
    # Validate table name to prevent SQL injection
    validate_table_name(table_name, include_streams=False)

    try:
        with SessionLocal() as session:
            # Build base query
            base_query = f"SELECT * FROM {table_name}"

            # Add source filtering if provided
            params = {}
            if source:
                base_query += " WHERE source = :source"
                params["source"] = source

            # Add ordering and pagination
            base_query += " ORDER BY id ASC"

            data_result = session.execute(text(base_query), params)
            records = [dict(row._mapping) for row in data_result]

            return format_table_response(records, table_name, source)

    except Exception as e:
        logger.error("Error fetching table data for %s: %s", table_name, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch table data: {e!s}",
        )


@app.get(
    "/api/db/summary",
    response_model=dict[str, Any],
    tags=["Database"],
    status_code=status.HTTP_200_OK,
)
async def get_db_summary() -> dict[str, Any]:
    """Return a summary of the database"""
    logger.info("Fetching database summary")
    inspector = inspect(engine)
    summary = []

    with SessionLocal() as session:
        for table_name in inspector.get_table_names():
            # Get columns
            columns = [col["name"] for col in inspector.get_columns(table_name)]

            # Get row count
            row_count = session.execute(
                text(f"SELECT COUNT(*) FROM {table_name}")
            ).scalar()

            # Get a sample of the first 5 rows
            result = session.execute(text(f"SELECT * FROM {table_name} LIMIT 1"))
            rows = [dict(row._mapping) for row in result]

            # Get filter statistics if filter_reasons column exists
            filter_stats = {}
            if "filter_reasons" in columns:
                filter_stats = get_table_filter_statistics(session, table_name)

            summary.append(
                {
                    "table": table_name,
                    "columns": columns,
                    "primary_key": inspector.get_pk_constraint(table_name),
                    "indexes": inspector.get_indexes(table_name),
                    "row_count": row_count,
                    "filtered": filter_stats,
                    "sample_row": rows[0] if rows else "",
                }
            )

    return {"tables": summary}


@app.get(
    "/api/tables/{table_name}/filtered_counts/{source}",
    response_model=dict[str, Any],
    tags=["Database"],
    status_code=status.HTTP_200_OK,
)
async def get_table_filtered_counts(table_name: str, source: str) -> dict[str, Any]:
    """Get filter statistics for an entire table"""
    logger.info(
        "Fetching filter statistics for table %s in source %s", table_name, source
    )
    try:
        with SessionLocal() as session:
            filter_stats = get_table_filter_statistics_by_source(
                session, table_name, source
            )

            return {
                "success": True,
                "data": filter_stats,
            }

    except Exception as e:
        logger.error("Error getting filter statistics for table %s: %s", table_name, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get(
    "/api/tables/{table_name}/filtered_counts/{source}/{rule}",
    response_model=dict[str, Any],
    tags=["Database"],
    status_code=status.HTTP_200_OK,
)
async def get_table_filtered_counts_by_rule(
    table_name: str, source: str, rule: str
) -> dict[str, Any]:
    """Get filter statistics for a specific rule on a specific table and source"""
    logger.info(
        "Fetching filter statistics for table %s in source %s", table_name, source
    )
    try:
        with SessionLocal() as session:
            filter_stats = get_table_filter_statistics_by_source(
                session, table_name, source
            )

            # Extract the count for the specific assignment/rule
            # filter_stats structure: {"filter_stats": {"Blacklisted by rule 'alice_sports_content': matched pattern...": 9908, "Passed": 258901}, "passed": 258901, ...}
            filter_stats_dict = filter_stats.get("filter_stats", {})

            # Search for filter reasons that contain the assignment/rule ID
            # The assignment ID is embedded in descriptive text like "Blacklisted by rule 'alice_sports_content': matched pattern..."
            rule_count = None
            has_been_run = False

            for reason, count in filter_stats_dict.items():
                if reason != "Passed" and rule in reason:
                    rule_count = count
                    has_been_run = True
                    break

            # If no match found, check if there are any non-"Passed" entries (rule has been run but no matches)
            if not has_been_run and any(
                reason != "Passed" for reason in filter_stats_dict.keys()
            ):
                # Rule may have been run but produced no filtered results
                rule_count = 0
                has_been_run = True

            return {
                "success": True,
                "data": {
                    "rule_name": rule,
                    "filtered_count": rule_count,
                    "has_been_run": has_been_run,
                    "total": filter_stats.get("total", 0),
                    "passed": filter_stats.get("passed", 0),
                    "all_not_passed": filter_stats.get("all_not_passed", 0),
                },
            }

    except Exception as e:
        logger.error(
            "Error getting filter statistics for rule %s on table %s: %s",
            rule,
            table_name,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get(
    "/api/tables/{table_name}/filters",
    response_model=dict[str, Any],
    tags=["Database"],
    status_code=status.HTTP_200_OK,
)
async def get_table_filter_values(table_name: str) -> dict[str, Any]:
    """Get precomputed filter values for a table's filterable columns"""
    logger.info("Fetching filter values for table %s", table_name)
    # Validate table name to prevent SQL injection
    validate_table_name(table_name, include_streams=False)

    try:
        with SessionLocal() as session:
            filter_values = get_all_filter_values(session, table_name)

            return {
                "success": True,
                "data": filter_values,
                "table_name": table_name,
            }

    except Exception as e:
        logger.error("Error getting filter values for table %s: %s", table_name, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get(
    "/api/tables/{table_name}/columns",
    response_model=dict[str, Any],
    tags=["Database"],
    status_code=status.HTTP_200_OK,
)
async def get_table_columns(table_name: str) -> dict[str, Any]:
    """Get column names for a specific table"""
    logger.info("Fetching columns for table %s", table_name)
    # Validate table name to prevent SQL injection
    validate_table_name(table_name, include_streams=False)

    try:
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns(table_name)]

        return {
            "success": True,
            "data": columns,
            "table_name": table_name,
        }

    except Exception as e:
        logger.error("Error getting columns for table %s: %s", table_name, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get(
    "/api/tables/{table_name}/filter_counts_by_assignment/{source}",
    response_model=dict[str, Any],
    tags=["Database"],
    status_code=status.HTTP_200_OK,
)
async def get_table_filter_counts_by_assignment(
    table_name: str, source: str
) -> dict[str, Any]:
    """Get filter statistics organized by assignment for a specific table and source"""
    logger.info(
        "Fetching filter statistics organized by assignment for table %s in source %s",
        table_name,
        source,
    )
    try:
        with SessionLocal() as session:
            filter_stats = get_table_filter_statistics_by_source(
                session, table_name, source
            )

            # Get all assignments for this source
            ingestion_engine = IngestionRulesEngine()
            source_assignments = ingestion_engine.get_source_assignments(source)

            if not source_assignments:
                return {
                    "success": True,
                    "data": {
                        "assignments": {},
                        "total": filter_stats.get("total", 0),
                        "passed": filter_stats.get("passed", 0),
                        "all_not_passed": filter_stats.get("all_not_passed", 0),
                    },
                    "table_name": table_name,
                    "source": source,
                }

            # Extract filter statistics and organize by assignment
            filter_stats_dict = filter_stats.get("filter_stats", {})
            assignment_counts = {}

            for assignment in source_assignments:
                assignment_id = assignment.id
                assignment_name = assignment.assignment_name
                assigned_rules = assignment.assigned_rules

                # With new JSON array format, assignment IDs are returned directly as keys in filter statistics
                total_filtered_count = filter_stats_dict.get(assignment_id, 0)
                has_been_run = assignment_id in filter_stats_dict or any(
                    reason != "Passed" for reason in filter_stats_dict.keys()
                )
                matched_rules = assigned_rules.copy() if has_been_run else []

                assignment_counts[assignment_id] = {
                    "assignment_id": assignment_id,
                    "filtered_count": total_filtered_count,
                    "has_been_run": has_been_run,
                    "assigned_rules": assigned_rules,
                    "matched_rules": matched_rules,
                }

            return {
                "success": True,
                "data": {
                    "assignments": assignment_counts,
                    "total": filter_stats.get("total", 0),
                    "passed": filter_stats.get("passed", 0),
                    "all_not_passed": filter_stats.get("all_not_passed", 0),
                },
                "table_name": table_name,
                "source": source,
            }

    except Exception as e:
        logger.error(
            "Error getting filter counts by assignment for table %s, source %s: %s",
            table_name,
            source,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# Streams API Endpoints


@app.get(
    "/api/streams",
    response_model=StreamsResponse,
    tags=["Streams"],
    status_code=status.HTTP_200_OK,
)
async def get_streams(
    source: str | None = None,
    group: str | None = None,
    page: int = 1,
    page_size: int = 100,
    sort_field: str = "name",
    sort_order: str = "asc",
    global_filter: str | None = None,
    column_filters: str | None = None,
    apply_rules: bool = True,
    filter_view: str = "matched",
) -> StreamsResponse:
    """Get joined streams view with M3U channels, EPG data, and program counts.

    This endpoint provides a comprehensive view of all available streams by joining:
    - M3U channels (primary data with stream URLs)
    - EPG channels (display names and icons)
    - Programs (aggregated counts and next program info)

    Args:
        source: Filter by source name
        group: Filter by channel group
        page: Page number (1-based)
        page_size: Number of records per page (max 500)
        sort_field: Field to sort by (name, tvg_id, display_name, group, source, program_count)
        sort_order: Sort order (asc/desc)
        global_filter: Global search across name, tvg_id, display_name, group
        column_filters: JSON string of column-specific filters
        apply_rules: Whether to apply ingestion rules filtering (default: True)
        filter_view: Filter view mode ("matched", "unmatched", "all") for rules filtering

    Returns:
        StreamsResponse with paginated stream data and filter options

    """
    logger.info(
        "Getting streams: page=%s, size=%s, source=%s, group=%s",
        page,
        page_size,
        source,
        group,
    )

    try:
        # Validate page_size
        page_size = min(page_size, 500)
        if page_size < 1:
            page_size = 100

        # Parse column filters if provided
        parsed_column_filters = {}
        if column_filters:
            try:
                parsed_column_filters = json.loads(column_filters)
            except json.JSONDecodeError:
                logger.warning("Invalid column_filters JSON: %s", column_filters)

        with SessionLocal() as session:
            # Get streams data
            streams, total_count = get_streams_query(
                session=session,
                source=source,
                group=group,
                page=page,
                page_size=page_size,
                sort_field=sort_field,
                sort_order=sort_order,
                global_filter=global_filter,
                column_filters=parsed_column_filters,
                apply_rules=apply_rules,
                filter_view=filter_view,
            )

            # Get filter values
            filter_values = get_streams_filter_values(session)

            # Get filter view counts
            filter_view_counts = get_filter_view_counts(
                session=session,
                source=source,
                group=group,
                global_filter=global_filter,
                column_filters=parsed_column_filters,
            )

            # Calculate pagination metadata
            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_prev = page > 1

            return StreamsResponse(
                success=True,
                data=streams,
                total=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                has_next=has_next,
                has_prev=has_prev,
                filters=filter_values,
                filter_view_counts=filter_view_counts,
            )

    except Exception as e:
        logger.error("Error getting streams: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get streams: {e!s}",
        )


@app.get(
    "/api/streams/{source}/{channel_id}/programs",
    response_model=StreamProgramsResponse,
    tags=["Streams"],
    status_code=status.HTTP_200_OK,
)
async def get_stream_programs(
    source: str,
    channel_id: str,
    page: int = 1,
    page_size: int = 100,
    sort_field: str = "start_time",
    sort_order: str = "asc",
    global_filter: str | None = None,
    column_filters: str | None = None,
) -> StreamProgramsResponse:
    """Get programs for a specific stream channel with context.

    Args:
        source: Source name
        channel_id: Channel ID (tvg_id)
        page: Page number (1-based)
        page_size: Number of records per page (max 500)
        sort_field: Field to sort by (start_time, end_time, title)
        sort_order: Sort order (asc/desc)
        global_filter: Global search across title, description, channel names
        column_filters: JSON string of column-specific filters

    Returns:
        StreamProgramsResponse with paginated program data

    """
    logger.info(
        "Getting programs for stream: source=%s, channel_id=%s",
        source,
        channel_id,
    )

    try:
        # Validate page_size
        page_size = min(page_size, 500)
        if page_size < 1:
            page_size = 100

        # Parse column filters if provided
        parsed_column_filters = {}
        if column_filters:
            try:
                parsed_column_filters = json.loads(column_filters)
            except json.JSONDecodeError:
                logger.warning("Invalid column_filters JSON: %s", column_filters)

        with SessionLocal() as session:
            # Get program data
            programs, total_count = get_stream_programs_query(
                session=session,
                channel_id=channel_id,
                source=source,
                page=page,
                page_size=page_size,
                sort_field=sort_field,
                sort_order=sort_order,
                global_filter=global_filter,
                column_filters=parsed_column_filters,
            )

            # Calculate pagination metadata
            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_prev = page > 1

            return StreamProgramsResponse(
                success=True,
                data=programs,
                total=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                has_next=has_next,
                has_prev=has_prev,
                filters={},  # Programs don't need complex filtering for now
            )

    except Exception as e:
        logger.error("Error getting stream programs: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stream programs: {e!s}",
        )


@app.get(
    "/api/streams/filters",
    response_model=dict[str, Any],
    tags=["Streams"],
    status_code=status.HTTP_200_OK,
)
async def get_streams_filters() -> dict[str, Any]:
    """Get precomputed filter values for streams view.

    Returns:
        Dictionary with filter values for source and group columns

    """
    logger.info("Getting streams filter values")

    try:
        with SessionLocal() as session:
            filter_values = get_streams_filter_values(session)

            return {
                "success": True,
                "data": filter_values,
                "table_name": "streams",
            }

    except Exception as e:
        logger.error("Error getting streams filter values: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get streams filter values: {e!s}",
        )


@app.post(
    "/api/tables/{table_name}/precompute-filters",
    response_model=dict[str, str],
    tags=["Database"],
    status_code=status.HTTP_200_OK,
)
async def precompute_table_filters(table_name: str) -> dict[str, str]:
    """Precompute filter values for any table or view.

    This is typically called after data ingestion to update filter options.

    Args:
        table_name: Name of the table/view to precompute filters for

    Returns:
        Success message

    """
    logger.info("Precomputing filter values for table: %s", table_name)

    validate_table_name(table_name)

    try:
        with SessionLocal() as session:
            precompute_filter_values(session, table_name)

            return {
                "message": f"Successfully precomputed filter values for {table_name}",
                "table_name": table_name,
            }

    except Exception:
        logger.exception("Error precomputing filter values for %s", table_name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to precompute filter values for {table_name}",
        )


@app.post(
    "/api/tables/precompute-all-filters",
    response_model=dict[str, Any],
    tags=["Database"],
    status_code=status.HTTP_200_OK,
)
async def precompute_all_table_filters() -> dict[str, Any]:
    """Precompute filter values for all configured tables and views.

    This is a convenience endpoint that precomputes filters for all tables at once.
    Useful after bulk data ingestion.

    Returns:
        Success message with details of processed tables

    """
    logger.info("Precomputing filter values for all tables")

    try:
        with SessionLocal() as session:
            from utils.filter_utils import (
                precompute_all_filter_values,
                FILTERABLE_COLUMNS_CONFIG,
            )

            precompute_all_filter_values(session)

            return {
                "message": "Successfully precomputed filter values for all tables",
                "processed_tables": list(FILTERABLE_COLUMNS_CONFIG.keys()),
                "success": True,
            }

    except Exception:
        logger.exception("Error precomputing all filter values")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to precompute all filter values",
        )


# Scheduler API Endpoints


@app.get(
    "/api/scheduler/status",
    response_model=dict[str, Any],
    tags=["Scheduler"],
    status_code=status.HTTP_200_OK,
)
async def get_scheduler_status() -> dict[str, Any]:
    """Get current scheduler status and job information"""
    logger.info("Getting scheduler status")
    scheduler_manager = get_scheduler_manager()
    return scheduler_manager.get_scheduler_status()


@app.post(
    "/api/scheduler/start",
    response_model=dict[str, str],
    tags=["Scheduler"],
    status_code=status.HTTP_200_OK,
)
async def start_scheduler_endpoint() -> dict[str, str]:
    """Start the refresh scheduler"""
    logger.info("Starting scheduler via API")
    try:
        start_scheduler()
        return {"message": "Scheduler started successfully", "status": "running"}
    except Exception:
        logger.exception("Error starting scheduler")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start scheduler",
        )


@app.post(
    "/api/scheduler/stop",
    response_model=dict[str, str],
    tags=["Scheduler"],
    status_code=status.HTTP_200_OK,
)
async def stop_scheduler_endpoint() -> dict[str, str]:
    """Stop the refresh scheduler"""
    logger.info("Stopping scheduler via API")
    try:
        stop_scheduler()
        return {"message": "Scheduler stopped successfully", "status": "stopped"}
    except Exception:
        logger.exception("Error stopping scheduler")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop scheduler",
        )


@app.post(
    "/api/scheduler/restart",
    response_model=dict[str, str],
    tags=["Scheduler"],
    status_code=status.HTTP_200_OK,
)
async def restart_scheduler_endpoint() -> dict[str, str]:
    """Restart the refresh scheduler"""
    logger.info("Restarting scheduler via API")
    try:
        scheduler_manager = get_scheduler_manager()
        scheduler_manager.restart()
        return {"message": "Scheduler restarted successfully", "status": "running"}
    except Exception:
        logger.exception("Error restarting scheduler")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restart scheduler",
        )


@app.post(
    "/api/scheduler/update/{source_name}",
    response_model=dict[str, str],
    tags=["Scheduler"],
    status_code=status.HTTP_200_OK,
)
async def update_source_schedule(
    source_name: str,
    sources_file: str = os.path.join(DATA_PATH, "sources.json"),
) -> dict[str, str]:
    """Update schedule for a specific source"""
    logger.info("Updating schedule for source: %s", source_name)
    try:
        scheduler_manager = get_scheduler_manager()
        # Load sources configuration
        with open(sources_file) as f:
            sources = [Source(**source) for source in json.load(f)]

        # Find the source
        source = next(
            (source for source in sources if source.name == source_name), None
        )
        if source:
            logger.info("Updating sources")
            scheduler_manager.update_source_schedule(source)
        else:
            logger.info("Deleting source: %s", source_name)
            # source not found, remove existing jobs
            delete_source_schedule(source_name)

        return {
            "message": f"Schedule updated for source {source_name}",
            "source_name": source_name,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error updating schedule for %s", source_name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update schedule",
        )


@app.delete(
    "/api/scheduler/delete/{source_name}",
    response_model=dict[str, str],
    tags=["Scheduler"],
    status_code=status.HTTP_200_OK,
)
async def delete_source_schedule(source_name: str) -> dict[str, str]:
    """Delete/remove schedule for a specific source"""
    logger.info("Deleting schedule for source: %s", source_name)
    try:
        scheduler_manager = get_scheduler_manager()
        if scheduler_manager.scheduler:
            scheduler_manager.scheduler.remove_source_jobs(source_name)

        return {
            "message": f"Schedule deleted for source {source_name}",
            "source_name": source_name,
        }

    except Exception:
        logger.exception("Error deleting schedule for %s", source_name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete schedule",
        )


@app.get(
    "/api/scheduler/validate",
    response_model=dict[str, Any],
    tags=["Scheduler"],
    status_code=status.HTTP_200_OK,
)
async def validate_scheduler_config(
    sources_file: str = os.path.join(DATA_PATH, "sources.json"),
) -> dict[str, Any]:
    """Validate scheduler configuration for all sources"""
    logger.info("Validating scheduler configuration")
    try:
        # Load sources configuration
        with open(sources_file) as f:
            sources = [Source(**source) for source in json.load(f)]

        # Validate and get results
        scheduler_manager = get_scheduler_manager()
        results = scheduler_manager.validate_and_schedule_sources(sources)

        return {
            "success": True,
            "validation_results": results,
            "total_sources": len(sources),
            "enabled_sources": len([s for s in sources if s.enabled]),
        }

    except Exception:
        logger.exception("Error validating scheduler configuration")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate configuration",
        )


@app.get(
    "/api/rules/status",
    response_model=dict[str, Any],
    tags=["Rules"],
    status_code=status.HTTP_200_OK,
)
async def get_rules_status() -> dict[str, Any]:
    """Get current status of ingestion rules system"""
    logger.info("Getting ingestion rules status")
    try:
        status_info = get_ingestion_rules_status()
        return {"success": True, "data": status_info}
    except Exception:
        logger.exception("Error getting rules status")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get rules status",
        )


@app.get(
    "/api/rules",
    response_model=dict[str, Any],
    tags=["Rules"],
    status_code=status.HTTP_200_OK,
)
async def get_rules() -> dict[str, Any]:
    """Get all ingestion rules and source assignments"""
    logger.info("Getting ingestion rules and source assignments")
    try:
        rules = load_rules()
        assignments = load_assignments()

        return {
            "rules": rules,
            "source_assignments": assignments,
        }
    except Exception:
        logger.exception("Error getting rules")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get rules",
        )


@app.post(
    "/api/rules/save",
    response_model=dict[str, Any],
    tags=["Rules"],
    status_code=status.HTTP_200_OK,
)
async def save_rules_only(rules_data: list[dict[str, Any]]) -> dict[str, Any]:
    """Save only ingestion rules to rules.json file"""
    logger.info("Saving ingestion rules only")
    try:
        result = save_rules(rules_data)

        if not result["success"]:
            return result

        logger.info("Successfully saved rules")
        return result

    except Exception:
        logger.exception("Error saving rules")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save rules",
        )


@app.get(
    "/api/assignments",
    response_model=dict[str, Any],
    tags=["Rules"],
    status_code=status.HTTP_200_OK,
)
async def get_assignments() -> dict[str, Any]:
    """Get all source rule assignments"""
    logger.info("Getting source rule assignments")
    try:
        assignments = load_assignments()
        return {"success": True, "data": assignments}
    except Exception:
        logger.exception("Error getting assignments")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get assignments",
        )


@app.post(
    "/api/assignments/apply",
    response_model=dict[str, Any],
    tags=["Rules"],
    status_code=status.HTTP_200_OK,
)
async def apply_assignment(
    assignment_id: str = Body(..., description="ID of the assignment to apply"),
    table_name: str = Body(..., description="Name of the table to apply assignment to"),
) -> dict[str, Any]:
    """Apply a specific assignment by ID to a table (new multi-assignment architecture)"""
    logger.info("Applying assignment")
    try:
        logger.info(
            f"[apply_assignment]: Applying assignment '{assignment_id}' to {table_name}"
        )

        # Load all assignments to check if it exists
        _, assignments = post_load_engine.ingestion_engine.load_rules()
        assignment_exists = any(a.id == assignment_id for a in assignments)

        if not assignment_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assignment '{assignment_id}' not found",
            )

        # Now get the assignment (only enabled ones)
        assignment = post_load_engine.ingestion_engine.get_assignment_by_id(
            assignment_id
        )
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Assignment '{assignment_id}' is disabled and cannot be applied",
            )

        # Apply the assignment to the specified table
        result = post_load_engine.apply_assignment_to_table(
            assignment_id, table_name, assignment.source_name
        )

        logger.info(
            f"Assignment '{assignment_id}' application completed for {table_name} from {assignment.source_name}"
        )

        # Convert numpy types to Python types for JSON serialization
        serializable_result = {
            "processed": int(result.get("processed", 0)),
            "filtered": int(result.get("filtered", 0)),
            "passed": int(result.get("passed", 0)),
        }

        return {
            "success": True,
            "message": f"Assignment '{assignment_id}' applied to {table_name} for source {assignment.source_name}",
            "assignment_id": assignment_id,
            "table_name": table_name,
            "source_name": assignment.source_name,
            "results": serializable_result,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error applying assignment")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply assignment",
        )


@app.post(
    "/api/assignments/unapply",
    response_model=dict[str, Any],
    tags=["Rules"],
    status_code=status.HTTP_200_OK,
)
async def unapply_assignment(
    assignment_id: str = Body(..., description="ID of the assignment to unapply"),
    table_name: str = Body(
        None,
        description="Optional: specific table to unapply from. If not provided, unapplies from all relevant tables.",
    ),
) -> dict[str, Any]:
    """Unapply a specific assignment by ID from relevant tables (new multi-assignment architecture)"""
    logger.info("Unapplying assignment")
    try:
        logger.info(
            f"[unapply_assignment]: Unapplying assignment '{assignment_id}' from {table_name or 'all relevant tables'}"
        )

        # Load all assignments to find the one we want to unapply (including disabled)
        _, assignments = post_load_engine.ingestion_engine.load_rules()
        assignment = next((a for a in assignments if a.id == assignment_id), None)

        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assignment '{assignment_id}' not found",
            )

        # Get all rules for this assignment to determine relevant tables
        rules, _ = post_load_engine.ingestion_engine.load_rules()
        relevant_tables = set()

        for rule_name in assignment.assigned_rules:
            rule = next((r for r in rules if r.name == rule_name), None)
            if rule:
                relevant_tables.update(rule.tables)

        if not relevant_tables:
            logger.warning(f"No relevant tables found for assignment '{assignment_id}'")
            return {
                "success": True,
                "message": f"No relevant tables found for assignment '{assignment_id}'",
                "assignment_id": assignment_id,
                "source_name": assignment.source_name,
                "results": {"processed": 0, "restored": 0, "passed": 0},
            }

        # If specific table provided, validate it's relevant
        if table_name:
            if table_name not in relevant_tables:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Table '{table_name}' is not relevant to assignment '{assignment_id}'. Relevant tables: {list(relevant_tables)}",
                )
            tables_to_process = [table_name]
        else:
            tables_to_process = list(relevant_tables)

        logger.info(
            "Processing tables: %s for assignment '%s'",
            tables_to_process,
            assignment_id,
        )

        # Unapply the assignment from relevant tables
        total_results = {"processed": 0, "restored": 0, "passed": 0}
        table_results = {}

        for table in tables_to_process:
            result = post_load_engine.unapply_assignment_from_table(
                assignment_id, table, assignment.source_name
            )

            total_results["processed"] += result.get("processed", 0)
            total_results["restored"] += result.get("restored", 0)
            total_results["passed"] += result.get("passed", 0)
            table_results[table] = result

        logger.info(
            "Assignment '%s' unapplication completed for %d tables from %s",
            assignment_id,
            len(tables_to_process),
            assignment.source_name,
        )

        # Convert numpy types to Python types for JSON serialization
        serializable_result = {
            "processed": int(total_results["processed"]),
            "restored": int(total_results["restored"]),
            "passed": int(total_results["passed"]),
        }

        return {
            "success": True,
            "message": f"Assignment '{assignment_id}' unapplied from {len(tables_to_process)} relevant tables for source {assignment.source_name}",
            "assignment_id": assignment_id,
            "relevant_tables": list(relevant_tables),
            "processed_tables": tables_to_process,
            "source_name": assignment.source_name,
            "results": serializable_result,
            "table_results": table_results,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error unapplying assignment")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unapply assignment",
        )


@app.post(
    "/api/assignments/save",
    response_model=dict[str, Any],
    tags=["Rules"],
    status_code=status.HTTP_200_OK,
)
async def save_assignments_only(
    assignments_data: list[dict[str, Any]],
) -> dict[str, Any]:
    """Save only source rule assignments to assignments.json file"""
    logger.info("Saving source rule assignments only")
    try:
        result = save_assignments(assignments_data)

        if not result["success"]:
            return result

        logger.info("Successfully saved assignments")
        return result

    except Exception:
        logger.exception("Error saving assignments")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save assignments",
        )


@app.post(
    "/api/rules/validate",
    response_model=dict[str, Any],
    tags=["Rules"],
    status_code=status.HTTP_200_OK,
)
async def validate_rules(config_data: dict[str, Any]) -> dict[str, Any]:
    """Validate ingestion rules configuration without saving"""
    logger.info("Validating ingestion rules configuration")
    try:
        rules_data = config_data.get("rules", [])
        assignments_data = config_data.get("source_assignments", [])

        logger.info(
            "Validating %d rules and %d source assignments",
            len(rules_data),
            len(assignments_data),
        )

        errors = []

        # Validate rules
        for i, rule_data in enumerate(rules_data):
            try:
                IngestionRule(**rule_data)
            except (TypeError, ValueError) as e:
                errors.append(f"Rule {i + 1}: {e!s}")

        # Validate source assignments
        for i, assignment_data in enumerate(assignments_data):
            try:
                SourceRuleAssignment(**assignment_data)
            except (TypeError, ValueError) as e:
                errors.append(f"Source assignment {i + 1}: {e!s}")

        # Check that assigned rules exist
        rule_names = {rule_data.get("name") for rule_data in rules_data}
        for assignment_data in assignments_data:
            for rule_name in assignment_data.get("assigned_rules", []):
                if rule_name not in rule_names:
                    errors.append(
                        f"Source '{assignment_data.get('source_name')}' references non-existent rule '{rule_name}'"
                    )

        is_valid = len(errors) == 0
        return {
            "success": True,
            "valid": is_valid,
            "errors": errors,
        }

    except Exception:
        logger.exception("Error validating rules")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate rules",
        )


@app.get(
    "/api/rules/logs",
    response_model=dict[str, Any],
    tags=["Rules"],
    status_code=status.HTTP_200_OK,
)
async def get_rules_logs() -> dict[str, Any]:
    """Get list of ingestion rules log files"""
    logger.info("Getting ingestion rules log files")
    try:
        if not os.path.exists(INGESTION_RULES_LOGS):
            return {"success": True, "data": []}

        log_files = []
        for filename in os.listdir(INGESTION_RULES_LOGS):
            if filename.endswith(".json"):
                filepath = os.path.join(INGESTION_RULES_LOGS, filename)
                stat = os.stat(filepath)
                log_files.append(
                    {
                        "filename": filename,
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "path": filepath,
                    }
                )

        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x["modified"], reverse=True)

        return {"success": True, "data": log_files}

    except Exception:
        logger.exception("Error getting rules logs")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get rules logs",
        )


@app.get(
    "/api/rules/logs/{filename}",
    response_model=dict[str, Any],
    tags=["Rules"],
    status_code=status.HTTP_200_OK,
)
async def get_rules_log_content(filename: str) -> dict[str, Any]:
    """Get content of a specific ingestion rules log file"""
    logger.info("Getting content of rules log file: %s", filename)
    try:
        # Validate filename to prevent directory traversal
        if not filename.endswith(".json") or "/" in filename or "\\" in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename"
            )

        filepath = os.path.join(INGESTION_RULES_LOGS, filename)

        if not os.path.exists(filepath):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Log file '{filename}' not found",
            )

        with open(filepath, encoding="utf-8") as f:
            log_data = json.load(f)

        return {"success": True, "filename": filename, "data": log_data}

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error getting rules log content")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get log content",
        )


@app.post(
    "/api/rules/apply",
    response_model=dict[str, Any],
    tags=["Rules"],
    summary="Apply rule assignments to database records",
)
async def apply_rule_assignments(request: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Apply rule assignments to database records for specified table and source"""
    logger.info("Applying rule assignments to database records")

    try:
        table_name = request.get("table_name")
        source_name = request.get("source_name")  # Optional

        # Validate required parameters
        if not table_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="table_name is required"
            )

        # Validate table name against allowed tables
        allowed_tables = ["m3u_channels", "epg_channels", "programs"]
        if table_name not in allowed_tables:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid table_name. Must be one of: {allowed_tables}",
            )

        logger.info(
            "Applying rules to table: %s, source: %s",
            table_name,
            source_name or "all sources",
        )

        # Apply rules to the specified table and source
        result = apply_post_load_rules(table_name, source_name)

        logger.info(
            "All rules application completed for the %s from %s",
            table_name,
            source_name,
        )

        return {
            "success": True,
            "message": f"Rules applied successfully to {table_name}"
            + (f" for source {source_name}" if source_name else ""),
            "table_name": table_name,
            "source_name": source_name,
            "results": result,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error applying rule assignments")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply rule assignments",
        )


@app.post(
    "/api/rules/apply/single",
    response_model=dict[str, Any],
    tags=["Rules"],
    summary="Apply a single rule to a specific source and table",
)
async def apply_single_rule(request: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Apply a single rule to a specific table and source"""
    logger.info("Applying single rule to database records")

    try:
        rule_name = request.get("rule_name")
        table_name = request.get("table_name")
        source_name = request.get("source_name")

        # Validate required parameters
        if not all([rule_name, table_name, source_name]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="rule_name, table_name, and source_name are required",
            )

        # Validate table name
        allowed_tables = ["m3u_channels", "epg_channels", "programs"]
        if table_name not in allowed_tables:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid table_name. Must be one of: {allowed_tables}",
            )

        logger.info(
            "Applying single rule '%s' to %s for source %s",
            rule_name,
            table_name,
            source_name,
        )

        result = post_load_engine.apply_single_rule_to_source(
            rule_name, table_name, source_name
        )

        logger.info(
            "Single rule '%s' application completed for %s from %s",
            rule_name,
            table_name,
            source_name,
        )

        # Convert numpy types to Python types for JSON serialization
        serializable_result = {
            "processed": int(result.get("processed", 0)),
            "filtered": int(result.get("filtered", 0)),
            "passed": int(result.get("passed", 0)),
        }

        return {
            "success": True,
            "message": f"Rule '{rule_name}' applied to {table_name} for source {source_name}",
            "rule_name": rule_name,
            "table_name": table_name,
            "source_name": source_name,
            "results": serializable_result,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error applying single rule")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply single rule",
        )


@app.post(
    "/api/rules/apply/source",
    response_model=dict[str, Any],
    tags=["Rules"],
    summary="Apply all rules to a specific source",
)
async def apply_rules_to_source(request: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Apply all assigned rules to a specific source across all tables"""
    logger.info("Applying all rules to source")

    try:
        source_name = request.get("source_name")
        table_names = request.get("table_names")  # Optional

        # Validate required parameters
        if not source_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="source_name is required",
            )

        # Validate table names if provided
        if table_names:
            allowed_tables = ["m3u_channels", "epg_channels", "programs"]
            invalid_tables = [t for t in table_names if t not in allowed_tables]
            if invalid_tables:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid table names: {invalid_tables}. Must be from: {allowed_tables}",
                )

        logger.info(
            "Applying all rules to source %s for tables: %s",
            source_name,
            table_names or "all",
        )

        result = post_load_engine.apply_all_rules_to_source(source_name, table_names)

        logger.info("All rules for %s applied to %s", source_name, table_names)

        return {
            "success": True,
            "message": f"All rules applied to source {source_name}",
            "source_name": source_name,
            "table_names": table_names or ["m3u_channels", "epg_channels", "programs"],
            "results": result,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error applying rules to source")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply rules to source",
        )


@app.post(
    "/api/rules/unapply",
    response_model=dict[str, Any],
    tags=["Rules"],
    summary="Unapply (remove) rules from database records",
)
async def unapply_rules(request: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Unapply (remove) rules from database records for specified table and source"""
    logger.info("Unapplying rules from database records")

    try:
        table_name = request.get("table_name")
        source_name = request.get("source_name")
        rule_names = request.get(
            "rule_names"
        )  # Optional - if not provided, unapply all

        # Validate required parameters
        if not all([table_name, source_name]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="table_name and source_name are required",
            )

        # Validate table name
        allowed_tables = ["m3u_channels", "epg_channels", "programs"]
        if table_name not in allowed_tables:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid table_name. Must be one of: {allowed_tables}",
            )

        logger.info(
            "Unapplying rules from %s for source %s: %s",
            table_name,
            source_name,
            rule_names or "all rules",
        )

        result = post_load_engine.unapply_rules_from_source(
            table_name, source_name, rule_names
        )

        logger.info("Rule unapplication completed: %s", result)

        return {
            "success": True,
            "message": f"Rules unapplied from {table_name} for source {source_name}",
            "table_name": table_name,
            "source_name": source_name,
            "rule_names": rule_names or "all",
            "results": result,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error unapplying rules")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unapply rules",
        )


# Job Queue Management API Endpoints


@app.get(
    "/api/jobs/queue/status",
    response_model=dict[str, Any],
    tags=["Job Queue"],
    status_code=status.HTTP_200_OK,
)
async def get_job_queue_status() -> dict[str, Any]:
    """Get current job queue status and information"""
    logger.info("Getting job queue status")
    try:
        status = await get_queue_status()
        return {"success": True, "data": status}
    except Exception:
        logger.exception("Error getting job queue status")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job queue status",
        )


@app.get(
    "/api/jobs/{job_id}/status",
    response_model=dict[str, Any],
    tags=["Job Queue"],
    status_code=status.HTTP_200_OK,
)
async def get_job_status_by_id(job_id: str) -> dict[str, Any]:
    """Get status of a specific job"""
    logger.info("Getting status for job %s", job_id)
    try:
        job_status = await get_job_status(job_id)
        if not job_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
            )
        return {"success": True, "data": job_status}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error getting job status")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job status",
        )


@app.post(
    "/api/jobs/{job_id}/cancel",
    response_model=dict[str, Any],
    tags=["Job Queue"],
    status_code=status.HTTP_200_OK,
)
async def cancel_job_by_id(job_id: str) -> dict[str, Any]:
    """Cancel a queued job"""
    logger.info("Cancelling job %s", job_id)
    try:
        cancelled = await cancel_job(job_id)
        if not cancelled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job {job_id} cannot be cancelled (not found or already running/completed)",
            )
        return {"success": True, "message": f"Job {job_id} cancelled successfully"}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error cancelling job")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel job",
        )


# File Generation API Endpoints


@app.get("/api/iseetv.m3u", tags=["File Generation"])
async def get_global_m3u():
    """Generate global M3U playlist with all filtered channels from all sources.

    Returns:
        M3U playlist content with proper content-type headers

    """
    logger.info("Generating global M3U playlist")
    try:
        # Get all channels and apply unified filtering
        m3u_channels, epg_channels, programs = get_filtered_channels_and_programs()
        filtered_m3u_channels, _, _ = apply_unified_channel_filtering(
            m3u_channels, epg_channels, programs
        )

        # Generate M3U content
        m3u_content = generate_m3u_content(filtered_m3u_channels)

        # Return with proper content type
        return Response(
            content=m3u_content,
            media_type="audio/x-mpegurl",
            headers={
                "Content-Disposition": "attachment; filename=iseetv.m3u",
                "Cache-Control": "no-cache",
            },
        )
    except Exception:
        logger.exception("Error generating global M3U")
        raise HTTPException(status_code=500, detail="Error generating M3U")


@app.get("/api/iseetv.xml", tags=["File Generation"])
async def get_global_epg():
    """Generate global EPG XML with all filtered channels and programs from all sources.

    Returns:
        EPG XML content with proper content-type headers

    """
    logger.info("Generating global EPG XML")
    try:
        # Get all channels and programs, apply unified filtering
        m3u_channels, epg_channels, programs = get_filtered_channels_and_programs()
        _, filtered_epg_channels, filtered_programs = apply_unified_channel_filtering(
            m3u_channels, epg_channels, programs
        )

        # Generate EPG content
        epg_content = generate_epg_content(filtered_epg_channels, filtered_programs)

        # Return with proper content type
        return Response(
            content=epg_content,
            media_type="application/xml",
            headers={
                "Content-Disposition": "attachment; filename=iseetv.xml",
                "Cache-Control": "no-cache",
            },
        )
    except Exception:
        logger.exception("Error generating global EPG")
        raise HTTPException(status_code=500, detail="Error generating EPG")


@app.get("/api/{source}.m3u", tags=["File Generation"])
async def get_source_m3u(source: str):
    """Generate source-specific M3U playlist with filtered channels from a specific source.

    Args:
        source: Source name to filter by

    Returns:
        M3U playlist content with proper content-type headers

    """
    logger.info("Generating source-specific M3U playlist for source %s", source)
    try:
        # Get channels for specific source and apply unified filtering
        m3u_channels, epg_channels, programs = get_filtered_channels_and_programs(
            source=source
        )
        filtered_m3u_channels, _, _ = apply_unified_channel_filtering(
            m3u_channels, epg_channels, programs
        )

        # Generate M3U content
        m3u_content = generate_m3u_content(filtered_m3u_channels)

        # Return with proper content type
        return Response(
            content=m3u_content,
            media_type="audio/x-mpegurl",
            headers={
                "Content-Disposition": f"attachment; filename={source}.m3u",
                "Cache-Control": "no-cache",
            },
        )
    except Exception:
        logger.exception("Error generating M3U for source %s", source)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating M3U for source {source}",
        )


@app.get("/api/{source}.xml", tags=["File Generation"])
async def get_source_epg(source: str):
    """Generate source-specific EPG XML with filtered channels and programs from a specific source.

    Args:
        source: Source name to filter by

    Returns:
        EPG XML content with proper content-type headers

    """
    logger.info("Generating source-specific EPG XML for source %s", source)
    try:
        # Get channels and programs for specific source, apply unified filtering
        m3u_channels, epg_channels, programs = get_filtered_channels_and_programs(
            source=source
        )
        _, filtered_epg_channels, filtered_programs = apply_unified_channel_filtering(
            m3u_channels, epg_channels, programs
        )

        # Generate EPG content
        epg_content = generate_epg_content(filtered_epg_channels, filtered_programs)

        # Return with proper content type
        return Response(
            content=epg_content,
            media_type="application/xml",
            headers={
                "Content-Disposition": f"attachment; filename={source}.xml",
                "Cache-Control": "no-cache",
            },
        )
    except Exception:
        logger.exception("Error generating EPG for source %s", source)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating EPG for source {source}",
        )


# Application event handlers


@app.on_event("startup")
async def startup_event():
    """Initialize job queue and scheduler on application startup"""
    logger.info("Application startup - initializing job queue and scheduler")
    try:
        # Initialize job queue first
        await initialize_job_queue()
        logger.debug("Job queue initialized successfully")

        # Start the scheduler
        start_scheduler()
        logger.debug("Scheduler started successfully on application startup")
    except Exception:
        logger.exception("Failed to start job queue and scheduler on startup")
        # Don't fail the entire application if startup fails


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the scheduler and job queue on application shutdown"""
    logger.info("Application shutdown - stopping scheduler and job queue")
    try:
        # Stop scheduler first
        stop_scheduler()
        logger.debug("Scheduler stopped successfully")

        # Shutdown job queue
        await shutdown_job_queue()
        logger.debug("Job queue shutdown successfully on application shutdown")
    except Exception:
        logger.exception("Error stopping scheduler and job queue on shutdown")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1314)
