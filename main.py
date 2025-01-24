import os
from typing import Dict
from fastapi import FastAPI, HTTPException, Query
from dotenv import load_dotenv
from geojson_pydantic import FeatureCollection
import httpx
import rasterio
from rasterio.mask import mask
import shapely
from starlette.middleware.cors import CORSMiddleware

load_dotenv()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
api_key = os.getenv("GEOAPIFY_API_KEY")
print(api_key)


async def get_isochrone(
    lat: float,
    lng: float,
    travel_time: int,
) -> FeatureCollection:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.geoapify.com/v1/isoline?lat={lat}&lon={lng}&type=time&mode=approximated_transit&range={travel_time}&apiKey={api_key}"
        )

        return FeatureCollection(**resp.json())


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
        geojson = await get_isochrone(lat, lng, travel_time)

        # Calculate the population within the isochrone
        pop = population_in_geojson(geojson)

        # Format the response GeoJSON with population data
        output = geojson_output(geojson, pop)
        return output
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
