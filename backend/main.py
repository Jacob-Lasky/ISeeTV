from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from typing import Dict, List, Literal, Any
from sqlalchemy import inspect, text
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
)
from download.downloader import (
    create_download_task,
    background_single_download_task,
)
from common.state import get_progress
from common.utils import create_task_id, get_progress_response
from common.constants import DATA_PATH
from ingest.epg_parser import parse_epg_for_programs, parse_epg_for_channels
from ingest.m3u_parser import parse_m3u
from ingest.epg_loader import load_epg_file_async
from ingest.m3u_loader import load_m3u_file_async
from ingest.ingest_tasks import (
    create_ingest_task,
    start_ingest_task,
    complete_ingest_task,
    fail_ingest_task,
    update_ingest_item_progress,
)
from common.db import init_db, engine, SessionLocal
from common.utils import create_task_id

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ISeeTV API",
    description="An IPTV Pipeline Platform",
    version="0.1.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_tags=[
        {"name": "Health", "description": "Health checks"},
        {"name": "Settings", "description": "Global app configuration"},
        {"name": "Sources", "description": "Manage IPTV sources (M3U, EPG, metadata)"},
        {"name": "Download", "description": "Download operations"},
        {"name": "Ingest", "description": "Ingest operations"},
        {"name": "Database", "description": "Database operations"},
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


@app.get(
    "/",
    response_model=Message,
    tags=["Redirect"],
    status_code=status.HTTP_308_PERMANENT_REDIRECT,
)
async def root() -> RedirectResponse:
    """Redirect to the Swagger docs"""
    return RedirectResponse(url="/api/docs")


@app.get(
    "/docs",
    response_model=Message,
    tags=["Redirect"],
    status_code=status.HTTP_308_PERMANENT_REDIRECT,
)
async def docs() -> RedirectResponse:
    """Redirect to the Swagger docs"""
    return RedirectResponse(url="/api/docs")


@app.get(
    "/api",
    response_model=Message,
    tags=["Redirect"],
    status_code=status.HTTP_308_PERMANENT_REDIRECT,
)
async def api() -> RedirectResponse:
    """Redirect to the Swagger docs"""
    return RedirectResponse(url="/api/docs")


@app.get(
    "/api/health",
    response_model=Message,
    tags=["Health"],
    status_code=status.HTTP_200_OK,
)
async def get_health() -> Message:
    """Return a health check."""
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
    sources_file: str = os.path.join(DATA_PATH, "sources.json")
) -> List[Source]:
    """Return sources from the provided file"""
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
    return IngestProgress(**get_progress_response(task_id, "ingest"))


@app.get(
    "/api/ingest/progress",
    response_model=Dict[str, IngestProgress],
    tags=["Ingest"],
    status_code=status.HTTP_200_OK,
)
async def get_all_ingest_progress() -> Dict[str, IngestProgress]:
    """Get all ingest progress tasks"""
    return {
        task_id: IngestProgress(**progress)
        for task_id, progress in get_progress("ingest").items()
    }


@app.get(
    "/api/download/progress/{task_id}",
    response_model=DownloadProgress,
    tags=["Download"],
    status_code=status.HTTP_200_OK,
)
async def get_download_progress_by_id(task_id: str) -> DownloadProgress:
    """Get download progress for a specific task"""
    return DownloadProgress(**get_progress_response(task_id, "download"))


@app.get(
    "/api/download/progress",
    response_model=Dict[str, DownloadProgress],
    tags=["Download"],
    status_code=status.HTTP_200_OK,
)
async def get_all_download_progress() -> Dict[str, DownloadProgress]:
    """Get all download progress tasks"""
    return {
        task_id: DownloadProgress(**progress)
        for task_id, progress in get_progress("download").items()
    }


@app.delete(
    "/api/download/cancel/{task_id}",
    response_model=Message,
    tags=["Download"],
    status_code=status.HTTP_200_OK,
)
async def cancel_download(task_id: str) -> Message:
    """Cancel a download task by task ID"""
    try:
        from common.state import cancel_download_task

        success = cancel_download_task(task_id)
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
            create_download_task(task_id, 1)

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
    try:
        # Create unique task ID for each source
        task_id = create_task_id(source_name, file_type, "download")

        # Create download task (1 item per task)
        create_download_task(task_id, 1)

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
        task_id = create_task_id(source_name, file_type, "load")

        # Estimate total items (rough estimate for progress tracking)
        # We'll update this with actual counts during parsing
        estimated_items = 1000000 if file_type == "epg" else 500000

        create_ingest_task(task_id, file_type, estimated_items, source_name)

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
    """Background task to load file data into database with progress tracking"""
    session = SessionLocal()
    try:
        # Start the task
        start_ingest_task(task_id)
        logger.info(
            f"Started background load task {task_id} for {file_type} file: {file_path}"
        )

        # Count total items for accurate progress tracking
        total_processed = 0

        # Load data using async generators with task tracking
        if file_type == "m3u":
            async for result in load_m3u_file_async(
                session, file_path, source_name, task_id
            ):
                total_processed += 1
                if result.status == "error":
                    logger.warning(f"Load error in task {task_id}: {result.message}")
        elif file_type == "epg":
            async for result in load_epg_file_async(
                session, file_path, source_name, task_id
            ):
                total_processed += 1
                if result.status == "error":
                    logger.warning(f"Load error in task {task_id}: {result.message}")

        # Complete the task
        complete_ingest_task(
            task_id,
            f"Successfully loaded {total_processed} records from {file_type.upper()} file",
        )
        logger.info(
            f"Completed background load task {task_id}: {total_processed} records processed"
        )

    except Exception as e:
        logger.error(f"Background load task {task_id} failed: {e}")
        fail_ingest_task(task_id, str(e))
        session.rollback()
    finally:
        session.close()


@app.get(
    "/api/db/{table}/head",
    response_model=List[Dict[str, Any]],
    tags=["Database"],
    status_code=status.HTTP_200_OK,
)
async def get_db_table_head(table: str) -> List[Dict[str, Any]]:
    """Return the first 10 rows of a table"""
    with SessionLocal() as session:
        result = session.execute(text(f"SELECT * FROM {table} LIMIT 10"))
        return result.fetchall()


@app.get(
    "/api/tables/{table_name}",
    response_model=Dict[str, Any],
    tags=["Database"],
    status_code=status.HTTP_200_OK,
)
async def get_table_data(
    table_name: str,
    source: str = None,
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
            count_query = f"SELECT COUNT(*) FROM {table_name}"

            # Add source filtering if provided
            params = {}
            if source:
                base_query += " WHERE source = :source"
                count_query += " WHERE source = :source"
                params["source"] = source

            # Add ordering and pagination
            base_query += " ORDER BY id ASC"

            # Execute queries
            total_result = session.execute(text(count_query), params)
            total_count = total_result.scalar()

            data_result = session.execute(text(base_query), params)
            records = [dict(row._mapping) for row in data_result]

            return {
                "success": True,
                "data": {
                    "records": records,
                    "total": total_count,
                    "table_name": table_name,
                    "source_filter": source,
                },
            }

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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1314)
