Frontend Design
- [ ] Landing page containing the live, interactive game map.
- [ ] Team creation and game start page.
- [ ] Global challenges and area claiming page.
- [ ] Team page with hand, active challenge (+time remaining).
- [ ] Score page and game time remaining.

Backend Design
- [x] Google Sheets communication to store data between sessions.
- [x] Object-oriented system containing Containers, Items (Areas, Cards, Players), and Teams.
  - [x] Ability to convert to and be created from json strings which can be stored in GSheets.
- [ ] Functions to handle the claiming of areas and the use of cards.
  - [x] CheckArea:
    - [x] Use geolocation to find current area.
    - [x] Check if current area is protected.
  - [ ] StartChallenge:
    - [ ] Select and move a ChallengeCard from global_challenges to team_x_active.
    - [ ] Start the expiry of the challenge card using its duration.
  - [ ] EndChallenge:
    - [ ] If not expired and not forfeit, discard the ChallengeCard, move the Area to team_x_areas, protect the area, and deal RewardCards to team_x_hand.
    - [ ] If expired or forfeit, move the ChallengeCard back to global_challenges.
  - [ ] UseRewardCard:
    - [ ] Based on whether the card is "PowerUp" or "Curse", apply the effect.
    - [ ] Move the used RewardCard to the discard_deck.
- [ ] Geolocation when starting a challenge or using a reward card.
- [ ] Notification system for the claiming of areas and usage of RewardCards.
- [ ] System to handle game timer and scoring.

Content
- [ ] Cards for the challenge_deck.
- [ ] RewardCards (Powerup & Curse) for the reward_deck.
- [ ] Game rules.
