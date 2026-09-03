from container_management import *
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import geopandas as gpd
from shapely.geometry import Point
from streamlit_geolocation import streamlit_geolocation

conn = st.connection("gsheets", type=GSheetsConnection)

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

def initialise_core_components(
    team_a_players: List[str],
    team_b_players: List[str],
    team_c_players: List[str],
) -> Dict[str, Container]:
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
            **({"items": player_items[name]} if name in player_items else {}),
        )
        for name, type_, max_items in specs
    }

def get_current_area(lat: float, lon: float, board: gpd.GeoDataFrame) -> str:
    coords = Point(lon, lat)
    board = board.to_crs(epsg=4326)

    matching_polygon = board[board.contains(coords)]

    if not matching_polygon.empty:
        area_name = matching_polygon["area_name"].values[0]
        return area_name
    else:
        return None

