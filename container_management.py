from __future__ import annotations
from typing import List, Optional, Dict, Any, Union
import json
import random as r
import time
from datetime import timedelta

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
            challenge_start=data.get("challenge_start"),
            challenge_end=data.get("challenge_end")
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
        self, name: str, type: str, max_items: int, items: Optional[List[Any]] = None
    ):
        self.name = name
        self.type = type
        self.max_items = max_items
        self.items = list(items) if items is not None else []

    def add_item(self, item: Any) -> None:
        if self.has_space():
            self.items.append(item)

    def remove_item(self, item: Any) -> bool:
        if item in self.items:
            self.items.remove(item)
            return True
        return False

    def transfer_item(self, item: Any, recipient: Container) -> bool:
        if item in self.items:
            if recipient.has_space():
                self.items.remove(item)
                recipient.add_item(item)
                return True
        return False

    def shuffle(self) -> None:
        r.shuffle(self.items)

    def to_json(self, indent: Optional[int] = None) -> str:
        serialized_items = [
            item.to_dict() if hasattr(item, "to_dict") else item
            for item in self.items
        ]
        return json.dumps(
            {
                "name": self.name, "type": self.type, 
                "max_items": self.max_items ,"items": serialized_items
            },
            indent=indent,
        )

    def has_space(self) -> bool:
        return len(self.items) < self.max_items

    @classmethod
    def from_json(cls, json_str: str) -> Container:
        data = json.loads(json_str)
        deserialised_items = [item_from_dict(i) for i in data["items"]]
        return cls(
            name=data["name"],
            type=data["type"],
            max_items = data["max_items"],
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
    def __init__(
        self, 
        title: str, 
        description: str, 
        card_type: str, 
        duration: int,
        challenge_start: Optional[float] = None,
        challenge_end: Optional[float] = None
    ):
        super().__init__(title, description, card_type)
        self.duration = duration
        self.challenge_start = challenge_start

        if challenge_end is not None:
            self.challenge_end = challenge_end
        elif challenge_start is not None:
            self.challenge_end = challenge_start + duration
        else:
            self.challenge_end = None

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["duration"] = self.duration
        data["challenge_start"] = self.challenge_start
        data["challenge_end"] = self.challenge_end
        return data

    def start_challenge(self) -> None:
        self.challenge_start = time.time()
        self.challenge_end = self.challenge_start + self.duration

    def _check_expiration(self) -> None:
        if self.challenge_end is not None:
            now = time.time()
            if now >= self.challenge_end:
                self.challenge_start = None
                self.challenge_end = None

    @property
    def is_active(self) -> bool:
        self._check_expiration()
        if self.challenge_start is not None and self.challenge_end is not None:
            now = time.time()
            return self.challenge_start <= now < self.challenge_end
        return False

    @property
    def prot_remaining(self) -> Optional[timedelta]:
        self._check_expiration()
        if self.challenge_end is not None:
            remaining_seconds = self.challenge_end - time.time()
            return timedelta(seconds=max(remaining_seconds, 0))
        return None


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
            now = time.time()
            if now >= self.prot_end:
                self.prot_start = None
                self.prot_end = None

    def start_protection(self, duration: float) -> None:
        self.prot_start = time.time()
        self.prot_end = self.prot_start + duration

    @property
    def is_prot(self) -> bool:
        self._check_expiration()
        if self.prot_start is not None and self.prot_end is not None:
            now = time.time()
            return self.prot_start <= now < self.prot_end
        return False

    @property
    def prot_remaining(self) -> Optional[timedelta]:
        self._check_expiration()
        if self.prot_end is not None:
            remaining_seconds = self.prot_end - time.time()
            return timedelta(seconds=max(remaining_seconds, 0))
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
