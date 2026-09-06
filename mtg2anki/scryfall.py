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


def fetch_cards(set_code, log=print):
    """Fetch commons/uncommons for a set, excluding basics and DFCs"""
    query = f"set:{set_code} r<r -type:basic -is:dfc"
    url = f"{API}/cards/search?q={query}&order=spoiled"

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
