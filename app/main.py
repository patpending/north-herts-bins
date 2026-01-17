"""
North Hertfordshire Bin Collection API Service

A FastAPI-based REST API for querying bin collection schedules.
Designed for standalone use and Home Assistant integration.
"""

import os
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .scraper import (
    NorthHertsBinCollection,
    NorthHertsBinCollectionError,
)


# Configuration
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))  # 1 hour default
DEFAULT_UPRN = os.getenv("DEFAULT_UPRN", "010070035296")


# Simple in-memory cache
class SimpleCache:
    def __init__(self, ttl: int = 3600):
        self.ttl = ttl
        self._cache: dict = {}

    def get(self, key: str):
        if key in self._cache:
            value, timestamp = self._cache[key]
            if (datetime.now() - timestamp).total_seconds() < self.ttl:
                return value
            del self._cache[key]
        return None

    def set(self, key: str, value):
        self._cache[key] = (value, datetime.now())

    def clear(self):
        self._cache.clear()


cache = SimpleCache(ttl=CACHE_TTL_SECONDS)
bin_client = NorthHertsBinCollection()


# Pydantic models for API documentation
class AddressResponse(BaseModel):
    uprn: str
    address: str
    postcode: str


class CollectionResponse(BaseModel):
    bin_type: str
    collection_date: str
    collection_date_formatted: str
    days_until: int


class CollectionsResponse(BaseModel):
    uprn: str
    address: Optional[str] = None
    collections: list[CollectionResponse]
    next_collection: Optional[CollectionResponse] = None
    last_updated: str


class HomeAssistantSensor(BaseModel):
    """Format compatible with Home Assistant REST sensor."""
    state: str = Field(description="Next collection bin type")
    days_until: int = Field(description="Days until next collection")
    next_date: str = Field(description="Next collection date")
    collections: list[CollectionResponse]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    yield
    cache.clear()


