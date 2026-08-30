# Import modules
import geopandas as gpd
import shapely
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

# Define EH postal districts of interest
EH_DISTS = [
    f"EH{i}" for i in [*range(1, 13), 16]
]

# Read geospatial files
postal_polygons = gpd.read_file(
    "MapData/Initial/PostalDistrict.shp"
).to_crs(epsg=4326)[["PostDist", "geometry"]]
boundary = gpd.read_file(
    "MapData/Initial/Boundary.geojson"
).to_crs(epsg=4326)
eh3_lines = gpd.read_file(
    "MapData/Initial/EH3SplitLines.geojson"
).to_crs(epsg=4326)
boundary_centre = gpd.GeoDataFrame(
    geometry=[shapely.geometry.Point(-3.1932798, 55.9523657)],
    crs="EPSG:4326"
)

# Filter UK postal districts
eh_polygons = postal_polygons[postal_polygons["PostDist"].isin(EH_DISTS)]

# Clip districts using the boundary
clipped_eh_polygons = gpd.clip(eh_polygons, boundary)

# Split irregular EH3 district into subdistricts using eh3_lines
eh3_clipped = clipped_eh_polygons[clipped_eh_polygons["PostDist"] == "EH3"]
eh3_clipped_geom = eh3_clipped.geometry.iloc[0]
line_splitter = shapely.union_all(eh3_lines.geometry)

split_output = shapely.ops.split(eh3_clipped_geom, line_splitter)

eh3_clipped_split = gpd.GeoDataFrame(
    geometry=list(split_output.geoms), 
    crs="EPSG:4326"
)

eh3_clipped_split = eh3_clipped_split.assign(
    centroid_y=eh3_clipped_split.geometry.centroid.y
).sort_values("centroid_y", ascending=False).reset_index(drop=True)
eh3_clipped_split["PostDist"] = ["EH3a", "EH3b", "EH3c"]
eh3_clipped_split = eh3_clipped_split.drop(columns=["centroid_y"])

# Merge original EH polygons with EH3 subdistricts
clipped_eh_polygons = gpd.GeoDataFrame(
    pd.concat(
        [
            clipped_eh_polygons[clipped_eh_polygons["PostDist"] != "EH3"],
            eh3_clipped_split
        ],
        ignore_index=True
    ),
    crs="EPSG:4326"
)

# Assign game-related properties to the polygons
clipped_eh_polygons["relative_area"] = clipped_eh_polygons.geometry.area
clipped_eh_polygons["relative_centroid_dist"] = (
    clipped_eh_polygons.geometry.centroid.distance(
        boundary_centre.geometry.iloc[0]
    )
)
scaler = MinMaxScaler(feature_range=(1, 10))
clipped_eh_polygons[["relative_area", "relative_centroid_dist"]] = scaler.fit_transform(
    clipped_eh_polygons[["relative_area", "relative_centroid_dist"]]
)
clipped_eh_polygons["control"] = "Unclaimed"
clipped_eh_polygons["is_protected"] = False
clipped_eh_polygons["protection_start"] = None
clipped_eh_polygons["protection_end"] = None

clipped_eh_geometry = clipped_eh_polygons[["PostDist", "geometry", "relative_area", "relative_centroid_dist"]]
clipped_eh_attributes = clipped_eh_polygons.drop(columns=["geometry", "relative_area", "relative_centroid_dist"])

clipped_eh_geometry.to_file(
    "MapData/Board/GameBoard.geojson", driver="GeoJSON"
)
clipped_eh_attributes.to_csv("area_initial_attributes.csv", index=False)