import streamlit as st
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection
from streamlit_geolocation import streamlit_geolocation
import pandas as pd
import geopandas as gpd
from typing import List, Dict, Optional
from game_functions import *
from container_management import Container, ChallengeCard
from shapely.geometry import Point
import time
import re

CONN = st.connection("gsheets", type=GSheetsConnection)

TEAMS = ["Team A", "Team B", "Team C"]

def build_player_form() -> None:
    with st.form("add_player_form", clear_on_submit=True):
        st.header('Add Players')
        name = st.text_input("Enter player name:", key="add_player")
        team = st.selectbox(
            "Select team:", 
            key="select_team",
            options=TEAMS
        )
        submitted = st.form_submit_button("Add Player")

        if submitted and name and team:
            current_team_data = get_teams_data()

            new_row = pd.DataFrame({
                "team_name": [team],
                "player_name": [name]
            })

            new_team_data = pd.concat(
                [current_team_data, new_row], ignore_index=True
            )
            update_teams_data(new_team_data)
            st.cache_data.clear()
            st.rerun()

@st.fragment(run_every="30s")
def build_team_players(team_data):
    st.header("Current Players:")

    players_by_team = {name: [] for name in TEAMS}

    if not team_data.empty:
        left, middle, right = st.columns(3)

        for column, team_name in zip([left, middle, right], TEAMS):
            team_players = team_data[team_data["team_name"] == team_name]["player_name"].tolist()
            players_by_team[team_name] = team_players

            with column:
                st.subheader(f"{team_name}")
                st.button(
                    f"Clear {team_name}", 
                    on_click=clear_team_data,
                    args=(team_name,)
                )
                st.write("")
                for player in team_players:
                    st.write(f"- {player}")

    return (
        players_by_team["Team A"], 
        players_by_team["Team B"], 
        players_by_team["Team C"]
    )

