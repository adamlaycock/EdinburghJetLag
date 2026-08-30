# Import modules
import geopandas as gpd
import streamlit as st
from streamlit_folium import st_folium
import matplotlib.colors as colors
import pandas as pd

# Read game board GeoJSON and format "control"
gdf = gpd.read_file(
    "MapData/Board/GameBoard.geojson"
).merge(pd.read_csv("area_initial_attributes.csv"), on="area_name", how="inner")
gdf["control"] = pd.Categorical(
    gdf["control"], 
    categories=["Team A", "Team B", "Team C", "Unclaimed"]
)

# Establish variables and functions for area styling
color_list = ["#FF0000", "#FFFF00", "#0000FF", "#808080"]
minx, miny, maxx, maxy = gdf.total_bounds

def style_status(feature):
    protection = feature["properties"].get("is_protected")

    if protection:
        return {
            "color": "#111111",
            "weight": 4,
            "fillOpacity": 0.75
        }
    else:
        return {
            "color": "black",
            "weight": 1.5,
            "fillOpacity": 0.25
        }

# Build game board map from GeoDataFrame
m = gdf.explore(
    column="control",
    cmap=color_list,
    categorical=True,
    tooltip=False,
    popup=["area_name", "control", "is_protected"],
    tiles="OpenStreetMap",
    style_kwds=dict(style_function=style_status),
)

# Set map boundaries and zoom limits
m.fit_bounds([[miny, minx], [maxy, maxx]])
m.options["maxBounds"] = [[miny, minx], [maxy, maxx]]
m.options["maxBoundsViscosity"] = 1
m.options["zoomSnap"] = 0.1
m.options["minZoom"] = 12.5

# Display map
st_folium(m, width=700, height=500, returned_objects=[])