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

# optional bootstrap window
BOOTSTRAP_DAYS = getattr(config, "BOOTSTRAP_DAYS", 0)

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
# QUERY BUILDER
# -----------------------------

def build_query(last_id):

    # FIRST RUN → bootstrap window
    if last_id == 0 and BOOTSTRAP_DAYS > 0:
        print(f"Bootstrap mode active ({BOOTSTRAP_DAYS} days)")

        query = f"""
        SELECT
            message.ROWID,
            message.text,
            message.date,
            message.is_from_me,
            handle.id
        FROM message
        LEFT JOIN handle ON message.handle_id = handle.ROWID
        WHERE message.text IS NOT NULL
        AND datetime(message.date/1000000000 + 978307200, 'unixepoch')
            >= datetime('now', '-{BOOTSTRAP_DAYS} days')
        ORDER BY message.ROWID ASC
        """

        params = ()

    # NORMAL INCREMENTAL MODE
    else:
        query = """
        SELECT
            m.ROWID,
            m.text,
            m.date,
            m.is_from_me,
            h.id AS phone,
            m.associated_message_type,
            a.filename
        FROM message m
        
        LEFT JOIN handle h
            ON m.handle_id = h.ROWID
        
        LEFT JOIN message_attachment_join maj
            ON maj.message_id = m.ROWID
        
        LEFT JOIN attachment a
            ON a.ROWID = maj.attachment_id
        
        WHERE m.ROWID > ?
        ORDER BY m.ROWID ASC
        """

        params = (last_id,)

    return query, params

# -----------------------------
# MAIN
# -----------------------------

def main():

    refresh_snapshot()

    conn = sqlite3.connect(SNAPSHOT_DB)
    cur = conn.cursor()

    last_id = get_last_id()
    print("Last processed ROWID:", last_id)

    query, params = build_query(last_id)

    cur.execute(query, params)
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
