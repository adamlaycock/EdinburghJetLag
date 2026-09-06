from app_elements import *
from container_management import *
from game_functions import *

teams_data = get_teams_data()
core_comps = load_containers()

tab1, tab2, tab3, tab4 = st.tabs(["Players", "Game Map", "Global Challenges", "Team Hands"])

with tab1:
    build_player_form()
    st.write("---")
    a_players, b_players, c_players = build_team_players(teams_data)
    st.write("---")

    if any([a_players, b_players, c_players]):
        st.header("Start Game")
        if st.button("Click to Start JetLagEdinburgh"):
            core_comps = initialise_core_components(
                a_players, b_players, c_players
            )
            save_containers(core_comps)

with tab2:
    build_game_map(core_comps)

with tab3:
    build_global_challenges(core_comps)

with tab4:
    team_name = st.selectbox(
        "Select team:",
        options=[None, "Team A", "Team B", "Team C"],
        index=0
    )

    if team_name:
        build_team_active(core_comps, team_name)

        build_team_hand(core_comps, team_name)