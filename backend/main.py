from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from typing import Optional, Dict, List
import uvicorn
import json
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

app = FastAPI(
    title="ISeeTV API",
    description="ISeeTV API",
    version="0.1.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
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

DATA_PATH = "/app/data"


class Message(BaseModel):
    message: str


class Source(BaseModel):
    name: str
    m3u_url: str
    epg_url: Optional[str]
    number_of_connections: Optional[int]
    refresh_every_hours: Optional[int]
    subscription_expires: Optional[str]
    source_timezone: Optional[str]
    enabled: bool


class GlobalSettings(BaseModel):
    user_timezone: str
    program_cache_days: int
    theme: str


@app.get("/", response_model=Message, tags=["Meta"])
async def root():
    """Redirect to the Swagger docs"""
    return RedirectResponse(url="/api/docs")


@app.get("/docs", response_model=Message, tags=["Meta"])
async def docs():
    """Redirect to the Swagger docs"""
    return RedirectResponse(url="/api/docs")


@app.get("/api", response_model=Message, tags=["Meta"])
async def api():
    """Redirect to the Swagger docs"""
    return RedirectResponse(url="/api/docs")


@app.get("/api/health", response_model=Message, tags=["Health"])
async def get_health():
    """Return a health check."""
    return Message(message="ok")


@app.get("/api/settings", response_model=GlobalSettings, tags=["Settings"])
async def get_settings(settings_file: str = f"{DATA_PATH}/settings.json"):
    """Return settings from the provided file"""
    try:
        with open(settings_file, "r") as f:
            return GlobalSettings(**json.load(f))
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/settings", response_model=Message, tags=["Settings"])
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


@app.get("/api/sources", response_model=List[Source], tags=["Sources"])
async def get_sources(sources_file: str = f"{DATA_PATH}/sources.json"):
    """Return sources from the provided file"""
    try:
        with open(sources_file, "r") as f:
            return [Source(**source) for source in json.load(f)]
    except (FileNotFoundError, json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sources", response_model=Message, tags=["Sources"])
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1314)
