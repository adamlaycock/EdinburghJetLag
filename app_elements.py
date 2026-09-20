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
import plotly.express as px
import random

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
                if st.button(f"Clear {team_name}"):
                    clear_team_data(team_name)
                    st.rerun()
                st.write("")
                for player in team_players:
                    st.write(f"- {player}")

    return (
        players_by_team["Team A"], 
        players_by_team["Team B"], 
        players_by_team["Team C"]
    )

@st.fragment(run_every="10s")
def build_game_map() -> None:
    core_components = load_containers()

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
                "weight": 3,
                "fillOpacity": 0.5,
            }

        return {
            "color": "#111111",
            "weight": 1.5,
            "fillOpacity": 0.25,
        }

    bounds = full_gdf.total_bounds
    minx, miny, maxx, maxy = bounds
    center_lat = (miny + maxy) / 2
    center_lon = (minx + maxx) / 2

    m = full_gdf.explore(
        column="control",
        cmap=colors,
        categorical=True,
        legend=False,
        tooltip=False,
        popup=["name", "control", "is_prot"],
        tiles="OpenStreetMap",
        style_kwds={"style_function": style_status},
        zoom_start=12.5,
        location=[center_lat, center_lon]
    )

    for key in list(m._children):
        if "legend" in key.lower():
            del m._children[key]

    m.options["minZoom"] = 12.5
    m.options["maxBounds"] = [[miny, minx], [maxy, maxx]]
    m.options["maxBoundsViscosity"] = 1.0
    m.options["zoomSnap"] = 0.1

    st.header("Map:")
    st_folium(m, width="stretch", height=500, returned_objects=[])

@st.fragment(run_every="10s") 
def build_global_challenges() -> None:
    core_components = load_containers()
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

@st.fragment(run_every="10s")
def build_team_hand(team_name: str):
    core_components = load_containers()
    team_name = team_name.lower().replace(" ", "_")

    team_hand = core_components[f"{team_name}_hand"]

    if team_hand.items:
        for reward_card, card_num in zip(
            team_hand.items, 
            ["one", "two", "three", "four", "five"]
        ):
            with st.container(border=True):
                st.subheader(reward_card.name)
                st.write(f"{reward_card.description}")

                if st.button("Use Card", key=f"use_{card_num}"):
                    if reward_card.reward_type == "powerup":
                        if "Shuffle Challenges" in reward_card.name:
                            num_cards = random.randint(2, len(core_components["global_challenges"].items))
                            for i in range(num_cards):
                                core_components["global_challenges"].transfer_random_item(
                                    core_components["challenge_deck"]
                                )
                                core_components["challenge_deck"].transfer_random_item(
                                    core_components["global_challenges"]
                                )
                        team_hand.transfer_item(
                            reward_card, 
                            core_components["discard_deck"]
                        )
                        save_containers(core_components)
                        msg = f"""
                            {{{team_name}}} has used **{reward_card.name}**!
                        """
                        send_discord_notification(msg)
                        st.rerun()
                    else:
                        choose_target_team(reward_card, team_name)
                    
                if st.button("Discard Card", key=f"discard_{card_num}"):
                    team_hand.transfer_item(
                        reward_card,
                        core_components["discard_deck"]
                    )
                    save_containers(core_components)
                    st.rerun()
    else:
        with st.container(border=True):
            st.write("Your hand is currently empty.")
            st.write("Complete challenges to gain new reward cards.")

