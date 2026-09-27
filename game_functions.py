from container_management import *
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import geopandas as gpd
from shapely.geometry import Point
from streamlit_geolocation import streamlit_geolocation
from typing import Optional
import requests
import networkx as nx
import numpy as np

conn = st.connection("gsheets", type=GSheetsConnection)

def update_teams_data(new_team_data: pd.DataFrame) -> None:
    """Connects to the Google spreadsheet and updates the "team_mgmt" sheet 
    with new player information. It also clears the cached data retrieved by
    get_teams_data().

    Args:
        new_team_data (pd.DataFrame): pandas DataFrame containing the new
                                      player information.

    Returns:
        None
    
    """
    conn.update(worksheet="team_mgmt", data=new_team_data)
    get_teams_data.clear()

@st.cache_data(ttl=5) 
def get_teams_data() -> pd.DataFrame:
    """Connects to the Google spreadsheet and retrieves the current data stored
    in the "team_mgmt" sheet.

    Args:
        None

    Returns:
        df (pd.DataFrame): pandas DataFrame containing the player information
                           currently stored in "team_mgmt".
    
    """
    df = conn.read(worksheet='team_mgmt')
    if df.empty:
        return pd.DataFrame({
            "team_name": [],
            "player_name": []
        })
    else:
        return df

def clear_team_data(team_name: str) -> None:
    """Clears the players currently associated with a specific team, specified
    by the team_name argument. Also clears the cached data retrieved by
    get_teams_data().

    Args:
        team_name (str): Name of the team to be cleared.

    Returns:
        None
    
    """
    current_team_data = get_teams_data()

    new_team_data = current_team_data[current_team_data["team_name"]!=team_name]

    conn.update(worksheet="team_mgmt", data=new_team_data)
    get_teams_data.clear()

def save_containers(containers: dict[str, Container]) -> None:
    """Saves the current state of game-essential container instances. Also
    conducts the JSON serialisation of the containers during the saving 
    process.

    Args:
        containers (dict[str, Container]): Dictionary of container instances.

    Returns:
        None
    
    """
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

@st.cache_data(ttl=10)
def load_containers() -> Dict[str, Container]:
    """Loads the JSON data stored in the "container_mgmt" google sheet and then
    deserialises the JSON information back into Container instances before
    aggregating them into a dictionary.

    Args:
        None
    
        Returns:
            Dict[str, Container]: Contains Container instances that hold game
                                  information.

    """
    df = conn.read(worksheet="container_mgmt", ttl=10)
    df = df.dropna(subset=["container_key", "json"])

    return {
        row["container_key"]: Container.from_json(row["json"])
        for _, row in df.iterrows()
    }

@st.cache_data(ttl=10)
def get_cooldowns() -> pd.DataFrame:
    """Pulls cooldown data from the "cooldown_mgmt" sheet and returns the team
    and cooldown timestamp as a pandas DataFrame.

    Args:
        None

    Returns:
        df (pd.DataFrame): pandas DataFrame containing team cooldown 
                           information.
    
    """
    df = conn.read(worksheet="cooldown_mgmt", ttl=30)
    df = df.dropna(subset=["team_key", "timestamp"])

    return df

def update_cooldowns(team_keys: List[str], duration: int) -> None:
    """Updates challenge cooldown data when called by creating new timestamps
    for teams specified in the team_keys list.

    Args:
        team_keys (List[str]): Holds team names to start cooldowns for.

        duration (int): Number of seconds that the cooldown should last for.

    Returns:
        None
    
    """
    df = conn.read(worksheet="cooldown_mgmt", ttl=0)

    for team_key in team_keys:
        df = df[df["team_key"] != team_key]

        new_row = pd.DataFrame({
            "team_key": [team_key],
            "timestamp": [time.time() + duration]
        })

        df = pd.concat(
            [df, new_row], ignore_index=True
        )

    conn.update(worksheet="cooldown_mgmt", data=df)

    get_cooldowns.clear()


