import streamlit as st
import geopandas as gpd
import fiona
import folium
from streamlit_folium import st_folium
import pandas as pd
import colorsys

GPKG_PATH = "clean_mining_data.gpkg"

# Commodity columns per layer
LAYER_COMMODITY_COLS = {
    "INDOPAC_Mineral_Exploration": ["commodity_1", "commodity_2", "commodity_3", "commodity_4", "commodity_5", "commodity_6"],
    "INDOPAC_Mineral_Facilities": ["commodity", "commodity_product"],
    "INDOPAC_Mineral_Resources_Coal": ["commodity"],
    "INDOPAC_Mineral_Resources_Copper": ["commodity"],
    "INDOPAC_OG_Provinces_Continuous": [],
    "INDOPAC_OG_Provinces_Conventional": [],
    "INDOPAC_OG_Resources_Recoverable": [],
    "INDOPAC_Mineral_Development": ["commodity_1", "commodity_2", "commodity_3", "commodity_4", "commodity_5", "commodity_6"],
}

# Primary name field per layer (for popups/tooltips)
LAYER_NAME_FIELD = {
    "INDOPAC_Mineral_Exploration": "site_name",
    "INDOPAC_Mineral_Facilities": "facility_name",
    "INDOPAC_Mineral_Resources_Coal": "resource_name",
    "INDOPAC_Mineral_Resources_Copper": "tract_name",
    "INDOPAC_OG_Provinces_Continuous": "province_name",
    "INDOPAC_OG_Provinces_Conventional": "province_name",
    "INDOPAC_OG_Resources_Recoverable": "country_short_form",
    "INDOPAC_Mineral_Development": "site_name",
}

# Country field per layer
LAYER_COUNTRY_FIELD = {
    "INDOPAC_Mineral_Exploration": "country_short_form",
    "INDOPAC_Mineral_Facilities": "country_short_form",
    "INDOPAC_Mineral_Resources_Coal": "country_short_form",
    "INDOPAC_Mineral_Resources_Copper": "country_short_form",
    "INDOPAC_OG_Provinces_Continuous": None,
    "INDOPAC_OG_Provinces_Conventional": None,
    "INDOPAC_OG_Resources_Recoverable": "country_short_form",
    "INDOPAC_Mineral_Development": "country_name",
}

# Fixed colors for well-known commodities
KNOWN_COMMODITY_COLORS = {
    "gold":           "#FFD700",
    "copper":         "#FF6B35",
    "coal":           "#8D8D8D",
    "natural gas":    "#00CFFF",
    "oil":            "#A0522D",
    "iron":           "#C0392B",
    "nickel":         "#50E3C2",
    "zinc":           "#7ED321",
    "lead":           "#BD10E0",
    "silver":         "#C0C0C0",
    "chromium":       "#F5A623",
    "manganese":      "#9013FE",
    "bauxite":        "#D0021B",
    "lithium":        "#4A90E2",
    "molybdenum":     "#B8E986",
    "uranium":        "#39FF14",
    "tin":            "#FFC0CB",
    "tungsten":       "#FF4500",
    "platinum":       "#E8D5B7",
    "cobalt":         "#0080FF",
    "phosphate":      "#ADFF2F",
    "potash":         "#FF69B4",
}

# Fallback palette for unlisted commodities (visually distinct bright colors)
_FALLBACK_PALETTE = [
    "#FF3CAC", "#784BA0", "#2B86C5", "#43E97B", "#FA8231",
    "#F9CA24", "#6C5CE7", "#00CEC9", "#E17055", "#FDCB6E",
    "#A29BFE", "#55EFC4", "#FD79A8", "#E84393", "#00B894",
]


def get_commodity_color_map(commodities: list[str]) -> dict[str, str]:
    """Return a stable commodity → hex-color mapping."""
    color_map = {}
    fallback_idx = 0
    for comm in sorted(commodities):
        key = comm.lower().strip()
        if key in KNOWN_COMMODITY_COLORS:
            color_map[comm] = KNOWN_COMMODITY_COLORS[key]
        else:
            color_map[comm] = _FALLBACK_PALETTE[fallback_idx % len(_FALLBACK_PALETTE)]
            fallback_idx += 1
    return color_map


