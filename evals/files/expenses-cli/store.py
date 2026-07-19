import json
from pathlib import Path

DB = Path(__file__).parent / "expenses.json"


def load():
    if DB.exists():
        return json.loads(DB.read_text())
    return []


def save(items):
    DB.write_text(json.dumps(items, indent=2))
