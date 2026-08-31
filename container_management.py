from __future__ import annotations
from typing import List, Optional, Dict, Any, Union
import json
import pandas as pd

# --- FACTORY DISPATCHER ---

def item_from_dict(data: Union[Dict[str, Any], Any]) -> Any:
    if not isinstance(data, dict) or "model_type" not in data:
        return data

    model_type = data["model_type"]

    if model_type == "ChallengeCard":
        return ChallengeCard(
            title=data["title"],
            description=data["description"],
            card_type=data["card_type"],
            duration=data["duration"],
        )
    elif model_type == "RewardCard":
        return RewardCard(
            title=data["title"],
            description=data["description"],
            card_type=data["card_type"],
            reward_type=data["reward_type"],
        )
    elif model_type == "Card":
        return Card(
            title=data["title"],
            description=data["description"],
            card_type=data["card_type"],
        )
    elif model_type == "Player":
        return Player(name=data["name"])
    elif model_type == "Area":
        return Area(
            name=data["name"],
            prot_start=data.get("prot_start"),
            prot_end=data.get("prot_end"),
        )

    return data

# --- CONTAINER CLASS ---

class Container:
    def __init__(
        self, name: str, type: str, items: Optional[List[Any]] = None
    ):
        self.name = name
        self.type = type
        self.items = list(items) if items is not None else []

    def add_item(self, item: Any) -> None:
        self.items.append(item)

    def remove_item(self, item: Any) -> bool:
        if item in self.items:
            self.items.remove(item)
            return True
        return False

    def transfer_item(self, item: Any, recipient: Container) -> bool:
        if item in self.items:
            self.items.remove(item)
            recipient.add_item(item)
            return True
        return False

    def to_json(self, indent: Optional[int] = None) -> str:
        serialized_items = [
            item.to_dict() if hasattr(item, "to_dict") else item
            for item in self.items
        ]
        return json.dumps(
            {"name": self.name, "type": self.type, "items": serialized_items},
            indent=indent,
        )

    @classmethod
    def from_json(cls, json_str: str) -> Container:
        data = json.loads(json_str)
        deserialised_items = [item_from_dict(i) for i in data["items"]]
        return cls(
            name=data["name"],
            type=data["type"],
            items=deserialised_items,
        )

# --- ITEMS ---

class Card:
    def __init__(self, title: str, description: str, card_type: str):
        self.title = title
        self.description = description
        self.card_type = card_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_type": self.__class__.__name__,
            "title": self.title,
            "description": self.description,
            "card_type": self.card_type,
        }

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Card) and self.to_dict() == other.to_dict()


class ChallengeCard(Card):
    def __init__(self, title: str, description: str, card_type: str, duration: int):
        super().__init__(title, description, card_type)
        self.duration = duration

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["duration"] = self.duration
        return data


class RewardCard(Card):
    def __init__(self, title: str, description: str, card_type: str, reward_type: str):
        super().__init__(title, description, card_type)
        self.reward_type = reward_type

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["reward_type"] = self.reward_type
        return data


class Player:
    def __init__(self, name: str):
        self.name = name

    def to_dict(self) -> Dict[str, Any]:
        return {"model_type": "Player", "name": self.name}

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Player) and self.name == other.name


class Area:
    def __init__(
        self,
        name: str,
        prot_start: Optional[float] = None,
        prot_end: Optional[float] = None,
    ):
        self.name = name
        self.prot_start = prot_start
        self.prot_end = prot_end

    def _check_expiration(self) -> None:
        if self.prot_end is not None:
            now = pd.Timestamp.now(tz="UTC")
            end_dt = pd.to_datetime(self.prot_end, unit="s", utc=True)
            remaining_seconds = (end_dt - now).total_seconds()
            
            if remaining_seconds < 0:
                self.prot_start = None
                self.prot_end = None

    @property
    def is_prot(self) -> bool:
        self._check_expiration()
        if self.prot_start is not None and self.prot_end is not None:
            now = pd.Timestamp.now(tz="UTC").timestamp()
            return self.prot_start <= now < self.prot_end
        return False

    @property
    def prot_remaining(self) -> Optional[pd.Timedelta]:
        self._check_expiration()
        if self.is_prot and self.prot_end is not None:
            now = pd.Timestamp.now(tz="UTC")
            end_dt = pd.to_datetime(self.prot_end, unit="s", utc=True)
            return max(end_dt - now, pd.Timedelta(0))
        return None

    def to_dict(self) -> Dict[str, Any]:
        self._check_expiration()
        return {
            "model_type": "Area",
            "name": self.name,
            "prot_start": self.prot_start,
            "prot_end": self.prot_end,
        }

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Area) and self.to_dict() == other.to_dict()