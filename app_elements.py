import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from typing import List
from game_functions import get_teams_data, clear_team_data

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
