import os
from typing import Dict
from fastapi import FastAPI, HTTPException, Query
from dotenv import load_dotenv
from geojson_pydantic import FeatureCollection
import rasterio
from rasterio.mask import mask
import shapely
from starlette.middleware.cors import CORSMiddleware
from traveltimepy import Transportation, TravelTimeSdk, Coordinates

load_dotenv()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the TravelTime SDK client
client = TravelTimeSdk(
    app_id=os.getenv("APP_ID") or "", api_key=os.getenv("API_KEY") or ""
)


async def get_isochrone(
    client: TravelTimeSdk,
    lat: float,
    lng: float,
    travel_time: int,
) -> FeatureCollection:
    response = await client.time_map_fast_geojson_async(
        coordinates=[Coordinates(lat=lat, lng=lng)],
        transportation=Transportation(type="public_transport"),
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


@app.get("/isochrone")
async def get_isochrone_data(
    lat: float = Query(..., description="Latitude of the location"),
    lng: float = Query(..., description="Longitude of the location"),
    travel_time: int = Query(..., description="Travel time in seconds"),
):
    """
    GET endpoint to retrieve an isochrone and calculate the population within it.
    """
    try:
        # Generate the isochrone GeoJSON
        geojson = await get_isochrone(client, lat, lng, travel_time)

        # Calculate the population within the isochrone
        pop = population_in_geojson(geojson)

        # Format the response GeoJSON with population data
        output = geojson_output(geojson, pop)
        return output
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
