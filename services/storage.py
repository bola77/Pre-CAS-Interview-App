# services/storage.py
import json
from pathlib import Path

DATA_FILE = Path("data/session_exports.json")

def save_session(payload: dict):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text())
        except Exception:
            data = []
    else:
        data = []
    data.append(payload)
    DATA_FILE.write_text(json.dumps(data, indent=2))