def get_primary_commodity(row, layer_name: str) -> str:
    """Return the first non-empty commodity value for a feature."""
    comm_cols = LAYER_COMMODITY_COLS.get(layer_name, [])
    for col in comm_cols:
        val = str(row.get(col, "")).strip()
        if val and val.lower() not in ("", "nan", "none"):
            return val
    return "Unknown"


@st.cache_data
def get_layer_names():
    return fiona.listlayers(GPKG_PATH)


@st.cache_data
def load_layer(layer_name):
    gdf = gpd.read_file(GPKG_PATH, layer=layer_name)
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    return gdf


@st.cache_data
def get_commodities(layer_name):
    gdf = load_layer(layer_name)
    comm_cols = LAYER_COMMODITY_COLS.get(layer_name, [])
    commodities = set()
    for col in comm_cols:
        if col in gdf.columns:
            vals = gdf[col].dropna().astype(str).str.strip()
            vals = vals[vals != "" ][vals != "nan"]
            commodities.update(vals.unique())
    return sorted(commodities)


def filter_by_commodities(gdf, layer_name, selected):
    if not selected:
        return gdf
    comm_cols = LAYER_COMMODITY_COLS.get(layer_name, [])
    if not comm_cols:
        return gdf
    mask = pd.Series(False, index=gdf.index)
    for col in comm_cols:
        if col in gdf.columns:
            stripped = gdf[col].astype(str).str.strip()
            mask = mask | stripped.isin(selected)
    return gdf[mask]


def build_point_popup(row, layer_name):
    name_field = LAYER_NAME_FIELD.get(layer_name, "")
    country_field = LAYER_COUNTRY_FIELD.get(layer_name)
    comm_cols = LAYER_COMMODITY_COLS.get(layer_name, [])

    name = str(row.get(name_field, "")) if name_field else ""
    country = str(row.get(country_field, "")) if country_field else ""

    comms = []
    for col in comm_cols:
        val = str(row.get(col, "")).strip()
        if val and val != "nan":
            comms.append(val)

    html = f"<div style='font-family:sans-serif;min-width:180px'>"
    if name and name != "nan":
        html += f"<b style='font-size:14px'>{name}</b><br>"
    if country and country != "nan":
        html += f"<span style='color:#555'>Country:</span> {country}<br>"
    if comms:
        html += f"<span style='color:#555'>Commodities:</span> {', '.join(comms)}"
    html += "</div>"

    return folium.Popup(html, max_width=320)


