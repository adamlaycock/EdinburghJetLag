import geopandas as gpd
import matplotlib.pyplot as plt

polygons = gpd.read_file(
    "MapData/PostalDistrict.shp"
)
polygons = polygons[polygons["PostArea"] == "EH"]
dists = ["EH1", "EH2", "EH3", "EH4", "EH5", "EH6", "EH7", "EH8", "EH9", "EH10", "EH11", "EH12", "EH16"]
polygons = polygons[polygons["PostDist"].isin(dists)]
boundary = gpd.read_file(
    "MapData/Boundary.geojson"
)

if polygons.crs != boundary.crs:
    boundary = boundary.to_crs(polygons.crs)

clipped_polygons = gpd.clip(polygons, boundary)

clipped_polygons.explore(
    tiles="OpenStreetMap",
    style_kwds={
        "fillColor": "lightblue",
        "color": "black",
        "fillOpacity": 0.5,
        "weight": 1
    },
    tooltip="PostDist",
    popup=True
)
