import random as r
from typing import List, Optional

class Card:
    def __init__(self, title: str, description: str, type: str):
        self.title = title
        self.description = description
        self.type = type

    def __repr__(self):
        return f"[{self.title} ({self.type}) - {self.description}]"

class ChallengeCard(Card):
    def __init__(self, title: str, description: str, type: str, duration: str):
        super().__init__(title, description, type)
        self.duration = duration

class RewardCard(Card):
    def __init__(self, title: str, description: str, type: str, reward_type: str):
        super().__init__(title, description, type)
        self.reward_type = reward_type

    def __repr__(self):
        return f"[{self.title} ({self.reward_type}) - {self.description}]"

class CardContainer:
    def __init__(self, cards: Optional[List[Card]] = None):
        self.cards = list(cards) if cards is not None else []
        if self.cards:
            self.shuffle()

    def shuffle(self) -> None:
        r.shuffle(self.cards)

    def remove_card(self) -> Optional[Card]:
        if not self.cards:
            return None

        return self.cards.pop()

    def add_card(self, card: Card) -> None:
        self.cards.append(card)

    def __len__(self):
        return len(self.cards)

    def __repr__(self):
        return f"[CardContainer with {len(self.cards)} cards]"

class Team:
    def __init__(self, name: str, members: List[str], max_hand_size: int = 5, max_challenges: int =1):
        self.name = name
        self.members = members
        self.max_hand_size = max_hand_size
        self.max_challenges = max_challenges
        self.hand = CardContainer()
        self.active_challenges = CardContainer()

    def has_hand_space(self) -> bool:
        return len(self.hand) < self.max_hand_size

    def has_challenge_space(self) -> bool:
        return len(self.active_challenges) < self.max_challenges

    def __repr__(self):
        return f"[Team: {self.name} - Hand: {len(self.hand)}/{self.max_hand_size} - Active Challenges: {len(self.active_challenges)}]"
