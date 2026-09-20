from app_elements import *
from container_management import *
from game_functions import *

teams_data = get_teams_data()

if "authenticated_team" not in st.session_state:
    st.session_state["authenticated_team"] = None

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Introduction", "Players", "Game Map", "Global Challenges", "Team Hands"])

with tab1:
    st.header("Introduction")
    st.write("Welcome to JetLagEdinburgh, a real-life board game inspired by the popular travel competition series [Jet Lag: The Game](https://www.youtube.com/c/jetlagthegame).")
    st.write("The city of Edinburgh has been divided into 15 zones using the city's postal districts, with the play area extending out approximately 5 kilometres from the Scott Monument in the city centre.")
    st.write("In small teams, you will travel around the city on-foot or using public transport and complete challenges to capture these zones.")
    st.write("Capturing a zone will net your team points, which are the game's ultimate win condition, alongside reward cards which can be played to shake up the game.")

    st.header("How to Play")
    st.write("JetLagEdinburgh will begin at the centre of the game board, the Scott Monument, where you will organise into teams and join the game's [Discord server](https://discord.gg/KTyUFE9sWn), which will serve as a central hub for game notifications.")
    st.write("Once the game begins, you will be able to see a list of five available challenges which can be completed to capture zones.")
    st.write("The starting zone containing the Scott Monument (EH2) will be protected from challenges for the first 15 minutes of the game to encourage dispersal.")
    st.write("Once within a new zone that you wish to challenge, you can start one of the five available challenges. Note that some challenges will only be possible to complete in specific zones.")
    st.write("Once a challenge has been started, that challenge and the zone are both off-limits to other teams while it is ongoing.")
    st.write("Once you complete a challenge, three game events will take place:")
    st.write("- Firstly, the completed challenge will be removed from the game and a new challenge will take its place in the available challenges.")
    st.write("- Secondly, the challenged zone will come under your control and be protected from being challenged by another team for 15 minutes.")
    st.write("- Thirdly, your team will receive a reward card which can be either a powerup, which are played on yourself, or a curse, which is played on another team.")
    st.write("You may abandon challenges if you deem them too difficult or time-consuming. This won't trigger any of the above events but will place your team on the same 10 minute challenge cooldown.")
    st.write("Each zone is associated with area and distance values which determine your team's score. Additionally, your score will be altered by a powerful multiplier which is based on the number of connected zones that you control.")
    st.write("The game will end when either the game timer expires or there are no more available challenges. The team with the highest score, which is shown on the in-game scoreboard, will win.")

    st.header("App Structure")
    st.write("The 'Players' tab is used to assign players to specific teams and start the game, it can be ignored once the game has started.")
    st.write("The 'Game Map' tab contains the game scoreboard (only visible once the first zone has been captured), the game map, and the ability to see which zone you are currently in. Currently protected zones are displayed on the map with reduced transparency and thicker borders.")
    st.write("The 'Global Challenges' tab contains the challenges available for completion and a button to start a challenge once you are in a required zone.")
    st.write("The 'Team Hands' tab is one of the most important, as it holds your team's active challenge, reward cards, and current curses. You complete or abandon challenges, play or discard reward cards, and clear curses on this page. Each team has a separate access password to keep hands private.")

    st.header("Game Rules")
    st.write("You may only start a challenge in the zone that you are currently in. For example, if you are currently in the EH2 zone and want to capture EH1, you must first enter EH1 before starting a challenge on the 'available challenges' page.")
    st.write("You may not complete challenge activities outside of the zone that are currently challenging. For example, if you are completing a scavenger hunt in EH3a, you may not enter EH3b to find items. However, you may leave and re-enter the zone to avoid obstacles etc.")
    st.write("If you fail or abandon a challenge, you cannot try that zone again until you successfully capture a different one. Additionally, you can never attempt the same challenge again in a zone where you previously failed or abandoned it.")
    st.write("You must send your team's current location every 20 minutes. WhatsApp's current location feature would be preferable.")
    st.write("Trams are prohibited by default, but can be temporarily unlocked using powerup cards.")
    st.write("If you wish to use a powerup, you must play that card before completing the action. For example, if your team wishes to take the tram. You must play the tram card before boarding.")
    st.write("Be respectful while completing challenges or clearing curses. For example, if a challenge asks you to find a photograph a cat, please don't take a photo of a cat through someone's window. We'll trust you found it.")
    st.write("If at any point you need a challenge or card clarifying, message or call Adam who will (hopefully) be able to resolve the issue.")

with tab2:
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
            core_comps["unclaimed_areas"].get_item_by_name("EH2").start_protection(900)
            save_containers(core_comps)
            send_discord_notification("A new game has been started!")

with tab3:
    build_scoreboard(calculate_scores())

    build_game_map()

    zone, accuracy = get_current_area()
    if zone:
        st.write(f"You are currently within the **{zone}** zone.")
        st.write(f"Accurate to **{accuracy:.0f}m**.")

with tab4:
    build_global_challenges()

    st.header("Start a Challenge:")
    if st.button("Start a Challenge"):
        build_start_challenge()

with tab5:
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
        build_team_active(team_name)

        st.header("Active Curses:")
        build_team_curses(team_name)

        st.header("Available Cards:")
        build_team_hand(team_name)
