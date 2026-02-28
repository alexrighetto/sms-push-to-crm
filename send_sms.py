import sqlite3
import requests
import os
import shutil
from datetime import datetime

# -----------------------------
# CONFIG
# -----------------------------

LIVE_DB = os.path.expanduser("~/Library/Messages/chat.db")
SNAPSHOT_DB = os.path.expanduser("~/crm_sync/messages/chat.db")
WEBHOOK = "https://n8n.srv739556.hstgr.cloud/webhook/sms-ingest"
STATE_FILE = os.path.expanduser("~/sms_bridge/last_id.txt")

# -----------------------------
# SNAPSHOT COPY (keeps DB fresh)
# -----------------------------

def refresh_snapshot():
    try:
        shutil.copy2(LIVE_DB, SNAPSHOT_DB)
        print("Snapshot updated:", datetime.now())
    except Exception as e:
        print("Snapshot copy failed:", e)

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
    with open(STATE_FILE, "w") as f:
        f.write(str(last_id))

# -----------------------------
# MAIN
# -----------------------------

# refresh DB snapshot first
refresh_snapshot()

# connect to snapshot DB
conn = sqlite3.connect(SNAPSHOT_DB)
cur = conn.cursor()

last_id = get_last_id()

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
        requests.post(WEBHOOK, json=payload, timeout=10)
        print("Sent:", payload)
    except Exception as e:
        print("Error sending:", e)

    if rowid > max_id:
        max_id = rowid

save_last_id(max_id)

conn.close()
