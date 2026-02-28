import sqlite3
import requests
import os
import shutil
from datetime import datetime

# -----------------------------
# LOAD CONFIG
# -----------------------------

try:
    import config
except ImportError:
    raise Exception(
        "Missing config.py. Copy config.example.py to config.py and edit it."
    )

LIVE_DB = os.path.expanduser(config.LIVE_DB)
SNAPSHOT_DB = os.path.expanduser(config.SNAPSHOT_DB)
WEBHOOK = config.WEBHOOK
STATE_FILE = os.path.expanduser(config.STATE_FILE)

# -----------------------------
# SNAPSHOT COPY
# -----------------------------

def refresh_snapshot():
    try:
        os.makedirs(os.path.dirname(SNAPSHOT_DB), exist_ok=True)
        shutil.copy2(LIVE_DB, SNAPSHOT_DB)
        print("Snapshot updated:", datetime.now())
    except Exception as e:
        raise Exception(f"Snapshot copy failed: {e}")

# -----------------------------
# STATE MANAGEMENT
# -----------------------------

def get_last_id():
    try:
        with open(STATE_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return 0


def save_last_id(last_id):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        f.write(str(last_id))

# -----------------------------
# MAIN
# -----------------------------

def main():

    refresh_snapshot()

    conn = sqlite3.connect(SNAPSHOT_DB)
    cur = conn.cursor()

    last_id = get_last_id()
    print("Last processed ROWID:", last_id)

    query = """
    SELECT
        message.ROWID,
        message.text,
        message.date,
        message.is_from_me,
        handle.id
    FROM message
    LEFT JOIN handle ON message.handle_id = handle.ROWID
    WHERE message.ROWID > ?
    ORDER BY message.ROWID ASC
    """

    cur.execute(query, (last_id,))
    rows = cur.fetchall()

    max_id = last_id

    for row in rows:
        rowid, text, date, is_from_me, phone = row

        payload = {
            "id": rowid,
            "phone": phone,
            "text": text,
            "from_me": is_from_me,
            "date": date
        }

        try:
            response = requests.post(WEBHOOK, json=payload, timeout=10)
            response.raise_for_status()
            print("Sent:", payload)
        except Exception as e:
            print("Webhook error. Sync stopped:", e)
            conn.close()
            return

        if rowid > max_id:
            max_id = rowid

    save_last_id(max_id)
    print("Checkpoint saved:", max_id)

    conn.close()


if __name__ == "__main__":
    main()
