import random as r

class Card:
    def __init__(self, title: str, description: str, card_type: str):
        self.title = title
        self.description = description
        self.card_type = card_type

    def __repr__(self):
        return f"[{self.card_type}: {self.title} - {self.description}]"

class ChallengeCard(Card):
    def __init__(self, title: str, description: str, duration: int):
        super().__init__(title, description, card_type="Challenge")
        self.duration = duration

    def __repr__(self):
        return f"[Challenge: {self.title} - '{self.description}' ({self.duration})]"

class Deck:
    def __init__(self, cards: list):
        self.cards = cards
        self.dealt_cards = {}
        self.shuffle()

    def shuffle(self):
        r.shuffle(self.cards)

    def deal_card(self, recipient: "Team", mode: str):
        if len(self.cards) == 0:
            return None

        if mode == "challenge":
             if not recipient.has_challenge_space():
                  return None
        else:
            if not recipient.has_hand_space():
                return None

        drawn_card = self.cards.pop()
        
        recipient.add_card(drawn_card, mode=mode)
        
        self.dealt_cards[drawn_card] = recipient.name
        return drawn_card

    def return_card(self, card: Card, donor: "Team"):
        if card in self.dealt_cards:
            del self.dealt_cards[card]

        donor.remove_card(card.title) 
        self.cards.append(card)
        self.shuffle()

    def get_owner(self, card: Card):
        return self.dealt_cards.get(card)

class Team:
    def __init__(self, name: str, members: list, max_hand_size: int = 5, max_challenges: int = 1):
        self.name = name
        self.members = members
        self.max_hand_size = max_hand_size
        self.max_challenges = max_challenges 
        self.hand = []
        self.active_challenges = []

    def has_hand_space(self) -> bool:
        return len(self.hand) < self.max_hand_size

    def has_challenge_space(self) -> bool:
        return len(self.active_challenges) < self.max_challenges

    def add_card(self, card: Card, mode: str = "reward") -> bool:
        if mode == "challenge":
            if not self.has_challenge_space():
                return False
            self.active_challenges.append(card)
            return True
        else:
            if not self.has_hand_space():
                return False
            self.hand.append(card)
            return True

    def remove_card(self, title: str):
        for card in self.hand:
            if card.title.lower() == title.lower():
                self.hand.remove(card)
                return card 
            
        for card in self.active_challenges:
            if card.title.lower() == title.lower():
                self.active_challenges.remove(card)
                return card
        print(f"Card '{title}' not found in {self.name}'s items.")
        return None

    def __repr__(self):
        return f"Team: '{self.name}' (Hand: {len(self.hand)}/{self.max_hand_size} cards | Active Challenges: {len(self.active_challenges)}/{self.max_challenges})"
