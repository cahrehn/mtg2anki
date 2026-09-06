"""Run-to-run state: which cards we have already seen."""

import json


def load_seen_ids(path):
    """Load previously seen card IDs (desktop/AnkiConnect run)"""
    if path.exists():
        with open(path, "r") as f:
            return json.load(f).get("card_ids", [])
    return []


def save_seen_ids(path, card_ids):
    """Save current card IDs to state file"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"card_ids": card_ids}, f, indent=2)


class FeedState:
    """Assigns every card a stable, increasing sequence number.

    The phone stores the highest sequence number it has imported, so it can
    work out what is new without us tracking per-device state on this end.
    """

    def __init__(self, seqs=None, next_seq=1):
        self.seqs = dict(seqs or {})
        self.next_seq = next_seq

    @classmethod
    def load(cls, path):
        if not path.exists():
            return cls()
        with open(path, "r") as f:
            data = json.load(f)
        return cls(data.get("seqs", {}), data.get("next_seq", 1))

    def save(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump({"next_seq": self.next_seq, "seqs": self.seqs}, f, indent=2, sort_keys=True)
            f.write("\n")

    def seq_for(self, card_id):
        """Sequence number for a card, assigning one if it is new"""
        if card_id not in self.seqs:
            self.seqs[card_id] = self.next_seq
            self.next_seq += 1
        return self.seqs[card_id]

    def is_known(self, card_id):
        return card_id in self.seqs
