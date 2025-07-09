from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from typing import Dict, List, Literal, Any, Sequence, Optional
from sqlalchemy import inspect, text, Row
import uvicorn
import json
from fastapi import HTTPException, status
from fastapi.responses import RedirectResponse, StreamingResponse
import asyncio
import logging
import os
from models.models import (
    DownloadProgress,
    IngestProgress,
    Message,
    Source,
    GlobalSettings,
    DownloadTaskResponse,
    DownloadAllTasksResponse,
    TableResponse,
)
from models.stream_models import (
    StreamsResponse,
    StreamProgramsResponse,
)
from download.downloader import (
    background_single_download_task,
)
from common.task_manager import DownloadTaskManager
from common.utils import (
    create_task_id,
    get_progress_response,
    get_all_progress_response,
    format_download_progress_response,
    format_ingest_progress_response,
    format_table_response,
)
from common.constants import DATA_PATH
from ingest.epg_loader import load_epg_file_async
from ingest.m3u_loader import load_m3u_file_async
from common.task_manager import TaskManager, IngestTaskManager
from utils.filter_utils import precompute_filter_values, get_all_filter_values
from utils.stream_utils import (
    get_streams_query,
    get_stream_programs_query,
    precompute_streams_filter_values,
    get_streams_filter_values,
)
from common.db import init_db, engine, SessionLocal
from common.utils import log_function
from scheduler.scheduler_integration import (
    get_scheduler_manager,
    initialize_scheduler,
    start_scheduler,
    stop_scheduler,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


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
    log_function("Redirecting to Swagger docs")
    return RedirectResponse(url="/api/docs")


@app.get(
    "/docs",
    response_model=Message,
    tags=["Redirect"],
    status_code=status.HTTP_308_PERMANENT_REDIRECT,
)
async def docs() -> RedirectResponse:
    """Redirect to the Swagger docs"""
    log_function("Redirecting to Swagger docs")
    return RedirectResponse(url="/api/docs")


@app.get(
    "/api",
    response_model=Message,
    tags=["Redirect"],
    status_code=status.HTTP_308_PERMANENT_REDIRECT,
)
async def api() -> RedirectResponse:
    """Redirect to the Swagger docs"""
    log_function("Redirecting to Swagger docs")
    return RedirectResponse(url="/api/docs")


@app.get(
    "/api/health",
    response_model=Message,
    tags=["Health"],
    status_code=status.HTTP_200_OK,
)
async def get_health() -> Message:
    """Return a health check."""
    log_function()
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
    log_function(level="debug")
    try:
        with open(settings_file, "r") as f:
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
    log_function(level="debug")
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
    response_model=List[Source],
    tags=["Sources"],
    status_code=status.HTTP_200_OK,
)
async def get_sources(
    sources_file: str = os.path.join(DATA_PATH, "sources.json"),
) -> List[Source]:
    """Return sources from the provided file"""
    log_function(level="debug")
    try:
        with open(sources_file, "r") as f:
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
    sources: List[Source], sources_file: str = os.path.join(DATA_PATH, "sources.json")
) -> Message:
    """Set sources in the provided file"""
    log_function(level="debug")
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
    log_function(f"Getting ingest progress for: {task_id}")
    return IngestProgress(**get_progress_response(task_id, "ingest"))


@app.get(
    "/api/ingest/progress",
    response_model=Dict[str, Dict],
    tags=["Ingest"],
    status_code=status.HTTP_200_OK,
)
async def get_ingest_progress() -> Dict[str, Dict]:
    """Get all ingest progress"""
    log_function("Getting ingest progress", level="debug")
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
    log_function(f"Getting download progress for: {task_id}", level="debug")
    return DownloadProgress(**get_progress_response(task_id, "download"))