def initialise_core_components(
    team_a_players: List[str],
    team_b_players: List[str],
    team_c_players: List[str],
) -> Dict[str, Container]:
    """Creates the core Container instances and sets the values for their
    attributes before returning them as a dictionary. Also creates the Area 
    instances from the GeoJSON file.

    Args:
        team_a_players (List[str]): List containing players names for Team A.

        team_b_players (List[str]): List containing players names for Team B.

        team_c_players (List[str]): List containing players names for Team C.

    Returns:
        Dict[str, Container]: Dictionary containiner the game's core container
                              instances.
    
    """

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
        ("team_a_curses", "cards", 5),

        ("team_b_hand", "cards", 5),
        ("team_b_active", "cards", 1),
        ("team_b_players", "players", 5),
        ("team_b_areas", "areas", 15),
        ("team_b_curses", "cards", 5),

        ("team_c_hand", "cards", 5),
        ("team_c_active", "cards", 1),
        ("team_c_players", "players", 5),
        ("team_c_areas", "areas", 15),
        ("team_c_curses", "cards", 5),
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

def get_current_area() -> Optional[tuple[str, float]]:
    """Gets the player's current location using streamlit_geolocation() and
    checks which zone the current coordinates are located within.

    Args:
        None

    Returns:
        Optional[tuple[str, float]]: Tuple containing current zone and location
                                     accuracy. Tuple will only be returned if
                                     the current coordinates are within a zone.
    
    """
    st.header("Get Current Zone:")
    geolocation = streamlit_geolocation()

    lat = geolocation.get("latitude")
    lon = geolocation.get("longitude")
    accuracy = geolocation.get("accuracy")

    if lat is None or lon is None:
        return None, None
    
    gdf = gpd.read_file(
        "MapData/Board/GameBoard.geojson"
    ).to_crs("EPSG:4326")

    matching_polygon = gdf[gdf.geometry.covers(Point(lon, lat))]

    if matching_polygon.empty:
        return None, None

    return (matching_polygon.iloc[0]["name"], accuracy)

def initialise_decks(mode: str) -> List[Card]:
    """Uses static CSV files to build challenge and reward Card instances.

    Args:
        mode (str): String which determines which list of Card instances will
                    be returned by the function.

    Returns:
        List[Card]: List of either ChallengeCard or RewardCard instances.
    
    """
    challenge_df = pd.read_csv(
        "CardData/challenge_cards.csv",
        quotechar='"'
    )
    challenge_items = [
        ChallengeCard(**row) 
        for row in challenge_df.to_dict(orient="records")
    ]

    reward_df = pd.read_csv(
        "CardData/reward_cards.csv",
        quotechar='"'
    )
    reward_items = [
        RewardCard(**row) 
        for row in reward_df.to_dict(orient="records")
    ]

    if mode == "challenge":
        return challenge_items

    return reward_items

def find_area_by_name(
    area_name: str, core_comps: Dict[str, Container], exclusion: Optional[str],
) -> Optional[tuple[Area, str]]:
    """Checks which Area Container instance an Area instance is currently 
    stored in.

    Args:
        area_name (str): Name of the area to be located. Should match an Area's
                         name attribute.

        core_comps (Dict[str, Container]): Dictionary container the core
                                           Container instances.

        exclusion (Optional[str]): Name of an Area Container that should not be
                                   included in the current search.

    Returns:
        Optional[tuple[Area, str]]: Tuple containing the Area instance and the
                                    name of the Container that it is currently
                                    stored in.
    
    """
    container_names = [
        "team_a_areas", "team_b_areas", "team_c_areas", "unclaimed_areas",
    ]

    if exclusion:
        container_names.remove(exclusion)

    for name in container_names:
        container = core_comps[name]
        item = container.get_item_by_name(area_name)

        if item is not None:
            return item, container

    return None

def start_challenge(
        team_name: str, challenge_name: str, challenge_area: str
) -> None:
    """Performs checks that need to be cleared before starting a challenge,
    such as checking Area protection and team challenge cooldowns. If
    successful, the function moves the necessary Card and Area instances
    between Containers before saving the current Container states and sending
    challenge-related discord notifications.

    Args:
        team_name (str): Name of the team who are attempting to start a
                         challenge.

        challenge_name (str): Name of the selected ChallengeCard instance.

        challenge_area (str): Name of the selected Area to be challenged.

    Returns:
        None
    
    """
    core_components = load_containers()
    team_name = team_name.lower().replace(" ", "_")
    active_container = core_components[f"{team_name}_active"]
    areas_container = core_components[f"{team_name}_areas"]

    cooldowns = get_cooldowns()
    if cooldowns[cooldowns["team_key"]==team_name]["timestamp"].iloc[0] <= time.time():
        if core_components["challenged_areas"].get_item_by_name(challenge_area) is None:
            area, original_container = find_area_by_name(
                challenge_area, 
                core_comps=core_components, 
                exclusion=areas_container.name
            )
            if not area.is_prot:
                if active_container.has_space():
                    challenge_card = core_components["global_challenges"].get_item_by_name(
                        challenge_name
                    )
                    if challenge_card is not None:
                        challenge_card.start_challenge(
                            challenge_area, original_container.name
                        )
                        core_components["global_challenges"].transfer_item(
                            challenge_card,
                            active_container
                        )
                        original_container.transfer_item(
                            area,
                            core_components["challenged_areas"]
                        )
                        save_containers(core_components)
                        msg = f"""
                            {{{team_name}}} has started **{challenge_name}** in the **{challenge_area}** zone!
                        """
                        send_discord_notification(msg)
                        st.rerun()
                    else:
                        st.error("This challenge is no longer available!")
                else:
                    st.error("Your team already has an active challenge!")
            else:
                st.error("This area is currently protected!")
        else:
            st.error("This area is already being challenged!")
    else:
        st.error("Your team's challenge cooldown has not yet expired!")

