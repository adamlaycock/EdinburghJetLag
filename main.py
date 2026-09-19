from app_elements import *
from container_management import *
from game_functions import *

teams_data = get_teams_data()
core_comps = load_containers()

if "authenticated_team" not in st.session_state:
    st.session_state["authenticated_team"] = None

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
            core_comps["challenge_deck"].items = initialise_decks("challenge")
            core_comps["reward_deck"].items = initialise_decks("reward")
            for i in range(5):
                core_comps["challenge_deck"].transfer_random_item(core_comps["global_challenges"])
            update_cooldowns(["team_a", "team_b", "team_c"], 0)
            save_containers(core_comps)

with tab2:
    if len(core_comps["unclaimed_areas"].items) + len(core_comps["challenged_areas"].items)!= 15:
        build_scoreboard(calculate_scores(core_comps))

    build_game_map(core_comps)

    zone, accuracy = get_current_area()
    if zone:
        st.write(f"You are currently within the **{zone}** zone.")
        st.write(f"Accurate to **{accuracy}m**.")

with tab3:
    build_global_challenges(core_comps)

    st.header("Start a Challenge:")
    if st.button("Start a Challenge"):
        build_start_challenge(core_comps)

with tab4:
    team_name = st.selectbox(
        "Select team:",
        options=[None, "Team A", "Team B", "Team C"],
        index=0
    )
    if team_name:
        if st.session_state["authenticated_team"] != team_name:
            pwd = st.text_input("Enter your team's password:", type="password")

            stored_pwd_key = f"{team_name.lower().replace(' ', '_')}_pwd"
            correct_pwd = st.secrets.get(stored_pwd_key)

            if pwd:
                if correct_pwd and pwd == correct_pwd:
                    st.session_state["authenticated_team"] = team_name
                    st.rerun()
                else:
                    st.error("Incorrect password!")

    if st.session_state["authenticated_team"] == team_name and team_name != None:

        st.header("Active Challenge:")
        build_team_active(core_comps, team_name)

        st.header("Active Curses:")
        build_team_curses(core_comps, team_name)

        st.header("Available Cards:")
        build_team_hand(core_comps, team_name)