@app.get(
    "/api/download/progress",
    response_model=Dict[str, DownloadProgress],
    tags=["Download"],
    status_code=status.HTTP_200_OK,
)
async def get_all_download_progress() -> Dict[str, DownloadProgress]:
    """Get all download progress tasks"""
    log_function(level="debug")
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
    log_function(f"Canceling download task {task_id}")
    try:
        from common.state import cancel_task

        success = cancel_task(task_id, "download")
        if success:
            return Message(message=f"Download task {task_id} cancelled successfully")
        else:
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
    log_function(f"Downloading all {file_type} files")
    try:
        with open(sources_file, "r") as f:
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

        # Create task IDs and start downloads
        task_ids = []
        for source in file_type_sources:
            # Create unique task ID for each source
            task_id = create_task_id(source.name, file_type, "download")
            task_ids.append(task_id)

            # Create download task (1 item per task)
            DownloadTaskManager.create_download_task(task_id, 1)

            # Start background download task for this source
            asyncio.create_task(
                background_single_download_task(
                    task_id, source.name, file_type, sources_file, download_dir
                )
            )

        return DownloadAllTasksResponse(
            message=f"{file_type} downloads started for {len(file_type_sources)} sources",
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
    """Download file of a specific type for a specific source"""
    log_function(f"Downloading {file_type} file for source {source_name}")
    try:
        # Create unique task ID for each source
        task_id = create_task_id(source_name, file_type, "download")

        # Create download task (1 item per task)
        DownloadTaskManager.create_download_task(task_id, 1)

        # Start background download task for this source
        asyncio.create_task(
            background_single_download_task(
                task_id, source_name, file_type, sources_file, download_dir
            )
        )
        return DownloadTaskResponse(
            message=f"{file_type} file for {source_name} download started",
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
    log_function(f"Downloading {file_type} file for source {source_name}")
    try:
        # Validate file type
        if file_type not in ["m3u", "epg"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Must be 'm3u' or 'epg'",
            )

        # Load sources to get the file URL
        with open(sources_file, "r") as f:
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

        # Use httpx for better async streaming support
        import httpx
        from fastapi.responses import StreamingResponse

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
                        detail=f"Network error while fetching file: {str(e)}",
                    )
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Error streaming file: {str(e)}",
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
        logger.error(f"Unexpected error in download_file_stream: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@app.post(
    "/api/load/{file_type}/{source_name}",
    response_model=Dict[str, str],
    tags=["Database"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def load_file_to_db(
    file_type: Literal["m3u", "epg"],
    source_name: str,
    sources_file: str = os.path.join(DATA_PATH, "sources.json"),
) -> Dict[str, str]:
    """Start async database loading task for parsed file data"""
    log_function(f"Loading {file_type} file to database for {source_name}")
    try:
        # Load sources configuration
        with open(sources_file, "r") as f:
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

        # Start background task
        asyncio.create_task(
            background_load_task(task_id, file_type, file_path, source_name)
        )

        return {
            "task_id": task_id,
            "message": f"Started loading {file_type.upper()} file for {source_name}",
            "status": "pending",
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
    log_function()
    session = SessionLocal()
    try:
        # Start the task (Step 1: Download already completed)
        TaskManager.start_task(task_id, "ingest", "ingesting")

        logger.info(
            f"Started background load task {task_id} for {file_type} file: {file_path}"
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

        # Precompute filter values for the affected tables
        if file_type == "m3u":
            precompute_filter_values(session, "m3u_channels")
            logger.info(
                f"Precomputed filter values for m3u_channels after task {task_id}"
            )
        elif file_type == "epg":
            precompute_filter_values(session, "epg_channels")
            precompute_filter_values(session, "programs")
            logger.info(
                f"Precomputed filter values for epg_channels and programs after task {task_id}"
            )

        # Precompute streams filter values (combines M3U and EPG data)
        precompute_streams_filter_values(session)
        logger.info(f"Precomputed streams filter values after task {task_id}")

        # Add a small delay to ensure frontend can display progress bars
        await asyncio.sleep(2)

        # Complete the task
        TaskManager.complete_task(
            task_id,
            "ingest",
            f"Successfully loaded records from {source_name} {file_type} file",
        )
        logger.info(
            f"Completed background load task {task_id}: filter values precomputed"
        )

    except Exception as e:
        logger.error(f"Background load task {task_id} failed: {e}")
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
async def get_db_table_head(table: str) -> Dict[str, Any]:
    """Return the first 10 rows of a table"""
    try:
        with SessionLocal() as session:
            result = session.execute(text(f"SELECT * FROM {table} LIMIT 10"))
            records = [dict(row._mapping) for row in result.fetchall()]
            return format_table_response(records, table)
    except Exception as e:
        logger.error(f"Error fetching head of table {table}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch head of table: {str(e)}",
        )


@app.get(
    "/api/tables/{table_name}",
    response_model=TableResponse,
    tags=["Database"],
    status_code=status.HTTP_200_OK,
)
async def get_table_data(
    table_name: str,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    """Return paginated table data with optional source filtering"""
    # Validate table name to prevent SQL injection
    valid_tables = ["epg_channels", "m3u_channels", "programs"]
    if table_name not in valid_tables:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid table name. Must be one of: {', '.join(valid_tables)}",
        )

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
        logger.error(f"Error fetching table data for {table_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch table data: {str(e)}",
        )


@app.get(
    "/api/db/summary",
    response_model=Dict[str, Any],
    tags=["Database"],
    status_code=status.HTTP_200_OK,
)
async def get_db_summary() -> Dict[str, Any]:
    """Return a summary of the database"""
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

            summary.append(
                {
                    "table": table_name,
                    "columns": columns,
                    "primary_key": inspector.get_pk_constraint(table_name),
                    "indexes": inspector.get_indexes(table_name),
                    "row_count": row_count,
                    "sample_row": rows[0] if rows else "",
                }
            )

    return {"tables": summary}


@app.get(
    "/api/tables/{table_name}/filters",
    response_model=Dict[str, Any],
    tags=["Database"],
    status_code=status.HTTP_200_OK,
)
async def get_table_filter_values(table_name: str) -> Dict[str, Any]:
    """Get precomputed filter values for a table's filterable columns"""
    # Validate table name to prevent SQL injection
    valid_tables = ["epg_channels", "m3u_channels", "programs"]
    if table_name not in valid_tables:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid table name. Must be one of: {valid_tables}",
        )

    try:
        with SessionLocal() as session:
            filter_values = get_all_filter_values(session, table_name)

            return {
                "success": True,
                "data": filter_values,
                "table_name": table_name,
            }

    except Exception as e:
        logger.error(f"Error getting filter values for table {table_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get(
    "/api/tables/{table_name}/columns",
    response_model=Dict[str, Any],
    tags=["Database"],
    status_code=status.HTTP_200_OK,
)
async def get_table_columns(table_name: str) -> Dict[str, Any]:
    """Get column names for a specific table"""
    # Validate table name to prevent SQL injection
    valid_tables = ["epg_channels", "m3u_channels", "programs"]
    if table_name not in valid_tables:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid table name. Must be one of: {valid_tables}",
        )

    try:
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns(table_name)]

        return {
            "success": True,
            "data": columns,
            "table_name": table_name,
        }

    except Exception as e:
        logger.error(f"Error getting columns for table {table_name}: {e}")
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
    source: Optional[str] = None,
    group: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
    sort_field: str = "name",
    sort_order: str = "asc",
    global_filter: Optional[str] = None,
    column_filters: Optional[str] = None,
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

    Returns:
        StreamsResponse with paginated stream data and filter options
    """
    log_function(
        f"Getting streams: page={page}, size={page_size}, source={source}, group={group}"
    )

    try:
        # Validate page_size
        if page_size > 500:
            page_size = 500
        if page_size < 1:
            page_size = 100

        # Parse column filters if provided
        parsed_column_filters = {}
        if column_filters:
            try:
                import json

                parsed_column_filters = json.loads(column_filters)
            except json.JSONDecodeError:
                logger.warning(f"Invalid column_filters JSON: {column_filters}")

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
            )

            # Get filter values
            filter_values = get_streams_filter_values(session)

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
            )

    except Exception as e:
        logger.error(f"Error getting streams: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get streams: {str(e)}",
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
    global_filter: Optional[str] = None,
    column_filters: Optional[str] = None,
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
    log_function(
        f"Getting programs for stream: source={source}, channel_id={channel_id}"
    )

    try:
        # Validate page_size
        if page_size > 500:
            page_size = 500
        if page_size < 1:
            page_size = 100

        # Parse column filters if provided
        parsed_column_filters = {}
        if column_filters:
            try:
                import json

                parsed_column_filters = json.loads(column_filters)
            except json.JSONDecodeError:
                logger.warning(f"Invalid column_filters JSON: {column_filters}")

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
        logger.error(f"Error getting stream programs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stream programs: {str(e)}",
        )


@app.get(
    "/api/streams/filters",
    response_model=Dict[str, Any],
    tags=["Streams"],
    status_code=status.HTTP_200_OK,
)
async def get_streams_filters() -> Dict[str, Any]:
    """Get precomputed filter values for streams view.

    Returns:
        Dictionary with filter values for source and group columns
    """
    log_function("Getting streams filter values")

    try:
        with SessionLocal() as session:
            filter_values = get_streams_filter_values(session)

            return {
                "success": True,
                "data": filter_values,
                "table_name": "streams",
            }

    except Exception as e:
        logger.error(f"Error getting streams filter values: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get streams filter values: {str(e)}",
        )


@app.post(
    "/api/streams/precompute-filters",
    response_model=Dict[str, str],
    tags=["Streams"],
    status_code=status.HTTP_200_OK,
)
async def precompute_streams_filters() -> Dict[str, str]:
    """Precompute filter values for streams view.

    This is typically called after data ingestion to update filter options.

    Returns:
        Success message
    """
    log_function("Precomputing streams filter values")

    try:
        with SessionLocal() as session:
            precompute_streams_filter_values(session)

            return {
                "message": "Successfully precomputed streams filter values",
                "table_name": "streams",
            }

    except Exception as e:
        logger.error(f"Error precomputing streams filter values: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to precompute streams filter values: {str(e)}",
        )


# Scheduler API Endpoints


@app.get(
    "/api/scheduler/status",
    response_model=Dict[str, Any],
    tags=["Scheduler"],
    status_code=status.HTTP_200_OK,
)
async def get_scheduler_status() -> Dict[str, Any]:
    """Get current scheduler status and job information"""
    log_function("Getting scheduler status")
    scheduler_manager = get_scheduler_manager()
    return scheduler_manager.get_scheduler_status()


@app.post(
    "/api/scheduler/start",
    response_model=Dict[str, str],
    tags=["Scheduler"],
    status_code=status.HTTP_200_OK,
)
async def start_scheduler_endpoint() -> Dict[str, str]:
    """Start the refresh scheduler"""
    log_function("Starting scheduler via API")
    try:
        start_scheduler()
        return {"message": "Scheduler started successfully", "status": "running"}
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start scheduler: {str(e)}",
        )


@app.post(
    "/api/scheduler/stop",
    response_model=Dict[str, str],
    tags=["Scheduler"],
    status_code=status.HTTP_200_OK,
)
async def stop_scheduler_endpoint() -> Dict[str, str]:
    """Stop the refresh scheduler"""
    log_function("Stopping scheduler via API")
    try:
        stop_scheduler()
        return {"message": "Scheduler stopped successfully", "status": "stopped"}
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop scheduler: {str(e)}",
        )


@app.post(
    "/api/scheduler/restart",
    response_model=Dict[str, str],
    tags=["Scheduler"],
    status_code=status.HTTP_200_OK,
)
async def restart_scheduler_endpoint() -> Dict[str, str]:
    """Restart the refresh scheduler"""
    log_function("Restarting scheduler via API")
    try:
        scheduler_manager = get_scheduler_manager()
        scheduler_manager.restart()
        return {"message": "Scheduler restarted successfully", "status": "running"}
    except Exception as e:
        logger.error(f"Error restarting scheduler: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart scheduler: {str(e)}",
        )


@app.post(
    "/api/scheduler/update/{source_name}",
    response_model=Dict[str, str],
    tags=["Scheduler"],
    status_code=status.HTTP_200_OK,
)
async def update_source_schedule(
    source_name: str,
    sources_file: str = os.path.join(DATA_PATH, "sources.json"),
) -> Dict[str, str]:
    """Update schedule for a specific source"""
    log_function(f"Updating schedule for source: {source_name}")
    try:
        scheduler_manager = get_scheduler_manager()
        # Load sources configuration
        with open(sources_file, "r") as f:
            sources = [Source(**source) for source in json.load(f)]

        # Find the source
        source = next(
            (source for source in sources if source.name == source_name), None
        )
        if source:
            log_function("updating sources")
            scheduler_manager.update_source_schedule(source)
        else:
            log_function(f"deleting source: {source_name}")
            # source not found, remove existing jobs
            delete_source_schedule(source_name)

        return {
            "message": f"Schedule updated for source {source_name}",
            "source_name": source_name,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating schedule for {source_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update schedule: {str(e)}",
        )


@app.delete(
    "/api/scheduler/delete/{source_name}",
    response_model=Dict[str, str],
    tags=["Scheduler"],
    status_code=status.HTTP_200_OK,
)
async def delete_source_schedule(source_name: str) -> Dict[str, str]:
    """Delete/remove schedule for a specific source"""
    log_function(f"Deleting schedule for source: {source_name}")
    try:
        scheduler_manager = get_scheduler_manager()
        if scheduler_manager.scheduler:
            scheduler_manager.scheduler.remove_source_jobs(source_name)

        return {
            "message": f"Schedule deleted for source {source_name}",
            "source_name": source_name,
        }

    except Exception as e:
        logger.error(f"Error deleting schedule for {source_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete schedule: {str(e)}",
        )


@app.get(
    "/api/scheduler/validate",
    response_model=Dict[str, Any],
    tags=["Scheduler"],
    status_code=status.HTTP_200_OK,
)
async def validate_scheduler_config(
    sources_file: str = os.path.join(DATA_PATH, "sources.json"),
) -> Dict[str, Any]:
    """Validate scheduler configuration for all sources"""
    log_function("Validating scheduler configuration")
    try:
        # Load sources configuration
        with open(sources_file, "r") as f:
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

    except Exception as e:
        logger.error(f"Error validating scheduler configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate configuration: {str(e)}",
        )


@app.get(
    "/api/rules/status",
    response_model=Dict[str, Any],
    tags=["Rules"],
    status_code=status.HTTP_200_OK,
)
async def get_rules_status() -> Dict[str, Any]:
    """Get current status of ingestion rules system"""
    log_function("Getting ingestion rules status")
    try:
        from rules.ingestion_rules import get_rules_status

        status_info = get_rules_status()
        return {"success": True, "data": status_info}
    except Exception as e:
        logger.error(f"Error getting rules status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rules status: {str(e)}",
        )


@app.get(
    "/api/rules",
    response_model=Dict[str, Any],
    tags=["Rules"],
    status_code=status.HTTP_200_OK,
)
async def get_rules() -> Dict[str, Any]:
    """Get all ingestion rules and source assignments"""
    log_function("Getting ingestion rules and source assignments")
    try:
        from common.rules_storage import load_rules, load_assignments

        rules = load_rules()
        assignments = load_assignments()

        return {
            "rules": rules,
            "source_assignments": assignments,
        }
    except Exception as e:
        logger.error(f"Error getting rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rules: {str(e)}",
        )


@app.post(
    "/api/rules/save",
    response_model=Dict[str, Any],
    tags=["Rules"],
    status_code=status.HTTP_200_OK,
)
async def save_rules_only(rules_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Save only ingestion rules to rules.json file"""
    log_function("Saving ingestion rules only")
    try:
        from common.rules_storage import save_rules

        result = save_rules(rules_data)

        if not result["success"]:
            return result

        log_function(f"Successfully saved rules")
        return result

    except Exception as e:
        logger.error(f"Error saving rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save rules: {str(e)}",
        )


@app.post(
    "/api/assignments/save",
    response_model=Dict[str, Any],
    tags=["Rules"],
    status_code=status.HTTP_200_OK,
)
async def save_assignments_only(
    assignments_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Save only source rule assignments to assignments.json file"""
    log_function("Saving source rule assignments only")
    try:
        from common.rules_storage import save_assignments

        result = save_assignments(assignments_data)

        if not result["success"]:
            return result

        log_function(f"Successfully saved assignments")
        return result

    except Exception as e:
        logger.error(f"Error saving assignments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save assignments: {str(e)}",
        )


@app.post(
    "/api/rules/validate",
    response_model=Dict[str, Any],
    tags=["Rules"],
    status_code=status.HTTP_200_OK,
)
async def validate_rules(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate ingestion rules configuration without saving"""
    log_function("Validating ingestion rules configuration")
    try:
        from rules.ingestion_rules import IngestionRule, SourceRuleAssignment

        rules_data = config_data.get("rules", [])
        assignments_data = config_data.get("source_assignments", [])

        log_function(
            f"Validating {len(rules_data)} rules and {len(assignments_data)} source assignments"
        )

        errors = []

        # Validate rules
        for i, rule_data in enumerate(rules_data):
            try:
                IngestionRule(**rule_data)
            except (TypeError, ValueError) as e:
                errors.append(f"Rule {i+1}: {str(e)}")

        # Validate source assignments
        for i, assignment_data in enumerate(assignments_data):
            try:
                SourceRuleAssignment(**assignment_data)
            except (TypeError, ValueError) as e:
                errors.append(f"Source assignment {i+1}: {str(e)}")

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

    except Exception as e:
        logger.error(f"Error validating rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate rules: {str(e)}",
        )


@app.get(
    "/api/rules/logs",
    response_model=Dict[str, Any],
    tags=["Rules"],
    status_code=status.HTTP_200_OK,
)
async def get_rules_logs() -> Dict[str, Any]:
    """Get list of ingestion rules log files"""
    log_function("Getting ingestion rules log files")
    try:
        from rules.ingestion_rules import INGESTION_RULES_LOGS

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

    except Exception as e:
        logger.error(f"Error getting rules logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rules logs: {str(e)}",
        )


@app.get(
    "/api/rules/logs/{filename}",
    response_model=Dict[str, Any],
    tags=["Rules"],
    status_code=status.HTTP_200_OK,
)
async def get_rules_log_content(filename: str) -> Dict[str, Any]:
    """Get content of a specific ingestion rules log file"""
    log_function(f"Getting content of rules log file: {filename}")
    try:
        from rules.ingestion_rules import INGESTION_RULES_LOGS

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

        with open(filepath, "r", encoding="utf-8") as f:
            log_data = json.load(f)

        return {"success": True, "filename": filename, "data": log_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rules log content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get log content: {str(e)}",
        )


# Application event handlers


@app.on_event("startup")
async def startup_event():
    """Initialize and start the scheduler on application startup"""
    log_function("Application startup - initializing scheduler")
    try:
        # Start the scheduler
        start_scheduler()
        logger.info("Scheduler started successfully on application startup")
    except Exception as e:
        logger.error(f"Failed to start scheduler on startup: {e}")
        # Don't fail the entire application if scheduler fails to start


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the scheduler on application shutdown"""
    log_function("Application shutdown - stopping scheduler")
    try:
        stop_scheduler()
        logger.info("Scheduler stopped successfully on application shutdown")
    except Exception as e:
        logger.error(f"Error stopping scheduler on shutdown: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1314)
