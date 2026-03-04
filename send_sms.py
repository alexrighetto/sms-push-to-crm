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
    raise Exception("Missing config.py. Copy config.example.py to config.py and edit it.")

LIVE_DB = os.path.expanduser(config.LIVE_DB)
SNAPSHOT_DB = os.path.expanduser(config.SNAPSHOT_DB)
WEBHOOK = config.WEBHOOK
STATE_FILE = os.path.expanduser(config.STATE_FILE)

# Optional: first-run bootstrap window (days). If 0 -> no bootstrap.
BOOTSTRAP_DAYS = int(getattr(config, "BOOTSTRAP_DAYS", 0))

# Optional: throttle between webhook posts (seconds). Ex: 0.2
RATE_LIMIT_SLEEP = float(getattr(config, "RATE_LIMIT_SLEEP", 0))

DEVICE_ID = getattr(config, "DEVICE_ID", "unknown-device")


# -----------------------------
# SNAPSHOT COPY
# -----------------------------

def refresh_snapshot():
    try:
        os.makedirs(os.path.dirname(SNAPSHOT_DB), exist_ok=True)

        # copy main database
        shutil.copy2(LIVE_DB, SNAPSHOT_DB)

        # copy WAL and SHM files if they exist
        for suffix in ("-wal", "-shm"):
            src = LIVE_DB + suffix
            dst = SNAPSHOT_DB + suffix

            if os.path.exists(src):
                shutil.copy2(src, dst)

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
# APPLE TIME CONVERSION
# -----------------------------
# Apple Messages stores time as nanoseconds since 2001-01-01 00:00:00 UTC.
# Unix epoch starts at 1970-01-01. The offset is 978307200 seconds.

def apple_time_to_unix(date_ns):
    try:
        return int(date_ns / 1_000_000_000 + 978307200)
    except:
        return None


# -----------------------------
# EVENT TYPE DETECTION
# -----------------------------

def detect_event_type(text, attachments_csv, associated_type):
    has_attachments = bool(attachments_csv)
    has_reaction = associated_type is not None and int(associated_type) > 0
    has_text = bool(text)

    if has_attachments:
        return "attachment"
    if has_reaction:
        return "reaction"
    if has_text:
        return "message"
    return "unknown"


def normalize_protocol(service):
    if not service:
        return "unknown"
    s = str(service).strip().lower()
    if s == "sms":
        return "sms"
    if s == "imessage":
        return "imessage"
    return s


def split_attachments(attachments_csv):
    if not attachments_csv:
        return []
    parts = [p.strip() for p in str(attachments_csv).split(",") if p.strip()]
    # de-dup while preserving order
    seen = set()
    out = []
    for p in parts:
        if p not in seen:
            out.append(p)
            seen.add(p)
    return out


# -----------------------------
# QUERY BUILDER
# -----------------------------
# We GROUP BY message ROWID to avoid duplicates from joins (attachments/chat joins).

def build_query(last_id):

    base_select = """
    SELECT
        m.ROWID                                AS message_rowid,
        m.text                                 AS text,
        m.date                                 AS date_ns,
        m.is_from_me                           AS is_from_me,
        h.id                                   AS sender_phone,
        m.service                              AS service,
        m.associated_message_type              AS associated_message_type,
        GROUP_CONCAT(DISTINCT a.filename) AS attachments_csv,
        GROUP_CONCAT(DISTINCT a.mime_type) AS attachment_types,
        c.chat_identifier                      AS chat_identifier,
        c.display_name                         AS chat_display_name
    FROM message m

    LEFT JOIN handle h
        ON m.handle_id = h.ROWID

    LEFT JOIN chat_message_join cmj
        ON cmj.message_id = m.ROWID

    LEFT JOIN chat c
        ON c.ROWID = cmj.chat_id

    LEFT JOIN message_attachment_join maj
        ON maj.message_id = m.ROWID

    LEFT JOIN attachment a
        ON a.ROWID = maj.attachment_id
    """

    if last_id == 0 and BOOTSTRAP_DAYS > 0:
        print(f"Bootstrap mode active ({BOOTSTRAP_DAYS} days)")

        query = f"""
        {base_select}
        WHERE datetime(m.date/1000000000 + 978307200, 'unixepoch')
            >= datetime('now', '-{BOOTSTRAP_DAYS} days')
        GROUP BY m.ROWID
        ORDER BY m.ROWID ASC
        """
        params = ()

    else:
        query = f"""
        {base_select}
        WHERE m.ROWID > ?
        GROUP BY m.ROWID
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
        # Unpack (always 10 columns)
        rowid = row[0]
        text = row[1]
        date_ns = row[2]
        is_from_me = bool(row[3])
        sender_phone = row[4]
        service = row[5]
        associated_type = row[6]
        attachments_csv = row[7]
        attachment_types = row[8]
        chat_identifier = row[9]
        chat_display_name = row[10]

        protocol = normalize_protocol(service)
        attachments = split_attachments(attachments_csv)
        event_type = detect_event_type(text, attachments_csv, associated_type)

        unix_time = apple_time_to_unix(date_ns)
        iso_time = datetime.utcfromtimestamp(unix_time).isoformat() + "Z" if unix_time else None

        conversation_type = "group" if (chat_identifier or chat_display_name) else "direct"

        payload = {
            "id": rowid,
            "device_id": DEVICE_ID,
            
            "source": "imessage",
            "event_type": event_type,

            "from_me": is_from_me,
            "phone": sender_phone,          # sender (handle.id) when available
            "text": text,

            "date": date_ns,                # raw Apple date (ns since 2001)
            "timestamp_unix": unix_time,
            "timestamp_iso": iso_time,

            "protocol": protocol,           # sms / imessage / unknown

            "conversation_type": conversation_type,
            "chat_id": chat_identifier,
            "chat_name": chat_display_name,

            "attachments": attachments,     # list of attachment paths
            "attachment_types": attachment_types,
            "reaction_type": associated_type # numeric tapback type when present
        }

        try:
            response = requests.post(WEBHOOK, json=payload, timeout=10)
            response.raise_for_status()
            print("Sent:", rowid, event_type, protocol, conversation_type)
        except Exception as e:
            print("Webhook error. Sync stopped:", e)
            conn.close()
            return

        if rowid > max_id:
            max_id = rowid

        if RATE_LIMIT_SLEEP > 0:
            try:
                import time
                time.sleep(RATE_LIMIT_SLEEP)
            except:
                pass

    save_last_id(max_id)
    print("Checkpoint saved:", max_id)

    conn.close()


if __name__ == "__main__":
    main()
