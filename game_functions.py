from container_management import *
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import geopandas as gpd
from shapely.geometry import Point
from streamlit_geolocation import streamlit_geolocation

conn = st.connection("gsheets", type=GSheetsConnection)

def update_teams_data(new_team_data):
    conn.update(worksheet="team_mgmt", data=new_team_data)

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

@st.cache_data(ttl=30)
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
        ("challenged_areas", "areas", 15),

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

def get_current_coords() -> Point | None:
    geolocation = streamlit_geolocation()

    lat = geolocation.get("latitude")
    lon = geolocation.get("longitude")

    if lat is None or lon is None:
        return None
    
    return Point(lon, lat)

def get_current_area(position: Point) -> str | None:
    if position:
        gdf = gpd.read_file(
            "MapData/Board/GameBoard.geojson"
        ).to_crs("EPSG:4326")

        matching_polygon = gdf[gdf.geometry.covers(position)]

        if matching_polygon.empty:
            return None

        return matching_polygon.iloc[0]["name"]
    return None


def initialise_decks(mode: str) -> None:
    challenge_items = [
        ChallengeCard("challenge 1", "challenge 1 desc", "challenge", 3600),
        ChallengeCard("challenge 2", "challenge 2 desc", "challenge", 3600),
        ChallengeCard("challenge 3", "challenge 3 desc", "challenge", 3600),
        ChallengeCard("challenge 4", "challenge 4 desc", "challenge", 3600),
        ChallengeCard("challenge 5", "challenge 5 desc", "challenge", 3600),
        ChallengeCard("challenge 6", "challenge 6 desc", "challenge", 3600),
        ChallengeCard("challenge 7", "challenge 7 desc", "challenge", 3600),
        ChallengeCard("challenge 8", "challenge 8 desc", "challenge", 3600),
        ChallengeCard("challenge 9", "challenge 9 desc", "challenge", 3600),
        ChallengeCard("challenge 10", "challenge 10 desc", "challenge", 3600),
        ChallengeCard("challenge 11", "challenge 11 desc", "challenge", 3600),
        ChallengeCard("challenge 12", "challenge 12 desc", "challenge", 3600),
    ]
    reward_items = [
        RewardCard("reward 1", "reward 1 desc", "reward", "curse"),
        RewardCard("reward 2", "reward 1 desc", "reward", "curse"),
        RewardCard("reward 3", "reward 1 desc", "reward", "curse"),
        RewardCard("reward 4", "reward 1 desc", "reward", "curse"),
        RewardCard("reward 5", "reward 1 desc", "reward", "curse"),
        RewardCard("reward 6", "reward 1 desc", "reward", "curse"),
        RewardCard("reward 7", "reward 1 desc", "reward", "powerup"),
        RewardCard("reward 8", "reward 1 desc", "reward", "powerup"),
        RewardCard("reward 9", "reward 1 desc", "reward", "powerup"),
        RewardCard("reward 10", "reward 1 desc", "reward", "powerup"),
        RewardCard("reward 11", "reward 1 desc", "reward", "powerup"),
        RewardCard("reward 12", "reward 1 desc", "reward", "powerup"),
    ]

    if mode == "challenge":
        return challenge_items

    return reward_items
    