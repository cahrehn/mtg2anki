"""Scryfall API client."""

import time

import requests

from .config import API_HEADERS


def scryfall_get(url, attempts=4, log=print, sleep=time.sleep):
    """GET a Scryfall URL with retries on transient failures"""
    delay = 2
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, headers=API_HEADERS, timeout=30)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt == attempts:
                raise
            log(f"  Scryfall request failed ({e}); retry {attempt}/{attempts - 1} in {delay}s")
            sleep(delay)
            delay *= 2


def fetch_set_info(set_code, log=print):
    """Fetch set information from Scryfall API"""
    url = f"https://api.scryfall.com/sets/{set_code}"
    data = scryfall_get(url, log=log).json()
    return {
        "code": data["code"],
        "name": data["name"],
        "released_at": data.get("released_at", "Unknown"),
    }
