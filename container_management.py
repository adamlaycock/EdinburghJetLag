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

    def remove_card(self, card: Card) -> Optional[Card]:
        if card in self.cards:
            self.cards.remove(card)
            return card
        return None

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
        if not json_str or json_str.strip() in ("", "[]"):
            return cls(name=name, cards=[])
        
        raw_cards = json.loads(json_str)
        cards = [card_from_dict(c) for c in raw_cards]
        return cls(name=name, cards=cards, auto_shuffle=False)

@dataclass
class Area:
    name: str
    control: str
    prot_start: Optional[pd.Timestamp] = None
    prot_end: Optional[pd.Timestamp] = None

    @property
    def is_prot(self) -> bool:
        if self.prot_start and self.prot_end:
            now = pd.Timestamp.now()
            return self.prot_start <= now < self.prot_end
        return False

    @property
    def prot_remaining(self) -> Optional[pd.Timedelta]:
        if self.is_prot and self.prot_end:
            now = pd.Timestamp.now()
            return max(self.prot_end - now, pd.Timedelta(0))
        return None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["prot_start"] = (
            self.prot_start.isoformat()
            if self.prot_start is not None
            else None
        )
        data["prot_end"] = (
            self.prot_end.isoformat()
            if self.prot_end is not None
            else None
        )
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Area":
        return cls(
            name=data["name"],
            control=data["control"],
            prot_start=(
                pd.Timestamp(data["prot_start"])
                if data.get("prot_start")
                else None
            ),
            prot_end=(
                pd.Timestamp(data["prot_end"]) 
                if data.get("prot_end") 
                else None
            ),
        )

class AreaContainer:
    def __init__(self, name: str, areas: Optional[List[Area]] = None):
        self.name = name
        self.areas = list(areas) if areas is not None else []

    def remove_area(self, area: Area) -> Optional[Area]:
        if area in self.areas:
            self.areas.remove(area)
            return area
        return None

    def add_area(self, area: Area) -> None:
        self.areas.append(area)

    def to_json(self) -> str:
        return json.dumps([a.to_dict() for a in self.areas])

    @classmethod
    def from_json(cls, name: str, json_str: str) -> "AreaContainer":
        if not json_str or json_str.strip() in ("", "[]"):
            return cls(name=name, areas=[])

        raw_areas = json.loads(json_str)
        areas = [Area.from_dict(a) for a in raw_areas]
        return cls(name=name, areas=areas)

    def __len__(self):
        return len(self.areas)

    def __repr__(self):
        return f"[{self.name} with {len(self.areas)} areas]"

class Team:
    def __init__(self, name: str, members: List[str], max_hand_size: int = 5, max_challenges: int = 1):
        self.name = name
        self.members = members
        self.max_hand_size = max_hand_size
        self.max_challenges = max_challenges
        self.hand = CardContainer(name=f"{name}_hand")
        self.active_challenges = CardContainer(name=f"{name}_active")
        self.areas = AreaContainer(name=f"{name}_areas")

    def has_hand_space(self) -> bool:
        return len(self.hand) < self.max_hand_size

    def has_challenge_space(self) -> bool:
        return len(self.active_challenges) < self.max_challenges

    def __repr__(self):
        return f"[Team: {self.name} - Hand: {len(self.hand)}/{self.max_hand_size} - Active: {len(self.active_challenges)}]"









def load_card_container(container_key: str) -> CardContainer:
    df = conn.read(worksheet="container_mgmt", ttl=0)

    if df.empty or "container_key" not in df.columns:
        return CardContainer(name=container_key)

    match = df[df["container_key"] == container_key]
    if match.empty:
        return CardContainer(name=container_key)

    json_str = match.iloc[0]["json"]
    return CardContainer.from_json(name=container_key, json_str=json_str)

def load_area_container(container_key: str) -> AreaContainer:
    df = conn.read(worksheet="container_mgmt", ttl=0)

    if df.empty or "container_key" not in df.columns:
        return AreaContainer(name=container_key)

    match = df[df["container_key"] == container_key]
    if match.empty:
        return AreaContainer(name=container_key)

    json_str = match.iloc[0]["json"]
    return AreaContainer.from_json(name=container_key, json_str=json_str)

def save_container(container: CardContainer | AreaContainer) -> None:
    df = conn.read(worksheet="container_mgmt", ttl=0)

    if df.empty or "container_key" not in df.columns:
        df = pd.DataFrame(columns=["container_key", "json"])

    df["container_key"] = df["container_key"].astype(str)
    df["json"] = df["json"].astype(str)

    if container.name in df["container_key"].values:
        df.loc[df["container_key"] == container.name, "json"] = container.to_json()
    else:
        new_row = pd.DataFrame([{
            "container_key": container.name,
            "json": container.to_json()
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        
    conn.update(worksheet="container_mgmt", data=df)
    st.cache_data.clear()

def transfer_card(donor: CardContainer , card: Card, recipient: CardContainer) -> None:
    removed = donor.remove_card(card)
    if removed:
        recipient.add_card(removed)

def transfer_area(donor: AreaContainer , area: Area, recipient: AreaContainer) -> None:
    removed = donor.remove_area(area)
    if removed:
        recipient.add_area(removed)
