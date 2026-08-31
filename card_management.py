from dataclasses import dataclass, asdict
import json
import random as r
from typing import List, Optional, Dict, Any
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

conn = st.connection("gsheets", type=GSheetsConnection)

@dataclass
class Card:
    title: str
    description: str
    type: str

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["_class"] = self.__class__.__name__
        return data

@dataclass
class ChallengeCard(Card):
    duration: str

@dataclass
class RewardCard(Card):
    reward_type: str

CARD_TYPES = {
    "Card": Card,
    "ChallengeCard": ChallengeCard,
    "RewardCard": RewardCard
}

def card_from_dict(data: Dict[str, Any]) -> Card:
    class_name = data.pop("_class", "Card")
    cls = CARD_TYPES.get(class_name, Card)
    return cls(**data)

class CardContainer:
    def __init__(self, name: str, cards: Optional[List[Card]] = None, auto_shuffle: bool = False):
        self.name = name
        self.cards = list(cards) if cards is not None else []
        if auto_shuffle and self.cards:
            self.shuffle()

    def shuffle(self) -> None:
        r.shuffle(self.cards)

    def remove_card(self) -> Optional[Card]:
        return self.cards.pop() if self.cards else None

    def add_card(self, card: Card) -> None:
        self.cards.append(card)

    def __len__(self):
        return len(self.cards)

    def __repr__(self):
        return f"[CardContainer '{self.name}' ({len(self.cards)} cards)]"

    def to_json(self) -> str:
        return json.dumps([c.to_dict() for c in self.cards])

    @classmethod
    def from_json(cls, name: str, json_str: str) -> "CardContainer":
        if not json_str or json_str == "[]":
            return cls(name=name, cards=[])
        
        raw_cards = json.loads(json_str)
        cards = [card_from_dict(c) for c in raw_cards]
        return cls(name=name, cards=cards, auto_shuffle=False)

class Team:
    def __init__(self, name: str, members: List[str], max_hand_size: int = 5, max_challenges: int = 1):
        self.name = name
        self.members = members
        self.max_hand_size = max_hand_size
        self.max_challenges = max_challenges
        self.hand = CardContainer(name=f"{name}_hand")
        self.active_challenges = CardContainer(name=f"{name}_active")

    def has_hand_space(self) -> bool:
        return len(self.hand) < self.max_hand_size

    def has_challenge_space(self) -> bool:
        return len(self.active_challenges) < self.max_challenges

    def __repr__(self):
        return f"[Team: {self.name} - Hand: {len(self.hand)}/{self.max_hand_size} - Active: {len(self.active_challenges)}]"

def load_card_container(container_key: str) -> CardContainer:
    df = conn.read(worksheet="card_management", ttl=0)

    if df.empty or "container_key" not in df.columns:
        return CardContainer(name=container_key)

    match = df[df["container_key"] == container_key]
    if match.empty:
        return CardContainer(name=container_key)

    json_str = match.iloc[0]["cards_json"]
    return CardContainer.from_json(name=container_key, json_str=json_str)

def save_card_container(card_container: CardContainer) -> None:
    df = conn.read(worksheet="card_management", ttl=0)

    if df.empty or "container_key" not in df.columns:
        df = pd.DataFrame(columns=["container_key", "cards_json"])

    df["container_key"] = df["container_key"].astype(str)
    df["cards_json"] = df["cards_json"].astype(str)

    if card_container.name in df["container_key"].values:
        df.loc[df["container_key"] == card_container.name, "cards_json"] = card_container.to_json()
    else:
        new_row = pd.DataFrame([{
            "container_key": card_container.name,
            "cards_json": card_container.to_json()
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        
    conn.update(worksheet="card_management", data=df)
    st.cache_data.clear()
