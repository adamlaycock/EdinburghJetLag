import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

TEAMS = [f"Team {team}" for team in ["A", "B", "C"]]

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5) 
def get_teams():
    df = conn.read(worksheet='teams')
    if df.empty:
        return pd.DataFrame({
            "team_name": [],
            "player_name": []
        })
    else:
        return df

def clear_team_players(team_name: str):
    current_team_data = get_teams()

    new_team_data = current_team_data[current_team_data["team_name"]!=team_name]

    conn.update(worksheet="teams", data=new_team_data)
    st.cache_data.clear()

def build_team_players(team_name: str, team_data: pd.DataFrame):
    st.subheader(f"{team_name}:")
    st.button(
        f"Clear {team_name}", 
        on_click=clear_team_players,
        args=(team_name,)
    )
    st.write("")
    for player in team_data[team_data["team_name"]==team_name]["player_name"]:
        st.write(f"- {player}")

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
        current_team_data = get_teams()

        new_row = pd.DataFrame({
            "team_name": [team],
            "player_name": [name]
        })

        new_team_data = pd.concat([current_team_data, new_row], ignore_index=True)
        conn.update(worksheet="teams", data=new_team_data)
        st.cache_data.clear()
        st.rerun()

current_team_data = get_teams()
if not current_team_data.empty:
    left, middle, right = st.columns(3)

    for column, team in zip(
        [left, middle, right],
        TEAMS
    ):
        with column:
            build_team_players(team, current_team_data)