@st.fragment(run_every="30s")
def build_game_map(core_components) -> None:
    containers = {
        "Team A": core_components["team_a_areas"],
        "Team B": core_components["team_b_areas"],
        "Team C": core_components["team_c_areas"],
        "Unclaimed": core_components["unclaimed_areas"],
    }

    dfs = [
        pd.DataFrame({
            "name": [item.name for item in container.items],
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
    full_gdf["is_prot"] = full_gdf["is_prot"].astype(bool)

    full_gdf["control"] = pd.Categorical(
        full_gdf["control"],
        categories=containers.keys(),
    )
    colors = ["#FF0000", "#FFFF00", "#0000FF", "#808080"]

    def style_status(feature):
        if feature["properties"]["is_prot"]:
            return {
                "color": "black",
                "weight": 4,
                "fillOpacity": 0.75,
            }

        return {
            "color": "#111111",
            "weight": 1.5,
            "fillOpacity": 0.25,
        }

    m = full_gdf.explore(
        column="control",
        cmap=colors,
        categorical=True,
        legend=False,
        tooltip=False,
        popup=["name", "control", "is_prot"],
        tiles="OpenStreetMap",
        style_kwds={"style_function": style_status},
    )

    for key in list(m._children):
        if "legend" in key.lower():
            del m._children[key]

    bounds = full_gdf.total_bounds
    minx, miny, maxx, maxy = bounds

    m.fit_bounds([[miny, minx], [maxy, maxx]])
    m.options["maxBounds"] = [[miny, minx], [maxy, maxx]]
    m.options["maxBoundsViscosity"] = 1
    m.options["zoomSnap"] = 0.75
    m.options["minZoom"] = 12.5

    st_folium(m, width=700, height=500, returned_objects=[])

@st.fragment(run_every="1s") 
def build_global_challenges(core_components) -> None:
    global_challenges = core_components["global_challenges"]

    if global_challenges.items:
        st.header("Available Challenges:")
        for challenge_card, card_num in zip(
            global_challenges.items,
            ["one", "two", "three", "four", "five"]
        ):
            with st.container(border=True):
                st.subheader(challenge_card.name)
                st.write(f"{challenge_card.description}")
                st.write(f"This challenge must be completed within **{int(challenge_card.duration / 60)} minutes**.")

def build_team_hand(core_components: Dict[str, Container], team_name: str):
    team_name = team_name.lower().replace(" ", "_")

    team_hand = core_components[f"{team_name}_hand"]

    if team_hand.items:
        for reward_card, card_num in zip(
            team_hand.items, 
            ["one", "two", "three", "four", "five"]
        ):
            with st.container(border=True):
                st.subheader(reward_card.name)
                st.write(f"{reward_card.reward_type}")
                st.write(f"{reward_card.description}")

                if st.button("Use Card", key=f"use_{card_num}"):
                    if reward_card.reward_type == "powerup":
                        send_discord_notification(
                            team_name,
                            None,
                            reward_card
                        )
                        team_hand.transfer_item(
                            reward_card, 
                            core_components["discard_deck"]
                        )
                        save_containers(core_components)
                        st.rerun()
                    else:
                        choose_target_team(reward_card, team_name, core_components)
                    
                if st.button("Discard Card", key=f"discard_{card_num}"):
                    team_hand.transfer_item(
                        reward_card,
                        core_components["discard_deck"]
                    )
                    save_containers(core_components)
                    st.rerun()

@st.fragment(run_every="1s")
def build_team_active(core_components: Dict[str, Container], team_name:str):
    team_name = team_name.lower().replace(" ", "_")

    team_active = core_components[f"{team_name}_active"]
    team_areas = core_components[f"{team_name}_areas"]

    if team_active.items:
        for challenge_card in team_active.items:
            if challenge_card.is_expired:
                core_components["challenged_areas"].transfer_item_by_name(
                    challenge_card.challenge_area,
                    core_components[f"{challenge_card.area_og_container}"]
                )
                challenge_card.reset_challenge()
                team_active.transfer_item(
                        challenge_card, 
                        core_components["global_challenges"]
                    )
                save_containers(core_components)

            with st.container(border=True):
                st.subheader(challenge_card.name)
                st.write(f"{challenge_card.description}")
                st.write(f"Challenging: {challenge_card.challenge_area}")
                build_time_remaining(challenge_card)
                if st.button("Complete Challenge"):
                    core_components["challenged_areas"].transfer_item_by_name(
                        challenge_card.challenge_area,
                        team_areas
                    )
                    challenge_card.reset_challenge()
                    team_active.transfer_item(
                        challenge_card, 
                        core_components["discard_deck"]
                    )
                    core_components["reward_deck"].transfer_random_item(
                        core_components[f"{team_name}_hand"]
                    )
                    core_components["challenge_deck"].transfer_random_item(
                        core_components["global_challenges"]
                    )
                    save_containers(core_components)
                    st.rerun()

def build_time_remaining(challenge_card) -> None:
    time_remaining = challenge_card.time_remaining

    if time_remaining is None:
        return

    total_seconds = int(time_remaining.total_seconds())

    st.write(
        f"Time Remaining: **"
        f"{total_seconds // 60:02d}:"
        f"{total_seconds % 60:02d}**"
    )

def build_team_curses(
    core_components: Dict[str, Container], 
    team_name: str
):
    team_name = team_name.lower().replace(" ", "_")
    team_curses = core_components[f"{team_name}_curses"]

    if team_curses.items:
            for curse_card, card_num in zip(
                team_curses.items, 
                ["one", "two", "three", "four", "five"]
            ):
                with st.container(border=True):
                    st.subheader(f"{curse_card.name}")
                    st.write(f"{curse_card.description}")
                    if st.button("Clear Curse", key=f"{card_num}_clear"):
                        team_curses.transfer_item(
                            curse_card,
                            core_components["discard_deck"]
                        )
                        save_containers(core_components)
                        st.rerun()


@st.dialog("Choose Target Team")
def choose_target_team(reward_card: Any, team_name: str, core_components: Dict[str, Any]):
    st.write(f"Select a target team to apply **{reward_card.name}**:")
    
    target_team = st.selectbox(
        "Select team:",
        options=["Team A", "Team B", "Team C"],
        index=None
    )
    
    if st.button("Submit"):
        if target_team:
            recipient = target_team.lower().replace(" ", "_")
            send_discord_notification(team_name, recipient, reward_card)

            team_hand = core_components[f"{team_name}_hand"]
            team_hand.transfer_item(
                reward_card,
                core_components[f"{recipient}_curses"]
            )
            save_containers(core_components)
            st.rerun()

from typing import Dict, Any

@st.dialog("Start a Challenge")
def build_start_challenge(core_components: Dict[str, Any]) -> None:
    team_name = st.selectbox(
        "Select a team:",
        options=[None, "Team A", "Team B", "Team C"],
        index=0
    )
    challenge_name = None
    if team_name:
        challenge_name = st.selectbox(
            "Select a challenge:",
            options=[
                challenge_card.name 
                for challenge_card in core_components["global_challenges"].items
            ]
        )
    if challenge_name:
        all_containers = ["team_a_areas", "team_b_areas", "team_c_areas", "unclaimed_areas"]
        excluded_container = f"{team_name.lower().replace(' ', '_')}_areas"
        target_containers = [c for c in all_containers if c != excluded_container]
        area_options = [
            area.name 
            for c_name in target_containers 
            for area in core_components[c_name].items
        ]
        area_options = sorted(area_options, key=lambda x: int(re.search(r'\d+', x).group()))
        
        area_name = st.selectbox(
            "Select your current area:",
            options=area_options
        )

    if team_name and challenge_name and area_name:
        st.write(f"{team_name} @ {area_name}")
        with st.container(border=True):
            challenge_card = core_components["global_challenges"].get_item_by_name(
                challenge_name
            )
            st.subheader(challenge_card.name)
            st.write(f"{challenge_card.description}")
            st.write(f"{challenge_card.duration / 60} minutes.")
        if st.button("Submit"):
            start_challenge(core_components, team_name, challenge_name, area_name)
            