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

        WHERE datetime(m.date/1000000000 + 978307200, 'unixepoch')
            >= datetime('now', '-{BOOTSTRAP_DAYS} days')

        ORDER BY m.ROWID ASC
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
# EVENT TYPE DETECTION
# -----------------------------

def detect_event(text, filename, associated_type):

    if filename:
        return "attachment"

    if associated_type and associated_type > 0:
        return "reaction"

    if text:
        return "message"

    return "unknown"


# -----------------------------
# APPLE TIME CONVERSION
# -----------------------------

def apple_time_to_unix(date):

    try:
        unix = int(date / 1000000000 + 978307200)
        return unix
    except:
        return None


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

        rowid = row[0]
        text = row[1]
        date = row[2]
        is_from_me = row[3]
        phone = row[4]
        associated_type = row[5]
        filename = row[6]

        event_type = detect_event(text, filename, associated_type)

        unix_time = apple_time_to_unix(date)

        payload = {
            "id": rowid,
            "phone": phone,
            "text": text,
            "from_me": bool(is_from_me),
            "date": date,
            "timestamp_unix": unix_time,
            "timestamp_iso": datetime.utcfromtimestamp(unix_time).isoformat() if unix_time else None,
            "event_type": event_type,
            "attachment": filename
        }

        try:

            response = requests.post(
                WEBHOOK,
                json=payload,
                timeout=10
            )

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
