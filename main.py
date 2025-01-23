import os
from datetime import datetime
from typing import Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from geojson_pydantic import FeatureCollection
import rasterio
from rasterio.mask import mask
import shapely
from starlette.middleware.cors import CORSMiddleware
from traveltimepy import TravelTimeSdk, PublicTransport, Coordinates
from tzfpy import get_tz


load_dotenv()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IsochroneRequest(BaseModel):
    lat: float
    lng: float
    arrival_time: datetime
    travel_time: int


client = TravelTimeSdk(
    app_id=os.getenv("APP_ID") or "", api_key=os.getenv("API_KEY") or ""
)


async def get_isochrone(
    client: TravelTimeSdk,
    lat: float,
    lng: float,
    arrival_time: datetime,
    travel_time: int,
) -> FeatureCollection:
    arrival_time = arrival_time.replace(tzinfo=ZoneInfo(get_tz(lng, lat)))
    response = await client.time_map_geojson_async(
        coordinates=[Coordinates(lat=lat, lng=lng)],
        transportation=PublicTransport(),
        arrival_time=arrival_time,
        travel_time=travel_time,
    )
    return response


def population_in_geojson(geojson: FeatureCollection) -> int:
    geom = shapely.from_geojson(geojson.model_dump_json())
    with rasterio.open(os.getenv("GEOTIFF_URL")) as ds:
        inside, _ = mask(ds, shapes=[geom.buffer(0)], crop=True)
        return int(inside.sum())


def geojson_output(geom: FeatureCollection, pop: int) -> Dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": geom.model_dump()["features"][0]["geometry"],
                "properties": {"population": pop},
            }
        ],
    }


@app.post("/isochrone")
async def get_isochrone_data(request: IsochroneRequest):
    try:
        geojson = await get_isochrone(
            client, request.lat, request.lng, request.arrival_time, request.travel_time
        )
        pop = population_in_geojson(geojson)

        output = geojson_output(geojson, pop)
        return output
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