def count_adjacent_zones(gdf: gpd.GeoDataFrame, tolerance=1.0) -> int:
    """Finds, and then returns the size of, the largest group of connected 
    geometries in the GeoPandas GeoDataFrame, providing that the geometries are
    within a one metre tolerance of each other.

    Args:
        gdf (gpd.GeoDataFrame): GeoPandas GeoDataFrame containing geometries to
                                compare.
        
        tolerance (float): Distance, in metres, that two geometries have to be
                           located within to be considered connected.

    Returns:
        int: Maximum number of connected geometries.
    
    """
    projected = gdf.to_crs("EPSG:27700")

    G = nx.Graph()
    G.add_nodes_from(projected.index)

    for i, geom in projected.geometry.items():
        for j in projected.index:
            if i < j:
                other = projected.loc[j, "geometry"]

                if geom.distance(other) <= tolerance:
                    G.add_edge(i, j)

    return max(
        len(component)
        for component in nx.connected_components(G)
    )


def calculate_scores() -> Optional[pd.DataFrame]:
    """Calculates each Team's scores based on the area and distance properties 
    of the zones that they control, and how of those zones are directly connected.

    Args:
        None

    Returns:
        pd.DataFrame: pandas DataFrame containing each team and their score at
                      the current time. This will not be returned if all zones
                      are uncaptured.
    
    """
    core_components = load_containers()
    if len(core_components["unclaimed_areas"].items) + len(core_components["challenged_areas"].items)!= 15:
        containers = {
            "Team A": core_components["team_a_areas"],
            "Team B": core_components["team_b_areas"],
            "Team C": core_components["team_c_areas"],
            "Unclaimed": core_components["unclaimed_areas"],
        }
        dfs = [
            pd.DataFrame({
                "name": [item.name for item in container.items],
                "area": [item.area for item in container.items],
                "distance": [item.distance for item in container.items],
                "geometry": [item.geometry for item in container.items],
                "is_prot": [item.is_prot for item in container.items],
                "control": control,
            })
            for control, container in containers.items()
        ]
        full_gdf = gpd.GeoDataFrame(
            pd.concat(dfs, ignore_index=True),
            geometry="geometry",
            crs="EPSG:4326",
        )
        full_gdf = full_gdf[full_gdf["control"] != "Unclaimed"]

        adjacency_df = (
            full_gdf.groupby("control")
            .apply(count_adjacent_zones, include_groups=False)
            .reset_index(name="number")
        )
        score_df = full_gdf.groupby("control")[["area", "distance"]].sum().reset_index()
        score_df = score_df.merge(adjacency_df, how="inner", on="control")
        score_df["score"] = (score_df["area"] + score_df["distance"]) * score_df["number"]

        return score_df[["control", "score"]]
    return None

def send_discord_notification(msg: str) -> None:
    """Sends a custom discord notification via a webhook integration. Also
    includes team IDs to personalise the notifications that are sent.

    Args:
        msg (str): Message text.

    Returns:
        None
    
    """


    TEAM_MAPPING = {
        "team_a": "<@&1545068980996145182>",
        "team_b": "<@&1545069081256788018>",
        "team_c": "<@&1545069296064004166>"
    }
    msg = msg.format(**TEAM_MAPPING)

    embed = {
        "title": "Game Update!",
        "description": msg,
        "color": 0xFFFFFF,
        "footer": {
            "text": "EdinburghJetLag • Alerts"
        }
    }

    payload = {
        "embeds": [embed],
        "username": "EdinburghJetLag"
    }

    requests.post(st.secrets["discord_webhook"], json=payload)