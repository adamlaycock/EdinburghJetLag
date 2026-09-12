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

def build_start_challenge(core_components) -> None:
    global_challenges = core_components["global_challenges"]

    if global_challenges.items:
        st.header("Start a Challenge:")
        with st.form("start_challenge", clear_on_submit=True):
            team_name = st.selectbox(
                "Select team:",
                options=[None, "Team A", "Team B", "Team C"],
                index=0
            )
            challenge_name = st.selectbox(
                "Select challenge:",
                options=[challenge_card.name for challenge_card in global_challenges.items]
            )
            # current_area = get_current_area(get_current_coords())
            # if current_area:
            #     st.write(f"Current Area: {current_area}")
            current_area = st.text_input("PLACEHOLDER! Input current areaa:")

            if st.form_submit_button("Start Challenge"):
                if team_name and challenge_name and current_area:
                    team_name = team_name.lower().replace(" ", "_")
                    challenged_areas = core_components["challenged_areas"]
                    active_container = core_components[f"{team_name}_active"]
                    areas_container = core_components[f"{team_name}_areas"]

                    if challenged_areas.get_item_by_name(current_area) is None:
                        area, original_container = find_area_by_name(
                            current_area, 
                            core_comps=core_components, 
                            exclusion=areas_container.name
                        )
                        if not area.is_prot:
                            if active_container.has_space():
                                challenge_card = global_challenges.get_item_by_name(
                                    challenge_name
                                )
                                if challenge_card is not None:
                                    challenge_card.start_challenge(current_area, original_container.name)
                                    global_challenges.transfer_item(
                                        challenge_card,
                                        active_container
                                    )
                                    original_container.transfer_item(
                                        area,
                                        core_components["challenged_areas"]
                                    )
                                    save_containers(core_components)
                                    st.rerun()

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
                    team_hand.transfer_item(
                        reward_card, 
                        core_components["discard_deck"]
                    )
                    # Add reward_card effects here
                    save_containers(core_components)
                    st.rerun()
                    
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
                        if confirm_action_dialog("curse"):
                            team_curses.transfer_item(
                                curse_card,
                                core_components["discard_deck"]
                            )
                            save_containers(core_components)


@st.dialog("Confirm Action")
def confirm_action_dialog(mode: str) -> bool:
    if mode == "curse":
        st.write("Have you met the requirements to clear this curse from your team?")
        st.write("Please confirm that you wish to clear this curse below:")
        if st.button("Clear Curse"):
            return True
    if mode == "challenge":
        st.write("Have you met complete this challenge?")
        st.write("Please confirm that you wish to complete this challenge below:")
        if st.button("Complete Challenge"):
            return True
