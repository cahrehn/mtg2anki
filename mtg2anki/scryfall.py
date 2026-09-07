"""Scryfall API access."""

import time

import requests

API = "https://api.scryfall.com"

# Scryfall asks clients to identify themselves and to leave 50-100ms between
# requests. https://scryfall.com/docs/api
HEADERS = {
    "User-Agent": "mtg2anki/1.0 (+https://github.com/cahrehn/mtg2anki)",
    "Accept": "application/json",
}
REQUEST_DELAY = 0.1


def fetch_set_info(set_code):
    """Fetch set information from Scryfall API"""
    response = requests.get(f"{API}/sets/{set_code}", headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    return {
        "code": data["code"],
        "name": data["name"],
        "released_at": data.get("released_at", "Unknown"),
    }


def search_query(set_code):
    """Commons and uncommons, minus basics, DFCs and Alchemy rebalances.

    Rebalanced cards share a set code with their paper originals, so without
    -is:rebalanced a set like DMU returns "A-Radha, Coalition Warlord"
    alongside "Radha, Coalition Warlord" - ten duplicate notes in that set.
    """
    return f"set:{set_code} r<r -type:basic -is:dfc -is:rebalanced"


def fetch_cards(set_code, log=print):
    """Fetch the cards we make notes for, following pagination"""
    url = f"{API}/cards/search?q={search_query(set_code)}&order=spoiled"

    all_cards = []
    while url:
        time.sleep(REQUEST_DELAY)
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        for card in data.get("data", []):
            if '"' not in card["name"]:
                all_cards.append({
                    "name": card["name"],
                    "id": card["id"],
                    "layout": card.get("layout", "normal"),
                })

        url = data.get("next_page")

    log(f"Found {len(all_cards)} cards")
    return all_cards
