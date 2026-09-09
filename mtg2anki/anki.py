"""AnkiConnect client."""

import requests

from .config import ANKICONNECT_URL


def invoke_ankiconnect(action, **params):
    """Call AnkiConnect API"""
    response = requests.post(ANKICONNECT_URL, json={
        "action": action,
        "version": 6,
        "params": params
    })
    result = response.json()
    if result.get("error"):
        raise Exception(f"AnkiConnect error: {result['error']}")
    return result["result"]


def ankiconnect_available(log=print):
    """Return True if AnkiConnect responds on localhost"""
    try:
        invoke_ankiconnect("version")
        return True
    except Exception as e:
        log(f"AnkiConnect not reachable: {e}")
        return False
