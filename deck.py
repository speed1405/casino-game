import random

SUITS = ['♠', '♥', '♦', '♣']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

def create_deck(num_decks=1):
    deck = [{'suit': suit, 'rank': rank} for suit in SUITS for rank in RANKS] * num_decks
    random.shuffle(deck)
    return deck

def card_value_blackjack(card):
    if card['rank'] in ['J', 'Q', 'K']:
        return 10
    if card['rank'] == 'A':
        return 11
    return int(card['rank'])

def calculate_hand_blackjack(hand):
    value = sum(card_value_blackjack(card) for card in hand)
    aces = sum(1 for card in hand if card['rank'] == 'A')
    while value > 21 and aces:
        value -= 10
        aces -= 1
    return value

def card_value_baccarat(card):
    if card['rank'] in ['10', 'J', 'Q', 'K']:
        return 0
    if card['rank'] == 'A':
        return 1
    return int(card['rank'])

def calculate_hand_baccarat(hand):
    value = sum(card_value_baccarat(card) for card in hand)
    return value % 10