# Create FastAPI app
app = FastAPI(
    title="North Hertfordshire Bin Collection API",
    description="""
    API for querying bin collection schedules in North Hertfordshire.

    ## Features
    - Look up addresses by postcode
    - Get bin collection schedules by UPRN or address
    - Home Assistant compatible REST sensor endpoint
    - Caching to reduce API calls

    ## Usage
    1. Look up your address using `/api/addresses?postcode=YOUR_POSTCODE`
    2. Note the UPRN for your address
    3. Get collections using `/api/collections?uprn=YOUR_UPRN`

    ## Home Assistant Integration
    Use the `/api/homeassistant` endpoint with a REST sensor.
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# Get the directory containing this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


# API Routes

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the web interface."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/addresses", response_model=list[AddressResponse])
async def get_addresses(
    postcode: str = Query(..., description="UK postcode to search", examples=["SG6 1JF"])
):
    """
    Look up addresses by postcode.

    Returns a list of addresses with their UPRNs.
    """
    cache_key = f"addresses:{postcode}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        addresses = bin_client.lookup_addresses(postcode)
        result = [a.to_dict() for a in addresses]
        cache.set(cache_key, result)
        return result
    except NorthHertsBinCollectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@app.get("/api/collections", response_model=CollectionsResponse)
async def get_collections(
    uprn: Optional[str] = Query(None, description="Property UPRN"),
    postcode: Optional[str] = Query(None, description="UK postcode"),
    house_number: Optional[str] = Query(None, description="House number or name")
):
    """
    Get bin collection schedule for an address.

    Provide either:
    - `uprn` directly, OR
    - `postcode` AND `house_number`
    """
    if not uprn and not (postcode and house_number):
        raise HTTPException(
            status_code=400,
            detail="Either 'uprn' or both 'postcode' and 'house_number' are required"
        )

    cache_key = f"collections:{uprn or f'{postcode}:{house_number}'}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        collections = bin_client.get_collections(
            uprn=uprn,
            postcode=postcode,
            house_number=house_number
        )

        # Get resolved UPRN if we looked it up
        resolved_uprn = uprn
        if not resolved_uprn and postcode and house_number:
            resolved_uprn = bin_client.find_uprn(postcode, house_number)

        collection_dicts = [c.to_dict() for c in collections]

        # Find next collection
        now = datetime.now()
        next_collection = None
        for c in collections:
            if c.collection_date >= now:
                next_collection = c.to_dict()
                break

        result = {
            "uprn": resolved_uprn or "unknown",
            "collections": collection_dicts,
            "next_collection": next_collection,
            "last_updated": datetime.now().isoformat()
        }

        cache.set(cache_key, result)
        return result

    except NorthHertsBinCollectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@app.get("/api/homeassistant", response_model=HomeAssistantSensor)
async def homeassistant_sensor(
    uprn: Optional[str] = Query(None, description="Property UPRN"),
    postcode: Optional[str] = Query(None, description="UK postcode"),
    house_number: Optional[str] = Query(None, description="House number or name")
):
    """
    Home Assistant compatible REST sensor endpoint.

    Returns data formatted for use with Home Assistant's REST sensor platform.

    Example configuration.yaml:
    ```yaml
    sensor:
      - platform: rest
        name: "Bin Collection"
        resource: "http://localhost:8000/api/homeassistant?uprn=YOUR_UPRN"
        value_template: "{{ value_json.state }}"
        json_attributes:
          - days_until
          - next_date
          - collections
        scan_interval: 3600
    ```
    """
    collections_data = await get_collections(uprn, postcode, house_number)

    next_coll = collections_data.get("next_collection")
    if next_coll:
        return {
            "state": next_coll["bin_type"],
            "days_until": next_coll["days_until"],
            "next_date": next_coll["collection_date_formatted"],
            "collections": collections_data["collections"]
        }
    else:
        return {
            "state": "No upcoming collections",
            "days_until": -1,
            "next_date": "N/A",
            "collections": []
        }


@app.get("/api/next", response_model=CollectionResponse)
async def get_next_collection(
    uprn: Optional[str] = Query(None, description="Property UPRN"),
    postcode: Optional[str] = Query(None, description="UK postcode"),
    house_number: Optional[str] = Query(None, description="House number or name")
):
    """Get only the next upcoming bin collection."""
    collections_data = await get_collections(uprn, postcode, house_number)

    if collections_data.get("next_collection"):
        return collections_data["next_collection"]
    else:
        raise HTTPException(status_code=404, detail="No upcoming collections found")


class NextCollectionSensor(BaseModel):
    """Simple format for Home Assistant sensor."""
    state: str = Field(description="Next bin type")
    days: int = Field(description="Days until collection")
    date: str = Field(description="Collection date")
    last_updated: str = Field(description="Timestamp of last data fetch")


@app.get("/api/sensor/next", response_model=NextCollectionSensor)
async def next_collection_sensor(
    uprn: Optional[str] = Query(None, description="Property UPRN"),
    postcode: Optional[str] = Query(None, description="UK postcode"),
    house_number: Optional[str] = Query(None, description="House number or name")
):
    """
    Simple next collection sensor for Home Assistant.

    Returns just the essentials: bin type, days until, and date.

    Example Home Assistant configuration:
    ```yaml
    sensor:
      - platform: rest
        name: "Next Bin"
        resource: "http://localhost:8000/api/sensor/next?uprn=010070035296"
        value_template: "{{ value_json.state }}"
        json_attributes:
          - days
          - date
    ```
    """
    collections_data = await get_collections(uprn, postcode, house_number)
    next_coll = collections_data.get("next_collection")

    if next_coll:
        return {
            "state": next_coll["bin_type"],
            "days": next_coll["days_until"],
            "date": next_coll["collection_date_formatted"],
            "last_updated": datetime.now().isoformat()
        }
    else:
        return {
            "state": "None",
            "days": -1,
            "date": "N/A",
            "last_updated": datetime.now().isoformat()
        }


@app.get("/api/config")
async def get_config():
    """Get the default configuration."""
    return {"default_uprn": DEFAULT_UPRN}


@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/api/cache/clear")
async def clear_cache():
    """Clear the response cache."""
    cache.clear()
    return {"status": "cache cleared"}


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "detail": str(exc.detail) if hasattr(exc, 'detail') else None}
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )
