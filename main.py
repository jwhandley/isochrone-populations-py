import os
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from geojson_pydantic import FeatureCollection
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


def population_in_geojson(geojson: FeatureCollection) -> int:
    geom = shapely.from_geojson(geojson.model_dump_json())
    with rasterio.open(os.getenv("GEOTIFF_URL")) as ds:
        inside, _ = mask(ds, shapes=[geom.buffer(0)], crop=True)
        return int(inside.sum())


@app.post("/isochrone")
async def get_isochrone_data(geojson: FeatureCollection):
    try:
        pop = population_in_geojson(geojson)
        return pop
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
