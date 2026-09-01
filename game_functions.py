from container_management import *
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import geopandas as gpd
from shapely.geometry import Point

conn = st.connection("gsheets", type=GSheetsConnection)

def save_container(container: Container) -> bool:
    container_key = container.name
    json_string = container.to_json(indent=None)

    df = conn.read(worksheet="container_mgmt", ttl=0)
    mask = df["container_key"] == container_key

    if mask.any():
        df.loc[mask, ["json", "updated_at"]] = [json_string, pd.Timestamp.now(tz="UTC")]

        conn.update(worksheet="container_mgmt", data=df)
        return True

    return False


def load_container(container_key: str) -> Container:
    df = conn.read(worksheet="container_mgmt", ttl=0)
    mask = df["container_key"] == container_key

    if mask.any():
        return Container.from_json(df.loc[mask, "json"].iloc[0])
    
    return None

def initialise_core_components() -> dict:
    specs = [
        ("challenge_deck", "cards", 100),
        ("reward_deck", "cards", 100),
        ("discard_deck", "cards", 100),
        ("global_challenges", "cards", 5),
        ("unclaimed_areas", "areas", 15),
    ]
    return {
        name: Container(name=name, type=type_, max_items=max_items)
        for name, type_, max_items in specs
    }

def initialise_teams(teams: Dict[str, List[str]]) -> Dict[str, Team]:
    return {
        name: Team(
            name=name, 
            players=Container(
                name=f"{name}_players", type="players", max_items=5, 
                items=player_list
            )
        )
        for name, player_list in teams.items()
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
