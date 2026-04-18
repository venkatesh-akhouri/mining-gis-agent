from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import geopandas as gpd
import fiona
import json
import urllib.request
import ssl

app = FastAPI(title="Mining GIS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GPKG_PATH = "clean_mining_data.gpkg"

LAYER_COMMODITY_COLS = {
    "INDOPAC_Mineral_Exploration":    ["commodity_1","commodity_2","commodity_3","commodity_4","commodity_5","commodity_6"],
    "INDOPAC_Mineral_Facilities":     ["commodity","commodity_product"],
    "INDOPAC_Mineral_Resources_Coal": ["commodity"],
    "INDOPAC_Mineral_Resources_Copper": ["commodity"],
    "INDOPAC_OG_Provinces_Continuous":  [],
    "INDOPAC_OG_Provinces_Conventional":[],
    "INDOPAC_OG_Resources_Recoverable": [],
    "INDOPAC_Mineral_Development":    ["commodity_1","commodity_2","commodity_3","commodity_4","commodity_5","commodity_6"],
}

LAYER_NAME_FIELD = {
    "INDOPAC_Mineral_Exploration":    "site_name",
    "INDOPAC_Mineral_Facilities":     "facility_name",
    "INDOPAC_Mineral_Resources_Coal": "resource_name",
    "INDOPAC_Mineral_Resources_Copper": "tract_name",
    "INDOPAC_OG_Provinces_Continuous":  "province_name",
    "INDOPAC_OG_Provinces_Conventional":"province_name",
    "INDOPAC_OG_Resources_Recoverable": "country_short_form",
    "INDOPAC_Mineral_Development":    "site_name",
}

LAYER_COUNTRY_FIELD = {
    "INDOPAC_Mineral_Exploration":    "country_short_form",
    "INDOPAC_Mineral_Facilities":     "country_short_form",
    "INDOPAC_Mineral_Resources_Coal": "country_short_form",
    "INDOPAC_Mineral_Resources_Copper":"country_short_form",
    "INDOPAC_OG_Provinces_Continuous":  None,
    "INDOPAC_OG_Provinces_Conventional":None,
    "INDOPAC_OG_Resources_Recoverable": "country_short_form",
    "INDOPAC_Mineral_Development":    "country_name",
}


def _primary_commodity(row, comm_cols):
    for col in comm_cols:
        val = str(row.get(col, "")).strip()
        if val and val.lower() not in ("nan", "none", ""):
            return val
    return "Unknown"


@app.get("/api/layers")
def get_layers():
    return fiona.listlayers(GPKG_PATH)


@app.get("/api/layers/{layer_name}/meta")
def get_meta(layer_name: str):
    layers = fiona.listlayers(GPKG_PATH)
    if layer_name not in layers:
        raise HTTPException(404, "Layer not found")
    return {
        "commodity_cols":  LAYER_COMMODITY_COLS.get(layer_name, []),
        "name_field":      LAYER_NAME_FIELD.get(layer_name),
        "country_field":   LAYER_COUNTRY_FIELD.get(layer_name),
    }


@app.get("/api/layers/{layer_name}/commodities")
def get_commodities(layer_name: str):
    layers = fiona.listlayers(GPKG_PATH)
    if layer_name not in layers:
        raise HTTPException(404, "Layer not found")
    gdf = gpd.read_file(GPKG_PATH, layer=layer_name)
    comm_cols = LAYER_COMMODITY_COLS.get(layer_name, [])
    seen = set()
    for col in comm_cols:
        if col in gdf.columns:
            vals = gdf[col].dropna().astype(str).str.strip()
            vals = vals[(vals != "") & (vals.str.lower() != "nan") & (vals.str.lower() != "none")]
            seen.update(vals.unique())
    return sorted(seen)


@app.get("/api/layers/{layer_name}/geojson")
def get_geojson(layer_name: str):
    layers = fiona.listlayers(GPKG_PATH)
    if layer_name not in layers:
        raise HTTPException(404, "Layer not found")
    gdf = gpd.read_file(GPKG_PATH, layer=layer_name)
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    comm_cols = LAYER_COMMODITY_COLS.get(layer_name, [])
    name_field = LAYER_NAME_FIELD.get(layer_name, "")
    country_field = LAYER_COUNTRY_FIELD.get(layer_name, "")

    gdf["_primary_commodity"] = gdf.apply(
        lambda r: _primary_commodity(r, comm_cols), axis=1
    )
    gdf["_name"]    = gdf[name_field].astype(str)    if name_field    and name_field    in gdf.columns else ""
    gdf["_country"] = gdf[country_field].astype(str) if country_field and country_field in gdf.columns else ""

    all_comms = []
    for col in comm_cols:
        if col in gdf.columns:
            all_comms.append(col)
    gdf["_all_commodities"] = gdf.apply(
        lambda r: ", ".join(
            v for col in all_comms
            if (v := str(r.get(col,"")).strip()) and v.lower() not in ("nan","none","")
        ), axis=1
    )

    keep = ["geometry","_primary_commodity","_name","_country","_all_commodities"]
    return json.loads(gdf[keep].to_json())


@app.get("/tiles/{z}/{x}/{y}")
def get_tile(z: int, x: int, y: int):
    url = f"https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        data = r.read()
    return Response(content=data, media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})


# Serve frontend — must be last
app.mount("/", StaticFiles(directory="static", html=True), name="static")
