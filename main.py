from app_elements import *
from container_management import *
from game_functions import *


tab1, tab2, tab3, tab4 = st.tabs(["Players", "Game Map", "Global Challenges", "Team Hands"])

with tab1:
    build_player_form()
    st.write("---")
    a_players, b_players, c_players = build_team_players()
    st.write("---")

    if any([a_players, b_players, c_players]):
        st.header("Start Game")
        if st.button("Click to Start JetLagEdinburgh"):
            core_comps = initialise_core_components(
                a_players, b_players, c_players
            )
            save_containers(core_comps)