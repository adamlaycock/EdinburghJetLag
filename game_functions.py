from container_management import *
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import geopandas as gpd
from shapely.geometry import Point

conn = st.connection("gsheets", type=GSheetsConnection)

###############################################################################
# Functions for communicating with "team_mgmt"
###############################################################################

@st.cache_data(ttl=5) 
def get_teams_data():
    df = conn.read(worksheet='team_mgmt')
    if df.empty:
        return pd.DataFrame({
            "team_name": [],
            "player_name": []
        })
    else:
        return df

def clear_team_data(team_name: str) -> None:
    current_team_data = get_teams_data()

    new_team_data = current_team_data[current_team_data["team_name"]!=team_name]

    conn.update(worksheet="team_mgmt", data=new_team_data)
    st.cache_data.clear()

###############################################################################
# Functions for communicating with "container_mgmt"
###############################################################################

def save_containers(containers: dict[str, Container]) -> None:
    df = conn.read(worksheet="container_mgmt", ttl=0)
    df["json"] = df["json"].astype("object")

    for container in containers.values():
        container_key = container.name
        json_string = container.to_json(indent=None)

        mask = df["container_key"] == container_key

        if mask.any():
            df.loc[mask, "json"] = json_string

    conn.update(worksheet="container_mgmt", data=df)

    load_containers.clear()

@st.cache_data(ttl=5)
def load_containers() -> Dict[str, Container]:
    df = conn.read(worksheet="container_mgmt", ttl=0)

    return {
        row["container_key"]: Container.from_json(row["json"])
        for _, row in df.iterrows()
    }

###############################################################################
# Functions for starting the game
###############################################################################

def initialise_core_components(
    team_a_players: List[str],
    team_b_players: List[str],
    team_c_players: List[str],
) -> Dict[str, Container]:

    gdf = gpd.read_file("MapData/Board/GameBoard.geojson")
    gdf_areas = [
        Area(
            name=name,
            area=area,
            distance=distance,
            geometry=geometry,
        )
        for name, area, distance, geometry in zip(
            gdf["name"],
            gdf["area"],
            gdf["distance"],
            gdf["geometry"],
        )
    ]
    
    specs = [
        ("challenge_deck", "cards", 100),
        ("reward_deck", "cards", 100),
        ("discard_deck", "cards", 100),
        ("global_challenges", "cards", 5),
        ("unclaimed_areas", "areas", 15),

        ("team_a_hand", "cards", 5),
        ("team_a_active", "cards", 1),
        ("team_a_players", "players", 5),
        ("team_a_areas", "areas", 15),

        ("team_b_hand", "cards", 5),
        ("team_b_active", "cards", 1),
        ("team_b_players", "players", 5),
        ("team_b_areas", "areas", 15),

        ("team_c_hand", "cards", 5),
        ("team_c_active", "cards", 1),
        ("team_c_players", "players", 5),
        ("team_c_areas", "areas", 15),
    ]

    player_items = {
        "team_a_players": team_a_players,
        "team_b_players": team_b_players,
        "team_c_players": team_c_players,
    }

    return {
        name: Container(
            name=name,
            type=type_,
            max_items=max_items,
            **(
                {"items": gdf_areas}
                if name == "unclaimed_areas"
                else {"items": player_items[name]}
                if name in player_items
                else {}
            ),
        )
        for name, type_, max_items in specs
    }

###############################################################################
# Functions identifying current area using geolocation
###############################################################################

def get_current_area(lat: float, lon: float, areas: gpd.GeoDataFrame) -> str:
    coords = Point(lon, lat)
    areas = areas.to_crs(epsg=4326)

    matching_polygon = areas[areas.contains(coords)]

    if not matching_polygon.empty:
        area_name = matching_polygon["area_name"].values[0]
        return area_name
    else:
        return None
