import random as r
from typing import List, Optional
from dataclasses import dataclass, asdict
import json
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

conn = st.connection("gsheets", type=GSheetsConnection)

@dataclass
class Card:
    def __init__(self, title: str, description: str, type: str):
        self.title = title
        self.description = description
        self.type = type

    def __repr__(self):
        return f"[{self.title} ({self.type}) - {self.description}]"

@dataclass
class ChallengeCard(Card):
    def __init__(self, title: str, description: str, type: str, duration: str):
        super().__init__(title, description, type)
        self.duration = duration

@dataclass
class RewardCard(Card):
    def __init__(self, title: str, description: str, type: str, reward_type: str):
        super().__init__(title, description, type)
        self.reward_type = reward_type

    def __repr__(self):
        return f"[{self.title} ({self.reward_type}) - {self.description}]"

class CardContainer:
    def __init__(self, name: str, cards: Optional[List[Card]] = None):
        self.name = name
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

    def to_json(self) -> str:
        return json.dumps([asdict(c) for c in self.cards])

    @classmethod
    def from_json(cls, name: str, json_str: str) -> CardContainer:
        if not json_str or json_str == "[]":
            return cls(name=name, cards=[])
        
        raw_cards = json.loads(json_str)
        cards = [Card(**c) for c in raw_cards]
        return cls(name=name, cards=cards)

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


def load_card_container(container_key: str) -> CardContainer:
    df = conn.read(worksheet="card_management", ttl=0)

    match = df[df["container_key"] == container_key]

    if match.empty:
        return(CardContainer(name=container_key))

    json_str = match.iloc[0]["cards_json"]
    return CardContainer.from_json(name=container_key, json_str=json_str)

def save_card_container(card_container: CardContainer) -> None:
    df = conn.read(worksheet="card_management", ttl=0)

    if card_container.name in df["container_key"].values:
        df.loc[df["container_key"] == card_container.name, "cards_json"] = card_container.to_json()
    else:
        new_row = pd.DataFrame(
            [{
                "container_key": card_container.name, 
                "cards_json": card_container.to_json()
            }]
        )
        df = pd.concat([df, new_row], ignore_index=True)
        
    conn.update(worksheet="card_management", data=df)
    st.cache_data.clear()
    