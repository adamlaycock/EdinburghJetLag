import streamlit as st
from streamlit_folium import st_folium
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from typing import List, Dict
from game_functions import get_teams_data, clear_team_data
from container_management import Container

conn = st.connection("gsheets", type=GSheetsConnection)

TEAMS = ["team_a", "team_b", "team_c"]

###############################################################################
# Functions for communicating with "team_mgmt"
###############################################################################

def build_player_form() -> None:
    with st.form("add_player_form", clear_on_submit=True):
        st.subheader('Add Players')
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
            conn.update(worksheet="teams", data=new_team_data)
            st.cache_data.clear()
            st.rerun()


def build_team_players(team_names: List[str], team_data: pd.DataFrame):
    if not team_data.empty:
        left, middle, right = st.columns(3)

        for column, team_name in zip(
            [left, middle, right],
            team_names
        ):
            with column:
                st.subheader(f"{team_name}:")
                st.button(
                    f"Clear {team_name}", 
                    on_click=clear_team_data,
                    args=(team_name,)
                )
                st.write("")
                for player in team_data[team_data["team_name"]==team_name]["player_name"]:
                    st.write(f"- {player}")

def build_game_map(core_components: Dict[str, Container]) -> None:
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
        tooltip=False,
        popup=["name", "control", "is_prot"],
        tiles="OpenStreetMap",
        style_kwds={"style_function": style_status},
    )

    bounds = full_gdf.total_bounds
    minx, miny, maxx, maxy = bounds

    m.fit_bounds([[miny, minx], [maxy, maxx]])
    m.options["maxBounds"] = [[miny, minx], [maxy, maxx]]
    m.options["maxBoundsViscosity"] = 1
    m.options["zoomSnap"] = 0.1
    m.options["minZoom"] = 12.5

    st_folium(m, width=700, height=500, returned_objects=[])
    