def build_map(gdf, layer_name, color_map: dict[str, str]):
    bounds = gdf.geometry.total_bounds  # (minx, miny, maxx, maxy)
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=4,
        tiles="CartoDB dark_matter",
    )

    # Fit bounds
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

    geom_types = gdf.geometry.geom_type.dropna().unique().tolist()
    is_point = any("Point" in g for g in geom_types)

    comm_cols = LAYER_COMMODITY_COLS.get(layer_name, [])
    has_commodities = bool(comm_cols)

    if is_point:
        for _, row in gdf.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue
            popup = build_point_popup(row, layer_name)
            primary = get_primary_commodity(row, layer_name)
            c = color_map.get(primary, "#FFFFFF")
            folium.CircleMarker(
                location=[geom.y, geom.x],
                radius=6,
                color=c,
                fill=True,
                fill_color=c,
                fill_opacity=0.85,
                weight=1.5,
                popup=popup,
                tooltip=str(row.get(LAYER_NAME_FIELD.get(layer_name, ""), "")),
            ).add_to(m)
    else:
        name_field = LAYER_NAME_FIELD.get(layer_name, "")
        country_field = LAYER_COUNTRY_FIELD.get(layer_name)

        # Build popup fields list (only those that exist in gdf)
        popup_fields = []
        popup_aliases = []
        for f, label in (
            [(name_field, "Name")] if name_field and name_field in gdf.columns else []
        ) + (
            [(country_field, "Country")] if country_field and country_field in gdf.columns else []
        ) + [
            (c, c.replace("_", " ").title()) for c in comm_cols if c in gdf.columns
        ]:
            popup_fields.append(f)
            popup_aliases.append(label + ":")

        tooltip_fields = [name_field] if name_field and name_field in gdf.columns else []

        def style_fn(feature):
            comm = "Unknown"
            props = feature.get("properties", {})
            for col in comm_cols:
                val = str(props.get(col, "")).strip()
                if val and val.lower() not in ("", "nan", "none"):
                    comm = val
                    break
            c = color_map.get(comm, "#3498DB")
            return {"fillColor": c, "color": "#FFFFFF", "weight": 0.6, "fillOpacity": 0.55}

        def highlight_fn(feature):
            props = feature.get("properties", {})
            comm = "Unknown"
            for col in comm_cols:
                val = str(props.get(col, "")).strip()
                if val and val.lower() not in ("", "nan", "none"):
                    comm = val
                    break
            c = color_map.get(comm, "#3498DB")
            return {"fillColor": c, "color": "#FFFFFF", "weight": 2.5, "fillOpacity": 0.85}

        folium.GeoJson(
            gdf,
            style_function=style_fn,
            highlight_function=highlight_fn,
            tooltip=folium.GeoJsonTooltip(
                fields=tooltip_fields,
                aliases=["Name:"] if tooltip_fields else [],
                localize=True,
            ) if tooltip_fields else None,
            popup=folium.GeoJsonPopup(
                fields=popup_fields,
                aliases=popup_aliases,
                localize=True,
                max_width=420,
            ) if popup_fields else None,
        ).add_to(m)

    # ── Legend ────────────────────────────────────────────────────────────────
    if color_map:
        legend_items = "".join(
            f"<div style='display:flex;align-items:center;margin:3px 0'>"
            f"<span style='display:inline-block;width:14px;height:14px;border-radius:50%;"
            f"background:{clr};margin-right:8px;flex-shrink:0'></span>"
            f"<span style='font-size:12px;color:#ddd'>{comm}</span></div>"
            for comm, clr in sorted(color_map.items())
        )
        legend_html = f"""
        <div style='position:fixed;bottom:30px;left:30px;z-index:9999;
                    background:#1a1a2e;border:1px solid #444;border-radius:8px;
                    padding:12px 16px;max-height:320px;overflow-y:auto;
                    box-shadow:0 4px 16px rgba(0,0,0,0.6)'>
          <b style='color:#fff;font-size:13px;font-family:sans-serif'>Commodities</b>
          <div style='margin-top:8px;font-family:sans-serif'>{legend_items}</div>
        </div>"""
        m.get_root().html.add_child(folium.Element(legend_html))

    return m


# ── Streamlit UI ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="Mining GIS Viewer", page_icon="⛏", layout="wide")

st.title("⛏ Indo-Pacific Mining GIS Viewer")
st.caption("Interactive visualization of mineral development, exploration, and resources.")

layer_names = get_layer_names()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Layer & Filters")

    selected_layer = st.selectbox(
        "Select Layer",
        layer_names,
        help="Choose which GIS layer to display on the map.",
    )

    commodity_list = get_commodities(selected_layer)

    selected_commodities = []
    if commodity_list:
        st.subheader("Commodity Filter")
        st.caption(f"{len(commodity_list)} commodities in this layer")

        select_all = st.checkbox("Show all commodities", value=True)
        if select_all:
            selected_commodities = commodity_list
        else:
            selected_commodities = st.multiselect(
                "Select commodities",
                options=commodity_list,
                default=[],
                placeholder="Choose one or more...",
            )
    else:
        st.info("No commodity data for this layer.")
        selected_commodities = []

# ── Load & filter ─────────────────────────────────────────────────────────────
gdf = load_layer(selected_layer)

has_commodity_filter = bool(LAYER_COMMODITY_COLS.get(selected_layer))

if has_commodity_filter and selected_commodities:
    filtered = filter_by_commodities(gdf, selected_layer, selected_commodities)
elif has_commodity_filter and not selected_commodities:
    filtered = gdf.iloc[0:0]  # empty — no selection made
else:
    filtered = gdf

# ── Stats row ─────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
col1.metric("Layer", selected_layer.replace("INDOPAC_", ""))
col2.metric("Total features", len(gdf))
col3.metric("Displayed", len(filtered))

# ── Map ───────────────────────────────────────────────────────────────────────
# Build color map from the currently visible commodities
all_comms = get_commodities(selected_layer)
color_map = get_commodity_color_map(all_comms) if all_comms else {}

if len(filtered) == 0:
    if has_commodity_filter and not selected_commodities:
        st.info("Select at least one commodity in the sidebar to display features.")
    else:
        st.warning("No features match the selected commodity filters.")
else:
    with st.spinner("Rendering map..."):
        m = build_map(filtered, selected_layer, color_map)
    st_folium(m, width="100%", height=650, returned_objects=[])
