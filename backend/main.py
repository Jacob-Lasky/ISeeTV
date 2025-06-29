from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from typing import Dict, List, Literal
import uvicorn
import json
from fastapi import HTTPException, status
from fastapi.responses import RedirectResponse
import asyncio
import logging
from common.models import (
    DownloadProgress,
    Message,
    Source,
    GlobalSettings,
    DownloadTaskResponse,
    DownloadAllTasksResponse,
)
from common.download_helper import (
    create_download_task,
    background_single_download_task,
)
from common.state import get_download_progress
from common.utils import create_task_id

DATA_PATH = "/app/data"

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
        {"name": "Meta", "description": "Meta operations"},
        {"name": "Health", "description": "Health checks"},
        {"name": "Settings", "description": "Global app configuration"},
        {"name": "Sources", "description": "Manage IPTV sources (M3U, EPG, metadata)"},
        {"name": "Download", "description": "Download operations"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/",
    response_model=Message,
    tags=["Meta"],
    status_code=status.HTTP_308_PERMANENT_REDIRECT,
)
async def root():
    """Redirect to the Swagger docs"""
    return RedirectResponse(url="/api/docs")


@app.get(
    "/docs",
    response_model=Message,
    tags=["Meta"],
    status_code=status.HTTP_308_PERMANENT_REDIRECT,
)
async def docs():
    """Redirect to the Swagger docs"""
    return RedirectResponse(url="/api/docs")


@app.get(
    "/api",
    response_model=Message,
    tags=["Meta"],
    status_code=status.HTTP_308_PERMANENT_REDIRECT,
)
async def api():
    """Redirect to the Swagger docs"""
    return RedirectResponse(url="/api/docs")


@app.get(
    "/api/health",
    response_model=Message,
    tags=["Health"],
    status_code=status.HTTP_200_OK,
)
async def get_health():
    """Return a health check."""
    return Message(message="ok")


@app.get(
    "/api/settings",
    response_model=GlobalSettings,
    tags=["Settings"],
    status_code=status.HTTP_200_OK,
)
async def get_settings(settings_file: str = f"{DATA_PATH}/settings.json"):
    """Return settings from the provided file"""
    try:
        with open(settings_file, "r") as f:
            return GlobalSettings(**json.load(f))
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/settings",
    response_model=Message,
    tags=["Settings"],
    status_code=status.HTTP_201_CREATED,
)
async def set_settings(
    settings: GlobalSettings, settings_file: str = f"{DATA_PATH}/settings.json"
):
    """Set settings in the provided file"""
    try:
        with open(settings_file, "w") as f:
            json.dump(settings.dict(), f, indent=4)
        return Message(message="Settings saved successfully")
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/sources",
    response_model=List[Source],
    tags=["Sources"],
    status_code=status.HTTP_200_OK,
)
async def get_sources(sources_file: str = f"{DATA_PATH}/sources.json"):
    """Return sources from the provided file"""
    try:
        with open(sources_file, "r") as f:
            return [Source(**source) for source in json.load(f)]
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/api/sources",
    response_model=Message,
    tags=["Sources"],
    status_code=status.HTTP_201_CREATED,
)
async def set_sources(
    sources: List[Source], sources_file: str = f"{DATA_PATH}/sources.json"
):
    """Set sources in the provided file"""
    try:
        with open(sources_file, "w") as f:
            json.dump([source.dict() for source in sources], f, indent=4)
        return Message(message="Sources saved successfully")
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/download/progress/{task_id}",
    response_model=DownloadProgress,
    tags=["Download"],
    status_code=status.HTTP_200_OK,
)
async def get_download_progress_by_id(task_id: str):
    """Get download progress for a specific task"""
    download_progress = get_download_progress()
    if task_id not in download_progress:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return DownloadProgress(**download_progress[task_id])


@app.get(
    "/api/download/progress",
    response_model=Dict[str, DownloadProgress],
    tags=["Download"],
    status_code=status.HTTP_200_OK,
)
async def get_all_download_progress():
    """Get all download progress tasks"""
    download_progress = get_download_progress()
    return {
        task_id: DownloadProgress(**progress)
        for task_id, progress in download_progress.items()
    }


@app.delete(
    "/api/download/cancel/{task_id}",
    response_model=Message,
    tags=["Download"],
    status_code=status.HTTP_200_OK,
)
async def cancel_download(task_id: str):
    """Cancel a download task by task ID"""
    try:
        from common.state import cancel_download_task

        success = cancel_download_task(task_id)
        if success:
            return Message(message=f"Download task {task_id} cancelled successfully")
        else:
            raise HTTPException(
                status_code=404, detail=f"Task {task_id} not found or already completed"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/download/{file_type}/all",
    response_model=DownloadAllTasksResponse,
    tags=["Download"],
    status_code=status.HTTP_200_OK,
)
async def download_all_files(
    file_type: Literal["m3u", "epg"],
    sources_file: str = f"{DATA_PATH}/sources.json",
    download_dir: str = f"{DATA_PATH}/sources",
):
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
            task_id = create_task_id(source.name, file_type)
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
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/download/{file_type}/{source_name}",
    response_model=DownloadTaskResponse,
    tags=["Download"],
    status_code=status.HTTP_200_OK,
)
async def queue_file_for_download(
    file_type: Literal["m3u", "epg"],
    source_name: str,
    sources_file: str = f"{DATA_PATH}/sources.json",
    download_dir: str = f"{DATA_PATH}/sources",
):
    """Download file of a specific type for a specific source"""
    try:
        # Create unique task ID for each source
        task_id = create_task_id(source_name, file_type)

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
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/download/file/{source_name}/{file_type}",
    tags=["Download"],
    status_code=status.HTTP_200_OK,
)
async def download_file_stream(
    source_name: str,
    file_type: str,
    sources_file: str = f"{DATA_PATH}/sources.json",
):
    """Stream a file directly to the browser for download"""
    try:
        # Validate file type
        if file_type not in ["m3u", "epg"]:
            raise HTTPException(
                status_code=400, detail="Invalid file type. Must be 'm3u' or 'epg'"
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
                status_code=404, detail=f"Source '{source_name}' not found"
            )

        # Get file metadata
        file_metadata = source_data.get("file_metadata", {})
        file_info = file_metadata.get(file_type)

        if not file_info or not file_info.get("url"):
            raise HTTPException(
                status_code=404,
                detail=f"No {file_type.upper()} URL found for source '{source_name}'",
            )

        file_url = file_info["url"]

        # Stream the file from the remote URL
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Failed to fetch file from {file_url}",
                    )

                # Get content type and filename
                content_type = response.headers.get(
                    "content-type", "application/octet-stream"
                )
                filename = f"{source_name}_{file_type}.{file_type}"

                # Create streaming response
                from fastapi.responses import StreamingResponse

                async def generate():
                    async for chunk in response.content.iter_chunked(8192):
                        yield chunk

                return StreamingResponse(
                    generate(),
                    media_type=content_type,
                    headers={"Content-Disposition": f"attachment; filename={filename}"},
                )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Sources file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid sources file format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1314)
