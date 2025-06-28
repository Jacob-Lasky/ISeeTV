from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from typing import Dict, List
import uvicorn
import json
from fastapi import HTTPException, status
from fastapi.responses import RedirectResponse
import httpx
import asyncio
from datetime import datetime
import os
from common.models import DownloadProgress, Message, Source, GlobalSettings
from common.download_helper import (
    create_download_task,
    background_single_download_task,
    download_file,
)
from common.state import get_download_progress

DATA_PATH = "/app/data"

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
    "/api/download/all_m3u",
    response_model=Message,
    tags=["Sources"],
    status_code=status.HTTP_200_OK,
)
async def download_all_m3u(
    sources_file: str = f"{DATA_PATH}/sources.json",
    download_dir: str = f"{DATA_PATH}/sources",
):
    """Start background download of all M3U files - one task per source"""
    try:
        with open(sources_file, "r") as f:
            sources = [Source(**source) for source in json.load(f)]

        # Filter sources with M3U URLs in file_metadata
        m3u_sources = [
            source for source in sources 
            if source.get_file_metadata("m3u") and source.get_file_metadata("m3u").url
        ]

        if not m3u_sources:
            return Message(message="No sources with M3U URLs found")

        # Create individual tasks for each source
        task_ids = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for source in m3u_sources:
            # Create unique task ID for each source
            task_id = f"m3u_{source.name}_{timestamp}"
            task_ids.append(task_id)

            # Create download task (1 item per task)
            create_download_task(task_id, 1)

            # Start background download task for this source
            asyncio.create_task(
                background_single_download_task(
                    task_id, source.name, "m3u", sources_file, download_dir
                )
            )

        return Message(
            message=f"M3U downloads started for {len(task_ids)} sources. Task IDs: {', '.join(task_ids)}"
        )
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/download/m3u/{source_name}",
    response_model=Message,
    tags=["Sources"],
    status_code=status.HTTP_200_OK,
)
async def download_m3u(
    source_name: str,
    sources_file: str = f"{DATA_PATH}/sources.json",
    download_dir: str = f"{DATA_PATH}/sources",
):
    """Download M3U file for a specific source"""
    try:
        await download_file(source_name, "m3u", sources_file, download_dir)
        return Message(message=f"M3U file for {source_name} downloaded successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/download/all_epg",
    response_model=Message,
    tags=["Sources"],
    status_code=status.HTTP_200_OK,
)
async def download_all_epg(
    sources_file: str = f"{DATA_PATH}/sources.json",
    download_dir: str = f"{DATA_PATH}/sources",
):
    """Start background download of all EPG files - one task per source"""
    try:
        with open(sources_file, "r") as f:
            sources = [Source(**source) for source in json.load(f)]

        # Filter sources with EPG URLs in file_metadata
        epg_sources = [
            source for source in sources 
            if source.get_file_metadata("epg") and source.get_file_metadata("epg").url
        ]

        if not epg_sources:
            return Message(message="No sources with EPG URLs found")

        # Create individual tasks for each source
        task_ids = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for source in epg_sources:
            # Create unique task ID for each source
            task_id = f"epg_{source.name}_{timestamp}"
            task_ids.append(task_id)

            # Create download task (1 item per task)
            create_download_task(task_id, 1)

            # Start background download task for this source
            asyncio.create_task(
                background_single_download_task(
                    task_id, source.name, "epg", sources_file, download_dir
                )
            )

        return Message(
            message=f"EPG downloads started for {len(task_ids)} sources. Task IDs: {', '.join(task_ids)}"
        )
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/download/epg/{source_name}",
    response_model=Message,
    tags=["Sources"],
    status_code=status.HTTP_200_OK,
)
async def download_epg(
    source_name: str,
    sources_file: str = f"{DATA_PATH}/sources.json",
    download_dir: str = f"{DATA_PATH}/sources",
):
    """Download EPG file for a specific source"""
    try:
        await download_file(source_name, "epg", sources_file, download_dir)
        return Message(message=f"EPG file for {source_name} downloaded successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/download/progress/{task_id}",
    response_model=DownloadProgress,
    tags=["Sources"],
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
    tags=["Sources"],
    status_code=status.HTTP_200_OK,
)
async def get_all_download_progress():
    """Get all download progress tasks"""
    download_progress = get_download_progress()
    return {
        task_id: DownloadProgress(**progress)
        for task_id, progress in download_progress.items()
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1314)