@st.fragment(run_every="10s")
def build_team_active(team_name:str):
    core_components = load_containers()
    team_name = team_name.lower().replace(" ", "_")

    team_active = core_components[f"{team_name}_active"]
    team_areas = core_components[f"{team_name}_areas"]

    if team_active.items:
        for challenge_card in team_active.items:
            with st.container(border=True):
                st.subheader(challenge_card.name)
                st.write(f"{challenge_card.description}")
                st.write(f"Challenging: {challenge_card.challenge_area}")
                if st.button("Complete Challenge"):
                    if core_components[f"{team_name}_hand"].has_space():
                        msg = f"""
                            {{{team_name}}} has completed **{challenge_card.name}**, capturing the **{challenge_card.challenge_area}** zone!
                        """
                        send_discord_notification(msg)
                        area = core_components["challenged_areas"].get_item_by_name(
                            challenge_card.challenge_area
                        )
                        area.start_protection(900)
                        core_components["challenged_areas"].transfer_item(
                            area,
                            team_areas
                        )
                        challenge_card.reset_challenge()
                        team_active.transfer_item(
                            challenge_card, 
                            core_components["discard_deck"]
                        )
                        core_components["challenge_deck"].transfer_random_item(
                            core_components["global_challenges"]
                        )
                        core_components["reward_deck"].transfer_random_item(
                            core_components[f"{team_name}_hand"]
                        )
                        save_containers(core_components)
                        update_cooldowns([team_name], 600)
                        st.rerun()
                    else:
                        st.error("You must use or discard a card from your hand before completing this challenge.")
                        time.sleep(5)
                if st.button("Abandon Challenge"):
                    msg = f"""
                        {{{team_name}}} has abandoned **{challenge_card.name}**, failing to capture the **{challenge_card.challenge_area}** zone!
                    """
                    send_discord_notification(msg)
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
                    update_cooldowns([team_name], 600)
                    st.rerun()
    else:
        with st.container(border=True):
            st.write("Your team has no active challenge.")
            st.write("Challenges can be started on the 'Global Challenges' panel.")

@st.fragment(run_every="10s")
def build_team_curses(
    team_name: str
):
    core_components = load_containers()
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
                        msg = f"""
                            {{{team_name}}} has cleared **{curse_card.name}!**
                        """
                        send_discord_notification(msg)
                        save_containers(core_components)
                        st.rerun()
    else:
        with st.container(border=True):
            st.write("Your team has no active curses.")
            st.write("Curses may be cast upon your team throughout the course of the game.")


@st.dialog("Choose Target Team")
def choose_target_team(reward_card: Any, team_name: str):
    core_components = load_containers()
    st.write(f"Select a target team to apply **{reward_card.name}**:")
    
    target_team = st.selectbox(
        "Select team:",
        options=["Team A", "Team B", "Team C"],
        index=None
    )
    
    if st.button("Submit"):
        if target_team:
            recipient = target_team.lower().replace(" ", "_")

            team_hand = core_components[f"{team_name}_hand"]
            if core_components[f"{recipient}_curses"].has_space():
                team_hand.transfer_item(
                    reward_card,
                    core_components[f"{recipient}_curses"]
                )
                save_containers(core_components)
                msg = f"""
                    {{{team_name}}} has cast **{reward_card.name}** on {{{recipient}}}!
                """
                send_discord_notification(msg)
                st.rerun()
            else:
                st.error("The target team has already reached the maximum number of curses.")
        else:
            st.error("Please select a team.")

from typing import Dict, Any

@st.dialog("Start a Challenge")
def build_start_challenge() -> None:
    core_components = load_containers()
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
        if st.button("Submit"):
            start_challenge(team_name, challenge_name, area_name)

@st.fragment(run_every="10s")
def build_scoreboard(scores: pd.DataFrame) -> None:
    if scores is not None:
        total_score = scores["score"].sum()
        scores["score_percent"] = (scores["score"] / total_score) * 100
        scores["row"] = "Score"
        scores["score_label"] = scores["score"].map(lambda x: f"{x:.0f} pts")

        color_map = {
            "Team A": "#FF0000",
            "Team B": "#FFFF00",
            "Team C": "#0000FF",
        }

        fig = px.bar(
            scores,
            x="score_percent",
            y="row",
            color="control",
            orientation="h",
            text="score_label",
            color_discrete_map=color_map,
        )

        fig.update_layout(
            barmode="stack",
            showlegend=False,
            bargap=0,
            xaxis=dict(
                visible=False,
                range=[0, 100],
            ),
            yaxis=dict(
                visible=False,
                range=[-0.1, 0.1],
            ),
            height=100,
            margin=dict(l=0, r=0, t=0, b=0),
            hovermode=False,
            font=dict(size=18)
        )

        fig.update_traces(
            marker_line_width=0,
            width=0.3,
            textposition="inside",
            insidetextanchor="middle",
        )

        st.header("Scoreboard:")
        st.plotly_chart(
            fig,
            width="stretch",
            config={"displayModeBar": False},
        )
